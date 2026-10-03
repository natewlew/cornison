# cornison case

A 3D-printed tray case + switch plate, generated directly from the real
PCB geometry (`../pcb/cornison.kicad_pcb`). No copper is touched;
everything here only reads the board to place bosses, notches and cutouts
correctly. Re-run the generators any time the PCB changes.

## What's in here

| File / dir | What it is |
|---|---|
| `extract_board.py` | Reads the PCB (KiCad python) → `board.json`: per-half outline, switch poses, M2 holes, MCU/OLED/reset/TRRS part positions |
| `case.py` | Reads `board.json` (build123d, via `uv run --with build123d`) → the case tray + switch plate, as STEP/STL/DXF in `out/` |
| `dxf_to_loops.py` | Turns a plate DXF into closed point loops (graph-based, endpoint-matching — doesn't trust any single edge ordering) |
| `make_fr4_plate.py` | Reads the DXF loops → `plate-fr4-{left,right}/`, a KiCad project per half for ordering the plate in FR4 |
| `preview/` | The 3D preview artifact (three.js) used to sanity-check the design by eye |
| `out/` | Generated STEP/STL/DXF — gitignored-worthy, regenerate anytime |

## Stack-up

Heights measured from the case's true bottom (z=0):

| Z | Feature |
|---|---|
| 0 – 2.5mm | Floor. MagSafe ring recesses into it from below (see below) |
| 2.5 – 6.5mm | Boss height — clearance for the hotswap sockets + B-side LEDs |
| 6.5 – 8.1mm | PCB (1.6mm) |
| 8.1 – 13.1mm | Air gap above the PCB — standard Cherry MX clearance |
| 11.5 – 13.1mm | Switch plate (1.6mm FR4) |
| 13.1mm | Wall top / plate top, flush |

The plate extends over the whole MCU/OLED/reset area — the Pro Micro is
soldered directly to the PCB (no access needed), and the OLED module
plugs into its 4-pin header from above through a slot cut for the header
pins specifically (not the display), sized from the real footprint's pad
spacing. The OLED sits exposed on top of the plate, no separate cover,
no soldering for the display — Boardsource-Corne style. A small round
hole gives paperclip access to the reset switch underneath.

Every switch cutout is a plain 14×14mm square, including the 1.5u thumb
key — the switch body is always that size regardless of keycap width
(verified against the stock corne plate's own `SW_Hole` footprint). Where
a hole would otherwise break out through the plate's edge (the outermost,
most-rotated thumb key and its neighbor sit close to the real board edge
there), the plate — and the case wall around it — locally, smoothly
widens just enough to keep the hole fully enclosed.

## Mounting

- **PCB → case:** 7 bosses per half, positioned under the PCB's existing
  M2 mounting holes. Press M2×3.2mm heat-set inserts into them (soldering
  iron or heat-set tool), then screw the PCB down from above with M2×4mm
  low-head screws **and an M2 washer under each screw head**. The boss
  bore (`INSERT_BORE_D`) and boss depth (`BOSS_H`) in case.py are sized to
  McMaster 94459A767's own published spec for this exact insert (M2×0.4mm,
  brass, 3.2mm installed length): 3.2mm hole diameter, 4mm minimum
  surrounding material.

  The washer isn't optional: the PCB's M2 mounting holes (`M2_HOLE_v2`
  footprint) are a plain 4.3mm hole with no annular ring, sized for the
  original sandwich-case design where a standoff barrel passes fully
  through it. No standard M2 screw head clears 4.3mm (flat ~3.8mm, pan
  ~4.0mm, socket cap ~3.8mm, all per their ISO/DIN specs) — without a
  washer bridging the hole, any of them just drops straight through and
  clamps nothing. Use a washer with an OD meaningfully bigger than 4.3mm
  (5.5–6mm gives a comfortable bearing ring; a bare 5mm standard washer
  only overlaps by ~0.35mm per side).
- **Plate → case:** not screwed down. It drops in and is held by the
  switches once they're clipped through it into the hotswap sockets,
  same as a standard tray-mount board.
