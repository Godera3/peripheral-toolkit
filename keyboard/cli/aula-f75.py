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
    print()
    print("Adjustments (wireless only):")
    print("  aula-f75 color <hex>        set fixed-on colour, e.g. ff0000, 00ff00, 0000ff")
    print("  aula-f75 brightness <0-9>   set brightness level (default 9, captured 5)")
    print("  aula-f75 colorful on|off     toggle colourful mode")


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


def prepare_device(dev):
    """Ensure the device is in a clean state: reset if stale claims prevent use."""
    for i in range(2):
        if dev.is_kernel_driver_active(i):
            dev.detach_kernel_driver(i)
    try:
        usb.util.claim_interface(dev, 0)
        usb.util.release_interface(dev, 0)
    except usb.core.USBError as e:
        if e.errno == 16:
            dev.reset()
            time.sleep(1)
            for i in range(2):
                if dev.is_kernel_driver_active(i):
                    dev.detach_kernel_driver(i)
            usb.util.claim_interface(dev, 0)
            usb.util.release_interface(dev, 0)


def restore_kernel_drivers(dev):
    try:
        dev.attach_kernel_driver(1)
        usb.util.dispose_resources(dev)
        return
    except Exception:
        pass
    port_str = '.'.join(str(p) for p in dev.port_numbers)
    intf_path1 = f"{dev.bus}-{port_str}:1.1"
    intf_path0 = f"{dev.bus}-{port_str}:1.0"
    sysfs = "/sys/bus/usb/drivers/usbhid"
    usb.util.dispose_resources(dev)
    try:
        with open(f"{sysfs}/bind", "w") as f:
            f.write(intf_path1)
    except Exception:
        pass
    try:
        with open(f"{sysfs}/bind", "w") as f:
            f.write(intf_path0)
    except Exception:
        pass
    try:
        import subprocess
        subprocess.run(
            ["sudo", "-n", "/usr/local/bin/aula-f75-restore-driver"],
            capture_output=True, timeout=5
        )
    except Exception:
        pass


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


def load_wireless_sequence():
    path = os.path.join(FRAG_DIR, "wireless_sequence.bin")
    with open(path, 'rb') as f:
        return bytearray(f.read())


def set_param_flag(seq, flag=0x28):
    """Patch fragment 39 byte 15 to flag (0x28 for parameter changes)."""
    idx = 39 * 20
    seq[idx + 15] = flag
    seq[idx + 19] = sum(seq[idx:idx + 19]) & 0xFF


def patch_effect_id(seq, effect_id):
    """Patch effect ID into fragment 38 byte 15 and recompute checksum."""
    idx = 38 * 20
    seq[idx + 15] = effect_id
    seq[idx + 19] = sum(seq[idx:idx + 19]) & 0xFF


def patch_color(seq, r, g, b):
    """Patch the fixed-on RGB color in fragments 0-35.
    Based on color_change capture: bytes 12-14 of fragment 1 hold the active RGB triple.
    Bytes 15-17 are a separate entry and must NOT be touched."""
    idx = 1 * 20
    seq[idx + 12] = r
    seq[idx + 13] = g
    seq[idx + 14] = b
    seq[idx + 19] = sum(seq[idx:idx + 19]) & 0xFF


def patch_brightness(seq, level):
    """Patch brightness into fragment 42 byte 7.
    Captured default is 0x09; brightness_change used 0x05."""
    idx = 42 * 20
    seq[idx + 7] = level & 0xFF
    seq[idx + 19] = sum(seq[idx:idx + 19]) & 0xFF


def patch_colorful(seq, on):
    """Patch colorful flag into fragment 42 byte 8.
    ON=0x47 (colorful_on capture), OFF=0x40 (colorful_off capture).
    Both keep effect 0x01 (fixed_on)."""
    idx = 42 * 20
    seq[idx + 8] = 0x47 if on else 0x40
    seq[idx + 19] = sum(seq[idx:idx + 19]) & 0xFF


