// Copyright 2026 natewlew
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// The two halves are not interchangeable (left has 3 dedicated mod keys,
// right has 4 arrow keys instead), so handedness can't be auto-detected
// from a matrix grid intersection like SPLIT_HAND_MATRIX_GRID, and there's
// no dedicated hardware handedness pin. Store it in each half's EEPROM
// instead - set once per half via the EH_LEFT/EH_RGHT keycodes on the
// adjust layer (see keymaps/default/keymap.c), not by flashing separate
// eeprom-lefthand/righthand.eep files.
#define EE_HANDS
