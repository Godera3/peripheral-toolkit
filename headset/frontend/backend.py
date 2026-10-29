import sys
import os
import subprocess

# Ensure we can import the core module from the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from headset import core

def get_battery() -> int:
    try:
        return core.get_battery()
    except Exception:
        return -1

def set_eq_mode(mode: str):
    """mode: 'game', 'music', 'movie', 'custom'"""
    try:
        core.set_eq(mode)
    except Exception as e:
        print(f"Error setting EQ: {e}")

def set_sidetone_volume(percent: int):
    try:
        core.set_sidetone_volume(percent)
    except Exception as e:
        print(f"Error setting sidetone volume: {e}")

def set_sidetone_manual(on: bool):
    try:
        core.set_sidetone(on)
    except Exception as e:
        print(f"Error toggling sidetone: {e}")

def set_lights(on: bool):
    try:
        if on:
            core.set_lights_on()
        else:
            core.set_lights_off()
    except Exception as e:
        print(f"Error toggling lights: {e}")

def set_color(hex_color: str):
    try:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        core.set_color(r, g, b)
    except Exception as e:
        print(f"Error setting color: {e}")

def toggle_smart_sidetone(on: bool):
    """Starts or stops the systemd background daemon."""
    action = "start" if on else "stop"
    try:
        subprocess.run(["systemctl", "--user", action, "barracuda-sidetone.service"], check=True)
    except Exception as e:
        print(f"Failed to toggle smart sidetone daemon: {e}")

def get_smart_sidetone_status() -> bool:
    """Checks if the systemd background daemon is currently running."""
    try:
        res = subprocess.run(["systemctl", "--user", "is-active", "barracuda-sidetone.service"], capture_output=True, text=True)
        return res.stdout.strip() == "active"
    except Exception:
        return False

def get_lights_state() -> bool:
    try:
        return core.get_lights_state()
    except Exception:
        return False

def get_eq() -> str:
    try:
        val = core.get_eq()
        modes = {0x07: "game", 0x08: "music", 0x09: "movie", 0xFF: "custom"}
        return modes.get(val, "game")
    except Exception:
        return "game"

def get_sidetone_volume() -> int:
    try:
        val = core.get_sidetone_volume()
        if val >= 0:
            return round((val / 15.0) * 100)
        return 0
    except Exception:
        return 0

def get_link_state() -> int:
    try:
        return core.get_link_state()
    except Exception:
        return 1

def is_bluetooth_connected() -> bool:
    """Checks if the headset is connected via PipeWire/Bluetooth."""
    try:
        # pactl lists all audio sinks. If the Barracuda is on BT, it will be listed here.
        res = subprocess.run(["pactl", "list", "sinks", "short"], capture_output=True, text=True)
        return "bluez_output" in res.stdout.lower()
    except Exception:
        return False

def set_default_sink(device_type: str):
    """Automatically switches audio between the 2.4GHz dongle and Bluetooth."""
    try:
        if device_type == "bluetooth":
            # 1. First, force the Bluetooth card to the high-quality A2DP profile
            cards = subprocess.run(["pactl", "list", "cards", "short"], capture_output=True, text=True).stdout
            for card in cards.splitlines():
                if "bluez" in card:
                    card_id = card.split()[0]
                    subprocess.run(["pactl", "set-card-profile", card_id, "a2dp-sink"])
                    break
            
        # 2. Find the correct sink
        res = subprocess.run(["pactl", "list", "sinks", "short"], capture_output=True, text=True)
        sinks = res.stdout.splitlines()
        
        target_sink = None
        for sink in sinks:
            if device_type == "bluetooth" and "bluez_output" in sink:
                target_sink = sink.split()[1]
                break
            elif device_type == "wireless" and "alsa_output.usb-MediaTek_Inc_Razer" in sink:
                target_sink = sink.split()[1]
                break
                
        if target_sink:
            # Set as default
            subprocess.run(["pactl", "set-default-sink", target_sink])
            # Move all currently playing streams
            streams = subprocess.run(["pactl", "list", "short", "sink-inputs"], capture_output=True, text=True)
            for stream in streams.stdout.splitlines():
                stream_id = stream.split()[0]
                subprocess.run(["pactl", "move-sink-input", stream_id, target_sink])
            print(f"Audio automatically routed to: {target_sink}")
        else:
            print(f"Could not find sink for {device_type}")
    except Exception as e:
        print(f"Failed to switch audio sink: {e}")
