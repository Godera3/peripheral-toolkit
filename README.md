# Peripheral Toolkit

Linux-native CLI tools for reverse-engineered gaming peripherals.

## Devices

| Device | Type | USB ID | Status |
|--------|------|--------|--------|
| AULA F75 | Keyboard | `258a:010c` (wired), `3554:fa09` (wireless) | ✅ 16 RGB effects + sleep control |
| Logitech G Pro X 2 Superlight | Mouse | `046d:c547` | ⏸️ Captures pending |
| Razer Barracuda X Chroma | Headset | `1532:0574` | ⏸️ Captures pending |

## Usage

```bash
# Dependency: pyusb (pure Python, talks to libusb-1.0).
# Debian/Ubuntu/Mint: sudo apt install python3-usb  (or: pip install pyusb)
pip install pyusb

# Either run with sudo...
sudo python3 keyboard/cli/aula-f75.py list
sudo python3 keyboard/cli/aula-f75.py rainbow
sudo python3 keyboard/cli/aula-f75.py sleep off

# ...or install the included udev rule once and run without sudo (recommended).
# See keyboard/README.md → "Permissions".
```

USB access needs read/write on the keyboard's device node, which only root
has by default. Install [`keyboard/frontend/claude/99-aula-f75.rules`](keyboard/frontend/claude/99-aula-f75.rules)
to grant your user direct access and drop `sudo` entirely.

## Structure

```
keyboard/    AULA F75 — captures, CLI tool, protocol docs
mouse/       Logitech G Pro X 2 — (coming soon)
headset/     Razer Barracuda X — (coming soon)
```
