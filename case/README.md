# cornison case

A 3D-printed tray case, switch plate, MCU cover, plate-mount spacer and
tenting leg, generated directly from the real
PCB geometry (`../pcb/cornison.kicad_pcb`). No copper is touched;
everything here only reads the board to place bosses, notches and cutouts
correctly. Re-run the generators any time the PCB changes.

## What's in here

| File / dir | What it is |
|---|---|
| `scripts/extract_board.py` | Reads the PCB (KiCad python) → `board.json`: per-half outline, switch poses, M2 holes, MCU/OLED/reset/TRRS part positions |
| `scripts/case.py` | Reads `board.json` (build123d, via `uv run --with build123d`) → the case tray, switch plate, MCU cover, plate-mount spacer, tenting leg and floor-mat cutting template, as STEP/STL/DXF in `out/` |
| `scripts/dxf_to_loops.py` | Turns a plate DXF into closed point loops (graph-based, endpoint-matching — doesn't trust any single edge ordering) |
| `scripts/make_fr4_plate.py` | Reads the DXF loops → `plate-fr4-{left,right}/`, a KiCad project per half for ordering the plate in FR4 |
| `out/` | Generated STEP/STL/DXF (gitignored; regenerate anytime). Emptied of old STL/STEP/DXF files at the start of each run |

## Stack-up

Heights measured from the case's true bottom (z=0):

| Z | Feature |
|---|---|
| 0 – 2.5mm | Floor, flat underneath |
| 2.5 – 6.5mm | Boss height — clearance for the hotswap sockets + B-side LEDs |
| 6.5 – 8.1mm | PCB (1.6mm) |
| 8.1 – 13.1mm | Air gap above the PCB — standard Cherry MX clearance |
| 11.5 – 13.1mm | Switch plate (1.6mm FR4) |
| 13.1mm | Wall top / plate top, flush |

The plate stops short of the MCU strip. The TRRS jack (5.0mm), reset
switch (about 5.2mm) and Pro Micro (about 5.5mm on ordinary headers) all
stand taller than the 3.4mm under the plate, so the plate is cut away
over them and a separate printed cover goes there instead — see
[MCU cover](#mcu-cover) below.

Every switch cutout is a plain 14×14mm square, including the 1.5u thumb
key — the switch body is always that size regardless of keycap width
(verified against the stock corne plate's own `SW_Hole` footprint).

The plate's edge (and the case cavity, 0.5mm outside it) doesn't trace the
PCB outline. `board_envelope()` builds it from straight lines: straight
down the pinky side and the MCU side, one straight bottom edge out to the
thumb cluster, a straight-sided hull round the thumb keys, and a straight
edge across each column's top, so the top still steps with the column
stagger. It contains everything the old traced shape did: the PCB, at
least 3mm of plate round every switch cutout (2.2mm or more beside the
taller column at a top-edge step), and the MCU-strip area. So
the plate overhangs the PCB in places (up to ~5mm along the bottom), and
nothing lost clearance.

## Mounting

- **PCB → case:** 8 bosses per half: one under each of the PCB's 7
  M2 mounting holes, plus one at the spot the outer/lower hole moves to in
  the next PCB revision (one row down, at the SW13/SW14/SW43/SW44
  junction on the left, SW34/SW35/SW46/SW47 on the right). The case fits
  either PCB: on today's board that extra boss has no hole above it and
  just props the PCB up near the bottom-row corner (it clears every part
  on the underside); on the next board it's the old spot's boss that does
  that. Only fit inserts in the bosses that have a PCB hole above them —
  a bare insert pressed against the board's solder mask isn't wanted. Press M2×3.2mm heat-set inserts into them (soldering
  iron or heat-set tool). On the normal build nothing screws the PCB down
  by itself: the plate screws and the cover screws clamp it (below).
  Without the plate mount, screw it down from above with M2×4mm low-head
  screws **and an M2.5 washer under each screw head** on the 4.3mm holes. The boss
  bore (`INSERT_BORE_D`) and boss depth (`BOSS_H`) in `scripts/case.py` are sized to
  McMaster 94459A767's own published spec for this exact insert (M2×0.4mm,
  brass, 3.2mm installed length): 3.2mm hole diameter, 4mm minimum
  surrounding material.

  In that case the washer isn't optional on five of the seven holes (the two beside
  the TRRS jack are 2.2mm and clamp under a bare screw head): those
  mounting holes (`M2_HOLE_v2` footprint) are a plain 4.3mm hole with no annular ring, sized for the
  original sandwich-case design where a standoff barrel passes fully
  through it. No standard M2 screw head clears 4.3mm (flat ~3.8mm, pan
  ~4.0mm, socket cap ~3.8mm, all per their ISO/DIN specs) — without a
  washer bridging the hole, any of them just drops straight through and
  clamps nothing. Use a washer with an OD meaningfully bigger than 4.3mm
  (5.5–6mm gives a comfortable bearing ring; a bare 5mm standard washer
  only overlaps by ~0.35mm per side).
- **Plate → PCB → case:** 5 mounting points per half also screw
  the plate down, sandwich-style — same idea as the stock Corne. At each
  one, a printed spacer sits between the PCB and the plate, its pilot nub
  dropped into the PCB's 4.3mm hole, and one **M2×10 low-head screw** runs
  plate → spacer → PCB into the same heat-set insert the PCB screw would
  otherwise use. The other two per half are the cover posts beside the
  TRRS jack, inside the MCU opening where there is no plate.

  The plate has holes at both outer/lower spots (6 per half). Screw and
  spacer go only in the one your PCB has a hole under; the other plate
  hole stays empty.

  Four of the five take the standard spacer (`spacer-{pom,fr4,mjf}`,
  5.6mm across — pick the one matching your plate material). The fifth,
  the top hole nearest the MCU strip, takes the narrow one
  (`spacer-narrow-{pom,fr4,mjf}`, 5.0mm): its neighbouring switches are
  only 2.77mm from the hole's centre, and the standard spacer would touch
  them. That hole is the tight one in three ways:
  - the plate wall between it and the nearest switch cutout is 1.62mm —
    fine for a printed or POM plate, but under JLCPCB's 2.0mm ask, so an
    FR4 order may get it queried;
  - the narrow spacer clears the switch bodies by 0.27mm;
  - a 4.0mm screw head overlaps the footprint of two switches' top
    housings by 0.27mm on paper. The stock Corne has a screw in the same
    spot, so it is expected to fit, but check it on a real plate and use
    the smallest-headed screw you have there.

  `report_plate_mount()` prints each hole's spacer, its clearance, and
  whether the head lands under a keycap.

  **Or print all of them as one piece:** `spacer-frame-{pom,fr4,mjf}-{left,right}`
  is the plate's own outline with an opening round each switch (15.6mm,
  the size of a switch's top housing, so the clips that snap out under
  the plate have room), standing between the PCB and the plate. Its five
  posts are the same size as the loose spacers would be at each hole, with
  the same pilot into the PCB hole, so the same M2×10 screws go through.
  It has posts at both outer/lower spots, without pilots there, so it
  sits flat on either PCB.
  It's hidden under the plate. Inner ribs are about 3.45mm; the strips
  round the outer edge are thinner, 1.2–2mm, because the switches sit
  close to the board edge. Print it top face down, pilots up. Nothing else
  on the top of the PCB is under the plate (checked against every
  top-side pad in the KiCad file), so the frame only has to clear the
  switches.
