#!/usr/bin/env python3
"""Generate the cornison 3D-printed tray case + switch plates.

Reads board.json (produced by extract_board.py) and writes STEP/STL/DXF
into case/out/ for both halves:
  - case-{left,right}             the printed tray (screw the PCB to bosses)
  - plate-{pom,fr4ref}-{left,right}  switch-plate geometry (DXF + STEP + STL)

The plate extends over the whole MCU/OLED/reset area -- the Pro Micro is
soldered directly to the PCB (no access needed), and the OLED module plugs
into its header from above through a slot in the plate, sitting exposed on
top rather than hidden under a separate cover (Boardsource-Corne style).

Run with:
  uv run --with build123d python3 case.py

All dimensions are parameters below. This is a first-pass generator: the
MagSafe ring size is still worth double-checking against the real part
before ordering.
"""
import json
import math
import os

import build123d as b3d

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_JSON = os.path.join(HERE, "board.json")

# CASE_PROTOTYPE=1 skips the MagSafe recess (a 54mm bridge cut into the
# bottom face -- fine for a service printer, but an unsupported bridge
# that big will sag or need supports on a home FDM printer) and writes to
# out-prototype/ instead of out/, so a quick home-printer fit-check run
# never overwrites the real service-print files.
PROTOTYPE_MODE = os.environ.get("CASE_PROTOTYPE") == "1"
OUT_DIR = os.path.join(HERE, "out-prototype" if PROTOTYPE_MODE else "out")

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
PLATE_SHRINK = 0.5            # plate outline = half outline - this, so it drops into the cavity

OUTER_CORNER_ROUND = 3.0      # fillet radius used when rounding the outer case profile

BOSS_OD = 6.0
INSERT_BORE_D = 3.2           # McMaster 94459A767 (M2x0.4, 3.2mm installed
                               # length): "Drill Bit Size" / "For Maximum
                               # Hole Diameter" is 3.2mm -- a bigger hole
                               # gives the knurled insert nothing to bite into
INSERT_DEPTH = 3.2

KEY_HOLE = 14.0                # square switch cutout
M2_CLEARANCE_D = 2.3

USB_NOTCH_W = 12.0
TRRS_NOTCH_W = 9.0
NOTCH_MARGIN_Z = 0.0            # notches start right at the floor top

# No separate MCU cover: the Pro Micro is soldered directly to the PCB and
# the plate simply extends over it (Boardsource-Corne style). The OLED
# module plugs into a 4-pin header (OLED_1side) from above, through a slot
# cut in the plate, so it sits exposed on top of the plate -- no window,
# no separate cover part, nothing to solder for the display itself.
OLED_SLOT_MARGIN_X = 2.0        # margin added beyond the pin span, each end
OLED_SLOT_MARGIN_Y = 1.5        # margin added beyond the pin row, each side
RESET_HOLE_D = 3.0              # clearance hole so a paperclip can reach the switch
FAB_MIN_WALL = 2.2   # target minimum plate wall/connect width -- JLCPCB's FR4
                      # routing ask is >=2.0mm; this gives a bit of margin

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

PLATE_OPEN_RADIUS = 1.1    # the real board outline has ~20 tiny (<0.3mm wide,
                            # <1mm long) spike/tooth artifacts along otherwise
                            # straight edges -- likely noise from the original
                            # panel-split outline export. None of these are big
                            # enough to matter functionally, but they're well
                            # under any process's minimum feature size. A
                            # morphological opening (erode then regrow by this
                            # radius) clips off anything narrower than 2.2mm
                            # without needing per-spike coordinates

STL_TOLERANCE = 0.05       # mm, chordal deviation for STL export (0.001 default is overkill)
STL_ANGULAR_TOLERANCE = 0.25

FOOT_D = 8.0
FOOT_DEPTH = 1.0
FOOT_WALL_CLEARANCE = 1.5         # min wall thickness kept around every foot recess

MAGSAFE_OD = 54.10                # per Apple's published MagSafe ring spec
MAGSAFE_ID = 46.0
MAGSAFE_DEPTH = 2.0                # Apple's recommended ring thickness
MAGSAFE_FLOOR_BOOST = 2.0          # extra floor thickness under the ring zone,
                                    # so a 2mm-deep recess still leaves a solid floor

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


