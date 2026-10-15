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
     plus a printed MCU cover (`cover-{left,right}`) and a cutting
     template for a butyl floor mat (`mat-template-{left,right}`, STL +
     DXF, both in the physical frame unlike the plate DXF), to
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
  scallops between rows. The envelope contains the PCB outline, every
  reinforcement patch (bar the corners trimmed at the top-edge steps) and
  `legacy_mcu_footprint()`, so nothing lost clearance. `build_case()` asserts the PCB and plate both fit inside the
  cavity.
- **The plate does not cover the MCU strip.** The TRRS jack (5.0mm),
  reset switch (~5.2mm) and Pro Micro (~5.5mm on ordinary headers) all
  stand taller than the 3.4mm under the plate, so `build_plate_sketch()`
  cuts an opening over them and `build_cover()` makes a separate printed
  cover: underside 6.0mm above the PCB, on posts at the two mounting
  holes beside the TRRS jack (M2×12 screws into the same inserts), OLED
  lying on top through a slot. Those part heights are from the 3D models
  in `pcb/kbd`, not yet from real parts. `legacy_mcu_footprint()` is what
  the plate covered back when it went over that strip. `board_envelope()`
  still includes it, so the walls round the MCU strip never come in
  closer than they were then.
- **`dxf_to_loops.py` reconstructs closed loops via a point-adjacency
  graph**, not by trusting the DXF's own edge ordering — build123d's own
  `Wire.order_edges()` has a real bug on this geometry (it silently
  drops a long straight run).
- **Mounting holes for two PCB revisions.** The next PCB moves the
  outer/lower hole down one row. That change is now made in
  `pcb/cornison.kicad_pcb` (2026-10-14), so `board.json`'s `m2_holes` shows
  the new spot. The boards actually in hand are still the first revision,
  with the hole at the old spot. `load_board()` builds
  `data["mount_holes"]`: the PCB's own holes plus both spots in
  `EITHER_OR_HOLES`, named by the four keys meeting there. Bosses, plate
  holes and spacer posts use `mount_holes`; the case walls still follow
  `m2_holes` only. A boss with no PCB hole above it is checked against
  `board.json`'s `keepouts`, since it presses on the board's underside.
  This replaced the support ribs (2026-10-12 to 2026-10-14) that braced
  the bottom-row corner.
- **Tenting-leg inserts live in the leg, not the case.** A tilt across the
  case's width means tens of mm of height difference between legs — far
  too much for one screw to span if the insert were in the case. Each leg
  has its own M2 insert in the flat mounting face; the screw comes down
  from inside the case through a plain floor hole, the same M2×6 at every
  corner. `build_tent()` builds in the case's frame hanging below z=0:
  z=0 is the flat mounting face, and everything below one tilted desk
  plane is cut off so all four legs sit flat.
- **`b3d.extrude()` follows the sketch's own face normal**, and a polygon
  drawn clockwise has its normal pointing down. The first tent's frame
  came out 2mm below the leg tops that way, so the mounting face was not
  flat; the checks at the time only probed the legs. `extrude_down()`
  passes the direction explicitly and asserts where the solid landed, and
  `build_tent()` now probes the mounting face on every beam.
- **`b3d.offset()` on a multi-face sketch offsets each face separately**
  and leaves them overlapping rather than merged — the (since removed)
  OLED bezel's pocket and reset column never joined, and the area check
  double-counted. Fuse the faces after offsetting.
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
  top-housing footprints by 0.27mm on paper — not yet checked on a real
  plate. M2×10 gives full 3.2mm insert engagement.
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

## Order status (as of 2026-10-12 — verify before relying on this)

