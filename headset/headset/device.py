"""
device.py
=========
Raw hidraw and input event access for the Barracuda X Chroma.
"""
import os, glob, fcntl

def find_hidraw() -> str:
    for path in glob.glob("/sys/class/hidraw/hidraw*/device/uevent"):
        try:
            with open(path) as f:
                if "0003:00001532:00000574" in f.read():
                    return "/dev/" + path.split("/")[-3]
        except OSError:
            continue
    raise RuntimeError("Razer Barracuda X Chroma hidraw node not found.")

def find_input_event() -> str:
    """Finds the event node for the headset's Consumer Control (Volume Wheel)."""
    for path in glob.glob("/sys/class/input/event*/device/uevent"):
        try:
            with open(path) as f:
                content = f.read()
                # Match the Vendor/Product, and ensure it's the Consumer Control
                if "PRODUCT=3/1532/574/110" in content and "Consumer Control" in content:
                    dev_name = path.split("/")[-3]
                    return f"/dev/input/{dev_name}"
        except OSError:
            continue
    raise RuntimeError("Barracuda Consumer Control input event not found.")

def send_output(dev_path: str, payload: bytes):
    fd = os.open(dev_path, os.O_RDWR)
    try:
        written = os.write(fd, payload)
        if written != 64:
            raise IOError(f"Short write: only {written} bytes sent")
    finally:
        os.close(fd)

def get_feature(dev_path: str, report_id: int, size: int = 64) -> bytes:
    req = (3 << 30) | (size << 16) | (ord('H') << 8) | 0x07
    fd = os.open(dev_path, os.O_RDWR)
    buf = bytearray(size)
    buf[0] = report_id
    try:
        fcntl.ioctl(fd, req, buf)
        return bytes(buf)
    finally:
        os.close(fd)
