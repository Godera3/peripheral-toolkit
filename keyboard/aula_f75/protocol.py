"""
protocol.py
===========
Pure byte-level protocol helpers for the AULA F75. No USB and no I/O beyond
reading the captured `.bin` blobs that ship in `fragments/`.

Wireless frames are 20-byte SET_REPORT payloads. A full command is 48 frames
(`wireless_sequence.bin`) and a sleep command is 11 (`sleep_sequence.bin`).
Byte 19 of every frame is a checksum: the low byte of the sum of bytes 0..18.
Each `patch_*` helper writes its field and then recomputes only that frame's
checksum — the captures are otherwise left byte-for-byte identical.
"""
from __future__ import annotations

import struct
from pathlib import Path

FRAG_DIR = Path(__file__).parent / "fragments"

WIRELESS_FRAG_LEN = 20
WIRELESS_FRAG_COUNT = 48

# 0-based frame indices inside the wireless sequence.
FRAG_COLOR = 1
FRAG_SLEEP = 2
FRAG_EFFECT_ID = 38
FRAG_PARAM_FLAG = 39
FRAG_BRIGHTNESS = 42
FRAG_COLORFUL = 42


def checksum(frag: bytes) -> int:
    """Byte 19 = (sum of bytes 0..18) mod 256. One scheme for every frame."""
    return sum(frag[:19]) & 0xFF


def _recalc(seq: bytearray, frag_index: int) -> None:
    off = frag_index * WIRELESS_FRAG_LEN
    seq[off + 19] = checksum(seq[off:off + 19])


def patch_effect_id(seq: bytearray, effect_id: int) -> None:
    """Write the effect code into frame 38, byte 15."""
    off = FRAG_EFFECT_ID * WIRELESS_FRAG_LEN
    seq[off + 15] = effect_id & 0xFF
    _recalc(seq, FRAG_EFFECT_ID)


def set_param_flag(seq: bytearray, flag: int = 0x28) -> None:
    """Write the 'parameter change' flag into frame 39, byte 15."""
    off = FRAG_PARAM_FLAG * WIRELESS_FRAG_LEN
    seq[off + 15] = flag & 0xFF
    _recalc(seq, FRAG_PARAM_FLAG)


def patch_color(seq: bytearray, r: int, g: int, b: int) -> None:
    """Write the fixed-on RGB triple into frame 1, bytes 12..14.

    From the colour-change capture. Bytes 15..17 are a separate entry and are
    deliberately left alone.
    """
    off = FRAG_COLOR * WIRELESS_FRAG_LEN
    seq[off + 12], seq[off + 13], seq[off + 14] = r & 0xFF, g & 0xFF, b & 0xFF
    _recalc(seq, FRAG_COLOR)


def patch_brightness(seq: bytearray, level: int) -> None:
    """Write the brightness level into frame 42, byte 7."""
    off = FRAG_BRIGHTNESS * WIRELESS_FRAG_LEN
    seq[off + 7] = level & 0xFF
    _recalc(seq, FRAG_BRIGHTNESS)


def patch_colorful(seq: bytearray, on: bool) -> None:
    """Write the colourful flag into frame 42, byte 8 (0x47 on / 0x40 off)."""
    off = FRAG_COLORFUL * WIRELESS_FRAG_LEN
    seq[off + 8] = 0x47 if on else 0x40
    _recalc(seq, FRAG_COLORFUL)


def patch_sleep(seq: bytearray, sleep_value: int) -> None:
    """Write the sleep value into frame 2, byte 15."""
    off = FRAG_SLEEP * WIRELESS_FRAG_LEN
    seq[off + 15] = sleep_value & 0xFF
    _recalc(seq, FRAG_SLEEP)


def _read(name: str) -> bytearray:
    return bytearray((FRAG_DIR / name).read_bytes())


def load_wireless_sequence() -> bytearray:
    return _read("wireless_sequence.bin")


def load_sleep_sequence() -> bytearray:
    return _read("sleep_sequence.bin")


def load_gaps(name: str = "wireless_gaps.bin") -> list[float] | None:
    """Inter-frame delays captured alongside a sequence, or None if absent."""
    path = FRAG_DIR / name
    if not path.exists():
        return None
    data = path.read_bytes()
    return list(struct.unpack(f"<{len(data) // 8}d", data))


def load_wired_fragments(effect_id: int) -> list[bytes]:
    """The three wired fragments for `effect_id`.

    Raises KeyError for an unknown effect code and FileNotFoundError if the
    capture is missing on disk.
    """
    from .effects import BY_CODE, WIRED_PREFIX

    effect = BY_CODE[effect_id]
    prefix = WIRED_PREFIX[effect_id]
    return [
        (FRAG_DIR / f"{prefix}{effect.wired_file}_frag{i}.bin").read_bytes()
        for i in range(3)
    ]
