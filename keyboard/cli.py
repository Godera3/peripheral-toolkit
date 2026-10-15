#!/usr/bin/env python3
"""
cli.py
======
Thin command-line front end for the `aula_f75` package. All protocol logic
lives in the package; this file only parses arguments and maps exceptions to
exit codes.

    python3 cli.py list
    python3 cli.py rainbow
    python3 cli.py fixed-on
    python3 cli.py color ff0000
    python3 cli.py brightness 5
    python3 cli.py colorful on
    python3 cli.py sleep on 40
"""
from __future__ import annotations

import argparse
import sys

from aula_f75 import (
    ALIASES,
    EFFECTS,
    DeviceBusy,
    DeviceNotFound,
    WirelessNotFound,
    WiredNotFound,
    set_brightness,
    set_color,
    set_colorful,
    set_effect,
    set_sleep,
)

SLEEP_MODES = {"off": 0x00, "on": 0x03}


def _cmd_list(_args) -> None:
    for effect in sorted(EFFECTS, key=lambda e: e.code):
        aliases = sorted(a for a, code in ALIASES.items() if code == effect.code)
        print(f"  0x{effect.code:02x} {effect.name:20s} ({', '.join(aliases)})")
    print()
    print("Sleep modes: (aula-f75 sleep <mode> [timeout])")
    for name, value in sorted(SLEEP_MODES.items(), key=lambda kv: kv[1]):
        print(f"  0x{value:02x}  sleep-{name}")
    print("  or:  aula-f75 sleep on <minutes>")
    print()
    print("Adjustments (wireless only):")
    print("  aula-f75 color <hex>        set fixed-on colour, e.g. ff0000, 00ff00, 0000ff")
    print("  aula-f75 brightness <0-9>   set brightness level (default 9, captured 5)")
    print("  aula-f75 colorful on|off     toggle colourful mode")


def _cmd_sleep(args) -> None:
    mode = args.mode.lower()
    if mode == "off":
        if args.timeout is not None:
            raise SystemExit("sleep off takes no timeout")
        value = SLEEP_MODES["off"]
    elif mode == "on":
        value = args.timeout if args.timeout is not None else SLEEP_MODES["on"]
    else:
        try:
            value = int(mode)
        except ValueError:
            raise SystemExit(f"unknown sleep mode: {args.mode!r}")
    set_sleep(value)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aula-f75",
        description="Control AULA F75 keyboard lighting (wired or wireless).",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="list effects, sleep modes and adjustments").set_defaults(
        fn=_cmd_list
    )

    for alias in sorted(ALIASES):
        sp = sub.add_parser(alias, help=f"set the {alias} effect")
        sp.set_defaults(fn=lambda _a, _n=alias: set_effect(_n))

    sp = sub.add_parser("sleep", help="sleep mode / timeout (wireless only)")
    sp.add_argument("mode", help="off | on | <minutes>")
    sp.add_argument("timeout", nargs="?", type=int, default=None)
    sp.set_defaults(fn=_cmd_sleep)

    sp = sub.add_parser("color", help="fixed-on colour, hex RRGGBB (wireless only)")
    sp.add_argument("hex")
    sp.set_defaults(fn=lambda a: set_color(a.hex))

    sp = sub.add_parser("brightness", help="brightness 0-9 (wireless only)")
    sp.add_argument("level", type=int)
    sp.set_defaults(fn=lambda a: set_brightness(a.level))

    sp = sub.add_parser("colorful", help="colourful mode on/off (wireless only)")
    sp.add_argument("mode", choices=["on", "off"])
    sp.set_defaults(fn=lambda a: set_colorful(a.mode == "on"))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    fn = getattr(args, "fn", None)
    if fn is None:
        parser.print_help()
        return 1

    try:
        fn(args)
    except WirelessNotFound:
        print("Wireless AULA dongle not found.", file=sys.stderr)
        return 1
    except WiredNotFound:
        print("Wired AULA keyboard not found.", file=sys.stderr)
        return 1
    except DeviceNotFound:
        print("AULA keyboard not found.", file=sys.stderr)
        return 1
    except DeviceBusy as exc:
        print(f"Keyboard is busy: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 — CLI boundary: report, then exit
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.command != "list":
        print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
