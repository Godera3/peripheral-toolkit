#!/usr/bin/env python3
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from headset import core

def main():
    parser = argparse.ArgumentParser(description="Razer Barracuda X Chroma Linux CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("battery", help="Get current battery percentage")
    subparsers.add_parser("listen", help="Listen for physical button presses")
    subparsers.add_parser("lights-off", help="Turn off the Chroma lighting")
    subparsers.add_parser("lights-on", help="Turn on the Chroma lighting")

    eq_parser = subparsers.add_parser("eq", help="Set the EQ preset")
    eq_parser.add_argument("mode", choices=["game", "music", "movie", "custom"], help="EQ Mode")

    args = parser.parse_args()

    try:
        if args.command == "battery":
            bat = core.get_battery()
            print(f"Battery: {bat}%")
        elif args.command == "listen":
            core.listen_events()
        elif args.command == "lights-off":
            core.set_lights_off()
            print("Lights turned off.")
        elif args.command == "lights-on":
            core.set_lights_on()
            print("Lights turned on.")
        elif args.command == "eq":
            core.set_eq(args.mode)
            print(f"EQ set to {args.mode}.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
