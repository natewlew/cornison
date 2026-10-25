#!/usr/bin/env python3
"""
Derive the QMK `LAYOUT` key array for keyboards/cornison/keyboard.json
directly from pcb/cornison.kicad_pcb, the same way case/extract_board.py
derives the case geometry from it.

Ground truth, not hand-typed guesses:
  - matrix row/col come from the row*/col* net names on each switch pad
    and its paired diode (not from eyeballing the schematic).
  - x/y come from the real footprint positions (mm -> key units), using
    one global origin/scale for the whole panel, so the real gap between
    the two halves is preserved automatically.
  - rotation is pcbnew's raw GetOrientationDegrees(), unnegated: QMK/KLE
    layout space is Y-down, same sense as KiCad's own Y-down screen, so
    unlike case.py's load_board() (which negates rotation once when
    moving into build123d's Y-up 3D frame) no sign flip belongs here.

Run with KiCad's bundled python3 (has pcbnew), same as extract_board.py:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 \
      firmware/qmk/gen_layout.py
"""
import json
import re
from pathlib import Path

import pcbnew

PCB_PATH = Path(__file__).resolve().parent.parent.parent / "pcb" / "cornison.kicad_pcb"
KEY_UNIT_MM = 19.05


# QMK's RGB Matrix wants x 0-224, y 0-64 across the whole keyboard.
RGB_X_MAX, RGB_Y_MAX = 224, 64
LED_FLAG_UNDERGLOW, LED_FLAG_KEYLIGHT = 2, 4


def rgb_matrix_section(footprints, keys_by_ref, min_x, min_y):
    """`rgb_matrix`/`ws2812` for keyboard.json, from the real LED chains.

    Chain order is traced from the nets, not from reference numbers: each LED's
    DOUT (pad 2) net is the next LED's DIN (pad 4), and each half's chain
    starts at the LED whose DIN is the Pro Micro's data net (`LED` / `LED_r`).
    QMK numbers the left half's LEDs first, then the right's (split_count).
    Per-key LEDs (SK6812MINI-E) get the matrix position of the switch they sit
    under, found by proximity; the WS2812B underglow LEDs have no key.
    """
    leds = {}
    for fp in footprints:
        name = str(fp.GetFPID().GetLibItemName())
        if "SK6812" in name or "WS2812" in name:
            pads = {p.GetNumber(): p.GetNetname() for p in fp.Pads()}
            pos = fp.GetPosition()
            leds[fp.GetReference()] = {
                "din": pads["4"], "dout": pads["2"], "underglow": "WS2812" in name,
                "x": pcbnew.ToMM(pos.x), "y": pcbnew.ToMM(pos.y),
            }
    by_din = {v["din"]: ref for ref, v in leds.items()}
    chains = []
    for start_net in ("LED", "LED_r"):
        ref, chain = by_din[start_net], []
        while ref:
            chain.append(ref)
            ref = by_din.get(leds[ref]["dout"])
        chains.append(chain)
    if sorted(chains[0] + chains[1]) != sorted(leds):
        raise SystemExit("LED chains don't cover every LED exactly once")

    all_x = [k["x"] * KEY_UNIT_MM + min_x for k in keys_by_ref.values()]
    all_y = [k["y"] * KEY_UNIT_MM + min_y for k in keys_by_ref.values()]
    span_x, span_y = max(all_x) - min_x, max(all_y) - min_y

    entries = []
    used_switches = set()
    for chain in chains:
        for ref in chain:
            led = leds[ref]
            entry = {
                "x": round((led["x"] - min_x) / span_x * RGB_X_MAX),
                "y": round(min(max((led["y"] - min_y) / span_y, 0), 1) * RGB_Y_MAX),
            }
            if led["underglow"]:
                entry["flags"] = LED_FLAG_UNDERGLOW
            else:
                # the switch this LED sits under: nearest by footprint position
                sw = min(
                    keys_by_ref.values(),
                    key=lambda k: (k["x"] * KEY_UNIT_MM + min_x - led["x"]) ** 2
                    + (k["y"] * KEY_UNIT_MM + min_y - led["y"] + 0) ** 2,
                )
                dist = ((sw["x"] * KEY_UNIT_MM + min_x - led["x"]) ** 2 + (sw["y"] * KEY_UNIT_MM + min_y - led["y"]) ** 2) ** 0.5
                if dist > 8:
                    raise SystemExit(f"{ref}: nearest switch {sw['ref']} is {dist:.1f}mm away")
                if sw["ref"] in used_switches:
                    raise SystemExit(f"{ref}: switch {sw['ref']} already has an LED")
                used_switches.add(sw["ref"])
                entry = {"matrix": sw["matrix"], **entry, "flags": LED_FLAG_KEYLIGHT}
            entries.append(entry)
    if len(used_switches) != len(keys_by_ref):
        raise SystemExit(f"{len(keys_by_ref) - len(used_switches)} switches have no per-key LED")
    counts = [len(c) for c in chains]
    print(f"rgb_matrix: {counts} LEDs per half, chains start {chains[0][0]} / {chains[1][0]}, end {chains[0][-1]} / {chains[1][-1]}")
    return {
        "ws2812": {"pin": "D3"},
        "rgb_matrix": {"driver": "ws2812", "split_count": counts, "layout": entries},
    }


