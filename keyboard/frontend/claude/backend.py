"""
backend.py
==========
The only module that talks to the CLI backend or touches privilege
escalation. Everything else in the frontend goes through this.

Privilege model
----------------
The documented backend contract assumes `sudo python3 aula-f75.py ...`.
That doesn't work cleanly from a GUI subprocess: there's no terminal
attached for sudo to prompt in, so it either hangs waiting for a password
on stdin, or fails outright depending on the sudoers timestamp cache.

Instead, this app uses a one-time udev rule (99-aula-f75.rules) that grants
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
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Resolve the backend path relative to this file, not the CWD the app was
# launched from, since the spec places this script at frontend/ and the
# backend at ../cli/ relative to it.
_FRONTEND_DIR = Path(__file__).resolve().parent
BACKEND_SCRIPT = _FRONTEND_DIR.parent.parent / "cli" / "aula-f75.py"

UDEV_RULE_SOURCE = _FRONTEND_DIR / "99-aula-f75.rules"
UDEV_RULE_DEST = Path("/etc/udev/rules.d/99-aula-f75.rules")

WIRED_VID_PID = ("258a", "010c")
WIRELESS_VID_PID = ("3554", "fa09")

CALL_TIMEOUT_SECONDS = 10


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
    """Raised when the backend script itself can't be found or invoked."""


def _run(args: list[str]) -> CommandResult:
    if not BACKEND_SCRIPT.exists():
        raise BackendError(
            f"Backend script not found at {BACKEND_SCRIPT}. "
            "Expected keyboard/cli/aula-f75.py relative to keyboard/frontend/."
        )
    try:
        proc = subprocess.run(
            ["python3", str(BACKEND_SCRIPT), *args],
            capture_output=True,
            text=True,
            timeout=CALL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise BackendError(
            f"Backend call timed out after {CALL_TIMEOUT_SECONDS}s: {' '.join(args)}"
        ) from exc
    except OSError as exc:
        raise BackendError(f"Failed to launch backend: {exc}") from exc

    return CommandResult(
        ok=proc.returncode == 0,
        stdout=proc.stdout.strip(),
        stderr=proc.stderr.strip(),
        returncode=proc.returncode,
    )


def apply_effect(token: str) -> CommandResult:
    """Send an effect to the keyboard. token is any name/alias from `list`."""
    return _run([token])


def set_sleep(mode: str, minutes: int | None = None) -> CommandResult:
    """mode is 'on' or 'off'. minutes only applies when mode == 'on'."""
    args = ["sleep", mode]
    if mode == "on" and minutes is not None:
        args.append(str(minutes))
    return _run(args)


def list_effects_raw() -> CommandResult:
    """Mostly useful for debugging — the GUI ships its own static effect
    table (see effects.py) so it doesn't have to parse stdout to populate
    the browser. This stays available for a future "verify against
    backend" diagnostic."""
    return _run(["list"])


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