def send_captured_sequence(dev, name):
    path = os.path.join(FRAG_DIR, f"{name}_sequence.bin")
    with open(path, 'rb') as f:
        seq = bytearray(f.read())
    gaps = load_gaps()
    send_sequence(dev, seq, gaps)


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
        print("       aula-f75 color <hex>")
        print("       aula-f75 brightness <0-9>")
        print("       aula-f75 colorful on|off")
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
        prepare_device(dev)
        iface = 1
        if dev.is_kernel_driver_active(iface):
            dev.detach_kernel_driver(iface)
        try:
            gaps = load_gaps()
            send_sequence(dev, seq, gaps)
            print("Done!")
        finally:
            restore_kernel_drivers(dev)
        return

    cmd = sys.argv[1].lower()

    if cmd in ("color", "brightness", "colorful"):
        dev = usb.core.find(idVendor=WIRELESS_VIDPID[0], idProduct=WIRELESS_VIDPID[1])
        if dev is None:
            print("Wireless AULA dongle not found.")
            sys.exit(1)

        if cmd == "color":
            if len(sys.argv) < 3:
                print("Usage: aula-f75 color <hex>")
                sys.exit(1)
            hex_color = sys.argv[2].lstrip("#")
            if len(hex_color) != 6 or not all(c in "0123456789abcdefABCDEF" for c in hex_color):
                print(f"Invalid hex colour: {sys.argv[2]}")
                sys.exit(1)
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            print(f"Setting colour: #{hex_color} (R={r}, G={g}, B={b})")
            seq = load_wireless_sequence()
            patch_effect_id(seq, 0x01)
            set_param_flag(seq, 0x28)
            patch_color(seq, r, g, b)
            # Colour change disables colourful mode in OEM software
            idx = 42 * 20
            seq[idx + 8] = 0x40
            seq[idx + 19] = sum(seq[idx:idx + 19]) & 0xFF
        elif cmd == "brightness":
            if len(sys.argv) < 3:
                print("Usage: aula-f75 brightness <0-9>")
                sys.exit(1)
            try:
                level = int(sys.argv[2])
            except ValueError:
                print(f"Invalid brightness level: {sys.argv[2]}")
                sys.exit(1)
            if not 0 <= level <= 9:
                print("Brightness level must be 0-9")
                sys.exit(1)
            print(f"Setting brightness: {level}")
            seq = load_wireless_sequence()
            patch_effect_id(seq, 0x01)
            set_param_flag(seq, 0x28)
            patch_brightness(seq, level)
        elif cmd == "colorful":
            if len(sys.argv) < 3 or sys.argv[2].lower() not in ("on", "off"):
                print("Usage: aula-f75 colorful on|off")
                sys.exit(1)
            on = sys.argv[2].lower() == "on"
            print(f"Setting colourful: {'on' if on else 'off'}")
            seq = load_wireless_sequence()
            patch_effect_id(seq, 0x01)
            set_param_flag(seq, 0x28)
            patch_colorful(seq, on)

        prepare_device(dev)
        iface = 1
        if dev.is_kernel_driver_active(iface):
            dev.detach_kernel_driver(iface)
        try:
            gaps = load_gaps()
            send_sequence(dev, seq, gaps)
            print("Done!")
        finally:
            restore_kernel_drivers(dev)
        return

    effect_id = EFFECTS.get(cmd)
    if effect_id is None:
        print(f"Unknown command or effect: {cmd}")
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

    if not is_wired:
        prepare_device(dev)

    iface = 1
    if dev.is_kernel_driver_active(iface):
        dev.detach_kernel_driver(iface)

    try:
        if is_wired:
            send_wired(dev, effect_id)
        else:
            seq = load_wireless_sequence()
            cmd_idx = 38 * 20
            seq[cmd_idx + 15] = effect_id
            seq[cmd_idx + 19] = sum(seq[cmd_idx:cmd_idx + 19]) & 0xFF
            gaps = load_gaps()
            send_sequence(dev, seq, gaps)
        print("Done!")
    finally:
        restore_kernel_drivers(dev)


if __name__ == "__main__":
    main()
