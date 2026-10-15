# TODO

What still needs ordering, measuring and confirming before the Cornison
build is final. Started 2026-10-11.

## To order

Sockets, one order (Mouser suggested; DigiKey's page for the 12-position
socket says they no longer carry it):

- [ ] 4 × Mill-Max `315-43-112-41-003000` — 12-position low-profile socket, 2 per Pro Micro
- [ ] 60 × Mill-Max `3320-0-00-15-00-00-03-0` — pins for the Pro Micros (48 needed, rest spare)
- [ ] 2 × Samtec `SLW-104-01-G-S` — 4-position low-profile OLED socket, takes the OLED's standard square pins
- [ ] Check Mouser's price and stock for the 12-position socket before ordering (not confirmed)

Reset switches (missed in the first order):

- [ ] 2 × reset switch — 2-pin through-hole tactile switch, 3.5 × 6mm body, about 4.3mm tall, legs 6.5mm apart. Sold by keyboard shops as a "Corne reset switch"; add a spare

Hardware for the MCU covers:

- [ ] 4 × M2 × 12mm pan-head screw

Hardware for mounting the plate down (not just switch-held):

- [ ] 10 × M2 × 10mm low-head screw
- [ ] Print 8 × standard spacer (4 per half, + a few spares) — `spacer-{pom,fr4,mjf}` from `case/out/`, matching the plate material in use
- [ ] Print 2 × narrow spacer (1 per half, + a spare) — `spacer-narrow-{pom,fr4,mjf}`, for the top hole nearest the MCU strip
- [ ] Reprint the plates (or drill 2.3mm at that hole) to get the fifth plate hole per half
- [ ] Or, instead of the loose spacers: print 2 × spacer frame — `spacer-frame-{pom,fr4,mjf}-{left,right}`, top face down

Hardware for tenting legs (if using them instead of rubber feet/MagSafe):

- [ ] 8 × M2 × 3.2mm heat-set insert (one per leg, same part as the case bosses)
- [ ] 8 × M2 × 6mm low-head screw
- [ ] Print 2 × tenting leg — `tent-{left,right}.stl` from `case/out/`, default 18° (set `TENT_ANGLE_DEG` and regenerate to try other angles first)

Hold until the checks below pass:

- [ ] FR4 switch plates (new design with the MCU opening)
- [ ] Case reprint from `case/out/case-{left,right}.stl` — any case printed before 2026-10-12 has one boss per half about 10mm off its PCB hole (skip that screw on it); any printed before the tenting-leg change has a blind foot recess, not the through-hole the legs need
- [ ] MCU covers from a print service, if not home-printed

## To measure on the test build

The test build has the Pro Micro direct-soldered (no socket), so it goes
without the MCU cover and OLED. Measure each of these from the top
surface of the PCB. The cover's underside is 6.0mm up, so all three must
come in under that:

- [ ] TRRS jack, highest point (assumed 5.0mm)
- [ ] Reset switch, highest point (assumed 5.2mm)
- [ ] Pro Micro on the Mill-Max sockets, highest point including pin stubs (assumed under 5.5mm)

If any is over, change `COVER_UNDERSIDE_ABOVE_PCB` in `case/scripts/case.py` and
run `./build.sh generate`.

## To confirm on the test build

Firmware:

- [ ] Bootloader on a bare Pro Micro: serial port (Caterina, flash as-is) or `ATm32U4DFU` (add `"bootloader": "atmel-dfu"` to `keyboard.json`)
- [ ] `diode_direction: COL2ROW` is right — every key registers on both halves
- [ ] Handedness sets correctly with `EH_LEFT` / `EH_RGHT`
- [ ] Both halves work together over TRRS

Soldering details the build guide leaves vague:

- [ ] What the diode orientation mark on the PCB looks like
- [ ] What the LED orientation marks look like (if fitting LEDs)
- [ ] LED soldering temperature against the original Corne guide (the guide says 320°C, unverified)

Fit:

- [ ] All 7 bosses line up with the PCB's holes on a case printed from the corrected files (both halves)
- [ ] The extra boss at the next-revision hole spot props up today's PCB without pressing on anything on its underside
- [ ] USB connector on the Keebio Pro Micro stands less than about 2mm off its board, so it fits face-down on the Mill-Max sockets
- [ ] Once Mill-Max sockets are in: re-check the Pro Micro's clearance against the top wall away from the USB notch — the direct-soldered test build needed ~1mm/2mm of hand-trimming there, but the low-profile mount may sit shorter and need less (or none)