- PCBs arrived from JLCPCB and look good. Both halves flashed and bench
  tested individually with the default keymap (bare board, no
  case/plate/switches — tested by shorting each hotswap socket's pads
  with tweezers): all 24 matrix positions register correctly on each
  half. Confirms two things that were previously only inferred:
  - `diode_direction: COL2ROW` is correct.
  - The Keebio Pro Micro USB-C actually used ships with a **Caterina**
    bootloader, confirming `development_board: promicro` in
    `firmware/qmk/cornison/keyboard.json`. Flash with e.g. `qmk flash -kb
    cornison -km default -bl avrdude-split-left` (or `-right` for that
    half) — writes `eeprom-{lefthand,righthand}.eep` in the same step,
    so no separate EH_LEFT/EH_RGHT tap is needed. First attempt after a
    reset sometimes fails with `butterfly_recv`/"Device not configured"
    from avrdude losing the Caterina handshake timing — harmless,
    nothing is written yet, just retry.
  - Both halves confirmed working together over TRRS, not just
    individually.
  - The `natewlew` keymap (ported from `keyboards/keebio/nyquist/keymaps/natewlew`
    in the `qmk_firmware` fork, lives in `qmk_userspace/keyboards/cornison/keymaps/natewlew/`,
    not in this repo) is flashed to both halves and working on real
    hardware as of 2026-10-12, split connection included.
  - Full firmware bring-up is done: matrix, bootloader, handedness, and
    split link all confirmed on real hardware.
- `firmware/qmk/cornison` builds against a `git worktree` of
  `~/Development/natewlew/qmk_firmware` checked out to real upstream
  QMK (`git remote add upstream https://github.com/qmk/qmk_firmware.git`),
  not `bastardkb-qmk` (a vendor fork for bastardkb's own boards — wrong
  home for an unrelated personal keyboard) and not that repo's own stale
  2022 branch/fork `master` (from 2023 — old enough that its keyboard
  discovery doesn't support a `keyboard.json`-only keyboard with no
  `rules.mk`).
- FR4 switch plates (JLCPCB orders, most recently order numbers Y10/Y11)
  were fabricated from pre-fix files: the two angled thumb-key holes per
  half are rotated 30° off, and the plate's thumb-area outline also
  doesn't fit the corrected case cavity. They also sit over the TRRS jack
  and reset switch, which are taller than the gap under the plate, and
  their OLED slot is too short for the header's fourth pin. Don't reorder
  until a home test print of the regenerated plate confirms the fix.
- `case/plate-fr4-{left,right}/` were regenerated 2026-10-13 from the
  current plate (MCU opening, 5 mounting holes per half) and pass
  `./build.sh drc` with 0 violations. Checked in pcbnew: 24 switch holes
  + 5 M2 holes per half, every M2 hole on a PCB mounting hole, plate area
  matching the generator. The Gerber zips in each `production/` folder
  are still the 2026-10-02 export of the old design — re-export from
  KiCad before any order. The fifth hole's 1.62mm wall is under JLCPCB's
  2.0mm ask and may be queried.
- Any case printed before 2026-10-12 has one boss per half ~10mm off its
  PCB hole (the outer-edge one nearer the thumb row) — skip that screw on
  it; fixed in the generator, needs a reprint.
- First test build has the Pro Micro **direct-soldered** (no socket), so
  it goes without the MCU cover and OLED. On this build, the printed case
  needed hand-trimming along the top wall near the Pro Micro, away from
  the USB notch (not at the plug opening itself) — measured against the
  real geometry: the wall there sits flush against the Pro Micro
  footprint's edge with 0 clearance in the model already, independent of
  mounting method. Not yet fixed in the generator: the real target mount
  is the low-profile Mill-Max sockets (shorter than direct-soldered
  headers), which may not need the same trim — re-measure once those are
  in hand rather than widen the opening against today's substitute part.
- 2026-10-14: case, plate and spacer frame carry both the current and
  the next-revision outer/lower mounting spot (8 bosses, 6 plate holes per
  half); the support ribs are gone. Cases printed 2026-10-12/13 have ribs
  and no second boss; plates printed before have only 5 holes. FR4
  projects regenerated, DRC 0 violations, Gerber zips still stale.
- Plate-mount spacers added (2026-10-12); a fifth plate-mount hole per
  half added 2026-10-13 (the top one nearest the MCU strip, narrow
  spacer). Plates printed before 2026-10-13 lack that hole — reprint, or
  drill 2.3mm at the PCB hole's position. The case is unchanged by both.
  Not yet physically confirmed: screw-head fit at the fifth hole, and
  keycap-skirt clearance over the 4 (of 5) screw heads per half that land
  under a keycap (see TODO.md).
- Spacer frame added 2026-10-14 (`spacer-frame-{pom,fr4,mjf}-{left,right}`):
  the 10 loose spacers as one plate-shaped piece per half, between PCB and
  plate. Openings 15.6mm per switch; outer border strips only 1.2–2mm.
  Not printed yet.
