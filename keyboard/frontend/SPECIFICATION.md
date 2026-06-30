# AULA F75 Keyboard Frontend Specification

## Goal
Build a modern GUI frontend for the AULA F75 mechanical keyboard RGB controller. The backend (`../cli/aula-f75.py`) handles all USB communication — the frontend is purely a GUI shell that calls it.

## Backend CLI Reference

### `aula-f75 list`
Lists effects + sleep modes. Output format:

```
  0x00 Light Off           (off)
  0x01 Fixed On            (fixed, fixed-on)
  0x02 Respire             (respire)
  0x03 Rainbow             (rainbow)
  0x04 Flash Away          (flash-away, flashaway)
  0x05 Raindrops           (raindrops)
  0x06 Rainbow Wheel       (rainbow-wheel, rainbowwheel)
  0x07 Ripples Shining     (ripples, ripples-shining)
  0x08 Stars Twinkle       (stars, stars-twinkle)
  0x0a Retro Snake         (retro-snake, retrosnake)
  0x0b Neon Stream         (neon, neon-stream)
  0x0c Reaction            (reaction)
  0x0d Sine Wave           (sine-wave, sinewave)
  0x0f Rotating Windmill   (windmill, rotating-windmill)
  0x10 Colorful Waterfall  (waterfall, colorful-waterfall)
  0x11 Blossoming          (blossoming)

Sleep modes:
  0x00  sleep-off
  0x03  sleep-on
  or:  aula-f75 sleep on <minutes>
```

### `aula-f75 <effect-name>`
Applies effect immediately. Auto-detects wired (`258a:010c`) vs wireless dongle (`3554:fa09`).
- Exit 0 + prints "Done!" on success
- Exit 1 + prints "AULA keyboard not found." on failure
- **Must run as root** (sudo)

### `aula-f75 sleep <mode> [timeout]`
- `aula-f75 sleep off` — disable sleep
- `aula-f75 sleep on` — enable, default timeout
- `aula-f75 sleep on 40` — enable, 40-minute timeout
- Wireless dongle only; prints error on wired

## Frontend Requirements

### Must have
- Device detection: show status (wired / wireless / disconnected)
- Effect browser: all 16 effects listed with human-readable names
- One-click apply: tap an effect to send it to keyboard
- Connection indicator: clearly show wired vs wireless
- Sleep controls: toggle on/off, set timeout (numeric input or slider)
- Graceful error handling: if keyboard disconnected, show clear message
- Must run on Linux (Mint 22.3 Cinnamon X11)

### Nice to have
- Color preview swatch next to each effect
- Current effect highlighted
- Loading spinner while effect is applying
- Keyboard disconnected → disable controls + show reconnect button
- System tray integration (optional)

### Privilege escalation
**Option A — udev rule (recommended, zero-auth):** Create `/etc/udev/rules.d/99-aula-f75.rules`:
```
SUBSYSTEM=="usb", ATTR{idVendor}=="258a", ATTR{idProduct}=="010c", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="3554", ATTR{idProduct}=="fa09", MODE="0666"
```
Then `sudo udevadm control --reload-rules && udevadm trigger`. This grants user rw access to both devices — the backend runs without any sudo.

**Option B — pkexec wrapper:** Create a small shell script that runs `pkexec python3 ../cli/aula-f75.py "$@"` and call that instead. Polkit pops a GUI auth dialog.

**Do not use bare sudo in subprocess.** Pick one option above.

### Technical constraints
- **Do not write USB/HID code** — call the CLI tool only
- Python preferred for easiest integration with existing Python backend
- GUI framework: any (PyQt6, GTK4, tkinter, web, Tauri, etc.)
- Put all files in a `frontend/` directory under `keyboard/`
- MIT or GPLv3 license
- Provide `requirements.txt` or install instructions

### File structure
```
keyboard/
├── cli/
│   ├── aula-f75.py          # backend — don't modify
│   └── fragments/           # binary fragment data
└── frontend/
    └── (your code here)
```

## What to deliver
1. Complete frontend source code (single script or small project)
2. `requirements.txt` or dependency list
3. Install + run instructions
4. Read the backend `aula-f75.py` code to understand its output format if needed
