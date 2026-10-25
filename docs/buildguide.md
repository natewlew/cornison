# Cornison Build Guide

> **Draft — written before the first board was built.** Everything here
> comes from the PCB file, the case generator and the firmware, not from a
> finished build. Steps marked **⚠ confirm on first build** are the ones
> most likely to need correcting. Photos are still to be added.

The structure follows foostan's
[Corne Cherry v3 build guide](https://github.com/foostan/crkbd/blob/main/docs/corne-cherry/v3/buildguide_en.md),
which is worth having open alongside this one: the soldering steps are the
same, and its photos apply until this guide has its own. The differences
are the six extra keys, the non-reversible PCB, and the 3D-printed tray
case that replaces Corne's sandwich plates.

## Parts

### Required

| Part | Qty | Notes |
|---|---|---|
| PCB | 1 panel | Both halves arrive joined by breakaway tabs. Gerbers in [pcb/production/](../pcb/production/) |
| Case | 2 | 1 per half, 3D printed. See [case/README.md](../case/README.md#ordering-the-case) |
| Switch plate | 2 | 1 per half: FR4, POM or 3D printed. See [case/README.md](../case/README.md#ordering-the-plate) |
| MCU cover | 2 | 1 per half, 3D printed. See [case/README.md](../case/README.md#mcu-cover) |
| Pro Micro | 2 | Or a pin-compatible board (Elite-C, Sea-Picro EXT) |
| TRRS jack (MJ-4PP-9) | 2 | |
| Reset switch | 2 | 2-pin through-hole tactile switch |
| Diode | 48 | SMD, **SOD-123 package**. A similar-looking "0805" diode does not fit |
| Hotswap socket | 48 | Kailh or Gateron, MX |
| Key switch | 48 | MX-compatible only |
| Keycap | 48 | 46 × 1u, 2 × 1.5u (the innermost thumb key on each half) |
| M2 heat-set insert, 3.2mm long | 14 | 7 per half, in the case bosses. [McMaster 94459A767](https://www.mcmaster.com/94459A767/) is a confirmed fit |
| Plate-mount spacers | 8 standard + 2 narrow | 3D printed, 4 + 1 per half, matching your plate material (`spacer-pom`, `spacer-narrow-pom`, …). Or 2 spacer frames (`spacer-frame-*-{left,right}`) instead. See [case/README.md](../case/README.md#mounting) |
| M2 × 10mm screw | 10 | Low-head, 5 per half: plate → spacer → PCB → case |
| M2 × 12mm screw | 4 | Pan-head, for the MCU covers |
| Rubber feet, 10 × 2mm round | 8 | 4 per half |
| TRRS cable | 1 | A TRS (3-pole) cable also works |
| USB cable | 1 | To match your controller. Must carry data, not charge-only |

### Optional

| Part | Qty | Notes |
|---|---|---|
| OLED module (0.91", 128×32, SSD1306) | 2 | |
| Low-profile 4-pin socket for OLED | 2 | About 3.5mm tall, so the OLED plugs in through the cover |
| Low-profile sockets and pins for the Pro Micro | 4 × 12-pin | Mill-Max style. Only if you want the controller removable |
| SK6812MINI-E LED | 48 | Per-key backlight, 24 per half (one under every key) |
| WS2812B LED | 12 | Underglow, 6 per half |
| MagSafe ring | 2 | Keebio Magnetic MagSafe Tenting Stand Kit R2, 1 ring per half |
| Tenting legs | 2 | 3D printed (`tent-{left,right}`), 18° by default. Each needs 4 more M2 heat-set inserts and 4 M2 × 6mm low-head screws |
| M2 × 4mm screw + M2.5 washer (2.7mm ID / 6.0mm OD) | 10 + 10 | Only when building without the plate mount, to screw the PCB down. Low-head or pan-head, **not** flat-head |
| M2 × 4mm screw | 4 | Only when building without the MCU covers, for the two holes beside each TRRS jack |

Notes on the LEDs:

- Every key has a per-key LED footprint. The PCB's first revision left the
  six keys added over a standard Corne (the three outer bottom-row keys on
  each half) without one; v1.1 adds them, as LED55-57 (left) and LED58-60
  (right), at the end of each half's chain.
- The LEDs are wired in one chain per half, starting with the six
  underglow LEDs. The per-key LEDs come after them, so **per-key lighting
  needs all six underglow LEDs fitted** on that half.
- The underglow LEDs face down into the case floor. They will only be
  visible through a translucent case.
- The firmware describes the LED chain (30 LEDs per half) but leaves RGB
  off. LEDs stay dark until a keymap sets `RGB_MATRIX_ENABLE = yes`. With it
  on, the firmware takes about 2.4KB more of the Pro Micro's flash.

## Firmware preparation

Flash both controllers **before** soldering them to the PCB. A controller
that turns out to be dead is easy to replace at this point and very hard
to replace later.

Follow [firmware/qmk/cornison/readme.md](../firmware/qmk/cornison/readme.md)
to build and flash the `default` keymap. While each bare controller is
plugged in, short its `RST` and `GND` pins and note what appears:

- a new serial port: Caterina bootloader, flash as-is
- `ATm32U4DFU`: add `"bootloader": "atmel-dfu"` to `keyboard.json` first

## Verification

<!-- TODO photo: assets/confirm_front.jpg — panel, top side -->
<!-- TODO photo: assets/confirm_back.jpg — panel, bottom side -->

Check the PCB for visible damage before you start.

Unlike the Corne, **this PCB is not reversible**. Each half has one top
side and one bottom side:

| Side | What gets soldered there |
|---|---|
| Top (the side with the "Corne Cherry" silkscreen text) | Pro Micro, TRRS jack, reset switch, OLED socket. Switches plug in from this side |
| Bottom | Diodes, LEDs, hotswap sockets |

Snap the two halves apart at the breakaway tabs and file the tab stubs
flush. The case has only 0.5mm of clearance around the board, so a stub
left on the edge will stop the PCB dropping in.

<!-- TODO photo: assets/confirm_remove_tabs.jpg — halves separated, edges filed -->

## Assembly

Do every step on both halves.

### Diodes

<!-- TODO photo: assets/build_diode.jpg — one diode, showing orientation -->
<!-- TODO photo: assets/build_diode_overview.jpg — bottom side, all diodes -->

Solder the 24 diodes per half to the **bottom** side. Diodes are
directional: match the bar on the diode to the bar on the PCB marking.

The easy way is to put a small blob of solder on one pad of every
footprint first, then slide each diode into the melted blob with
tweezers, then solder the other leg.

### LEDs (optional)

<!-- TODO photo: assets/build_led_underglow.jpg -->
<!-- TODO photo: assets/build_led_backlight.jpg -->

Both LED types solder to the **bottom** side. They are heat-sensitive,
the SK6812MINI-E especially: keep the iron no hotter than about 320°C
(the Corne guide's figure) and on each pad as briefly as you can.

- **WS2812B (underglow), LED1–6 on the left and LED28–33 on the right:**
  sit on the surface of the bottom side, lens facing away from the board.
  Match the marked corner on the LED to the mark on the footprint.
- **SK6812MINI-E (per-key):** sit in the cutout with the lens facing
  through the board towards the top side, so the light comes up under the
  switch. Match the notched leg to the mark on the footprint.

Because the LEDs are chained, one bad joint turns off every LED after it.
If the chain stops part-way, check the last lit LED and the first dark
one.

### TRRS jack, reset switch, OLED socket

<!-- TODO photo: assets/build_trrs_reset_oled.jpg -->

Insert all three from the **top** side and solder them on the bottom.
Tape them down while you flip the board so they stay seated flat.

### Pro Micro

<!-- TODO photo: assets/build_promicro.jpg -->

The Pro Micro goes on the **top** side, in the footprint outline, with
the USB connector pointing at the top edge of the board.

The MCU cover sits **6.0mm above the PCB**, which leaves room for either
of these:

- **Soldered directly** on ordinary pin headers, components facing the
  PCB. Trim the pin stubs on top down to the solder, so the Pro Micro
  tops out at 5.5mm or less above the PCB. Left long they stood about 7mm
  on the first build, which tipped the cover up and kept the OLED from
  seating.
- **Low-profile sockets** (Mill-Max style) with their matching pins
  soldered to the Pro Micro. Optional: they only make the controller
  removable.

Ordinary 8.5mm sockets and machined DIP sockets do **not** fit: they lift
the Pro Micro to about 11mm and 7–8mm, and the OLED sits right over it.
A board built that way works, but has to go without the cover and the
OLED.

**⚠ confirm on first build.** The 6.0mm figure comes from 3D models of
the parts, not from real ones. Before printing covers, measure from the
top surface of the PCB to the highest point of the mounted Pro Micro, the
TRRS jack and the reset switch. All three need to come in under 6.0mm.

### OLED module (optional)

<!-- TODO photo: assets/build_oled.jpg -->

Solder the 4-pin header to the OLED module. Solder one pin first, reheat
it while you level the module, then solder the rest.

Do not plug the OLED in yet. It goes in through the cover later.

The OLED doesn't rest on the cover. It sits in a window cut through the
cover, held by its pins alone. If it won't push all the way in with the
cover on, check that the cover sits flat: something under it, usually
long Pro Micro pin stubs, is lifting it.

### Operation check

Check each half now, while everything is still easy to reach.

1. Plug USB into one half, TRRS disconnected.
2. Short the two pads of every hotswap footprint with tweezers and
   confirm each of the 24 positions sends a key.
3. Set handedness on that half (see the
   [firmware readme](../firmware/qmk/cornison/readme.md#handedness)).
4. Repeat for the other half.
5. Connect the TRRS cable with USB in one half only and test both halves
   together.

**⚠ confirm on first build:** if nothing at all registers on a half, the
likely cause is `diode_direction` in `keyboard.json`, which has not yet
been checked against a real board. It is a one-line firmware change.

Never plug or unplug the TRRS cable while USB is connected. It can short
power to ground and damage the controllers.

### Hotswap sockets

<!-- TODO photo: assets/build_socket.jpg -->
<!-- TODO photo: assets/build_socket_overview.jpg -->

Solder the 24 sockets per half to the **bottom** side, each seated flat
in its footprint outline. Use plenty of solder; these joints take the
force of every switch insertion.

### Heat-set inserts

<!-- TODO photo: assets/build_inserts.jpg -->

Each case half has 7 bosses, one under each hole in the PCB. Press an M2
heat-set insert into each of them with a soldering iron or heat-set tip,
until it is flush with the top of the boss. Keep it vertical. Let the
inserts cool before the next step.

In a resin (SLA) case, glue the inserts in instead of heating them.

### Tenting legs (optional)

The tent screws into inserts in the bottom of the case, from below, so
it can go on or come off at any time. Fit the inserts now, with the
other inserts:

1. Press an M2 heat-set insert into each of the 4 small holes in the
   bottom of the case, beside the round corner recesses, until it's
   flush with the bottom.

The tent itself goes on at the end (see Finishing).

### Mount the PCB and plate

<!-- TODO photo: assets/build_pcb_in_case.jpg -->
<!-- TODO photo: assets/build_plate_switches.jpg -->

1. Lower the PCB onto the bosses, top side up, with the USB connector and
   TRRS jack lined up with their wall notches. Nothing screws it down
   yet.
2. Set a spacer on each of the 5 plate-mount holes, its pilot dropped
   into the PCB hole: the standard spacer on four, the narrow one on the
   top hole nearest the Pro Micro. Or lay the spacer frame on instead,
   pilots down.
3. Lay the plate on top and screw it down with 5 M2 × 10mm low-head
   screws, through plate, spacer and PCB into the inserts. The plate has
   two holes near the outer bottom corner; only the one over your PCB's
   hole gets a screw. The two PCB holes beside the TRRS jack stay empty
   for now; the cover's screws go there.

Screw the plate down before fitting any switches. The screw head at the
narrow-spacer hole slightly overlaps the two neighbouring switches' top
housings, so it can't go in once they're fitted.

**⚠ confirm on first build:** the narrow spacer clears its neighbouring
switch bodies by only 0.27mm, and that screw head's overlap with the
switch housings is on paper only. Use the smallest-headed screw you have
there.

**Building without the plate mount?** Screw the PCB down at step 1
instead, with 5 M2 × 4mm screws, **each with an M2.5 washer under the
head**. Those five holes are 4.3mm across, larger than any M2 screw head,
so a bare screw drops straight through and holds nothing. Then skip steps
2 and 3: drop the plate in and let the switches hold it.

### Switches

1. Clip a switch into each corner of the plate and press it into its
   socket.
2. Add the remaining switches one at a time. Check that both pins are
   straight before each one, and support the PCB from below if a socket
   feels like it is being pushed off its pads.

Don't fill the plate with switches first and then try to seat them all at
once. Two of the thumb keys on each half are rotated (15° and 60°);
follow the plate cutouts.

### Cover, OLED, keycaps, feet

<!-- TODO photo: assets/build_cover.jpg -->
<!-- TODO photo: assets/build_oled_cover.jpg -->
<!-- TODO photo: assets/build_finish.jpg -->

1. Set the MCU cover over the Pro Micro, posts down onto the two empty
   mounting holes, rim on the case wall. Fasten it with two M2 × 12mm
   screws. No washers: the posts clamp the PCB. (Building without a
   cover? Put an M2 × 4mm screw in those two holes instead. They are
   2.2mm holes, so they don't need a washer.)
2. Plug the OLED module into its socket through the slot in the cover. It
   lies on top of the cover. The small round hole beside it is for
   reaching the reset switch with a paperclip.
3. Fit the keycaps. The 1.5u caps go on the innermost thumb key of each
   half.
4. Tenting legs: hold the tent's flat face against the bottom of the
   case, legs pointing down, and drive an M2 × 6mm low-head screw up
   through each leg's platform into the insert. For extra weight, first
   put stick-on tire weight segments (19 × 16 × 4mm) into the cells in
   the middle of the tent, up to 9; the case holds them in. Rubber feet go in the
   recesses on the leg ends. Without tents, the rubber feet go in the 4
   round recesses at the corners of the case bottom.
5. If you are using the MagSafe tenting kit, stick a ring onto the flat
   bottom of each half.

## Troubleshooting

| Symptom | Check |
|---|---|
| Nothing registers on one half | `diode_direction` in `keyboard.json`; Pro Micro solder joints |
| One key dead | That key's diode orientation and joints; bent switch pin; socket joints |
| A whole row or column dead | The Pro Micro pin for that row or column |
| Halves work alone but not together | Handedness not set; TRRS jack joints; cable |
| LEDs stop part-way along | Joints on the last lit LED and the first dark one |
| PCB won't drop into the case | Breakaway tab stubs not filed flush |
