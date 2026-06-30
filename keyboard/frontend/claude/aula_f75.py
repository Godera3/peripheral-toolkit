#!/usr/bin/env python3
"""
aula_f75.py
===========
Entry point. Run with: python3 aula_f75.py
"""
import sys

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from main_window import MainWindow
from theme import STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("AULA F75 Control")
    app.setDesktopFileName("aula-f75")
    app.setStyleSheet(STYLESHEET)
    app.setFont(QFont("Inter", 10))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
