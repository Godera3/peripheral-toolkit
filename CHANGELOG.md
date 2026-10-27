# Changelog

Notable changes to the toolkit. Older history lives in the git log.

## 2026-10-27 - Razer Barracuda X Chroma: full reverse engineering + CLI

### Added
- **Full Linux driver for the Razer Barracuda X Chroma (`1532:0574`).**
  A new `headset/` package provides bidirectional communication over `hidraw`
  without needing to detach the kernel driver. Features:
  - `battery`: Query exact battery percentage.
  - `eq`: Set EQ mode (Game, Music, Movie, Custom) from Linux.
  - `lights-on` / `lights-off`: Toggle Chroma lighting.
  - `listen`: Real-time event listener for physical EQ button presses.
- **Protocol Documentation:** `headset/captures/PLAN.md` updated with the exact
  property map (`0x13` EQ, `0x21` Battery, `0x40` Lighting) and framing rules.

### Changed
- Switched from Windows `USBPcap` to host-side Linux `usbmon` for captures.
  `USBPcap` fails inside QEMU on complex composite devices due to the emulated
  xHCI controller. Host-side `usbmon` captures the raw bytes flawlessly.

### Known Issues
- Changing EQ via USB `SET_REPORT` does not trigger the firmware's voice prompt
  (the physical button does). Tracked in `headset/BUGS.md`.
