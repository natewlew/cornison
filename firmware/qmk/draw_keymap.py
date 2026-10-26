#!/usr/bin/env python3
"""
Draw a keymap as an SVG, one block per layer, keys coloured by what they do.

Reads the keymap's own keymap.c (and the .h files beside it, for layer-key
#defines such as `#define LOWER MO(_LOWER)`) and the real key positions from
cornison/keyboard.json, so the split and the angled thumb keys come out as
they sit on the board. Plain python3, nothing to install:

  python3 firmware/qmk/draw_keymap.py natewlew     (or ./build.sh keymap-svg natewlew)

writes firmware/qmk/cornison/keymaps/<keymap>/keymap.svg. Re-run it after
changing the keymap. A keycode it doesn't know is drawn with its own name and
no colour: add it to LABELS below.
"""
import json
import math
import re
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYBOARD = HERE / "cornison"

U = 58          # px per key unit
KEY = U - 6     # drawn key size (gap between keys)
PAD = 16        # outer margin
TITLE_H = 30    # layer title band

# Colour groups. The emoji are what the readme's legend uses.
GROUPS = {
    "mod":      ("🟪", "Modifiers"),
    "layer":    ("🟧", "Layer keys"),
    "nav":      ("🟦", "Navigation"),
    "shortcut": ("🟩", "Shortcuts (most send Cmd on a Mac, Ctrl on a PC)"),
    "num":      ("🟨", "Numbers"),
    "fn":       ("🟫", "F-keys, media and lighting"),
    "system":   ("🟥", "System"),
}

# keycode -> (label, group). Labels use "\n" for a second line. Group None:
# drawn plain (letters, symbols, editing keys).
LABELS = {
    "KC_TAB": ("Tab", None), "KC_BSPC": ("Bksp", None), "KC_ENT": ("Enter", None),
    "KC_ESC": ("Esc", None), "KC_DEL": ("Del", None), "KC_SPC": ("Space", None),
    "KC_LSFT": ("Shift", "mod"), "KC_RSFT": ("Shift", "mod"), "KC_LCTL": ("Ctrl", "mod"),
    "KC_LALT": ("Alt", "mod"), "KC_LGUI": ("Cmd", "mod"), "KC_CAPS": ("Caps", "mod"),
    "CW_TOGG": ("Caps\nword", "mod"),
    "CTR_GUI_COMBO": ("Cmd /\nCtrl", "mod"),
    "KC_LEFT": ("←", "nav"), "KC_DOWN": ("↓", "nav"), "KC_UP": ("↑", "nav"), "KC_RGHT": ("→", "nav"),
    "KC_HOME": ("Home", "nav"), "KC_END": ("End", "nav"), "KC_PGUP": ("PgUp", "nav"), "KC_PGDN": ("PgDn", "nav"),
    "C_CTR_UNDO": ("Undo", "shortcut"), "C_CTR_REDO": ("Redo", "shortcut"),
    "C_CTR_CUT": ("Cut", "shortcut"), "C_CTR_COPY": ("Copy", "shortcut"),
    "C_CTR_PASTE": ("Paste", "shortcut"), "C_CTR_P_TEXT": ("Paste\nplain", "shortcut"),
    "C_SELECT_ALL": ("Select\nall", "shortcut"), "C_SAVE": ("Save", "shortcut"),
    "C_CTR_D": ("Cmd/\nCtrl D", "shortcut"), "C_CTR_FIND": ("Find", "shortcut"),
    "SCREENSHOT_SELECTION": ("Screen\nshot", "shortcut"),
    "C_NEW_TAB": ("New\ntab", "shortcut"), "C_CLOSE_TAB": ("Close\ntab", "shortcut"),
    "C_REOPEN_TAB": ("Reopen\ntab", "shortcut"),
    "NEXT_TAB": ("Next\ntab", "shortcut"), "PREV_TAB": ("Prev\ntab", "shortcut"),
    "C(KC_C)": ("Ctrl C", "shortcut"),
    "ALT_TAB": ("Next\napp", "shortcut"), "ALT_SHIFT_TAB": ("Prev\napp", "shortcut"),
    "ALT_GRV": ("Next\nwindow", "shortcut"), "ALT_SHIFT_GRV": ("Prev\nwindow", "shortcut"),
    "KC_MNXT": ("Next\ntrack", "fn"), "KC_MPLY": ("Play/\npause", "fn"),
    "KC_VOLD": ("Vol −", "fn"), "KC_VOLU": ("Vol +", "fn"),
    "RM_TOGG": ("LEDs\non/off", "fn"), "RM_NEXT": ("LED\nmode", "fn"),
    "RM_VALD": ("LEDs\ndim", "fn"), "RM_VALU": ("LEDs\nbright", "fn"),
    "QK_BOOT": ("Boot", "system"), "QK_RBT": ("Reboot", "system"), "AG_NORM": ("Mac\nmode", "system"), "AG_SWAP": ("PC\nmode", "system"),
    # symbols
    "KC_TILD": ("~", None), "KC_EXLM": ("!", None), "KC_AT": ("@", None), "KC_HASH": ("#", None),
    "KC_DLR": ("$", None), "KC_PERC": ("%", None), "KC_CIRC": ("^", None), "KC_AMPR": ("&", None),
    "KC_ASTR": ("*", None), "KC_LPRN": ("(", None), "KC_RPRN": (")", None), "KC_UNDS": ("_", None),
    "KC_PLUS": ("+", None), "KC_LCBR": ("{", None), "KC_RCBR": ("}", None), "KC_PIPE": ("|", None),
    "KC_QUOT": ("'", None), "KC_DQUO": ('"', None), "KC_DOT": (".", None), "KC_COMM": (",", None),
    "KC_SLSH": ("/", None), "KC_SCLN": (";", None), "KC_GRV": ("`", None), "KC_MINS": ("-", None),
    "KC_EQL": ("=", None), "KC_LBRC": ("[", None), "KC_RBRC": ("]", None), "KC_BSLS": ("\\", None),
}
for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    LABELS[f"KC_{c}"] = (c, None)
for d in "1234567890":
    LABELS[f"KC_{d}"] = (d, "num")
