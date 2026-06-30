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
pip install pyusb
sudo python3 keyboard/cli/aula-f75.py list
sudo python3 keyboard/cli/aula-f75.py rainbow
sudo python3 keyboard/cli/aula-f75.py sleep off
```

## Structure

```
keyboard/    AULA F75 — captures, CLI tool, protocol docs
mouse/       Logitech G Pro X 2 — (coming soon)
headset/     Razer Barracuda X — (coming soon)
```
