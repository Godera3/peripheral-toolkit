"""
core.py
=======
Public operations, one plain function each. They either return ``None`` on
success or raise — no printing and no `sys.exit`, so the CLI and the PyQt
frontend can both call them directly.
"""
from __future__ import annotations

import time

from . import device, protocol
from .effects import ALIASES

# bmRequestType / bRequest for a HID SET_REPORT.
CONTROL_OUT = 0x21
CONTROL_SET_REPORT = 0x09

# wValue high byte: 0x03 for wired frames, 0x02 (with low byte 0x13) wireless.
WIRED_CONTROL_HIGH = 0x03
WIRELESS_CONTROL_HIGH = 0x02
WIRELESS_CONTROL_LOW = 0x13

DEFAULT_GAP = 0.03
WIRED_GAP = 0.02
CTRL_TIMEOUT_MS = 5000

# The fixed-on effect code that colour / brightness / colourful all build on.
FIXED_ON = 0x01
PARAM_CHANGE_FLAG = 0x28


def _send_wireless(dev, seq: bytearray, gaps: list[float] | None = None) -> None:
    count = len(seq) // protocol.WIRELESS_FRAG_LEN
    for i in range(count):
        off = i * protocol.WIRELESS_FRAG_LEN
        frag = bytes(seq[off:off + protocol.WIRELESS_FRAG_LEN])
        transferred = dev.ctrl_transfer(
            CONTROL_OUT,
            CONTROL_SET_REPORT,
            (WIRELESS_CONTROL_HIGH << 8) | WIRELESS_CONTROL_LOW,
            device.VENDOR_IFACE,
            frag,
            CTRL_TIMEOUT_MS,
        )
        if transferred != len(frag):
            raise IOError(f"short transfer: {transferred}/{len(frag)} bytes at frame {i}")
        gap = gaps[i] if gaps and i < len(gaps) else DEFAULT_GAP
        time.sleep(gap)


def _send_wired(dev, effect_id: int) -> None:
    try:
        frags = protocol.load_wired_fragments(effect_id)
    except (KeyError, FileNotFoundError) as exc:
        raise RuntimeError(f"no wired fragments for effect 0x{effect_id:02x}: {exc}")
    for frag in frags:
        w_value = (WIRED_CONTROL_HIGH << 8) | frag[0]
        dev.ctrl_transfer(
            CONTROL_OUT, CONTROL_SET_REPORT, w_value, device.VENDOR_IFACE, frag, CTRL_TIMEOUT_MS
        )
        time.sleep(WIRED_GAP)


def _require_wireless(kind: str, what: str) -> None:
    if kind != "wireless":
        raise RuntimeError(f"{what} is only supported on the wireless dongle")


def _wireless_param_sequence():
    """A wireless sequence primed for a fixed-on parameter change."""
    seq = protocol.load_wireless_sequence()
    protocol.patch_effect_id(seq, FIXED_ON)
    protocol.set_param_flag(seq, PARAM_CHANGE_FLAG)
    return seq


def set_effect(alias: str) -> None:
    """Apply an effect by its CLI alias (see `effects.ALIASES`)."""
    alias = alias.lower()
    effect_id = ALIASES.get(alias)
    if effect_id is None:
        raise ValueError(f"unknown effect: {alias!r}")

    dev, kind = device.find()
    with device.Session(dev, kind) as d:
        if kind == "wired":
            _send_wired(d, effect_id)
        else:
            seq = protocol.load_wireless_sequence()
            protocol.patch_effect_id(seq, effect_id)
            _send_wireless(d, seq, protocol.load_gaps())


def set_color(hex_color: str) -> None:
    """Set the fixed-on colour from a 6-digit hex string (``RRGGBB``)."""
    value = hex_color.lstrip("#")
    if len(value) != 6 or any(c not in "0123456789abcdefABCDEF" for c in value):
        raise ValueError(f"invalid hex colour: {hex_color!r}")

    r, g, b = int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
    # Adjustments target the dongle explicitly (the original queried the
    # wireless VID/PID only, never falling back to the wired device).
    dev, kind = device.find("wireless")
    with device.Session(dev, kind) as d:
        seq = _wireless_param_sequence()
        protocol.patch_color(seq, r, g, b)
        # The OEM software clears colourful mode whenever a colour is picked.
        protocol.patch_colorful(seq, False)
        _send_wireless(d, seq, protocol.load_gaps())


def set_brightness(level: int) -> None:
    """Set the brightness level, 0-9."""
    if not 0 <= level <= 9:
        raise ValueError("brightness must be 0-9")

    dev, kind = device.find("wireless")
    with device.Session(dev, kind) as d:
        seq = _wireless_param_sequence()
        protocol.patch_brightness(seq, level)
        _send_wireless(d, seq, protocol.load_gaps())


def set_colorful(on: bool) -> None:
    """Turn the default multi-colour (colourful) mode on or off."""
    dev, kind = device.find("wireless")
    with device.Session(dev, kind) as d:
        seq = _wireless_param_sequence()
        protocol.patch_colorful(seq, on)
        _send_wireless(d, seq, protocol.load_gaps())


def set_sleep(value: int) -> None:
    """Set sleep mode.

    ``value`` is ``0x00`` (off), ``0x03`` (on, default timeout) or ``1..255``
    minutes.
    """
    if not 0 <= value <= 0xFF:
        raise ValueError("sleep value must be 0-255")

    dev, kind = device.find()
    _require_wireless(kind, "sleep")
    with device.Session(dev, kind) as d:
        seq = protocol.load_sleep_sequence()
        protocol.patch_sleep(seq, value)
        _send_wireless(d, seq, protocol.load_gaps("sleep_gaps.bin"))
