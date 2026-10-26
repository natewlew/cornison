# Self-contained: natewlew.c/.h here started as a copy of users/natewlew from
# my qmk_userspace. QMK would otherwise also pull in users/<keymap name> when
# that userspace is set up, and the two define the same process_record_user.
# Keymap rules.mk is read before QMK picks the users/ folder, so naming one
# that doesn't exist keeps it out.
USER_NAME := cornison-natewlew-standalone
SRC += natewlew.c

# Mac or PC mode follows the host OS (natewlew.c). About 570 bytes of flash.
OS_DETECTION_ENABLE = yes

# Caps Word (CW_TOGG on Raise): caps for one word, off at the next space.
CAPS_WORD_ENABLE = yes