# ----------------------------------------------------------------------
# Case tray
# ----------------------------------------------------------------------
def build_case(side, data, plate_sk):
    outline = data["outline"]
    keys = data["keys"]
    m2_holes = data["m2_holes"]
    parts = data["parts"]
    ob = outline_bbox(outline)
    is_left = side == "left"

    wall_top_z = FLOOR_T + BOSS_H + PCB_T + PLATE_TOP_ABOVE_PCB  # flush with plate top
    boss_top_z = FLOOR_T + BOSS_H
    pcb_top_z = FLOOR_T + BOSS_H + PCB_T

    # Wrap the real plate too, not just the shared reinforcement patches:
    # the plate gets extra material (reset-hole patch, wider margins) that
    # the cavity otherwise never hears about, and the two drifted apart.
    cavity_sk = reinforced_cavity(outline, keys, m2_holes) + b3d.offset(
        plate_footprint(plate_sk), amount=CAVITY_CLEARANCE, kind=b3d.Kind.ARC
    )
    outer_sk = rounded_outer_sketch(cavity_sk, WALL_T)

    outer_solid = b3d.extrude(outer_sk, amount=wall_top_z)
    cavity_solid = b3d.Pos(0, 0, FLOOR_T) * b3d.extrude(
        cavity_sk, amount=wall_top_z - FLOOR_T + 1.0
    )
    case = outer_solid - cavity_solid

    # ---- bosses under the PCB M2 holes ----
    boss_positions = []
    for h in m2_holes:
        x, y = h["x"], h["y"]
        boss = b3d.Pos(x, y, FLOOR_T) * b3d.Cylinder(
            radius=BOSS_OD / 2, height=BOSS_H, align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN)
        )
        case = case + boss
        boss_positions.append((x, y))
    for h in m2_holes:
        x, y = h["x"], h["y"]
        bore = b3d.Pos(x, y, boss_top_z - INSERT_DEPTH) * b3d.Cylinder(
            radius=INSERT_BORE_D / 2, height=INSERT_DEPTH + 0.5,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )
        case = case - bore

    # ---- USB + TRRS wall notches ----
    # The real outline isn't a rectangle -- it has a stepped top edge, so a
    # notch position guessed as a fixed offset from the outline's bounding
    # box can land entirely outside the real wall (found exactly this: a
    # USB notch placed ~9mm off, cutting empty air while the real wall
    # nearby stayed solid, confirmed by slicing the exported STL and
    # finding an unbroken boundary where the notch was supposed to be).
    # Scan for where the actual wall is instead of assuming.
    def scan_wall_crossing(sk, probe_fn, lo, hi, step=0.1):
        n = int((hi - lo) / step)
        for i in range(n + 1):
            t = lo + i * step
            x, y = probe_fn(t)
            probe = b3d.Pos(x, y, 0) * b3d.Circle(0.05)
            if (sk & probe).area > 0.5 * probe.area:
                return t
        return None

    usb_part = part_by_type(parts, "ProMicro_v3")
    trrs_part = part_by_type(parts, "MJ-4PP-9_1side")

    usb_cx, _ = bbox_center(usb_part["bbox"])
    notch_h = wall_top_z - FLOOR_T + 1.0

    usb_wall_y = scan_wall_crossing(outer_sk, lambda t: (usb_cx, t), 5, 60)
    assert usb_wall_y is not None, f"{side}: couldn't find the outer wall near the USB connector (x={usb_cx:.1f})"
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
        trrs_wall_x = scan_wall_crossing(outer_sk, lambda t: (ob[2] + 15 - t, trrs_cy), 0, 30)
    else:
        trrs_wall_x = scan_wall_crossing(outer_sk, lambda t: (ob[0] - 15 + t, trrs_cy), 0, 30)
    assert trrs_wall_x is not None, f"{side}: couldn't find the outer wall near the TRRS jack (y={trrs_cy:.1f})"
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

    # ---- rubber feet recesses ----
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
    for (x, y) in foot_positions:
        foot = b3d.Pos(x, y, -0.1) * b3d.Cylinder(
            radius=FOOT_D / 2, height=FOOT_DEPTH + 0.1,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )
        case = case - foot

    # ---- MagSafe locating recess (simple disk pocket, not a true ring) ----
    # A 2mm-deep recess would only leave 0.5mm of floor (FLOOR_T=2.5) above
    # it, so first thicken the floor locally by adding a boss-like pad that
    # rises into the cavity, then cut the recess from the true bottom face --
    # net floor thickness under the ring ends up the same as everywhere else.
    # Skipped entirely in prototype mode: cutting it from the true bottom
    # face means an unsupported 54mm-diameter bridge starting at the very
    # first layer if printed floor-down (the normal, otherwise support-free
    # orientation for this shape) -- a service printer (MJF/SLA) handles
    # that fine, a home FDM printer generally won't, and it has no effect
    # on the PCB/plate fit-check a prototype print is actually for.
    key_xs = [k["x"] for k in data["keys"]]
    key_ys = [k["y"] for k in data["keys"]]
    magsafe_center = (sum(key_xs) / len(key_xs), sum(key_ys) / len(key_ys))
    if not PROTOTYPE_MODE:
        magsafe_boost = b3d.Pos(magsafe_center[0], magsafe_center[1], FLOOR_T) * b3d.Cylinder(
            radius=MAGSAFE_OD / 2 + 2.0, height=MAGSAFE_FLOOR_BOOST,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )
        case = case + magsafe_boost
        magsafe = b3d.Pos(magsafe_center[0], magsafe_center[1], -0.1) * b3d.Cylinder(
            radius=MAGSAFE_OD / 2, height=MAGSAFE_DEPTH + 0.1,
            align=(b3d.Align.CENTER, b3d.Align.CENTER, b3d.Align.MIN),
        )
        case = case - magsafe

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
        dist = math.hypot(fx - magsafe_center[0], fy - magsafe_center[1])
        assert dist > MAGSAFE_OD / 2 + 2, (
            f"{side}: foot at ({fx:.1f},{fy:.1f}) is only {dist:.1f}mm from "
            f"MagSafe centre, needs > {MAGSAFE_OD/2+2:.1f}mm"
        )

    if not PROTOTYPE_MODE:
        assert_clear_of_wall(magsafe_center[0], magsafe_center[1], MAGSAFE_OD / 2, 1.5, "MagSafe recess")

    metrics = {
        "wall_top_z": wall_top_z,
        "boss_top_z": boss_top_z,
        "pcb_top_z": pcb_top_z,
        "magsafe_center": magsafe_center,
        "foot_positions": foot_positions,
        "boss_positions": boss_positions,
    }
    return case, metrics