- **The bottom is flat** apart from the 4 screw holes near the corners
  for the tenting legs (rubber feet go over them otherwise), so a MagSafe
  ring sticks on anywhere in the middle.

## MCU cover

`cover-{left,right}` is a flat 2mm printed cover over the Pro Micro, TRRS
jack and reset switch, about 25 × 65mm.

| Height above PCB top | Feature |
|---|---|
| 0 – 6.0mm | Two posts, standing on the PCB over the two mounting holes beside the TRRS jack |
| 5.0 – 6.0mm | Rim, resting on the case wall top along the board's top and inner edges |
| 6.0mm | Cover underside |
| 8.0mm | Cover top (3.0mm above the plate and wall top) — the OLED lies here |

- **Mounting:** one M2×12mm screw per post, through cover, post and PCB
  into the same heat-set insert an ordinary PCB screw would use (2.4mm of
  thread in the 3.2mm insert). The post's 6mm foot does the washer's job
  at those two holes, so no washer there.
- **OLED:** plugs into a low-profile socket on the PCB through a slot in
  the cover, sized for the whole 4-pin header, and rests on the cover's
  top.
- **Reset:** a 2mm hole over the switch for a paperclip.
- **Pro Micro:** soldered directly on ordinary headers, or on low-profile
  (Mill-Max style) sockets. Standard 8.5mm sockets put it at about 11mm
  and do not fit — build without the cover and OLED in that case.
- The cover stays out from under every keycap and clear of the USB and
  TRRS wall notches.
- **Printing:** top face down, posts up. No supports.

