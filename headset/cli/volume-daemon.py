#!/usr/bin/env python3
import os
import sys
import subprocess
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from headset import device

def main():
    print("Volume daemon starting...")
    while True:
        try:
            dev_path = device.find_hidraw()
            print(f"Connected to {dev_path}")
            fd = os.open(dev_path, os.O_RDONLY)
            try:
                while True:
                    data = os.read(fd, 64)
                    if not data or data[0] != 0x0c:
                        continue
                    if len(data) >= 2:
                        val = data[1]
                        if val == 0x02:
                            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"])
                        elif val == 0x01:
                            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"])
            finally:
                os.close(fd)
        except RuntimeError:
            # Headset not found, wait and retry
            time.sleep(2)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
