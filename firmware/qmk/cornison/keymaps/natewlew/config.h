// Copyright 2026 natewlew
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// The monitor's built-in KVM may keep the keyboard powered while switching
// computers, so it would never see the new host and re-detect its OS.
// Restart the keyboard whenever USB re-initialises instead. If the KVM
// misbehaves with this, remove it (and switch with AG_SWAP / AG_NORM).
#define OS_DETECTION_KEYBOARD_RESET
