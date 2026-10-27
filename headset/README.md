# Razer Barracuda X Chroma — Linux Controller

> **New to this tool?** Read the [CLI_GUIDE.md](CLI_GUIDE.md) for a simple, step-by-step explanation of every command.

Reverse-engineered USB HID protocol for the Razer Barracuda X Chroma headset.
Control EQ modes, Chroma lighting, and battery telemetry from Linux without
Razer Synapse.

## Quick Start

    python3 cli/barracuda.py battery      # current battery percentage
    python3 cli/barracuda.py eq movie     # game / music / movie / custom
    python3 cli/barracuda.py lights-off   # Chroma lighting off
    python3 cli/barracuda.py lights-on    # Chroma lighting on
    python3 cli/barracuda.py listen       # watch physical EQ button presses

## Permissions

Needs read/write on `/dev/hidraw*`. Install the udev rule once:

    sudo tee /etc/udev/rules.d/99-razer-barracuda-x-chroma.rules <<'RULE'
    SUBSYSTEM=="hidraw", ATTRS{idVendor}=="1532", ATTRS{idProduct}=="0574", MODE="0660", GROUP="plugdev", TAG+="uaccess"
    RULE
    sudo udevadm control --reload-rules
    sudo udevadm trigger

## Protocol

- USB ID `1532:0574`, Interface 3 (HID)
- Report ID `0x02`, 64 bytes
  - Host to device: control transfer, Output report (wValue 0x0202)
  - Device to host: interrupt IN
- Checksum: byte 62 = XOR of bytes 0..61
- Full property map, framing, and experiment log: see `captures/PLAN.md`

## Layout

    headset/__init__.py
    headset/protocol.py    — frame builder, XOR checksum
    headset/device.py      — hidraw lookup, feature/output transport
    headset/core.py        — get_battery, set_eq, set_lights_*, listen_events
    cli/barracuda.py       — argparse wrapper
    captures/PLAN.md       — reverse-engineering notes
    vm/                    — Windows 10 RE guest setup

## Known Issues

See `BUGS.md`. Main one: EQ write via USB does not trigger the firmware's
voice prompt (physical button press does).


## Performance & System Footprint

Unlike Razer Synapse (which uses 300-500MB of RAM, installs kernel drivers, and constantly polls USB devices), this toolkit is designed with a **zero-overhead, event-driven architecture**. 

### Real-World Benchmarks
Measured on a Linux system running these daemons 24/7:

| Metric | Volume Daemon | Sidetone Daemon | Total Impact |
| :--- | :--- | :--- | :--- |
| **Idle CPU** | 0.0% | 0.0% | **0.0%** |
| **RAM (RSS)** | ~4.9 MB | ~6.1 MB | **~11 MB** |
| **Disk I/O** | 0 B/s | 0 B/s | **Zero** |
| **Processes** | 1 | 2 | **3 total** |

### Why is it so lightweight?
1. **Blocking I/O (Volume):** The volume daemon uses a direct kernel `os.read()`. The CPU puts the process to sleep until the exact millisecond you turn the physical wheel. It does not poll.
2. **Event-Driven (Sidetone):** The sidetone daemon listens to PipeWire's native event stream (`pactl subscribe`). It sits at 0.0% CPU and only wakes up when an application actually opens the microphone.
3. **No Logs, No Caches:** The daemons do not write to your SSD unless you explicitly trigger a hardware state change.

*Both daemons run as standard `systemd --user` services, meaning they start instantly at login, survive reboots, and run with unprivileged user permissions (no `sudo` required).*
