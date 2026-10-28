"""
core.py
=======
High-level API for the Barracuda X Chroma.
"""
import os, time
from . import device, protocol

EQ_MODES = {
    "game": 0x07,
    "music": 0x08,
    "movie": 0x09,
    "custom": 0xFF
}

def get_battery() -> int:
    dev = device.find_hidraw()
    # Try up to 3 times to wake up a sleeping dongle
    for attempt in range(3):
        try:
            device.send_output(dev, protocol.build_get(0x21))
            time.sleep(0.1) # Give it 100ms to wake up
            buf = device.get_feature(dev, 0x02, size=64)
            if len(buf) >= 14 and buf[10] == 0x21:
                return buf[13]
        except Exception:
            pass
        time.sleep(0.1)
    return -1

def set_eq(mode_str: str):
    mode = EQ_MODES.get(mode_str.lower())
    if mode is None:
        raise ValueError(f"Unknown EQ mode: {mode_str}. Options: {list(EQ_MODES.keys())}")
    dev = device.find_hidraw()
    device.send_output(dev, protocol.build_set(0x13, bytes([mode])))

def set_lights_off():
    dev = device.find_hidraw()
    device.send_output(dev, protocol.build_set(0x40, bytes([0x00])))

def set_lights_on():
    dev = device.find_hidraw()
    device.send_output(dev, protocol.build_set(0x40, bytes([0x0C])))

def set_sidetone(on: bool):
    dev = device.find_hidraw()
    payload = protocol.build_set(0x18, bytes([0x01 if on else 0x00]))
    device.send_output(dev, payload)

def set_sidetone_volume(percent: int):
    """Set sidetone volume. Percent 0-100 maps to hardware 0-15."""
    percent = max(0, min(100, percent))
    hw_val = round((percent / 100.0) * 15)
    
    dev = device.find_hidraw()
    payload = protocol.build_set(0x19, bytes([hw_val]))
    device.send_output(dev, payload)

def listen_events():
    dev = device.find_hidraw()
    fd = os.open(dev, os.O_RDONLY)
    try:
        while True:
            data = os.read(fd, 64)
            if not data or data[0] != 0x02:
                continue
            if len(data) >= 14 and data[10] == 0x13:
                val = data[13]
                mode_name = next((k.capitalize() for k, v in EQ_MODES.items() if v == val), f"0x{val:02X}")
                print(f"-> Headset physically changed EQ to: {mode_name}")
    except KeyboardInterrupt:
        pass
    finally:
        os.close(fd)

def get_lights_state() -> bool:
    """Reads Property 0x40 to see if lights are on."""
    dev = device.find_hidraw()
    device.send_output(dev, protocol.build_get(0x40))
    time.sleep(0.05)
    buf = device.get_feature(dev, 0x02, size=64)
    if len(buf) >= 14 and buf[10] == 0x40:
        return buf[13] != 0x00
    return False

def set_color(r: int, g: int, b: int):
    """Sets a static color (Stops the current loop)."""
    dev = device.find_hidraw()
    # Razer Static Color Payload
    payload = protocol.build_set(0x0F, bytes([0x01, 0x01, 0x01, 0x01, 0x00, 0x00, r, g, b]))
    device.send_output(dev, payload)

def get_eq() -> int:
    """Reads Property 0x13 to get the current EQ mode."""
    dev = device.find_hidraw()
    device.send_output(dev, protocol.build_get(0x13))
    time.sleep(0.05)
    buf = device.get_feature(dev, 0x02, size=64)
    if len(buf) >= 14 and buf[10] == 0x13:
        return buf[13]
    return -1

def get_sidetone_volume() -> int:
    """Reads Property 0x19 to get the current sidetone volume (0-15)."""
    dev = device.find_hidraw()
    device.send_output(dev, protocol.build_get(0x19))
    time.sleep(0.05)
    buf = device.get_feature(dev, 0x02, size=64)
    if len(buf) >= 14 and buf[10] == 0x19:
        return buf[13]
    return -1
