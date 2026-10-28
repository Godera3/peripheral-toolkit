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
from workers import BatteryWorker, HardwareListener

class HeadsetWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Razer Barracuda X Chroma")
        self.setFixedWidth(520)
        
        self.config_file = os.path.expanduser("~/.config/barracuda-gui.json")
        self.last_volume = 80

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(14)

        # ── 1. Header ──────────────────────────────────────────────────
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.addWidget(QLabel("BARRACUDA X CHROMA", objectName="Title"))
        titles.addWidget(QLabel("Connected · 2.4 GHz dongle", objectName="Subtitle"))
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
        self.st_slider.setValue(0)
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

        # ── 5. Timers & Initialization ─────────────────────────────────
        self.worker = None
        
        self.listener = HardwareListener()
        self.listener.eq_changed.connect(self.on_live_eq_changed)
        self.listener.lights_changed.connect(self.on_live_lights_changed)
        self.listener.start()

        # Delay the initial hardware sync to let the dongle wake up
        QTimer.singleShot(500, self.sync_initial_state)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_all_state)
        self.timer.start(60000)
        self.refresh_all_state()

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

    def sync_initial_state(self):
        cfg = self.load_config()
        saved_vol = cfg.get("sidetone_vol", 80)
        if saved_vol == 0: saved_vol = 80
        self.last_volume = saved_vol

        # EQ
        current_eq = backend.get_eq()
        modes = ["movie", "music", "custom", "game"]
        if current_eq in modes:
            idx = modes.index(current_eq)
            self.eq_group.button(idx).setChecked(True)
            
        # Hardware Source of Truth for Sidetone
        daemon_active = backend.get_smart_sidetone_status()
        
        self.smart_toggle.blockSignals(True)
        self.smart_toggle.setChecked(daemon_active)
        self.smart_toggle.blockSignals(False)
        
        self.st_slider.blockSignals(True)
        self.st_slider.setValue(self.last_volume)
        self.st_slider.blockSignals(False)
        
        if daemon_active:
            self.st_slider.setEnabled(True)
            self.st_status_label.setText("Managed by Smart Sidetone daemon")
            self.st_val_label.setStyleSheet(f"color: {ACCENT}; font-weight: bold;")
            self.st_val_label.setText(f"{self.last_volume}%")
            backend.set_sidetone_volume(self.last_volume)
        else:
            self.st_slider.setEnabled(False)
            backend.set_sidetone_manual(False)
            self.st_status_label.setText("Enable Smart Sidetone to adjust volume.")
            self.st_val_label.setStyleSheet(f"color: {MUTED}; font-weight: bold;")
            self.st_val_label.setText(f"{self.last_volume}% (Muted)")
        
        # Lights
        self.light_toggle.blockSignals(True)
        self.light_toggle.setChecked(backend.get_lights_state())
        self.light_toggle.blockSignals(False)
        
        self.picker.set_color(cfg.get("color_hex", "#00ff00"))
    def force_sync(self):
        self.sync_initial_state()
        self.refresh_all_state()

    def refresh_all_state(self):
        if self.worker is None or self.worker.isFinished():
            self.worker = BatteryWorker()
            self.worker.result.connect(self.update_battery_ui)
            self.worker.start()
            
        actual_lights = backend.get_lights_state()
        if self.light_toggle.isChecked() != actual_lights:
            self.light_toggle.blockSignals(True)
            self.light_toggle.setChecked(actual_lights)
            self.light_toggle.blockSignals(False)

    def update_battery_ui(self, level):
        if level < 0:
            self.batt_label.setText("--%")
            self.batt_label.setStyleSheet("color: #888888; border-color: #888888;")
        else:
            self.batt_label.setText(f"{level}%")
            color = "#ff5555" if level < 20 else "#fce94f" if level < 50 else ACCENT
            self.batt_label.setStyleSheet(f"color: {color}; border-color: {color};")

    def on_live_lights_changed(self, is_on):
        # Block signals so we don't send a USB command back to the headset
        self.light_toggle.blockSignals(True)
        self.light_toggle.setChecked(is_on)
        self.light_toggle.blockSignals(False)
        self.save_config()

    def on_live_eq_changed(self, mode):
        modes = ["movie", "music", "custom", "game"]
        if mode in modes:
            idx = modes.index(mode)
            self.eq_group.button(idx).setChecked(True)

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
        backend.toggle_smart_sidetone(checked)
        self.st_slider.setEnabled(checked)
        
        if checked:
            backend.set_sidetone_manual(False)
            self.st_status_label.setText("Managed by Smart Sidetone daemon")
            self.st_status_label.setStyleSheet(f"color: {ACCENT}; font-size: 11px;")
            self.st_val_label.setStyleSheet(f"color: {ACCENT}; font-weight: bold;")
            self.st_slider.setValue(self.last_volume)
            self.st_val_label.setText(f"{self.last_volume}%")
            backend.set_sidetone_volume(self.last_volume)
        else:
            backend.set_sidetone_manual(False)
            self.st_status_label.setText("Enable Smart Sidetone to adjust volume.")
            self.st_status_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
            self.st_val_label.setStyleSheet(f"color: {MUTED}; font-weight: bold;")
            self.st_slider.setValue(self.last_volume)
            self.st_val_label.setText(f"{self.last_volume}% (Muted)")
            
        self.save_config()

    def on_lights_toggled(self, checked):
        backend.set_lights(checked)
        self.save_config()

    def on_color_changed(self, hexc):
        backend.set_color(hexc)
        self.save_config()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(stylesheet(ACCENT))
    w = HeadsetWindow()
    w.show()
    sys.exit(app.exec())
