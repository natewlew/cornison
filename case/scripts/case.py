#!/usr/bin/env python3
"""Generate the cornison 3D-printed tray case + switch plates.

Reads board.json (produced by extract_board.py) and writes STEP/STL/DXF
into case/out/ for both halves:
  - case-{left,right}             the printed tray (screw the PCB to bosses)
  - plate-{pom,fr4ref,mjf}-{left,right}  switch-plate geometry (DXF + STEP + STL)
  - cover-{left,right}            printed cover over the Pro Micro/TRRS/reset
  - spacer-*, spacer-frame-*, tent-*  plate-mount spacers and tenting legs

The plate stops short of the MCU strip: the TRRS jack, reset switch and
Pro Micro all stand taller than the 3.4mm under the plate. A separate
printed cover sits over that strip instead, screwed down through the two
PCB mounting holes beside the TRRS jack, and the OLED module plugs into
its socket through a slot in the cover and rests on top of it.

Run from the repo root with:
  ./build.sh generate

All dimensions are parameters below.
"""
import json
import math
import os

import build123d as b3d

CASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD_JSON = os.path.join(CASE_DIR, "board.json")

OUT_DIR = os.path.join(CASE_DIR, "out")

# ----------------------------------------------------------------------
# Parameters (all mm unless noted)
# ----------------------------------------------------------------------
FLOOR_T = 2.5
BOSS_H = 4.0                 # clearance under PCB (hotswap sockets + LEDs);
                              # also McMaster 94459A767's own "Min Material
                              # Thickness" spec for its 3.2mm-long insert
PCB_T = 1.6
PLATE_TOP_ABOVE_PCB = 5.0     # Cherry MX: plate top sits 5mm above PCB top
FR4_PLATE_T = 1.6
POM_PLATE_T = 1.5
MJF_PLATE_T = 2.0   # JLC3DP PA12-HP/MJF nylon: 1.5mm is under their stated
                    # 2mm minimum feature thickness and gets rejected outright.
                    # Standard Cherry MX plate spec is 1.5mm +/-0.1mm; the
                    # switch clips have some engagement-depth tolerance
                    # beyond that but an unverified amount -- 2.0mm (JLC3DP's
                    # exact minimum) stays as close to spec as their process
                    # allows, rather than going further out to 2.5mm+

WALL_T = 2.5                  # radial wall thickness
CAVITY_CLEARANCE = 0.5        # gap between PCB/plate outline and cavity wall

OUTER_CORNER_ROUND = 3.0      # fillet radius used when rounding the outer case profile

BOSS_OD = 6.0
INSERT_BORE_D = 3.2           # McMaster 94459A767 (M2x0.4, 3.2mm installed
                               # length): "Drill Bit Size" / "For Maximum
                               # Hole Diameter" is 3.2mm -- a bigger hole
                               # gives the knurled insert nothing to bite into
INSERT_DEPTH = 3.2

KEY_HOLE = 14.0                # square switch cutout
SWITCH_FLANGE = 15.6            # standard Cherry MX top-housing footprint,
                                 # above the plate, under the keycap -- what
                                 # a plate-mount screw head has to clear
M2_CLEARANCE_D = 2.3

USB_NOTCH_W = 12.0
TRRS_NOTCH_W = 9.0
NOTCH_MARGIN_Z = 0.0            # notches start right at the floor top

# MCU cover: a printed part over the Pro Micro/TRRS/reset strip, standing
# on posts at the two PCB mounting holes beside the TRRS jack (the same
# two holes the stock Corne OLED cover uses). The OLED module plugs into a
# low-profile socket through a slot in the cover and rests on top of it.
#
# Part heights above the PCB's top face, measured from foostan's own 3D
# models in pcb/kbd (PJ320A.step, tact-switch.step, ProMicro.step with the
# footprints' model offsets applied) -- NOT yet from real parts. The Pro
# Micro figure is one on ordinary 2.5mm headers including its pin stubs;
# on Mill-Max low-profile sockets it sits no higher. Standard 8.5mm
# sockets put it at ~11mm and do not fit under this cover.
PART_HEIGHTS = {
    "MJ-4PP-9_1side": 5.0,
    "ResetSW_1side": 5.2,
    "ProMicro_v3": 5.5,
}
COVER_UNDERSIDE_ABOVE_PCB = 6.0   # 0.5 over the tallest part above
COVER_T = 2.0                      # JLC3DP's MJF minimum feature thickness
COVER_POST_OD = 6.0                # bears on the PCB around its 4.3mm mounting
                                    # hole, same ring a 6.0mm OD washer gives
COVER_SCREW_D = 2.4
COVER_POST_REACH = 6.0             # a mounting hole this close (in x) to the MCU
                                    # strip, and below the Pro Micro, carries a post
COVER_KEYCAP_CLEARANCE = 0.5
MCU_OPENING_MARGIN = 0.6           # plate opening = part bboxes grown by this
COVER_PLATE_LAP = 1.0              # where the cover is cut back for a keycap, the
                                    # plate reaches this far in under its edge
KEYCAP_1U = 18.1
KEYCAP_1_5U = 27.6
OLED_SLOT_MARGIN_X = 1.7        # beyond the end pins: half a 2.54mm pitch of header
                                 # plastic plus 0.43 clearance. The slot has to pass
                                 # the whole header, not just the pins
OLED_SLOT_MARGIN_Y = 1.5        # margin added beyond the pin row, each side
RESET_HOLE_D = 3.0              # the old plate's reset hole -- now only sizes the
                                 # cavity bulge in legacy_mcu_footprint
COVER_RESET_HOLE_D = 2.0        # paperclip access to the reset switch. Smaller than
                                 # the old plate's 3.0 so it clears the OLED slot
                                 # without the slot having to give way
COVER_MIN_WALL = 1.0            # JLC3DP's MJF minimum wall
FAB_MIN_WALL = 2.2   # target minimum plate wall/connect width -- JLCPCB's FR4
                      # routing ask is >=2.0mm; this gives a bit of margin
PLATE_HOLE_MIN_WALL = 1.5   # a PCB mounting hole still gets its plate hole
                            # with a wall thinner than FAB_MIN_WALL, down to
                            # this -- one hole per half sits 1.62mm from a
                            # switch cutout, and a standoff there was wanted
                            # more than the margin. Over JLC3DP's 1.0mm MJF
                            # minimum; under JLCPCB's 2.0mm FR4 ask, so an
                            # FR4 order may get that wall queried

# Plate mount: at every plate-mount M2 hole, a printed spacer stands
# between the PCB and the plate, and one longer screw runs plate -> spacer
# -> PCB into the same heat-set insert -- same idea as the stock Corne's
# sandwich mount. Pins the plate down instead of leaving it held only by
# the switches' own socket grip.
SPACER_OD = 5.6             # clear of neighboring 14mm switch bodies at the
                            # tightest (4-key-junction) holes, with a real
                            # bearing ring left over the PCB's 4.3mm hole
SPACER_OD_NARROW = 5.0      # for a hole whose neighbors are too close for
                            # SPACER_OD: still 0.35mm of bearing ring on
                            # the PCB's 4.3mm hole
SPACER_BORE_D = 2.4         # clears an M2 screw shank, same as COVER_SCREW_D
SPACER_FRAME_OPENING = 15.6 # spacer frame: one piece per half in place of the
                            # loose spacers, shaped like the plate, sitting
                            # between PCB and plate. Each switch gets an
                            # opening this size -- the switch's 15.6mm top
                            # housing, so the clips that snap out under the
                            # plate have room -- leaving ~3.45mm ribs at the
                            # 19.05mm key pitch
SPACER_PILOT_D = 4.1        # drops into the PCB's 4.3mm hole so the spacer
                            # can't wander sideways once the plate goes on
SPACER_PILOT_H = 1.2
SPACER_SHORT = 0.1          # spacer stands this much short of the full PCB-
                            # to-plate gap, so the switches (not the spacer)
                            # are what actually seats the plate's height
PLATE_SCREW_LEN = 10.0      # M2x10: boss top (6.5) + PCB (1.6) + spacer up to
                            # plate top (13.1) = 8.0mm of stack, leaving the
                            # insert (3.2mm deep, bottom at 3.3) with >3mm of
                            # thread engagement
PLATE_SCREW_HEAD_D = 4.0    # low-head M2 screw; checked against every
                            # neighboring switch's 15.6mm top housing below

RESET_REINFORCE_MARGIN = 2.3    # min plate material kept around the reset hole --
                                 # see the comment at its cut, below. Needs to be
                                 # bigger than the naturally-close true outline
                                 # there (only ~1.5mm away) to actually push the
                                 # local edge outward, not just match it
PLATE_REINFORCE_MARGIN = 3.0    # min plate material kept around every switch hole,
                                 # even where the raw outline would clip it -- 1.2 left
                                 # one thumb-cluster corner just under JLC3DP's 1.0mm
                                 # MJF minimum wall ask; 1.6 cleared that but left several
                                 # switch holes at ~1.3-1.8mm from the plate edge, under
                                 # JLCPCB's stricter 2.0mm ask for FR4 routing
                                 # "connect"/tab width (they flagged it by email; measured
                                 # directly via true closed-loop geometric distance, not
                                 # just the area-ratio clearance check below). This value
                                 # measures out to ~2.4mm minimum on both halves

STL_TOLERANCE = 0.05       # mm, chordal deviation for STL export (0.001 default is overkill)
STL_ANGULAR_TOLERANCE = 0.25

# The outer/lower PCB mounting hole moves down one row in the next PCB
# revision (see TODO.md). Until then the case, plate and spacer frame carry
# both spots, so either PCB fits; whichever spot has no hole in the PCB just
# props the PCB up. Each spot is named by the four keys whose corners meet
# at it, so it follows the real key positions.
EITHER_OR_HOLES = {
    "left": [("SW7", "SW8", "SW13", "SW14"), ("SW13", "SW14", "SW43", "SW44")],
    "right": [("SW28", "SW29", "SW34", "SW35"), ("SW34", "SW35", "SW46", "SW47")],
}
EITHER_OR_DRILL = 4.3              # the M2_HOLE_v2 footprint's hole

FOOT_D = 8.0                       # footprint a mounting point needs clearance
                                    # for -- a rubber foot or a tent leg's boss,
                                    # whichever ends up over it. Only governs
                                    # placement/wall-clearance now; the case cut
                                    # itself is just a small screw hole (below)
FOOT_WALL_CLEARANCE = 1.5         # min wall thickness kept around every foot position

# Tenting legs: an optional printed part per half, bolted on at the same
# 4 foot positions in place of rubber feet, tilting the half so its inner
# edge (toward the gap between halves) sits higher than its outer edge --
# a peaked-roof tent, not a magnetic one. Each leg carries its own M2
# insert at the top (not the case), since a single screw can't span the
# full range of leg heights a tilt produces across a ~130mm foot span --
# the case side only needs a plain screw-clearance hole, the same length
# screw at every corner regardless of that corner's leg height.
TENT_ANGLE_DEG = float(os.environ.get("TENT_ANGLE_DEG", "18"))
TENT_SCREW_CLEARANCE_D = 2.3       # M2 shank clearance through the case floor,
                                    # same as M2_CLEARANCE_D
