#!/usr/bin/env python3
import os
import sys
import time
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from headset import core, device

def is_mic_in_use():
    try:
        result = subprocess.run(["pactl", "list", "source-outputs"], capture_output=True, text=True)
        if not result.stdout:
            return False
        for stream in result.stdout.split("Source Output #")[1:]:
            if 'application.name = "cinnamon"' in stream or 'media.name = "Peak detect"' in stream:
                continue
            return True
        return False
    except Exception:
        return False

def main():
    print("Event-Driven Sidetone daemon starting...")
    
    try:
        core.set_sidetone_volume(80)
        core.set_sidetone(False)
    except:
        pass
        
    current_state = False
    
    while True:
        try:
            # The magic fix: stdbuf -oL forces line-buffering so we get events instantly
            p = subprocess.Popen(["stdbuf", "-oL", "pactl", "subscribe"], stdout=subprocess.PIPE, text=True)
            print("Listening for audio events...")
            
            # Check initial state immediately
            active = is_mic_in_use()
            if active and not current_state:
                core.set_sidetone(True)
                current_state = True
                print("-> Turning Sidetone ON.")
            
            for line in p.stdout:
                # Debug print so you can see it working!
                print(f"[DEBUG] Event: {line.strip()}")
                
                if "source-output" in line:
                    active = is_mic_in_use()
                    
                    if active and not current_state:
                        print("-> Turning Sidetone ON.")
                        core.set_sidetone(True)
                        current_state = True
                    elif not active and current_state:
                        print("-> Turning Sidetone OFF.")
                        core.set_sidetone(False)
                        current_state = False

        except RuntimeError:
            current_state = False
            time.sleep(2)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
