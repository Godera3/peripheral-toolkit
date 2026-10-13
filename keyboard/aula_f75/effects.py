"""
effects.py
==========
Single source of truth for the AULA F75 effect table.

Imported by both `cli.py` and (later) the PyQt frontend, so effect codes,
human names and the wired fragment filenames live in exactly one place.
Pure data + lookups — no USB, no I/O.

A note on `WIRED_PREFIX`
------------------------
The numeric prefix on the wired capture files follows *capture order*,
which is not effect-code order. The first two captures are `01_fixed_on`
(0x01) then `02_light_off` (0x00), because the board's power-on state was
captured first. Codes 0x09 and 0x0e are skipped by the protocol, and
`self_define` (0x15) was captured last as `17_`.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Effect:
    code: int
    name: str        # human label, e.g. "Fixed On"
    cli_alias: str   # canonical alias the CLI accepts, e.g. "fixed-on"
    wired_file: str  # wired fragment filename stem, e.g. "fixed_on"


EFFECTS: list[Effect] = [
    Effect(0x00, "Light Off",          "off",               "light_off"),
    Effect(0x01, "Fixed On",           "fixed-on",          "fixed_on"),
    Effect(0x02, "Respire",            "respire",           "respire"),
    Effect(0x03, "Rainbow",            "rainbow",           "rainbow"),
    Effect(0x04, "Flash Away",         "flash-away",        "flash_away"),
    Effect(0x05, "Raindrops",          "raindrops",         "raindrops"),
    Effect(0x06, "Rainbow Wheel",      "rainbow-wheel",     "rainbow_wheel"),
    Effect(0x07, "Ripples Shining",    "ripples-shining",   "ripples_shining"),
    Effect(0x08, "Stars Twinkle",      "stars-twinkle",     "stars_twinkle"),
    Effect(0x0a, "Retro Snake",        "retro-snake",       "retro_snake"),
    Effect(0x0b, "Neon Stream",        "neon-stream",       "neon_stream"),
    Effect(0x0c, "Reaction",           "reaction",          "reaction"),
    Effect(0x0d, "Sine Wave",          "sine-wave",         "sine_wave"),
    Effect(0x0f, "Rotating Windmill",  "rotating-windmill", "rotating_windmill"),
    Effect(0x10, "Colorful Waterfall", "colorful-waterfall", "colorful_waterfall"),
    Effect(0x11, "Blossoming",         "blossoming",        "blossoming"),
    # Present in the wired captures (17_self_define) but never captured over
    # the dongle, so it is reachable through the wired path only.
    Effect(0x15, "Self Define",        "self-define",       "self_define"),
]


# Every spelling the CLI accepts -> effect code. The canonical `cli_alias`
# above is always present; the extra rows are accepted synonyms.
ALIASES: dict[str, int] = {
    "off": 0x00,
    "fixed": 0x01, "fixed-on": 0x01,
    "respire": 0x02,
    "rainbow": 0x03,
    "flash-away": 0x04, "flashaway": 0x04,
    "raindrops": 0x05,
    "rainbow-wheel": 0x06, "rainbowwheel": 0x06,
    "ripples": 0x07, "ripples-shining": 0x07,
    "stars": 0x08, "stars-twinkle": 0x08,
    "retro-snake": 0x0a, "retrosnake": 0x0a,
    "neon": 0x0b, "neon-stream": 0x0b,
    "reaction": 0x0c,
    "sine-wave": 0x0d, "sinewave": 0x0d,
    "windmill": 0x0f, "rotating-windmill": 0x0f,
    "waterfall": 0x10, "colorful-waterfall": 0x10,
    "blossoming": 0x11,
    "self-define": 0x15,
}

BY_CODE: dict[int, Effect] = {e.code: e for e in EFFECTS}
NAME_BY_CODE: dict[int, str] = {e.code: e.name for e in EFFECTS}

# effect code -> numeric filename prefix on the wired capture files.
# Verified against `ls aula_f75/fragments/`; see the module docstring.
WIRED_PREFIX: dict[int, str] = {
    0x00: "02_",  # 02_light_off
    0x01: "01_",  # 01_fixed_on
    0x02: "03_",  # 03_respire
    0x03: "04_",  # 04_rainbow
    0x04: "05_",  # 05_flash_away
    0x05: "06_",  # 06_raindrops
    0x06: "07_",  # 07_rainbow_wheel
    0x07: "08_",  # 08_ripples_shining
    0x08: "09_",  # 09_stars_twinkle
    0x0a: "10_",  # 10_retro_snake
    0x0b: "11_",  # 11_neon_stream
    0x0c: "12_",  # 12_reaction
    0x0d: "13_",  # 13_sine_wave
    0x0f: "14_",  # 14_rotating_windmill
    0x10: "15_",  # 15_colorful_waterfall
    0x11: "16_",  # 16_blossoming
    0x15: "17_",  # 17_self_define
}
