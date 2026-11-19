"""
backend.py
==========
The only module that talks to the library backend or touches privilege
escalation. Everything else in the frontend goes through this.

Privilege model
----------------
The app uses a one-time udev rule (99-aula-f75.rules) that grants
the user's session direct read/write access to the keyboard's USB device
nodes. Once installed, the backend runs as a normal user process — no sudo,
no password prompt, on every single call. The udev rule itself is installed
exactly once, via pkexec, because writing to /etc/udev/rules.d/ does require
root.

USBPermissionChecker below verifies device-node permissions at startup so
the UI can tell the difference between "keyboard not plugged in" and
"keyboard plugged in but rule not installed yet" — those need different
messages and different fixes.
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Add the keyboard package to path so we can import aula_f75
_FRONTEND_DIR = Path(__file__).resolve().parent
_KEYBOARD_ROOT = _FRONTEND_DIR.parent.parent
if str(_KEYBOARD_ROOT) not in sys.path:
    sys.path.insert(0, str(_KEYBOARD_ROOT))

# Ensure we import the package, not the local entry script aula_f75.py
import importlib.util

_pkg_path = _KEYBOARD_ROOT / "aula_f75"
spec = importlib.util.spec_from_file_location(
    "aula_f75", _pkg_path / "__init__.py"
)
if spec and spec.loader:
    aula_f75 = importlib.util.module_from_spec(spec)
    sys.modules["aula_f75"] = aula_f75
    spec.loader.exec_module(aula_f75)
else:
    import aula_f75  # type: ignore
from aula_f75 import (
    DeviceBusy,
    DeviceNotFound,
    WiredNotFound,
    WirelessNotFound,
)

UDEV_RULE_SOURCE = _FRONTEND_DIR / "99-aula-f75.rules"
UDEV_RULE_DEST = Path("/etc/udev/rules.d/99-aula-f75.rules")

WIRED_VID_PID = ("258a", "010c")
WIRELESS_VID_PID = ("3554", "fa09")


class ConnectionState(Enum):
    WIRED = "wired"
    WIRELESS = "wireless"
    DISCONNECTED = "disconnected"
    NO_PERMISSION = "no_permission"  # plugged in, but udev rule missing


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int


class BackendError(Exception):
    """Raised when the backend operation fails."""


def _to_backend_error(exc: Exception) -> BackendError:
    if isinstance(exc, (WirelessNotFound, WiredNotFound, DeviceNotFound, DeviceBusy, ValueError, RuntimeError, IOError)):
        return BackendError(str(exc))
    return BackendError(str(exc))


def apply_effect(token: str) -> CommandResult:
    """Send an effect to the keyboard. token is any name/alias from effects."""
    try:
        aula_f75.set_effect(token)
        return CommandResult(ok=True, stdout="", stderr="", returncode=0)
    except Exception as exc:
        raise _to_backend_error(exc) from exc


def set_color(hex_color: str) -> CommandResult:
    """Set the fixed-on colour from a 6-digit hex string (e.g. 'ff0000')."""
    try:
        aula_f75.set_color(hex_color)
        return CommandResult(ok=True, stdout="", stderr="", returncode=0)
    except Exception as exc:
        raise _to_backend_error(exc) from exc


def set_brightness(level: int) -> CommandResult:
    """Set brightness level 0-9."""
    try:
        aula_f75.set_brightness(level)
        return CommandResult(ok=True, stdout="", stderr="", returncode=0)
    except Exception as exc:
        raise _to_backend_error(exc) from exc


def set_colorful(on: bool) -> CommandResult:
    """Toggle colourful mode on/off."""
    try:
        aula_f75.set_colorful(on)
        return CommandResult(ok=True, stdout="", stderr="", returncode=0)
    except Exception as exc:
        raise _to_backend_error(exc) from exc


def set_sleep(mode: str, minutes: int | None = None) -> CommandResult:
    """mode is 'on' or 'off'. minutes only applies when mode == 'on'."""
    try:
        if mode == "off":
            if minutes is not None:
                raise ValueError("sleep off takes no timeout")
            aula_f75.set_sleep(0x00)
        elif mode == "on":
            if minutes is not None:
                aula_f75.set_sleep(minutes & 0xFF)
            else:
                aula_f75.set_sleep(0x03)
        else:
            try:
                aula_f75.set_sleep(int(mode) & 0xFF)
            except ValueError:
                raise ValueError(f"unknown sleep mode: {mode!r}")
        return CommandResult(ok=True, stdout="", stderr="", returncode=0)
    except Exception as exc:
        raise _to_backend_error(exc) from exc


def list_effects_raw() -> CommandResult:
    """Mostly useful for debugging."""
    # Build a simple list representation
    lines = []
    from aula_f75 import EFFECTS, ALIASES

    for effect in sorted(EFFECTS, key=lambda e: e.code):
        aliases = sorted(a for a, code in ALIASES.items() if code == effect.code)
        lines.append(
            f"  0x{effect.code:02x} {effect.name:20s} ({', '.join(aliases)})"
        )
    return CommandResult(
        ok=True, stdout="\n".join(lines), stderr="", returncode=0
    )


class USBPermissionChecker:
    """
    Inspects /dev/bus/usb device nodes directly to distinguish:
      - keyboard not plugged in at all
      - keyboard plugged in, but current user lacks rw permission (rule missing)
      - keyboard plugged in and accessible

    This only does filesystem permission checks — it never opens the device
    or sends USB control transfers. That stays the backend script's job.
    """

    @staticmethod
    def _find_device_nodes(vid: str, pid: str) -> list[Path]:
        matches: list[Path] = []
        for bus_path in glob.glob("/sys/bus/usb/devices/*"):
            id_vendor_file = Path(bus_path) / "idVendor"
            id_product_file = Path(bus_path) / "idProduct"
            if not (id_vendor_file.exists() and id_product_file.exists()):
                continue
            try:
                found_vid = id_vendor_file.read_text().strip()
                found_pid = id_product_file.read_text().strip()
            except OSError:
                continue
            if found_vid == vid and found_pid == pid:
                busnum_file = Path(bus_path) / "busnum"
                devnum_file = Path(bus_path) / "devnum"
                if busnum_file.exists() and devnum_file.exists():
                    try:
                        busnum = int(busnum_file.read_text().strip())
                        devnum = int(devnum_file.read_text().strip())
                        node = Path(
                            f"/dev/bus/usb/{busnum:03d}/{devnum:03d}"
                        )
                        if node.exists():
                            matches.append(node)
                    except (OSError, ValueError):
                        continue
        return matches

    @classmethod
    def check(cls) -> ConnectionState:
        for vid, pid, state in (
            (*WIRED_VID_PID, ConnectionState.WIRED),
            (*WIRELESS_VID_PID, ConnectionState.WIRELESS),
        ):
            nodes = cls._find_device_nodes(vid, pid)
            if not nodes:
                continue
            # Device is present — check whether we can actually read+write it.
            accessible = all(os.access(node, os.R_OK | os.W_OK) for node in nodes)
            return state if accessible else ConnectionState.NO_PERMISSION
        return ConnectionState.DISCONNECTED

    @staticmethod
    def udev_rule_installed() -> bool:
        return UDEV_RULE_DEST.exists()

    @staticmethod
    def install_udev_rule() -> CommandResult:
        """
        Writes the udev rule to /etc/udev/rules.d/ and reloads udev. This is
        the ONE privileged operation in the whole app, and it runs exactly
        once (or whenever the user explicitly re-clicks "Install Rule") —
        never on a per-effect basis.

        Uses pkexec so Cinnamon shows its normal graphical auth dialog
        instead of expecting a password on a non-existent terminal.
        """
        if not UDEV_RULE_SOURCE.exists():
            raise BackendError(f"udev rule template missing: {UDEV_RULE_SOURCE}")

        # A small shell script so the whole install is one pkexec prompt,
        # not three.
        install_cmd = (
            f"cp {UDEV_RULE_SOURCE} {UDEV_RULE_DEST} && "
            f"chmod 644 {UDEV_RULE_DEST} && "
            f"udevadm control --reload-rules && "
            f"udevadm trigger"
        )
        try:
            proc = subprocess.run(
                ["pkexec", "sh", "-c", install_cmd],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError as exc:
            raise BackendError(
                "pkexec not found. Install policykit-1 "
                "(sudo apt install policykit-1) or apply the rule manually — "
                "see README."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise BackendError("Polkit authentication timed out.") from exc

        return CommandResult(
            ok=proc.returncode == 0,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            returncode=proc.returncode,
        )
