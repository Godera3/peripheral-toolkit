#!/usr/bin/env python3
"""Watch the Razer Barracuda X Chroma dongle (1532:0574) for its firmware mute button.
Prints 'HEADSET_MUTE 0|1' to stdout on every change. Report format (64 bytes):
b0=0x02, b1=0x0a, b13 = 1 muted / 0 unmuted."""
import glob, os, select, sys, time

VIDPID = "00001532:00000574"

def log(msg):
    print(f"mute-watcher: {msg}", file=sys.stderr, flush=True)

def emit(state):
    print(f"HEADSET_MUTE {state}", flush=True)

def find_node():
    for p in glob.glob("/sys/class/hidraw/hidraw*/device/uevent"):
        try:
            if VIDPID in open(p).read():
                return "/dev/" + p.split("/")[4]
        except OSError:
            pass
    return None

last = None
while True:
    node = find_node()
    if not node:
        time.sleep(2)
        continue
    try:
        fd = os.open(node, os.O_RDONLY)
    except OSError as e:
        log(f"cannot open {node}: {e}")
        time.sleep(2)
        continue
    log(f"watching {node}")
    try:
        while True:
            select.select([fd], [], [])
            d = os.read(fd, 64)
            if len(d) >= 14 and d[0] == 0x02 and d[1] == 0x0a:
                state = 1 if d[13] == 1 else 0
                if state != last:
                    last = state
                    emit(state)
    except OSError as e:
        log(f"lost {node}: {e}")
    finally:
        os.close(fd)
        if last != 0:
            last = 0
            emit(0)
    time.sleep(1)
