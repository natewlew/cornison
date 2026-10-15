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
    out_path = Path(__file__).resolve().parent / "layout.generated.json"
    out_path.write_text(json.dumps(out, indent=4) + "\n")
    print(f"wrote {out_path} ({len(layout)} keys)")

    # Grid for eyeballing against the PCB silkscreen.
    grid = {(k["matrix"][0], k["matrix"][1]): k["ref"] for k in keys}
    for row in range(8):
        print(" ".join(f"{grid[(row, col)]:>5}" for col in range(6)))


if __name__ == "__main__":
    main()