# ----------------------------------------------------------------------
# MCU cover
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# Plate (POM/FR4-agnostic polygon geometry)
# ----------------------------------------------------------------------
def build_plate_sketch(side, data):
    """Build the plate sketch, verifying each cut by comparing the area
    actually removed to the cutter's own nominal area -- if a hole is
    clipped by the plate boundary (too close to the edge), the boolean
    subtract removes less material than the cutter's full area, and this
    catches that directly instead of relying on a fragile bbox proxy.

    The plate extends over the whole MCU/OLED/reset area (the Pro Micro is
    soldered to the PCB and needs no access; the OLED module plugs into its
    header from above, through a slot in the plate, so it sits exposed on
    top rather than under a separate cover)."""
    outline = data["outline"]
    keys = data["keys"]
    m2_holes = data["m2_holes"]
    parts = data["parts"]

    plate_sk = offset_pts(outline, -PLATE_SHRINK)
    plate_sk = open_sketch(plate_sk, PLATE_OPEN_RADIUS)
    cavity_sk = reinforced_cavity(outline, keys, m2_holes)  # same shape build_case cuts into the walls

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

    # Reinforce every switch hole first (union in the same enlarged
    # footprints that went into `cavity_sk` above, so the case wall already
    # bulges out to match wherever this adds material) -- some corners
    # (the outermost, most-rotated thumb key) sit close enough to the raw
    # outline that a hole there would otherwise break out through the edge.
    plate_sk = plate_sk + key_reinforcement_sketch(keys, m2_holes)

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
    for h in m2_holes:
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
            print(f"  NOTE: {side} M2 hole at ({h['x']:.1f},{h['y']:.1f}) skipped on the plate -- "
                  f"cuts cleanly but a neighboring hole leaves under {FAB_MIN_WALL}mm of wall "
                  f"({ring_void:.2f}mm^2 of the safety margin already gone); no plate standoff "
                  f"there, PCB-to-case mounting is unaffected")
            continue

        plate_sk = test

    # extend the plate to cover the whole MCU/OLED/reset area (union, not a
    # relief cut), clipped to the case cavity like the reinforcement above.
    # Margin needs to be generous, not just cover the parts: the board's own
    # outline has a tight zigzag step right near this corner (same stepped
    # edge that caused the USB notch bug in build_case), and a too-small
    # margin leaves a sub-1mm plate sliver hugging that step. Verified 3.0mm
    # is enough to fully clear it; using a bit more for real margin.
    usb_part = part_by_type(parts, "ProMicro_v3")
    oled_part = part_by_type(parts, "OLED_1side")
    reset_part = part_by_type(parts, "ResetSW_1side")
    mcu_bb = bbox_union([usb_part["bbox"], oled_part["bbox"], reset_part["bbox"]], margin=3.5)
    mcx, mcy = bbox_center(mcu_bb)
    mw, mh = bbox_size(mcu_bb)
    mcu_fill = b3d.Pos(mcx, mcy, 0) * b3d.Rectangle(mw, mh)
    mcu_fill = mcu_fill & cavity_sk
    plate_sk = plate_sk + mcu_fill

    # OLED header slot: sized to the real 4-pin 2.54mm header pad span, not
    # to the module's display area -- the module plugs in from above and
    # sits exposed on top of the plate, so the plate only needs pin clearance
    pads = oled_part["pads"]
    pad_xs = [p["pos"][0] for p in pads]
    pad_ys = [p["pos"][1] for p in pads]
    slot_x0, slot_x1 = min(pad_xs) - OLED_SLOT_MARGIN_X, max(pad_xs) + OLED_SLOT_MARGIN_X
    slot_y0, slot_y1 = min(pad_ys) - OLED_SLOT_MARGIN_Y, max(pad_ys) + OLED_SLOT_MARGIN_Y

    # ...but the reset hole sits close enough to the OLED slot's own edge
    # (verified: as little as 0.35mm apart) that cutting both as originally
    # sized leaves another sub-1mm sliver between them. Clip the slot's edge
    # back if it would come within MIN_GAP of the reset hole, rather than
    # assuming the fixed margins never collide with a neighboring cutout.
    # 1.5 cleared JLC3DP's 1.0mm MJF minimum but left this the tightest spot
    # on the FR4 plate at ~1.3-1.5mm, under JLCPCB's stricter 2.0mm ask for
    # routing "connect"/tab width (they flagged it directly by email).
    rx, ry = reset_part["pos"]
    MIN_GAP = 2.2
    reset_r = RESET_HOLE_D / 2
    if slot_x1 > rx - reset_r - MIN_GAP > slot_x0:
        slot_x1 = rx - reset_r - MIN_GAP
    if slot_x0 < rx + reset_r + MIN_GAP < slot_x1:
        slot_x0 = rx + reset_r + MIN_GAP

    slot_cx, slot_cy = (slot_x0 + slot_x1) / 2, (slot_y0 + slot_y1) / 2
    slot_w, slot_h = slot_x1 - slot_x0, slot_y1 - slot_y0
    oled_slot = b3d.Pos(slot_cx, slot_cy, 0) * b3d.Rectangle(slot_w, slot_h)
    plate_sk = cut(plate_sk, oled_slot, slot_w * slot_h, f"OLED header slot ({side})", min_ratio=0.9)

    # reset access hole, centred on the switch's own footprint position
    # (its pads are offset by the -90deg rotation, so bbox-center is off).
    # mcu_fill is clipped to cavity_sk (& cavity_sk above) so it can't push
    # material past the true outline the way key_reinforcement_sketch does
    # for switch/M2 holes -- and the board happens to be narrow right where
    # this hole sits (found only ~1.4-1.5mm to the true edge, under
    # JLCPCB's 2.0mm "connect" ask). Give it its own unclipped reinforcement
    # patch, same technique as the switch holes, rather than relying on
    # mcu_fill to cover it.
    reset_patch = b3d.Pos(rx, ry, 0) * b3d.Circle(reset_r + RESET_REINFORCE_MARGIN)
    plate_sk = plate_sk + reset_patch
    reset_hole = b3d.Pos(rx, ry, 0) * b3d.Circle(reset_r)
    plate_sk = cut(plate_sk, reset_hole, math.pi * reset_r ** 2, f"reset hole ({side})", min_ratio=0.9)

    return plate_sk, mcu_bb


