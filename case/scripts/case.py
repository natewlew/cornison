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
FLOOR_T = 4.0                # McMaster 94459A767's 4mm "Min Material
                              # Thickness": the tenting legs' inserts go in
                              # from below, through the floor (2.5 before
                              # 2026-10-23, when the inserts were in the legs)
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
# The wall below each notch stays up as far as the plug allows, closing the
# gap under the board there. Measured on the real parts (2026-10-21): the
# Keebio Pro Micro's USB-C socket is 3mm tall, centred 1-2mm above the PCB
# top, its mouth nearly flush with the case's outer face -- so the cable's
# grip stays outside and only the socket passes through the notch, and the
# wall comes up past the PCB's underside. The TRRS cable's grip sits ~2mm
# into the wall, on the jack's axis (2.5mm above the PCB top, from
# PJ320A.step), so its notch is a U round the grip: the user's own cable's
# grip is 7mm, but the notch is sized to fit most TRRS cables, which leaves
# the U's bottom just under the PCB's underside.
USB_SOCKET_BOTTOM = -0.5        # vs the PCB top: centre 1mm, 3mm tall
TRRS_AXIS_ABOVE_PCB = 2.5
TRRS_PLUG_D = 10.0
TRRS_GRIP_FROM_PCB_EDGE = 2.0   # the plugged-in TRRS cable's grip starts this far out
                                 # from the PCB's edge (the user's cable, measured
                                 # 2026-10-26). With the wall 0.5mm off the PCB its
                                 # outer face is 3.0 out, so the grip reaches 1.0mm in
NOTCH_CLEARANCE = 0.5
TRRS_NOTCH_W = TRRS_PLUG_D + 2 * NOTCH_CLEARANCE

# MCU cover: a printed part over the Pro Micro/TRRS/reset strip, standing
# on posts at the two PCB mounting holes beside the TRRS jack (the same
# two holes the stock Corne OLED cover uses). The OLED module plugs into a
# low-profile socket through a slot in the cover; its socket holds it, just
# clear of a shallow pocket in the cover's top.
#
# Part heights above the PCB's top face, measured from foostan's own 3D
# models in pcb/kbd (PJ320A.step, tact-switch.step, ProMicro.step with the
# footprints' model offsets applied) -- NOT yet from real parts. The Pro
# Micro figure is one on ordinary 2.5mm headers including its pin stubs;
# on Mill-Max low-profile sockets it sits no higher. Standard 8.5mm
# sockets put it at ~11mm and do not fit under this cover. Measured on the
# real build: direct-soldered with the stubs left long, it stood ~7mm and
# lifted the cover -- the stubs have to be trimmed to the solder.
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
COVER_INSET_BEVEL_IN = 1.0         # inset cover: its bevel starts this far in under
                                    # the cover's edge (and runs at 45 deg from the
                                    # cover's top edge down to the case's outer face)
COVER_PLATE_REST_IN = 1.0          # the skirt under the cover's angled edge reaches this
                                    # far in past the plate's edge (2mm wide in all, with
                                    # the 1mm lap: JLC3DP's minimum)
COVER_PLATE_LAP = 1.0              # where the cover is cut back for a keycap, the
                                    # plate reaches this far in under its edge
KEYCAP_1U = 18.1
KEYCAP_1_5U = 27.6
OLED_SLOT_MARGIN_X = 1.7        # beyond the end pins: half a 2.54mm pitch of header
                                 # plastic plus 0.43 clearance. The OLED window has to pass
                                 # the whole header, not just the pins
OLED_SLOT_MARGIN_Y = 1.5        # margin added beyond the pin row, each side
OLED_MODULE_L = 38.0            # measured 2026-10-19 (33 before, which left the
                                 # module running 5mm past the window at the back)
OLED_MODULE_W = 12.0            # measured
OLED_PIN_EDGE = 1.4             # pin row centre to the module's pin-side edge --
                                 # from the library's OLED-Module-with-Pins.step,
                                 # NOT measured; it sets where the OLED window lands
OLED_BOARD_ABOVE_PCB = 8.0      # measured 8-9mm: PCB top to the underside of the
                                 # module's board, plugged fully into its ~4mm
                                 # socket. The low end, so the covers clear it
OLED_WINDOW_CLEAR = 0.75        # flat cover's OLED window = module outline grown by
                                 # this each side. 0.5 was tight at the pin end
COVER_RESET_HOLE_D = 2.0        # paperclip access to the reset switch. Smaller than
                                 # the old plate's 3.0 so it clears the OLED slot
                                 # without the slot having to give way
COVER_MIN_WALL = 1.0            # JLC3DP's MJF minimum wall
# Two-piece clear cover (build_clear_cover): printed base + flat clear top
OLED_TOP_ABOVE_PCB = 14.0       # measured 13-14mm: PCB top to the OLED's glass,
                                 # plugged fully into its socket. The high end; a
                                 # direct-soldered OLED sits lower and still fits
STANDOFF_L = 15.0               # M2 male-female hex standoff body, PCB top to the
                                 # clear top
STANDOFF_MALE = 4.0             # its male thread: through the PCB, then 2.4mm into
                                 # the insert. A 3mm one barely reaches the insert
                                 # (tried 2026-10-18: won't start); 6mm bottoms out
STANDOFF_HEX_AF = 4.0           # across flats: M2 standoffs come in 3.5 and 4.0;
                                 # the bigger one sizes the base's holes
STANDOFF_HOLE_CLEAR = 0.4       # base hole = hex across corners + this
CLEAR_UNDERSIDE_ABOVE_PCB = STANDOFF_L
CLEAR_T = 2.0                   # clear acrylic sheet
CLEAR_TOP_SCREW_LEN = 5         # M2x5 through the clear top into the standoff
CLEAR_BASE_WALL_T = 2.0         # JLC3DP's 2mm minimum feature
CLEAR_PART_CLEARANCE = 0.5      # the base wall stands this far off every part
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

RUBBER_FOOT_D = 10.0               # the round rubber feet, on the case bottom
RUBBER_FOOT_H = 2.0                # or on the tent's leg ends: 10mm across, 2mm tall
RUBBER_RECESS_CLEAR = 0.4          # recess is this much wider than the foot
RUBBER_RECESS = 0.8                # and this deep, so the foot stands 1.2mm proud
FOOT_D = RUBBER_FOOT_D + RUBBER_RECESS_CLEAR  # the case bottom's rubber-foot
                                    # recess, at each of the 4 corner positions
                                    # (the tent's legs stand on the same spots)
FOOT_WALL_CLEARANCE = 1.5         # min wall thickness kept around every foot position

# Tenting legs: an optional printed part per half, bolted on at the same
# 4 foot positions in place of rubber feet, tilting the half so its inner
# edge (toward the gap between halves) sits higher than its outer edge --
# a peaked-roof tent, not a magnetic one. Each leg has a platform beside
# it at the mounting face; an M2 screw goes up through it from below into
# an insert in the case floor, so the tent comes off without opening the
# case, and the same short screw works at every leg however tall.
TENT_ANGLE_DEG = float(os.environ.get("TENT_ANGLE_DEG", "18"))
TENT_SCREW_CLEARANCE_D = 2.3       # M2 shank clearance through the platform,
                                    # same as M2_CLEARANCE_D
TENT_SCREW_SEAT = 3.0              # screw head seats this far below the
                                    # mounting face: the platform it clamps
TENT_SCREW_COLUMN_D = 5.0          # counterbore under the seat, kept clear
                                    # down to the desk: M2 low head (~4mm) and
                                    # room for the driver
TENT_SCREW_OFFSET = 13.5           # screw this far from its leg's centre: leg
                                    # radius + column radius + 1mm
TENT_PLUMB_SCREW_IN = 6.0          # a plumb leg's screw also moves this far in
                                    # toward the tent's middle (its offset along
                                    # the edge already clears the leaning leg)
TENT_FILLET_R = 4.0                # frame outline rounded by this much: fills
                                    # the notches where platforms and legs meet
                                    # the beams, and softens inside corners
TENT_MIN_T = 5.0                   # tent thickness at the case's low (outer)
                                    # edge, where the desk plane comes closest
                                    # to the case -- thicker than the frame, so
                                    # the desk plane never cuts into it
TENT_SCREW_LEN = 6.0               # M2x6: TENT_SCREW_SEAT through the
                                    # platform, the rest into the case's insert
TENT_FOOT_D = 20.0                 # leg diameter, clipped flush to the case's
                                    # own outline where it would overhang it
TENT_TALL_LEGS = 2                 # this many of the tallest legs (the inner
                                    # pair) get their screws along the inner
                                    # edge rather than toward the middle
TENT_PLUMB = os.environ.get("TENT_PLUMB", "1") == "1"  # the tall legs lean
                                    # in by the tent angle, so they stand
                                    # plumb on the desk (the user's pick,
                                    # 2026-10-23). TENT_PLUMB=0: square to the
                                    # case like the short ones, carrying the
                                    # case's side wall on down to the desk
TENT_FRAME_W = 10.0                # width of the beams tying the 4 legs together
TENT_FRAME_T = 4.0                 # their thickness, hanging off the flat
                                    # mounting face; they never reach the desk
# Weight tray: a shallow band across the middle of the tent, beam to beam,
# square to the case, with a grid of cells for stick-on tire (wheel balance)
# weight segments, the user's own: 19 x 16 x 4mm. The cells open on the
# mounting face, so bolting the tent on traps the weights against the case
# bottom (their own adhesive can hold them in the cell too). Ribs between
# cells keep the printed bridges to one cell's width.
TENT_WEIGHT_CELLS = (3, 3)         # front to back, across; (0, 0): no tray
TENT_WEIGHT_L = 16.0               # segment side front to back
TENT_WEIGHT_W = 19.0               # segment side across it
TENT_WEIGHT_T = 4.0                # segment height
TENT_WEIGHT_G = 7.0                # grams per segment, for the console (1/4 oz)
TENT_WEIGHT_CLEAR = 0.2            # each cell this much bigger all round
TENT_WEIGHT_DEPTH_CLEAR = 0.4      # and this much deeper than a segment
TENT_WEIGHT_RIB = 2.0              # between cells (JLC3DP's 2mm minimum)
TENT_WEIGHT_WALL = 2.0             # tray walls and floor
TENT_WEIGHT_DESK_CLEAR = 2.0       # tray's underside kept this far off the desk
                                    # plane (the rubber feet add 1.2mm more)

TENT_RUBBER_D = RUBBER_FOOT_D      # the same rubber feet as the case bottom,
TENT_RUBBER_H = RUBBER_FOOT_H      # in the same size recess on each leg end
TENT_RUBBER_CLEAR = RUBBER_RECESS_CLEAR
TENT_RUBBER_RECESS = RUBBER_RECESS
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
MAT_PUNCH_D = 10.0                 # hollow-punch size for the holes: 2mm all
                                    # round each 6mm boss (0.5mm, the first
                                    # mat, left butyl smearing onto the bosses
                                    # as it went in, 2026-10-21). The tent
                                    # screws no longer reach the floor top, so
                                    # the mat goes over them
MAT_BOSS_HOLE_D = MAT_PUNCH_D
MAT_PIN_MARGIN = 1.5               # mat kept this far off the through-hole
                                    # parts' footprints: their pins poke out
                                    # under the PCB, right over the foil
MAT_MIN_WIDTH = 2.0                # strips narrower than this are dropped
MAT_TEMPLATE_T = 0.6               # printed tracing template thickness
MAT_LABEL_H = 0.6                  # side label raised this far off the template
MAT_LABEL_SIZE = 10.0              # "LEFT"/"RIGHT" font size; "FOIL SIDE"
MAT_LABEL_SUB_SIZE = 4.0           # under it, so the label reads backwards
                                    # when the template's flipped for tracing
                                    # on the backing paper
MAT_LABEL_MARGIN = 2.0             # label kept this far inside the mat
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


