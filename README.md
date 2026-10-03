# Cornison

A split mechanical keyboard based on [foostan](https://github.com/foostan)'s
[Corne Cherry v3](https://github.com/foostan/crkbd), with a few extra keys
added in a [Levinson](https://github.com/wilba6582/Levinson)-style layout —
the name is a mix of **Corne** and **Levinson**.

- **Left half:** the standard Corne 3×6 grid, plus 3 thumb keys and
  dedicated Ctrl, Alt, and Cmd keys.
- **Right half:** the standard Corne 3×6 grid, plus 2 thumb keys and 4
  arrow keys.
- 48 keys total, Kailh/Gateron hotswap sockets (no soldering switches),
  Pro Micro (or Elite-C/Sea-Picro EXT) controller per half, OLED display,
  TRRS between halves, optional per-key and underglow RGB LEDs.
- A 3D-printed case and switch plate, generated directly from the PCB
  rather than hand-modeled, so it stays in sync with any board change.

## Repository layout

| Path | What's in it |
|---|---|
| `pcb/` | KiCad project (schematic, PCB, both halves in one panel) |
| `pcb/kbd/` | [foostan/kbd](https://github.com/foostan/kbd) footprint/symbol library (submodule) |
| `case/` | Case + switch plate generator — see [case/README.md](case/README.md) |
| `case/out/` | Generated STEP/STL/DXF for the case and plates (gitignored, regenerate locally) |
| `case/plate-fr4-{left,right}/` | KiCad projects for ordering the switch plate in FR4 |

## Editing the PCB

Open `pcb/cornison.kicad_pro` in KiCad. `pcb/kbd` is a git submodule — after
cloning, run:

```sh
git submodule update --init --recursive
```

## Regenerating the case and plates

The case and plates are generated from the PCB, not drawn by hand. After
any change to the PCB:

```sh
cd case

# 1. Re-extract geometry from the PCB (needs KiCad's bundled python3)
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 extract_board.py

# 2. Regenerate the case + plates (STEP/STL/DXF)
uv run --with build123d python3 case.py

# 3. Regenerate the FR4 KiCad plate projects
uv run --with build123d python3 make_fr4_plate.py
```

See [case/README.md](case/README.md) for the full write-up: stack-up
heights, mounting hardware, assembly order, and how to order each part.

## Ordering

- **PCB:** upload the Gerbers in `pcb/production/` to a fab (JLCPCB).
- **Switch plate (FR4):** upload `case/plate-fr4-{left,right}/production/`
  to a fab as two separate PCB orders — see
  [case/README.md](case/README.md#ordering-the-plate) for settings.
- **Case:** send `case/out/case-{left,right}.stl` to a 3D-print service
  (MJF nylon recommended) or print at home — see
  [case/README.md](case/README.md#ordering-the-case).

## Credits

Based on [foostan/crkbd](https://github.com/foostan/crkbd) (MIT licensed).
Uses the [foostan/kbd](https://github.com/foostan/kbd) footprint/symbol
library. See [LICENSE](LICENSE).
