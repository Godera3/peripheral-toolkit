"""
workers.py
==========
QThread wrappers around backend.py calls. subprocess.run() blocks, and the
CLI's own documentation implies real USB write latency — running it
directly on the GUI thread would freeze the whole window on every click.
Each worker emits a signal with the CommandResult (or a BackendError
message) when done; callers connect once and never block.
"""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

import backend
from backend import BackendError, CommandResult, ConnectionState


class EffectApplyWorker(QThread):
    finished_ok = pyqtSignal(object)  # CommandResult
    finished_err = pyqtSignal(str)

    def __init__(self, alias: str, parent=None):
        super().__init__(parent)
        self._alias = alias

    def run(self) -> None:
        try:
            result = backend.apply_effect(self._alias)
        except BackendError as exc:
            self.finished_err.emit(str(exc))
            return
        self.finished_ok.emit(result)


class SleepSetWorker(QThread):
    finished_ok = pyqtSignal(object)  # CommandResult
    finished_err = pyqtSignal(str)

    def __init__(self, mode: str, minutes: int | None, parent=None):
        super().__init__(parent)
        self._mode = mode
        self._minutes = minutes

    def run(self) -> None:
        try:
            result = backend.set_sleep(self._mode, self._minutes)
        except BackendError as exc:
            self.finished_err.emit(str(exc))
            return
        self.finished_ok.emit(result)


class ConnectionPollWorker(QThread):
    """Lightweight, runs on a timer from the main window to re-check
    device presence/permissions without touching the GUI thread."""

    state_ready = pyqtSignal(object)  # ConnectionState

    def run(self) -> None:
        state = backend.USBPermissionChecker.check()
        self.state_ready.emit(state)


class UdevInstallWorker(QThread):
    finished_ok = pyqtSignal(object)  # CommandResult
    finished_err = pyqtSignal(str)

    def run(self) -> None:
        try:
            result = backend.USBPermissionChecker.install_udev_rule()
        except BackendError as exc:
            self.finished_err.emit(str(exc))
            return
        self.finished_ok.emit(result)


class ParamApplyWorker(QThread):
    """Generic worker for quick parameter changes (color, brightness, colorful).
    Takes a zero-argument callable that returns a CommandResult."""

    finished = pyqtSignal(object)  # CommandResult

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            result = self._fn()
        except BackendError as exc:
            self.finished.emit(
                CommandResult(ok=False, stdout="", stderr=str(exc), returncode=-1)
            )
            return
        self.finished.emit(result)
