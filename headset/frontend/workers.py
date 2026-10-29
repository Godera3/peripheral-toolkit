import enum
import errno
import glob
import os
import select
import sys

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtDBus import (
    QDBusConnection, QDBusMessage, QDBusPendingCallWatcher, QDBusPendingReply, QDBusServiceWatcher
)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from headset import device
from backend import get_battery

# --- Config ---
RAZER_VID = 0x1532
BT_MAC = "44:5E:CD:5A:EB:7A" # From your bluetoothctl output
BT_ADAPTER = "hci0"
GRACE_MS = 6000
BT_POLL_MS = 10_000

LOST_HEAD = bytes.fromhex("020a60")
LOST_TAIL = bytes.fromhex("808020020100")

def is_link_lost(pkt: bytes) -> bool:
    return pkt[:3] == LOST_HEAD and LOST_TAIL in pkt

def find_hidraw_nodes() -> list[str]:
    out = []
    for sys_dir in glob.glob("/sys/class/hidraw/hidraw*"):
        try:
            with open(f"{sys_dir}/device/uevent") as f:
                uevent = f.read()
        except OSError:
            continue
        for line in uevent.splitlines():
            if line.startswith("HID_ID="):
                _bus, vid, pid = line.split("=", 1)[1].split(":")
                if int(vid, 16) == RAZER_VID:
                    out.append("/dev/" + os.path.basename(sys_dir))
                    break
    return out

class BatteryWorker(QThread):
    result = pyqtSignal(int)
    def run(self):
        self.result.emit(get_battery())

class HidDongleWorker(QThread):
    link_up = pyqtSignal(bool)
    node_present = pyqtSignal(bool)
    eq_changed = pyqtSignal(str)
    lights_changed = pyqtSignal(bool)
    problem = pyqtSignal(str)

    SCAN_INTERVAL_MS = 1000
    SELECT_TIMEOUT_S = 0.5

    def run(self) -> None:
        fds: dict[int, str] = {}
        while not self.isInterruptionRequested():
            if not fds:
                for path in find_hidraw_nodes():
                    try:
                        fds[os.open(path, os.O_RDONLY | os.O_NONBLOCK)] = path
                    except OSError:
                        pass
                if not fds:
                    self.msleep(self.SCAN_INTERVAL_MS)
                    continue
                self.node_present.emit(True)

            try:
                readable, _, _ = select.select(list(fds), [], [], self.SELECT_TIMEOUT_S)
            except (OSError, ValueError):
                readable = list(fds)

            for fd in readable:
                try:
                    data = os.read(fd, 64)
                    if not data:
                        raise OSError(errno.ENODEV, "EOF")
                except BlockingIOError:
                    continue
                except OSError:
                    os.close(fd)
                    fds.pop(fd, None)
                    continue
                
                self.link_up.emit(not is_link_lost(data))
                
                if len(data) >= 14 and data[0] == 0x02:
                    if data[10] == 0x13:
                        val = data[13]
                        modes = {0x07: "game", 0x08: "music", 0x09: "movie", 0xFF: "custom"}
                        self.eq_changed.emit(modes.get(val, "game"))
                    elif data[10] == 0x40:
                        self.lights_changed.emit(data[13] != 0x00)

            if not fds:
                self.node_present.emit(False)
                self.link_up.emit(False)

        for fd in fds:
            os.close(fd)

class BluezWatcher(QObject):
    connected_changed = pyqtSignal(bool)
    BLUEZ = "org.bluez"
    DEV_IFACE = "org.bluez.Device1"
    PROPS_IFACE = "org.freedesktop.DBus.Properties"

    def __init__(self, mac: str, adapter: str = "hci0", parent: QObject | None = None):
        super().__init__(parent)
        self._path = f"/org/bluez/{adapter}/dev_{mac.upper().replace(':', '_')}"
        self._bus = QDBusConnection.systemBus()
        self._value: bool | None = None
        self._seq = 0

        self._bus.connect(self.BLUEZ, self._path, self.PROPS_IFACE, "PropertiesChanged", self._on_props_changed)
        self._svc = QDBusServiceWatcher(self.BLUEZ, self._bus, QDBusServiceWatcher.WatchModeFlag.WatchForOwnerChange, self)
        self._svc.serviceRegistered.connect(lambda _n: self.refresh())
        self._svc.serviceUnregistered.connect(lambda _n: self._set(False))

        self._poll = QTimer(self)
        self._poll.setInterval(BT_POLL_MS)
        self._poll.timeout.connect(self.refresh)
        self._poll.start()
        self.refresh()

    @pyqtSlot(QDBusMessage)
    def _on_props_changed(self, msg: QDBusMessage) -> None:
        args = msg.arguments()
        if args and args[0] == self.DEV_IFACE:
            self.refresh()

    def refresh(self) -> None:
        self._seq += 1
        seq = self._seq
        msg = QDBusMessage.createMethodCall(self.BLUEZ, self._path, self.PROPS_IFACE, "Get")
        msg.setArguments([self.DEV_IFACE, "Connected"])
        watcher = QDBusPendingCallWatcher(self._bus.asyncCall(msg, 3000), self)
        watcher.finished.connect(lambda w, s=seq: self._on_reply(w, s))

    def _on_reply(self, watcher: QDBusPendingCallWatcher, seq: int) -> None:
        watcher.deleteLater()
        if seq != self._seq:
            return
        reply = QDBusPendingReply(watcher)
        if reply.isError():
            self._set(False)
            return
        v = reply.argumentAt(0)
        v = v.variant() if hasattr(v, "variant") else v
        self._set(bool(v))

    def _set(self, value: bool) -> None:
        if value != self._value:
            self._value = value
            self.connected_changed.emit(value)

class State(enum.Enum):
    WIRELESS = "wireless"
    BLUETOOTH = "bluetooth"
    OFF = "off"
    RESOLVING = "resolving"

class StatusResolver(QObject):
    state_changed = pyqtSignal(object)

    def __init__(self, grace_ms: int = GRACE_MS, parent: QObject | None = None):
        super().__init__(parent)
        self._node = False
        self._lost_flag = False
        self._bt: bool | None = None
        self.state: State | None = None

        self._grace = QTimer(self)
        self._grace.setSingleShot(True)
        self._grace.setInterval(grace_ms)
        self._grace.timeout.connect(self._grace_expired)

    @pyqtSlot(bool)
    def on_node(self, present: bool) -> None:
        self._node = present
        if present:
            self._lost_flag = False
        self._evaluate()

    @pyqtSlot(bool)
    def on_link(self, up: bool) -> None:
        self._lost_flag = not up
        self._evaluate()

    @pyqtSlot(bool)
    def on_bt(self, connected: bool) -> None:
        self._bt = connected
        self._evaluate()

    @property
    def _dongle_up(self) -> bool:
        return self._node and not self._lost_flag

    def _evaluate(self) -> None:
        if self._dongle_up:
            self._grace.stop()
            self._set(State.WIRELESS)
        elif self._bt:
            self._grace.stop()
            self._set(State.BLUETOOTH)
        elif self._bt is None:
            pass
        elif self.state in (State.WIRELESS, None):
            self._set(State.RESOLVING)
            if not self._grace.isActive():
                self._grace.start()
        elif self.state is State.BLUETOOTH:
            self._set(State.OFF)

    def _grace_expired(self) -> None:
        if not self._dongle_up and not self._bt:
            self._set(State.OFF)

    def _set(self, s: State) -> None:
        if s is not self.state:
            self.state = s
            self.state_changed.emit(s)
