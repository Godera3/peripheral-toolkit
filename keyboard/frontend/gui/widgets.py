"""
widgets.py
==========
Custom widgets. The one worth real attention is EffectSwatch: a small
live-rendered preview, driven by each effect's `anim` tag from effects.py,
so "Rainbow" actually cycles hue, "Respire" actually breathes, "Raindrops"
actually sparkles at random — rather than every effect getting the same
static colored square. This is the one signature element in the app; it
stays restrained everywhere else.

ToggleSwitch is a small custom-painted on/off control, since QCheckBox
reads as a form element and sleep mode reads more like a physical switch.
"""
from __future__ import annotations

import math
import random

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from theme import HAIRLINE, INK_FAINT, PANEL, SIGNAL

# A small, fixed hue wheel used by hue-cycle / hue-sweep / rainbow-flavored
# effects, so they don't all just reduce to "shifting rainbow #1".
_RAINBOW_STOPS = [
    QColor(255, 87, 87),
    QColor(255, 184, 77),
    QColor(255, 240, 92),
    QColor(110, 231, 138),
    QColor(94, 230, 168),
    QColor(94, 184, 230),
    QColor(151, 110, 230),
    QColor(230, 94, 168),
]


def _lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
    return QColor(
        int(c1.red() + (c2.red() - c1.red()) * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue() + (c2.blue() - c1.blue()) * t),
    )


def _rainbow_at(phase: float) -> QColor:
    """phase in [0, 1) -> interpolated color around the stop wheel."""
    phase = phase % 1.0
    n = len(_RAINBOW_STOPS)
    pos = phase * n
    i = int(pos) % n
    t = pos - int(pos)
    return _lerp_color(_RAINBOW_STOPS[i], _RAINBOW_STOPS[(i + 1) % n], t)


