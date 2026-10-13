"""
device.py
=========
Finding the keyboard and managing the vendor interface.

The AULA F75 exposes a vendor HID interface (interface 1) that must be
detached from `usbhid` before we can send SET_REPORTs, and handed back when
we are done so the rotary knob / media keys keep working. `Session` owns that
round-trip.
"""
from __future__ import annotations

import time

import usb.core
import usb.util

WIRED_VIDPID = (0x258a, 0x010c)
WIRELESS_VIDPID = (0x3554, 0xfa09)

VENDOR_IFACE = 1


class DeviceNotFound(Exception):
    """No AULA keyboard (wired or wireless dongle) is connected."""


class DeviceBusy(Exception):
    """The vendor interface could not be detached from the kernel driver."""


def find(kind: str | None = None):
    """Return ``(dev, kind)`` for the keyboard, or raise `DeviceNotFound`.

    ``kind`` may be ``"wired"`` or ``"wireless"`` to require a specific
    connection; by default the wired device is preferred, then the dongle.
    """
    if kind in (None, "wired"):
        dev = usb.core.find(idVendor=WIRED_VIDPID[0], idProduct=WIRED_VIDPID[1])
        if dev is not None:
            return dev, "wired"
    if kind in (None, "wireless"):
        dev = usb.core.find(idVendor=WIRELESS_VIDPID[0], idProduct=WIRELESS_VIDPID[1])
        if dev is not None:
            return dev, "wireless"
    raise DeviceNotFound("AULA keyboard not found.")


def restore(dev) -> None:
    """Give the vendor interface back to `usbhid`.

    Order matters: the libusb handle must be released *before* re-attaching,
    otherwise `attach_kernel_driver()` fails with EBUSY (Errno 16) after any
    control transfer. A root-only sysfs bind and the optional setuid helper
    are kept as best-effort fallbacks; both are no-ops for unprivileged
    callers.
    """
    try:
        port_str = ".".join(str(p) for p in dev.port_numbers)
        bus = dev.bus
    except Exception:
        port_str, bus = None, None

    try:
        usb.util.dispose_resources(dev)
    except Exception:
        pass

    try:
        dev.attach_kernel_driver(VENDOR_IFACE)
        return
    except Exception:
        pass

    if port_str is None:
        return

    sysfs = "/sys/bus/usb/drivers/usbhid"
    for intf in (f"{bus}-{port_str}:1.1", f"{bus}-{port_str}:1.0"):
        try:
            with open(f"{sysfs}/bind", "w") as fh:
                fh.write(intf)
        except Exception:
            pass

    try:
        import subprocess

        subprocess.run(
            ["sudo", "-n", "/usr/local/bin/aula-f75-restore-driver"],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass


class Session:
    """Detach the vendor interface on enter, restore it on exit.

    Usage::

        dev, kind = device.find()
        with device.Session(dev, kind) as d:
            ...  # send control transfers
    """

    def __init__(self, dev, kind: str):
        self.dev = dev
        self.kind = kind

    def __enter__(self):
        try:
            if self.dev.is_kernel_driver_active(VENDOR_IFACE):
                self.dev.detach_kernel_driver(VENDOR_IFACE)
        except Exception:
            pass
        time.sleep(0.5)
        return self.dev

    def __exit__(self, *exc_info):
        restore(self.dev)
        return False
