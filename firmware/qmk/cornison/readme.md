# Cornison

A split keyboard derived from [foostan's Corne Cherry
v3](https://github.com/foostan/crkbd), with extra keys added in a
Levinson-style arrangement: 3 thumb keys plus dedicated Ctrl/Alt/Cmd on
the left, 2 thumb keys plus 4 arrow keys on the right. 24 keys per half,
48 total. See the [hardware repo](https://github.com/natewlew/cornison)
for the PCB, case, and how this `keyboard.json` was derived from it
(`../gen_layout.py`).

* Keyboard Maintainer: [natewlew](https://github.com/natewlew)
* Hardware Supported: Cornison PCB, Pro Micro (or pin-compatible
  ATmega32U4 board, e.g. Elite-C) per half
* Hardware Availability: https://github.com/natewlew/cornison

Make example for this keyboard (after setting up your build environment):

    make cornison:default

Flash example for this keyboard:

    qmk flash -kb cornison -km default

See the [build environment setup](https://docs.qmk.fm/#/getting_started_build_tools)
and the [make instructions](https://docs.qmk.fm/#/getting_started_make_guide)
for more information. Brand new to QMK? Start with our [Complete Newbs
Guide](https://docs.qmk.fm/#/newbs).

Two keymaps:

* `keymaps/default/` - a plain starting point.
* `keymaps/natewlew/` - my daily driver (5 layers, Mac/Linux-aware
  shortcuts), ported from my Nyquist keymap. Self-contained: it carries
  its own copy of my shared userspace code. See its
  [readme](keymaps/natewlew/readme.md).

## Bootloader

The Cornison PCB has a reset switch next to the TRRS jack to enter the
bootloader. **Confirmed on real hardware:** the Keebio Pro Micro USB-C
used here ships with a **Caterina** bootloader (a new serial port
appears on reset), matching `development_board: promicro` in
`keyboard.json` - no change needed.

First flash attempt right after a reset sometimes fails with
`butterfly_recv(pgm, &c, 1) failed` / "Device not configured" from
avrdude - a timing race with the Caterina handshake, not a hardware
problem. Nothing is written yet at that point; just retry.

## Handedness

The two halves are not interchangeable (different key counts), so there's
no hardware pin to auto-detect which side is which - `config.h` sets
`EE_HANDS`. The simplest way to set it is at flash time, via QMK's
split-specific avrdude targets, which write the firmware *and* the
correct `eeprom-{lefthand,righthand}.eep` in the same step:

```sh
qmk flash -kb cornison -km default -bl avrdude-split-left   # left half
qmk flash -kb cornison -km default -bl avrdude-split-right  # right half
```

This only needs to be done once per half; it survives a reflash as long
as the firmware keeps using plain `avrdude`/`-bl avrdude-split-{left,right}`
and the EEPROM isn't separately cleared (`EE_CLR` on the Adjust layer
does clear it). The Adjust layer also has `EH_LEFT`/`EH_RGHT` (hold the
left thumb cluster's innermost key, then also press its neighbor, to
reach Adjust - see `keymaps/default/keymap.c`) as a fallback if you ever
need to re-set handedness without reflashing.

## Bring-up checklist

1. `qmk lint -kb cornison` and `qmk compile -kb cornison -km default`
   from a QMK checkout with this directory symlinked/copied in as
   `keyboards/cornison`. Use a plain QMK checkout (your own fork or
   upstream `qmk/qmk_firmware`), not a vendor fork meant for someone
   else's boards.
2. Flash each half with its `-bl avrdude-split-{left,right}` target
   (above) - this also sets handedness, no separate step needed.
3. With USB plugged into **one half at a time** (TRRS disconnected),
   short every hotswap socket's pads with tweezers and confirm each of
   that half's 24 matrix positions registers. **Both halves: done,
   2026-10-12 - all 24 positions correct on each, confirming
   `diode_direction: COL2ROW` is right.**
4. Connect the TRRS cable (USB still in one half only) and re-test both
   halves together. **Done, 2026-10-12** - confirmed working with the
   `natewlew` keymap over TRRS.