**Not yet checked against real parts.** The part heights behind
`COVER_UNDERSIDE_ABOVE_PCB` in `case.py` are measured from the 3D models
in `pcb/kbd`, not from the components themselves. Measure a built board
before ordering covers from a print service.

## MagSafe tenting stand

The Keebio Magnetic MagSafe Tenting Stand Kit R2's ring is adhesive-backed
(measured: 50mm OD, 0.5mm thick) and sticks straight onto the flat case
bottom. No recess is needed, so the case has none. Earlier versions cut a
0.5mm locating pocket, which only meant a 50mm unsupported bridge on a
home printer.

## Tenting legs

An alternative to the MagSafe stand: one printed part per half
(`tent-{left,right}.stl`) that bolts on at the same 4 points the rubber
feet use and tilts the half so its **inner edge** (toward the gap between
halves) sits higher than its **outer edge** — a peaked-roof tent.

**Shape.** One face is flat: that is the mounting face, and it goes
against the underside of the case. Hanging off it are four round legs
(`TENT_FOOT_D`, 20mm, trimmed flush wherever they would overhang the
case's outline) joined by 10 × 4mm beams with a brace across the middle.
The legs are cut off along a single tilted plane, so all four end flat
on the desk. That plane is `TENT_MIN_T` (5mm) from the case at its outer
edge; at the default 18° the legs are about 7mm tall on the outer side
and 45–49mm on the inner side (51mm at the case's inner edge).

A beam that would leave the case's footprint is bent inward through a
waypoint. The outline turns inward where the straight bottom edge meets
the thumb cluster.

**How it attaches.** Each leg has an M2×3.2mm heat-set insert pressed
into the flat mounting face. An **M2×6 screw** goes in from *inside* the
case — head on the case floor, down through the floor hole
(`build_case()` cuts a plain M2 clearance hole at each foot position),
into the leg's insert. So the tent goes on before the PCB, and the PCB
has to come out to take it off again.

The insert is in the leg rather than the case because a tilt across the
case's width means tens of millimetres of height difference between
legs; an insert in the case would need a screw as long as each leg. This
way one short screw works at every corner. The floor holes are small
enough that a plain adhesive foot still sticks over them if no tent is
fitted.

**Angle.** Set with the `TENT_ANGLE_DEG` environment variable, default
18°:

```sh
TENT_ANGLE_DEG=15 ./build.sh generate
```

The console output prints each leg's height.

**Hardware per half:** 4 × M2×3.2mm heat-set insert (the same part as the
case bosses), 4 × M2×6mm low-head screw, 4 × 10mm round rubber foot.

**Rubber feet.** The desk end of each leg has a round recess for a
10 × 2mm rubber foot: 10.4mm across and 0.8mm deep, so the foot stands
1.2mm proud. It is cut square to the desk plane, and sits 2mm off the
leg's centre toward the middle of the tent so there is a rim all the way
round (`TENT_RUBBER_*` in `scripts/case.py` for a different foot).

**Printing.** Flat mounting face down on the bed, legs pointing up; no
supports needed.

**Not yet confirmed on a real part:** that the screw heads clear what is
under the PCB (two of the four per half sit under a switch socket or the
Pro Micro's pins; by the numbers there is about 0.5mm of room over a
1.6mm head, so use low-head screws), and that the half sits steady on the
desk at the default angle.

## Floor mat (optional)

A butyl sound-deadening mat (car "Dynamat"-style sheet) on the case floor
damps the thin printed floor and adds about 20g per half. It has to fit
between the floor and the hotswap sockets on the PCB's underside: 4.0mm
under the PCB, less ~1.8mm of socket, so use **~1.7mm sheet (Dynamat
Xtreme, 67mil), not the common 2mm/80mil mats**. It has to be pure
butyl: a Kilmat 80mil sheet tried for this smelled of asphalt, which
means it is asphalt-based or blended and will off-gas, worst when warm,
a foot from your face.

`case.py` writes a cutting template per half: `mat-template-{left,right}.stl`
(a 0.6mm print) and `.dxf` (to print 1:1 on paper). It is the cavity
pulled 0.5mm in from the wall, with 7mm holes at the bosses, 5mm holes
at the tent screw heads, and no mat under the MCU strip, where the
through-hole pins of the Pro Micro, TRRS jack, reset switch and OLED
header stick out under the PCB right over the mat's foil. The generator
checks a 1.7mm mat against the case solid.

Both files are in the real-world frame, the same as the case STL: lay
the template on the **foil side** as printed, or flip it over if
tracing on the backing paper. Cut with a sharp knife in several light
passes (chill the sheet first so the butyl doesn't drag), punch the
holes with a leather punch, and test-fit with the backing still on
before sticking it down. The foil is conductive and faces the sockets
with ~0.5mm to spare; a layer of Kapton tape over it is cheap insurance.

## Hardware BOM (per keyboard, both halves)

| Item | Qty | Notes |
|---|---|---|
| M2×3.2mm heat-set insert | 14 (+8 for tenting legs) | 7 per half, in the case bosses that have a PCB hole above them (8 bosses per half; the spare one stays empty: on first-revision PCBs the lower of the two outer bosses, on the next revision the upper one). [McMaster 94459A767](https://www.mcmaster.com/94459A767/) is a confirmed fit. +4 per half if printing tenting legs (one insert per leg, pressed into the leg itself) |
| M2×4mm low-head screw | 0 (4 without the MCU covers) | Only for the two holes per half beside the TRRS jack when no cover is fitted; those holes are 2.2mm and need no washer. 14 total if skipping the spacer/screw-down mount entirely (use M2×4 everywhere the table below says M2×10) |
| M2×6mm low-head screw | 8 | Case → tenting leg, 4 per half, if printing tenting legs — same length at every corner regardless of that corner's own leg height (see Tenting legs, above) |
| M2×10mm low-head screw | 10 | Plate → spacer → PCB → case bosses, 5 per half |
| M2×12mm pan-head screw | 4 | MCU cover → case bosses, 2 per half |
| M2.5 washer, 2.7mm ID / 6.0mm OD | 0 (10 if skipping the plate mount) | Only needed under a bare M2×4 screw on one of the 4.3mm PCB holes, which the plate mount no longer leaves any of. Required there (fits M2 screws fine, just a looser slip fit) — the PCB's mounting hole is 4.3mm with no annular ring, bigger than any standard M2 screw head. McMaster's M2-labeled washer (5.0mm OD) only just clears it; M2.5 size gives real margin. Not needed under the M2×6, M2×10 (bears on the plate's small clearance hole) or M2×12 (bears on the cover's printed post) |
| Rubber feet, 10 × 2mm round | 8 | 4 per half. On a tented half they go in the recesses on the leg ends; without a tent they stick to the case bottom at the same 4 points |
| MagSafe ring (Keebio kit) | 2 | 1 per half, adhesive-backed — alternative to tenting legs, see above |
| Case | 2 | 1 per half, 3D printed (`case-{left,right}.stl`), see Ordering the case below |
| Switch plate | 2 | 1 per half — FR4 (from the `plate-fr4-{left,right}/` KiCad projects), or POM or MJF nylon (`plate-{pom,mjf}-*`), see below |
| MCU cover | 2 | 1 per half, 3D printed (`cover-{left,right}.stl`) |
| Plate-mount spacer, standard | 8 (+ spares) | 4 per half, 3D printed (`spacer-{pom,fr4,mjf}.stl` — pick the one matching your plate material) |
| Plate-mount spacer, narrow | 2 (+ spares) | 1 per half, for the top hole nearest the MCU strip (`spacer-narrow-{pom,fr4,mjf}.stl`) |
| Spacer frame (instead of the 10 loose spacers) | 2 | 1 per half, 3D printed (`spacer-frame-{pom,fr4,mjf}-{left,right}.stl`) |
| Tenting leg | 2 | 1 per half, 3D printed (`tent-{left,right}.stl`) — alternative to rubber feet |
| Floor mat (optional) | 2 | 1 per half, butyl sound-deadening sheet about 1.7mm thick (Dynamat Xtreme or similar; not 2mm/80mil), cut with the `mat-template-{left,right}` template. See Floor mat (optional), above |

## Ordering the plate

Both materials come from the exact same generated geometry (`scripts/case.py`'s
`build_plate_sketch`), so there's no risk of the two drifting apart.

- **FR4** (recommended default — cheap, orders alongside the PCB):
  upload `plate-fr4-left/` and `plate-fr4-right/` to JLCPCB as two
  separate PCB orders. Settings: 1.6mm thickness, any color, **no
  copper layers needed** (it's Edge.Cuts only) — JLCPCB's "no SMT,
  2-layer, 1.6mm" default works, or ask for their "structural/plate"
  option if offered. Each project's `.kicad_pcb` passes `kicad-cli pcb
  drc` clean (0 violations) — verified.
- **POM**: send `out/plate-pom-{left,right}.dxf` (or the `.step`) to a
  laser or CNC shop, 1.5mm POM (Delrin) sheet.

## Ordering the case

Send `out/case-{left,right}.stl` to a print service (JLC3DP or similar).
MJF PA12 (nylon) is recommended — the heat-set inserts need a material
that can take heat without melting the surrounding plastic, which MJF
nylon handles well. SLA resin also works but glue the inserts in instead
of heat-setting them.

STL export tolerance is 0.05mm chordal deviation, 0.25° angular — fine
enough for FDM/SLA/MJF without generating an excessive mesh.

## Prototyping cheaply first (your own printer)

Before committing to a service print, it's worth doing a fit-check on a
home FDM printer while the real PCB and FR4 plates are on order — much
cheaper, and cheap/fast to iterate if something's off.

- **Material:** PETG is the best balance of toughness and ease. PLA is
  fine too for a pure fit-check, just more brittle.
- **Heat-set inserts work the same as on MJF** — same M2×3 inserts,
  same soldering-iron technique. No design difference.
- **Print orientation:** floor-down, as designed. The walls and all 7
  boss posts are simple vertical extrusions — no supports needed.
- **The same files serve both:** home printer and print service use the
  same `out/` files. For a home print, use the `.stl` files and the
  plate/spacer variant for your plate material (`pom` for a POM or
  printed 1.5mm plate).

## Assembly order

1. **Inserts:** press an M2×3.2mm heat-set insert into each of the 7
   bosses per half that has a PCB hole above it. Leave the spare
   outer/lower boss empty: on first-revision PCBs that's the lower of the
   two, on the next revision the upper one.
2. **Tenting legs, if used:** press an insert into the flat face of each
   leg, hold the tent against the bottom of the case, and drive an M2×6
   screw down from inside the case through the floor into each leg. This
   has to happen while the case is still empty. A floor mat, if used,
   goes in after this; its holes clear the screw heads, so the tent can
   still come off later.
3. **PCB:** lower it onto the bosses, USB connector and TRRS jack lined up
   with their notches. Nothing screws it down yet.
4. **Spacers:** set one on each of the 5 plate-mount holes, pilot down
   into the PCB hole. Four take the standard spacer; the top hole nearest
   the MCU strip takes the narrow one. Or lay the spacer frame on
   instead, pilots down.
5. **Plate:** lay it on and screw it down with 5 M2×10 low-head screws,
   through plate, spacer and PCB into the inserts. Of the two outer/lower
   plate holes, only the one over your PCB's hole gets a screw. Do this
   before fitting any switches: the screw head at the narrow-spacer hole
   overlaps its two neighbouring switches' top housings slightly.
6. **Switches:** press each one through the plate into its hotswap
   socket.
7. **MCU cover:** posts down onto the two holes beside the TRRS jack,
   rim on the case wall, fastened with two M2×12 pan-head screws.
8. **OLED:** plug it into its socket through the cover's slot; it lies
   on top of the cover.
9. **Keycaps.**
10. **Feet:** rubber feet into the recesses on the leg ends, or, without
    tents, stuck to the case bottom over the 4 corner screw holes. If
    using the MagSafe stand, stick a ring onto each half's flat bottom.

**Without the plate mount:** at step 3, screw the PCB down with M2×4
screws, each with an M2.5 washer, at the 5 holes that have a 4.3mm drill.
Skip steps 4 and 5; the switches hold the plate. **Without the MCU
covers:** put a bare M2×4 in each of the two 2.2mm holes beside the TRRS
jack.

## Re-running the generators

From the repo root:

```sh
./build.sh case        # everything: extract, generate, fr4, drc

./build.sh extract     # 1. re-extract from the PCB whenever it changes
./build.sh generate    # 2. regenerate the case, plates and cover (STEP/STL/DXF)
./build.sh fr4         # 3. regenerate the FR4 KiCad plate projects from the DXF
./build.sh drc         # 4. design rule check on both plate projects
```

See the [root README](../README.md#build-commands) for requirements.

## Known first-pass limitations

- USB and TRRS wall notches are generous rectangles, not fitted to a
  specific connector shell — check against your actual cable ends.
- The case's convex outer corners are rounded by the wall offset (~3mm);
  the inside corners where the top edge steps between columns stay sharp.
- Two M2 mounting points per half don't get a plate clearance hole (see
  Mounting, above) — expected, not a bug.
- The MCU cover's height is set from 3D-model part heights, not measured
  parts (see MCU cover, above).
- A direct-soldered Pro Micro (no socket) was found to need a bit more
  clearance than modeled, near the top wall away from the USB notch — not
  yet fixed in the generator, since the design's real target is the
  low-profile Mill-Max sockets (see TODO.md), which sit shorter and may
  not need it. Re-measure once those are in hand.