TENT_MIN_T = 5.0                   # tent thickness at the case's low (outer)
                                    # edge, where the desk plane comes closest
                                    # to the case -- thicker than the frame, so
                                    # the desk plane never cuts into it
TENT_SCREW_LEN = 6.0               # M2x6: FLOOR_T (2.5) + a few mm into the
                                    # insert, same at every corner regardless
                                    # of that corner's own leg height
TENT_FOOT_D = 20.0                 # leg diameter, clipped flush to the case's
                                    # own outline where it would overhang it
TENT_FRAME_W = 10.0                # width of the beams tying the 4 legs together
TENT_FRAME_T = 4.0                 # their thickness, hanging off the flat
                                    # mounting face; they never reach the desk
TENT_BORE_EXTRA = 1.0              # insert bore runs this much past the insert,
                                    # room for the screw tip
TENT_RUBBER_D = 10.0               # the round rubber feet that go on the leg
TENT_RUBBER_H = 2.0                # ends: 10mm across, 2mm tall
TENT_RUBBER_CLEAR = 0.4            # recess is this much wider than the foot
TENT_RUBBER_RECESS = 0.8           # and this deep, so the foot stands 1.2mm proud
TENT_RUBBER_SHIFT = 2.0            # recess centre, moved this far from the
                                    # leg's centre toward the middle of the
                                    # tent: the leg is trimmed to the case
                                    # outline 6mm from its centre, and a
                                    # centred recess would leave a 0.8mm rim

# Floor mat: butyl sound-deadening sheet (Dynamat Xtreme class, foil on
# top) stuck to the case floor under the PCB. Only a cutting template is
# generated -- the mat itself is bought sheet. The gap it goes in is
# BOSS_H minus the hotswap sockets on the PCB's underside (~1.8mm).
MAT_T = 1.7                        # Dynamat Xtreme 67mil; 80mil (2mm) mats
                                    # leave no room under the sockets
MAT_EDGE_CLEARANCE = 0.5           # mat edge in from the cavity wall
MAT_BOSS_HOLE_D = BOSS_OD + 1.0    # punch size round each boss
MAT_SCREW_HOLE_D = 5.0             # round each tent screw's head (M2 low head
                                    # ~4mm), which sits on the floor
MAT_PIN_MARGIN = 1.5               # mat kept this far off the through-hole
                                    # parts' footprints: their pins poke out
                                    # under the PCB, right over the foil
MAT_MIN_WIDTH = 2.0                # strips narrower than this are dropped
MAT_TEMPLATE_T = 0.6               # printed tracing template thickness
MAT_DENSITY = 2.2                  # kg/m^2, Dynamat Xtreme's published
                                    # 0.45 lb/ft^2 -- only for the printout

Z_TOL = 1e-6


def load_board():
    """board.json holds raw KiCad coordinates (Y points down). All geometry
    here is built in those same numbers, so KiCad's footprint angles (CCW
    as seen on its Y-down screen) are a clockwise rotation in the raw
    numbers -- negated once here, so the model is an exact copy of the
    board in KiCad's frame. 3D exports are mirrored back into a real Y-up
    frame by to_physical(); the DXF stays in KiCad's frame."""
    board = json.load(open(BOARD_JSON))
    for side in board.values():
        for k in side["keys"]:
            k["rot"] = -k["rot"]
    # mount_holes: the PCB's own holes, plus the either/or spots (see
    # EITHER_OR_HOLES) whether or not this PCB has a hole there. The case,
    # plate and spacers use these; the walls still follow m2_holes only.
    for name, side in board.items():
        keys = {k["ref"]: k for k in side["keys"]}
        holes = [dict(h, on_pcb=True, either_or=False) for h in side["m2_holes"]]
        for refs in EITHER_OR_HOLES[name]:
            x = sum(keys[r]["x"] for r in refs) / 4
            y = sum(keys[r]["y"] for r in refs) / 4
            match = [h for h in holes if math.hypot(h["x"] - x, h["y"] - y) < 0.5]
            if match:
                match[0]["either_or"] = True
            else:
                holes.append({"x": x, "y": y, "drill": EITHER_OR_DRILL, "on_pcb": False, "either_or": True})
        assert sum(h["either_or"] for h in holes) == 2, f"{name}: expected 2 either/or mounting spots"
        side["mount_holes"] = holes
    return board


def to_physical(shape):
    """KiCad frame -> real-world Y-up frame (what a slicer/printer sees).
    Without this every printed part comes out as the mirror image of the
    board, so the PCB only fits in the case switch-side down."""
    return b3d.mirror(shape, about=b3d.Plane.XZ)


def plate_footprint(plate_sk):
    """The plate's outer outline with its holes filled in."""
    faces = [b3d.Face(f.outer_wire()) for f in plate_sk.faces()]
    sk = faces[0]
    for f in faces[1:]:
        sk = sk + f
    return sk


def poly(pts):
    # b3d.Polygon silently produces a degenerate (zero-area) face if given
    # a list of [x, y] lists instead of (x, y) tuples -- always coerce.
    return b3d.Polygon(*[tuple(p) for p in pts])


def hull_sketch(points):
    """Convex hull of 2D points as a Sketch (monotone chain)."""
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in points))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return poly(lower[:-1] + upper[:-1])


def offset_pts(pts, amount):
    """Grow (amount>0) or shrink (amount<0) a closed polygon by `amount`,
    with rounded corners, returning a Sketch."""
    sk = poly(pts)
    if amount == 0:
        return sk
    return b3d.offset(sk, amount=amount, kind=b3d.Kind.ARC)


def open_sketch(sk, radius):
    """Morphological opening: shrink by `radius` then grow back by the same
    amount. Any solid feature narrower than 2*radius gets eroded away
    entirely and doesn't return on the regrow -- used to clip off narrow
    necks in the outline (leftover panelization-tab notches in the real
    board outline) rather than widen them by hand."""
    return b3d.offset(
        b3d.offset(sk, amount=-radius, kind=b3d.Kind.ARC), amount=radius, kind=b3d.Kind.ARC
    )


def rounded_outer_sketch(pts_or_sketch, grow):
    """Outer case footprint: some base shape (point list, or an existing
    Sketch such as a reinforced cavity) grown by `grow`, with rounded
    corners on the outside. The real outline has lots of small concave
    notches (tab bridges, thumb-cluster relief) where a uniform fillet
    radius doesn't fit -- fall back to a smaller radius, then to no
    fillet at all, rather than aborting the whole build."""
    base = poly(pts_or_sketch) if isinstance(pts_or_sketch, list) else pts_or_sketch
    sk = b3d.offset(base, amount=grow, kind=b3d.Kind.ARC) if grow else base
    for radius in (OUTER_CORNER_ROUND, 1.0, 0.4):
        try:
            return b3d.fillet(sk.vertices(), radius=radius)
        except ValueError as e:
            print(f"  (outer fillet r={radius} failed: {e}; trying smaller)")
    print("  (skipping outer corner fillet -- sharp corners)")
    return sk


def bbox_union(bboxes, margin=0.0):
    x0 = min(b[0] for b in bboxes) - margin
    y0 = min(b[1] for b in bboxes) - margin
    x1 = max(b[2] for b in bboxes) + margin
    y1 = max(b[3] for b in bboxes) + margin
    return (x0, y0, x1, y1)


def bbox_center(bb):
    return ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)


def bbox_size(bb):
    return (bb[2] - bb[0], bb[3] - bb[1])


def outline_bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def key_reinforcement_sketch(keys, m2_holes):
    """Union of a slightly-enlarged footprint around every switch hole and
    M2 clearance hole. Some corners (the outermost, most-rotated thumb key;
    one mounting hole per side near the thumb cluster) sit close enough to
    the raw outline that a hole there would break out through the plate's
    edge -- this shape gets unioned into BOTH the plate and the case's own
    cavity, so the wall bulges out to match wherever the plate needed extra
    material, and the two never collide."""
    shapes = None
    for k in keys:
        # the plate cutout is always the switch's own 14x14 square,
        # regardless of keycap size (1.5u only widens the keycap, not the
        # switch body) -- confirmed against the stock corne SW_Hole
        # footprint, which uses the same plain 14x14 square everywhere
        rw = rh = KEY_HOLE + 2 * PLATE_REINFORCE_MARGIN
        rect = b3d.Pos(k["x"], k["y"], 0) * b3d.Rot(0, 0, k["rot"]) * b3d.Rectangle(rw, rh)
        # round its corners so wherever this actually adds material to the
        # plate, it reads as a deliberate local extension of the outline
        # rather than a sharp rectangular tab glued on
        rect = b3d.fillet(rect.vertices(), radius=PLATE_REINFORCE_MARGIN * 1.5)
        shapes = rect if shapes is None else shapes + rect
    for h in m2_holes:
        circ = b3d.Pos(h["x"], h["y"], 0) * b3d.Circle(M2_CLEARANCE_D / 2 + PLATE_REINFORCE_MARGIN)
        shapes = circ if shapes is None else shapes + circ
    return shapes


def reinforced_cavity(outline, keys, m2_holes):
    """The case cavity / plate footprint, widened around every switch hole
    and M2 hole per key_reinforcement_sketch -- the single shared shape
    both build_case and build_plate_sketch cut/fill against, so they
    always agree."""
    base = offset_pts(outline, CAVITY_CLEARANCE)
    return base + key_reinforcement_sketch(keys, m2_holes)


def part_by_type(parts, type_name):
    matches = [p for p in parts if p["type"] == type_name]
    if not matches:
        raise KeyError(type_name)
    return matches[0]


def overlap(a, b, attr="area"):
    """Area (or volume) shared by two shapes. An empty intersection comes
    back from build123d as None, not as a zero-size shape."""
    common = a & b
    return 0.0 if common is None else getattr(common, attr)


def rect_from_bb(bb):
    cx, cy = bbox_center(bb)
    w, h = bbox_size(bb)
    return b3d.Pos(cx, cy, 0) * b3d.Rectangle(w, h)


