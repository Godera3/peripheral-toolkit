"""
main_window.py
==============
Top-level window. Layout:

  TitleBar          app name + connection status pill
  [optional banner] shown only when disconnected or permission-missing
  Effects section    scrollable grid of EffectCard widgets
  Sleep section       toggle + timeout slider/spinbox, wireless-only

State flows one direction: ConnectionPollWorker -> _on_connection_state ->
_apply_connection_state, which is the single place that decides what's
enabled, what banner shows, and what the status pill says. Nothing else
in the window mutates that state directly.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QColorDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import backend
from backend import BackendError, CommandResult, ConnectionState
from effects import EFFECTS, Effect
from theme import SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XL, state_color
from widgets import EffectSwatch, ToggleSwitch
from workers import (
    ConnectionPollWorker,
    EffectApplyWorker,
    ParamApplyWorker,
    SleepSetWorker,
    UdevInstallWorker,
)

POLL_INTERVAL_MS = 4000
DEFAULT_SLEEP_MINUTES = 30


class EffectCard(QFrame):
    """One effect tile: swatch + name + hex code. Click anywhere to apply."""

    def __init__(self, effect: Effect, on_click, parent=None):
        super().__init__(parent)
        self._effect = effect
        self._on_click = on_click
        self.setObjectName("EffectCard")
        self.setProperty("active", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(78)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE_SM, SPACE_SM, SPACE_SM, SPACE_SM)
        layout.setSpacing(SPACE_SM)

        swatch = EffectSwatch(anim=effect.anim, base_hue=self._hue_for(effect.code))
        layout.addWidget(swatch)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        name_label = QLabel(effect.name)
        name_label.setObjectName("EffectName")
        code_label = QLabel(f"0x{effect.code:02x}  ·  {effect.primary_alias}")
        code_label.setObjectName("EffectCode")
        text_col.addWidget(name_label)
        text_col.addWidget(code_label)
        text_col.addStretch()
        layout.addLayout(text_col)
        layout.addStretch()

        self._spinner = QLabel("")
        self._spinner.setStyleSheet("color: " + state_color("wired") + ";")
        layout.addWidget(self._spinner)

    @staticmethod
    def _hue_for(code: int) -> float:
        # Spreads single-hue effects across the wheel by code so the grid
        # doesn't visually clump on one color when several effects share
        # an animation family (e.g. respire vs fixed-on).
        return (code * 0.13) % 1.0

    def set_active(self, active: bool) -> None:
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_busy(self, busy: bool) -> None:
        self._spinner.setText("●" if busy else "")
        self.setEnabled(not busy)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self._on_click(self._effect)


class FixedOnControlsPanel(QFrame):
    """Color presets, custom picker, brightness slider, colorful toggle.
    Visible only when Fixed On (0x01) is active on a wireless connection."""

    color_selected = pyqtSignal(object)  # str (hex)
    brightness_changed = pyqtSignal(object)  # int (0-9)
    colorful_toggled = pyqtSignal(object)  # bool

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EffectCard")
        self.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        layout.setSpacing(SPACE_SM)

        # ── Header ──
        header = QLabel("FIXED ON")
        header.setObjectName("SectionLabel")
        layout.addWidget(header)

        # ── Color presets ──
        self._preset_colors = [
            ("#FF0000", "Red"), ("#FF8000", "Orange"), ("#F5E642", "Yellow"),
            ("#00FF00", "Green"), ("#00FFFF", "Cyan"), ("#0000FF", "Blue"),
            ("#8000FF", "Purple"), ("#FFFFFF", "White"),
        ]
        self._color_btns: list[QPushButton] = []

        color_row = QHBoxLayout()
        color_row.setSpacing(SPACE_SM)
        color_label = QLabel("Color")
        color_label.setStyleSheet("color: #8B8F9C; font-size: 12px;")
        color_row.addWidget(color_label)

        for hex_color, name in self._preset_colors:
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setToolTip(name)
            btn.setStyleSheet(
                f"background-color: {hex_color}; border: 1px solid #2D3038; "
                f"border-radius: 4px; min-width: 0; padding: 0;"
            )
            btn.clicked.connect(lambda checked, h=hex_color: self._on_color_picked(h))
            color_row.addWidget(btn)
            self._color_btns.append(btn)

        custom_btn = QPushButton("Custom\u2026")
        custom_btn.setFixedHeight(28)
        custom_btn.clicked.connect(self._on_custom_color)
        color_row.addWidget(custom_btn)
        color_row.addStretch()
        layout.addLayout(color_row)

        # ── Brightness ──
        bright_row = QHBoxLayout()
        bright_row.setSpacing(SPACE_SM)
        bright_label = QLabel("Brightness")
        bright_label.setStyleSheet("color: #8B8F9C; font-size: 12px;")
        bright_row.addWidget(bright_label)

        self._brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self._brightness_slider.setRange(0, 9)
        self._brightness_slider.setValue(9)
        self._brightness_slider.valueChanged.connect(self._on_brightness_changed)
        bright_row.addWidget(self._brightness_slider, stretch=1)

        self._brightness_label = QLabel("9")
        self._brightness_label.setFixedWidth(20)
        self._brightness_label.setStyleSheet("color: #8B8F9C; font-size: 12px;")
        bright_row.addWidget(self._brightness_label)
        layout.addLayout(bright_row)

        # ── Colorful toggle ──
        colorful_row = QHBoxLayout()
        colorful_row.setSpacing(SPACE_SM)
        colorful_label = QLabel("Colorful")
        colorful_label.setStyleSheet("color: #8B8F9C; font-size: 12px;")
        colorful_row.addWidget(colorful_label)

        self._colorful_toggle = ToggleSwitch(checked=False)
        self._colorful_toggle.toggled.connect(self._on_colorful_toggled)
        colorful_row.addWidget(self._colorful_toggle)

        self._colorful_status = QLabel("OFF")
        self._colorful_status.setStyleSheet("color: #6B6F7C; font-size: 12px;")
        colorful_row.addWidget(self._colorful_status)
        colorful_row.addStretch()
        layout.addLayout(colorful_row)

        # ── Debounce timer for brightness ──
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._emit_brightness)
        self._pending_brightness = 9

    # ── Public helpers ──

    def is_colorful_on(self) -> bool:
        return self._colorful_toggle.isChecked()

    def set_colorful_checked(self, on: bool) -> None:
        self._colorful_toggle.blockSignals(True)
        self._colorful_toggle.setChecked(on)
        self._colorful_status.setText("ON" if on else "OFF")
        self._colorful_toggle.blockSignals(False)

    # ── Slots ──

    def _on_color_picked(self, hex_color: str) -> None:
        self.color_selected.emit(hex_color)

    def _on_custom_color(self) -> None:
        color = QColorDialog.getColor()
        if color.isValid():
            self._on_color_picked(color.name())

    def _on_brightness_changed(self, value: int) -> None:
        self._brightness_label.setText(str(value))
        self._pending_brightness = value
        self._debounce.start()

    def _emit_brightness(self) -> None:
        self.brightness_changed.emit(self._pending_brightness)

    def _on_colorful_toggled(self, checked: bool) -> None:
        self._colorful_status.setText("ON" if checked else "OFF")
        self.colorful_toggled.emit(checked)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AULA F75 — RGB Control")
        self.resize(560, 700)
        self.setMinimumSize(440, 560)

        self._cards: dict[int, EffectCard] = {}
        self._active_code: int | None = None
        # None (not DISCONNECTED) until the first real poll result arrives.
        # Using DISCONNECTED as the sentinel here would mean the first poll,
        # if it also resolves to DISCONNECTED, gets deduped away by the
        # "state == self._connection_state" check below and the UI never
        # leaves its initial "Checking..." placeholder.
        self._connection_state: ConnectionState | None = None
        self._apply_worker: EffectApplyWorker | None = None
        self._sleep_worker: SleepSetWorker | None = None
        self._udev_worker: UdevInstallWorker | None = None
        self._poll_worker: ConnectionPollWorker | None = None
        self._fixed_on_worker: ParamApplyWorker | None = None

        self._build_ui()
        self._start_polling()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_titlebar())

        self._banner_host = QVBoxLayout()
        self._banner_host.setContentsMargins(SPACE_LG, SPACE_MD, SPACE_LG, 0)
        banner_wrap = QWidget()
        banner_wrap.setLayout(self._banner_host)
        root_layout.addWidget(banner_wrap)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        scroll_layout.setSpacing(SPACE_LG)

        scroll_layout.addWidget(self._build_effects_section())
        scroll_layout.addWidget(self._build_fixed_on_panel())
        scroll_layout.addWidget(self._build_sleep_section())
        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        root_layout.addWidget(scroll, stretch=1)

        self.setCentralWidget(root)

    def _build_titlebar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TitleBar")
        bar.setFixedHeight(56)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(SPACE_LG, 0, SPACE_LG, 0)

        title = QLabel("AULA F75")
        title.setObjectName("AppTitle")
        layout.addWidget(title)
        layout.addStretch()

        self._status_pill = QLabel("Checking…")
        self._status_pill.setObjectName("StatusPill")
        self._status_pill.setStyleSheet(
            "color: #8B8F9C; border: 1px solid #2D3038; background: transparent;"
        )
        layout.addWidget(self._status_pill)
        return bar

    def _build_effects_section(self) -> QWidget:
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE_MD)

        label = QLabel("EFFECTS")
        label.setObjectName("SectionLabel")
        layout.addWidget(label)

        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setSpacing(SPACE_SM)
        columns = 2
        for i, effect in enumerate(EFFECTS):
            card = EffectCard(effect, on_click=self._on_effect_clicked)
            self._cards[effect.code] = card
            grid.addWidget(card, i // columns, i % columns)
        layout.addWidget(grid_host)
        return section

    def _build_fixed_on_panel(self) -> FixedOnControlsPanel:
        panel = FixedOnControlsPanel()
        panel.color_selected.connect(self._on_fixed_on_color)
        panel.brightness_changed.connect(self._on_fixed_on_brightness)
        panel.colorful_toggled.connect(self._on_fixed_on_colorful)
        self._fixed_on_panel = panel
        return panel

    def _build_sleep_section(self) -> QWidget:
        section = QFrame()
        section.setObjectName("EffectCard")  # reuse panel styling
        layout = QVBoxLayout(section)
        layout.setContentsMargins(SPACE_MD, SPACE_MD, SPACE_MD, SPACE_MD)
        layout.setSpacing(SPACE_SM)

        header = QHBoxLayout()
        label = QLabel("SLEEP MODE")
        label.setObjectName("SectionLabel")
        header.addWidget(label)
        header.addStretch()
        self._sleep_toggle = ToggleSwitch(checked=False)
        self._sleep_toggle.toggled.connect(self._on_sleep_toggled)
        header.addWidget(self._sleep_toggle)
        layout.addLayout(header)

        self._sleep_hint = QLabel("Wireless dongle only.")
        self._sleep_hint.setStyleSheet("color: #8B8F9C; font-size: 12px;")
        layout.addWidget(self._sleep_hint)

        timeout_row = QHBoxLayout()
        timeout_row.setSpacing(SPACE_SM)
        timeout_label = QLabel("Timeout")
        timeout_row.addWidget(timeout_label)

        self._sleep_slider = QSlider(Qt.Orientation.Horizontal)
        self._sleep_slider.setRange(1, 120)
        self._sleep_slider.setValue(DEFAULT_SLEEP_MINUTES)
        self._sleep_slider.valueChanged.connect(self._on_slider_changed)
        timeout_row.addWidget(self._sleep_slider, stretch=1)

        self._sleep_spinbox = QSpinBox()
        self._sleep_spinbox.setRange(1, 120)
        self._sleep_spinbox.setValue(DEFAULT_SLEEP_MINUTES)
        self._sleep_spinbox.setSuffix(" min")
        self._sleep_spinbox.valueChanged.connect(self._on_spinbox_changed)
        timeout_row.addWidget(self._sleep_spinbox)

        layout.addLayout(timeout_row)

        self._sleep_apply_btn = QPushButton("Apply timeout")
        self._sleep_apply_btn.clicked.connect(self._on_apply_sleep_timeout)
        layout.addWidget(self._sleep_apply_btn)

        self._set_sleep_controls_enabled(False)
        return section

    # ------------------------------------------------------------------
    # Connection state
    # ------------------------------------------------------------------

    def _start_polling(self) -> None:
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_connection)
        self._poll_timer.start(POLL_INTERVAL_MS)
        self._poll_connection()  # immediate first check, don't wait 4s

    def _poll_connection(self) -> None:
        if self._poll_worker is not None and self._poll_worker.isRunning():
            return  # previous check still in flight, skip this tick
        self._poll_worker = ConnectionPollWorker()
        self._poll_worker.state_ready.connect(self._on_connection_state)
        self._poll_worker.start()

    def _on_connection_state(self, state: ConnectionState) -> None:
        if state == self._connection_state:
            return
        self._connection_state = state
        self._apply_connection_state(state)

    def _apply_connection_state(self, state: ConnectionState) -> None:
        self._clear_banners()

        pill_text = {
            ConnectionState.WIRED: "● Wired",
            ConnectionState.WIRELESS: "● Wireless",
            ConnectionState.DISCONNECTED: "○ Disconnected",
            ConnectionState.NO_PERMISSION: "○ Needs setup",
        }[state]
        color = state_color(state.value)
        self._status_pill.setText(pill_text)
        self._status_pill.setStyleSheet(
            f"color: {color}; border: 1px solid {color}; background: transparent;"
        )

        controls_enabled = state in (ConnectionState.WIRED, ConnectionState.WIRELESS)
        for card in self._cards.values():
            card.setEnabled(controls_enabled)

        sleep_enabled = state == ConnectionState.WIRELESS
        self._set_sleep_controls_enabled(sleep_enabled)
        self._sleep_hint.setText(
            "Wireless dongle only — not available on wired connection."
            if state == ConnectionState.WIRED
            else "Wireless dongle only."
        )

        fixed_on_enabled = state == ConnectionState.WIRELESS
        self._fixed_on_panel.setEnabled(fixed_on_enabled)
        if not fixed_on_enabled:
            self._fixed_on_panel.setVisible(False)

        if state == ConnectionState.DISCONNECTED:
            self._show_banner(
                "Keyboard not found.",
                "Plug in the AULA F75 (wired or wireless dongle) — controls will "
                "enable automatically once it's detected.",
                kind="error",
            )
        elif state == ConnectionState.NO_PERMISSION:
            self._show_banner(
                "Keyboard detected, but this app can't access it yet.",
                "A one-time permission rule is needed so commands don't require "
                "a password every time. Click to install it now.",
                kind="warn",
                action_label="Install permission rule",
                action=self._on_install_udev_rule,
            )

    def _set_sleep_controls_enabled(self, enabled: bool) -> None:
        for w in (self._sleep_toggle, self._sleep_slider, self._sleep_spinbox, self._sleep_apply_btn):
            w.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Banners
    # ------------------------------------------------------------------

    def _clear_banners(self) -> None:
        while self._banner_host.count():
            item = self._banner_host.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _show_banner(
        self, title: str, body: str, kind: str = "error", action_label: str | None = None, action=None
    ) -> None:
        frame = QFrame()
        frame.setObjectName("ErrorBanner" if kind == "error" else "WarnBanner")
        layout = QVBoxLayout(frame)
        layout.setSpacing(SPACE_SM)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(title_label)

        body_label = QLabel(body)
        body_label.setWordWrap(True)
        body_label.setStyleSheet("color: #C7C9D1;")
        layout.addWidget(body_label)

        if action_label and action:
            btn = QPushButton(action_label)
            btn.setObjectName("PrimaryButton")
            btn.clicked.connect(action)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self._banner_host.addWidget(frame)

    # ------------------------------------------------------------------
    # Effect apply
    # ------------------------------------------------------------------

    def _on_effect_clicked(self, effect: Effect) -> None:
        if self._apply_worker is not None and self._apply_worker.isRunning():
            return  # ignore rapid double-clicks while a call is in flight

        card = self._cards[effect.code]
        card.set_busy(True)

        self._apply_worker = EffectApplyWorker(effect.primary_alias)
        self._apply_worker.finished_ok.connect(
            lambda result, e=effect: self._on_effect_applied(e, result)
        )
        self._apply_worker.finished_err.connect(
            lambda msg, e=effect: self._on_effect_error(e, msg)
        )
        self._apply_worker.start()

    def _on_effect_applied(self, effect: Effect, result: CommandResult) -> None:
        card = self._cards[effect.code]
        card.set_busy(False)

        if result.ok and "Done!" in result.stdout:
            if self._active_code is not None and self._active_code in self._cards:
                self._cards[self._active_code].set_active(False)
            card.set_active(True)
            self._active_code = effect.code
            self._fixed_on_panel.setVisible(
                effect.code == 0x01
                and self._connection_state == ConnectionState.WIRELESS
            )
        else:
            # Exit 0 but unexpected output, or non-zero exit — treat as failure.
            if "AULA keyboard not found." in (result.stdout + result.stderr):
                self._on_connection_state(ConnectionState.DISCONNECTED)
            self._show_apply_failure(effect, result.stdout or result.stderr)

    def _on_effect_error(self, effect: Effect, message: str) -> None:
        card = self._cards[effect.code]
        card.set_busy(False)
        self._show_apply_failure(effect, message)

    def _show_apply_failure(self, effect: Effect, detail: str) -> None:
        QMessageBox.warning(
            self,
            "Couldn't apply effect",
            f"\"{effect.name}\" wasn't applied.\n\n{detail or 'Unknown error.'}",
        )

    # ------------------------------------------------------------------
    # Fixed ON parameter controls
    # ------------------------------------------------------------------

    def _schedule_param(self, fn) -> None:
        worker = ParamApplyWorker(fn)
        worker.finished.connect(self._on_fixed_on_param_done)
        worker.start()

    def _on_fixed_on_color(self, hex_color: str) -> None:
        need_colorful_off = self._fixed_on_panel.is_colorful_on()
        if need_colorful_off:
            self._fixed_on_panel.set_colorful_checked(False)
        self._schedule_param(lambda: backend.set_color(hex_color))
        if need_colorful_off:
            QTimer.singleShot(
                200, lambda: self._schedule_param(lambda: backend.set_colorful(False))
            )

    def _on_fixed_on_brightness(self, level: int) -> None:
        self._schedule_param(lambda: backend.set_brightness(level))

    def _on_fixed_on_colorful(self, on: bool) -> None:
        self._schedule_param(lambda: backend.set_colorful(on))

    def _on_fixed_on_param_done(self, result: CommandResult) -> None:
        if not result.ok:
            QMessageBox.warning(
                self,
                "Parameter not applied",
                result.stderr or result.stdout or "Unknown error.",
            )

    # ------------------------------------------------------------------
    # Sleep controls
    # ------------------------------------------------------------------

    def _on_slider_changed(self, value: int) -> None:
        self._sleep_spinbox.blockSignals(True)
        self._sleep_spinbox.setValue(value)
        self._sleep_spinbox.blockSignals(False)

    def _on_spinbox_changed(self, value: int) -> None:
        self._sleep_slider.blockSignals(True)
        self._sleep_slider.setValue(value)
        self._sleep_slider.blockSignals(False)

    def _on_sleep_toggled(self, checked: bool) -> None:
        if checked:
            self._on_apply_sleep_timeout()
        else:
            self._run_sleep_set("off", None)

    def _on_apply_sleep_timeout(self) -> None:
        if not self._sleep_toggle.isChecked():
            self._sleep_toggle.setChecked(True)
            return  # the setChecked above will re-enter via _on_sleep_toggled
        minutes = self._sleep_spinbox.value()
        self._run_sleep_set("on", minutes)

    def _run_sleep_set(self, mode: str, minutes: int | None) -> None:
        if self._sleep_worker is not None and self._sleep_worker.isRunning():
            return
        self._set_sleep_controls_enabled(False)
        self._sleep_worker = SleepSetWorker(mode, minutes)
        self._sleep_worker.finished_ok.connect(self._on_sleep_set_done)
        self._sleep_worker.finished_err.connect(self._on_sleep_set_error)
        self._sleep_worker.start()

    def _on_sleep_set_done(self, result: CommandResult) -> None:
        self._set_sleep_controls_enabled(
            self._connection_state == ConnectionState.WIRELESS
        )
        if not result.ok:
            QMessageBox.warning(
                self, "Sleep setting not applied", result.stdout or result.stderr or "Unknown error."
            )

    def _on_sleep_set_error(self, message: str) -> None:
        self._set_sleep_controls_enabled(
            self._connection_state == ConnectionState.WIRELESS
        )
        QMessageBox.warning(self, "Sleep setting not applied", message)

    # ------------------------------------------------------------------
    # udev install
    # ------------------------------------------------------------------

    def _on_install_udev_rule(self) -> None:
        if self._udev_worker is not None and self._udev_worker.isRunning():
            return
        self._udev_worker = UdevInstallWorker()
        self._udev_worker.finished_ok.connect(self._on_udev_install_done)
        self._udev_worker.finished_err.connect(self._on_udev_install_error)
        self._udev_worker.start()

    def _on_udev_install_done(self, result: CommandResult) -> None:
        if result.ok:
            QMessageBox.information(
                self,
                "Permission rule installed",
                "Unplug and reconnect the keyboard (or replug the dongle) for the "
                "new permissions to take effect.",
            )
        else:
            QMessageBox.warning(
                self,
                "Couldn't install permission rule",
                result.stderr or result.stdout or "Authentication was cancelled or failed.",
            )
        self._poll_connection()

    def _on_udev_install_error(self, message: str) -> None:
        QMessageBox.warning(self, "Couldn't install permission rule", message)

    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # noqa: N802
        for card in self._cards.values():
            card.findChild(EffectSwatch) and None  # swatches stop themselves via parent deletion
        for swatch in self.findChildren(EffectSwatch):
            swatch.stop()
        super().closeEvent(event)
