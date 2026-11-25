#!/usr/bin/env python3
"""Read or set DPI on the G Pro X 2 SE through HID++ 0x2202.

Run with pkexec and an absolute path. Writes switch the mouse to host mode
first, because onboard mode answers DPI writes with Busy. The original mode
is restored even if the write fails.
"""
import argparse
import os
import select
import time

HIDRAW = os.environ.get("HIDRAW", "/dev/hidraw3")
DEVICE_INDEX = 1
SW_ID = 1
ROOT = 0x0000
DPI_FEATURE = 0x09
MODE_FEATURE = 0x0D
ONBOARD_MODE = 1
HOST_MODE = 2


def drain(fd):
    while True:
        ready, _, _ = select.select([fd], [], [], 0)
        if not ready:
            return
        try:
            os.read(fd, 64)
        except OSError:
            return


def request(fd, feature, function, params=(0, 0, 0), length=16):
    """Send one HID++ request and return the first reply for it."""
    header = bytes([0x11, DEVICE_INDEX, feature, (function << 4) | SW_ID])
    packet = header + bytes(params[:length]) + bytes(length - len(params[:length]))
    for _ in range(3):
        drain(fd)
        os.write(fd, packet)
        deadline = time.monotonic() + 1.2
        while time.monotonic() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.15)
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


def read_params(fd):
    reply = request(fd, DPI_FEATURE, 5)
    if not reply:
        raise RuntimeError("no DPI parameters reply")
    return {
        "sensor": reply[4],
        "dpi_x": int.from_bytes(reply[5:7], "big"),
        "default_x": int.from_bytes(reply[7:9], "big"),
        "dpi_y": int.from_bytes(reply[9:11], "big"),
        "default_y": int.from_bytes(reply[11:13], "big"),
        "lod": reply[13],
    }


def read_mode(fd):
    reply = request(fd, MODE_FEATURE, 2)
    return reply[4] if reply else None


def set_mode(fd, value):
    return request(fd, MODE_FEATURE, 1, (value, 0, 0)) is not None


def set_dpi(fd, dpi, lod):
    high, low = (dpi >> 8) & 0xFF, dpi & 0xFF
    return request(fd, DPI_FEATURE, 6, (0, high, low, high, low, lod))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", type=int, metavar="DPI", help="new X/Y DPI")
    parser.add_argument("--lod", type=int, default=None, choices=(1, 2, 3))
    args = parser.parse_args()

    fd = os.open(HIDRAW, os.O_RDWR | os.O_NONBLOCK)
    try:
        before = read_params(fd)
        mode = read_mode(fd)
        print(f"before: X={before['dpi_x']} Y={before['dpi_y']} LOD={before['lod']} mode={mode}")
        if args.set is None:
            return

        lod = args.lod if args.lod is not None else before["lod"]
        try:
            if mode == ONBOARD_MODE and not set_mode(fd, HOST_MODE):
                raise RuntimeError("could not enter host mode")
            reply = set_dpi(fd, args.set, lod)
            if not reply:
                raise RuntimeError("DPI write refused")
            after = read_params(fd)
            if after["dpi_x"] != args.set:
                raise RuntimeError(f"DPI read back {after['dpi_x']}, expected {args.set}")
            print(f"after: X={after['dpi_x']} Y={after['dpi_y']} LOD={after['lod']}")
        finally:
            if mode is not None and read_mode(fd) != mode:
                set_mode(fd, mode)
            print(f"mode restored to {read_mode(fd)}")
    finally:
        os.close(fd)


if __name__ == "__main__":
    main()