def legacy_mcu_footprint(data):
    """The footprint the plate used to have over the MCU strip, back when
    it covered it: a filled rectangle around the Pro Micro/OLED/reset
    parts, a reinforcement patch around the reset hole (which sits only
    ~1.5mm from the true board edge) and one around every mounting hole.
    The plate is cut away there
    now, but board_envelope still includes this shape, so the walls round
    the MCU strip never come in closer than they were."""
    parts = data["parts"]
    bb = bbox_union(
        [part_by_type(parts, t)["bbox"] for t in ("ProMicro_v3", "OLED_1side", "ResetSW_1side")], margin=3.5
    )
    fill = rect_from_bb(bb) & reinforced_cavity(data["outline"], data["keys"], data["m2_holes"])
    rx, ry = part_by_type(parts, "ResetSW_1side")["pos"]
    legacy = fill + b3d.Pos(rx, ry, 0) * b3d.Circle(RESET_HOLE_D / 2 + RESET_REINFORCE_MARGIN)
    # ...and the mounting-hole patches the opening now removes from the plate
    for h in data["m2_holes"]:
        legacy = legacy + b3d.Pos(h["x"], h["y"], 0) * b3d.Circle(M2_CLEARANCE_D / 2 + PLATE_REINFORCE_MARGIN)
    return legacy


def board_envelope(side, data):
    """The plate's outer edge, and grown by CAVITY_CLEARANCE the case
    cavity's: straight along the pinky side, the MCU side and the bottom,
    straight across each column's top (so the top still steps with the
    column stagger), and a convex hull round the angled thumb keys. It
    holds everything the case used to trace -- the PCB outline, every
    switch's reinforcement patch, the old MCU-strip footprint -- so nothing
    loses clearance; only the scallops and notches between them fill in."""
    keys = data["keys"]
    left = side == "left"
    traced = poly(data["outline"]) + key_reinforcement_sketch(keys, data["m2_holes"]) + legacy_mcu_footprint(data)

    def bb_of(sk):
        b = sk.bounding_box()
        return (b.min.X, b.min.Y, b.max.X, b.max.Y)

    def strip(xa, xb):
        return bb_of(traced & rect_from_bb((xa, y0 - 1, xb, y1 + 1)))

    x0, y0, x1, y1 = bb_of(traced)
    half = KEY_HOLE / 2 + PLATE_REINFORCE_MARGIN
    corners = []
    for k in keys:
        if abs(k["rot"]) < 1e-6:
            continue
        a = math.radians(k["rot"])
        for dx, dy in ((-half, -half), (half, -half), (half, half), (-half, half)):
            corners.append((k["x"] + dx * math.cos(a) - dy * math.sin(a), k["y"] + dx * math.sin(a) + dy * math.cos(a)))
    # where the thumb cluster starts, coming in from the pinky side, and
    # the one straight bottom edge up to there
    tx = min(c[0] for c in corners) if left else max(c[0] for c in corners)
    bot = strip(x0, tx)[3] if left else strip(tx, x1)[3]

    # columns: each straight across at its own top, down to `bot` -- or,
    # past where the thumb cluster starts, to its own lowest switch. Only
    # real columns count: a lone key between two of them (the left half's
    # bottom-row thumb key) would otherwise carry its taller neighbour's
    # top out over the next column.
    straight = [k for k in keys if abs(k["rot"]) < 1e-6]
    by_x = {}
    for k in straight:
        by_x.setdefault(round(k["x"], 1), []).append(k)
    cols = sorted(x for x, ks in by_x.items() if len(ks) > 1)
    pcb = poly(data["outline"])
    tops = []
    for i, c in enumerate(cols):
        lo = (cols[i - 1] + c) / 2 if i else c - half
        hi = (c + cols[i + 1]) / 2 if i + 1 < len(cols) else c + half
        pcb_top = bb_of(pcb & rect_from_bb((lo + 0.6, y0 - 1, hi - 0.6, y1 + 1)))[1]
        tops.append(min(min(k["y"] for k in by_x[c]) - half, pcb_top))
    # Each step sits midway between two columns, or as far over as the
    # PCB's own corner reaches. A switch's reinforcement patch is 1mm wider
    # than the column pitch, so the taller column's patch pokes 0.5mm past
    # the midpoint; it's trimmed back to the step below (still 2.5mm of
    # plate beside that switch hole).
    pcb_pts = [tuple(p) for p in data["outline"]]
    steps = []
    for (a, ta), (b, tb) in zip(zip(cols, tops), zip(cols[1:], tops[1:])):
        m = (a + b) / 2
        if ta < tb:
            m = max([m] + [x for x, y in pcb_pts if a < x < b and y < tb - 1e-6])
        elif tb < ta:
            m = min([m] + [x for x, y in pcb_pts if a < x < b and y < ta - 1e-6])
        steps.append(m)
    kx0, kx1 = cols[0] - half, cols[-1] + half
    edges = [x0 if left else kx0] + steps + [kx1 if left else x1]
    sky = None
    for xa, xb, top in zip(edges, edges[1:], tops):
        r = rect_from_bb((xa, y0 - 10, xb, top))
        sky = r if sky is None else sky + r
    env = (traced - sky) + rect_from_bb((x0, bot - 4, tx, bot) if left else (tx, bot - 4, x1, bot))
    for xa, xb, c, top in zip(edges, edges[1:], cols, tops):
        past_thumb = xb > tx if left else xa < tx
        low = max(k["y"] for k in by_x[c]) + half if past_thumb else bot
        env = env + rect_from_bb((xa, top, xb, low))
    # the MCU strip: straight down its outer edge to where the board turns
    # in toward the thumb cluster
    ma, mb = (kx1, x1) if left else (x0, kx0)
    edge_x = x1 if left else x0
    mcu_bot = strip(edge_x - 1, edge_x + 1)[3]
    env = env + rect_from_bb((ma, strip(ma, mb)[1], mb, mcu_bot))
    # the PCB's own corners round the thumb keys too: its tip reaches past
    # the switch patches
    thumb_top = min(c[1] for c in corners)
    pcb_pts = [tuple(p) for p in data["outline"] if (p[0] > tx if left else p[0] < tx) and p[1] > thumb_top]
    env = env + hull_sketch(corners + pcb_pts + [(tx, bot), (edge_x, mcu_bot)])

    faces = env.faces()
    assert len(faces) == 1, f"{side}: board envelope came out as {len(faces)} pieces"
    return plate_footprint(env)   # fills any pocket the pieces close off


def keycap_sketch(keys, grow):
    """Union of every keycap's footprint, grown by `grow`. Which way the
    1.5u cap's long side runs relative to its footprint isn't recorded in
    board.json, so both orientations are unioned -- conservative."""
    shapes = None
    for k in keys:
        long_side = KEYCAP_1_5U if k["is_1_5u"] else KEYCAP_1U
        for (w, h) in {(long_side, KEYCAP_1U), (KEYCAP_1U, long_side)}:
            cap = b3d.Pos(k["x"], k["y"], 0) * b3d.Rot(0, 0, k["rot"]) * b3d.Rectangle(
                w + 2 * grow, h + 2 * grow
            )
            shapes = cap if shapes is None else shapes + cap
    return shapes


MCU_ZONE_PARTS = ("ProMicro_v3", "OLED_1side", "ResetSW_1side", "MJ-4PP-9_1side")


def mcu_zone(side, data):
    """The strip of board holding the Pro Micro, OLED socket, reset switch
    and TRRS jack, as a bbox run out past the board's top and inner edges,
    plus the PCB mounting holes that carry the cover's posts."""
    parts = data["parts"]
    x0, y0, x1, y1 = bbox_union([part_by_type(parts, t)["bbox"] for t in MCU_ZONE_PARTS], margin=MCU_OPENING_MARGIN)
    mcu_bb = part_by_type(parts, "ProMicro_v3")["bbox"]
    post_holes = [
        h for h in data["m2_holes"]
        if mcu_bb[0] - COVER_POST_REACH < h["x"] < mcu_bb[2] + COVER_POST_REACH and h["y"] > mcu_bb[3]
    ]
    assert post_holes, f"{side}: no PCB mounting hole near the MCU strip to carry the cover"
    # far enough to swallow the whole reinforcement patch the plate carries
    # around each mounting hole, so no crescent of it is left on the
    # opening's edge
    reach = M2_CLEARANCE_D / 2 + PLATE_REINFORCE_MARGIN + 0.1
    for h in post_holes:
        x0, x1 = min(x0, h["x"] - reach), max(x1, h["x"] + reach)
        y1 = max(y1, h["y"] + reach)
    ob = outline_bbox(data["outline"])
    y0 = ob[1] - 5.0
    if side == "left":
        x1 = ob[2] + 5.0
    else:
        x0 = ob[0] - 5.0
    return (x0, y0, x1, y1), post_holes


def plate_mount_holes(side, data, plate_sk):
    """M2 holes where the plate can be screwed down with a spacer, not just
    rest on the switches: the plate actually has a clearance hole there
    (some don't -- too close to a neighboring switch hole), and it isn't a
    cover post (those sit in the MCU opening, where there's no plate)."""
    _, post_holes = mcu_zone(side, data)
    post_xy = {(h["x"], h["y"]) for h in post_holes}
    holes = []
    for h in data["mount_holes"]:
        if (h["x"], h["y"]) in post_xy:
            continue
        probe = b3d.Pos(h["x"], h["y"], 0) * b3d.Circle(0.3)
        if overlap(plate_sk, probe) < 0.01:
            holes.append(h)
    assert len(holes) >= 3, f"{side}: only {len(holes)} plate-mount holes found, expected several"
    return holes


def build_spacer(plate_t, od=None):
    """PCB-to-plate spacer for one plate-mount hole: a pilot nub that drops
    into the PCB's 4.3mm hole (keeps it from sliding sideways once the
    plate goes on top), a barrel standing up to just under the plate's
    underside, and a through-bore for the screw shank."""
    od = SPACER_OD if od is None else od
    height = PLATE_TOP_ABOVE_PCB - plate_t - SPACER_SHORT
    assert height > SPACER_PILOT_H, f"spacer height {height:.2f}mm is too short for its own {SPACER_PILOT_H}mm pilot"
    body = b3d.Cylinder(
        radius=od / 2, height=height,
        align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
    )
    pilot = b3d.Pos(0, 0, -SPACER_PILOT_H) * b3d.Cylinder(
        radius=SPACER_PILOT_D / 2, height=SPACER_PILOT_H,
        align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
    )
    bore = b3d.Cylinder(
        radius=SPACER_BORE_D / 2, height=height + SPACER_PILOT_H + 0.2,
        align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
    )
    spacer = (body + pilot) - b3d.Pos(0, 0, -SPACER_PILOT_H - 0.1) * bore
    assert spacer.is_valid, "spacer solid is not valid"
    return spacer