def polygonize(sk, max_dev=0.01):
    """A one-face sketch as a straight-sided polygon: lines kept as they
    are, curves split into chords no more than `max_dev` off the curve.
    Edges are chained by their end points rather than trusting their
    order or direction (see dxf_to_loops.py)."""
    faces = sk.faces()
    assert len(faces) == 1 and not faces[0].inner_wires(), "polygonize takes one face with no holes"
    chains = []
    for e in faces[0].outer_wire().edges():
        if e.geom_type == b3d.GeomType.LINE:
            n = 1
        else:
            r = e.radius if e.geom_type == b3d.GeomType.CIRCLE else 1.0
            step = 2 * math.acos(max(1 - max_dev / r, -1.0)) * r     # chord length at that deviation
            n = max(2, math.ceil(e.length / step))
        chains.append([(v.X, v.Y) for v in (e @ (i / n) for i in range(n + 1))])
    loop = chains.pop(0)
    while chains:
        for i, c in enumerate(chains):
            if math.dist(c[0], loop[-1]) < 1e-4:
                loop += c[1:]
            elif math.dist(c[-1], loop[-1]) < 1e-4:
                loop += c[-2::-1]
            else:
                continue
            chains.pop(i)
            break
        else:
            raise AssertionError("polygonize: outline edges don't chain into one loop")
    assert math.dist(loop[0], loop[-1]) < 1e-4, "polygonize: outline is not closed"
    out = poly(loop[:-1])
    # chords cut across curves, so up to max_dev times the outline's length
    # can go (concave curves add it back instead)
    assert abs(out.area - sk.area) <= max_dev * faces[0].outer_wire().length, f"polygonize: area {out.area:.3f} vs {sk.area:.3f}"
    return out


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


def close_holes(sk, radius, within):
    """Morphological closing of a sketch's openings: each hole loses any
    notch narrower than 2*radius and gets rounded corners; a hole that small
    all over fills in. Only the openings inside it are touched -- the empty
    space between it and `within`'s edge (the case outline) is left alone.

    The openings are found as the empty faces of `within - sk` that don't
    reach `within`'s edge, and each is opened on its own, as a face with no
    holes: fusing `sk` first leaves overlapping faces unmerged, b3d.offset()
    offsets those separately, and on a face with holes that splits into
    pieces it hits a build123d 0.13 bug ('Face' object has no attribute
    'unwrap')."""
    out = sk
    for g in (within - sk).faces():
        if g.inner_wires():
            continue
        gap = b3d.Sketch() + g
        grown = b3d.offset(gap, amount=0.2, kind=b3d.Kind.ARC)
        if overlap(grown, within) < grown.area - 0.01:
            continue                         # reaches the outline: not an opening
        try:
            fill = gap - open_sketch(gap, radius)
        except (RuntimeError, ValueError):
            fill = gap                       # gone entirely when eroded
        out = out + fill
    return out


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


def board_envelope(side, data):
    """The plate's outer edge, and grown by CAVITY_CLEARANCE the case
    cavity's: straight along the pinky side, the MCU side and the bottom,
    straight across each column's top (so the top still steps with the
    column stagger), and a convex hull round the angled thumb keys. It
    holds everything the case used to trace -- the PCB outline and every
    switch's and plate mounting hole's reinforcement patch -- so nothing
    loses clearance; only the scallops and notches between them fill in.

    Not the cover-post holes' patches: they're in the plate's MCU opening,
    so there's no plate there to reinforce. Until 2026-10-26 those patches,
    and the old plate's MCU-strip footprint (a reset hole and patches from
    when the plate covered that strip), held the MCU-side edge 1.5mm out
    past the PCB -- a 2.0mm gap to the wall where everywhere else has 0.5,
    and a cover window sitting off-centre over the Pro Micro."""
    keys = data["keys"]
    left = side == "left"
    _, post_holes = mcu_zone(side, data)
    post_xy = {(h["x"], h["y"]) for h in post_holes}
    plate_holes = [h for h in data["m2_holes"] if (h["x"], h["y"]) not in post_xy]
    traced = poly(data["outline"]) + key_reinforcement_sketch(keys, plate_holes)

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


def cover_outline(side, data):
    """The MCU covers' outline before the case wall and its notches clip
    it: the MCU zone less every keycap, straightened on the key side. Left
    at that, the key side had two nubs: a tab over the wall top past the
    straight run beside the keys, and a tooth between the angled thumb
    keycap and the column keycap above it. So the outline is cut at the
    straight key-side edge, and at the angled keycap's edge run on until
    it meets that. Returns the outline and what the cut took off, which
    the plate fills instead. Needs no case geometry, so the plate can use
    it too."""
    zone_bb, _ = mcu_zone(side, data)
    caps = keycap_sketch(data["keys"], COVER_KEYCAP_CLEARANCE)
    raw = open_sketch(rect_from_bb(zone_bb) - caps, 0.6)
    raw = max(raw.faces(), key=lambda f: f.area)
    cx, cy = bbox_center(part_by_type(data["parts"], "ProMicro_v3")["bbox"])
    key_dir = -1 if side == "left" else 1  # the keys lie this way (in x) from the MCU strip
    big = 500.0

    # key-side edge: where the keycaps start, level with the Pro Micro
    ray = b3d.Pos(cx + key_dir * big / 2, cy, 0) * b3d.Rectangle(big, 0.2)
    hit = (ray & caps).bounding_box()
    x_edge = hit.min.X if key_dir > 0 else hit.max.X
    past_edge = b3d.Pos(x_edge + key_dir * big / 2, cy, 0) * b3d.Rectangle(big, 2 * big)

    # angled keycap edge: the outline's longest slanted straight run, as a
    # half-plane on the side away from the Pro Micro
    slanted = [
        e for e in raw.edges()
        if e.geom_type == b3d.GeomType.LINE and min(abs(e.tangent_at(0).X), abs(e.tangent_at(0).Y)) > 0.1
    ]
    assert slanted, f"{side}: no angled keycap edge on the cover outline"
    edge = max(slanted, key=lambda e: e.length)
    assert edge.length > 10, f"{side}: the cover's longest slanted edge is only {edge.length:.1f}mm"
    p0, d = edge.position_at(0), edge.tangent_at(0)
    n = b3d.Vector(-d.Y, d.X)
    if (b3d.Vector(cx, cy) - p0).dot(n) > 0:
        n = -n
    corners = [p0 + d * big, p0 - d * big, p0 - d * big + n * big, p0 + d * big + n * big]
    past_angled = poly([(p.X, p.Y) for p in corners])

    out = max((raw - past_edge - past_angled).faces(), key=lambda f: f.area)
    trimmed = raw - out
    assert trimmed.area < 40, (
        f"{side}: straightening the cover took off {trimmed.area:.1f}mm^2 -- expected two small nubs"
    )
    return out, trimmed


