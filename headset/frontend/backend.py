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
