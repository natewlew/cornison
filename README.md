# Cornison

A split mechanical keyboard based on [foostan](https://github.com/foostan)'s
[Corne Cherry v3](https://github.com/foostan/crkbd), with a few extra keys
added in a [Keebio Levinson](https://github.com/Keebio/Levinson)-style
layout (an ortholinear grid-plus-thumb-keys arrangement in the same family
as [Let's Split](https://github.com/qmk/qmk_firmware/tree/master/keyboards/lets_split)) —
the name is a mix of **Corne** and **Levinson**.

![Cornison](docs/images/finished/cornison-v1.1%20both%20front%20portrait%20finished.jpg)

- **Left half:** the standard Corne 3×6 grid, plus 3 thumb keys and
  dedicated Ctrl, Alt, and Cmd keys.
- **Right half:** the standard Corne 3×6 grid, plus 2 thumb keys and 4
  arrow keys.
- 48 keys total, Kailh/Gateron hotswap sockets (no soldering switches),
  Pro Micro (or Elite-C/Sea-Picro EXT) controller per half, OLED display,
  TRRS between halves, optional per-key and underglow RGB LEDs.
- A 3D-printed case and switch plate, generated directly from the PCB
  rather than hand-modeled, so it stays in sync with any board change.

## Gallery

<img src="docs/images/finished/cornison-v1.1%20left%20top%20finished.jpg" alt="Left half from above" width="49%"> <img src="docs/images/finished/cornison-v1.1%20right%20top%20finished.jpg" alt="Right half from above" width="49%">

<img src="docs/images/finished/cornison-v1.1%20both%20front%20finished.jpg" alt="Both halves" width="49%"> <img src="docs/images/case/cornison-v1.1%20case%20assembled%20portrait.jpg" alt="Both halves on tents, from the side" width="49%">

<img src="docs/images/finished/cornison-v1.1%20right%20front%20finished.jpg" alt="Right half tented, from the front" width="49%"> <img src="docs/images/finished/cornison-v1.1%20right%20front%20portrait%20finished.jpg" alt="Right half tented, portrait" width="49%">

## Repository layout

| Path | What's in it |
|---|---|
| `pcb/` | KiCad project (schematic, PCB, both halves in one panel) |
| `pcb/kbd/` | [foostan/kbd](https://github.com/foostan/kbd) footprint/symbol library (submodule) |
| `build.sh` | Runs every generator — see [Build commands](#build-commands) |
| `case/` | Case, switch plate and MCU cover generator — see [case/README.md](case/README.md) |
| `case/scripts/` | The generator scripts `build.sh` calls |
| `case/out/` | Generated STEP/STL/DXF for the case and plates (gitignored, regenerate locally) |
| `case/plate-fr4-{left,right}/` | KiCad projects for ordering the switch plate in FR4 |
| `firmware/qmk/cornison/` | QMK keyboard definition — see [Firmware](#firmware) below |
| `docs/` | [Build guide](docs/buildguide.md) — parts list and step-by-step assembly |

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
./build.sh case
```

That runs the whole pipeline. Each step is also its own command:

## Build commands

| Command | What it does |
|---|---|
| `./build.sh extract` | Reads the PCB and writes `case/board.json` |
| `./build.sh generate` | Reads `case/board.json` and writes the case, plates, MCU cover, spacers and tents (STEP/STL/DXF) to `case/out/` |
| `./build.sh fr4` | Turns the plate DXF into the KiCad projects in `case/plate-fr4-{left,right}/`. **Overwrites those tracked files**, which are what gets sent to JLCPCB |
| `./build.sh drc` | Runs KiCad's design rule check on both FR4 plate projects |
| `./build.sh case` | All four above, in that order |
| `./build.sh layout` | Regenerates the QMK `LAYOUT` from the PCB into `firmware/qmk/layout.generated.json` |
| `./build.sh help` | Lists the commands |

Requirements: KiCad (for `extract`, `layout` and `drc`) and
[uv](https://docs.astral.sh/uv/) (for `generate` and `fr4`).
`extract` and `layout` need the python3 bundled with KiCad; if it isn't at
the default macOS path, set `KICAD_PYTHON` to it.

See [case/README.md](case/README.md) for the full write-up: stack-up
heights, mounting hardware, assembly order, and how to order each part.

## Firmware

`firmware/qmk/cornison/` is a standalone QMK keyboard definition (not a
QMK fork) - symlink or copy it into a QMK checkout as `keyboards/cornison`
to build it:

```sh
ln -s "$(pwd)/firmware/qmk/cornison" /path/to/qmk_firmware/keyboards/cornison
cd /path/to/qmk_firmware
qmk compile -kb cornison -km default
```

Its `matrix_pins` and matrix topology are copied from upstream QMK's
`crkbd/rev1` (same Pro Micro pinout, same split/OLED setup) - cornison's
own difference is a full 6-column bottom row per half (dedicated
Ctrl/Alt/Cmd + 3 thumb keys on the left, 4 arrow keys + 2 thumb keys on
the right) instead of crkbd's 3-key thumb cluster, so it needs its own
`LAYOUT` rather than reusing crkbd's.

`firmware/qmk/gen_layout.py` (run with `./build.sh layout`) derives that `LAYOUT` array - matrix row/col and
key positions - straight from `pcb/cornison.kicad_pcb`, so it can be
regenerated after any PCB change instead of hand-edited. See
[firmware/qmk/cornison/readme.md](firmware/qmk/cornison/readme.md) for
flashing, bootloader, and handedness setup.

## 3D printing the case

![Assembled case](docs/images/case/cornison-v1.1%20case%20assembled.jpg)

The printable files aren't checked in. Generate them into `case/out/`
first; `case/board.json` is in the repo, so this step needs only
[uv](https://docs.astral.sh/uv/), not KiCad:

```sh
./build.sh generate
```

Print one of each part per half, unless the table says otherwise:

| Part | Files | Needed? | Orientation |
|---|---|---|---|
| Case | `case-{left,right}.stl` | Yes | Floor down |
| Plate-mount spacers | `spacer-{pom,fr4,mjf}.stl` (4 per half) and `spacer-narrow-{pom,fr4,mjf}.stl` (1 per half) | Yes, unless you skip the plate mount. Pick the set that matches your plate material: the spacer height depends on the plate's thickness | — |
| …or a spacer frame | `spacer-frame-{pom,fr4,mjf}-{left,right}.stl` | Replaces the 10 loose spacers | Top face down, pilots up |
| MCU cover | `cover-inset-{left,right}.stl` | Yes (covers the Pro Micro, TRRS jack and reset switch, with a window for the OLED) | Top face down, posts up |
| Tenting legs | `tent-{left,right}.stl` | Optional, 18° | Flat mounting face down, legs up |
| Switch plate | `plate-pom-{left,right}.stl` (1.5mm) or `plate-mjf-{left,right}.stl` (2.0mm) | Only if you aren't ordering the FR4 plate | Flat |
| Cutting templates | `mat-template-{left,right}.stl`, `foam-plate-template-{left,right}.stl` | Only for the optional floor mat or foam | Flat (0.6mm) |

None of these need supports. Each run of `./build.sh generate` also
writes STEP files for every part (for a service that prefers them) and
deletes the old files in `case/out/` first.

**Home printer (FDM):** PETG works well; PLA is fine for a fit check but
more brittle. Dry PETG before printing: an undried spool leaves
rough, separated top surfaces. The walls are thin, so 4 perimeters
helps. Heat-set inserts go into a PETG case the same way as MJF.

The parts in the photos were printed on a Bambu Lab P1S in Prusament
PETG: Galaxy Black for the cases, Chalky Blue for the tents and covers.
The switch plate is FR4, ordered from JLCPCB. Bambu Lab's own PETG
Matte (black and white) also works and may print a little cleaner on a
Bambu printer, since its profiles are tuned for it. The Prusament colours
just look better.

**Print service:** MJF PA12 nylon (JLC3DP or similar) is the recommended
material, and takes heat-set inserts well. SLA resin works too, but glue
the inserts in instead of heat-setting them. Home and service prints use
the same files.

See [case/README.md](case/README.md) for each part in detail: the
stack-up, mounting hardware, the hardware BOM, and the assembly order.

## Ordering

- **PCB:** upload the Gerbers in `pcb/production/` to a fab (JLCPCB).
- **Switch plate (FR4):** upload `case/plate-fr4-{left,right}/production/`
  to a fab as two separate PCB orders — see
  [case/README.md](case/README.md#ordering-the-plate) for settings.
- **Case and other printed parts:** print them at home or send them to a
  3D-print service, see [3D printing the case](#3d-printing-the-case).

## Credits

Based on [foostan/crkbd](https://github.com/foostan/crkbd) (MIT licensed).
Uses the [foostan/kbd](https://github.com/foostan/kbd) footprint/symbol
library. See [LICENSE](LICENSE).
