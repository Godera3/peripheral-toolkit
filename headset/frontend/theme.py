from PyQt6.QtWidgets import QWidget, QColorDialog, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtGui import QColor
from PyQt6.QtCore import pyqtSignal, Qt

# Razer Chroma Colors
ACCENT = "#00ff00"  # Neon Green
BG = "#181825"
CARD = "#1e1e2e"
TEXT = "#cdd6f4"
MUTED = "#a6adc8"

def stylesheet(accent):
    return f"""
    QWidget {{
        background-color: {BG};
        color: {TEXT};
        font-family: 'Inter', 'Barlow', sans-serif;
        font-size: 14px;
    }}
    QLabel#Title {{
        font-size: 20px;
        font-weight: bold;
        color: #ffffff;
    }}
    QLabel#Subtitle {{
        font-size: 12px;
        color: {MUTED};
    }}
    QLabel#Badge {{
        font-weight: bold;
        color: {accent};
        border: 1px solid {accent};
        border-radius: 10px;
        padding: 4px 10px;
    }}
    QWidget#Card {{
        background-color: {CARD};
        border-radius: 8px;
        border: 1px solid #313244;
    }}
    QPushButton#Effect {{
        background-color: transparent;
        border: 1px solid #313244;
        border-radius: 6px;
        color: {TEXT};
    }}
    QPushButton#Effect:hover {{
        background-color: #313244;
    }}
    QPushButton#Effect:checked {{
        border: 1px solid {accent};
        color: {accent};
        font-weight: bold;
    }}
    QSlider::groove:horizontal {{
        border: 1px solid #313244;
        height: 6px;
        background: #313244;
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {accent};
        width: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}
    """

def card(title, parent=None):
    from PyQt6.QtWidgets import QVBoxLayout
    w = QWidget(objectName="Card")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(15, 15, 15, 15)
    lay.setSpacing(10)
    lbl = QLabel(title.upper(), styleSheet=f"color: {MUTED}; font-weight: bold; font-size: 11px;")
    lay.addWidget(lbl)
    return w, lay

class ColorPicker(QWidget):
    colorChanged = pyqtSignal(str)
    
    def __init__(self, default_hex):
        super().__init__()
        self.current_color = default_hex
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 7 preset colors
        presets = ["#ff0000", "#ff8800", "#ffff00", "#00ff00", "#00ccff", "#8800ff", "#ffffff"]
        for c in presets:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"background-color: {c}; border-radius: 12px; border: 1px solid #111;")
            btn.clicked.connect(lambda checked, col=c: self.set_color(col))
            layout.addWidget(btn)
            
        layout.addStretch()
        
        self.hex_label = QLabel(default_hex.upper())
        self.hex_label.setStyleSheet("background: #111; padding: 5px; border-radius: 4px; font-family: monospace;")
        layout.addWidget(self.hex_label)
        
        self.btn_custom = QPushButton("Pick")
        self.btn_custom.setFixedSize(50, 26)
        self.btn_custom.clicked.connect(self.open_picker)
        layout.addWidget(self.btn_custom)

    def set_color(self, hexc):
        self.current_color = hexc
        self.hex_label.setText(hexc.upper())
        self.colorChanged.emit(hexc)

    def open_picker(self):
        c = QColorDialog.getColor(QColor(self.current_color), self, "Select Color")
        if c.isValid():
            self.set_color(c.name())