def plate_mount_holes(side, data, plate_sk):
    """M2 holes where the plate can be screwed down with a spacer, not just
    rest on the switches: the plate actually has a clearance hole there
    (some don't -- too close to a neighboring switch hole), and it isn't a
    cover post (those sit in the MCU opening, where there's no plate)."""
    _, post_holes = mcu_zone(side, data)
    post_xy = {(h["x"], h["y"]) for h in post_holes}
    holes = []
    for h in data["m2_holes"]:
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
        posts.append((h["x"], h["y"], od))
        web = web + b3d.Pos(h["x"], h["y"], 0) * b3d.Circle(od / 2)
    faces = web.faces()
    fused = faces[0]
    for f in faces[1:]:
        fused = fused + f
    pieces = fused.faces()
    main = max(pieces, key=lambda f: f.area)
    for (x, y, od) in posts:
        assert overlap(main, b3d.Pos(x, y, 0) * b3d.Circle(0.5)) > 0.7, (
            f"{side}: spacer frame post at ({x:.1f},{y:.1f}) isn't joined to the rest of the frame"
        )

    frame = extrude_up(main, 0.0, height)
    for (x, y, od) in posts:
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
    return frame, {"height": height, "posts": len(posts), "area": main.area, "dropped": stray}


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

    # ---- bosses under the PCB M2 holes ----
    boss_positions = []
    for h in data["m2_holes"]:
        x, y = h["x"], h["y"]
        boss = b3d.Pos(x, y, FLOOR_T) * b3d.Cylinder(
            radius=BOSS_OD / 2, height=BOSS_H, align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN)
        )
        case = case + boss
        boss_positions.append((x, y))
    for h in data["m2_holes"]:
        x, y = h["x"], h["y"]
        bore = b3d.Pos(x, y, boss_top_z - INSERT_DEPTH) * b3d.Cylinder(
            radius=INSERT_BORE_D / 2, height=INSERT_DEPTH + 0.5,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )
        case = case - bore

    usb_part = part_by_type(parts, "ProMicro_v3")
    trrs_part = part_by_type(parts, "MJ-4PP-9_1side")

    usb_cx, _ = bbox_center(usb_part["bbox"])
    usb_floor_z = pcb_top_z + USB_SOCKET_BOTTOM - NOTCH_CLEARANCE
    assert boss_top_z <= usb_floor_z < pcb_top_z, f"{side}: USB notch floor ({usb_floor_z:.2f}) doesn't close the gap under the PCB"
    trrs_axis_z = pcb_top_z + TRRS_AXIS_ABOVE_PCB
    trrs_floor_z = trrs_axis_z - TRRS_NOTCH_W / 2
    assert FLOOR_T + 1.0 < trrs_floor_z < pcb_top_z, f"{side}: TRRS notch floor ({trrs_floor_z:.2f}) is out of range"

    usb_wall_hit = scan_wall_crossing(outer_sk, lambda t: (usb_cx, t), 5, 60)
    assert usb_wall_hit is not None, f"{side}: couldn't find the outer wall near the USB connector (x={usb_cx:.1f})"
    usb_wall_y = usb_wall_hit[1]
    y0, y1 = usb_wall_y - 3.0, usb_wall_y + 12.0  # generous past the wall band; a no-op once inside the cavity
    usb_notch = b3d.Pos(usb_cx, (y0 + y1) / 2, usb_floor_z) * b3d.Box(
        USB_NOTCH_W, y1 - y0, wall_top_z - usb_floor_z + 1.0,
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
    trrs_notch = b3d.Pos((x0 + x1) / 2, trrs_cy, trrs_axis_z) * (
        b3d.Box(
            x1 - x0, TRRS_NOTCH_W, wall_top_z - trrs_axis_z + 1.0,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )
        + b3d.Rot(0, 90, 0) * b3d.Cylinder(radius=TRRS_NOTCH_W / 2, height=x1 - x0)
    )
    case = case - trrs_notch
    pcb_at_jack = poly(data["outline"]) & rect_from_bb((ob[0] - 1, trrs_cy - 0.05, ob[2] + 1, trrs_cy + 0.05))
    pb = pcb_at_jack.bounding_box()
    trrs_grip_x = pb.max.X + TRRS_GRIP_FROM_PCB_EDGE if is_left else pb.min.X - TRRS_GRIP_FROM_PCB_EDGE

    # Ground-truth check: confirm each notch actually opened the wall it was
    # aimed at, and that the opposite wall is still solid -- this is what
    # would have caught scan_wall_crossing() returning the scan parameter
    # instead of the probed coordinate (the TRRS notch silently cut the
    # wrong wall on the left half, and no wall at all on the right half).
    outer_bb = outer_sk.bounding_box()
    notch_z = (pcb_top_z + wall_top_z) / 2

    def assert_material(x, y, present, label, z=notch_z):
        probe = b3d.Pos(x, y, z) * b3d.Box(0.6, 0.6, 0.6)
        vol = (case & probe).volume
        if present:
            assert vol > 0.05, f"{side}: {label} at ({x:.1f},{y:.1f}) has no wall material -- expected solid wall here"
        else:
            assert vol < 0.01, f"{side}: {label} at ({x:.1f},{y:.1f}) still has wall material -- notch didn't open here"

    usb_notch_x, usb_notch_y = usb_cx, (y0 + y1) / 2
    assert_material(usb_notch_x, usb_notch_y, False, "USB notch")
    # the wall under each notch, where the PCB's underside is
    under_z = boss_top_z - 0.3
    assert_material(usb_cx, usb_wall_y + WALL_T / 2, True, "wall under the USB notch", under_z)

    trrs_notch_x, trrs_notch_y = (x0 + x1) / 2, trrs_cy
    trrs_opposite_x = outer_bb.min.X + WALL_T / 2 if is_left else outer_bb.max.X - WALL_T / 2
    assert_material(trrs_notch_x, trrs_notch_y, False, "TRRS notch")
    trrs_wall_mid_x = trrs_wall_x - WALL_T / 2 if is_left else trrs_wall_x + WALL_T / 2
    assert_material(trrs_wall_mid_x, trrs_cy, True, "wall under the TRRS notch", trrs_floor_z - 0.4)
    # the U's sides come up past the PCB's underside beyond the grip's middle
    for dy in (-1, 1):
        y = trrs_cy + dy * (TRRS_NOTCH_W / 2 - 0.4)
        assert_material(trrs_wall_mid_x, y, True, "wall at the TRRS notch's side", under_z)
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
    # A rubber-foot recess in the bottom at each corner, for a case with
    # no tent; a tent's flat mounting face just covers them.
    for (x, y) in foot_positions:
        case = case - b3d.Pos(x, y, -0.1) * b3d.Cylinder(
            radius=FOOT_D / 2, height=RUBBER_RECESS + 0.1,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )
    # The tent's inserts, pressed in from below flush with the bottom. The
    # hole runs through the floor: the insert is shorter than it, and the
    # screw stops inside the insert, so nothing reaches the cavity.
    tent_tall, tent_screws = tent_leg_layout(side, outer_sk, foot_positions)
    for (x, y) in tent_screws:
        case = case - b3d.Pos(x, y, -0.1) * b3d.Cylinder(
            radius=INSERT_BORE_D / 2, height=FLOOR_T + 0.2,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )

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
    assert INSERT_DEPTH <= FLOOR_T, f"the tent's {INSERT_DEPTH}mm insert is longer than the {FLOOR_T}mm floor"
    for (sx, sy) in tent_screws:
        assert_clear_of_wall(sx, sy, INSERT_BORE_D / 2, 2.0, "tent insert")
        for (fx, fy) in foot_positions:
            gap = math.hypot(sx - fx, sy - fy) - FOOT_D / 2 - INSERT_BORE_D / 2
            assert gap >= 1.5, f"{side}: tent insert at ({sx:.1f},{sy:.1f}) is {gap:.1f}mm from a foot recess"

    def case_solid_at(x, y, z):
        return overlap(case, b3d.Pos(x, y, z) * b3d.Box(0.4, 0.4, 0.4), "volume") > 0.03

    for (fx, fy) in foot_positions:
        assert not case_solid_at(fx, fy, RUBBER_RECESS / 2), f"{side}: foot recess at ({fx:.1f},{fy:.1f}) is not open"
        assert case_solid_at(fx, fy, RUBBER_RECESS + 0.4), f"{side}: foot recess at ({fx:.1f},{fy:.1f}) is too deep"
    for (sx, sy) in tent_screws:
        for z in (0.3, INSERT_DEPTH / 2, FLOOR_T - 0.3):
            assert not case_solid_at(sx, sy, z), f"{side}: tent insert hole at ({sx:.1f},{sy:.1f}) is blocked at z {z}"
        assert case_solid_at(sx + INSERT_BORE_D / 2 + 0.5, sy, FLOOR_T / 2), f"{side}: no floor round the tent insert at ({sx:.1f},{sy:.1f})"

    metrics = {
        "wall_top_z": wall_top_z,
        "boss_top_z": boss_top_z,
        "pcb_top_z": pcb_top_z,
        "foot_positions": foot_positions,
        "tent_tall": tent_tall,
        "tent_screws": tent_screws,
        "boss_positions": boss_positions,
        "cavity_sk": cavity_sk,
        "outer_sk": outer_sk,
        # the USB-end wall's outer face beside the USB notch, and which way
        # (in y) it lies from the board
        "usb_wall_y": usb_wall_y,
        "usb_dir": 1 if usb_wall_y > usb_part["pos"][1] else -1,
        "notch_bbs": [
            (usb_cx - USB_NOTCH_W / 2, y0, usb_cx + USB_NOTCH_W / 2, y1),
            (x0, trrs_cy - TRRS_NOTCH_W / 2, x1, trrs_cy + TRRS_NOTCH_W / 2),
        ],
        "trrs_notch_bb": (x0, trrs_cy - TRRS_NOTCH_W / 2, x1, trrs_cy + TRRS_NOTCH_W / 2),
        # the plugged-in cable's grip: where it starts (x), which way it runs
        # (out of the case), its axis
        "trrs_grip": (trrs_grip_x, 1 if is_left else -1, trrs_cy, trrs_axis_z),
    }
    return case, metrics


# ----------------------------------------------------------------------
# Floor mat template
# ----------------------------------------------------------------------
def build_floor_mat(side, data, case, metrics):
    """Outline of the sound-deadening mat on the case floor: the cavity
    pulled in from the wall, with holes round the bosses, and kept off the
    MCU strip's through-hole pins. Returned in
    KiCad's frame like everything else; the caller exports it."""
    mat = b3d.offset(metrics["cavity_sk"], amount=-MAT_EDGE_CLEARANCE, kind=b3d.Kind.ARC)
    pins = bbox_union([part_by_type(data["parts"], t)["bbox"] for t in MCU_ZONE_PARTS], margin=MAT_PIN_MARGIN)
    # Open once before the holes: the MCU cut leaves a ~0.6mm strip along
    # the wall, and a 10mm boss hole cuts it loose as its own face, which
    # b3d.offset() throws on instead of eroding away.
    mat = open_sketch(mat - rect_from_bb(pins), MAT_MIN_WIDTH / 2)
    for x, y in metrics["boss_positions"]:
        mat = mat - b3d.Pos(x, y) * b3d.Circle(MAT_BOSS_HOLE_D / 2)
    # A hole can still cut a crumb off a corner (0.4mm^2 by the MCU strip);
    # offset() throws on those too, so drop them by area first.
    mat = b3d.Sketch() + [f for f in mat.faces() if f.area > (2 * MAT_MIN_WIDTH) ** 2]
    mat = open_sketch(mat, MAT_MIN_WIDTH / 2)
    assert mat.area > 0, f"{side}: floor mat came out empty"

    # Ground truth is the case solid itself: a mat of the real thickness,
    # lying on the floor, must not touch the walls or bosses.
    mat_solid = extrude_up(mat, FLOOR_T, MAT_T)
    clash = overlap(mat_solid, case, "volume")
    assert clash < 0.01, f"{side}: floor mat intersects the case ({clash:.2f}mm^3)"
    return mat, {"pieces": len(mat.faces()), "area": mat.area}


def mat_label(side, phys_mat):
    """'LEFT'/'RIGHT' over 'FOIL SIDE', in the real-world frame, at the spot
    nearest the mat's middle where the whole label (plus a margin) lies
    on the mat -- the two templates look alike, and one first build came
    out as two lefts."""
    label = b3d.Sketch() + [
        b3d.Pos(0, MAT_LABEL_SUB_SIZE / 2 + 1) * b3d.Text(side.upper(), MAT_LABEL_SIZE),
        b3d.Pos(0, -MAT_LABEL_SIZE / 2) * b3d.Text("FOIL SIDE", MAT_LABEL_SUB_SIZE),
    ]
    bb = label.bounding_box()
    w, h = bb.size.X + 2 * MAT_LABEL_MARGIN, bb.size.Y + 2 * MAT_LABEL_MARGIN
    label = b3d.Pos(-bb.center().X, -bb.center().Y) * label
    mbb = phys_mat.bounding_box()
    mid = mbb.center()  # a mirrored Sketch reports center() as the origin
    spots = [(mbb.min.X + i * 2.0, mbb.min.Y + j * 2.0)
             for i in range(int(mbb.size.X / 2) + 1) for j in range(int(mbb.size.Y / 2) + 1)]
    spots.sort(key=lambda p: math.dist(p, (mid.X, mid.Y)))
    for x, y in spots:
        box = b3d.Pos(x, y) * b3d.Rectangle(w, h)
        if overlap(box, phys_mat) > box.area - 0.01:
            return b3d.Pos(x, y) * label
    raise AssertionError(f"{side}: no room on the floor mat for its {w:.0f}x{h:.0f}mm label")


def export_floor_mat(side, mat):
    """Tracing template: a thin print plus a DXF for paper. Unlike the
    plate DXF, both are mirrored into the real-world frame, so the
    template reads right side up laid on the mat's foil (top) face. The
    label is raised on the print and on its own layer in the DXF, so
    nobody cuts along it."""
    phys = to_physical(mat)
    label = mat_label(side, phys)
    # to_physical() is a mirror, so it also takes the label back to KiCad's
    # frame, where write() expects everything
    template = extrude_up(mat, 0, MAT_TEMPLATE_T) + extrude_up(to_physical(label), MAT_TEMPLATE_T, MAT_LABEL_H)
    write(template, f"mat-template-{side}", indent="  ")
    dxf_path = os.path.join(OUT_DIR, f"mat-template-{side}.dxf")
    exp = b3d.ExportDXF()
    exp.add_shape(phys)
    exp.add_layer("label")
    exp.add_shape(label, layer="label")
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


def tent_leg_layout(side, outer_sk, feet):
    """Which legs are the tall ones, and where each leg's screw goes. Shared
    by build_case (the inserts) and build_tent (the platforms).

    The TENT_TALL_LEGS legs farthest from the outer edge are the tall ones.
    A screw goes TENT_SCREW_OFFSET from its leg toward the middle of the
    four -- except beside a tall leg, whose screw goes along the inner edge
    instead, and TENT_PLUMB_SCREW_IN in: with TENT_PLUMB a tall leg's lower
    end leans right under the spot toward the middle and would block the
    driver (and the user liked them there either way)."""
    is_left = side == "left"
    obb = outer_sk.bounding_box()
    pivot_x = obb.min.X if is_left else obb.max.X
    by_reach = sorted(range(len(feet)), key=lambda i: abs(feet[i][0] - pivot_x), reverse=True)
    tall = set(by_reach[:TENT_TALL_LEGS])
    cx = sum(x for x, y in feet) / len(feet)
    cy = sum(y for x, y in feet) / len(feet)
    screws = []
    for i, (x, y) in enumerate(feet):
        if i in tall:
            screws.append((x + math.copysign(TENT_PLUMB_SCREW_IN, cx - x), y + math.copysign(TENT_SCREW_OFFSET, cy - y)))
        else:
            d = math.hypot(cx - x, cy - y)
            screws.append((x + (cx - x) / d * TENT_SCREW_OFFSET, y + (cy - y) / d * TENT_SCREW_OFFSET))
    return tall, screws


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

    With TENT_PLUMB the tall inner pair lean in toward the outer edge by
    `angle_deg`, along the desk's normal, so they stand plumb when the half
    sits on the desk; the short outer legs stay square to the case.

    Beside each leg is a platform at the mounting face, with a counterbored
    hole: an M2 screw goes up through it from below into an insert in the
    case floor (tent_leg_layout places them). Under each seat a column is
    kept clear down to the desk for the driver, so the tent comes off
    without opening the case."""
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

    # Each leg runs from the mounting face along its own axis: straight down
    # (case frame) or, for a plumb leg, along the desk's downward normal,
    # which leans toward the outer edge (the pivot). A plumb leg is a true
    # round cylinder about that axis, so its end on the desk is a full
    # TENT_FOOT_D circle and its top on the mounting face is an ellipse
    # 1/cos(angle) wider across the tilt.
    sin_a, cos_a = math.sin(math.radians(angle_deg)), math.cos(math.radians(angle_deg))
    dtdx = tan if is_left else -tan
    plumb_dir = (-sin_a if is_left else sin_a, 0.0, -cos_a)
    straight_dir = (0.0, 0.0, -1.0)
    screws = metrics["tent_screws"]
    plumb = metrics["tent_tall"] if TENT_PLUMB else set()
    leg_dirs = [plumb_dir if i in plumb else straight_dir for i in range(len(feet))]

    def to_desk(x, y, d):
        """Where the line from (x, y, 0) along d meets the desk plane."""
        # z = d.z*L = -t(x + d.x*L), and thickness is linear in x
        length = thickness(x) / (-d[2] - d[0] * dtdx)
        return (x + d[0] * length, y + d[1] * length, d[2] * length)

    def along(p, d, dist):
        return (p[0] + d[0] * dist, p[1] + d[1] * dist, p[2] + d[2] * dist)

    # ---- legs: round, clipped flush to the case's own outline ----
    # A plumb leg is not the pad extruded along its slant: that makes a
    # generic extrusion surface, which OCC tessellates into long slivers
    # (up to 48mm long, near-zero area) that show up as a pattern on the
    # leg. A real Cylinder tessellates in clean strips like the straight
    # legs. Its tilted top is trimmed at the mounting face, and its side
    # clipped by the case outline slid down the same slant, so the flat
    # where it meets the case edge stays plumb too. That outline goes in
    # as a polygon: its rounded corners slid along the slant would be the
    # same sliver-prone surface again. (A leg that leans in can't also keep
    # its width and stay on the case's edge: that edge leans 18° on the
    # desk. A flared one, plumb inside and on the edge outside, was tried
    # and turned down, 2026-10-23.)
    legs = None
    for (x, y), d in zip(feet, leg_dirs):
        if d is straight_dir:
            pad = (b3d.Pos(x, y, 0) * b3d.Circle(TENT_FOOT_D / 2)) & outer_sk
            leg = extrude_down(pad, max_t + 1.0)
        else:
            r = TENT_FOOT_D / 2
            rise = r * tan + 1.0             # top cap starts above z=0 all round
            length = (max_t + 1.0) / cos_a + rise
            cyl = b3d.Pos(x, y, 0) * b3d.Rot(0, angle_deg if is_left else -angle_deg, 0) * b3d.Cylinder(
                radius=r, height=length, align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MAX)
            )
            cyl = b3d.Pos(*along((0.0, 0.0, 0.0), d, -rise / cos_a)) * cyl
            region = polygonize((b3d.Pos(x, y, 0) * b3d.Circle(r / cos_a + 2.0)) & outer_sk)
            clip = b3d.extrude(region, amount=(max_t + 1.0) / cos_a, dir=d)
            leg = cyl & clip
            assert len(leg.solids()) == 1, f"{side}: plumb leg at ({x:.1f},{y:.1f}) came out in pieces"
            bb = leg.bounding_box()
            assert abs(bb.max.Z) < 1e-6 and bb.min.Z < -thickness(x), (
                f"{side}: plumb leg at ({x:.1f},{y:.1f}) landed at z {bb.min.Z:.3f}..{bb.max.Z:.3f}"
            )
        legs = leg if legs is None else legs + leg

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
        # wholly inside: a beam let 0.5% past the outline got that bit
        # clipped off by `frame_sk & outer_sk` below, leaving a notch in
        # its outer edge
        b = beam(p0, p1)
        return overlap(b, outer_sk) >= b.area - 0.01

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
    # The two sides (front to back) get a strip along the case's edge below
    # instead of a beam between leg centres.
    sides = [e for e in edges if e in segments and abs(e[1][0] - e[0][0]) <= abs(e[1][1] - e[0][1])]
    frame_sk = beam(*brace)
    for s in segments:
        if s not in sides:
            frame_sk = frame_sk + beam(*s)
    # ---- screw platforms: a stub from each leg out to its screw ----
    platform_r = TENT_SCREW_COLUMN_D / 2 + 2.0
    for foot, (sx, sy) in zip(feet, screws):
        frame_sk = frame_sk + beam(foot, (sx, sy)) + b3d.Pos(sx, sy) * b3d.Circle(platform_r)
    # ---- the two sides, front to back: flush with the case's edge ----
    # A plain beam between leg centres is narrower than the legs and, on the
    # inner side, runs diagonally away from the case's edge (which turns in
    # toward the thumb cluster). Instead each side is a strip of the case's
    # own outline, between its two legs, wide enough to reach past both
    # legs' centres by half a beam and to take in any screw platform that
    # sits along the side (a plumb leg's). Its inner edge runs parallel to
    # the case's edge, and it replaces the side's beam.
    pads2d = [(b3d.Pos(x, y) * b3d.Circle(TENT_FOOT_D / 2)) & outer_sk for x, y in feet]
    outline_wire = outer_sk.faces()[0].outer_wire()

    def to_outline(px, py):
        return outline_wire.distance_to(b3d.Vector(px, py, 0))

    for e in sides:
        (x0, y0), (x1, y1) = e
        el = length(e)
        tx_, ty_ = (x1 - x0) / el, (y1 - y0) / el
        nx, ny = -ty_, tx_
        if nx * (cx - x0) + ny * (cy - y0) > 0:
            nx, ny = -nx, -ny            # point outward
        width = max(to_outline(x0, y0), to_outline(x1, y1)) + TENT_FRAME_W / 2
        for (sx, sy) in screws:
            on_edge = (sx - x0) * tx_ + (sy - y0) * ty_
            inward = -((sx - x0) * nx + (sy - y0) * ny)
            if 0 <= on_edge <= el and inward + platform_r < TENT_FOOT_D / 2:
                width = max(width, to_outline(sx, sy) + platform_r)
        # between the two legs (lines through their centres, square to the
        # side), from past the strip's inner edge out past the case's edge
        between = poly([(x0 - nx * width * 2, y0 - ny * width * 2), (x1 - nx * width * 2, y1 - ny * width * 2),
                        (x1 + nx * 60, y1 + ny * 60), (x0 + nx * 60, y0 + ny * 60)])
        # The band round just this side's stretch of the case edge (offsetting
        # the whole outline would pull in the front and back edges' bands
        # too, and jog the tent's front edge out to the case's near each leg)
        ends = poly([(x0, y0), (x1, y1), (x1 + nx * 60, y1 + ny * 60), (x0 + nx * 60, y0 + ny * 60)])
        stretch = [oe for oe in outline_wire.edges()
                   if overlap(b3d.Pos(*tuple(oe @ 0.5)[:2]) * b3d.Circle(0.05), ends) > 0]
        stretch = max(b3d.Wire.combine(stretch), key=lambda w: w.length)
        band = b3d.Sketch() + b3d.Face(b3d.offset(stretch, amount=width, kind=b3d.Kind.ARC).wires()[0])
        frame_sk = frame_sk + (band & outer_sk & between)
    frame_sk = frame_sk & outer_sk

    # ---- weight tray: a band across the middle, beam to beam ----
    # Centred on the brace but square to the case (front to back), not
    # along the brace: the brace leans a few degrees, and a band following
    # it looked like it pointed toward the front. Its ends run to the front
    # and back beams' centrelines, following the back beam's bend, so it
    # merges into the frame without poking out past it. Its floor is flat in
    # the case's frame and the desk plane rises toward the outer edge, so
    # the band slides toward the tall side if its shallow corner would come
    # within TENT_WEIGHT_DESK_CLEAR of the desk.
    tray_pts, cells = None, []
    n_along, n_across = TENT_WEIGHT_CELLS
    if n_along and n_across:
        ux, uy = 0.0, 1.0               # along: front to back
        vx, vy = 1.0, 0.0               # across

        def rect(rcx, rcy, w, l):
            return [(rcx + sl * ux * l / 2 + sw * vx * w / 2, rcy + sl * uy * l / 2 + sw * vy * w / 2)
                    for sl, sw in ((1, 1), (1, -1), (-1, -1), (-1, 1))]

        cell_l = TENT_WEIGHT_L + 2 * TENT_WEIGHT_CLEAR
        cell_w = TENT_WEIGHT_W + 2 * TENT_WEIGHT_CLEAR
        pocket_d = TENT_WEIGHT_T + TENT_WEIGHT_DEPTH_CLEAR
        grid_l = n_along * cell_l + (n_along - 1) * TENT_WEIGHT_RIB
        grid_w = n_across * cell_w + (n_across - 1) * TENT_WEIGHT_RIB
        tray_d = pocket_d + TENT_WEIGHT_WALL
        tray_w = grid_w + 2 * TENT_WEIGHT_WALL
        tx, ty = midpoint(brace)
        need = tray_d + TENT_WEIGHT_DESK_CLEAR
        low = min(thickness(tx + sw * tray_w / 2) for sw in (-1, 1))
        tx += max(0.0, (need - low) / tan) * (1 if is_left else -1)
        centrelines = poly([sg[0] for sg in segments])   # the beams' centre path round the frame
        tray_sk = poly(rect(tx, ty, tray_w, 400.0)) & centrelines
        assert len(tray_sk.faces()) == 1, f"{side}: weight tray came out in pieces"
        tray_pts = [(v.X, v.Y) for v in tray_sk.vertices()]
        for i in range(n_along):
            for j in range(n_across):
                a = (i - (n_along - 1) / 2) * (cell_l + TENT_WEIGHT_RIB)
                b = (j - (n_across - 1) / 2) * (cell_w + TENT_WEIGHT_RIB)
                cells.append(rect(tx + ux * a + vx * b, ty + uy * a + vy * b, cell_w, cell_l))
        assert min(thickness(x) for x, _ in tray_pts) >= need - 1e-6, f"{side}: weight tray comes within {TENT_WEIGHT_DESK_CLEAR}mm of the desk"
        assert overlap(tray_sk, outer_sk) >= tray_sk.area - 0.01, f"{side}: weight tray leaves the case's footprint"
        for c in cells:
            walled = b3d.offset(poly(c), amount=TENT_WEIGHT_WALL, kind=b3d.Kind.INTERSECTION)
            assert overlap(walled, tray_sk) >= walled.area - 0.01, (
                f"{side}: a weight cell comes within {TENT_WEIGHT_WALL}mm of the tray's end -- the beams are too close for {n_along} rows"
            )

    # ---- frame: rounded, then extruded ----
    # Morphological closing of the frame's openings, over the beams, leg
    # tops and weight tray together: it fills every notch narrower than
    # 2*TENT_FILLET_R and rounds the openings' corners. The outer boundary
    # (sides already flush, see above) is left alone, and the tray keeps its
    # own (deeper) rectangle under it.
    closing = frame_sk
    for pad in pads2d:
        closing = closing + pad
    if tray_pts:
        closing = closing + tray_sk
    closed = close_holes(closing, TENT_FILLET_R, outer_sk) & outer_sk
    assert overlap(closed, closing) >= closing.area - 0.5, f"{side}: rounding the frame lost material"
    frame = extrude_down(closed, TENT_FRAME_T)
    if plumb:
        # The frame's face along the inner edge leans in with the plumb
        # legs, flush with their outer flats: dropped straight down it stood
        # 1.3mm proud of them at its underside, a ledge beside each leg.
        # Clipped by the case outline slid down the legs' slant; on the outer
        # side that slide moves the outline away from the frame, so only the
        # inner side is cut. As a polygon, for the same reason as the legs.
        frame = frame & b3d.extrude(polygonize(outer_sk), amount=(TENT_FRAME_T + 1.0) / cos_a, dir=plumb_dir)
    tent = legs + frame
    if tray_pts:
        tent = tent + extrude_down(tray_sk, tray_d)

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
    for c in cells:
        tent = tent - b3d.Pos(0, 0, 0.1) * extrude_down(poly(c), pocket_d + 0.1)

    # ---- screw holes: through the platform, and a clear column under it ----
    # The column may cut a beam or the platform's own underside, never a leg.
    for (sx, sy) in screws:
        column = b3d.Pos(sx, sy, -TENT_SCREW_SEAT) * b3d.Cylinder(
            radius=TENT_SCREW_COLUMN_D / 2, height=max_t + 2.0,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MAX),
        )
        clash = overlap(column, legs, "volume")
        assert clash < 0.01, f"{side}: the driver column under the tent screw at ({sx:.1f},{sy:.1f}) runs into a leg ({clash:.2f}mm^3)"
        if tray_pts:
            assert overlap(b3d.Pos(sx, sy) * b3d.Circle(TENT_SCREW_COLUMN_D / 2), poly(tray_pts)) < 0.01, (
                f"{side}: the driver column at ({sx:.1f},{sy:.1f}) runs into the weight tray"
            )
        tent = tent - column - b3d.Pos(sx, sy, 0.1) * b3d.Cylinder(
            radius=TENT_SCREW_CLEARANCE_D / 2, height=TENT_SCREW_SEAT + 0.2,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MAX),
        )

    # ---- rubber-foot recesses, into the desk face of each leg ----
    # Same Pos*Rot*shape as the desk cut, so the recess floor is parallel to
    # the desk plane and the recess goes in square to it.
    assert TENT_RUBBER_H - TENT_RUBBER_RECESS >= 1.0, "rubber foot would barely stand proud of its recess"
    recess_r = (TENT_RUBBER_D + TENT_RUBBER_CLEAR) / 2
    # On a plumb leg the recess is placed on the pad and carried down the
    # leg's axis to the desk, so it keeps the same rim as on a straight leg.
    recess_centres = []
    for (x, y), ld in zip(feet, leg_dirs):
        d = math.hypot(cx - x, cy - y)
        rx, ry = x + (cx - x) / d * TENT_RUBBER_SHIFT, y + (cy - y) / d * TENT_RUBBER_SHIFT
        recess_centres.append((rx, ry))
        qx, qy, qz = to_desk(rx, ry, ld)
        tent = tent - b3d.Pos(qx, qy, qz) * b3d.Rot(0, angle_deg if is_left else -angle_deg, 0) * b3d.Pos(
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
    top_probes = leg_probes + [midpoint(s) for s in segments]
    if tray_pts:
        # middle of each tray side, 1mm in from it, and the ribs between
        # neighbouring cells
        for sw in (-1, 1):
            top_probes.append((tx + sw * (tray_w / 2 - 1.0), ty))
        centres = [(sum(x for x, _ in c) / 4, sum(y for _, y in c) / 4) for c in cells]
        for k, (ax, ay) in enumerate(centres):
            for (bx, by) in centres[k + 1:]:
                if math.hypot(bx - ax, by - ay) < max(cell_l, cell_w) + TENT_WEIGHT_RIB + 0.1:
                    top_probes.append(((ax + bx) / 2, (ay + by) / 2))
    else:
        top_probes.append(midpoint(brace))
        bx, by = midpoint(brace)
        assert void_at(bx, by, -TENT_FRAME_T - 0.5), f"{side}: brace is thicker than TENT_FRAME_T"
    for (px, py) in top_probes:
        assert solid_at(px, py, -0.3), f"{side}: tent has no material under its mounting face at ({px:.1f},{py:.1f})"
        assert void_at(px, py, 0.3), f"{side}: tent sticks up past its mounting face at ({px:.1f},{py:.1f})"
    # each weight cell: open from the mounting face to its depth at the
    # middle and every corner, a full floor under it, nothing under that
    for c in cells:
        ccx = sum(x for x, _ in c) / 4
        ccy = sum(y for _, y in c) / 4
        for (px, py) in [(ccx, ccy)] + [(x + (ccx - x) * 0.05, y + (ccy - y) * 0.05) for x, y in c]:
            for z in (0.3, -0.3, -pocket_d / 2, -pocket_d + 0.3):
                assert void_at(px, py, z), f"{side}: weight cell blocked at ({px:.1f},{py:.1f},{z:.1f})"
            assert solid_at(px, py, -pocket_d - TENT_WEIGHT_WALL / 2), f"{side}: no tray floor under ({px:.1f},{py:.1f})"
            assert void_at(px, py, -tray_d - 0.5), f"{side}: tray floor at ({px:.1f},{py:.1f}) is thicker than {TENT_WEIGHT_WALL}mm"
    # every leg ends exactly on the desk plane (probed on the rim beside the
    # rubber-foot recess), and the recess is open to its depth and no deeper.
    # Probes are placed on the pad, carried down the leg's own axis, and
    # step along that axis -- square to the desk on a plumb leg.
    for (x, y), (rx, ry), ld in zip(feet, recess_centres, leg_dirs):
        d = math.hypot(cx - rx, cy - ry)
        px, py = rx + (cx - rx) / d * (recess_r + 1.2), ry + (cy - ry) / d * (recess_r + 1.2)
        assert math.hypot(px - x, py - y) < TENT_FOOT_D / 2 - 0.5, f"{side}: no rim left beside the recess at ({x:.1f},{y:.1f})"
        q = to_desk(px, py, ld)
        assert solid_at(*along(q, ld, -0.6)), f"{side}: leg at ({q[0]:.1f},{q[1]:.1f}) stops short of the desk plane"
        assert void_at(*along(q, ld, 0.6)), f"{side}: leg at ({q[0]:.1f},{q[1]:.1f}) pokes below the desk plane"
        q = to_desk(rx, ry, ld)
        assert void_at(*along(q, ld, -TENT_RUBBER_RECESS / 2)), f"{side}: rubber-foot recess at ({q[0]:.1f},{q[1]:.1f}) is not open"
        assert solid_at(*along(q, ld, -TENT_RUBBER_RECESS - 0.5)), f"{side}: rubber-foot recess at ({q[0]:.1f},{q[1]:.1f}) is too deep"
    # a plumb leg really is plumb: its axis is the desk's normal. Probe its
    # centre line at a few heights, its inner face (material just inside the
    # leaning cylinder's side, none just past it), and just beside its top
    # centre toward the edge low down, where a straight leg would still be.
    normal = (-dtdx, 0.0, -1.0)
    n = math.hypot(*normal)
    for i in plumb:
        (x, y), ld = feet[i], leg_dirs[i]
        assert sum(a * b / n for a, b in zip(ld, normal)) > 1 - 1e-9, f"{side}: plumb leg at ({x:.1f},{y:.1f}) is off the desk normal"
        bottom = to_desk(x, y, ld)
        span = math.dist((x, y, 0.0), bottom)
        for f in (0.3, 0.6, 0.9):
            px, py, pz = along((x, y, 0.0), ld, span * f)
            assert solid_at(px, py, pz), f"{side}: plumb leg at ({x:.1f},{y:.1f}) has no material on its axis at z {pz:.1f}"
        inward = -1 if is_left else 1       # toward the tent's middle
        for f in (0.3, 0.6, 0.9):
            px, py, pz = along((x, y, 0.0), ld, span * f)
            face_x = px + inward * TENT_FOOT_D / 2 / cos_a   # the leaning cylinder's inner side at this z
            assert solid_at(face_x - inward * 0.6, py, pz), f"{side}: leg at ({x:.1f},{y:.1f}) has no inner face at z {pz:.1f}"
            assert void_at(face_x + inward * 0.6, py, pz), f"{side}: leg at ({x:.1f},{y:.1f}) bulges past its plumb inner face at z {pz:.1f}"
        px, py, pz = along((x, y, 0.0), ld, span * 0.9)
        assert void_at(x - inward * 1.0, y, pz), f"{side}: leg at ({x:.1f},{y:.1f}) still runs straight down"

    # each platform: hole open through it, seat under it for the head, and
    # the column below clear all the way to the desk
    seat_r = (TENT_SCREW_CLEARANCE_D / 2 + TENT_SCREW_COLUMN_D / 2) / 2
    for (sx, sy) in screws:
        assert void_at(sx, sy, -TENT_SCREW_SEAT / 2), f"{side}: tent screw hole at ({sx:.1f},{sy:.1f}) is not open"
        assert solid_at(sx + seat_r, sy, -TENT_SCREW_SEAT + 0.3), f"{side}: no platform for the screw head at ({sx:.1f},{sy:.1f})"
        assert void_at(sx, sy, 0.3), f"{side}: platform at ({sx:.1f},{sy:.1f}) sticks up past the mounting face"
        column = b3d.Pos(sx, sy, -TENT_SCREW_SEAT - 0.05) * b3d.Cylinder(
            radius=TENT_SCREW_COLUMN_D / 2 - 0.05, height=max_t + 2.0,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MAX),
        )
        assert overlap(tent, column, "volume") < 0.001, f"{side}: driver column under ({sx:.1f},{sy:.1f}) is not clear"
    # the screw: head on the platform's seat, up into the case's insert,
    # stopping inside it (the insert is flush with the case bottom)
    engagement = TENT_SCREW_LEN - TENT_SCREW_SEAT
    assert engagement <= INSERT_DEPTH, f"M2x{TENT_SCREW_LEN:.0f} runs out the top of the case's {INSERT_DEPTH}mm insert"
    assert engagement >= 2.5, f"M2x{TENT_SCREW_LEN:.0f} only reaches {engagement:.1f}mm into the case's insert"

    info = {
        "angle_deg": angle_deg,
        "span": abs(far_x - pivot_x),
        "leg_heights": [(x, y, round(thickness(x), 2)) for (x, y) in feet],
        # (x, y, how far in its end sits from the top, how tall it stands)
        "plumb_legs": [(feet[i][0], feet[i][1], abs(to_desk(*feet[i], leg_dirs[i])[0] - feet[i][0]),
                        -to_desk(*feet[i], leg_dirs[i])[2] / cos_a) for i in sorted(plumb)],
        "max_thickness": max_t,
        "screw_engagement": engagement,
        "weight": tray_pts and {
            "cells": len(cells),
            "cell": (cell_w, cell_l, pocket_d),
            "tray": (tray_w, tray_sk.bounding_box().size.Y, tray_d),
        },
    }
    return tent, info


# ----------------------------------------------------------------------
# MCU cover
# ----------------------------------------------------------------------
def grip_cut(metrics):
    """Where a cover over the wall has to give way to the TRRS cable's
    grip: the wall notch's width, from NOTCH_CLEARANCE inside where the
    grip starts out past the case."""
    gx, out, cy, _ = metrics["trrs_grip"]
    nx0, ny0, nx1, ny1 = metrics["trrs_notch_bb"]
    start = gx - out * NOTCH_CLEARANCE
    return rect_from_bb((start, ny0, nx1, ny1) if out > 0 else (nx0, ny0, start, ny1))


def bb_of_sketch(sk):
    b = sk.bounding_box()
    return (b.min.X, b.min.Y, b.max.X, b.max.Y)


def trrs_grip_solid(metrics):
    """The plugged-in TRRS cable's grip, as TRRS_PLUG_D across (the largest
    the wall notch is sized for): a cylinder on the jack's axis from where
    the grip starts, out past the case."""
    gx, out, cy, axis_z = metrics["trrs_grip"]
    length = 20.0
    return b3d.Pos(gx + out * length / 2, cy, axis_z) * b3d.Rot(0, 90, 0) * b3d.Cylinder(
        radius=TRRS_PLUG_D / 2, height=length
    )


def cover_footprint(side, data, metrics):
    """Outline shared by both MCU covers: cover_outline() out to the wall's
    outer edge -- but not over the USB/TRRS notches (a plug's overmold
    stands taller than the cover's underside there). cover_outline() keeps
    it from under every keycap (a pressed keycap's skirt comes down lower
    than the cover's top). Returns that outline, the part of it on the
    wall top, the post holes and the plate sketch."""
    _, post_holes = mcu_zone(side, data)
    wall_full = metrics["outer_sk"] - metrics["cavity_sk"]
    wall_sk = wall_full   # the wall top the rim can rest on: not over a notch
    for nb in metrics["notch_bbs"]:
        wall_sk = wall_sk - rect_from_bb(nb)
    # The cover is cut back only where the TRRS cable's grip comes in under
    # it -- 1mm, since the wall came in (2026-10-26) -- flush with the
    # notch's sides, which already carry the plug's clearance. It runs
    # straight across the USB notch: only the socket and the plug's shell
    # are in there (the grip stays outside), 3.5mm up at most, well under
    # the cover's 6.0mm underside.
    notches = [grip_cut(metrics)]
    limit = (metrics["cavity_sk"] + wall_full) - notches[0]
    # At the USB end, stop at the outer face of the wall beside the USB
    # notch, all the way across. Past the Pro Micro on the key side the
    # wall steps out to the next column, and following it up the step left
    # a rounded tab on the cover's corner (removed 2026-10-22, the user's
    # call) where the other corner just stops at this line.
    y, d = metrics["usb_wall_y"], metrics["usb_dir"]
    limit = limit & rect_from_bb((-500.0, min(y, y - d * 500.0), 500.0, max(y, y - d * 500.0)))
    cover_sk = cover_outline(side, data)[0] & limit
    # Drop anything too narrow to print and keep the one real piece. The
    # opening that finds those also rounds every outside corner by 0.6mm,
    # which flared the cover's notch edges wider than the case's sharp ones
    # right at the outer face (2026-10-24, the user's catch at the TRRS
    # notch). So the corners round each notch go back in from the original
    # outline. Only there: everywhere else the opening also smooths away a
    # 0.007mm jog in the outline that OCC can't offset past.
    kept = max(open_sketch(cover_sk, 0.6).faces(), key=lambda f: f.area)
    by_notches = None
    for (nx0, ny0, nx1, ny1) in [bb_of_sketch(n) for n in notches]:
        ring = rect_from_bb((nx0 - 1.0, ny0 - 1.0, nx1 + 1.0, ny1 + 1.0)) - rect_from_bb((nx0, ny0, nx1, ny1))
        by_notches = ring if by_notches is None else by_notches + ring
    cover_sk = b3d.Sketch() + kept + (cover_sk & by_notches & b3d.offset(b3d.Sketch() + kept, amount=0.6, kind=b3d.Kind.ARC))
    cover_sk = max(cover_sk.faces(), key=lambda f: f.area)
    plate_sk, _ = build_plate_sketch(side, data)
    # The rim runs the full wall width along the USB end, edge to edge: at
    # the key-side corner the cover's edge is over the plate's edge and the
    # gap to the wall, not the wall, and the rim stopped 0.9mm short there,
    # a step in the underside. It rests on the plate's top, level with the
    # wall top.
    band = rect_from_bb((-500.0, min(y, y - d * WALL_T), 500.0, max(y, y - d * WALL_T)))
    for nb in metrics["notch_bbs"]:
        band = band - rect_from_bb(nb)
    # ...and off the parts under the cover where it leaves the wall
    for t in PART_HEIGHTS:
        band = band - rect_from_bb(part_by_type(data["parts"], t)["bbox"])
    rim_sk = cover_sk & (wall_sk + band)
    return cover_sk, rim_sk, post_holes, plate_sk


def cover_footprint_inset(side, data, metrics):
    """The inset cover's outline (2026-10-25, the user's idea): the same
    cover, stopped at the plate's outer edge (board_envelope) instead of run
    out over the wall, so its top is a straight-edged panel with no notch
    steps. Its underside is 1mm above the wall top, so the USB end would
    hang on the two posts alone: a 45 degree bevel from its top edge runs
    down onto the wall top, wherever that edge faces the wall
    (inset_bevel). A flat lip there first (2026-10-25) needed supports:
    printed top-down, it stuck out 2mm with nothing under it. Returns the
    outline, the bevel's footprint on the wall, the post holes and the
    plate sketch, like cover_footprint(), plus where the bevel may go."""
    _, post_holes = mcu_zone(side, data)
    env = board_envelope(side, data)
    cover_sk = cover_outline(side, data)[0] & env
    cover_sk = max(open_sketch(cover_sk, 0.6).faces(), key=lambda f: f.area)
    plate_sk, _ = build_plate_sketch(side, data)
    # where the bevel may go: from just in under the cover's edge out to
    # the case's outer face -- on the wall side only, never through a notch
    # in the wall (a plug's overmold passes there) or under a keycap
    in_wall = metrics["outer_sk"] - metrics["cavity_sk"]
    band = metrics["outer_sk"] - b3d.offset(env, amount=-COVER_INSET_BEVEL_IN, kind=b3d.Kind.ARC)
    band = band - keycap_sketch(data["keys"], COVER_KEYCAP_CLEARANCE)
    for nb in metrics["notch_bbs"]:
        band = band - (rect_from_bb(nb) & in_wall)
    rim_sk = band & in_wall & inset_bevel_clip(side, cover_sk, metrics)
    return cover_sk, rim_sk, post_holes, plate_sk, band


def inset_bevel_clip(side, cover_sk, metrics):
    """The bevel's reach: out to the case's outer face, but only along the
    cover's own length -- it ends square with the cover's key-side edge and
    its TRRS end rather than running on round the wall."""
    b = cover_sk.bounding_box()
    big = 50.0
    if side == "left":
        return rect_from_bb((b.min.X, b.min.Y - big, b.max.X + big, b.max.Y))
    return rect_from_bb((b.min.X - big, b.min.Y - big, b.max.X, b.max.Y))


def reset_access(side, data, cover_sk, bevel=False):
    """Paperclip access to the reset switch through a cover: a hole,
    joined to the OLED window when it sits just past the window's side
    (rather than leave a sliver of cover between them), or opened out to
    the cover's inner edge as a slot when it's too near that edge for a
    printable wall. With bevel=True (the inset cover) the 45 degree bevel
    outside that edge thickens the wall going down -- by COVER_T/2 at the
    cover's mid-thickness -- and the wall is judged there: its 1.5mm at the
    top face is 2.5mm half-way down. A slot there first (2026-10-26) cut
    the frame round the window right through on the inner side, leaving a
    40mm strip hanging from the USB end (the user's catch). Returns the cut
    and whether it's a slot."""
    parts = data["parts"]
    window_bb = bbox_union([oled_module_bb(parts)], margin=OLED_WINDOW_CLEAR)
    rx, ry = part_by_type(parts, "ResetSW_1side")["pos"]
    r = COVER_RESET_HOLE_D / 2
    hole = b3d.Pos(rx, ry, 0) * b3d.Circle(r)
    cut = hole
    if max(window_bb[0] - rx, 0, rx - window_bb[2]) - r < COVER_MIN_WALL:
        cut = cut + rect_from_bb((min(rx, window_bb[2]), ry - r, max(rx, window_bb[0]), ry + r))
    wall = hole.faces()[0].outer_wire().distance_to(cover_sk.outer_wire()) + (COVER_T / 2 if bevel else 0.0)
    if wall >= CLEAR_BASE_WALL_T:
        return cut, False
    out = rx + (50.0 if side == "left" else -50.0)
    return cut + rect_from_bb((min(rx, out), ry - r, max(rx, out), ry + r)), True


def inset_bevel(side, data, metrics, cover_sk, band, wall_top_z, under_z, top_z):
    """The inset cover's bevel: a 45 degree slope from the cover's top
    edge down to the wall top. The cover's top is h = top_z - wall_top_z
    above the wall, and its edge is h in from the case's outer face (the
    0.5mm gap plus the 2.5mm wall), so the slope lands right on that face.
    Built as a frustum on the cover's outline box (straight, with mitred
    corners), trimmed to the band and the cover's length. Printed top-down,
    it grows outward at 45 degrees from the bed: no supports."""
    h = top_z - wall_top_z
    b = cover_sk.bounding_box()
    base = rect_from_bb((b.min.X - h, b.min.Y - h, b.max.X + h, b.max.Y + h))
    frustum = b3d.Pos(0, 0, wall_top_z) * b3d.extrude(base, amount=h, taper=45)
    top = frustum.faces().sort_by(b3d.Axis.Z)[-1].bounding_box()
    assert abs(top.size.X - b.size.X) < 0.05 and abs(top.size.Y - b.size.Y) < 0.05, (
        f"{side}: the bevel's frustum top is {top.size.X:.2f} x {top.size.Y:.2f}, "
        f"not the cover's {b.size.X:.2f} x {b.size.Y:.2f} (taper went the wrong way?)"
    )
    reach = band & inset_bevel_clip(side, cover_sk, metrics)
    # not across the reset slot, and no piece under 2mm wide left between
    # it and a notch (JLC3DP's minimum feature; a 1.3mm wedge was left
    # between the slot and the TRRS notch)
    reset_cut, slot = reset_access(side, data, cover_sk, bevel=True)
    if slot:
        reach = reach - reset_cut
    kept = b3d.Sketch()
    for f in reach.faces():
        try:
            piece = open_sketch(b3d.Sketch() + f, CLEAR_BASE_WALL_T / 2)
        except RuntimeError:
            # OCC can't offset the long L-shaped main run (round the corner,
            # down to the slot); it's 4mm wide all along, so keep it whole
            piece = b3d.Sketch() + f
        if piece.faces() and piece.area > 1.0:
            kept = kept + piece
    assert kept.faces(), f"{side}: the inset cover's bevel came out empty"
    bevel = frustum & (b3d.Pos(0, 0, wall_top_z) * b3d.extrude(kept, amount=h))
    # clear of the parts under the cover's edge: the TRRS jack's top is
    # level with the wall top, right where the bevel starts. Inside the
    # cavity only: the Pro Micro's bbox includes its USB connector's
    # overhang past the board edge, and unclipped it cut a slit through the
    # bevel along the whole USB end, over the wall (the notch handles the
    # connector)
    for t in PART_HEIGHTS:
        bb = bbox_union([part_by_type(data["parts"], t)["bbox"]], margin=MCU_OPENING_MARGIN)
        bevel = bevel - extrude_up(rect_from_bb(bb) & metrics["cavity_sk"], wall_top_z - 1.0, under_z - wall_top_z + 1.0)
    return bevel


def add_cover_posts(side, cover, cover_sk, post_holes, plate_sk, pcb_sk, pcb_top_z, under_z, top_z):
    """Posts from the PCB up to the cover's underside at each post hole,
    with the screw hole run through the whole cover."""
    # posts stand through the plate's level, so keep them off its edge
    plate_clear = b3d.offset(plate_sk, amount=MCU_OPENING_MARGIN, kind=b3d.Kind.ARC)
    for h in post_holes:
        post_sk = (b3d.Pos(h["x"], h["y"], 0) * b3d.Circle(COVER_POST_OD / 2)) & cover_sk
        post_sk = post_sk - plate_clear
        # and stop at the PCB's edge: the lower post's hole is 2.6mm in from
        # it, and since the wall came in to 0.5mm off the PCB (2026-10-26)
        # a round post would touch it
        post_sk = post_sk & pcb_sk
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
    return cover


def oled_module_bb(parts):
    """Where the plugged-in OLED module lies: over the Pro Micro, its
    pin-side edge OLED_PIN_EDGE past the pin row -- the placement the
    KiCad footprint gives its 3D model."""
    pads = part_by_type(parts, "OLED_1side")["pads"]
    cx = sum(p["pos"][0] for p in pads) / len(pads)
    edge_y = sum(p["pos"][1] for p in pads) / len(pads) + OLED_PIN_EDGE
    return (cx - OLED_MODULE_W / 2, edge_y - OLED_MODULE_L, cx + OLED_MODULE_W / 2, edge_y)


def build_clear_cover(side, data, case, metrics):
    """Two-piece alternative to build_cover, after the original crkbd's
    acrylic OLED cover: a printed base -- a wall round the same footprint --
    under a flat clear top over the whole MCU strip. In place of
    build_cover's printed posts, an M2 male-female hex standoff at each
    post hole threads through the PCB into the insert and clamps the PCB;
    the clear top screws onto the standoffs and holds the base down on the
    case wall. The OLED sits under it on its socket rather than on top, so
    the stack is much taller than build_cover's."""
    keys = data["keys"]
    parts = data["parts"]
    cavity_sk = metrics["cavity_sk"]
    pcb_top_z = metrics["pcb_top_z"]
    wall_top_z = metrics["wall_top_z"]
    under_z = pcb_top_z + CLEAR_UNDERSIDE_ABOVE_PCB
    top_z = under_z + CLEAR_T
    assert CLEAR_UNDERSIDE_ABOVE_PCB >= OLED_TOP_ABOVE_PCB + 0.5, "clear top is under 0.5mm over the OLED's glass"

    cover_sk, rim_sk, post_holes, plate_sk = cover_footprint(side, data, metrics)

    # base: a wall round the footprint, the full wall width where it sits on
    # the case wall, from the wall top up to the clear top
    try:
        inner_sk = b3d.offset(cover_sk, amount=-CLEAR_BASE_WALL_T, kind=b3d.Kind.INTERSECTION)
    except RuntimeError:
        # OCC's sharp-cornered offset trips on a couple of ~0.09mm edges in
        # the right half's outline since the wall came in (2026-10-26); the
        # rounded kind only rounds the base's inside corners
        inner_sk = b3d.offset(cover_sk, amount=-CLEAR_BASE_WALL_T, kind=b3d.Kind.ARC)
    ring_sk = (cover_sk - inner_sk) + rim_sk
    # Off the case wall, the wall crosses parts (the Pro Micro runs under its
    # key-side and USB-side runs), so there it starts above the tallest one.
    # That leaves the same 1mm gap over the plate's edge as build_cover's
    # underside. Stepping it down to the plate between parts left strips
    # under 2mm wide beside them.
    band_z = pcb_top_z + max(PART_HEIGHTS.values()) + CLEAR_PART_CLEARANCE
    assert wall_top_z < band_z < under_z, f"{side}: clear cover base band is out of order"
    # Clipped to the cavity: the Pro Micro's bbox includes its USB
    # connector's overhang past the board edge, which is the wall notch's
    # business
    part_boxes = {
        t: extrude_up(rect_from_bb(part_by_type(parts, t)["bbox"]) & cavity_sk, pcb_top_z, height)
        for t, height in PART_HEIGHTS.items()
    }
    # a collar round each standoff, from the band up
    hex_r = STANDOFF_HEX_AF / math.sqrt(3)  # across corners / 2
    hole_r = hex_r + STANDOFF_HOLE_CLEAR / 2
    wall_sk = ring_sk
    for h in post_holes:
        wall_sk = wall_sk + (b3d.Pos(h["x"], h["y"], 0) * b3d.Circle(hole_r + CLEAR_BASE_WALL_T) & cover_sk)
    # Below the TRRS notch the collar all but fills the wall's corner, and
    # left a closed slot ~1.4mm wide between itself and the rim. Fill every
    # pocket but the one big opening over the MCU strip.
    pockets = sorted((cover_sk - wall_sk).faces(), key=lambda f: f.area)
    filled = pockets[:-1]
    for f in filled:
        assert f.area < 30, f"{side}: clear cover base would fill a {f.area:.0f}mm^2 pocket"
        wall_sk = wall_sk + f
    base = extrude_up(wall_sk, band_z, under_z - band_z) + extrude_up(rim_sk, wall_top_z, band_z - wall_top_z)

    standoffs = []
    edge_gaps = []
    for h in post_holes:
        at = b3d.Pos(h["x"], h["y"], 0)
        cut = at * b3d.Circle(hole_r)
        # Both post holes sit under 1mm from the footprint's edge (the
        # key-side edge, the angled thumb-keycap edge): open the hole out
        # through the edge rather than leave a sliver of wall there
        c, p = b3d.Vertex(h["x"], h["y"], 0).closest_points(cover_sk.outer_wire())
        gap = (p - c).length - hole_r
        if gap < CLEAR_BASE_WALL_T:
            d = (p - c).normalized()
            reach = (p - c).length + 1.0
            cut = cut + b3d.Pos(h["x"] + d.X * reach / 2, h["y"] + d.Y * reach / 2, 0) * b3d.Rot(
                0, 0, math.degrees(math.atan2(d.Y, d.X))
            ) * b3d.Rectangle(reach, 2 * hole_r)
            edge_gaps.append(gap)
        base = base - extrude_up(cut, pcb_top_z - 1.0, under_z - pcb_top_z + 2.0)
        standoffs.append(extrude_up(at * b3d.Circle(hex_r), pcb_top_z, STANDOFF_L))

    # clear top: the whole footprint, with the screw holes and a paperclip
    # hole over the reset switch (beside the OLED module, not over it)
    rx, ry = part_by_type(parts, "ResetSW_1side")["pos"]
    clear_sk = cover_sk - (b3d.Pos(rx, ry, 0) * b3d.Circle(COVER_RESET_HOLE_D / 2))
    for h in post_holes:
        clear_sk = clear_sk - (b3d.Pos(h["x"], h["y"], 0) * b3d.Circle(COVER_SCREW_D / 2))
    clear = extrude_up(clear_sk, under_z, CLEAR_T)

    # the standoff's male thread goes through the PCB into the insert, whose
    # bore is blind: it can't run past the insert's bottom
    max_male = PCB_T + INSERT_DEPTH
    engagement = STANDOFF_MALE - PCB_T
    assert 2.0 <= engagement and STANDOFF_MALE <= max_male, (
        f"{side}: a {STANDOFF_MALE}mm standoff thread gets {engagement:.1f}mm into the insert "
        f"(needs 2.0mm or more, and at most {max_male:.1f}mm of thread)"
    )

    # ---- verification ----
    module_bb = oled_module_bb(parts)
    reset_to_module = max(module_bb[0] - rx, 0, rx - module_bb[2]) - COVER_RESET_HOLE_D / 2
    assert reset_to_module > 0, f"{side}: the clear top's reset hole is over the OLED module"
    for label, solid in (("base", base), ("clear top", clear)):
        assert solid.is_valid, f"{side}: clear cover {label} is not valid"
        assert len(solid.solids()) == 1, f"{side}: clear cover {label} came out as {len(solid.solids())} pieces"
        clash = overlap(solid, case, "volume")
        assert clash < 0.01, f"{side}: clear cover {label} intersects the case ({clash:.2f}mm^3)"
        hit = overlap(solid, trrs_grip_solid(metrics), "volume")
        assert hit < 0.01, f"{side}: a {TRRS_PLUG_D:.0f}mm TRRS grip would hit the clear cover {label} ({hit:.2f}mm^3)"
        for t, box in part_boxes.items():
            hit = overlap(solid, box, "volume")
            assert hit < 0.01, f"{side}: clear cover {label} collides with {t} ({hit:.2f}mm^3)"
    # each standoff, as a cylinder over its hex corners, misses every part,
    # the case, the plate and the base
    for so in standoffs:
        for label, other in [("case", case), ("base", base)] + list(part_boxes.items()):
            hit = overlap(so, other, "volume")
            assert hit < 0.01, f"{side}: a clear cover standoff collides with the {label} ({hit:.2f}mm^3)"
        so_sk = so.faces().sort_by(b3d.Axis.Z)[0]
        assert overlap(plate_sk, so_sk) < 0.01, f"{side}: a clear cover standoff runs through the plate"
    assert overlap(cover_sk, keycap_sketch(keys, 0)) < 1e-6, f"{side}: clear cover runs under a keycap"
    assert rim_sk.area > 20, f"{side}: clear cover base has almost no rim on the wall top ({rim_sk.area:.1f}mm^2)"
    plate_top_z = pcb_top_z + PLATE_TOP_ABOVE_PCB
    thickest = max(POM_PLATE_T, FR4_PLATE_T, MJF_PLATE_T)
    plate = extrude_up(plate_sk, plate_top_z - thickest, thickest)
    clash = overlap(base, plate, "volume")
    assert clash < 0.01, f"{side}: clear cover base intersects the plate ({clash:.2f}mm^3)"
    # the plugged-in OLED, from 0.5mm under its board up to its glass top,
    # must clear the base wall (grown by 0.5mm round its sides) and the top
    oled_box = extrude_up(
        rect_from_bb(bbox_union([module_bb], margin=0.5)),
        pcb_top_z + OLED_BOARD_ABOVE_PCB - 0.5, OLED_TOP_ABOVE_PCB - OLED_BOARD_ABOVE_PCB + 0.5,
    )
    for label, solid in (("base", base), ("clear top", clear)):
        hit = overlap(solid, oled_box, "volume")
        assert hit < 0.01, f"{side}: clear cover {label} is within 0.5mm of the OLED module ({hit:.2f}mm^3)"
    seat = overlap(ring_sk, cover_sk)  # what the clear top rests on, before posts
    info = {
        "under_above_pcb": under_z - pcb_top_z,
        "top_above_pcb": top_z - pcb_top_z,
        "footprint_bb": cover_sk.bounding_box(),
        "base_h": under_z - wall_top_z,
        "seat_area": seat,
        "max_male": max_male,
        "engagement": engagement,
        "hole_d": 2 * hole_r,
        "edge_gaps": edge_gaps,
        "filled_pockets": [f.area for f in filled],
        "oled_gap": CLEAR_UNDERSIDE_ABOVE_PCB - OLED_TOP_ABOVE_PCB,
    }
    return base, clear, clear_sk, info


def export_clear_top(side, clear, clear_sk):
    """STL/STEP for a look, plus the DXF a laser-cutting shop takes. The DXF
    is in the real-world frame, read from above, like the mat template --
    a through-cut sheet's mirror image is the same part flipped over, but
    this way the drawing matches the board as you see it."""
    write(clear, f"cover-clear-{side}", indent="  ")
    dxf_path = os.path.join(OUT_DIR, f"cover-clear-{side}.dxf")
    exp = b3d.ExportDXF()
    exp.add_shape(to_physical(clear_sk))
    exp.write(dxf_path)
    print(f"  wrote {dxf_path}")


def build_cover(side, data, case, metrics, inset=False):
    """Flat cover over the MCU strip. Its rim rests on the case wall top
    along the board's top and inner edges; at the other end it stands on
    posts over the PCB mounting holes beside the TRRS jack, and one long
    screw per post goes through cover, post and PCB into the same
    heat-set insert an ordinary PCB screw would use. inset=True builds the
    optional inset cover instead: stopped at the plate's outline, resting
    on the wall top by a lip under its edge (cover_footprint_inset)."""
    keys = data["keys"]
    parts = data["parts"]
    cavity_sk = metrics["cavity_sk"]
    pcb_top_z = metrics["pcb_top_z"]
    wall_top_z = metrics["wall_top_z"]
    under_z = pcb_top_z + COVER_UNDERSIDE_ABOVE_PCB
    top_z = under_z + COVER_T
    assert under_z > wall_top_z, f"{side}: cover underside is below the wall top"

    if inset:
        cover_sk, rim_sk, post_holes, plate_sk, band = cover_footprint_inset(side, data, metrics)
        cover = b3d.Pos(0, 0, under_z) * b3d.extrude(cover_sk, amount=COVER_T)
        cover = cover + inset_bevel(side, data, metrics, cover_sk, band, wall_top_z, under_z, top_z)
    else:
        cover_sk, rim_sk, post_holes, plate_sk = cover_footprint(side, data, metrics)
        cover = b3d.Pos(0, 0, under_z) * b3d.extrude(cover_sk, amount=COVER_T)
        cover = cover + b3d.Pos(0, 0, wall_top_z) * b3d.extrude(rim_sk, amount=under_z - wall_top_z)
    # A skirt down onto the plate where the plate laps under the cover's
    # edge (the angled thumb-keycap side): the cover's underside is 1mm
    # above the plate's top, and from the keys you could see straight
    # under it between the posts (the user's catch, 2026-10-26). It rests
    # on the plate's top, level with the wall top, like the rim.
    rest = cover_sk & b3d.offset(plate_sk, amount=COVER_PLATE_REST_IN, kind=b3d.Kind.ARC)
    for t in PART_HEIGHTS:
        bb = bbox_union([part_by_type(parts, t)["bbox"]], margin=MCU_OPENING_MARGIN)
        rest = rest - (rect_from_bb(bb) & metrics["cavity_sk"])
    kept = b3d.Sketch()
    for f in (rest.faces() if rest is not None else []):
        try:
            piece = open_sketch(b3d.Sketch() + f, CLEAR_BASE_WALL_T / 2)
        except RuntimeError:
            piece = b3d.Sketch() + f
        if piece.faces() and piece.area > 1.0:
            kept = kept + piece
    if kept.faces():
        cover = cover + extrude_up(kept, wall_top_z, under_z - wall_top_z)
    plate_rest_area = kept.area if kept.faces() else 0.0
    cover = add_cover_posts(side, cover, cover_sk, post_holes, plate_sk, poly(data["outline"]), pcb_top_z, under_z, top_z)

    # OLED window: through the cover over the module's whole footprint, so
    # everything under the OLED stays in view. Plugged fully in, the
    # module's board sits only 0-1mm above the cover's top: a cover under it
    # held it up and its pins stopped short of seating (the 1mm pocket that
    # fixed that was replaced by this window, 2026-10-19). The module's own
    # pin header (plastic and all) drops through the window into the socket.
    module_bb = oled_module_bb(parts)
    window_bb = bbox_union([module_bb], margin=OLED_WINDOW_CLEAR)
    window_sk = rect_from_bb(window_bb)
    pads = part_by_type(parts, "OLED_1side")["pads"]
    pad_xs = [p["pos"][0] for p in pads]
    pad_ys = [p["pos"][1] for p in pads]
    header_sk = rect_from_bb((
        min(pad_xs) - OLED_SLOT_MARGIN_X, min(pad_ys) - OLED_SLOT_MARGIN_Y,
        max(pad_xs) + OLED_SLOT_MARGIN_X, max(pad_ys) + OLED_SLOT_MARGIN_Y,
    ))
    assert overlap(header_sk, window_sk) > header_sk.area - 0.01, f"{side}: OLED header doesn't pass the window"
    assert overlap(window_sk, cover_sk) > window_sk.area - 0.01, f"{side}: OLED window runs off the cover's edge"
    # what's left round it is the narrowest part of the cover
    window_wall = window_sk.faces()[0].outer_wire().distance_to(cover_sk.outer_wire())
    assert window_wall >= CLEAR_BASE_WALL_T, (
        f"{side}: only {window_wall:.2f}mm of cover between the OLED window and the cover's edge"
    )
    reset_sk, reset_slot = reset_access(side, data, cover_sk, bevel=inset)
    if not reset_slot:
        assert overlap(reset_sk, cover_sk) > reset_sk.area - 0.01, f"{side}: reset hole runs off the cover's edge"
    cover = cover - extrude_up(window_sk + reset_sk, wall_top_z - 1.0, top_z - wall_top_z + 2.0)

    # ---- verification ----
    assert cover.is_valid, f"{side}: cover solid is not valid"
    assert len(cover.solids()) == 1, f"{side}: cover came out as {len(cover.solids())} separate pieces"
    assert overlap(cover_sk, keycap_sketch(keys, 0)) < 1e-6, f"{side}: cover runs under a keycap"
    clash = overlap(cover, case, "volume")
    assert clash < 0.01, f"{side}: cover intersects the case ({clash:.2f}mm^3)"
    hit = overlap(cover, trrs_grip_solid(metrics), "volume")
    assert hit < 0.01, f"{side}: a {TRRS_PLUG_D:.0f}mm TRRS grip would hit the cover ({hit:.2f}mm^3)"
    if inset and not reset_slot:
        # the reset hole's thin top wall leans on the bevel: make sure it's there
        rx, ry = part_by_type(parts, "ResetSW_1side")["pos"]
        cb = cover_sk.bounding_box()
        edge_x = cb.max.X if side == "left" else cb.min.X
        out = 1 if side == "left" else -1
        probe = b3d.Pos(edge_x + out * 0.5, ry, under_z + COVER_T / 4) * b3d.Box(0.4, 2 * COVER_RESET_HOLE_D, 0.4)
        assert overlap(cover, probe, "volume") > 0.9 * probe.volume, (
            f"{side}: no bevel beside the reset hole to back up its {cb.max.X - rx:.1f}mm wall"
        )
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
    # the plugged-in OLED's board, from 0.5mm under its measured height up,
    # must clear the cover
    oled_box = extrude_up(rect_from_bb(module_bb), pcb_top_z + OLED_BOARD_ABOVE_PCB - 0.5, 3.0)
    hit = overlap(cover, oled_box, "volume")
    assert hit < 0.01, f"{side}: cover is under 0.5mm from the OLED's board ({hit:.2f}mm^3)"
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
        "window_bb": window_bb,
        "window_wall": window_wall,
        "reset_slot": reset_slot,
        "plate_rest_area": plate_rest_area,
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
    # not the cover-post holes: they're in the MCU opening cut below, so
    # there's no plate there (and since the plate's patch round them went,
    # 2026-10-26, the checks below would only report them as "skipped")
    _, cover_posts = mcu_zone(side, data)
    cover_post_xy = {(h["x"], h["y"]) for h in cover_posts}
    for h in data["m2_holes"]:
        if (h["x"], h["y"]) in cover_post_xy:
            continue
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
    # Keep the plate there instead, and where cover_outline() straightened
    # the cover's key side, reaching COVER_PLATE_LAP in under the cover,
    # but never over a part under the cover or round a cover post.
    cover, trimmed = cover_outline(side, data)
    keep = keycap_sketch(keys, COVER_KEYCAP_CLEARANCE + COVER_PLATE_LAP)
    for f in trimmed.faces():
        keep = keep + b3d.offset(f, amount=COVER_PLATE_LAP, kind=b3d.Kind.ARC)
    for t in MCU_ZONE_PARTS:
        keep = keep - rect_from_bb(bbox_union([part_by_type(parts, t)["bbox"]], margin=MCU_OPENING_MARGIN))
    # Round a post, stop at the cover's edge instead of lapping under it,
    # and build_cover trims the post to keep MCU_OPENING_MARGIN off the plate
    for h in post_holes:
        keep = keep - (b3d.Pos(h["x"], h["y"], 0) * b3d.Circle(COVER_POST_OD / 2 + MCU_OPENING_MARGIN) & cover)
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
        print(f"  spacer frame: {finfo['posts']} posts, each with a pilot, {finfo['height']:.1f}mm tall under a {tag} plate"
              + (f", dropped {dropped:.1f}mm2 of loose slivers" if dropped > 0.5 else ""))

        tent, tent_info = build_tent(side, data, metrics, TENT_ANGLE_DEG)
        clash = overlap(tent, case, "volume")
        assert clash < 0.01, f"{side}: tent intersects the case ({clash:.2f}mm^3)"
        write(tent, f"tent-{side}", indent="  ")
        print(f"  tent: {TENT_ANGLE_DEG:.0f}deg across the case's {tent_info['span']:.0f}mm width, "
              f"{TENT_MIN_T:.0f}mm thick at the outer edge, {tent_info['max_thickness']:.1f}mm at the inner edge")
        print(f"  tent legs ({TENT_FOOT_D:.0f}mm dia), height at each leg's centre: "
              f"{[(round(x,1), round(y,1), h) for x, y, h in tent_info['leg_heights']]}mm")
        for x, y, shift, tall in tent_info["plumb_legs"]:
            print(f"  tent leg at ({x:.1f},{y:.1f}) leans {TENT_ANGLE_DEG:.0f}deg to stand plumb: "
                  f"{tall:.1f}mm tall on the desk, its end {shift:.1f}mm in from straight below its top")
        if tent_info["weight"]:
            w = tent_info["weight"]
            print(f"  tent weight tray: {w['tray'][0]:.1f} x {w['tray'][1]:.1f}mm, {w['tray'][2]:.1f}mm below the case; "
                  f"{w['cells']} cells {w['cell'][0]:.1f} x {w['cell'][1]:.1f} x {w['cell'][2]:.1f}mm deep for "
                  f"{TENT_WEIGHT_W:.0f} x {TENT_WEIGHT_L:.0f} x {TENT_WEIGHT_T:.0f}mm tire weights, "
                  f"~{w['cells'] * TENT_WEIGHT_G:.0f}g full at {TENT_WEIGHT_G:.0f}g each")
        print(f"  tent screws: M2x{TENT_SCREW_LEN:.0f} up through each leg's platform, "
              f"{tent_info['screw_engagement']:.1f}mm into a {INSERT_DEPTH}mm insert in the case floor, at "
              f"{[(round(x, 1), round(y, 1)) for x, y in metrics['tent_screws']]}")

        cover, info = build_cover(side, data, case, metrics)
        write(cover, f"cover-{side}", indent="  ")
        inset, iinfo = build_cover(side, data, case, metrics, inset=True)
        write(inset, f"cover-inset-{side}", indent="  ")
        ib = iinfo["footprint_bb"]
        print(f"  inset cover (optional): {ib.size.X:.1f} x {ib.size.Y:.1f}mm inside the wall, 45deg bevel onto "
              f"the wall top ({iinfo['rim_area']:.0f}mm^2), {iinfo['window_wall']:.1f}mm round the OLED window, "
              f"reset {'slot' if iinfo['reset_slot'] else 'hole'}")
        fb = info["footprint_bb"]
        print(f"  cover: {fb.size.X:.1f} x {fb.size.Y:.1f}mm, top {info['top_above_pcb']:.1f}mm above the PCB, "
              f"{len(info['post_holes'])} posts at {[(round(x,1), round(y,1)) for x, y in info['post_holes']]}")
        print(f"  cover screws: head to boss top is {info['screw_grip']:.1f}mm -- an M2x12 leaves "
              f"{12 - info['screw_grip']:.1f}mm in the {INSERT_DEPTH}mm insert")
        wb = info["window_bb"]
        print(f"  OLED window: {wb[2] - wb[0]:.1f} x {wb[3] - wb[1]:.1f}mm through the cover, "
              f"{info['window_wall']:.1f}mm of cover left at its narrowest")

        base, clear, clear_sk, cinfo = build_clear_cover(side, data, case, metrics)
        write(base, f"cover-base-{side}", indent="  ")
        export_clear_top(side, clear, clear_sk)
        fb = cinfo["footprint_bb"]
        print(f"  clear cover: {fb.size.X:.1f} x {fb.size.Y:.1f}mm, {CLEAR_T}mm clear top from "
              f"{cinfo['under_above_pcb']:.1f} to {cinfo['top_above_pcb']:.1f}mm above the PCB "
              f"({cinfo['oled_gap']:.1f}mm over the OLED's glass); base {cinfo['base_h']:.1f}mm tall, "
              f"{cinfo['seat_area']:.0f}mm^2 of wall top under the clear top")
        print(f"  clear cover standoffs: M2 male-female, {STANDOFF_L:.0f}mm body, {STANDOFF_MALE:.0f}mm male "
              f"thread ({cinfo['engagement']:.1f}mm in the insert, {cinfo['max_male']:.1f}mm at most); "
              f"base holes {cinfo['hole_d']:.1f}mm, "
              f"for up to {STANDOFF_HEX_AF}mm hex; M2x{CLEAR_TOP_SCREW_LEN} on top")
        if cinfo["filled_pockets"]:
            print(f"  clear cover base: filled {len(cinfo['filled_pockets'])} closed pocket(s) in the wall, "
                  f"{[round(a, 1) for a in cinfo['filled_pockets']]}mm^2")
        if cinfo["edge_gaps"]:
            print(f"  clear cover base: {len(cinfo['edge_gaps'])} standoff hole(s) opened out through the edge "
                  f"(would have left {[round(g, 2) for g in cinfo['edge_gaps']]}mm of wall)")

    print("\nDone.")


if __name__ == "__main__":
    main()