def main():
    board = pcbnew.LoadBoard(str(PCB_PATH))
    footprints = list(board.GetFootprints())

    switches = [fp for fp in footprints if fp.GetReference().startswith("SW")]
    diodes = [fp for fp in footprints if fp.GetReference().startswith("D")]

    # diode's non-row pad net -> row net, from the diode's own two pads.
    net_to_row = {}
    for d in diodes:
        nets = [p.GetNetname() for p in d.Pads()]
        rows = [n for n in nets if re.fullmatch(r"row\d+_?r?", n)]
        others = [n for n in nets if n not in rows]
        if len(rows) != 1 or len(others) != 1:
            raise SystemExit(f"{d.GetReference()}: expected 1 row net + 1 switch net, got {nets}")
        net_to_row[others[0]] = rows[0]

    keys = []
    for sw in switches:
        nets = [p.GetNetname() for p in sw.Pads() if p.GetNetname()]
        col_nets = [n for n in nets if re.fullmatch(r"col\d+_?r?", n)]
        other_nets = [n for n in nets if n not in col_nets]
        if len(col_nets) != 1 or len(other_nets) != 1:
            raise SystemExit(f"{sw.GetReference()}: expected 1 col net + 1 diode net, got {nets}")
        col_net = col_nets[0]
        row_net = net_to_row[other_nets[0]]

        is_right = col_net.endswith("_r")
        col = int(re.search(r"\d+", col_net).group())
        row = int(re.search(r"\d+", row_net).group()) + (4 if is_right else 0)

        pos = sw.GetPosition()
        x_mm, y_mm = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
        rot = sw.GetOrientationDegrees()
        fp_name = str(sw.GetFPID().GetLibItemName())

        key = {"ref": sw.GetReference(), "matrix": [row, col], "x_mm": x_mm, "y_mm": y_mm}
        if rot:
            key["r"] = round(rot, 2)
        if "1.5u" in fp_name:
            key["w"] = 1.5
        keys.append(key)

    if len(keys) != 48:
        raise SystemExit(f"expected 48 switches, found {len(keys)}")

    xs = [k["x_mm"] for k in keys]
    ys = [k["y_mm"] for k in keys]
    min_x, min_y = min(xs), min(ys)

    for k in keys:
        k["x"] = round((k["x_mm"] - min_x) / KEY_UNIT_MM, 3)
        k["y"] = round((k["y_mm"] - min_y) / KEY_UNIT_MM, 3)
        del k["x_mm"], k["y_mm"]

    # Reading order: row-pairs (0&4, 1&5, 2&6, 3&7), left half then right
    # half within a pair, left-to-right as the keys actually sit on the
    # board. The right half's column numbering mirrors the left's (col5
    # is the innermost column nearest the center gap on *both* halves),
    # so reading left-to-right across the right half means descending
    # column number - confirmed against the real x positions above
    # (e.g. row3 right: col3_r at x=10.47 sits left of col0_r at x=13.47).
    # This order is what keymap.c's LAYOUT(...) argument list must follow,
    # since the data-driven LAYOUT macro QMK generates from this array is
    # positional.
    def sort_key(k):
        row, col = k["matrix"]
        pair = row % 4
        half = 0 if row < 4 else 1
        col_key = col if half == 0 else -col
        return (pair, half, col_key)

    keys.sort(key=sort_key)

    seen = set()
    for k in keys:
        pos = tuple(k["matrix"])
        if pos in seen:
            raise SystemExit(f"duplicate matrix position {pos} ({k['ref']})")
        seen.add(pos)
    for row in range(8):
        for col in range(6):
            if (row, col) not in seen:
                raise SystemExit(f"missing matrix position [{row}, {col}]")

    layout = []
    for k in keys:
        entry = {"matrix": k["matrix"], "x": k["x"], "y": k["y"]}
        if "r" in k:
            entry["r"] = k["r"]
        if "w" in k:
            entry["w"] = k["w"]
        layout.append(entry)

    out = {"layouts": {"LAYOUT": {"layout": layout}}}
    out.update(rgb_matrix_section(footprints, keys_by_ref={k["ref"]: k for k in keys}, min_x=min_x, min_y=min_y))
    out_path = Path(__file__).resolve().parent / "layout.generated.json"
    out_path.write_text(json.dumps(out, indent=4) + "\n")
    print(f"wrote {out_path} ({len(layout)} keys)")

    # keyboard.json carries the same LAYOUT; keep it in step, plus the LED chain.
    # `features.rgb_matrix` is deliberately not set: RGB is off until a keymap
    # turns it on with RGB_MATRIX_ENABLE = yes.
    kb_path = Path(__file__).resolve().parent / "cornison" / "keyboard.json"
    kb = json.loads(kb_path.read_text())
    kb["layouts"] = out["layouts"]
    kb["ws2812"] = out["ws2812"]
    kb["rgb_matrix"] = out["rgb_matrix"]
    kb_path.write_text(json.dumps(kb, indent=4) + "\n")
    print(f"updated {kb_path}")

    # Grid for eyeballing against the PCB silkscreen.
    grid = {(k["matrix"][0], k["matrix"][1]): k["ref"] for k in keys}
    for row in range(8):
        print(" ".join(f"{grid[(row, col)]:>5}" for col in range(6)))


if __name__ == "__main__":
    main()
