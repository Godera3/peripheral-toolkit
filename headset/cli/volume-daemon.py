#!/usr/bin/env python3
import os
import sys
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from headset import device

def main():
    try:
        dev_path = device.find_hidraw()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Volume daemon running on {dev_path}. (Ctrl+C to exit)")
    fd = os.open(dev_path, os.O_RDONLY)
    
    try:
        while True:
            data = os.read(fd, 64)
            if not data or data[0] != 0x0c:
                continue
            
            # Swapped based on physical hardware mapping
            if len(data) >= 2:
                val = data[1]
                if val == 0x02:
                    # Physically scroll up -> decrease
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"])
                elif val == 0x01:
                    # Physically scroll down -> increase
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"])
                    
    except KeyboardInterrupt:
        print("\nStopped volume daemon.")
    finally:
        os.close(fd)

if __name__ == "__main__":
    main()