for n in range(1, 13):
    LABELS[f"KC_F{n}"] = (f"F{n}", "fn")

TRANSPARENT = {"_______", "KC_TRNS", "KC_TRANSPARENT"}

STYLE = """
.bg { fill: #ffffff; }
.title { font: 600 15px -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; fill: #1f2328; }
.legend { font: 13px -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; fill: #1f2328; }
.key rect { fill: #ffffff; stroke: #c9ccd1; stroke-width: 1; }
.key text { font: 12px -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; fill: #1f2328;
            text-anchor: middle; dominant-baseline: central; }
.key text.small { font-size: 9px; fill: #57606a; }
.key.big text { font-size: 15px; }
.key.trans rect { fill: none; stroke: #d0d7de; stroke-dasharray: 3 3; }
.key.mod rect      { fill: #e4d7fb; stroke: #8250df; }
.key.layer rect    { fill: #ffdcb8; stroke: #d1700a; }
.key.nav rect      { fill: #cfe2ff; stroke: #0969da; }
.key.shortcut rect { fill: #cdeccf; stroke: #1a7f37; }
.key.num rect      { fill: #fff0a8; stroke: #bf8700; }
.key.fn rect       { fill: #ead7c3; stroke: #8b5a2b; }
.key.system rect   { fill: #ffd0cc; stroke: #cf222e; }
.key.held rect     { stroke: #1f2328; stroke-width: 3; }
.key.mod text, .key.layer text, .key.nav text, .key.shortcut text,
.key.num text, .key.fn text, .key.system text { fill: #1f2328; }
@media (prefers-color-scheme: dark) {
  .bg { fill: #0d1117; }
  .title, .legend { fill: #e6edf3; }
  .key rect { fill: #2d333b; stroke: #545d68; }
  .key text { fill: #e6edf3; }
  .key text.small { fill: #9da7b3; }
  .key.trans rect { fill: none; stroke: #444c56; }
  .key.held rect { stroke: #ffffff; }
  .key.mod rect      { fill: #e4d7fb; }
  .key.layer rect    { fill: #ffdcb8; }
  .key.nav rect      { fill: #cfe2ff; }
  .key.shortcut rect { fill: #cdeccf; }
  .key.num rect      { fill: #fff0a8; }
  .key.fn rect       { fill: #ead7c3; }
  .key.system rect   { fill: #ffd0cc; }
  .key.mod text, .key.layer text, .key.nav text, .key.shortcut text,
  .key.num text, .key.fn text, .key.system text { fill: #1f2328; }
  .key.mod text.small, .key.layer text.small { fill: #57606a; }
}
"""


def split_args(body):
    """Split a LAYOUT(...) body on top-level commas."""
    out, depth, cur = [], 0, ""
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def read_keymap(keymap_dir):
    src = (keymap_dir / "keymap.c").read_text()
    src = re.sub(r"//[^\n]*", "", src)
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    layers = []
    for m in re.finditer(r"\[\s*(\w+)\s*\]\s*=\s*LAYOUT\s*\((.*?)\)\s*(?=,\s*\[|\s*}\s*;)", src, re.S):
        layers.append((m.group(1), split_args(m.group(2))))
    # layer keys: #define NAME MO(_LAYER) / LT(_LAYER, KC_x) / TG / TT / OSL
    layer_keys = {}
    for f in list(keymap_dir.glob("*.h")) + [keymap_dir / "keymap.c"]:
        for name, kind, layer, tap in re.findall(
            r"#define\s+(\w+)\s+(MO|LT|TG|TT|OSL)\(\s*(\w+)\s*(?:,\s*(\w+))?\s*\)", f.read_text()
        ):
            layer_keys[name] = (layer, tap or None)
    return layers, layer_keys


def layer_title(name):
    return name.strip("_").replace("_", " ").title()


