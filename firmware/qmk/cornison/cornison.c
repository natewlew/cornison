// Copyright 2026 natewlew
// SPDX-License-Identifier: GPL-2.0-or-later
#include QMK_KEYBOARD_H

#ifdef OLED_ENABLE

oled_rotation_t oled_init_kb(oled_rotation_t rotation) {
    if (!is_keyboard_master()) {
        return OLED_ROTATION_180; // flip the offhand's display right-side up
    }
    return rotation;
}

bool oled_task_kb(void) {
    if (!oled_task_user()) {
        return false;
    }

    if (is_keyboard_master()) {
        oled_write_P(PSTR("Layer: "), false);
        switch (get_highest_layer(layer_state)) {
            case 0:
                oled_write_ln_P(PSTR("Default"), false);
                break;
            case 1:
                oled_write_ln_P(PSTR("Lower"), false);
                break;
            case 2:
                oled_write_ln_P(PSTR("Raise"), false);
                break;
            case 3:
                oled_write_ln_P(PSTR("Adjust"), false);
                break;
            default:
                oled_write_ln_P(PSTR("Undefined"), false);
        }
    }

    return false;
}

#endif
