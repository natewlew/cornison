# Cornison

Context for working on this repo. This file exists because the repo was
split out of a larger checkout (foostan's crkbd) where a long session had
already found and fixed several real bugs — the notes below exist so that
work doesn't have to happen twice.

## What this is

A split mechanical keyboard, derived from foostan's Corne Cherry v3, with
extra keys in a Levinson-style arrangement — the name mixes Corne + Levinson.

- **Left half:** 3 thumb keys, plus dedicated Ctrl/Alt/Cmd keys.
- **Right half:** 2 thumb keys, plus 4 arrow keys.
- 24 keys per half (48 total), Kailh/Gateron hotswap sockets, SOD-123 SMD
  diodes.
- Pro Micro footprint (Elite-C and Sea-Picro EXT are pin-compatible), OLED
  module, TRRS jack, 2-pin through-hole reset switch, optional SK6812MINI-E
  (per-key) and WS2812B (underglow) LEDs.
- Firmware: QMK.

## Layout

- `pcb/` — KiCad project (`cornison.kicad_pro`). Both halves live in one
  panel, joined by `Breakaway_Tabs` footprints meant to be snapped apart
  after fabrication. `pcb/kbd` is a submodule
  ([foostan/kbd](https://github.com/foostan/kbd)) providing the footprint
  and symbol libraries both `fp-lib-table` and `sym-lib-table` point at.
- `case/` — a from-scratch 3D-printed case + switch plate generator, built
  directly from the real PCB rather than hand-modeled. The scripts live
  in `case/scripts/`; run them through `./build.sh` at the repo root
  (`./build.sh help` lists every command, `./build.sh case` runs the
  whole pipeline). Pipeline:
  1. `extract_board.py` (`./build.sh extract`; needs KiCad's bundled
     Python, which has `pcbnew`) reads `pcb/cornison.kicad_pcb` and writes `board.json`:
     per-half outline, switch poses, M2 hole centers, MCU/OLED/reset/TRRS
     part bounding boxes.
  2. `case.py` (`./build.sh generate`; runs under `uv run --with
     build123d`) reads
     `board.json` and writes the case tray + switch plates (STEP/STL/DXF)
     plus a printed MCU cover (`cover-inset-{left,right}`) and a cutting
     template for a butyl floor mat (`mat-template-{left,right}`, STL +
     DXF, both in the physical frame unlike the plate DXF), foam
     (added 2026-11-11, not cut yet): case foam, 2mm in place of the
     mat, cut with the mat template; plate foam, between PCB and plate
     with the loose spacers, with its own tracing template
     (`foam-plate-template-*`); plus cut-only `foam-{case,plate}-*.dxf`
     for a cutting service; and (2026-11-18, the user's idea) a
     plate-foam cutting jig, `foam-plate-jig-{bottom,top}-*`: the
     foam clamped between two copies of its shape, spacer holes punched
     first, the bottom's pins standing in them and pressing into the top.
     Work in progress since 2026-11-21: on the first test print the foam
     kept pulling out from between the templates while cutting; the
     docs point to the 1:1 paper DXF instead. All of these go to
     `out/`. The same files serve a home printer and a print service:
     there's no separate prototype mode any more (it only skipped the
     MagSafe recess, which is gone). Each run first deletes the old
     STL/STEP/DXF files in `out/`.
  3. `make_fr4_plate.py` (`./build.sh fr4`) turns the plate DXF into real KiCad PCB projects
     (`plate-fr4-{left,right}/`) for ordering the plate in FR4 from
     JLCPCB, via the graph-based `dxf_to_loops.py`.
  - See `case/README.md` for the full write-up: stack-up heights, mounting
    hardware, assembly order, and ordering instructions.
- `firmware/qmk/cornison/` — a standalone QMK keyboard definition (not a
  QMK fork; symlink/copy it into a checkout as `keyboards/cornison`).
  `matrix_pins`/split/OLED setup are copied from upstream QMK's
  `crkbd/rev1` — confirmed pad-for-pad identical Pro Micro pinout by
  reading `pcb/kbd/kicad-symbols/kbd.lib`'s `ProMicro` symbol against the
  real net names in `pcb/cornison.kicad_pcb`. The `LAYOUT` key array
  itself is cornison-specific (crkbd's 3-key thumb cluster doesn't have
  room for this board's full 6-column bottom row) and is generated, not
  hand-typed, by `firmware/qmk/gen_layout.py` (`./build.sh layout`; same
  KiCad-bundled-python3 pattern as `case/scripts/extract_board.py`) — matrix row/col come from each
  switch's col/row net and its paired diode, positions from the real
  footprint coordinates. Unlike `case.py`'s `load_board()`, this script
  does **not** negate KiCad's raw rotation: QMK/KLE layout space is
  Y-down, the same sense as KiCad's own screen, so no sign flip belongs
  here (the negation in `case.py` is specifically for build123d's Y-up
  3D frame).

## Conventions that caused real, previously-shipped bugs

These aren't style preferences — each one was found after a physical part
came out wrong.

- **`board.json` holds raw KiCad coordinates, where Y points down.**
  `case.py`'s `load_board()` negates every key's rotation once on load,
  specifically because KiCad's footprint angle convention (CCW as drawn on
  its Y-down screen) is the opposite sense of a CCW rotation in those same
  raw numbers. Skipping this gets every switch hole rotated the wrong way.
- **A mounting hole is its footprint's pad, not its origin.** One
  `M2_HOLE_v2` footprint per half has its pad dragged ~10mm from the
  footprint origin (origin at 27.5/54.1, real hole at 29.6/64.3 on the
  left). `extract_board.py` used to read origins, so a printed case had
  that boss 10mm from the real hole. It reads the pad now, and records
  each hole's drill size.
- **3D exports must go through `to_physical()`** (a mirror about the XZ
  plane) before being written to STEP/STL. Without it, every 3D-printed
  part comes out as the mirror image of the real board — the PCB only
  seats switch-side-down, bosses land nowhere near the real mounting
  holes, and the USB/TRRS notches end up on the wrong wall. This cost a
  full case reprint once already. The plate DXF is deliberately **not**
  mirrored (it stays in KiCad's raw frame), since `make_fr4_plate.py`
  writes it straight back into a KiCad project and a flat through-cut
  plate's mirror image is the same physical part flipped over.
- **build123d transform order is `Pos*Rot*shape`, not `Rot*Pos*shape`.**
  The outer transform in a chain applies last, about its own frame — if
  `Rot` were applied last, it would spin the translation around the
  global origin instead of spinning the shape in place before moving it.
- **Plate edge and case cavity come from one shape, `board_envelope()`.**
  The plate's outer edge is the envelope; the cavity is the same envelope
  grown by `CAVITY_CLEARANCE`. Building the two from independent margins
  once let them drift apart. Since 2026-10-14 the envelope is made of
  straight lines (pinky side, MCU side, bottom up to the thumb cluster, a
  hull round the thumb keys, a flat top per column) instead of tracing the
  PCB outline plus each switch's rounded reinforcement patch. Tracing left
  scallops between rows. The envelope contains the PCB outline and every
  switch's and plate-mount hole's reinforcement patch (bar the corners
  trimmed at the top-edge steps), so nothing lost clearance. `build_case()`
  asserts the PCB and plate both fit inside the cavity. Since 2026-10-26
  (the user's call) it no longer holds the old plate's MCU-strip footprint
  (`legacy_mcu_footprint()`, removed: a reset hole and patches from when
  the plate covered that strip) or the patches round the two cover-post
  holes (in the plate's MCU opening, so no plate to reinforce). Those held
  the MCU-side wall 1.5mm out: 2.0mm off the PCB there, 0.5 everywhere
  else, and the cover's OLED window off-centre. The wall came in to 0.5mm;
  the case is 1.5mm narrower per half. The plate lost only slivers
  (1.1/1.5mm^2 below the lower cover post); a plate printed before that
  overlaps the new wall by 0.2/0.4mm^2 there -- sand the corner. The cover
  posts now stop at the PCB's edge (the lower one's hole is 2.6mm in), or
  they'd touch the wall.
- **The plate does not cover the MCU strip.** The TRRS jack (5.0mm),
  reset switch (~5.2mm) and Pro Micro (~5.5mm on ordinary headers) all
  stand taller than the 3.4mm under the plate, so `build_plate_sketch()`
  cuts an opening over them and `build_cover()` makes a separate printed
  cover: underside 6.0mm above the PCB, on posts at the two mounting
  holes beside the TRRS jack (M2×12 screws into the same inserts), OLED
  plugged in through a window. Those part heights are from the 3D models
  in `pcb/kbd`, not yet from real parts. The OLED does **not** rest on the
  cover: plugged fully into its ~4mm socket, its board sits 8–9mm above the
  PCB (measured 2026-10-15), just above the cover top (8.0mm). A cover
  under the module held it up and its pins wouldn't seat; a 1mm pocket
  fixed that, and since 2026-10-19 the cover has a window through it over
  the module's whole footprint instead, so everything under the OLED shows. A direct-soldered Pro Micro with its stubs
  left long measured ~7mm, which tipped the cover up at the USB end; the
  stubs have to be trimmed to the solder. Since 2026-10-18
  there's also a two-piece clear cover (`build_clear_cover()`): a printed
  base wall plus a 2mm laser-cut clear top over the same footprint, with
  the OLED under it. The OLED glass is 13–14mm above the PCB on its socket
  (measured). The clear top sits on two M2 male-female hex standoffs
  (15mm body), which replace the printed posts, so its underside is 15mm
  up. The male thread has to be 4mm: it passes the 1.6mm PCB before it
  reaches the insert, and the insert bore is blind (4.8mm max). The 3mm
  ones in hand wouldn't start in the insert. Both covers share
  `cover_footprint()`. Neither is built yet. Also 2026-10-18:
  `cover_outline()` straightens both covers' key side. A tab over the wall
  top and a tooth under the angled thumb keycap are cut off, and the plate
  fills where the tooth was, lapping 1mm under the new edge. A plate from
  before this leaves a small hole there under a new cover. 2026-10-25/26:
  an optional **inset cover** (`cover-inset-{left,right}`,
  `cover_footprint_inset()` / `inset_bevel()`), the user's idea: the same
  cover stopped at the plate's outline, so its top is a straight-edged
  panel inside the wall, OLED window centred (3.4mm each side once the
  wall came in). Its underside is 1mm above the wall top, so a 45 degree
  bevel from its top edge runs down onto the wall top on the wall side;
  with the wall 0.5mm off the PCB the bevel lands exactly on the case's
  outer face. A flat lip came first and was dropped: printed top-down it
  stuck out 2mm with nothing under it (supports). The bevel prints
  without. Its reset hole is 1.5mm from the edge at the top face, but
  `reset_access(bevel=True)` judges the wall at mid-thickness, where the
  bevel makes it 2.5mm, and `build_cover()` checks the bevel is really
  there beside it. A slot open to the edge came first (2026-10-26): it cut
  the frame round the window right through on the inner side, leaving a
  40mm strip hanging from the USB end; the user flagged it as weak. Not printed yet; the user will print both and
  keep one. Also 2026-10-26 (the user's question, once the wall came in):
  the flat covers no longer cut back over the USB notch -- the grip stays
  outside, only the socket (3.5mm up at most) is in there, so the cover
  spans it and the notch becomes a port. At the TRRS notch they cut back
  only where the cable's grip reaches (`grip_cut()`): the user measured its
  front ~2mm out from the PCB's edge (`TRRS_GRIP_FROM_PCB_EDGE`), so it's
  1mm into the wall now, and the cut is 1.5mm deep instead of the whole
  wall. Every cover is checked against a 10mm grip (`trrs_grip_solid()`).
  The inset cover's bevel stays cut at both notches (it comes down to the
  wall top at the outer face). Also 2026-10-26 (the user's catch): along
  the angled thumb-keycap edge both covers hovered 1mm over the plate, and
  you could see under them between the posts; a 2mm skirt
  (`COVER_PLATE_REST_IN` past the plate's 1mm lap) now rests on the plate
  there, level with the rim. A part-bbox cut-out unclipped to the cavity
  once sliced the bevel along the USB end (the Pro Micro's bbox includes
  its connector's overhang). 2026-11-21 (the user's call): the inset cover
  is the only cover now. The flat cover (`cover-{left,right}`,
  `cover_footprint()`, `grip_cut()`) and the clear two-piece cover
  (`build_clear_cover()`, `cover-base-*`/`cover-clear-*`, the STANDOFF_/
  CLEAR_ constants) were removed; they're in git history before that.
  `build_cover()` builds the inset cover, still written as
  `cover-inset-{left,right}`. The notes above about them are history.
- **`dxf_to_loops.py` reconstructs closed loops via a point-adjacency
  graph**, not by trusting the DXF's own edge ordering — build123d's own
  `Wire.order_edges()` has a real bug on this geometry (it silently
  drops a long straight run).
- **The case and plate follow the v1.1 PCB only.** From 2026-10-14 to
  2026-10-24 they carried both PCB revisions' outer/lower mounting spot
  (`EITHER_OR_HOLES`, 8 bosses and 6 plate holes per half), since the
  boards in hand were v1.0. On 2026-10-24 the user retired v1.0 (v1.1 gets
  ordered; the v1.0 boards are kept for test fits), so that went:
  bosses, plate holes and spacer posts all follow `board.json`'s
  `m2_holes`, 7 bosses and 5 plate holes per half, every spacer-frame
  post with a pilot. A v1.0 board in a new case sits on the bosses but
  misses two screws (outer/lower, and the right half's lower-centre). If
  a hole spot ever needs to carry two revisions again, a boss with no PCB
  hole above it presses on the board's underside: check it against
  `board.json`'s `keepouts`.
- **Every switch has a per-key LED since 2026-10-24** (user's call, for
  anyone who builds or buys the PCB). v1.1 adds LED55-57 (left, under
  SW43-45) and LED58-60 (right, under SW46-48) at switch +4.75mm like the
  rest, continuing each chain after LED19 / LED46 (30 LEDs per half: 6
  underglow, then 24 per-key). Done by script, not in the KiCad GUI. In
  the schematic they fill cols 0-2 of the thumb-row line of each LED grid,
  wired onto the existing VCC/GND rails like their neighbours. The same day
  SW43-48/D43-48, which had sat below the A3 frame (y=330) joined only by
  row/col global labels, moved into the empty row-3 slots of the key matrix,
  wired into the column and row3 wires (netlist connectivity checked
  identical before/after). The PCB's old `Net-(LED19-Pad2)`/`Net-(LED46-Pad2)`
  nets were renamed to the schematic's `Net-(LED19-DOUT)`/`Net-(LED46-DOUT)`.
  The traces came from a throwaway grid router plus hand-placed power
  rails (VCC/VDD a B.Cu bus under each new row, GND/GNDA a straight F.Cu
  rail above it), checked for clearance and for not crossing another net's
  pad on the opposite side; the user reviews it visually, so tidy routing
  matters, not just DRC. Each LED footprint carries its own Edge.Cuts window
  (the LEDs shine up through the board), so tracks must stay 0.1mm off it:
  two `row3_r` runs on the right half crossed the LED59/LED60 windows and
  were rerouted. The user should still eyeball it in KiCad before ordering.
  2026-10-28 (the user's catch): on the left half two of those runs went
  between a bottom-row diode's pads on B.Cu, under its body: the LED19→LED55
  data line across D43 (col0) and the VCC join from LED57 to the trunk
  across D45 (col2, the new bus's only link to VCC). Both now cross on F.Cu
  clear of the diode's silk box; DRC unchanged. No track crosses between a
  diode's pads anywhere now. (D46's data line, right half, runs along that
  diode's silk edge beside the board edge, not between its pads; left as is.)
  `gen_layout.py` now also writes `rgb_matrix`/`ws2812` (D3) into
  `keyboard.json` from the real chain; `features.rgb_matrix` is left off, so
  a keymap enables it.
- **Tenting-leg inserts live in the case floor, the screws come up from
  below.** Since 2026-10-23 (the user's request: changing the tent used to
  mean taking the keyboard apart, when the inserts were in the legs and
  the screws came down from inside the case). A screw can't run the
  length of a leg, so each leg has a platform beside it at the mounting
  face; an M2×6 goes up through it into an insert pressed into the case
  bottom. That needed `FLOOR_T` 2.5 → 4.0 (the insert is 3.2mm, its spec
  wants 4mm of material); the whole case is 1.5mm taller. An interior boss
  instead was ruled out: almost nothing under the PCB is clear of parts
  near the legs. `tent_leg_layout()` places the screws for both parts: toward
  the tent's middle, except beside a plumb leg, which leans under that
  spot, so those go along the inner edge. A column under each seat is kept
  clear to the desk for the driver. The case's 4 corner spots are rubber
  foot recesses again. `build_tent()` builds in the case's frame hanging below z=0:
  z=0 is the flat mounting face, and everything below one tilted desk
  plane is cut off so all four legs sit flat.
- **`b3d.extrude()` follows the sketch's own face normal**, and a polygon
  drawn clockwise has its normal pointing down. The first tent's frame
  came out 2mm below the leg tops that way, so the mounting face was not
  flat; the checks at the time only probed the legs. `extrude_down()`
  passes the direction explicitly and asserts where the solid landed, and
  `build_tent()` now probes the mounting face on every beam.
- **Plumb tent legs lean along the desk normal** (`TENT_PLUMB`, on by
  default; `TENT_PLUMB=0` makes them square to the case). A leg that
  leans in can't also keep its width and stay on the case's edge, which
  leans 18° on the desk. On 2026-10-23 the user tried a flared leg (plumb
  inside, on the edge outside: rejected, the width grew), then legs
  square to the case, and settled on plumb legs of constant width that
  move in from the edge going down. Each is a real `Cylinder` about the
  desk normal, clipped by a polygonized case outline slid down the slant.
  The frame is clipped by the same slid outline, so its inner-edge face
  leans with the legs: dropped straight, its 4mm stood 1.3mm proud of
  each leg at its underside (a ledge the user spotted). The slide moves
  the outline away from the frame on the outer side, so only the inner
  side is cut. The first version extruded the pad obliquely
  instead. OCC tessellates that generic extrusion surface (and an arc slid
  the same way) into long near-zero-area slivers, which showed as a
  pattern on the legs. Keep the tent's faces to planes and cylinders. Anything
  placed on a leg's end (rubber-foot recess, probes) is placed on the
  pad at z=0 and carried down that axis with `to_desk()`. A sign error
  there put the probes ~4mm past the leg's end on the first try.
- **`b3d.offset()` on a multi-face sketch offsets each face separately**
  and leaves them overlapping rather than merged — the (since removed)
  OLED bezel's pocket and reset column never joined, and the area check
  double-counted. Fuse the faces after offsetting. `Face.fuse().clean()`
  doesn't reliably merge them either (the tent frame plus its weight tray
  stayed two faces). And in build123d 0.13, `offset()` on a face with holes
  that splits into pieces crashes (`'Face' object has no attribute
  'unwrap'`). `close_holes()` (rounding the tent frame's openings) gets
  round all three by offsetting only hole-free faces: the empty faces of
  `outline - sketch`, one at a time. On the plate foam (2026-11-11), `open_sketch()` on a face
  with 27 holes came back with two switch openings filled in (no error;
  the switch-body check caught it). `open_holed()`/`offset_holed()`
  offset each face's outer outline and each hole separately, and
  `shrink()` falls back to booleans (minus a band along every edge) when
  a shrinking hole splits, where `offset()` throws 'Unexpected result
  type'.
- **The tent frame is straight beams, clipped to the case outline.** An
  offset ring through the leg centres self-intersected (the union came
  back invalid while still reporting one solid). And the case outline is
  not convex — a straight beam across the notch between the bottom row
  and the thumb cluster was clipped to ~2mm wide — so any beam that
  leaves the footprint is bent inward through a waypoint.

## Verification habits that caught real bugs

- **Check against ground truth from pcbnew directly** (real footprint pad
  positions, real `GetOrientationDegrees()`), not the model against
  itself. Comparing the model to its own assumptions is exactly how the
  mirror and rotation bugs above shipped undetected the first time.
- **Measure wall/connect thickness by true closed-loop-to-closed-loop
  distance**, not by cruder proxies — both of these produced false
  readings during the JLCPCB plate fixes:
  - An area-ratio cut test ("did removing this hole remove close to its
    full nominal area?") dilutes a small real encroachment into
    insignificance when the test shape is much bigger than the
    encroachment. Use a thin annulus/ring test at the exact margin you
    care about instead.
  - Point-to-point proximity on a boundary can't tell a genuine thin
    material bridge from a sharp concave notch (empty space) that
    happens to loop back close to itself. Verify the midpoint between two
    "close" points is actually inside the solid before treating it as a
    thin wall.
- Run `./build.sh drc` (`kicad-cli pcb drc` on both plate projects) after
  any geometry change.

## Fabrication constraints learned from real vendor feedback

- **JLC3DP, MJF PA12-HP nylon:** hard minimum feature size is 2×2×10mm
  (a 1.5mm-thick plate was rejected outright). Separate soft "thin wall
  risk" review wants ≥1.0mm minimum wall, ≥2.0mm preferred.
- **JLCPCB, FR4 plate orders:** routing "connect"/tab width needs ≥2.0mm
  or it gets flagged as a breakage risk during production review. The
  plate has no copper layer at all (it's Edge.Cuts only) — when asked,
  answer "bare board" / "no solder mask ink", since there's no copper to
  mask and the whole board counts as non-copper area.
- Ordering the left and right halves as one combined PCB file (joined by
  breakaway tabs) triggers JLCPCB's "contains 2 different designs"
  surcharge, because the two halves aren't mirror-identical (this variant
  has different thumb-key counts per side). This is expected, not a
  mistake — paying it is normally still cheaper than two fully separate
  orders.
- Every time a file gets replaced on an existing JLCPCB order, they issue
  a **new order number** for it. Seeing an order number change after a
  replacement is expected, not a billing duplicate.

## Hardware specifics (verified, not assumed)

- **PCB mounting insert:** McMaster 94459A767 (Heat-Set Insert for
  Plastic, Standard, Brass, M2×0.4mm, 3.2mm installed length). Its own
  published spec — 3.2mm max hole diameter, 4mm minimum surrounding
  material — is what sets `INSERT_BORE_D` and `BOSS_H` in `case.py`.
- **PCB mounting screw:** M2×4mm, low-head or pan-head — **not** flat
  head. With the plate mount there are no PCB-only screws left: five
  holes per half take the plate screw below, and the two beside the TRRS
  jack (2.2mm holes, no washer needed) take the cover's M2×12, or a bare
  M2×4 on a build without covers.
- **Washer:** only if a bare M2×4 goes on one of the 4.3mm PCB holes
  (i.e. the plate mount is skipped). That hole has no annular ring and is
  bigger than any standard M2 head (flat ≈3.8mm, pan ≈4.0mm, socket cap
  ≈3.8mm). Use M2.5-size (2.7mm ID / 6.0mm OD), not M2-size (5.0mm OD,
  only ~0.35mm overlap per side).
- **Plate mounting screw/spacer:** M2×10mm low-head at 5 holes per half
  (10 standoffs in all). A printed spacer sits between PCB and plate; its
  4.1mm pilot drops into the 4.3mm PCB hole, so no washer. Four per half
  take the 5.6mm `spacer-{pom,fr4,mjf}`; the top hole nearest the MCU
  strip takes the 5.0mm `spacer-narrow-…`, because its neighbouring
  switch bodies are 2.77mm from the hole centre. That hole was added at
  the user's request after the first working prototype, against the
  generator's own 2.2mm wall rule: plate wall there is 1.62mm (under
  JLCPCB's 2.0mm FR4 ask), and a 4.0mm screw head overlaps two switch
  top-housing footprints by 0.27mm on paper. Fine on the real v1.1 build
  with the FR4 plate (the user, 2026-11-21). M2×10 gives full 3.2mm insert engagement.
- **MagSafe ring:** Keebio Magnetic MagSafe Tenting Stand Kit R2 — **50mm
  OD, 0.5mm thick, measured directly off the real ring.** `case.py` used
  to assume Apple's own published MagSafe spec (54.10mm OD, 2mm thick),
  which was the wrong reference — this kit's ring isn't Apple's OEM part.
  It's adhesive-backed and sticks to the flat case bottom: the locating
  recess was removed 2026-10-15 (the user's call: not needed to use the
  ring, and a 50mm first-layer bridge on a home printer).
- **Diodes:** genuine SOD-123 package required (confirmed via the
  `D3_SMD_v2` footprint's pad spacing and 3D model) — a visually-similar
  "0805" SMD diode is a different, incompatible package.

## Firmware, versioning and the controller

- **Version lives in `VERSION`** at the repo root: bump it there and run
  `./build.sh version` (`pcb/sync_version.py`), which copies it into the
  title blocks (`rev`, in `.kicad_pcb` and `.kicad_sch`), the FR4 plates'
  title blocks and every fabrication-toolkit `ARCHIVE_NAME`;
  `make_fr4_plate.py` reads it too. KiCad can't read an outside file, so a
  revision changed in KiCad's Page Settings drifts: `./build.sh version
  --check` catches that. The silkscreen label ("Cornison v${REVISION}")
  reads the PCB title block, so don't edit the text. v1.0 boards (foostan's
  "Corne Cherry v3.0.1" silkscreen) are retired; v1.1 moved two mounting
  holes, so case and plate follow v1.1 only.
- **Firmware build:** against real upstream QMK
  (https://github.com/qmk/qmk_firmware), not a vendor fork such as
  bastardkb's, and not a QMK old enough (2023) that keyboard discovery
  doesn't support a `keyboard.json`-only keyboard with no `rules.mk`.
- **Confirmed on real hardware:** `diode_direction: COL2ROW`; the Keebio
  Pro Micro USB-C ships with **Caterina** (`development_board: promicro`).
  Flash with e.g. `qmk flash -kb cornison -km default -bl
  avrdude-split-left` (or `-right`), which writes the handedness EEPROM in
  the same step. A first attempt after reset sometimes fails with
  `butterfly_recv`/"Device not configured" (avrdude losing the Caterina
  timing): nothing is written yet, just retry. New Pro Micros ship with an
  Arduino Leonardo sketch (2341:8036), so the first flash needs no reset:
  `stty -f /dev/cu.usbmodemXXXX 1200` drops it into Caterina, then run
  avrdude on the port when it comes back. Once QMK is on, the reset button
  needs a quick double-tap; Bootmagic (hold the top outer key while
  plugging in) also works.
- **`natewlew` keymap** lives in `firmware/qmk/cornison/keymaps/natewlew/`,
  self-contained (`natewlew.c/.h`, OS detection, shortcut table). Its
  `rules.mk` sets `USER_NAME` so QMK doesn't also pull in a userspace copy
  (both define `process_record_user`). Its readme shows `keymap.svg`,
  drawn by `firmware/qmk/draw_keymap.py` (`./build.sh keymap-svg`): redraw
  it whenever keymap.c changes, and add new custom keycodes to its
  `LABELS`.
- **Pro Micro mount standard:** the Pro Micro must top out at 5.5mm or
  less above the PCB: direct-soldered with the stubs trimmed to the
  solder, or on Mill-Max low-profile sockets. Taller mounts (machined DIP
  ~7-8mm, standard 8.5mm sockets ~11mm) are out of scope: the OLED module
  overlaps the Pro Micro in plan and sits 8-9mm up on its socket. The Pro
  Micro's own board sticks out 2mm past the PCB's edge (measured), so the
  USB notch is 19mm wide from the PCB's top up (`PRO_MICRO_CLEARANCE`).

## Working style for this project

- Fact-check specific claims (search, or measure directly from the actual
  files/geometry) rather than answering from memory or assumption —
  several wrong assumptions were caught and corrected this way during
  sourcing and fabrication decisions.
- When something's wrong, fix the root cause in the generator, not just
  the one symptom — e.g. the plate-edge-clearance issue and the thin
  reset-hole wall turned out to be two separate causes that needed two
  separate fixes, even though both symptoms looked similar at first.
- Don't regenerate or modify files behind hardware that's already been
  ordered or printed without asking first — ask, then apply the fix only
  once there's a clear go-ahead.
- Keep replies short and concrete.

## Private notes

The maintainer's dated build and order log is kept outside the repo and
imported here; for anyone else this line does nothing.

@~/.claude/cornison-private.md
