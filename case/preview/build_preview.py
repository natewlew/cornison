#!/usr/bin/env python3
"""Build the case preview artifact: embeds the generated STLs + key
layout as base64/JSON directly into a three.js HTML page."""
import base64
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CASE_DIR = os.path.join(HERE, "..")
OUT_DIR = os.path.join(CASE_DIR, "out")
BOARD_JSON = os.path.join(CASE_DIR, "board.json")

# must match case.py
FLOOR_T = 2.5
BOSS_H = 3.5
PCB_T = 1.6
PLATE_TOP_ABOVE_PCB = 5.0
POM_PLATE_T = 1.5
MAGSAFE_OD = 54.10                # Apple's published MagSafe ring spec
MAGSAFE_ID = 46.0
MAGSAFE_DEPTH = 2.0

PCB_Z_BASE = FLOOR_T + BOSS_H          # 6.0
PCB_TOP_Z = PCB_Z_BASE + PCB_T          # 7.6
WALL_TOP_Z = PCB_TOP_Z + PLATE_TOP_ABOVE_PCB  # 12.6
PLATE_Z_BASE = WALL_TOP_Z - POM_PLATE_T  # 11.1
KEYCAP_Z_BASE = WALL_TOP_Z               # 12.6, keycap bottom sits on plate top


def b64_stl(name):
    with open(os.path.join(OUT_DIR, name), "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def main():
    board = json.load(open(BOARD_JSON))

    stl = {
        "case_left": b64_stl("case-left.stl"),
        "case_right": b64_stl("case-right.stl"),
        "plate_left": b64_stl("plate-pom-left.stl"),
        "plate_right": b64_stl("plate-pom-right.stl"),
    }

    geom = {}
    for side in ("left", "right"):
        d = board[side]
        keys = [
            {"x": k["x"], "y": k["y"], "rot": k["rot"], "w": 27.0 if k["is_1_5u"] else 18.0}
            for k in d["keys"]
        ]
        xs = [p[0] for p in d["outline"]]
        ys = [p[1] for p in d["outline"]]
        key_xs = [k["x"] for k in keys]
        key_ys = [k["y"] for k in keys]
        magsafe_center = (sum(key_xs) / len(key_xs), sum(key_ys) / len(key_ys))
        geom[side] = {
            "keys": keys,
            "outline": d["outline"],
            "outline_bbox": [min(xs), min(ys), max(xs), max(ys)],
            "magsafe_center": magsafe_center,
        }

    z = {
        "pcb_z_base": PCB_Z_BASE,
        "pcb_top_z": PCB_TOP_Z,
        "wall_top_z": WALL_TOP_Z,
        "plate_z_base": PLATE_Z_BASE,
        "keycap_z_base": KEYCAP_Z_BASE,
        "pcb_t": PCB_T,
        "floor_t": FLOOR_T,
        "magsafe_od": MAGSAFE_OD,
        "magsafe_id": MAGSAFE_ID,
        "magsafe_depth": MAGSAFE_DEPTH,
    }

    template_path = os.path.join(HERE, "template.html")
    html = open(template_path).read()
    html = html.replace("__STL_JSON__", json.dumps(stl))
    html = html.replace("__GEOM_JSON__", json.dumps(geom))
    html = html.replace("__Z_JSON__", json.dumps(z))

    out_path = os.path.join(HERE, "case_preview.html")
    open(out_path, "w").write(html)
    print("wrote", out_path, "size", len(html))


if __name__ == "__main__":
    main()