def build_spacer_frame(side, plate_sk, keys, mount_plan, plate_t):
    """All of a half's plate spacers as one printed part: the plate's own
    outline, with an opening round every switch, standing between the PCB
    and the plate. The posts at the plate-mount holes keep the size each
    loose spacer had (report_plate_mount picked standard or narrow per
    hole) and the same pilot into the PCB hole. Built with z=0 at the PCB's
    top face, like build_spacer."""
    height = PLATE_TOP_ABOVE_PCB - plate_t - SPACER_SHORT

    openings = None
    for k in keys:
        sq = b3d.Pos(k["x"], k["y"], 0) * b3d.Rot(0, 0, k["rot"]) * b3d.Rectangle(SPACER_FRAME_OPENING, SPACER_FRAME_OPENING)
        openings = sq if openings is None else openings + sq
    web = open_sketch(plate_footprint(plate_sk) - openings, 0.6)   # drop anything under 1.2mm wide

    posts = []
    for h, kind in mount_plan:
        od = SPACER_OD if kind == "standard" else SPACER_OD_NARROW
        posts.append((h["x"], h["y"], od, not h["either_or"]))
        web = web + b3d.Pos(h["x"], h["y"], 0) * b3d.Circle(od / 2)
    faces = web.faces()
    fused = faces[0]
    for f in faces[1:]:
        fused = fused + f
    pieces = fused.faces()
    main = max(pieces, key=lambda f: f.area)
    for (x, y, od, pilot) in posts:
        assert overlap(main, b3d.Pos(x, y, 0) * b3d.Circle(0.5)) > 0.7, (
            f"{side}: spacer frame post at ({x:.1f},{y:.1f}) isn't joined to the rest of the frame"
        )

    # No pilot at the either/or spots: on a PCB without a hole there, a
    # pilot would land on solid board and hold the frame off it.
    frame = extrude_up(main, 0.0, height)
    for (x, y, od, pilot) in posts:
        if pilot:
            frame = frame + b3d.Pos(x, y, -SPACER_PILOT_H) * b3d.Cylinder(
                radius=SPACER_PILOT_D / 2, height=SPACER_PILOT_H, align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN)
            )
        frame = frame - b3d.Pos(x, y, -SPACER_PILOT_H - 0.1) * b3d.Cylinder(
            radius=SPACER_BORE_D / 2, height=height + SPACER_PILOT_H + 0.2,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )

    # ---- verification ----
    assert frame.is_valid, f"{side}: spacer frame is not valid"
    assert len(frame.solids()) == 1, f"{side}: spacer frame came out as {len(frame.solids())} pieces"
    bodies = None
    for k in keys:
        sq = b3d.Pos(k["x"], k["y"], 0) * b3d.Rot(0, 0, k["rot"]) * b3d.Rectangle(KEY_HOLE + 0.4, KEY_HOLE + 0.4)
        bodies = sq if bodies is None else bodies + sq
    hit = overlap(main, bodies)
    assert hit < 0.01, f"{side}: spacer frame reaches within 0.2mm of a switch body ({hit:.2f}mm^2)"
    stray = sum(f.area for f in pieces if f is not main)
    return frame, {"height": height, "posts": len(posts), "pilots": sum(p[3] for p in posts), "area": main.area, "dropped": stray}


def report_plate_mount(side, keys, mount_holes, metrics):
    """Check every plate-mount spacer/screw against the real switch
    geometry, in XY: a spacer wide enough to bear on the plate still has to
    clear its neighbors' 14mm switch bodies (below the plate) and a screw
    head has to clear their 15.6mm top housings (above the plate) -- both
    checked by growing the real switch footprints by the required
    clearance and testing the hole centre against that, not the other way
    around (a probe-vs-safe-zone test misses a feature sitting almost
    exactly tangent, same lesson as assert_clear_of_wall above).
    Also prints where a screw head ends up under a keycap -- not unsafe by
    itself (the keycap's skirt may still clear a low-head screw), but
    worth knowing, and the z-depth the screw reaches into its insert."""
    body_sk = None
    flange_sk = None
    for k in keys:
        b = b3d.Pos(k["x"], k["y"], 0) * b3d.Rot(0, 0, k["rot"]) * b3d.Rectangle(KEY_HOLE, KEY_HOLE)
        f = b3d.Pos(k["x"], k["y"], 0) * b3d.Rot(0, 0, k["rot"]) * b3d.Rectangle(SWITCH_FLANGE, SWITCH_FLANGE)
        body_sk = b if body_sk is None else body_sk + b
        flange_sk = f if flange_sk is None else flange_sk + f
    grown_body = b3d.offset(body_sk, amount=0.5, kind=b3d.Kind.ARC)
    grown_flange = b3d.offset(flange_sk, amount=0.3, kind=b3d.Kind.ARC)
    keycaps = keycap_sketch(keys, 0)

    boss_top_z = metrics["boss_top_z"]
    wall_top_z = metrics["wall_top_z"]
    insert_bottom_z = boss_top_z - INSERT_DEPTH
    tip_z = wall_top_z - PLATE_SCREW_LEN
    engagement = max(0.0, boss_top_z - max(tip_z, insert_bottom_z))
    assert tip_z > FLOOR_T + 0.5, (
        f"{side}: M2x{PLATE_SCREW_LEN:.0f} plate-mount screw tip at z={tip_z:.2f} is too close to "
        f"the case's true bottom (floor top at {FLOOR_T})"
    )

    def gap_to_squares(px, py, size):
        """True distance from a point to the nearest key's square of this
        size (0 if inside one), each square turned to its key's rotation."""
        best = None
        for k in keys:
            a = math.radians(-k["rot"])
            dx, dy = px - k["x"], py - k["y"]
            lx = dx * math.cos(a) - dy * math.sin(a)
            ly = dx * math.sin(a) + dy * math.cos(a)
            g = math.hypot(max(abs(lx) - size / 2, 0.0), max(abs(ly) - size / 2, 0.0))
            best = g if best is None else min(best, g)
        return best

    plan = []
    for h in mount_holes:
        x, y = h["x"], h["y"]
        body_gap = gap_to_squares(x, y, KEY_HOLE)
        flange_gap = gap_to_squares(x, y, SWITCH_FLANGE)

        # spacer: the standard one where it clears the switch bodies by
        # 0.5mm, the narrow one where it doesn't
        if body_gap - SPACER_OD / 2 >= 0.5:
            od, kind = SPACER_OD, "standard"
            assert overlap(grown_body, b3d.Pos(x, y, 0) * b3d.Circle(od / 2)) < 1e-3, (
                f"{side}: spacer at ({x:.1f},{y:.1f}) comes within 0.5mm of a switch body"
            )
        else:
            od, kind = SPACER_OD_NARROW, "narrow"
            assert body_gap - od / 2 >= 0.2, (
                f"{side}: even the narrow spacer at ({x:.1f},{y:.1f}) is only {body_gap - od / 2:.2f}mm "
                f"from a switch body"
            )
        ring = (od - h["drill"]) / 2
        assert ring >= 0.3, f"{side}: {kind} spacer at ({x:.1f},{y:.1f}) has only {ring:.2f}mm to bear on round the PCB hole"

        # screw head: must sit wholly on plate, and should clear the switch
        # top housings. Where it can't clear them it is reported, not hidden
        head_r = PLATE_SCREW_HEAD_D / 2
        assert body_gap - head_r >= 0.5, f"{side}: screw head at ({x:.1f},{y:.1f}) overhangs a switch cutout"
        head_clear = flange_gap - head_r
        note = f"{kind} spacer ({od}mm, {body_gap - od / 2:.2f}mm from the nearest switch body)"
        if head_clear < 0.3:
            note += (f"; TIGHT: a {PLATE_SCREW_HEAD_D}mm screw head comes {head_clear:+.2f}mm from a switch's "
                     f"{SWITCH_FLANGE}mm top housing (negative = overlaps its footprint) -- check on a real "
                     f"plate, use the smallest head you have")
        if overlap(keycaps, b3d.Pos(x, y, 0) * b3d.Circle(head_r)) > 1e-3:
            note += "; under a keycap"
        if h["either_or"]:
            note += "; EITHER/OR spot -- " + ("this PCB's hole" if h["on_pcb"] else "for the next PCB revision, no hole in this PCB")
        print(f"  plate-mount hole ({x:6.1f},{y:5.1f}): {note}")
        plan.append((h, kind))
    print(f"  plate-mount screw M2x{PLATE_SCREW_LEN:.0f}: {engagement:.1f}mm engagement in the "
          f"{INSERT_DEPTH}mm insert, tip at z={tip_z:.2f}")
    return plan


