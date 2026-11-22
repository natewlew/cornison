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
| 0 – 4.0mm | Floor, flat underneath; deep enough for the tenting legs' inserts |
| 4.0 – 8.0mm | Boss height — clearance for the hotswap sockets + B-side LEDs |
| 8.0 – 9.6mm | PCB (1.6mm) |
| 9.6 – 14.6mm | Air gap above the PCB — standard Cherry MX clearance |
| 13.0 – 14.6mm | Switch plate (1.6mm FR4) |
| 14.6mm | Wall top / plate top, flush |

The floor was 2.5mm until 2026-10-23, when the tenting legs' inserts
moved into it; everything above it moved up 1.5mm with it.

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

- **PCB → case:** 7 bosses per half, one under each of the v1.1 PCB's 7
  M2 mounting holes. (A v1.0 board still sits in the case for a test fit,
  but two of its holes are elsewhere: the outer/lower one a row higher,
  and on the right half the lower-centre one at the board edge. Those get
  no screw.) Press M2×3.2mm heat-set inserts into them (soldering
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

  The plate has 5 holes per half, one over each of these PCB holes. On a
  v1.0 board (test fits only), the outer/lower hole on both halves and the
  right half's lower-centre one have no PCB hole under them: leave those
  plate holes empty.

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
  Every post has a pilot, so it follows the v1.1 board's holes.
  It's hidden under the plate. Inner ribs are about 3.45mm; the strips
  round the outer edge are thinner, 1.2–2mm, because the switches sit
  close to the board edge. Print it top face down, pilots up. Nothing else
  on the top of the PCB is under the plate (checked against every
  top-side pad in the KiCad file), so the frame only has to clear the
  switches.
- **The bottom is flat** apart from a rubber-foot recess at each corner
  (10.4mm across, 0.8mm deep) and the 4 inserts for the tenting legs
  beside them, so a MagSafe ring sticks on anywhere in the middle.

## MCU cover

![inset cover with the OLED](../docs/images/finished/cornison-v1.1%20right%20top%20finished.jpg)

`cover-inset-{left,right}` is a 2mm printed cover over the Pro Micro, TRRS
jack and reset switch, about 20 × 60mm. It stops at the plate's outline,
inside the case wall, so its top is a flat panel with straight outer
edges and the OLED window centred over the Pro Micro. A 45° bevel runs
from its top edge down onto the wall top along the board's top and inner
edges, landing on the case's outer face, so from the side the wall
carries on up into the cover.

| Height above PCB top | Feature |
|---|---|
| 0 – 6.0mm | Two posts, standing on the PCB over the two mounting holes beside the TRRS jack |
| 5.0 – 8.0mm | Bevel, resting on the case wall top along the board's top and inner edges; a 2mm skirt resting on the plate along the angled edge |
| 6.0mm | Cover underside |
| 8.0mm | Cover top (3.0mm above the plate and wall top) |

- **Mounting:** one M2×12mm screw per post, through cover, post and PCB
  into the same heat-set insert an ordinary PCB screw would use (2.4mm of
  thread in the 3.2mm insert). The post's 6mm foot does the washer's job
  at those two holes, so no washer there. At the USB end the cover rests
  on the bevel.
- **OLED:** plugs into a low-profile socket on the PCB through a window
  in the cover, 13.5 × 39.5mm: the module's whole footprint (12 × 38mm,
  measured) plus 0.75mm, so
  everything under the OLED stays in view. Plugged fully into a ~4mm
  socket, the module's board sits 8–9mm above the PCB (measured), only
  0–1mm over the cover's top, so the socket alone holds it. When the
  cover was under it, its pins didn't seat. The window's position depends
  on `OLED_PIN_EDGE` (1.4mm, from the library model, not measured).
- **Reset:** a 2mm hole over the switch for a paperclip, joined to the
  window's side. It sits 1.5mm from the cover's inner edge at the top
  face, but the bevel right outside that edge thickens it going down
  (2.5mm half-way through), so the frame round the window stays a closed
  ring.
- **Pro Micro:** soldered directly on ordinary headers, or on low-profile
  (Mill-Max style) sockets. Either way it has to top out at 5.5mm or less.
  Trim the header pin stubs down to the solder: left long on the first
  build, they stood ~7mm and tipped the cover up at the USB end. Standard 8.5mm sockets put it at about 11mm
  and do not fit — build without the cover and OLED in that case.
- The cover stays out from under every keycap. Its key side is one
  straight edge, then one straight diagonal along the angled thumb keycap;
  the plate fills in under the diagonal's end.
