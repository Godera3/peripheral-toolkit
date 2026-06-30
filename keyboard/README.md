# AULA F75 Keyboard — Linux RGB Controller

Reverse-engineered USB HID protocol for the AULA F75 mechanical keyboard. Control RGB lighting from Linux on both **wired** (USB) and **wireless** (2.4 GHz dongle) connections.

## Quick Start

```bash
pip install pyusb
sudo python3 cli/aula-f75.py list          # see all effects
sudo python3 cli/aula-f75.py rainbow       # set an effect
sudo python3 cli/aula-f75.py sleep off     # disable sleep
sudo python3 cli/aula-f75.py sleep on 40   # enable sleep, 40min timeout
```

## Effects

| ID | Name | Aliases |
|----|------|---------|
| 0x00 | Light Off | off |
| 0x01 | Fixed On | fixed, fixed-on |
| 0x02 | Respire | respire |
| 0x03 | Rainbow | rainbow |
| 0x04 | Flash Away | flash-away, flashaway |
| 0x05 | Raindrops | raindrops |
| 0x06 | Rainbow Wheel | rainbow-wheel, rainbowwheel |
| 0x07 | Ripples Shining | ripples, ripples-shining |
| 0x08 | Stars Twinkle | stars, stars-twinkle |
| 0x0a | Retro Snake | retro-snake, retrosnake |
| 0x0b | Neon Stream | neon, neon-stream |
| 0x0c | Reaction | reaction |
| 0x0d | Sine Wave | sine-wave, sinewave |
| 0x0f | Rotating Windmill | windmill, rotating-windmill |
| 0x10 | Colorful Waterfall | waterfall, colorful-waterfall |
| 0x11 | Blossoming | blossoming |

## Protocol

The Windows OEM software uses a different protocol depending on connection type:

### Wired (`258a:010c`)
- **3 fragments** × 520 bytes via USB control transfer (SET_REPORT, Feature type 0x03, Report 0x06)
- Fragment 0: RGB color table (`06 0a 00`)
- Fragment 1: Zero padding (`06 84 00`)
- Fragment 2: Effect config (`06 04 00`) — effect ID at offset 0x12

### Wireless (`3554:fa09`)
- **48 fragments** × 20 bytes via USB control transfer (SET_REPORT, Output type 0x02, Report 0x13)
- Only fragment 38 differs between effects (byte 15 = effect ID, byte 19 = sum checksum)
- Critical timing: ~171ms pause before fragment 38, ~60-105ms before fragment 37
- Uses libusb (not hidraw) — the dongle has no interrupt OUT endpoint

### Sleep (wireless only)
- **11 fragments** × 20 bytes
- Fragment 0: Init/commit (`13 44 01 00`)
- Fragment 1: Effect command (always fixed_on)
- Fragment 2: Sleep parameter at byte 15 (`0x00`=off, `0x03`=on, `0x28`=timeout)

## Driver Recovery

If the keyboard stops responding after a USB reset:
```bash
# Find the device bus-port
lsusb -t
# Unbind/rebind
sudo sh -c 'echo -n "1-5" > /sys/bus/usb/drivers/usb/unbind'
sudo sh -c 'echo -n "1-5" > /sys/bus/usb/drivers/usb/bind'
```

## Contents

- `cli/aula-f75.py` — Main CLI tool (auto-detects wired vs wireless)
- `cli/replay_capture.py` — Replay exact pcapng captures with original timing
- `cli/fragments/` — Extracted fragment binaries for all effects
- `wired/` — 17 wired light effect pcapng captures
- `wireless/` — 17 wireless + 3 sleep pcapng captures
- `capture_aula.ps1` — PowerShell capture script (wired)
- `capture_wireless.ps1` — PowerShell capture script (wireless)
