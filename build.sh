#!/usr/bin/env bash
# Entry point for every generator in this repo. Run `./build.sh help`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$ROOT/case/scripts"

# KiCad's bundled python3 is the only one that has pcbnew. Override
# KICAD_PYTHON if KiCad lives somewhere else.
KICAD_PYTHON="${KICAD_PYTHON:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3}"

usage() {
    cat <<'EOF'
Usage: ./build.sh <command>

Case, plates and MCU cover (in pipeline order):
  extract     Read pcb/cornison.kicad_pcb and write case/board.json
  generate    Read case/board.json and write the case, switch plates,
              MCU cover, spacers and tents (STEP/STL/DXF) to case/out/
  fr4         Turn the plate DXF into the KiCad projects in
              case/plate-fr4-{left,right}/. OVERWRITES those tracked
              files, which are what gets sent to JLCPCB
  drc         Run KiCad's design rule check on both FR4 plate projects

  case        All of the above in order: extract, generate, fr4, drc

Other:
  layout      Regenerate the QMK LAYOUT and RGB matrix from the PCB into
              firmware/qmk/cornison/keyboard.json (and
              firmware/qmk/layout.generated.json)
  version     Copy the board version from VERSION into the PCB and
              schematic title blocks, the FR4 plates and the
              fabrication-toolkit export names. Bump VERSION, then run this
  version --check
              Exit 1 if any of those files disagrees with VERSION
  help        Show this message

Needs: KiCad (for extract, layout, drc) and uv (for generate and
fr4). Set KICAD_PYTHON if KiCad's bundled python3 is not at the default
macOS path.
EOF
}

need_kicad_python() {
    if [[ ! -x "$KICAD_PYTHON" ]]; then
        echo "build.sh: KiCad's python3 not found at $KICAD_PYTHON" >&2
        echo "          set KICAD_PYTHON to the python3 bundled with KiCad" >&2
        exit 1
    fi
}

need() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "build.sh: '$1' not found on PATH" >&2
        exit 1
    fi
}

step() { printf '\n==> %s\n' "$1"; }

do_extract() {
    need_kicad_python
    step "extract: PCB -> case/board.json"
    "$KICAD_PYTHON" "$SCRIPTS/extract_board.py"
}

do_generate() {
    need uv
    step "generate: case, plates, cover, spacers, tents -> case/out/"
    uv run --with build123d python3 "$SCRIPTS/case.py"
}

do_fr4() {
    need uv
    step "fr4: plate DXF -> case/plate-fr4-{left,right}/"
    uv run --with build123d python3 "$SCRIPTS/make_fr4_plate.py"
}

do_drc() {
    need kicad-cli
    step "drc: FR4 plate projects"
    local side report tmp
    for side in left right; do
        report="$(mktemp -t "plate-fr4-$side-drc")"
        # kicad-cli rewrites the .kicad_pro next to the board it checks (it
        # fills in every default setting), so check a copy: the tracked
        # project stays exactly as make_fr4_plate.py wrote it.
        tmp="$(mktemp -d -t "plate-fr4-$side")"
        cp "$ROOT/case/plate-fr4-$side/plate-fr4-$side.kicad_pcb" \
           "$ROOT/case/plate-fr4-$side/plate-fr4-$side.kicad_pro" "$tmp/"
        kicad-cli pcb drc --exit-code-violations -o "$report" \
            "$tmp/plate-fr4-$side.kicad_pcb" || {
            cat "$report" >&2
            echo "build.sh: DRC failed for the $side plate" >&2
            exit 1
        }
    done
}

do_version() {
    step "version: VERSION -> title blocks, plates, export names"
    python3 "$ROOT/pcb/sync_version.py" "$@"
}

do_layout() {
    need_kicad_python
    step "layout: PCB -> firmware/qmk/layout.generated.json"
    "$KICAD_PYTHON" "$ROOT/firmware/qmk/gen_layout.py"
}

case "${1:-help}" in
    extract)   do_extract ;;
    generate)  do_generate ;;
    fr4)       do_fr4 ;;
    drc)       do_drc ;;
    case)      do_extract; do_generate; do_fr4; do_drc ;;
    layout)    do_layout ;;
    version)   shift; do_version "$@" ;;
    help|-h|--help) usage ;;
    *)
        echo "build.sh: unknown command '$1'" >&2
        usage >&2
        exit 2
        ;;
esac
