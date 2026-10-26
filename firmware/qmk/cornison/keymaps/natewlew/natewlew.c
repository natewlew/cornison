// Copyright 2026 natewlew
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Started as a copy of users/natewlew in my qmk_userspace (shared with my
// other boards); this one has since moved on (OS detection, shortcut table,
// layer-based alt-tab). Port it back to the other boards when they need it.

#include "natewlew.h"

// Mac or PC mode. The Alt/GUI swap flag is the one setting for both: it swaps
// the physical Alt and Cmd keys for a PC layout, and it picks which modifier
// the shortcut keys below send. OS detection sets it when the keyboard is
// plugged in (or the monitor's KVM switches over); AG_SWAP / AG_NORM on the
// Adjust layer still override it by hand until the next detection.
bool is_pc_mode(void) {
    return keymap_config.swap_lalt_lgui || keymap_config.swap_ralt_rgui;
}

#ifdef OS_DETECTION_ENABLE
bool process_detected_host_os_user(os_variant_t os) {
    switch (os) {
        case OS_MACOS:
        case OS_IOS:
            keymap_config.swap_lalt_lgui = keymap_config.swap_ralt_rgui = false;
            break;
        case OS_LINUX:
        case OS_WINDOWS:
            keymap_config.swap_lalt_lgui = keymap_config.swap_ralt_rgui = true;
            break;
        default: // OS_UNSURE: keep whatever was set last
            break;
    }
    return true;
}
#endif

// The modifier most shortcuts use: Cmd on a Mac, Ctrl on a PC.
static uint16_t primary_mod(void) {
    return is_pc_mode() ? KC_LCTL : KC_LGUI;
}

// Primary modifier + this key, for C_CTR_UNDO up to C_PRIMARY_END (same
// order as in natewlew.h). Extra modifiers can ride along, e.g. S(KC_Z).
static const uint16_t PROGMEM primary_shortcuts[] = {
    KC_Z,     // C_CTR_UNDO
    S(KC_Z),  // C_CTR_REDO
    KC_X,     // C_CTR_CUT
    KC_C,     // C_CTR_COPY
    KC_V,     // C_CTR_PASTE
    KC_A,     // C_SELECT_ALL
    KC_S,     // C_SAVE
    KC_D,     // C_CTR_D
    KC_F,     // C_CTR_FIND
    KC_T,     // C_NEW_TAB
    KC_W,     // C_CLOSE_TAB
    S(KC_T),  // C_REOPEN_TAB
};
_Static_assert(sizeof(primary_shortcuts) / sizeof(primary_shortcuts[0]) == C_PRIMARY_END - C_CTR_UNDO,
               "primary_shortcuts[] and the C_CTR_UNDO..C_PRIMARY_END keycodes are out of step");

// Alt+Tab (Cmd+Tab on a Mac): the modifier stays down while Lower+Space is
// held, so tapping ALT_TAB again moves along the switcher. Remember which
// modifier went down, so it's the one released even if the mode changed.
static uint16_t tab_mod = KC_NO;

static void start_tabbing(void) {
    if (tab_mod == KC_NO) {
        tab_mod = is_pc_mode() ? KC_LALT : KC_LGUI;
        register_code(tab_mod);
    }
}

static void finish_tabbing(void) {
    if (tab_mod != KC_NO) {
        unregister_code(tab_mod);
        tab_mod = KC_NO;
    }
}

layer_state_t layer_state_set_user(layer_state_t state) {
    if (!layer_state_cmp(state, _LOWER_SPACE)) {
        finish_tabbing();
    }
    return state;
}

__attribute__((weak)) bool process_record_keymap(uint16_t keycode, keyrecord_t *record) {
    return true;
}

bool process_record_user(uint16_t keycode, keyrecord_t *record) {
    static uint16_t held_mod = KC_NO; // what CTR_GUI_COMBO pressed, so it releases that
    bool            pressed  = record->event.pressed;

    if (keycode >= C_CTR_UNDO && keycode < C_PRIMARY_END) {
        if (pressed) {
            uint16_t key = pgm_read_word(&primary_shortcuts[keycode - C_CTR_UNDO]);
            tap_code16((is_pc_mode() ? QK_LCTL : QK_LGUI) | key);
        }
        return false;
    }

    switch (keycode) {
        case CTR_GUI_COMBO:
            if (pressed) {
                held_mod = primary_mod();
                register_code(held_mod);
            } else if (held_mod != KC_NO) {
                unregister_code(held_mod);
                held_mod = KC_NO;
            }
            return false;

        case C_CTR_P_TEXT:
            if (pressed) {
                // Linux: Ctrl+Shift+V. Mac: Shift+Opt+Cmd+V.
                tap_code16(is_pc_mode() ? S(C(KC_V)) : S(A(G(KC_V))));
            }
            return false;

        case SCREENSHOT_SELECTION:
            if (pressed) {
                // Linux: Shift+PrtSc. Mac: Shift+Cmd+4.
                tap_code16(is_pc_mode() ? S(KC_PSCR) : S(G(KC_4)));
            }
            return false;

        case ALT_TAB:
        case ALT_SHIFT_TAB:
        case ALT_GRV:
        case ALT_SHIFT_GRV:
            if (pressed) {
                start_tabbing();
                switch (keycode) {
                    case ALT_TAB:       tap_code(KC_TAB);       break;
                    case ALT_SHIFT_TAB: tap_code16(S(KC_TAB));  break;
                    case ALT_GRV:       tap_code(KC_GRV);       break;
                    case ALT_SHIFT_GRV: tap_code16(S(KC_GRV));  break;
                }
            }
            return false;
    }
    return process_record_keymap(keycode, record);
}
