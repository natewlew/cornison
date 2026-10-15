#!/usr/bin/env python3
"""Extract everything the case generator needs from the real PCB:
per-half outlines, switch poses, M2 hole centres, and the bounding boxes
of the MCU/OLED/reset/TRRS parts. Written as case/board.json.

Run with KiCad's bundled python3 (has pcbnew), from the repo root:
  ./build.sh extract
"""
import json
import math
import os
import pcbnew

CASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(CASE_DIR, "..", "pcb", "cornison.kicad_pcb")
OUT = os.path.join(CASE_DIR, "board.json")
MM = pcbnew.FromMM

TAB_CUT_HALF_W = 3.5   # mm, half-width of the cut rectangle across each tab
TAB_CUT_HALF_H = 0.6   # mm, half-height (perpendicular to the tab's long axis)


def poly_pts(shape_line_chain):
    return [
        (shape_line_chain.CPoint(k).x / 1e6, shape_line_chain.CPoint(k).y / 1e6)
        for k in range(shape_line_chain.PointCount())
    ]


def main():
    board = pcbnew.LoadBoard(PCB)
    fps = list(board.GetFootprints())

    # ---- 1. split the panel into its connected outline components by
    #         cutting across each breakaway-tab bridge ----
    ps = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(ps, False)
    cut = pcbnew.SHAPE_POLY_SET()
    for f in fps:
        if str(f.GetFPID().GetLibItemName()) == "Breakaway_Tabs":
            p = f.GetPosition()
            x, y = p.x / 1e6, p.y / 1e6
            chain = pcbnew.SHAPE_LINE_CHAIN()
            for (dx, dy) in [
                (-TAB_CUT_HALF_W, -TAB_CUT_HALF_H),
                (TAB_CUT_HALF_W, -TAB_CUT_HALF_H),
                (TAB_CUT_HALF_W, TAB_CUT_HALF_H),
                (-TAB_CUT_HALF_W, TAB_CUT_HALF_H),
            ]:
                chain.Append(MM(x + dx), MM(y + dy))
            chain.SetClosed(True)
            cut.AddOutline(chain)
    ps.BooleanSubtract(cut)

    comps = []
    for i in range(ps.OutlineCount()):
        o = ps.Outline(i)
        comps.append((i, abs(o.Area()) / 1e12, poly_pts(o)))
    comps.sort(key=lambda c: -c[1])
    big_two = comps[:2]
    if len(big_two) != 2:
        raise RuntimeError(f"expected 2 large outline components, got {len(comps)}")

    halves_outline = {}
    for idx, area, pts in big_two:
        mean_x = sum(p[0] for p in pts) / len(pts)
        side = "left" if mean_x < 148 else "right"
        halves_outline[side] = pts
        print(f"{side}: outline area {area:.0f} mm^2, {len(pts)} pts")

    if set(halves_outline.keys()) != {"left", "right"}:
        raise RuntimeError(f"expected left+right halves, got {list(halves_outline.keys())}")

    # ---- 2. switch poses per half ----
    keys_by_side = {"left": [], "right": []}
    for f in fps:
        n = str(f.GetFPID().GetLibItemName())
        if n.startswith("CherryMX_Hotswap"):
            p = f.GetPosition()
            x, y = p.x / 1e6, p.y / 1e6
            side = "left" if x < 148 else "right"
            keys_by_side[side].append(
                {
                    "ref": f.GetReference(),
                    "x": x,
                    "y": y,
                    "rot": f.GetOrientationDegrees(),
                    "is_1_5u": "1.5u" in n,
                }
            )

    # ---- 3. M2 mounting holes per half ----
    m2_by_side = {"left": [], "right": []}
    for f in fps:
        n = str(f.GetFPID().GetLibItemName())
        if n == "M2_HOLE_v2":
            # The hole is the footprint's pad, NOT its origin: one
            # footprint per half has its pad dragged ~10mm away from the
            # origin, and a case printed from origins put that boss 10mm
            # from the real hole. The drill size differs too (4.3mm on
            # five holes per half, 2.2mm on the two beside the TRRS jack).
            pads = list(f.Pads())
            assert len(pads) == 1, f"M2_HOLE_v2 at {f.GetPosition()} has {len(pads)} pads, expected 1"
            p = pads[0].GetPosition()
            x, y = p.x / 1e6, p.y / 1e6
            side = "left" if x < 148 else "right"
            m2_by_side[side].append({"x": x, "y": y, "drill": pads[0].GetDrillSize().x / 1e6})

    # ---- 4. MCU / OLED / reset / TRRS bounding boxes per half ----
    PART_TYPES = ("ProMicro_v3", "OLED_1side", "ResetSW_1side", "MJ-4PP-9_1side")
    parts_by_side = {"left": [], "right": []}
    for f in fps:
        n = str(f.GetFPID().GetLibItemName())
        if n in PART_TYPES:
            bb = f.GetBoundingBox(False)
            x0, y0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
            x1, y1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
            cx = (x0 + x1) / 2
            side = "left" if cx < 148 else "right"
            parts_by_side[side].append(
                {
                    "ref": f.GetReference(),
                    "type": n,
                    "bbox": [x0, y0, x1, y1],
                    "pos": [f.GetPosition().x / 1e6, f.GetPosition().y / 1e6],
                    "rot": f.GetOrientationDegrees(),
                    "pads": [
                        {
                            "num": pad.GetNumber(),
                            "pos": [pad.GetPosition().x / 1e6, pad.GetPosition().y / 1e6],
                            "size": [pad.GetSize().x / 1e6, pad.GetSize().y / 1e6],
                        }
                        for pad in f.Pads()
                    ],
                }
            )

    # ---- 5. underside keep-outs per half (everything that stands off the
    #         PCB's back face -- sockets, diodes, LEDs, through-hole pins --
    #         except the breakaway tabs and the M2 mounting holes, which
    #         the case generator already treats on its own) ----
    SKIP_TYPES = {"Breakaway_Tabs", "M2_HOLE_v2"}
    keepouts_by_side = {"left": [], "right": []}
    for f in fps:
        n = str(f.GetFPID().GetLibItemName())
        if n in SKIP_TYPES:
            continue
        bb = f.GetBoundingBox(False)
        x0, y0 = bb.GetLeft() / 1e6, bb.GetTop() / 1e6
        x1, y1 = bb.GetRight() / 1e6, bb.GetBottom() / 1e6
        cx = (x0 + x1) / 2
        side = "left" if cx < 148 else "right"
        keepouts_by_side[side].append(
            {"ref": f.GetReference(), "type": n, "bbox": [x0, y0, x1, y1]}
        )

    result = {
        "left": {
            "outline": halves_outline["left"],
            "keys": keys_by_side["left"],
            "m2_holes": m2_by_side["left"],
            "parts": parts_by_side["left"],
            "keepouts": keepouts_by_side["left"],
        },
        "right": {
            "outline": halves_outline["right"],
            "keys": keys_by_side["right"],
            "m2_holes": m2_by_side["right"],
            "parts": parts_by_side["right"],
            "keepouts": keepouts_by_side["right"],
        },
    }

    for side in ("left", "right"):
        d = result[side]
        print(
            f"{side}: {len(d['keys'])} keys, {len(d['m2_holes'])} M2 holes, "
            f"{len(d['parts'])} MCU/OLED/reset/TRRS parts"
        )
        for p in d["parts"]:
            print(f"   {p['ref']:6s} {p['type']:20s} bbox={p['bbox']}")

    json.dump(result, open(OUT, "w"), indent=2)
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