# ----------------------------------------------------------------------
# Case tray
# ----------------------------------------------------------------------
def build_case(side, data, plate_sk):
    outline = data["outline"]
    parts = data["parts"]
    ob = outline_bbox(outline)
    is_left = side == "left"

    wall_top_z = FLOOR_T + BOSS_H + PCB_T + PLATE_TOP_ABOVE_PCB  # flush with plate top
    boss_top_z = FLOOR_T + BOSS_H
    pcb_top_z = FLOOR_T + BOSS_H + PCB_T

    # The plate's own envelope, grown: it already holds the PCB outline and
    # everything the cavity used to wrap separately, so the two can't drift
    # apart.
    cavity_sk = b3d.offset(board_envelope(side, data), amount=CAVITY_CLEARANCE, kind=b3d.Kind.ARC)
    for label, must_fit in (("PCB", offset_pts(outline, CAVITY_CLEARANCE)), ("plate", plate_footprint(plate_sk))):
        spill = must_fit.area - overlap(must_fit, cavity_sk)
        assert spill < 0.01, f"{side}: {label} spills {spill:.2f}mm^2 past the case cavity"
    outer_sk = rounded_outer_sketch(cavity_sk, WALL_T)

    outer_solid = b3d.extrude(outer_sk, amount=wall_top_z)
    cavity_solid = b3d.Pos(0, 0, FLOOR_T) * b3d.extrude(
        cavity_sk, amount=wall_top_z - FLOOR_T + 1.0
    )
    case = outer_solid - cavity_solid

    # A single scan helper, reused by the support ribs below and by the
    # USB/TRRS notches further down. The real outline isn't a rectangle --
    # it has a stepped top edge, so a position guessed as a fixed offset
    # from the outline's bounding box can land entirely outside the real
    # wall (found exactly this: a USB notch placed ~9mm off, cutting empty
    # air while the real wall nearby stayed solid, confirmed by slicing the
    # exported STL and finding an unbroken boundary where the notch was
    # supposed to be). Scan for where the actual wall is instead of assuming.
    def scan_wall_crossing(sk, probe_fn, lo, hi, step=0.1):
        """Returns the (x, y) point where the wall was found, not the scan
        parameter `t` -- for probe_fn's that aren't the identity in one
        axis (e.g. TRRS below), returning `t` itself silently returns the
        wrong coordinate."""
        n = int((hi - lo) / step)
        for i in range(n + 1):
            t = lo + i * step
            x, y = probe_fn(t)
            probe = b3d.Pos(x, y, 0) * b3d.Circle(0.05)
            if (sk & probe).area > 0.5 * probe.area:
                return (x, y)
        return None

    # ---- bosses under the PCB M2 holes (and the either/or spot it lacks) ----
    # A boss at a spot this PCB has no hole for presses on the board's
    # underside, so it has to miss every part there.
    for h in data["mount_holes"]:
        if h["on_pcb"]:
            continue
        for k in data["keepouts"]:
            kx0, ky0, kx1, ky1 = k["bbox"]
            gap = math.hypot(max(kx0 - h["x"], 0, h["x"] - kx1), max(ky0 - h["y"], 0, h["y"] - ky1)) - BOSS_OD / 2
            assert gap >= 0.0, (
                f"{side}: boss at the either/or spot ({h['x']:.1f},{h['y']:.1f}) would press on {k['ref']} ({gap:.2f}mm)"
            )
    boss_positions = []
    for h in data["mount_holes"]:
        x, y = h["x"], h["y"]
        boss = b3d.Pos(x, y, FLOOR_T) * b3d.Cylinder(
            radius=BOSS_OD / 2, height=BOSS_H, align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN)
        )
        case = case + boss
        boss_positions.append((x, y))
    for h in data["mount_holes"]:
        x, y = h["x"], h["y"]
        bore = b3d.Pos(x, y, boss_top_z - INSERT_DEPTH) * b3d.Cylinder(
            radius=INSERT_BORE_D / 2, height=INSERT_DEPTH + 0.5,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )
        case = case - bore

    usb_part = part_by_type(parts, "ProMicro_v3")
    trrs_part = part_by_type(parts, "MJ-4PP-9_1side")

    usb_cx, _ = bbox_center(usb_part["bbox"])
    notch_h = wall_top_z - FLOOR_T + 1.0

    usb_wall_hit = scan_wall_crossing(outer_sk, lambda t: (usb_cx, t), 5, 60)
    assert usb_wall_hit is not None, f"{side}: couldn't find the outer wall near the USB connector (x={usb_cx:.1f})"
    usb_wall_y = usb_wall_hit[1]
    y0, y1 = usb_wall_y - 3.0, usb_wall_y + 12.0  # generous past the wall band; a no-op once inside the cavity
    usb_notch = b3d.Pos(usb_cx, (y0 + y1) / 2, FLOOR_T) * b3d.Box(
        USB_NOTCH_W, y1 - y0, notch_h,
        align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
    )
    case = case - usb_notch

    trrs_bb = trrs_part["bbox"]
    _, trrs_cy = bbox_center(trrs_bb)
    # inner edge: right side of left half, left side of right half -- scan
    # inward from well past the board edge until the wall is found
    if is_left:
        trrs_wall_hit = scan_wall_crossing(outer_sk, lambda t: (ob[2] + 15 - t, trrs_cy), 0, 30)
    else:
        trrs_wall_hit = scan_wall_crossing(outer_sk, lambda t: (ob[0] - 15 + t, trrs_cy), 0, 30)
    assert trrs_wall_hit is not None, f"{side}: couldn't find the outer wall near the TRRS jack (y={trrs_cy:.1f})"
    trrs_wall_x = trrs_wall_hit[0]
    # left: wall's outer face is the larger x (cavity is smaller x), so the
    # 3mm outside-margin goes on the + side and the 12mm cavity-depth on -.
    # right: mirrored.
    x0 = trrs_wall_x - 12.0 if is_left else trrs_wall_x - 3.0
    x1 = trrs_wall_x + 3.0 if is_left else trrs_wall_x + 12.0
    trrs_notch = b3d.Pos((x0 + x1) / 2, trrs_cy, FLOOR_T) * b3d.Box(
        x1 - x0, TRRS_NOTCH_W, notch_h,
        align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
    )
    case = case - trrs_notch

    # Ground-truth check: confirm each notch actually opened the wall it was
    # aimed at, and that the opposite wall is still solid -- this is what
    # would have caught scan_wall_crossing() returning the scan parameter
    # instead of the probed coordinate (the TRRS notch silently cut the
    # wrong wall on the left half, and no wall at all on the right half).
    outer_bb = outer_sk.bounding_box()
    notch_z = (FLOOR_T + wall_top_z) / 2

    def assert_material(x, y, present, label):
        probe = b3d.Pos(x, y, notch_z) * b3d.Box(0.6, 0.6, 0.6)
        vol = (case & probe).volume
        if present:
            assert vol > 0.05, f"{side}: {label} at ({x:.1f},{y:.1f}) has no wall material -- expected solid wall here"
        else:
            assert vol < 0.01, f"{side}: {label} at ({x:.1f},{y:.1f}) still has wall material -- notch didn't open here"

    usb_notch_x, usb_notch_y = usb_cx, (y0 + y1) / 2
    assert_material(usb_notch_x, usb_notch_y, False, "USB notch")

    trrs_notch_x, trrs_notch_y = (x0 + x1) / 2, trrs_cy
    trrs_opposite_x = outer_bb.min.X + WALL_T / 2 if is_left else outer_bb.max.X - WALL_T / 2
    assert_material(trrs_notch_x, trrs_notch_y, False, "TRRS notch")
    assert_material(trrs_opposite_x, trrs_cy, True, "wall opposite the TRRS notch")

    # ---- foot/tent mounting points ----
    # A fixed inset from the bbox corner isn't safe here: the real outer
    # wall isn't a plain rectangle (it follows the board's own irregular
    # outline, further bulged wherever key_reinforcement_sketch widened
    # it), so a fixed inset can land a foot almost tangent to the wall at
    # some corners -- found this exact defect (a ~0.01mm sliver) by
    # ray-casting an exported STL. Instead, shrink the outer boundary by
    # the foot radius plus a real safety margin, and only place feet at
    # points already inside that safe zone -- guaranteed clearance by
    # construction, not by hoping a fixed offset happens to be enough.
    # placement uses a bit more margin than the verification below requires
    # -- picking the exact extreme vertex of the bare-minimum safe zone
    # leaves zero numerical slack, which the offset/fillet operations don't
    # reliably hit exactly, so give it real room instead of a razor's edge
    safe_zone_sk = b3d.offset(
        outer_sk, amount=-(FOOT_D / 2 + FOOT_WALL_CLEARANCE + 0.5), kind=b3d.Kind.ARC
    )
    safe_verts = [(v.X, v.Y) for v in safe_zone_sk.vertices()]
    foot_positions = [
        max(safe_verts, key=lambda p, dx=dx, dy=dy: p[0] * dx + p[1] * dy)
        for (dx, dy) in [(-1, -1), (1, -1), (-1, 1), (1, 1)]
    ]
    # Plain through-hole, not a blind recess: a tent leg's own insert sits
    # at the top of the leg (see build_tent), so the case side only ever
    # needs a screw-clearance hole here, the same for every mounting point
    # regardless of whether a tent leg or a plain adhesive foot ends up
    # over it (the hole is small enough that an adhesive foot still sticks
    # down fine straddling it).
    for (x, y) in foot_positions:
        foot = b3d.Pos(x, y, -0.1) * b3d.Cylinder(
            radius=TENT_SCREW_CLEARANCE_D / 2, height=FLOOR_T + 0.2,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )
        case = case - foot

    # ---- verification checks ----
    # A real minimum-clearance check, not just "doesn't poke through": shrink
    # the outer wall boundary by (feature radius + required wall thickness)
    # and confirm the feature's centre still lands inside what's left. This
    # is what caught the foot-recess defect above -- checking only for zero
    # overlap area missed a foot sitting almost exactly tangent to the wall.
    def assert_clear_of_wall(x, y, radius, min_wall, label):
        safe = b3d.offset(outer_sk, amount=-(radius + min_wall), kind=b3d.Kind.ARC)
        probe = b3d.Pos(x, y, 0) * b3d.Circle(0.05)
        covered = (probe & safe).area
        assert covered > 0.9 * probe.area, (
            f"{side}: {label} at ({x:.1f},{y:.1f}) has less than {min_wall}mm of wall "
            f"around it -- move it or shrink its radius"
        )

    for (fx, fy) in foot_positions:
        assert_clear_of_wall(fx, fy, FOOT_D / 2, FOOT_WALL_CLEARANCE, "foot recess")

    metrics = {
        "wall_top_z": wall_top_z,
        "boss_top_z": boss_top_z,
        "pcb_top_z": pcb_top_z,
        "foot_positions": foot_positions,
        "boss_positions": boss_positions,
        "cavity_sk": cavity_sk,
        "outer_sk": outer_sk,
        "notch_bbs": [
            (usb_cx - USB_NOTCH_W / 2, y0, usb_cx + USB_NOTCH_W / 2, y1),
            (x0, trrs_cy - TRRS_NOTCH_W / 2, x1, trrs_cy + TRRS_NOTCH_W / 2),
        ],
    }
    return case, metrics


# ----------------------------------------------------------------------
# Floor mat template
# ----------------------------------------------------------------------
def build_floor_mat(side, data, case, metrics):
    """Outline of the sound-deadening mat on the case floor: the cavity
    pulled in from the wall, with holes round the bosses and tent screw
    heads, and kept off the MCU strip's through-hole pins. Returned in
    KiCad's frame like everything else; the caller exports it."""
    mat = b3d.offset(metrics["cavity_sk"], amount=-MAT_EDGE_CLEARANCE, kind=b3d.Kind.ARC)
    for x, y in metrics["boss_positions"]:
        mat = mat - b3d.Pos(x, y) * b3d.Circle(MAT_BOSS_HOLE_D / 2)
    for x, y in metrics["foot_positions"]:
        mat = mat - b3d.Pos(x, y) * b3d.Circle(MAT_SCREW_HOLE_D / 2)
    pins = bbox_union([part_by_type(data["parts"], t)["bbox"] for t in MCU_ZONE_PARTS], margin=MAT_PIN_MARGIN)
    mat = mat - rect_from_bb(pins)
    mat = open_sketch(mat, MAT_MIN_WIDTH / 2)
    assert mat.area > 0, f"{side}: floor mat came out empty"

    # Ground truth is the case solid itself: a mat of the real thickness,
    # lying on the floor, must not touch the walls or bosses.
    mat_solid = extrude_up(mat, FLOOR_T, MAT_T)
    clash = overlap(mat_solid, case, "volume")
    assert clash < 0.01, f"{side}: floor mat intersects the case ({clash:.2f}mm^3)"
    for x, y in metrics["foot_positions"]:
        head = b3d.Pos(x, y) * b3d.Circle(PLATE_SCREW_HEAD_D / 2)
        assert overlap(head, mat) < 0.01, f"{side}: floor mat covers the tent screw head at ({x:.1f},{y:.1f})"
    return mat, {"pieces": len(mat.faces()), "area": mat.area}


def export_floor_mat(side, mat):
    """Tracing template: a thin print plus a DXF for paper. Unlike the
    plate DXF, both are mirrored into the real-world frame, so the
    template reads right side up laid on the mat's foil (top) face."""
    phys = to_physical(mat)
    write(extrude_up(mat, 0, MAT_TEMPLATE_T), f"mat-template-{side}", indent="  ")
    dxf_path = os.path.join(OUT_DIR, f"mat-template-{side}.dxf")
    exp = b3d.ExportDXF()
    exp.add_shape(phys)
    exp.write(dxf_path)
    print(f"  wrote {dxf_path}")


