from PyQt6.QtCore import QThread, pyqtSignal
from backend import get_battery
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from headset import device

class BatteryWorker(QThread):
    result = pyqtSignal(int)
    def run(self):
        self.result.emit(get_battery())

class HardwareListener(QThread):
    eq_changed = pyqtSignal(str)
    lights_changed = pyqtSignal(bool)

    def run(self):
        fd = None
        while True:
            try:
                if fd is None:
                    dev = device.find_hidraw()
                    fd = os.open(dev, os.O_RDONLY)
                
                data = os.read(fd, 64)
                if not data or data[0] != 0x02: 
                    continue
                
                # Check for EQ change (0x13)
                if len(data) >= 14 and data[10] == 0x13:
                    val = data[13]
                    modes = {0x07: "game", 0x08: "music", 0x09: "movie", 0xFF: "custom"}
                    mode = modes.get(val, "game")
                    self.eq_changed.emit(mode)
                    
                # Check for Lighting change (0x40)
                elif len(data) >= 14 and data[10] == 0x40:
                    is_on = (data[13] != 0x00)
                    self.lights_changed.emit(is_on)
            except Exception:
                if fd is not None:
                    try: os.close(fd)
                    except Exception: pass
                    fd = None
                time.sleep(2) # Wait 2 seconds before trying to reconnect
