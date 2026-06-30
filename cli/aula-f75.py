#!/usr/bin/env python3
import os, sys, time, struct
import usb.core
import usb.util

FRAG_DIR = os.path.join(os.path.dirname(__file__), "fragments")

WIRED_VIDPID = (0x258a, 0x010c)
WIRELESS_VIDPID = (0x3554, 0xfa09)

EFFECTS = {
    "off": 0x00,
    "fixed": 0x01, "fixed-on": 0x01,
    "respire": 0x02,
    "rainbow": 0x03,
    "flash-away": 0x04, "flashaway": 0x04,
    "raindrops": 0x05,
    "rainbow-wheel": 0x06, "rainbowwheel": 0x06,
    "ripples": 0x07, "ripples-shining": 0x07,
    "stars": 0x08, "stars-twinkle": 0x08,
    "retro-snake": 0x0a, "retrosnake": 0x0a,
    "neon": 0x0b, "neon-stream": 0x0b,
    "reaction": 0x0c,
    "sine-wave": 0x0d, "sinewave": 0x0d,
    "windmill": 0x0f, "rotating-windmill": 0x0f,
    "waterfall": 0x10, "colorful-waterfall": 0x10,
    "blossoming": 0x11,
}

EFFECT_NAMES = {
    0x00: "Light Off", 0x01: "Fixed On", 0x02: "Respire",
    0x03: "Rainbow", 0x04: "Flash Away", 0x05: "Raindrops",
    0x06: "Rainbow Wheel", 0x07: "Ripples Shining", 0x08: "Stars Twinkle",
    0x0a: "Retro Snake", 0x0b: "Neon Stream", 0x0c: "Reaction",
    0x0d: "Sine Wave", 0x0f: "Rotating Windmill",
    0x10: "Colorful Waterfall", 0x11: "Blossoming",
}

SLEEP_MODES = {
    "off": 0x00,
    "on": 0x03,
}


def list_effects():
    seen = set()
    for alias, eid in sorted(EFFECTS.items(), key=lambda x: x[1]):
        if eid not in seen:
            name = EFFECT_NAMES.get(eid, f"0x{eid:02x}")
            aliases = [k for k, v in EFFECTS.items() if v == eid]
            print(f"  0x{eid:02x} {name:20s} ({', '.join(aliases)})")
            seen.add(eid)
    print()
    print("Sleep modes: (aula-f75 sleep <mode> [timeout])")
    modes = sorted(SLEEP_MODES.items(), key=lambda x: x[1])
    for name, val in modes:
        print(f"  0x{val:02x}  sleep-{name}")
    print("  or:  aula-f75 sleep on <minutes>")


def send_wired(dev, effect_id):
    for prefix in ["01_", "02_", "03_", "04_", "05_", "06_", "07_", "08_",
                    "09_", "10_", "11_", "12_", "13_", "14_", "15_", "16_", "17_"]:
        effect_name = {v: k for k, v in {
            "fixed_on": 1, "light_off": 0, "respire": 2, "rainbow": 3,
            "flash_away": 4, "raindrops": 5, "rainbow_wheel": 6,
            "ripples_shining": 7, "stars_twinkle": 8, "retro_snake": 0xa,
            "neon_stream": 0xb, "reaction": 0xc, "sine_wave": 0xd,
            "rotating_windmill": 0xf, "colorful_waterfall": 0x10,
            "blossoming": 0x11, "self_define": 0x15,
        }.items()}.get(effect_id)
        if not effect_name:
            continue
        path = os.path.join(FRAG_DIR, f"{prefix}{effect_name}_frag0.bin")
        if not os.path.exists(path):
            continue
        for i in range(3):
            path = os.path.join(FRAG_DIR, f"{prefix}{effect_name}_frag{i}.bin")
            with open(path, 'rb') as f:
                frag = f.read()
            wValue = (0x03 << 8) | frag[0]
            dev.ctrl_transfer(0x21, 0x09, wValue, 1, frag, 5000)
            time.sleep(0.02)
        return True
    return False


def load_gaps():
    path = os.path.join(FRAG_DIR, "wireless_gaps.bin")
    if os.path.exists(path):
        import struct
        data = open(path, 'rb').read()
        gap_count = len(data) // 8
        return list(struct.unpack('<' + 'd' * gap_count, data))
    return None