def key_svg(cx, cy, w, rot, kc, layer_keys, held_for, base_kc=None):
    """One key, centred at (cx, cy) px, w units wide, rotated rot degrees (SVG sense)."""
    cls, label, small = [], None, None
    # The key held to reach this layer is usually transparent here; show it.
    if kc in TRANSPARENT and base_kc in layer_keys and layer_keys[base_kc][0] == held_for:
        kc = base_kc
    if kc in TRANSPARENT:
        cls.append("trans")
        label = ""
    elif kc in layer_keys:
        layer, tap = layer_keys[kc]
        cls.append("layer")
        if tap:
            label = LABELS.get(tap, (tap.replace("KC_", ""), None))[0]
            small = "hold"
        else:
            label = layer_title(layer)
        if layer == held_for:
            cls.append("held")
            small = "held"
    else:
        label, group = LABELS.get(kc, (kc.replace("KC_", ""), None))
        if group:
            cls.append(group)
        if len(label) == 1:
            cls.append("big")
    wpx = KEY + (w - 1) * U
    lines = label.split("\n") if label else []
    # only the key outline turns; the label stays level so it reads easily
    turn = f' transform="rotate({rot:.1f})"' if rot else ""
    parts = [f'<g class="key {" ".join(cls)}" transform="translate({cx:.1f} {cy:.1f})">',
             f'<rect x="{-wpx / 2:.1f}" y="{-KEY / 2:.1f}" width="{wpx:.1f}" height="{KEY}" rx="6"{turn}/>']
    shift = -5 if small else 0
    for i, line in enumerate(lines):
        y = shift + (i - (len(lines) - 1) / 2) * 14
        parts.append(f'<text y="{y:.1f}">{escape(line)}</text>')
    if small:
        parts.append(f'<text class="small" y="{KEY / 2 - 9:.1f}">{escape(small)}</text>')
    parts.append("</g>")
    return "".join(parts)


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "natewlew"
    keymap_dir = KEYBOARD / "keymaps" / name
    layers, layer_keys = read_keymap(keymap_dir)
    layout = json.loads((KEYBOARD / "keyboard.json").read_text())["layouts"]["LAYOUT"]["layout"]
    for lname, keys in layers:
        if len(keys) != len(layout):
            raise SystemExit(f"{lname}: {len(keys)} keys, layout has {len(layout)}")

    # keyboard.json x/y are key centres in units; KiCad's rotation is
    # counter-clockwise on its Y-down screen, SVG's is clockwise, hence -r.
    xs = [k["x"] for k in layout]
    ys = [k["y"] for k in layout]
    min_x, min_y = min(xs), min(ys)
    board_w = (max(xs) - min_x + 1.5) * U
    board_h = (max(ys) - min_y + 1.6) * U
    block_h = TITLE_H + board_h + 12
    legend_h = 26 * len(GROUPS) // 2 + 30
    width = board_w + 2 * PAD
    height = PAD + block_h * len(layers) + legend_h

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" '
           f'width="{width:.0f}" height="{height:.0f}">', f"<style>{STYLE}</style>",
           f'<rect class="bg" width="{width:.0f}" height="{height:.0f}" rx="10"/>']
    for i, (lname, keys) in enumerate(layers):
        top = PAD + i * block_h
        how = ""
        if i:
            keys_to_it = [base for base in layers[0][1] if base in layer_keys and layer_keys[base][0] == lname]
            if keys_to_it:
                layer, tap = layer_keys[keys_to_it[0]]
                held = LABELS.get(tap, (tap, None))[0] if tap else layer_title(layer)
                how = f" · hold {held}"
        out.append(f'<text class="title" x="{PAD}" y="{top + 18}">{escape(layer_title(lname))}'
                   f'<tspan class="legend">{escape(how)}</tspan></text>')
        for k, kc, base_kc in zip(layout, keys, layers[0][1]):
            cx = PAD + (k["x"] - min_x + 0.75) * U
            cy = top + TITLE_H + (k["y"] - min_y + 0.55) * U
            out.append(key_svg(cx, cy, k.get("w", 1), -k.get("r", 0), kc, layer_keys,
                               held_for=lname if i else None, base_kc=base_kc))

    # legend, two columns
    top = PAD + block_h * len(layers)
    items = list(GROUPS.items()) + [("held", ("", "Held to reach this layer"))]
    for j, (cls, (_, text)) in enumerate(items):
        col, row = j % 2, j // 2
        x = PAD + col * board_w / 2
        y = top + row * 26
        group = "layer held" if cls == "held" else cls
        out.append(f'<g class="key {group}" transform="translate({x + 11} {y + 11})">'
                   f'<rect x="-10" y="-10" width="20" height="20" rx="4"/></g>')
        out.append(f'<text class="legend" x="{x + 30}" y="{y + 15}">{escape(text)}</text>')
    out.append("</svg>")

    path = keymap_dir / "keymap.svg"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(HERE.parent.parent)} ({len(layers)} layers)")


if __name__ == "__main__":
    main()