def export_plate(side, data, thickness, tag):
    sk, mcu_bb = build_plate_sketch(side, data)
    solid = b3d.extrude(sk, amount=thickness)
    assert solid.is_valid, f"{side} {tag} plate solid is not valid"

    step_path = os.path.join(OUT_DIR, f"plate-{tag}-{side}.step")
    stl_path = os.path.join(OUT_DIR, f"plate-{tag}-{side}.stl")
    dxf_path = os.path.join(OUT_DIR, f"plate-{tag}-{side}.dxf")
    phys = to_physical(solid)
    b3d.export_step(phys, step_path)
    b3d.export_stl(phys, stl_path, tolerance=STL_TOLERANCE, angular_tolerance=STL_ANGULAR_TOLERANCE)
    # The DXF stays in KiCad's frame: make_fr4_plate.py writes it straight
    # back into a KiCad project. (For a laser/CNC shop it doesn't matter
    # either way -- a flat through-cut plate's mirror image is the same
    # part flipped over.)
    exp = b3d.ExportDXF()
    exp.add_shape(sk)
    exp.write(dxf_path)
    print(f"  wrote {step_path}")
    print(f"  wrote {stl_path}")
    print(f"  wrote {dxf_path}")
    return sk, mcu_bb


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if PROTOTYPE_MODE:
        print(f"CASE_PROTOTYPE=1: skipping the MagSafe recess, writing to {OUT_DIR}/")
    board = load_board()

    for side in ("left", "right"):
        print(f"\n=== {side} ===")
        data = board[side]

        plate_sk, mcu_bb = export_plate(side, data, POM_PLATE_T, "pom")
        # FR4 geometry is the same polygon; also dump STEP/STL/DXF for
        # reference even though the real FR4 order uses make_fr4_plate.py.
        export_plate(side, data, FR4_PLATE_T, "fr4ref")
        export_plate(side, data, MJF_PLATE_T, "mjf")

        case, metrics = build_case(side, data, plate_sk)
        assert case.is_valid, f"{side}: case solid is not valid"

        case_step = os.path.join(OUT_DIR, f"case-{side}.step")
        case_stl = os.path.join(OUT_DIR, f"case-{side}.stl")
        phys = to_physical(case)
        b3d.export_step(phys, case_step)
        b3d.export_stl(phys, case_stl, tolerance=STL_TOLERANCE, angular_tolerance=STL_ANGULAR_TOLERANCE)
        print(f"  wrote {case_step}")
        print(f"  wrote {case_stl}")

        print(f"  stack: floor 0-{FLOOR_T}, boss top {metrics['boss_top_z']:.2f}, "
              f"PCB top {metrics['pcb_top_z']:.2f}, plate/wall top {metrics['wall_top_z']:.2f}")
        print(f"  MagSafe centre: ({metrics['magsafe_center'][0]:.1f}, {metrics['magsafe_center'][1]:.1f})")
        print(f"  MCU area covered by plate, bbox: {[round(v,1) for v in mcu_bb]}")

    print("\nDone.")


if __name__ == "__main__":
    main()
