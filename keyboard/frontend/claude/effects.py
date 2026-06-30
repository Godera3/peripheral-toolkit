"""
effects.py
==========
Static table of the 16 documented effects. Kept as data rather than parsed
from `aula-f75 list` output at runtime — the GUI needs to be populated
before any subprocess call completes, and effect codes are part of the
documented CLI contract, not something expected to change underneath it.

Each entry also carries an `anim` hint consumed by EffectSwatch (see
widgets.py) to drive a small live color preview that's actually true to
what the effect does, rather than a static color chip.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Effect:
    code: int
    name: str
    primary_alias: str  # the alias sent to the backend on apply
    anim: str  # preview animation style, see widgets.EffectSwatch


EFFECTS: list[Effect] = [
    Effect(0x00, "Light Off", "off", "off"),
    Effect(0x01, "Fixed On", "fixed-on", "solid"),
    Effect(0x02, "Respire", "respire", "breathe"),
    Effect(0x03, "Rainbow", "rainbow", "hue-cycle"),
    Effect(0x04, "Flash Away", "flash-away", "flash"),
    Effect(0x05, "Raindrops", "raindrops", "sparkle-random"),
    Effect(0x06, "Rainbow Wheel", "rainbow-wheel", "hue-sweep"),
    Effect(0x07, "Ripples Shining", "ripples-shining", "ripple"),
    Effect(0x08, "Stars Twinkle", "stars-twinkle", "sparkle-soft"),
    Effect(0x0A, "Retro Snake", "retro-snake", "chase"),
    Effect(0x0B, "Neon Stream", "neon-stream", "stream"),
    Effect(0x0C, "Reaction", "reaction", "sparkle-random"),
    Effect(0x0D, "Sine Wave", "sine-wave", "wave"),
    Effect(0x0F, "Rotating Windmill", "rotating-windmill", "spin"),
    Effect(0x10, "Colorful Waterfall", "colorful-waterfall", "stream"),
    Effect(0x11, "Blossoming", "blossoming", "bloom"),
]

EFFECTS_BY_CODE: dict[int, Effect] = {e.code: e for e in EFFECTS}
