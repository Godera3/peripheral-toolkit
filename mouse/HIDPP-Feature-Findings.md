# Logitech G Pro X 2 SE — HID++ 2.0 findings

Recorded 2026-11-25 from live hardware. Read only, except one button-map
write that was restored and verified. Full history is in the HUB vault at
`01-Projects/Peripheral-RE.md` and `02-Sessions/2026-11-25.md`.

## Hardware

- Receiver `046d:c547` on USB `1-1`, paired mouse `046d:40a9`.
- `hidraw1` boot mouse, `hidraw2` boot keyboard, `hidraw3` HID++ vendor
  interface, `hidraw8` paired device. `hidraw*` are root-only, so run the
  probe as `pkexec python3 /absolute/path/hidpp_feature_probe.py`.
- UPower names it `PRO X SUPERLIGHT 2 SE`. Battery read 56–57%.

## Wire rules confirmed here

- Long report `0x11` is the reliable request form. Replies always arrive as
  long `0x11` reports, even for short `0x10` requests.
- Byte 3 is `(function << 4) | softwareId`. Software ID must be non-zero.
- Device index `1` addresses the paired mouse. Feature indexes below are from
  this device, not hardcoded guesses.

## Feature map (32 entries)

| Index | ID | Meaning |
|-------|----|---------|
| 00 | `0x0000` | ROOT |
| 01 | `0x0001` | FEATURE_SET |
| 02 | `0x0003` | DEVICE_INFO |
| 03 | `0x0005` | DEVICE_NAME, `PRO X SUPERLIGHT 2 SE` (21 bytes) |
| 04 | `0x1d4b` | wirelessDeviceStatus |
| 05 | `0x0020` | configChange |
| 06 | `0x1004` | unifiedBattery |
| 07 | `0x2250` | xyStats |
| 08 | `0x2251` | wheelStats |
| 09 | `0x2202` | extendedAdjustableDpi |
| 10 | `0x8090` | modeStatus |
| 11 | `0x80e0` | not identified |
| 12 | `0x8061` | extendedAdjustableReportRate |
| 13 | `0x8100` | onboardProfiles |
| 14 | `0x8110` | mouseButtonFilter |
| 15 | `0x1500` | not identified |
| 16 | `0x1801` | not identified |
| 17 | `0x1802` | deviceReset |
| 18 | `0x1803` | not identified |
| 19 | `0x1806` | configDeviceProps |
| 20 | `0x1817` | not identified |
| 21 | `0x1805` | oobState |
| 22 | `0x1830` | not identified |
| 23 | `0x1875` | not identified |
| 24 | `0x1861` | not identified |
| 25 | `0x1890` | not identified |
| 26 | `0x18a1` | not identified |
| 27 | `0x1e00` | not identified |
| 28 | `0x1e02` | not identified |
| 29 | `0x1e22` | not identified |
| 30 | `0x1602` | not identified |
| 31 | `0x1eb0` | not identified |

Legacy `0x2201` adjustableDpi and `0x8060` report rate are absent. This mouse
uses the extended variants. Names come from the public OpenLogi feature index
and Logitune HID++ wiki, not from running their code.

## Reads that worked

- battery `0x1004` fn1 → `0x38` = 56%
- DPI presets `0x2202` fn3 → 800, 1200, 1600, 2400, 3200
- current DPI `0x2202` fn5 → X/Y 800, default 800, LOD `0x02`
- DPI X range `0x2202` fn2 starts at 100 with step markers
- modeStatus `0x8090` fn0 → `00 02`, fn2 capabilities → `00 0c`
- onboardProfiles `0x8100` fn0 → `01 07 01 05 01 05 10 00`, fn2 → `01`
  (onboard mode), fn4 active profile → `1`
- buttonFilter `0x8110` fn0 → five buttons, fn3 map → `01 02 03 04 05`

Report rate `0x8061` still needs its wire format recovered.

## DPI write round-trip (verified 2026-11-25)

- `0x8100` fn2 mode reads `1` at rest. fn1 with value `2` switches to host
  mode; fn1 with `0` or `1` leaves it at `1`. Restored to `1` after testing.
- `0x2202` fn6 in onboard mode returns error report `11 01 ff 09 61 05`,
  where `0x05` is Busy. In host mode the same write succeeds when sent as a
  long report with `[sensor, dpi_x BE, dpi_y BE, lod]`, for example
  `00 06 40 06 40 02` for 1600 DPI and LOD 2.
- Read-back after the write showed X/Y 1600 while the stored defaults stayed
  800. Restoring onboard mode reverted the live DPI to 800. Host-mode DPI is
  therefore volatile; persistence needs the `0x8100` profile sector write.
- `mouse/hidpp_dpi.py` wraps get/set, switches to host mode only when needed
  and restores the original mode. Tested 800 → 1600 → 800 with read-back.

## Caution

An exploratory sweep sent `0x8110` fn4 `SetButtonMap` with a zero payload and
cleared the button map. It was restored to `01 02 03 04 05` immediately and
verified with fn3. Never sweep unknown function numbers. Resolve each one
from protocol docs first, and read state before any call that might write.

## Next

Work from documented function tables and verify every write with a read-back.
Windows G Hub capture is only a fallback for layouts the docs leave unresolved.
`lghub_installer.exe` is still unopened. REA belongs to the later static
installer pass, not this live-probe phase.
