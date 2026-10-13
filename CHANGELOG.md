# Changelog

Notable changes to the toolkit. Older history lives in the git log.

## 2026-10-14 — AULA F75: two bug fixes + no-`sudo` docs

### Fixed

- **Wireless `sleep` command crashed.**
  The `sleep` branch of `main()` called `send_sequence(dev, seq, …)`, but `seq`
  was never assigned in that scope (it only exists inside `send_sleep()` and the
  color/brightness/colorful branch). Every `sleep off`, `sleep on`,
  `sleep on <n>` and `sleep <n>` died with
  `UnboundLocalError: cannot access local variable 'seq'` and sent **zero**
  fragments. Now calls the already-written `send_sleep(dev, sleep_value)`
  helper — all four forms send the expected **11** fragmentation writes.
  ([`4b89a6c`](https://github.com/Godera3/peripheral-toolkit/commit/4b89a6c))

- **Kernel driver was not re-attached after each command (knob died).**
  `restore_kernel_drivers()` called `attach_kernel_driver(1)` **before**
  `usb.util.dispose_resources(dev)`. After any control transfer the interface
  stays busy, so `attach_kernel_driver()` fails with `EBUSY (Errno 16)` until
  the libusb handle is released. Under `sudo` a root-only sysfs
  `usbhid/bind` fallback masked the bug, but when running unprivileged
  (the frontend's udev-rule / "no sudo" model) it silently left **interface 1**
  — the rotary-encoder, consumer-control and system-control interfaces —
  unbound after *every* command until a physical replug. Fixed by releasing
  the handle before re-attaching (bus/port are captured first so the sysfs
  fallback still works for root).
  ([`1772e97`](https://github.com/Godera3/peripheral-toolkit/commit/1772e97))

  Isolated with four experiments: `detach→attach` (0 transfers) succeeds, but
  `detach→1 transfer→attach` and `detach→48→attach` both fail `Resource busy`,
  while `detach→48→dispose→attach` succeeds.

### Documentation

- Root and `keyboard/` READMEs now document the bundled udev rule so the CLI
  can run **without `sudo`**, and document the `color` / `brightness` /
  `colorful` adjustment commands (which also give a static, non-animating
  board).
- `keyboard/frontend/claude/README.md`: corrected the entry point
  (`claude/aula_f75.py`, not `app.py`) and removed the stale "the backend is a
  stub" note — the backend is the real driver.
