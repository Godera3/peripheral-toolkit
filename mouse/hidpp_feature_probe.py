#!/usr/bin/env python3
"""Read-only HID++ 2.0 discovery for the G Pro X 2 SE receiver.

Run with `pkexec python3 mouse/hidpp_feature_probe.py`. The Logitech receiver
exposes its paired device on /dev/hidraw3 here; set HIDRAW if that changes.
Nothing in this script writes device settings.
"""
import os
import select
import sys
import time

HIDRAW = os.environ.get("HIDRAW", "/dev/hidraw3")
DEVICE_INDEX = 1
SW_ID = 1

KNOWN = {
    0x0000: "ROOT", 0x0001: "FEATURE_SET", 0x0003: "DEVICE_INFO",
    0x0005: "DEVICE_NAME", 0x0020: "configChange",
    0x1004: "unifiedBattery", 0x1500: "unknown", 0x1602: "unknown",
    0x1801: "unknown", 0x1802: "deviceReset", 0x1803: "unknown",
    0x1805: "oobState", 0x1806: "configDeviceProps", 0x1817: "unknown",
    0x1830: "unknown", 0x1861: "unknown", 0x1875: "unknown",
    0x1890: "unknown", 0x18A1: "unknown", 0x1D4B: "wirelessDeviceStatus",
    0x1E00: "unknown", 0x1E02: "unknown", 0x1E22: "unknown",
    0x1EB0: "unknown", 0x2202: "extendedAdjustableDpi",
    0x2250: "xyStats", 0x2251: "wheelStats", 0x8061: "extendedReportRate",
    0x8090: "modeStatus", 0x80E0: "unknown", 0x8100: "onboardProfiles",
    0x8110: "mouseButtonFilter",
}


def drain(fd):
    while True:
        ready, _, _ = select.select([fd], [], [], 0)
        if not ready:
            return
        try:
            os.read(fd, 64)
        except OSError:
            return


def request(fd, feature, function, params=(0, 0, 0), long_report=False):
    """Send one HID++ short or long request and return the matching reply."""
    report = 0x11 if long_report else 0x10
    header = bytes([report, DEVICE_INDEX, feature, (function << 4) | SW_ID])
    packet = header + bytes(params) + bytes(16 - len(params))
    for _ in range(3):
        drain(fd)
        os.write(fd, packet)
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.12)
            if not ready:
                continue
            try:
                reply = os.read(fd, 64)
            except OSError:
                continue
            if reply[:4] == header:
                return reply
        time.sleep(0.05)
    return None


def main():
    fd = os.open(HIDRAW, os.O_RDWR | os.O_NONBLOCK)
    try:
        drain(fd)
        count_reply = request(fd, 1, 0)
        if not count_reply:
            sys.exit(f"no FEATURE_SET reply on {HIDRAW}")
        count = count_reply[4]
        print(f"FEATURE_SET: {count} features")
        for index in range(count):
            reply = request(fd, 1, 1, (index, 0, 0))
            if not reply:
                print(f"  [{index:02d}] no reply")
                continue
            feature = (reply[4] << 8) | reply[5]
            print(f"  [{index:02d}] 0x{feature:04x} {KNOWN.get(feature, '')}")

        print("\nSafe reads:")
        for label, feature, function, params, long_report in (
            ("battery level", 6, 1, (0, 0, 0), False),
            ("DPI X range", 9, 2, (0, 0, 0), True),
            ("DPI presets", 9, 3, (0, 0, 0), True),
            ("current DPI", 9, 5, (0, 0, 0), True),
        ):
            reply = request(fd, feature, function, params, long_report)
            print(f"  {label}: {reply.hex() if reply else 'no reply'}")
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
