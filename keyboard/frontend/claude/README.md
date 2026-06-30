# AULA F75 Control — Frontend

A PyQt6 GUI for the AULA F75 backend CLI (`cli/aula-f75.py`). The frontend
never touches USB/HID directly — every effect or sleep change is a
`subprocess` call into the backend script.

## Install

```bash
cd keyboard/frontend
pip install -r requirements.txt
```

Requires Python 3.10+ (uses `X | None` type syntax) and a desktop session
with `pkexec`/Polkit available — standard on Mint Cinnamon.

## Run

```bash
python3 app.py
```

On first run with the keyboard plugged in, you'll see a **"Needs setup"**
status and a banner with an **Install permission rule** button. Click it,
authenticate once via the graphical prompt, then unplug/replug the
keyboard. After that, the app needs no further authentication — see
"Why no `sudo`" below.

## Why no `sudo`

The backend's documented contract calls for `sudo python3 aula-f75.py ...`
on every command. That doesn't work from a GUI: `subprocess.run(["sudo",
...])` has no terminal attached, so it either hangs waiting for a password
on stdin or fails immediately depending on the sudo timestamp cache and
`askpass` configuration.

Instead, this app ships a `udev` rule
(`99-aula-f75.rules`) that grants your user's session direct read/write
access to the keyboard's USB device nodes, for both connection modes
(`258a:010c` wired, `3554:fa09` wireless). Once installed:

- The backend runs as your normal user — **no `sudo` in the subprocess
  call at all**. `backend.py` invokes `python3 aula-f75.py ...` directly.
- The *only* privileged operation in the whole app is writing that one
  rule file to `/etc/udev/rules.d/`, which happens once, via `pkexec` (a
  proper graphical Polkit prompt, not a hung terminal sudo).
- `USBPermissionChecker` checks actual device-node permissions at startup
  and on a 4-second poll, so the UI can tell "not plugged in" apart from
  "plugged in, but the rule isn't installed yet" — they show different
  banners and the second one offers the install button; the first just
  asks you to plug the keyboard in.

If you'd rather install the rule manually instead of using the in-app
button:

```bash
sudo cp 99-aula-f75.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
# then unplug/replug the keyboard
```

If `pkexec` isn't available on your system (`policykit-1` not installed),
`apt install policykit-1` or use the manual steps above.

## Architecture

```
frontend/
├── app.py            entry point
├── main_window.py     layout, all UI state transitions
├── backend.py          owns every subprocess call + udev install + permission checks
├── workers.py           QThread wrappers so subprocess calls never block the GUI
├── widgets.py           EffectSwatch (live animated preview), ToggleSwitch
├── effects.py            static table of the 16 effects (code, name, alias, anim style)
├── theme.py               palette / stylesheet, single source for all colors
└── 99-aula-f75.rules       udev rule template, installed via the in-app button
```

All backend calls run on a `QThread` (see `workers.py`); `subprocess.run`
blocks, and the GUI thread would freeze on every click without this. Each
worker emits a `CommandResult` or an error string back to the main thread.

`main_window.py` keeps connection state in one place
(`_apply_connection_state`) — that's the single function that decides
what's enabled, what banner shows, and what the status pill says. A
4-second poll timer re-checks device permissions in the background so
plugging in or unplugging the keyboard updates the UI without restarting
the app.

### A bug worth knowing about (found during testing, since fixed)

The connection state was originally initialized to `DISCONNECTED` and
deduplicated against incoming poll results to avoid redundant UI updates.
That broke the very first poll: if the real first result also happened to
be `DISCONNECTED` (e.g. keyboard not plugged in yet), the dedup check saw
"new state equals current state" and skipped the UI update entirely — the
status pill stayed stuck on its initial "Checking…" placeholder forever.
Fixed by using `None` as the "not yet known" sentinel instead of
`DISCONNECTED`, so the first real result is always applied. Caught by
actually running the app under `QT_QPA_PLATFORM=offscreen` and diffing two
screenshots, not by reading the code.

## Backend script

`cli/aula-f75.py` in this delivery is a **stub**, not the real driver — no
backend implementation was provided as part of this task. It implements
the exact documented contract (effect codes, aliases, exit codes, "Done!"
/ "AULA keyboard not found." strings, sleep on/off/timeout args) so the
frontend can be built and tested against real subprocess calls and real
exit codes instead of guessed behavior. `detect_device()` always reports
"wireless" present and every effect call sleeps 0.4s then succeeds — it
never touches actual USB.

**Replace `cli/aula-f75.py` with your real implementation.** The frontend
only depends on the documented CLI contract (see the spec), never on
anything inside this stub, so swapping the file is the only step needed.

## License

GPLv3 — see `LICENSE`.
