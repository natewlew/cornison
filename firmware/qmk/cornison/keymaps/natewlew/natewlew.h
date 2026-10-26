// Copyright 2026 natewlew
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Started as a copy of users/natewlew in my qmk_userspace (shared with my
// other boards); this one has since moved on (OS detection, shortcut table,
// layer-based alt-tab). Port it back to the other boards when they need it.

#pragma once

#include "quantum.h"

enum layer_names {
    _QWERTY,
    _LOWER,
    _LOWER_SPACE,
    _RAISE,
    _ADJUST
};

enum my_custom_keycodes {
    // Primary modifier + a key: Cmd on a Mac, Ctrl on Linux/Windows. These
    // stay together, in the same order as primary_shortcuts[] in natewlew.c.
    C_CTR_UNDO = SAFE_RANGE,
    C_CTR_REDO,
    C_CTR_CUT,
    C_CTR_COPY,
    C_CTR_PASTE,
    C_SELECT_ALL,
    C_SAVE,
    C_CTR_D,
    C_CTR_FIND,
    C_NEW_TAB,
    C_CLOSE_TAB,
    C_REOPEN_TAB,          // reopen the last closed tab
    C_PRIMARY_END,         // not a key: marks the end of the group above

    C_CTR_P_TEXT,          // paste as plain text
    SCREENSHOT_SELECTION,
    ALT_TAB,               // app switcher while Lower+Space is held
    ALT_SHIFT_TAB,
    ALT_GRV,               // same-app window switcher
    ALT_SHIFT_GRV,
    CTR_GUI_COMBO,         // hold: the primary modifier (Cmd / Ctrl)
    NEW_SAFE_RANGE
};

bool is_pc_mode(void);

bool process_record_keymap(uint16_t keycode, keyrecord_t *record);

#define LOWER     MO(_LOWER)
#define L_SP      LT(_LOWER_SPACE, KC_SPC)
#define RAISE     MO(_RAISE)
#define ADJUST    MO(_ADJUST)

// Browser tab switching is Ctrl+Tab on a Mac too, so plain keycodes do.
#define NEXT_TAB  C(KC_TAB)
#define PREV_TAB  C(S(KC_TAB))