- **USB and TRRS:** the bevel stops at both wall notches, so the plugs
  pass under the cover's edge. Checked against a 10mm TRRS cable grip.
- **Printing:** top face down, posts up. The bevel grows out at 45° from
  the bed: no supports.

**Not yet checked against real parts.** The part heights behind
`COVER_UNDERSIDE_ABOVE_PCB` in `case.py` are measured from the 3D models
in `pcb/kbd`, not from the components themselves. Measure a built board
before ordering covers from a print service.

Two other covers were removed on 2026-11-21: a flat cover that ran out
over the wall top (`cover-{left,right}`), and a two-piece clear cover
(`cover-base-*` under a laser-cut acrylic `cover-clear-*`, on M2
standoffs). Both are in git history before that date.

## MagSafe tenting stand

The Keebio Magnetic MagSafe Tenting Stand Kit R2's ring is adhesive-backed
(measured: 50mm OD, 0.5mm thick) and sticks straight onto the flat case
bottom. No recess is needed, so the case has none. Earlier versions cut a
0.5mm locating pocket, which only meant a 50mm unsupported bridge on a
home printer.

## Tenting legs

![tent and case bottom](../docs/images/case/cornison-v1.1%20right%20case%20tent%20bottom.jpg)

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

The two tall inner legs lean in by the tent angle, so on the desk they
stand plumb rather than square to the tilted case. They meet the case at
its edge and keep their width; going down, they move in from the edge
(at 18°, each one's end sits 13–15mm in from straight below its top),
so on the desk the case's tilted side wall overhangs them a little. The
frame's face along the inner edge leans in with them, so the tent's whole
inner side is one upright face, flush with the legs, with no ledge where
the frame meets a leg. The short outer legs stay square to the case. `TENT_PLUMB=0 ./build.sh
generate` makes the tall ones square to the case too, carrying the
case's side wall on down to the desk.

A beam that would leave the case's footprint is bent inward through a
waypoint. The outline turns inward where the straight bottom edge meets
the thumb cluster.

**How it attaches.** From below, with the keyboard assembled. Beside
each leg is a platform at the mounting face with a counterbored hole.
An **M2×6 screw** goes up through it into an M2×3.2mm heat-set insert
pressed into the case bottom, flush (the 4.0mm floor holds the whole
insert). The head seats 3mm below the mounting face, leaving 3.0mm in
the insert, and a 5mm column under each seat is kept clear down to the
desk for the driver. One short screw works at every leg however tall.

The outer legs' screws sit 13.5mm from the leg, toward the middle of
the tent. Toward the middle is where the inner legs lean, so their
screws sit 13.5mm along the inner edge instead (and 6mm in from the
leg), where the driver can reach.

The frame's two sides (front to back) are strips along the case's own
edge between their two legs, flush with it all the way, inner edge
parallel to it: about 12mm wide on the outer side, about 18mm on the
inner side, wide enough to take the inner legs' screw platforms. The
inner side follows the case edge where it turns in at the thumb cluster. The openings' corners and the joins round
the other platforms are rounded off (`TENT_FILLET_R`, 4mm). `tent_leg_layout()` in `scripts/case.py` places them for both the
case and the tent.

Before 2026-10-23 it went the other way round: inserts in the legs,
screws down from inside the case, so the PCB had to come out to change
the tent. Those tents don't fit a new case, and old cases have no
inserts.

**Angle.** Set with the `TENT_ANGLE_DEG` environment variable, default
18°:

```sh
TENT_ANGLE_DEG=15 ./build.sh generate
```

The console output prints each leg's height.

**Hardware per half:** 4 × M2×3.2mm heat-set insert in the case bottom
(the same part as the case bosses), 4 × M2×6mm low-head screw, 4 × 10mm
round rubber foot.

**Rubber feet.** The desk end of each leg has a round recess for a
10 × 2mm rubber foot: 10.4mm across and 0.8mm deep, so the foot stands
1.2mm proud. It is cut square to the desk plane, and sits 2mm off the
leg's centre toward the middle of the tent so there is a rim all the way
round (`TENT_RUBBER_*` in `scripts/case.py` for a different foot).

**Weight (optional).** A shallow band across the middle of the tent,
beam to beam and square to the case, has a 3 × 3 grid of cells for stick-on
tire (wheel balance) weight segments, 19 × 16 × 4mm. Fill as many as
you like: 8–9 at ¼ oz (7g) each is about 60g per half. Each cell is
19.4 × 16.4 × 4.4mm and opens on the mounting face, so bolting the tent
on traps the weights against the case bottom; their own adhesive can
hold them in the cell too. The band is 6.4mm deep (2mm floor), only
2.4mm deeper than the beams, and stays well clear of the desk. Segment
sizes vary by brand: `TENT_WEIGHT_*` in `scripts/case.py` sets the cell
size and grid, and `TENT_WEIGHT_CELLS = (0, 0)` drops the band.

**Printing.** Flat mounting face down on the bed, legs pointing up; no
supports needed. Each weight cell's floor prints as a 16mm bridge.

**Not yet confirmed on a real part:** inserts pressed into the case
bottom from below, and the driver reaching the screws past the legs;
and that the half sits steady on the desk at the default angle.

## Floor mat (optional)

A butyl sound-deadening mat (car "Dynamat"-style sheet) on the case floor
damps the printed floor and adds about 20g per half. It has to fit
between the floor and the hotswap sockets on the PCB's underside: 4.0mm
under the PCB, less ~1.8mm of socket, so use **~1.7mm sheet (Dynamat
Xtreme, 67mil), not the common 2mm/80mil mats**. It has to be pure
butyl: a Kilmat 80mil sheet tried for this smelled of asphalt, which
means it is asphalt-based or blended and will off-gas, worst when warm,
a foot from your face.

`case.py` writes a cutting template per half: `mat-template-{left,right}.stl`
(a 0.6mm print) and `.dxf` (to print 1:1 on paper). It is the cavity
pulled 0.5mm in from the wall, with 10mm holes at the bosses (2mm clear
all round each 6mm boss) and at the tent screw heads, and no mat under
the MCU strip, where the through-hole pins of the Pro Micro, TRRS jack,
reset switch and OLED header stick out under the PCB right over the
mat's foil. The generator checks a 1.7mm mat against the case solid.
Each template is labelled LEFT or RIGHT over FOIL SIDE: raised on the
print, on its own `label` layer in the DXF (it's not a cut line).

Both files are in the real-world frame, the same as the case STL: lay
the template on the **foil side** with the label reading normally, or
flip it over (label reads backwards) if tracing on the backing paper.
The halves are not mirror images of each other (different thumb
clusters), so a left traced twice can't be flipped into a right.

Cutting, from the first build (2026-10-21): heavy-duty scissors handle
the outline. For the holes, use a **10mm hollow punch** (leather/gasket
punch) and a mallet on a scrap board. Every hole is that size, so one
punch does them all. A craft knife works but is slow and ragged in
butyl. Trace with a fine marker and cut on the inside of the line. Chill
the sheet first so the butyl doesn't drag, and test-fit with the backing
still on. When sticking it down, peel the backing back from one end and
press down progressively, so the exposed butyl never gets near a boss:
it's tar-like and hard to get off once it's on the plastic. The foil is
conductive and faces the sockets with ~0.5mm to spare; a layer of Kapton
tape over it is cheap insurance.

## Foam (optional)

![case foam](../docs/images/case/cornison-v1.1%20left%20case%20with%20case%20foam.jpg)

Two foam pieces per half. Each has a cut-only DXF in `out/` (no label, in
the real-world frame seen from above) for an online cutting service. Or
cut them by hand from a template:

- **Case foam:** goes on the case floor *instead of* the butyl mat. Its
  outline is exactly the mat's, so cut it with the **mat template**
  (`mat-template-{left,right}`; ignore "FOIL SIDE") and the same 10mm
  punch. The cut-only file is `foam-case-{left,right}.dxf`. Use **2mm**
  foam: the gap is 4.0mm, less the 1.8mm hotswap sockets, so 2mm leaves
  0.2mm under them. It's a flat sheet under every part, with no socket
  cutouts (at 19mm pitch they'd leave a lace of ~3mm strips). It also
  covers the underglow LEDs.
- **Plate foam:** goes between the PCB and the plate, with the **loose
  spacers** standing through its holes (not with the spacer frame, which
  fills the same gap). It's the plate's outline, with a 14.5mm opening
  round each switch body and a **6mm** hole (hollow punch) round each
  spacer. Near a switch the spacer hole merges into that switch's
  opening. The punch template is `foam-plate-template-{left,right}`
  (STL to print at 0.6mm, or DXF to print 1:1 on paper): the outline,
  solid, with the five spacer circles, labelled LEFT or RIGHT in bold
  (reading backwards means the template is upside down). The switch
  openings are cut from a 1:1 paper print (below). The cut-only file is
  `foam-plate-{left,right}.dxf`.
  The gap is 3.5mm under a POM plate, 3.4mm under FR4 and 3.0mm under
  MJF. The generator checks it at 3.0mm, so it fits under every plate;
  3–3.5mm PE or Poron compresses to fit. The webs between openings are
  ~4.5mm, less round the thumb keys. Anything under 2mm is dropped. Some
  services' minimum feature size (Ponoko's EVA: 6mm) is larger than that,
  so check before ordering.

Cutting by hand: mark on the foam's top face (label reading normally).
The case foam uses the mat template; cut on the inside of the line and
punch the boss holes. For the plate foam, punch the five spacer holes
with the punch template, then print `foam-plate-{left,right}.dxf` 1:1 on
paper, which has every cut line, and cut along it with a fresh blade and
a steel rule: several light passes, not one heavy one.

**Plate-foam cutting jig: work in progress, don't rely on it yet.**
`foam-plate-jig-{bottom,top}-{left,right}` is still generated, but on the
first test print the foam kept pulling out from between the two
templates while cutting. The idea, for 3mm foam: the foam is clamped
between two printed copies of its shape, so the knife follows a template
edge at both faces and the thin webs between openings can't drag or
stretch.

1. Punch the five 6mm spacer holes first, with the punch template: the
   foam's outline, solid, with a circle at each spacer. Lay it on the
   foam, mark the circles, punch.
2. Lay the foam on the bottom template, its holes over the pins. It only
   fits one way up, and only on its own half's template: if it won't sit
   flat, it's flipped.
3. Press the top template onto the pin tips. The pins hold it 2.7mm
   above the bottom one, a light grip on 3mm foam that doesn't crush it.
4. On a cutting mat, cut round the outside and every switch opening,
   along the top template's edges. Each cut goes 6.7mm deep (template,
   foam, template), so use a #11 blade or a snap-off knife.

The tips are a press fit (3.0mm tip in a 3.1mm hole). If they're too
tight or loose on your printer, change `FOAM_JIG_TIP_FIT`. For other foam,
set `FOAM_JIG_FOAM_T`.

Assembly with plate foam: lay the foam on the PCB, drop the spacers
through its holes into the PCB holes, then the plate and its screws, then
the switches through plate and foam. Adhesive-backed foam goes adhesive
side down. Don't laser-cut PVC foam (it gives off chlorine), and have
Poron (polyurethane) knife- or die-cut rather than lasered. Neither is
built yet.

## Hardware BOM (per keyboard, both halves)

| Item | Qty | Notes |
|---|---|---|
| M2×3.2mm heat-set insert | 14 (+8 for tenting legs) | 7 per half, one in each case boss. [McMaster 94459A767](https://www.mcmaster.com/94459A767/) is a confirmed fit. +4 per half for the tenting legs, pressed into the case bottom |
| M2×4mm low-head screw | 0 (4 without the MCU covers) | Only for the two holes per half beside the TRRS jack when no cover is fitted; those holes are 2.2mm and need no washer. 14 total if skipping the spacer/screw-down mount entirely (use M2×4 everywhere the table below says M2×10) |
| M2×6mm low-head screw | 8 | Tenting leg → case, 4 per half, up from below — same length at every leg regardless of its height (see Tenting legs, above) |
| M2×10mm low-head screw | 10 | Plate → spacer → PCB → case bosses, 5 per half |
| M2×12mm pan-head screw | 4 | MCU cover → case bosses, 2 per half |
| M2.5 washer, 2.7mm ID / 6.0mm OD | 0 (10 if skipping the plate mount) | Only needed under a bare M2×4 screw on one of the 4.3mm PCB holes, which the plate mount no longer leaves any of. Required there (fits M2 screws fine, just a looser slip fit) — the PCB's mounting hole is 4.3mm with no annular ring, bigger than any standard M2 screw head. McMaster's M2-labeled washer (5.0mm OD) only just clears it; M2.5 size gives real margin. Not needed under the M2×6, M2×10 (bears on the plate's small clearance hole) or M2×12 (bears on the cover's printed post) |
| Rubber feet, 10 × 2mm round | 8 | 4 per half. On a tented half they go in the recesses on the leg ends; without a tent, in the 4 corner recesses on the case bottom |
| MagSafe ring (Keebio kit) | 2 | 1 per half, adhesive-backed — alternative to tenting legs, see above |
| Case | 2 | 1 per half, 3D printed (`case-{left,right}.stl`), see Ordering the case below |
| Switch plate | 2 | 1 per half — FR4 (from the `plate-fr4-{left,right}/` KiCad projects), or POM or MJF nylon (`plate-{pom,mjf}-*`), see below |
| MCU cover | 2 | 1 per half, 3D printed (`cover-inset-{left,right}.stl`) |
| Plate-mount spacer, standard | 8 (+ spares) | 4 per half, 3D printed (`spacer-{pom,fr4,mjf}.stl` — pick the one matching your plate material) |
| Plate-mount spacer, narrow | 2 (+ spares) | 1 per half, for the top hole nearest the MCU strip (`spacer-narrow-{pom,fr4,mjf}.stl`) |
| Spacer frame (instead of the 10 loose spacers) | 2 | 1 per half, 3D printed (`spacer-frame-{pom,fr4,mjf}-{left,right}.stl`) |
| Tenting leg | 2 | 1 per half, 3D printed (`tent-{left,right}.stl`) — alternative to rubber feet |
| Tire weight segment, 19 × 16 × 4mm | up to 18 | Optional tent weight, up to 9 per half in the cells in the middle of the tent. Stick-on wheel balance weights, cut from the strip |
| Floor mat (optional) | 2 | 1 per half, butyl sound-deadening sheet about 1.7mm thick (Dynamat Xtreme or similar; not 2mm/80mil), cut with the `mat-template-{left,right}` template. See Floor mat (optional), above |
| Case foam (optional, instead of the floor mat) | 2 | 1 per half, 2mm foam cut with the `mat-template-{left,right}` template and 10mm punch (or `foam-case-{left,right}.dxf`). See Foam (optional), above |
| Plate foam (optional, with the loose spacers) | 2 | 1 per half, 3–3.5mm PE/Poron (3mm under an MJF plate) cut with the `foam-plate-template-{left,right}` template and a 6mm punch (or `foam-plate-{left,right}.dxf`). See Foam (optional), above |

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
   bosses per half.
2. **Tenting-leg inserts, if you might use the tents:** press an insert
   into each of the 4 holes in the case bottom beside the corner
   recesses, from below, flush with the bottom. The tent itself goes on
   at the end.
3. **PCB:** lower it onto the bosses, USB connector and TRRS jack lined up
   with their notches. Nothing screws it down yet.
4. **Spacers:** set one on each of the 5 plate-mount holes, pilot down
   into the PCB hole. Four take the standard spacer; the top hole nearest
   the MCU strip takes the narrow one. Or lay the spacer frame on
   instead, pilots down.
5. **Plate:** lay it on and screw it down with 5 M2×10 low-head screws,
   through plate, spacer and PCB into the inserts. Do this
   before fitting any switches: the screw head at the narrow-spacer hole
   overlaps its two neighbouring switches' top housings slightly.
6. **Switches:** press each one through the plate into its hotswap
   socket.
7. **MCU cover:** posts down onto the two holes beside the TRRS jack,
   bevel on the case wall, fastened with two M2×12 pan-head screws.
8. **OLED:** plug it into its socket through the cover's window.
9. **Keycaps.**
10. **Feet:** either hold the tent against the case bottom and drive an
    M2×6 screw up through each platform into the insert, with rubber feet
    in the recesses on the leg ends; or, without tents, rubber feet in
    the 4 corner recesses on the case bottom. If using the MagSafe stand,
    stick a ring onto each half's flat bottom.

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

- The USB and TRRS wall notches no longer run down to the floor
  (2026-10-21). The USB notch is a rectangle whose wall comes up to 1.0mm
  under the PCB top, past its underside. That clears the measured 3mm
  USB-C socket centred 1–2mm up; the cable's grip stays outside the case.
  The TRRS notch is a U round the jack's axis, 11mm wide, sized for a 10mm
  grip (`TRRS_PLUG_D` in `case.py`) so most TRRS cables fit. Its bottom is
  1.4mm under the PCB's underside at the middle; its sides come up past
  the underside. Not yet checked against a range of real cables.
- The case's convex outer corners are rounded by the wall offset (~3mm);
  the inside corners where the top edge steps between columns stay sharp.
- Two M2 mounting points per half don't get a plate clearance hole (see
  Mounting, above) — expected, not a bug.
- The MCU cover's height is set from 3D-model part heights, not measured
  parts (see MCU cover, above).
- A direct-soldered Pro Micro (no socket) was found to need a bit more
  clearance than modeled, near the top wall away from the USB notch — not
  yet understood. That case predates the straight-sided outline; in the
  current model the Pro Micro's board edge (from its footprint) has
  2.3mm to the top wall and 3.2mm to the side wall, so what hit is
  something the footprint doesn't show. Find out on the real part before
  changing the generator.