# ----------------------------------------------------------------------
# Tenting legs
# ----------------------------------------------------------------------
def extrude_down(sk, amount):
    """Extrude a sketch downward from z=0. A bare b3d.extrude() follows the
    sketch's own face normal, and a polygon drawn clockwise has its normal
    pointing down -- the first tent's frame came out 2mm below the leg tops
    that way. Give the direction explicitly and check where it landed."""
    solid = b3d.extrude(sk, amount=amount, dir=(0, 0, -1))
    bb = solid.bounding_box()
    assert abs(bb.max.Z) < 1e-6 and abs(bb.min.Z + amount) < 1e-6, (
        f"extrude_down landed at z {bb.min.Z:.3f}..{bb.max.Z:.3f}, expected {-amount:.3f}..0"
    )
    return solid


def extrude_up(sk, z0, height):
    """Extrude a sketch upward from z0, whatever way its face normal points
    (see extrude_down)."""
    solid = b3d.Pos(0, 0, z0) * b3d.extrude(sk, amount=height, dir=(0, 0, 1))
    bb = solid.bounding_box()
    assert abs(bb.min.Z - z0) < 1e-6 and abs(bb.max.Z - z0 - height) < 1e-6, (
        f"extrude_up landed at z {bb.min.Z:.3f}..{bb.max.Z:.3f}, expected {z0:.3f}..{z0 + height:.3f}"
    )
    return solid


def build_tent(side, data, metrics, angle_deg):
    """Printed tenting leg: bolts on at the same 4 points build_case already
    cut a screw-clearance hole for, in place of rubber feet. Tilts the half
    so its inner edge (toward the gap between halves) sits higher than its
    outer edge -- a peaked-roof tent, not a magnetic one.

    Built in the case's own frame, hanging below z=0:
      - z=0 is the flat mounting face, which goes against the case's
        bottom. Four round legs and the beams joining them all start there.
      - The desk is a plane tilted by `angle_deg` about the Y axis, closest
        to the case (TENT_MIN_T away) at the case's outer edge. Everything
        below it is cut off, so all four legs end in that one plane and sit
        flat on the desk.

    Each leg carries its own M2 insert, pressed into the flat mounting
    face. The screw comes down from inside the case, through the floor
    hole, into that insert -- so one short screw works at every corner
    however tall that corner's leg is. (An insert in the case instead would
    need a screw as long as the leg.)"""
    is_left = side == "left"
    feet = metrics["foot_positions"]
    outer_sk = metrics["outer_sk"]
    obb = outer_sk.bounding_box()
    pivot_x = obb.min.X if is_left else obb.max.X
    far_x = obb.max.X if is_left else obb.min.X
    tan = math.tan(math.radians(angle_deg))

    def thickness(x):
        """Distance from the mounting face down to the desk plane at x."""
        return TENT_MIN_T + ((x - pivot_x) if is_left else (pivot_x - x)) * tan

    max_t = thickness(far_x)

    # ---- legs: round pads, clipped flush to the case's own outline ----
    pads_sk = None
    for (x, y) in feet:
        pad = b3d.Pos(x, y, 0) * b3d.Circle(TENT_FOOT_D / 2)
        pads_sk = pad if pads_sk is None else pads_sk + pad
    pads_sk = pads_sk & outer_sk

    # ---- frame: a beam along each side of the quad the legs make, plus a
    # brace across the middle of its two longer sides ----
    # foot_positions is in (BL, BR, TL, TR) order -- one max() per diagonal
    # direction in build_case -- so swap the last two to walk the quad.
    # Straight beams between leg centres, not an offset ring: offsetting a
    # path that runs through every leg's centre self-intersects at the
    # corners (the union came back invalid while still reporting one solid).
    def beam(p0, p1):
        (x0, y0), (x1, y1) = p0, p1
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        nx, ny = -dy / length * TENT_FRAME_W / 2, dx / length * TENT_FRAME_W / 2
        return poly([(x0 + nx, y0 + ny), (x0 - nx, y0 - ny), (x1 - nx, y1 - ny), (x1 + nx, y1 + ny)])

    def midpoint(e):
        return ((e[0][0] + e[1][0]) / 2, (e[0][1] + e[1][1]) / 2)

    def length(e):
        return math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1])

    def inside_case(p0, p1):
        b = beam(p0, p1)
        return overlap(b, outer_sk) >= 0.995 * b.area

    ring = [feet[0], feet[1], feet[3], feet[2]]
    edges = [(ring[i], ring[(i + 1) % 4]) for i in range(4)]
    cx = sum(x for x, y in feet) / 4
    cy = sum(y for x, y in feet) / 4

    # The case outline is not convex (there is a notch between the bottom
    # row and the thumb cluster), so a straight beam between two legs can
    # leave the case's footprint. Bend any such side inward through one
    # waypoint, pushed toward the middle until both halves stay inside.
    segments = []
    nodes = []          # one point on each side for the brace to land on
    for e in edges:
        mx, my = midpoint(e)
        if inside_case(*e):
            segments.append(e)
            nodes.append((mx, my))
            continue
        d = math.hypot(cx - mx, cy - my)
        for step in range(1, int(d)):
            w = (mx + (cx - mx) / d * step, my + (cy - my) / d * step)
            if inside_case(e[0], w) and inside_case(w, e[1]):
                segments += [(e[0], w), (w, e[1])]
                nodes.append(w)
                break
        else:
            raise AssertionError(f"{side}: no route inside the case for the tent beam {e[0]} -> {e[1]}")

    long_pair = (0, 2) if length(edges[0]) + length(edges[2]) > length(edges[1]) + length(edges[3]) else (1, 3)
    brace = (nodes[long_pair[0]], nodes[long_pair[1]])
    assert inside_case(*brace), f"{side}: tent brace leaves the case's footprint"
    frame_sk = beam(*brace)
    for s in segments:
        frame_sk = frame_sk + beam(*s)
    frame_sk = frame_sk & outer_sk

    tent = extrude_down(pads_sk, max_t + 1.0) + extrude_down(frame_sk, TENT_FRAME_T)

    # ---- cut off everything below the desk plane ----
    # Pos*Rot*shape: tilt the cutter's top face about the pivot line first,
    # then carry it to the pivot. A positive rotation about +Y swings +X
    # down, which is the way the left half's desk plane falls; the right
    # half's falls the other way.
    y_mid = (obb.min.Y + obb.max.Y) / 2
    below_desk = b3d.Pos(pivot_x, y_mid, -TENT_MIN_T) * b3d.Rot(0, angle_deg if is_left else -angle_deg, 0) * b3d.Box(
        1000, 1000, 500, align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MAX)
    )
    tent = tent - below_desk

    # ---- insert bores, into the flat mounting face ----
    bore_depth = INSERT_DEPTH + TENT_BORE_EXTRA
    for (x, y) in feet:
        left_under = thickness(x) - bore_depth - TENT_RUBBER_RECESS
        assert left_under >= 0.8, (
            f"{side}: only {left_under:.2f}mm of leg left between the insert bore and the rubber-foot "
            f"recess at ({x:.1f},{y:.1f}) -- raise TENT_MIN_T for an angle this shallow"
        )
        tent = tent - b3d.Pos(x, y, -bore_depth) * b3d.Cylinder(
            radius=INSERT_BORE_D / 2, height=bore_depth + 0.1,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )

    # ---- rubber-foot recesses, into the desk face of each leg ----
    # Same Pos*Rot*shape as the desk cut, so the recess floor is parallel to
    # the desk plane and the recess goes in square to it.
    assert TENT_RUBBER_H - TENT_RUBBER_RECESS >= 1.0, "rubber foot would barely stand proud of its recess"
    recess_r = (TENT_RUBBER_D + TENT_RUBBER_CLEAR) / 2
    recess_centres = []
    for (x, y) in feet:
        d = math.hypot(cx - x, cy - y)
        rx, ry = x + (cx - x) / d * TENT_RUBBER_SHIFT, y + (cy - y) / d * TENT_RUBBER_SHIFT
        recess_centres.append((rx, ry))
        tent = tent - b3d.Pos(rx, ry, -thickness(rx)) * b3d.Rot(0, angle_deg if is_left else -angle_deg, 0) * b3d.Pos(
            0, 0, -5.0
        ) * b3d.Cylinder(
            radius=recess_r, height=TENT_RUBBER_RECESS + 5.0,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )

    # ---- verification ----
    assert tent.is_valid, f"{side}: tent solid is not valid"
    assert len(tent.solids()) == 1, f"{side}: tent came out as {len(tent.solids())} separate pieces"
    assert TENT_FRAME_T < TENT_MIN_T, "frame is thicker than the tent's thinnest point -- the desk plane would cut it"

    def solid_at(x, y, z):
        return overlap(tent, b3d.Pos(x, y, z) * b3d.Box(0.4, 0.4, 0.4), "volume") > 0.03

    def void_at(x, y, z):
        return overlap(tent, b3d.Pos(x, y, z) * b3d.Box(0.4, 0.4, 0.4), "volume") < 0.001

    # the mounting face really is flat and at z=0, on the legs and on every
    # beam -- nothing above it, material right under it
    leg_probes = []
    for (x, y) in feet:
        d = math.hypot(cx - x, cy - y)
        leg_probes.append((x + (cx - x) / d * 5.0, y + (cy - y) / d * 5.0))  # 5mm in from the bore, toward the middle
    top_probes = leg_probes + [midpoint(s) for s in segments] + [midpoint(brace)]
    for (px, py) in top_probes:
        assert solid_at(px, py, -0.3), f"{side}: tent has no material under its mounting face at ({px:.1f},{py:.1f})"
        assert void_at(px, py, 0.3), f"{side}: tent sticks up past its mounting face at ({px:.1f},{py:.1f})"
    bx, by = midpoint(brace)
    assert void_at(bx, by, -TENT_FRAME_T - 0.5), f"{side}: brace is thicker than TENT_FRAME_T"
    # every leg ends exactly on the desk plane (probed on the rim beside the
    # rubber-foot recess), and the recess is open to its depth and no deeper
    for (x, y), (rx, ry) in zip(feet, recess_centres):
        d = math.hypot(cx - rx, cy - ry)
        px, py = rx + (cx - rx) / d * (recess_r + 1.2), ry + (cy - ry) / d * (recess_r + 1.2)
        assert math.hypot(px - x, py - y) < TENT_FOOT_D / 2 - 0.5, f"{side}: no rim left beside the recess at ({x:.1f},{y:.1f})"
        t = thickness(px)
        assert solid_at(px, py, -t + 0.6), f"{side}: leg at ({px:.1f},{py:.1f}) stops short of the desk plane"
        assert void_at(px, py, -t - 0.6), f"{side}: leg at ({px:.1f},{py:.1f}) pokes below the desk plane"
        t = thickness(rx)
        assert void_at(rx, ry, -t + TENT_RUBBER_RECESS / 2), f"{side}: rubber-foot recess at ({rx:.1f},{ry:.1f}) is not open"
        assert solid_at(rx, ry, -t + TENT_RUBBER_RECESS + 0.5), f"{side}: rubber-foot recess at ({rx:.1f},{ry:.1f}) is too deep"
    for (x, y) in feet:
        assert void_at(x, y, -INSERT_DEPTH / 2), f"{side}: insert bore at ({x:.1f},{y:.1f}) is not open"
    # the screw: head on the case floor, down through it into the insert
    reach = TENT_SCREW_LEN - FLOOR_T
    assert reach <= bore_depth, f"M2x{TENT_SCREW_LEN:.0f} bottoms out in the tent's insert bore"
    engagement = min(reach, INSERT_DEPTH)
    assert engagement >= 2.5, f"M2x{TENT_SCREW_LEN:.0f} only reaches {engagement:.1f}mm into the tent's insert"

    info = {
        "angle_deg": angle_deg,
        "span": abs(far_x - pivot_x),
        "leg_heights": [(x, y, round(thickness(x), 2)) for (x, y) in feet],
        "max_thickness": max_t,
        "screw_engagement": engagement,
    }
    return tent, info


