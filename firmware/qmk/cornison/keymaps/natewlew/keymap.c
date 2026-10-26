// Copyright 2026 natewlew
// SPDX-License-Identifier: GPL-2.0-or-later
#include QMK_KEYBOARD_H
#include "natewlew.h"

// Ported from keyboards/keebio/nyquist/keymaps/natewlew/keymap.c. Cornison's
// LAYOUT lists keys in the same left-to-right reading order per row as
// nyquist's LAYOUT_ortho_4x12 (6 left + 6 right per physical row, vs.
// nyquist's flat 12), so each row below is nyquist's row verbatim, just
// split visually at the half boundary - no token reordering needed.

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {

[_QWERTY] = LAYOUT(
    KC_TAB,  KC_Q,    KC_W,    KC_E,    KC_R,    KC_T,       KC_Y,    KC_U,    KC_I,    KC_O,    KC_P,    KC_BSPC,
    CTR_GUI_COMBO, KC_A, KC_S, KC_D,    KC_F,    KC_G,       KC_H,    KC_J,    KC_K,    KC_L,    KC_SCLN, KC_ENT,
    KC_LSFT, KC_Z,    KC_X,    KC_C,    KC_V,    KC_B,       KC_N,    KC_M,    KC_COMM, KC_DOT,  KC_SLSH, KC_RSFT,
    KC_LCTL, KC_LALT, KC_LGUI, ADJUST,  LOWER,   L_SP,       KC_SPC,  RAISE,   KC_LEFT, KC_DOWN, KC_UP,   KC_RGHT
),

[_LOWER] = LAYOUT(
    KC_TILD, KC_EXLM, KC_AT,   KC_HASH, KC_DLR,  KC_PERC,    KC_CIRC, KC_AMPR, KC_ASTR, KC_LPRN, KC_RPRN, KC_DEL,
    KC_ESC,  KC_HOME, KC_PGDN, KC_PGUP, KC_END,  _______,    _______, KC_UNDS, KC_PLUS, KC_LCBR, KC_RCBR, KC_PIPE,
    _______, _______, _______, _______, _______, _______, _______, KC_QUOT, KC_DQUO, KC_DOT, _______, _______,
    _______, _______, _______, _______, _______, _______,    _______, _______, _______, _______, _______, _______
),

[_LOWER_SPACE] = LAYOUT(
    _______, _______, ALT_SHIFT_TAB, ALT_TAB, ALT_SHIFT_GRV, ALT_GRV, PREV_TAB, NEXT_TAB, _______, _______, _______, _______,
    _______, C_SELECT_ALL, C_SAVE, C_CTR_D, C_CTR_FIND, SCREENSHOT_SELECTION, _______, C_NEW_TAB, C_CLOSE_TAB, C_REOPEN_TAB, _______, _______,
    C_CTR_REDO, C_CTR_UNDO, C_CTR_CUT, C_CTR_COPY, C_CTR_PASTE, C_CTR_P_TEXT, _______, _______, _______, _______, _______, _______,
    _______, _______, _______, _______, _______, _______,    _______, _______, _______, _______, _______, _______
),

[_RAISE] = LAYOUT(
    KC_GRV,  KC_1,    KC_2,    KC_3,    KC_4,    KC_5,       KC_6,    KC_7,    KC_8,    KC_9,    KC_0,    KC_DEL,
    CW_TOGG, KC_LEFT, KC_DOWN, KC_UP,   KC_RGHT, _______,    _______, KC_MINS, KC_EQL,  KC_LBRC, KC_RBRC, KC_BSLS,
    _______, _______, _______, C(KC_C), _______, _______,   _______, _______, _______, _______,  _______, _______,
    _______, _______, _______, _______, _______, _______,   _______, _______, KC_MNXT, KC_VOLD, KC_VOLU, KC_MPLY
),

// AG_NORM / AG_SWAP: Mac / PC mode by hand. OS detection normally sets it
// (see natewlew.c); these override it until the next plug-in or KVM switch.
// Audio (AU_*/MU_*/MI_*) and RGB keycodes from the Nyquist Adjust layer are
// dropped here - this board has no speaker. RM_* (LEDs on/off, next
// animation, dimmer, brighter) do nothing until RGB_MATRIX_ENABLE = yes is
// added to rules.mk; the LEDs are described in keyboard.json's rgb_matrix.
// RESET -> QK_BOOT (RESET was removed from QMK).
[_ADJUST] = LAYOUT(
    KC_F1,   KC_F2,   KC_F3,   KC_F4,   KC_F5,   KC_F6,      KC_F7,   KC_F8,   KC_F9,   KC_F10,  KC_F11,  KC_F12,
    _______, _______, _______, _______, _______, AG_NORM,    AG_SWAP, RM_TOGG, RM_NEXT, RM_VALD, RM_VALU, _______,
    QK_BOOT,  QK_RBT, _______, _______, _______, _______,   _______, _______, _______, _______, _______, _______,
    _______, _______, _______, _______, _______, _______,   _______, _______, _______, _______, _______, _______
)

};

#ifdef OLED_ENABLE
// Master half (the one with the USB cable): layer, Mac or PC mode (and the
// OS that was detected), and Caps Word / Caps Lock. 128x32: four lines.
bool oled_task_user(void) {
    if (!is_keyboard_master()) {
        return true;
    }
    oled_write_P(PSTR("Layer: "), false);
    switch (get_highest_layer(layer_state)) {
        case _QWERTY:      oled_write_ln_P(PSTR("Qwerty"), false); break;
        case _LOWER:       oled_write_ln_P(PSTR("Lower"), false); break;
        case _LOWER_SPACE: oled_write_ln_P(PSTR("Lower+Space"), false); break;
        case _RAISE:       oled_write_ln_P(PSTR("Raise"), false); break;
        case _ADJUST:      oled_write_ln_P(PSTR("Adjust"), false); break;
        default:           oled_write_ln_P(PSTR("?"), false); break;
    }

    oled_write_P(is_pc_mode() ? PSTR("Mode:  PC") : PSTR("Mode:  Mac"), false);
#ifdef OS_DETECTION_ENABLE
    switch (detected_host_os()) {
        case OS_MACOS:   oled_write_ln_P(PSTR(" (macOS)"), false); break;
        case OS_IOS:     oled_write_ln_P(PSTR(" (iOS)"), false); break;
        case OS_LINUX:   oled_write_ln_P(PSTR(" (Linux)"), false); break;
        case OS_WINDOWS: oled_write_ln_P(PSTR(" (Windows)"), false); break;
        default:         oled_write_ln_P(PSTR(" (unsure)"), false); break;
    }
#else
    oled_write_ln_P(PSTR(""), false);
#endif

    if (is_caps_word_on()) {
        oled_write_ln_P(PSTR("CAPS WORD"), true);
    } else if (host_keyboard_led_state().caps_lock) {
        oled_write_ln_P(PSTR("CAPS LOCK"), true);
    } else {
        oled_write_ln_P(PSTR(""), false);
    }
    return false;
}
#endif