class EffectSwatch(QWidget):
    """
    Small fixed-size canvas (default 56x32) that renders a continuous
    preview loop matching the given anim style. Pure QPainter — no images,
    so it stays crisp at any DPI and costs almost nothing to animate.
    """

    FRAME_MS = 60  # ~16fps; plenty smooth for a thumbnail, easy on CPU

    def __init__(self, anim: str, base_hue: float = 0.42, parent=None):
        super().__init__(parent)
        self._anim = anim
        self._base_hue = base_hue  # used by single-hue effects (respire, solid)
        self._t = 0.0
        self._sparkles: list[tuple[float, float, float]] = []  # x, y, life
        self.setFixedSize(56, 32)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self.FRAME_MS)

    def _tick(self) -> None:
        self._t += self.FRAME_MS / 1000.0
        if self._anim in ("sparkle-random", "sparkle-soft"):
            self._maybe_spawn_sparkle()
            self._sparkles = [
                (x, y, life - self.FRAME_MS / 1000.0)
                for (x, y, life) in self._sparkles
                if life - self.FRAME_MS / 1000.0 > 0
            ]
        self.update()

    def _maybe_spawn_sparkle(self) -> None:
        spawn_chance = 0.35 if self._anim == "sparkle-random" else 0.12
        if random.random() < spawn_chance and len(self._sparkles) < 6:
            w, h = self.width(), self.height()
            self._sparkles.append(
                (random.uniform(4, w - 4), random.uniform(4, h - 4), 0.7)
            )

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, self.width(), self.height())

        painter.setPen(QPen(QColor(HAIRLINE), 1))
        painter.setBrush(QColor(PANEL))
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)

        method = getattr(self, f"_paint_{self._anim.replace('-', '_')}", None)
        if method is not None:
            method(painter, rect)
        else:
            self._paint_solid(painter, rect)

        painter.end()

    # --- individual animation styles -------------------------------------

    def _paint_off(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(QColor(INK_FAINT), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        cx, cy = rect.center().x(), rect.center().y()
        painter.drawEllipse(QPointF(cx, cy), 3, 3)

    def _paint_solid(self, painter: QPainter, rect: QRectF) -> None:
        color = QColor.fromHslF(self._base_hue, 0.75, 0.55)
        self._fill_inset(painter, rect, color)

    def _paint_breathe(self, painter: QPainter, rect: QRectF) -> None:
        brightness = 0.35 + 0.35 * (0.5 + 0.5 * math.sin(self._t * 1.6))
        color = QColor.fromHslF(self._base_hue, 0.75, brightness)
        self._fill_inset(painter, rect, color)

    def _paint_hue_cycle(self, painter: QPainter, rect: QRectF) -> None:
        color = _rainbow_at(self._t * 0.18)
        self._fill_inset(painter, rect, color)

    def _paint_hue_sweep(self, painter: QPainter, rect: QRectF) -> None:
        inset = rect.adjusted(3, 3, -3, -3)
        steps = 7
        seg_w = inset.width() / steps
        for i in range(steps):
            color = _rainbow_at(self._t * 0.25 + i / steps)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(
                QRectF(inset.left() + i * seg_w, inset.top(), seg_w + 0.5, inset.height())
            )

    def _paint_flash(self, painter: QPainter, rect: QRectF) -> None:
        on = (self._t % 0.6) < 0.18
        color = QColor.fromHslF(self._base_hue, 0.8, 0.55 if on else 0.16)
        self._fill_inset(painter, rect, color)

    def _paint_wave(self, painter: QPainter, rect: QRectF) -> None:
        inset = rect.adjusted(3, 3, -3, -3)
        n = 10
        for i in range(n):
            xt = i / (n - 1)
            x = inset.left() + xt * inset.width()
            brightness = 0.25 + 0.4 * (0.5 + 0.5 * math.sin(self._t * 2.2 + xt * 6.0))
            color = QColor.fromHslF(self._base_hue, 0.75, brightness)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            r = 2.6
            painter.drawEllipse(QPointF(x, inset.center().y()), r, r)

    def _paint_chase(self, painter: QPainter, rect: QRectF) -> None:
        inset = rect.adjusted(3, 3, -3, -3)
        n = 8
        head = (self._t * 4.0) % n
        for i in range(n):
            dist = (head - i) % n
            fade = max(0.0, 1.0 - dist / 3.0)
            if fade <= 0.02:
                continue
            x = inset.left() + (i / (n - 1)) * inset.width()
            color = QColor.fromHslF(self._base_hue, 0.8, 0.18 + 0.42 * fade)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, inset.center().y()), 2.4, 2.4)

    def _paint_stream(self, painter: QPainter, rect: QRectF) -> None:
        inset = rect.adjusted(3, 3, -3, -3)
        n = 9
        offset = (self._t * 0.3) % 1.0
        for i in range(n):
            xt = (i / n + offset) % 1.0
            x = inset.left() + xt * inset.width()
            color = _rainbow_at(xt + self._t * 0.05)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, inset.center().y()), 2.2, 2.2)

    def _paint_spin(self, painter: QPainter, rect: QRectF) -> None:
        cx, cy = rect.center().x(), rect.center().y()
        radius = min(rect.width(), rect.height()) / 2 - 5
        blades = 4
        for b in range(blades):
            angle = self._t * 2.4 + (b / blades) * 2 * math.pi
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle) * 0.7
            color = _rainbow_at(b / blades + self._t * 0.1)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, y), 3.0, 3.0)

    def _paint_ripple(self, painter: QPainter, rect: QRectF) -> None:
        cx, cy = rect.center().x(), rect.center().y()
        max_r = min(rect.width(), rect.height()) / 2 - 2
        for i in range(2):
            phase = (self._t * 0.6 + i * 0.5) % 1.0
            r = phase * max_r
            alpha = max(0, int(180 * (1 - phase)))
            color = QColor.fromHslF(self._base_hue, 0.7, 0.55)
            color.setAlpha(alpha)
            painter.setPen(QPen(color, 1.4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), r, r)

    def _paint_bloom(self, painter: QPainter, rect: QRectF) -> None:
        cx, cy = rect.center().x(), rect.center().y()
        phase = (self._t * 0.45) % 1.0
        scale = 0.3 + 0.7 * (0.5 - 0.5 * math.cos(phase * 2 * math.pi))
        petals = 5
        r = (min(rect.width(), rect.height()) / 2 - 4) * scale
        for p in range(petals):
            angle = (p / petals) * 2 * math.pi
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            color = _rainbow_at(p / petals + 0.3)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(x, y), 2.6, 2.6)

    def _paint_sparkle_random(self, painter: QPainter, rect: QRectF) -> None:
        self._draw_sparkles(painter)

    def _paint_sparkle_soft(self, painter: QPainter, rect: QRectF) -> None:
        self._draw_sparkles(painter, soft=True)

    def _draw_sparkles(self, painter: QPainter, soft: bool = False) -> None:
        for x, y, life in self._sparkles:
            t = max(0.0, min(1.0, life / 0.7))
            alpha = int(220 * t)
            color = QColor.fromHslF(self._base_hue if soft else random.random(), 0.7, 0.7)
            color.setAlpha(alpha)
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            size = 2.0 + 1.2 * t
            painter.drawEllipse(QPointF(x, y), size, size)

    # --- shared helpers -----------------------------------------------------

    @staticmethod
    def _fill_inset(painter: QPainter, rect: QRectF, color: QColor) -> None:
        inset = rect.adjusted(3, 3, -3, -3)
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(inset, 4, 4)

    def stop(self) -> None:
        """Call when removing/hiding the widget to free the QTimer cleanly."""
        self._timer.stop()


class ToggleSwitch(QWidget):
    """Small custom on/off switch — sleep mode reads as a physical toggle,
    not a checkbox in a form."""

    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:  # noqa: N802 (Qt-style accessor)
        return self._checked

    def setChecked(self, value: bool) -> None:  # noqa: N802
        if value != self._checked:
            self._checked = value
            self.update()
            self.toggled.emit(self._checked)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track_color = QColor(SIGNAL) if self._checked else QColor(HAIRLINE)
        painter.setBrush(track_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 11, 11)

        knob_x = self.width() - 18 if self._checked else 4
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QPointF(knob_x + 7, self.height() / 2), 7, 7)
        painter.end()