# ----------------------------------------------------------------------
# MCU cover
# ----------------------------------------------------------------------
def build_cover(side, data, case, metrics):
    """Flat cover over the MCU strip. Its rim rests on the case wall top
    along the board's top and inner edges; at the other end it stands on
    posts over the PCB mounting holes beside the TRRS jack, and one long
    screw per post goes through cover, post and PCB into the same
    heat-set insert an ordinary PCB screw would use."""
    keys = data["keys"]
    parts = data["parts"]
    cavity_sk = metrics["cavity_sk"]
    outer_sk = metrics["outer_sk"]
    pcb_top_z = metrics["pcb_top_z"]
    wall_top_z = metrics["wall_top_z"]
    under_z = pcb_top_z + COVER_UNDERSIDE_ABOVE_PCB
    top_z = under_z + COVER_T
    assert under_z > wall_top_z, f"{side}: cover underside is below the wall top"

    zone_bb, post_holes = mcu_zone(side, data)

    # footprint: the zone, out to the wall's outer edge -- but not over
    # the USB/TRRS notches (a plug's overmold stands
    # taller than the cover's underside there) and not under any keycap (a
    # pressed keycap's skirt comes down lower than the cover's top)
    wall_sk = outer_sk - cavity_sk
    for nb in metrics["notch_bbs"]:
        wall_sk = wall_sk - rect_from_bb(bbox_union([nb], margin=0.5))
    limit = cavity_sk + wall_sk
    cover_sk = (rect_from_bb(zone_bb) & limit) - keycap_sketch(keys, COVER_KEYCAP_CLEARANCE)
    # drop anything too narrow to print, keep the one real piece
    cover_sk = open_sketch(cover_sk, 0.6)
    cover_sk = max(cover_sk.faces(), key=lambda f: f.area)

    slab = b3d.Pos(0, 0, under_z) * b3d.extrude(cover_sk, amount=COVER_T)
    rim_sk = cover_sk & wall_sk
    cover = slab + b3d.Pos(0, 0, wall_top_z) * b3d.extrude(rim_sk, amount=under_z - wall_top_z)

    # posts stand through the plate's level, so keep them off its edge
    plate_sk, _ = build_plate_sketch(side, data)
    plate_clear = b3d.offset(plate_sk, amount=MCU_OPENING_MARGIN, kind=b3d.Kind.ARC)
    for h in post_holes:
        post_sk = (b3d.Pos(h["x"], h["y"], 0) * b3d.Circle(COVER_POST_OD / 2)) & cover_sk
        post_sk = post_sk - plate_clear
        full = math.pi * (COVER_POST_OD / 2) ** 2
        assert post_sk.area > 0.8 * full, (
            f"{side}: cover post at ({h['x']:.1f},{h['y']:.1f}) is clipped to "
            f"{post_sk.area / full:.0%} of a full post"
        )
        cover = cover + b3d.Pos(0, 0, pcb_top_z) * b3d.extrude(post_sk, amount=under_z - pcb_top_z)
    for h in post_holes:
        cover = cover - b3d.Pos(h["x"], h["y"], pcb_top_z - 1.0) * b3d.Cylinder(
            radius=COVER_SCREW_D / 2, height=top_z - pcb_top_z + 2.0,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )

    # OLED socket slot: the module's own pin header (plastic and all) drops
    # through it into the socket, and the module lies on the cover. The
    # reset hole is right beside it; the old plate clipped the slot back to
    # keep a wall between them, which left it too short for the header's
    # fourth pin. Size both properly and check the wall instead.
    oled_part = part_by_type(parts, "OLED_1side")
    pad_xs = [p["pos"][0] for p in oled_part["pads"]]
    pad_ys = [p["pos"][1] for p in oled_part["pads"]]
    slot_x0, slot_x1 = min(pad_xs) - OLED_SLOT_MARGIN_X, max(pad_xs) + OLED_SLOT_MARGIN_X
    slot_y0, slot_y1 = min(pad_ys) - OLED_SLOT_MARGIN_Y, max(pad_ys) + OLED_SLOT_MARGIN_Y
    rx, ry = part_by_type(parts, "ResetSW_1side")["pos"]
    reset_r = COVER_RESET_HOLE_D / 2
    slot_to_reset = math.hypot(
        max(slot_x0 - rx, 0, rx - slot_x1), max(slot_y0 - ry, 0, ry - slot_y1)
    ) - reset_r
    assert slot_to_reset >= COVER_MIN_WALL, (
        f"{side}: only {slot_to_reset:.2f}mm of cover between the OLED slot and the reset hole"
    )
    through = dict(align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN))
    cover = cover - b3d.Pos((slot_x0 + slot_x1) / 2, (slot_y0 + slot_y1) / 2, under_z - 1.0) * b3d.Box(
        slot_x1 - slot_x0, slot_y1 - slot_y0, COVER_T + 2.0, **through
    )
    cover = cover - b3d.Pos(rx, ry, under_z - 1.0) * b3d.Cylinder(
        radius=reset_r, height=COVER_T + 2.0, **through
    )

    # ---- verification ----
    assert cover.is_valid, f"{side}: cover solid is not valid"
    assert len(cover.solids()) == 1, f"{side}: cover came out as {len(cover.solids())} separate pieces"
    assert overlap(cover_sk, keycap_sketch(keys, 0)) < 1e-6, f"{side}: cover runs under a keycap"
    clash = overlap(cover, case, "volume")
    assert clash < 0.01, f"{side}: cover intersects the case ({clash:.2f}mm^3)"
    assert rim_sk.area > 20, f"{side}: cover has almost no rim on the wall top ({rim_sk.area:.1f}mm^2)"
    # every part under the cover, as a box of its real height, must clear
    # it. Clipped to the cavity: the Pro Micro's footprint bbox includes
    # its USB connector's overhang past the board edge, which is the wall
    # notch's business, not the cover's.
    for t, height in PART_HEIGHTS.items():
        box = b3d.Pos(0, 0, pcb_top_z) * b3d.extrude(
            rect_from_bb(part_by_type(parts, t)["bbox"]) & cavity_sk, amount=height
        )
        hit = overlap(cover, box, "volume")
        assert hit < 0.01, f"{side}: cover collides with {t} ({hit:.2f}mm^3)"
    plate_top_z = pcb_top_z + PLATE_TOP_ABOVE_PCB
    thickest = max(POM_PLATE_T, FR4_PLATE_T, MJF_PLATE_T)
    plate = b3d.Pos(0, 0, plate_top_z - thickest) * b3d.extrude(plate_sk, amount=thickest)
    clash = overlap(cover, plate, "volume")
    assert clash < 0.01, f"{side}: cover intersects the plate ({clash:.2f}mm^3)"
    # ...and the plate must not sit over any of them either
    for t in PART_HEIGHTS:
        over = overlap(plate_sk, rect_from_bb(part_by_type(parts, t)["bbox"]))
        assert over < 0.01, f"{side}: plate still covers {over:.1f}mm^2 of {t}"

    info = {
        "post_holes": [(h["x"], h["y"]) for h in post_holes],
        "top_above_pcb": top_z - pcb_top_z,
        # screw head sits on the cover top; thread runs down to the boss top
        "screw_grip": top_z - metrics["boss_top_z"],
        "footprint_bb": cover_sk.bounding_box(),
        "rim_area": rim_sk.area,
        "slot_to_reset": slot_to_reset,
    }
    return cover, info


