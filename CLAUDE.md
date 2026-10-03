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
  directly from the real PCB rather than hand-modeled. Pipeline:
  1. `extract_board.py` (run with KiCad's bundled Python, which has
     `pcbnew`) reads `pcb/cornison.kicad_pcb` and writes `board.json`:
     per-half outline, switch poses, M2 hole centers, MCU/OLED/reset/TRRS
     part bounding boxes.
  2. `case.py` (run with `uv run --with build123d python3 case.py`) reads
     `board.json` and writes the case tray + switch plates (STEP/STL/DXF)
     to `out/`. Set `CASE_PROTOTYPE=1` to skip the MagSafe recess and write
     to `out-prototype/` instead, for a support-free home-printer test.
  3. `make_fr4_plate.py` turns the plate DXF into real KiCad PCB projects
     (`plate-fr4-{left,right}/`) for ordering the plate in FR4 from
     JLCPCB, via the graph-based `dxf_to_loops.py`.
  - See `case/README.md` for the full write-up: stack-up heights, mounting
    hardware, assembly order, and ordering instructions.

## Conventions that caused real, previously-shipped bugs

These aren't style preferences — each one was found after a physical part
came out wrong.

- **`board.json` holds raw KiCad coordinates, where Y points down.**
  `case.py`'s `load_board()` negates every key's rotation once on load,
  specifically because KiCad's footprint angle convention (CCW as drawn on
  its Y-down screen) is the opposite sense of a CCW rotation in those same
  raw numbers. Skipping this gets every switch hole rotated the wrong way.
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
- **The case cavity is built from the real plate footprint, not just the
  PCB outline.** `build_case()` unions in `plate_footprint(plate_sk)` (the
  plate's outer boundary with its holes filled back in) grown by
  `CAVITY_CLEARANCE`, so any local widening done to fix a thin plate wall
  automatically widens the matching case wall too. Building the two from
  independent margins let them drift apart.
- **`dxf_to_loops.py` reconstructs closed loops via a point-adjacency
  graph**, not by trusting the DXF's own edge ordering — build123d's own
  `Wire.order_edges()` has a real bug on this geometry (it silently
  drops a long straight run).

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
- Run `kicad-cli pcb drc` on both plate projects after any geometry change.

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
  head. The PCB's M2 mounting hole (`M2_HOLE_v2` footprint) is a plain
  4.3mm hole with no annular ring, bigger than any standard M2 screw
  head's diameter (flat ≈3.8mm, pan ≈4.0mm, socket cap ≈3.8mm) — a washer
  is required under the screw head to actually clamp the PCB down.
- **Washer:** M2.5-size (2.7mm ID / 6.0mm OD), not M2-size (2.2mm ID /
  5.0mm OD) — the M2.5 washer's larger OD leaves real margin over the
  4.3mm PCB hole; the M2 washer's nominal overlap is only ~0.35mm per
  side.
- **MagSafe ring:** Keebio Magnetic MagSafe Tenting Stand Kit R2, sized to
  Apple's published spec — 54.10mm OD / 46mm ID / 2mm ring thickness.
- **Diodes:** genuine SOD-123 package required (confirmed via the
  `D3_SMD_v2` footprint's pad spacing and 3D model) — a visually-similar
  "0805" SMD diode is a different, incompatible package.

## Order status (as of 2026-10-03 — verify before relying on this)

- PCB is ordered.
- FR4 switch plates (JLCPCB orders, most recently order numbers Y10/Y11)
  were fabricated from pre-fix files: the two angled thumb-key holes per
  half are rotated 30° off, and the plate's thumb-area outline also
  doesn't fit the corrected case cavity. Don't reorder until a home test
  print of the regenerated plate confirms the fix.
- The already-printed JLC3DP case is the mirror-image bug described above
  (3.9mm M2 insert bores too, from before that was corrected) — needs a
  reprint from the current `case/out/case-*.stl`.
- Any MJF nylon plates ordered from that same pre-fix batch are flat, so
  flipping one over gives the correct (non-mirrored) part — no reorder
  needed for those specifically.
- Home test prints run on an Ender-3 V2 in PrusaSlicer. Known-good
  settings found so far: 4 perimeters (the 2.5–3.2mm case walls need more
  than the default to avoid a gap down the middle), slower first layer,
  and a retensioned Y belt (a loose one caused a mid-print layer shift).

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
