"""
aula_f75
========
Shared driver package for the AULA F75 keyboard.

Imported directly by both `cli.py` and the PyQt frontend — no subprocess, no
stdout parsing, no venv/ system-Python mismatch::

    from aula_f75 import set_effect, set_color, set_colorful, set_sleep

    set_effect("rainbow")
    set_color("ff8800")
    set_sleep(0x00)

Every operation returns ``None`` on success and raises on failure. See
`device.DeviceNotFound` for the "keyboard is not plugged in" case.
"""
from __future__ import annotations

from . import device, protocol
from .core import (
    set_brightness,
    set_color,
    set_colorful,
    set_effect,
    set_sleep,
)
from .device import (
    DeviceBusy,
    DeviceNotFound,
    WiredNotFound,
    WirelessNotFound,
)
from .effects import (
    ALIASES,
    BY_CODE,
    EFFECTS,
    NAME_BY_CODE,
    WIRED_PREFIX,
    WIRELESS_CAPABLE,
)

__all__ = [
    # operations
    "set_effect",
    "set_color",
    "set_brightness",
    "set_colorful",
    "set_sleep",
    # exceptions
    "DeviceNotFound",
    "WiredNotFound",
    "WirelessNotFound",
    "DeviceBusy",
    # data
    "EFFECTS",
    "BY_CODE",
    "NAME_BY_CODE",
    "ALIASES",
    "WIRED_PREFIX",
    "WIRELESS_CAPABLE",
    # submodules
    "device",
    "protocol",
]