# ----------------------------------------------------------------------
# Plate (POM/FR4-agnostic polygon geometry)
# ----------------------------------------------------------------------
def build_plate_sketch(side, data):
    """Build the plate sketch, verifying each cut by comparing the area
    actually removed to the cutter's own nominal area -- if a hole is
    clipped by the plate boundary (too close to the edge), the boolean
    subtract removes less material than the cutter's full area, and this
    catches that directly instead of relying on a fragile bbox proxy.

    The plate is cut away over the MCU strip (Pro Micro, OLED socket,
    reset switch, TRRS jack) -- see build_cover for what goes there."""
    keys = data["keys"]
    parts = data["parts"]

    # the outer edge, with every switch's reinforcement patch already in it
    plate_sk = board_envelope(side, data)

    def cut(sk, cutter, cutter_area, label, tol=0.02, min_ratio=0.5):
        before = sk.area
        result = sk - cutter
        removed = before - result.area
        ratio = removed / cutter_area if cutter_area else 1.0
        if ratio < min_ratio:
            raise AssertionError(
                f"{side}: {label} only removed {removed:.1f}mm^2 of an expected "
                f"{cutter_area:.1f}mm^2 ({ratio:.0%}) -- badly clipped, check its position"
            )
        if ratio < 1 - tol:
            print(f"  WARNING: {side} {label} clipped -- removed {removed:.1f}/{cutter_area:.1f}mm^2 "
                  f"({ratio:.0%}); close to the plate edge, check by eye")
        return result

    for k in keys:
        # plate cutout is always the plain 14x14 switch-body square, even
        # for the 1.5u thumb keys -- see key_reinforcement_sketch
        # Pos*Rot*shape, not Rot*Pos*shape: the outer transform in a chain
        # applies last and about its own frame, so Rot*Pos would rotate the
        # translation itself around the global origin instead of spinning
        # the rectangle in place before moving it.
        hole = b3d.Pos(k["x"], k["y"], 0) * b3d.Rot(0, 0, k["rot"]) * b3d.Rectangle(KEY_HOLE, KEY_HOLE)
        plate_sk = cut(plate_sk, hole, KEY_HOLE * KEY_HOLE, f"key {k['ref']} hole")

    # M2 holes: some sit close enough to a neighboring switch hole that
    # cutting them leaves a sliver under ~1mm -- real risk for MJF/FDM
    # printing (JLC3DP flagged exactly this on the real files). Rather than
    # force a thin cut through, skip the hole entirely where that happens:
    # the material there is already mostly switch-hole anyway, so there's
    # no clearance to gain, and leaving it solid is strictly safer than a
    # fragile sliver. assert_clear_of_wall-style: test the cut on a throwaway
    # copy first, only commit it if it doesn't create a thin remnant.
    for h in data["mount_holes"]:
        hole = b3d.Pos(h["x"], h["y"], 0) * b3d.Circle(M2_CLEARANCE_D / 2)
        test = plate_sk - hole
        removed = plate_sk.area - test.area
        ratio = removed / (math.pi * (M2_CLEARANCE_D / 2) ** 2)
        if ratio < 0.9:
            print(f"  NOTE: {side} M2 hole at ({h['x']:.1f},{h['y']:.1f}) skipped on the plate -- "
                  f"too close to a switch hole to cut without leaving a thin sliver ({ratio:.0%} "
                  f"clear); no plate standoff there, PCB-to-case mounting is unaffected")
            continue

        # The hole itself may cut cleanly (ratio above) while still landing
        # close enough to a neighboring switch hole to leave a wall under
        # JLCPCB's 2mm "connect" ask -- found one at ~1.6mm this way, not
        # caught by the self-clip check above (that ratio mixes the small
        # encroachment in with the whole hole's area and dilutes it below
        # any reasonable threshold). Check the annulus we actually want
        # kept clear -- from the clearance radius out to +FAB_MIN_WALL --
        # directly: if any of *that* ring is already void (eaten by a
        # neighboring cutout), skip this hole rather than commit a
        # fab-risky cut, same outcome as the self-clip case above.
        safety_r = M2_CLEARANCE_D / 2 + FAB_MIN_WALL
        ring = b3d.Pos(h["x"], h["y"], 0) * (b3d.Circle(safety_r) - b3d.Circle(M2_CLEARANCE_D / 2))
        ring_void = ring.area - (plate_sk & ring).area
        if ring_void > 0.05:
            floor_r = M2_CLEARANCE_D / 2 + PLATE_HOLE_MIN_WALL
            floor_ring = b3d.Pos(h["x"], h["y"], 0) * (b3d.Circle(floor_r) - b3d.Circle(M2_CLEARANCE_D / 2))
            if floor_ring.area - (plate_sk & floor_ring).area > 0.05:
                print(f"  NOTE: {side} M2 hole at ({h['x']:.1f},{h['y']:.1f}) skipped on the plate -- "
                      f"a neighboring hole leaves under {PLATE_HOLE_MIN_WALL}mm of wall; no plate "
                      f"standoff there, PCB-to-case mounting is unaffected")
                continue
            print(f"  NOTE: {side} M2 hole at ({h['x']:.1f},{h['y']:.1f}) cut with a thin wall -- "
                  f"under {FAB_MIN_WALL}mm (JLCPCB's FR4 ask is 2.0) but at least {PLATE_HOLE_MIN_WALL}mm")

        plate_sk = test

    # Open the plate over the whole MCU strip: the TRRS jack, reset switch
    # and Pro Micro all stand taller than the gap under the plate (see
    # PART_HEIGHTS), so the plate can't cover them -- the printed cover
    # does. Every switch hole keeps its full reinforcement margin, so the
    # opening can't thin a wall next to a switch.
    zone_bb, post_holes = mcu_zone(side, data)
    opening = rect_from_bb(zone_bb) - key_reinforcement_sketch(keys, [])
    # build_cover cuts the cover back from every keycap -- from the angled
    # thumb key's most of all, since both 1.5u orientations count -- which
    # left a gap between the cover's edge and this opening's straight one.
    # Keep the plate there instead, reaching COVER_PLATE_LAP in under the
    # cover, but never over a part under the cover or round a cover post.
    keep = keycap_sketch(keys, COVER_KEYCAP_CLEARANCE + COVER_PLATE_LAP)
    for t in MCU_ZONE_PARTS:
        keep = keep - rect_from_bb(bbox_union([part_by_type(parts, t)["bbox"]], margin=MCU_OPENING_MARGIN))
    # Round a post, stop at the cover's edge instead of lapping under it,
    # and build_cover trims the post to keep MCU_OPENING_MARGIN off the plate
    cover_edge = keycap_sketch(keys, COVER_KEYCAP_CLEARANCE)
    for h in post_holes:
        keep = keep - (b3d.Pos(h["x"], h["y"], 0) * b3d.Circle(COVER_POST_OD / 2 + MCU_OPENING_MARGIN) - cover_edge)
    filled = plate_sk - (opening - keep)
    # drop any tab of the new fill under 1mm wide; the cover laps over
    # those spots anyway
    thin = (filled - open_sketch(filled, 0.5)) & (filled - (plate_sk - opening))
    plate_sk = filled if thin is None else filled - thin

    return plate_sk, zone_bb


def export_plate(side, data, thickness, tag):
    sk, mcu_bb = build_plate_sketch(side, data)
    solid = b3d.extrude(sk, amount=thickness)
    assert solid.is_valid, f"{side} {tag} plate solid is not valid"

    write(solid, f"plate-{tag}-{side}", indent="  ")
    # The DXF stays in KiCad's frame: make_fr4_plate.py writes it straight
    # back into a KiCad project. (For a laser/CNC shop it doesn't matter
    # either way -- a flat through-cut plate's mirror image is the same
    # part flipped over.)
    dxf_path = os.path.join(OUT_DIR, f"plate-{tag}-{side}.dxf")
    exp = b3d.ExportDXF()
    exp.add_shape(sk)
    exp.write(dxf_path)
    print(f"  wrote {dxf_path}")
    return sk, mcu_bb


def write(shape, name, indent=""):
    """Mirror into the real-world frame and write it as STL and STEP."""
    phys = to_physical(shape)
    for ext in ("stl", "step"):
        path = os.path.join(OUT_DIR, f"{name}.{ext}")
        if ext == "stl":
            b3d.export_stl(phys, path, tolerance=STL_TOLERANCE, angular_tolerance=STL_ANGULAR_TOLERANCE)
        else:
            b3d.export_step(phys, path)
        print(f"{indent}wrote {path}")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # start clean, so a part no longer generated can't linger and get printed
    for f in os.listdir(OUT_DIR):
        if f.endswith((".stl", ".step", ".dxf")):
            os.remove(os.path.join(OUT_DIR, f))
    # plates and spacers come per plate material (the spacer height depends
    # on plate thickness)
    plates = [("pom", POM_PLATE_T), ("fr4", FR4_PLATE_T), ("mjf", MJF_PLATE_T)]
    board = load_board()

    for tag, plate_t in plates:
        for name, od in ((f"spacer-{tag}", SPACER_OD), (f"spacer-narrow-{tag}", SPACER_OD_NARROW)):
            write(build_spacer(plate_t, od), name)

    for side in ("left", "right"):
        print(f"\n=== {side} ===")
        data = board[side]

        plate_sk, mcu_bb = export_plate(side, data, POM_PLATE_T, "pom")
        # FR4 geometry is the same polygon; its DXF is what
        # make_fr4_plate.py turns into the real FR4 order.
        export_plate(side, data, FR4_PLATE_T, "fr4ref")
        export_plate(side, data, MJF_PLATE_T, "mjf")

        case, metrics = build_case(side, data, plate_sk)
        assert case.is_valid, f"{side}: case solid is not valid"
        write(case, f"case-{side}", indent="  ")

        print(f"  stack: floor 0-{FLOOR_T}, boss top {metrics['boss_top_z']:.2f}, "
              f"PCB top {metrics['pcb_top_z']:.2f}, plate/wall top {metrics['wall_top_z']:.2f}")

        mat, mat_info = build_floor_mat(side, data, case, metrics)
        export_floor_mat(side, mat)
        print(f"  floor mat: {mat_info['pieces']} piece(s), {mat_info['area'] / 100:.0f}cm^2, "
              f"~{mat_info['area'] * 1e-6 * MAT_DENSITY * 1000:.0f}g at {MAT_T}mm butyl")
        print(f"  plate opening over the MCU strip, bbox: {[round(v,1) for v in mcu_bb]}")

        mount_holes = plate_mount_holes(side, data, plate_sk)
        mount_plan = report_plate_mount(side, data["keys"], mount_holes, metrics)
        kinds = [kind for _, kind in mount_plan]
        print(f"  plate-mount points: {len(kinds)} -- {kinds.count('standard')} standard spacers, "
              f"{kinds.count('narrow')} narrow")
        for tag, plate_t in plates:
            frame, finfo = build_spacer_frame(side, plate_sk, data["keys"], mount_plan, plate_t)
            clash = overlap(frame, b3d.Pos(0, 0, -metrics["pcb_top_z"]) * case, "volume")
            assert clash < 0.01, f"{side}: spacer frame intersects the case ({clash:.2f}mm^3)"
            write(frame, f"spacer-frame-{tag}-{side}", indent="  ")
        dropped = finfo["dropped"]
        print(f"  spacer frame: {finfo['posts']} posts ({finfo['pilots']} with pilots), {finfo['height']:.1f}mm tall under a {tag} plate"
              + (f", dropped {dropped:.1f}mm2 of loose slivers" if dropped > 0.5 else ""))

        tent, tent_info = build_tent(side, data, metrics, TENT_ANGLE_DEG)
        clash = overlap(tent, case, "volume")
        assert clash < 0.01, f"{side}: tent intersects the case ({clash:.2f}mm^3)"
        write(tent, f"tent-{side}", indent="  ")
        print(f"  tent: {TENT_ANGLE_DEG:.0f}deg across the case's {tent_info['span']:.0f}mm width, "
              f"{TENT_MIN_T:.0f}mm thick at the outer edge, {tent_info['max_thickness']:.1f}mm at the inner edge")
        print(f"  tent legs ({TENT_FOOT_D:.0f}mm dia), height at each leg's centre: "
              f"{[(round(x,1), round(y,1), h) for x, y, h in tent_info['leg_heights']]}mm")
        print(f"  tent screws: M2x{TENT_SCREW_LEN:.0f} from inside the case, "
              f"{tent_info['screw_engagement']:.1f}mm into each leg's {INSERT_DEPTH}mm insert")

        cover, info = build_cover(side, data, case, metrics)
        write(cover, f"cover-{side}", indent="  ")
        fb = info["footprint_bb"]
        print(f"  cover: {fb.size.X:.1f} x {fb.size.Y:.1f}mm, top {info['top_above_pcb']:.1f}mm above the PCB, "
              f"{len(info['post_holes'])} posts at {[(round(x,1), round(y,1)) for x, y in info['post_holes']]}")
        print(f"  cover screws: head to boss top is {info['screw_grip']:.1f}mm -- an M2x12 leaves "
              f"{12 - info['screw_grip']:.1f}mm in the {INSERT_DEPTH}mm insert")

    print("\nDone.")


if __name__ == "__main__":
    main()