- [ ] Mill-Max pins fit the holes in the Keebio USB-C Pro Micro
- [ ] USB plug fits through the case's USB notch
- [ ] TRRS plug fits through the case's TRRS notch
- [ ] PCB drops into the case once the breakaway tab stubs are filed

## To confirm with a home-printed cover and plate

- [ ] Plate drops in around the MCU strip without touching the TRRS jack, reset switch or Pro Micro
- [ ] Spacer pilots drop into the PCB's 4.3mm holes at the 5 plate-mount points per half and don't wobble
- [ ] M2 × 10 screws pull the plate down flush at those 5 points without binding on a switch
- [ ] At the fifth hole (top, nearest the MCU strip): the narrow spacer fits between the switch bodies, and the screw head seats on the plate without fouling the two neighbouring switch housings (it overlaps their footprint by 0.27mm on paper)
- [ ] At the 4 plate-mount holes per half that land under a keycap (per `report_plate_mount()`'s printout), the keycap's skirt still clears the low-head screw when fully pressed
- [ ] Cover posts land on the two mounting holes beside the TRRS jack
- [ ] M2 × 12 screws bite into the inserts (expected 2.4mm of thread)
- [ ] Cover clears every keycap when pressed, especially the 1.5u thumb key next to the lower post
- [ ] OLED header passes through the cover slot and the OLED lies flat on the cover (pins may need about 0.5mm trimmed)
- [ ] Paperclip reaches the reset switch through the 2mm hole
- [ ] USB and TRRS plugs still go in with the cover on

## To confirm with a home-printed spacer frame

- [ ] Frame drops onto the PCB around the switches, pilots into the 5 mounting holes
- [ ] Switches still clip into the plate with the frame underneath (openings are 15.6mm, the top-housing size)
- [ ] The 1.2–2mm strips round the outer edge survive printing and handling

## To confirm with a home-printed tenting leg

Print it flat mounting face down, legs up. It goes on before the PCB:
the screws go in from inside the case.

- [ ] Flat face sits flush against the underside of the case, all 4 legs and the beams touching
- [ ] Inserts press squarely into the flat face of each leg
- [ ] M2 × 6 screws go down through the case floor into the leg inserts and clamp (expected 3.2mm of thread)
- [ ] Screw heads on the case floor clear what is under the PCB — two per half sit under a switch socket or the Pro Micro's pins, with about 0.5mm to spare over a 1.6mm head by the numbers; use low-head screws
- [ ] 10 × 2mm rubber feet drop into the recesses on the leg ends and stand proud of them
- [ ] Assembled half sits steady on the desk at 18°, all 4 legs flat, no rocking or sliding
- [ ] Inner-edge-up tilt is comfortable with both halves on the desk

## Repo work still open

- [x] Run `./build.sh fr4` and `./build.sh drc` (done 2026-10-13, 0 violations)
- [ ] Re-export the Gerber zips in `case/plate-fr4-{left,right}/production/` from KiCad before any FR4 order — they're still the 2026-10-02 export of the old plate
- [x] Move the outer/lower PCB mounting hole down one row in `pcb/cornison.kicad_pcb` (done 2026-10-14): left (29.61, 64.28) → (29.61, 83.28), right (267.10, 64.27) → (267.11, 83.28), each exactly on its four-key junction. Each hole's pad is back on its footprint origin (it had been dragged ~10mm off it). Jogged `col1`/`col0_r` (F.Cu) and `VCC`/`VDD` (B.Cu) 0.5mm away there, leaving 0.64–0.78mm to the hole edge. DRC matches the board before the change (no new violations, 0 unconnected); `board.json` re-extracted; case, plate and spacer frame unchanged
- [ ] Look over the moved holes and jogged tracks in KiCad, then regenerate the PCB fab outputs (`pcb/production/` is still the 2026-09-26 export of the first revision) before ordering the next PCBs
- [ ] Once the first-revision PCBs are retired: drop the old spot (and the whole either/or mechanism) — remove `EITHER_OR_HOLES` in `case/scripts/case.py` and run `./build.sh case`; the case goes back to 7 bosses, the plate to 5 mounting holes, and every spacer-frame post gets its pilot back
- [ ] Foam, later: plate foam (~3.5mm Poron/PE, between PCB and plate) used with the loose spacers instead of the spacer frame, and case foam under the PCB. Generate a flat cutting template (DXF/SVG) from the spacer frame's outline, with holes round the 5 spacer posts
- [ ] Enable RGB in the firmware, if fitting LEDs
- [ ] Add photos to `docs/buildguide.md` and rewrite its "confirm on first build" sections
- [ ] Commit the uncommitted work (`docs/`, `firmware/`, `TODO.md`, case and README changes)