- **Nothing goes through the bottom** — it stays flat and clean for the
  MagSafe ring.

Two of the seven M2 mounting points per half sit close enough to a
neighboring switch that the plate can't have a full clearance hole there
(confirmed geometrically, not a generator bug — the switch cutout itself
already provides more clearance than that mounting point would need).
Those two just don't get a plate standoff; all 7 work fine for the
PCB-to-case screws, which is all that's actually load-bearing.

## MagSafe tenting stand

Sized for the Keebio Magnetic MagSafe Tenting Stand Kit R2, using Apple's
published MagSafe ring spec: **54.10mm OD / 46mm ID, 2mm ring thickness**.
The bottom has a 2mm-deep recess for the ring, centered under the key
cluster on each half. The floor is locally thickened under that recess
(from 2.5mm up to 4.5mm before the recess is cut) so it ends up back at
the normal 2.5mm of material, not thinned out.

Double-check the ring's actual adhesive-backed diameter against your kit
before printing — `MAGSAFE_OD`/`MAGSAFE_ID`/`MAGSAFE_DEPTH` in `case.py`.

## Hardware BOM (per keyboard, both halves)

| Item | Qty | Notes |
|---|---|---|
| M2×3.2mm heat-set insert | 14 | 7 per half, case bosses. [McMaster 94459A767](https://www.mcmaster.com/94459A767/) is a confirmed fit |
| M2×4mm low-head screw | 14 | PCB → case bosses |
| M2.5 washer, 2.7mm ID / 6.0mm OD | 14 | Required under each PCB screw (fits M2 screws fine, just a looser slip fit) — the PCB's mounting hole is 4.3mm with no annular ring, bigger than any standard M2 screw head. McMaster's M2-labeled washer (5.0mm OD) only just clears it; M2.5 size gives real margin |
| Rubber feet, ~8mm | 8 | 4 per half, corner recesses already modeled |
| MagSafe ring (Keebio kit) | 2 | 1 per half, adhesive-backed |
| Switch plate | 2 | 1 per half — FR4 or POM, see below |

## Ordering the plate

Both materials come from the exact same generated geometry (`case.py`'s
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
- **One exception:** the MagSafe recess is a 54mm-wide pocket cut into
  the bottom face, which means an unsupported 54mm bridge right at the
  first layer if printed floor-down — most FDM printers will sag or
  need supports there, for a feature that doesn't affect PCB/plate fit
  at all. Set `CASE_PROTOTYPE=1` to skip it entirely and write to
  `out-prototype/` instead of `out/` (so it never overwrites the real
  service-print files):
  ```sh
  CASE_PROTOTYPE=1 uv run --with build123d python3 case.py
  ```
  This gives a completely support-free print. Switch back to the
  MagSafe-enabled version once you're ready to order the real MJF/SLA
  case.

## Assembly order

1. Press M2×3 heat-set inserts into the 7 bosses per case half.
2. Screw the PCB down onto the bosses (M2×4, from above).
3. Drop the plate on top.
4. Press each switch through the plate into its hotswap socket.
5. Plug the OLED module into its header through the plate's slot.
6. Snap on keycaps.
7. Stick a MagSafe ring into each half's bottom recess.

## Re-running the generators

```sh
cd case
# 1. Re-extract from the PCB whenever it changes (needs KiCad's own python)
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 extract_board.py

# 2. Regenerate the case + plates (STEP/STL/DXF)
uv run --with build123d python3 case.py

# 3. Regenerate the FR4 KiCad plate projects from the DXF
uv run --with build123d python3 make_fr4_plate.py

# 4. Rebuild the 3D preview artifact
cd preview && python3 build_preview.py
```

## Known first-pass limitations

- USB and TRRS wall notches are generous rectangles, not fitted to a
  specific connector shell — check against your actual cable ends.
- The case's outer corners are left sharp rather than filleted; the real
  outline's tab-notch geometry is too tight for a uniform fillet radius
  everywhere without more careful per-corner classification.
- Two M2 mounting points per half don't get a plate clearance hole (see
  Mounting, above) — expected, not a bug.
