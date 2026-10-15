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


class WirelessNotFound(DeviceNotFound):
    """Wireless AULA dongle not found."""


class WiredNotFound(DeviceNotFound):
    """Wired AULA keyboard not found."""


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

    if kind == "wireless":
        raise WirelessNotFound("Wireless AULA dongle not found.")
    if kind == "wired":
        raise WiredNotFound("Wired AULA keyboard not found.")
    raise DeviceNotFound("AULA keyboard not found.")


def restore(dev) -> None:
    """Hand the vendor interface back to usbhid, best-effort.

    After control transfers, the handle may be busy - attempting to reattach on
    the same handle can fail with EBUSY. To reliably rebind, dispose the handle
    first, then acquire a fresh one and try to attach.

    Unprivileged callers cannot force a rebind if libusb's reattach fails:
    the sysfs fallback requires write access to /sys/bus/usb/drivers/usbhid/bind.
    Failures here are swallowed on purpose — `Session.__exit__` must not mask
    the original exception from the `with` block.
    """
    try:
        port_str = ".".join(str(p) for p in dev.port_numbers)
        bus = dev.bus
        vid = dev.idVendor
        pid = dev.idProduct
    except Exception:
        port_str, bus, vid, pid = None, None, None, None

    # Dispose current handle first (releases claim)
    try:
        usb.util.dispose_resources(dev)
    except Exception:
        pass

    attached = False
    if vid is not None and pid is not None:
        try:
            dev2 = usb.core.find(idVendor=vid, idProduct=pid)
            if dev2 is not None:
                try:
                    dev2.attach_kernel_driver(VENDOR_IFACE)
                    attached = True
                except usb.core.USBError:
                    pass
                try:
                    usb.util.dispose_resources(dev2)
                except Exception:
                    pass
        except Exception:
            pass

    if attached or port_str is None:
        return

    # Best-effort sysfs fallback. Only succeeds if the caller has write access
    # to usbhid's bind file — normally root, or a custom udev rule.
    sysfs = "/sys/bus/usb/drivers/usbhid"
    for intf in (f"{bus}-{port_str}:1.1", f"{bus}-{port_str}:1.0"):
        try:
            with open(f"{sysfs}/bind", "w") as fh:
                fh.write(intf)
            return
        except OSError:
            continue


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
        except usb.core.USBError as exc:
            raise DeviceBusy(
                f"could not detach usbhid from interface {VENDOR_IFACE}: {exc}"
            ) from exc
        time.sleep(0.5)
        return self.dev

    def __exit__(self, *exc_info):
        restore(self.dev)
        return False