def send_sequence(dev, seq_bytes, gaps=None):
    for i in range(0, len(seq_bytes), 20):
        dev.ctrl_transfer(0x21, 0x09, (0x02 << 8) | 0x13, 1,
                          bytes(seq_bytes[i:i + 20]), 5000)
        if gaps and i // 20 < len(gaps):
            time.sleep(gaps[i // 20])
        else:
            time.sleep(0.03)


def load_sleep_gaps():
    path = os.path.join(FRAG_DIR, "sleep_gaps.bin")
    if os.path.exists(path):
        data = open(path, 'rb').read()
        gap_count = len(data) // 8
        return list(struct.unpack('<' + 'd' * gap_count, data))
    return None


def send_sleep(dev, sleep_value):
    path = os.path.join(FRAG_DIR, "sleep_sequence.bin")
    with open(path, 'rb') as f:
        seq = bytearray(f.read())
    frag2_offset = 2 * 20
    seq[frag2_offset + 15] = sleep_value
    seq[frag2_offset + 19] = sum(seq[frag2_offset:frag2_offset + 19]) & 0xFF
    gaps = load_sleep_gaps()
    send_sequence(dev, bytes(seq), gaps)


def main():
    if len(sys.argv) < 2:
        print("Usage: aula-f75 <effect>")
        print("       aula-f75 list")
        print("       aula-f75 sleep <mode> [timeout]")
        sys.exit(1)

    if sys.argv[1] == "list":
        list_effects()
        return

    if sys.argv[1] == "sleep":
        if len(sys.argv) < 3:
            print("Usage: aula-f75 sleep <mode> [timeout_minutes]")
            print("Modes: off, on")
            print("  off        - disable sleep")
            print("  on         - enable sleep (default timeout)")
            print("  on <n>     - enable sleep, N-minute timeout")
            print("  <minutes>  - set timeout only (e.g., 40)")
            sys.exit(1)

        sleep_arg = sys.argv[2].lower()
        sleep_value = SLEEP_MODES.get(sleep_arg)

        if sleep_value is not None:
            if len(sys.argv) > 3:
                try:
                    timeout = int(sys.argv[3])
                    sleep_value = timeout
                except ValueError:
                    print(f"Invalid timeout: {sys.argv[3]}")
                    sys.exit(1)
        else:
            try:
                sleep_value = int(sleep_arg)
            except ValueError:
                print(f"Unknown sleep mode: {sleep_arg}")
                sys.exit(1)

        dev = (usb.core.find(idVendor=WIRED_VIDPID[0], idProduct=WIRED_VIDPID[1]) or
               usb.core.find(idVendor=WIRELESS_VIDPID[0], idProduct=WIRELESS_VIDPID[1]))
        if dev is None:
            print("AULA keyboard not found.")
            sys.exit(1)

        is_wired = (dev.idVendor, dev.idProduct) == WIRED_VIDPID
        if is_wired:
            print("Sleep is only supported on wireless dongle.")
            sys.exit(1)

        print(f"Setting sleep: value=0x{sleep_value:02x} ({sleep_value})")
        iface = 1
        if dev.is_kernel_driver_active(iface):
            dev.detach_kernel_driver(iface)
        try:
            send_sleep(dev, sleep_value)
            print("Done!")
        finally:
            usb.util.dispose_resources(dev)
        return

    effect_arg = sys.argv[1].lower()
    effect_id = EFFECTS.get(effect_arg)
    if effect_id is None:
        print(f"Unknown effect: {effect_arg}")
        print("Run 'aula-f75 list' to see available effects")
        sys.exit(1)

    dev = (usb.core.find(idVendor=WIRED_VIDPID[0], idProduct=WIRED_VIDPID[1]) or
           usb.core.find(idVendor=WIRELESS_VIDPID[0], idProduct=WIRELESS_VIDPID[1]))

    if dev is None:
        print("AULA keyboard not found.")
        print(f"Looked for: wired ({WIRED_VIDPID[0]:04x}:{WIRED_VIDPID[1]:04x})")
        print(f"        and: wireless dongle ({WIRELESS_VIDPID[0]:04x}:{WIRELESS_VIDPID[1]:04x})")
        sys.exit(1)

    is_wired = (dev.idVendor, dev.idProduct) == WIRED_VIDPID
    device_type = "wired" if is_wired else "wireless"
    print(f"Found {device_type} device ({dev.idVendor:04x}:{dev.idProduct:04x})")
    print(f"Setting: {EFFECT_NAMES.get(effect_id, f'0x{effect_id:02x}')}")

    iface = 1
    if dev.is_kernel_driver_active(iface):
        dev.detach_kernel_driver(iface)

    try:
        if is_wired:
            send_wired(dev, effect_id)
        else:
            path = os.path.join(FRAG_DIR, "wireless_sequence.bin")
            with open(path, 'rb') as f:
                seq = bytearray(f.read())
            cmd_idx = 38 * 20
            seq[cmd_idx + 15] = effect_id
            seq[cmd_idx + 19] = sum(seq[cmd_idx:cmd_idx + 19]) & 0xFF
            gaps = load_gaps()
            send_sequence(dev, seq, gaps)
        print("Done!")
    finally:
        usb.util.dispose_resources(dev)


if __name__ == "__main__":
    main()