- Cover/plate seam fixed 2026-10-14, after a printed cover came out short.
  The cover now reaches the wall's outer edge; it used to stop 1mm short
  because the old lap was 1.5mm onto a 2.5mm wall. The plate also fills the
  triangle the cover leaves where it's cut back for the angled thumb keycap,
  reaching 1mm in under the cover's edge. Cover posts are trimmed to stay
  0.6mm off the plate: before this, the plate overlapped the upper post by
  0.2mm. The case is unchanged (same volume).
- Straight-sided case and plate outline, 2026-10-14 (see
  `board_envelope()` above). The overall cavity bbox is unchanged
  (137.3 × 93.3mm), and the old cavity and plate fit inside the new ones
  except at the top-edge steps. There, the taller column's
  reinforcement corner (20mm patch on a 19mm pitch) is trimmed back to
  the step: ~0.6mm² of cavity and ~0.8mm² of plate per half. Every switch
  hole keeps ≥2.2mm of plate to the edge. Steps sit midway between real
  columns (2+ keys). A first version counted the left half's lone
  bottom-row thumb key as a column, which carried the middle column's top
  ~4mm over the next one. Cases and plates printed before this have
  the scalloped outline and are not interchangeable with new ones (a new
  plate won't drop into an old case).
- FR4 projects regenerated 2026-10-14 after both changes above: DRC 0
  violations; read back in pcbnew as 1 outline + 30 holes per half, area
  within 0.7mm^2 of the generator's plate. Gerber zips in `production/`
  are still the 2026-10-02 export — re-export before ordering.
- OLED bezel (printed part over the OLED, on top of the cover) added and
  then removed 2026-10-14: the user didn't like it. It was never committed.
  If it comes back, these are the OLED measurements it used (Unicorne kit
  module): 33 × 12mm module, screen starting 6mm from the pin edge and
  27mm long, solder ~3mm, module board ~10mm above the PCB.
- First working prototype assembled 2026-10-13 (printed case, plate,
  spacers and tents).
- MagSafe ring dimensions corrected (2026-10-12) from Apple's generic
  published spec (54.10mm OD, 2mm thick — the wrong reference) to the
  real Keebio ring, measured directly: **50mm OD, 0.5mm thick**. Any case
  printed before this has an oversized, overdeep recess (54mm/2mm). The
  recess has since been removed entirely (2026-10-15); the ring sticks to
  the flat bottom.
- Printed tenting legs added (2026-10-12), reworked 2026-10-13: 20mm
  legs, flat mounting face, legs cut to one desk plane, beams with a
  middle brace. Alternative to the MagSafe stand (kept — see
  case/README.md). Default 18° (`TENT_ANGLE_DEG`), raised from 12° on
  2026-10-14 at the user's request: 51mm at the case's inner edge vs 35mm
  at 12°. 20° had been the first idea and was turned down for height.
  The 2026-10-12 tent files were wrong (frame 2mm below the leg tops,
  square-cut leg ends) — don't print those. Any case printed before
  2026-10-12 has a blind 1mm foot recess, not the through-hole the tent
  needs. Not yet physically confirmed: screw-head clearance under the
  PCB, and desk stability at 18° (see TODO.md).
- The already-printed JLC3DP case is the mirror-image bug described above
  (3.9mm M2 insert bores too, from before that was corrected) — needs a
  reprint from the current `case/out/case-*.stl`.
- Any MJF nylon plates ordered from that same pre-fix batch are flat, so
  flipping one over gives the correct (non-mirrored) part — no reorder
  needed for those specifically.
- Switched home printer from an Ender-3 V2 to a Bambu Lab P1S (bought at
  $399 during the 2026-10-06 Prime Day/Bambu Halloween sale), with a BIQU
  CryoGrip Pro Frostbite plate. Printing Bambu PETG Matte, dried 8h at
  65°C in a Sunlu S2 dryer before printing and calibrated (Flow Dynamics +
  Flow Rate) for it. Plate type: whichever of Smooth PEI/Cool Plate
  SuperTack is selected, set that row's bed temp to 65°C in the filament
  profile. The Ender is still a fallback; its known-good settings (4
  perimeters, slower first layer, retensioned Y belt) carry over to any
  printer for this case's thin walls.
- First case print on the P1S had rough top-surface peaks/line separation
  on the hidden underside — traced to printing from an undried spool;
  cosmetic only (hidden under the PCB), no reprint needed once the spool's
  dried.

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
