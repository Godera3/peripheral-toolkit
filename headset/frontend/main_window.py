import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QSlider, QPushButton, QButtonGroup, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer
from theme import stylesheet, ACCENT, card, ColorPicker, MUTED
import backend

# Import Claude's state machine
from workers import (
    BatteryWorker, HidDongleWorker, BluezWatcher, 
    StatusResolver, State
)

class HeadsetWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Razer Barracuda X Chroma")
        self.setFixedWidth(520)
        
        self.config_file = os.path.expanduser("~/.config/barracuda-gui.json")
        self.last_volume = 80
        self.worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(14)

        # ── 1. Header ──────────────────────────────────────────────────
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(QLabel("BARRACUDA X CHROMA", objectName="Title"))
        
        self.status_label = QLabel("Checking...", objectName="Subtitle")
        self.status_label.setStyleSheet("color: #bdc3c7;")
        titles.addWidget(self.status_label)
        header.addLayout(titles)
        header.addStretch()
        
        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setFixedSize(28, 28)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet("background: transparent; border: 1px solid #313244; border-radius: 14px; color: white; font-weight: bold;")
        self.refresh_btn.clicked.connect(self.force_sync)
        header.addWidget(self.refresh_btn)

        self.batt_label = QLabel("--%", objectName="Badge")
        header.addWidget(self.batt_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(header)

        # ── 2. Audio EQ ────────────────────────────────────────────────
        eq_card, eq_layout = card("Audio EQ")
        eq_row = QHBoxLayout()
        eq_row.setSpacing(8)
        self.eq_group = QButtonGroup(self)
        
        eq_modes = ["Movie", "Music", "Custom", "Game"]
        for i, mode in enumerate(eq_modes):
            btn = QPushButton(mode, objectName="Effect", checkable=True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(34)
            self.eq_group.addButton(btn, i)
            eq_row.addWidget(btn)
            
        self.eq_group.button(0).setChecked(True)
        self.eq_group.idClicked.connect(self.on_eq_changed)
        eq_layout.addLayout(eq_row)
        root.addWidget(eq_card)

        # ── 3. Sidetone ────────────────────────────────────────────────
        st_card, st_layout = card("Echo Volume")
        
        st_header = QHBoxLayout()
        st_header.addWidget(QLabel("Sidetone / Mic Monitoring"))
        st_header.addStretch()
        self.st_val_label = QLabel("--%")
        self.st_val_label.setStyleSheet(f"color: {MUTED}; font-weight: bold;")
        st_header.addWidget(self.st_val_label)
        st_layout.addLayout(st_header)
        
        self.st_slider = QSlider(Qt.Orientation.Horizontal)
        self.st_slider.setRange(0, 100)
        self.st_slider.setValue(80)
        self.st_slider.valueChanged.connect(self.on_sidetone_slider)
        st_layout.addWidget(self.st_slider)
        
        self.st_status_label = QLabel("")
        self.st_status_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        st_layout.addWidget(self.st_status_label)
        
        smart_row = QHBoxLayout()
        smart_row.addWidget(QLabel("Smart Sidetone (Auto)"))
        smart_row.addStretch()
        self.smart_toggle = QCheckBox()
        self.smart_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.smart_toggle.toggled.connect(self.on_smart_toggle)
        smart_row.addWidget(self.smart_toggle)
        st_layout.addLayout(smart_row)
        
        root.addWidget(st_card)

        # ── 4. Chroma Lighting ─────────────────────────────────────────
        chroma_card, chroma_layout = card("Chroma Lighting")
        
        light_row = QHBoxLayout()
        light_row.addWidget(QLabel("Lighting"))
        light_row.addStretch()
        self.light_toggle = QCheckBox()
        self.light_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.light_toggle.toggled.connect(self.on_lights_toggled)
        light_row.addWidget(self.light_toggle)
        chroma_layout.addLayout(light_row)
        
        self.picker = ColorPicker("#00ff00")
        self.picker.colorChanged.connect(self.on_color_changed)
        chroma_layout.addWidget(self.picker)
        
        root.addWidget(chroma_card)
        root.addStretch()

        # ── 5. State Machine & Threads ─────────────────────────────────
        self.hid_worker = HidDongleWorker(self)
        self.bt_watcher = BluezWatcher("44:5E:CD:5A:EB:7A", "hci0", parent=self)
        self.resolver = StatusResolver(parent=self)

        # Connect hardware -> resolver
        self.hid_worker.node_present.connect(self.resolver.on_node)
        self.hid_worker.link_up.connect(self.resolver.on_link)
        self.bt_watcher.connected_changed.connect(self.resolver.on_bt)

        # Connect resolver -> UI
        self.resolver.state_changed.connect(self.on_state_changed)

        # Connect hardware live syncs -> UI
        self.hid_worker.eq_changed.connect(self.on_live_eq_changed)
        self.hid_worker.lights_changed.connect(self.on_live_lights_changed)

        # Start the worker thread
        self.hid_worker.start()

        # Initial Config Load
        self.sync_ui_state()

        # Poll battery every 60 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_battery)
        self.timer.start(60000)

    # ── State Management ───────────────────────────────────────────────
    def on_state_changed(self, state):
        if state == State.WIRELESS:
            self.status_label.setText("Connected · 2.4 GHz")
            self.status_label.setStyleSheet("color: #00ff00;")
            backend.set_default_sink("wireless")
            self.refresh_battery()
        elif state == State.BLUETOOTH:
            self.status_label.setText("Headset · Bluetooth Mode")
            self.status_label.setStyleSheet("color: #00ccff;")
            self.batt_label.setText("--%")
            self.batt_label.setStyleSheet("color: #888888; border-color: #888888;")
            # Wait 3 seconds for PipeWire to negotiate the Bluetooth audio sink
            QTimer.singleShot(3000, lambda: backend.set_default_sink("bluetooth"))
        elif state == State.OFF:
            self.status_label.setText("Disconnected · Headset Off")
            self.status_label.setStyleSheet("color: #888888;")
            self.batt_label.setText("--%")
            self.batt_label.setStyleSheet("color: #888888; border-color: #888888;")
        elif state == State.RESOLVING:
            self.status_label.setText("Checking…")
            self.status_label.setStyleSheet("color: #bdc3c7;")

    def on_live_eq_changed(self, mode):
        modes = ["movie", "music", "custom", "game"]
        if mode in modes:
            idx = modes.index(mode)
            self.eq_group.button(idx).setChecked(True)

    def on_live_lights_changed(self, is_on):
        self.light_toggle.blockSignals(True)
        self.light_toggle.setChecked(is_on)
        self.light_toggle.blockSignals(False)
        self.save_config()

    # ── Hardware Sync ──────────────────────────────────────────────────
    def refresh_battery(self):
        if self.resolver.state == State.WIRELESS:
            if self.worker is None or self.worker.isFinished():
                self.worker = BatteryWorker()
                self.worker.result.connect(self.update_battery_ui)
                self.worker.start()

    def update_battery_ui(self, level):
        if level < 0:
            self.batt_label.setText("--%")
            self.batt_label.setStyleSheet("color: #888888; border-color: #888888;")
        else:
            self.batt_label.setText(f"{level}%")
            color = "#ff5555" if level < 20 else "#fce94f" if level < 50 else ACCENT
            self.batt_label.setStyleSheet(f"color: {color}; border-color: {color};")

    def force_sync(self):
        self.sync_ui_state()
        self.refresh_battery()

    def sync_ui_state(self):
        try:
            # EQ
            current_eq = backend.get_eq()
            modes = ["movie", "music", "custom", "game"]
            if current_eq in modes:
                idx = modes.index(current_eq)
                self.eq_group.button(idx).setChecked(True)
        except Exception:
            pass

        # Load Config
        cfg = self.load_config()
        saved_vol = cfg.get("sidetone_vol", 80)
        if saved_vol == 0: saved_vol = 80
        self.last_volume = saved_vol
        saved_smart = cfg.get("smart_sidetone", True)
        
        self.st_slider.blockSignals(True)
        self.st_slider.setValue(saved_vol)
        self.st_slider.blockSignals(False)
        
        self.smart_toggle.blockSignals(True)
        self.smart_toggle.setChecked(saved_smart)
        self.smart_toggle.blockSignals(False)
        
        self.on_smart_toggle(saved_smart) # Apply the lock logic
        self.picker.set_color(cfg.get("color_hex", "#00ff00"))

    # ── UI Callbacks ───────────────────────────────────────────────────
    def on_eq_changed(self, idx):
        modes = ["movie", "music", "custom", "game"]
        backend.set_eq_mode(modes[idx])

    def on_sidetone_slider(self, val):
        if not self.smart_toggle.isChecked():
            return
        self.last_volume = val
        self.st_val_label.setText(f"{val}%")
        self.st_val_label.setStyleSheet(f"color: {ACCENT}; font-weight: bold;")
        backend.set_sidetone_volume(val)
        self.save_config()

    def on_smart_toggle(self, checked):
        self.st_slider.setEnabled(checked)
        if checked:
            self.st_status_label.setText("Managed by Smart Sidetone daemon")
            self.st_status_label.setStyleSheet(f"color: {ACCENT}; font-size: 11px;")
            self.st_val_label.setStyleSheet(f"color: {ACCENT}; font-weight: bold;")
            self.st_slider.setValue(self.last_volume)
            self.st_val_label.setText(f"{self.last_volume}%")
            backend.toggle_smart_sidetone(True)
            backend.set_sidetone_volume(self.last_volume)
        else:
            self.st_status_label.setText("Enable Smart Sidetone to adjust volume.")
            self.st_status_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
            self.st_val_label.setStyleSheet(f"color: {MUTED}; font-weight: bold;")
            self.st_slider.setValue(self.last_volume)
            self.st_val_label.setText(f"{self.last_volume}% (Muted)")
            backend.toggle_smart_sidetone(False)
            backend.set_sidetone_manual(False)
        self.save_config()

    def on_lights_toggled(self, checked):
        backend.set_lights(checked)
        self.save_config()

    def on_color_changed(self, hexc):
        backend.set_color(hexc)
        self.save_config()

    # ── Config ─────────────────────────────────────────────────────────
    def load_config(self):
        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except:
            return {}

    def save_config(self):
        cfg = {
            "sidetone_vol": self.last_volume,
            "smart_sidetone": self.smart_toggle.isChecked(),
            "lights_on": self.light_toggle.isChecked(),
            "color_hex": self.picker.current_color
        }
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(cfg, f)

    def closeEvent(self, e):
        self.hid_worker.requestInterruption()
        self.hid_worker.wait(2000)
        super().closeEvent(e)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(stylesheet(ACCENT))
    w = HeadsetWindow()
    w.show()
    sys.exit(app.exec())
