"""
protocol.py
===========
Byte-level framing for the Barracuda X Chroma.
"""
def checksum(data: bytes) -> int:
    c = 0
    for b in data[0:62]:
        c ^= b
    return c

def build_set(prop_id: int, data: bytes = b"") -> bytes:
    buf = bytearray(64)
    buf[0] = 0x02       # Report ID
    buf[2] = 0x60       # Razer magic
    buf[6] = len(data) + 4 # LEN: (80 + PROP + 00 + DATALEN) = 4 bytes + data
    buf[9] = 0x80
    buf[10] = prop_id | 0x80 # SET flag
    buf[12] = len(data)      # DATALEN
    
    if data:
        buf[13:13+len(data)] = data
        
    buf[62] = checksum(buf)
    return bytes(buf)

def build_get(prop_id: int) -> bytes:
    buf = bytearray(64)
    buf[0] = 0x02
    buf[2] = 0x60
    buf[6] = 0x04  # LEN: (80 + PROP + 00 + 00) = 4 bytes
    buf[9] = 0x80
    buf[10] = prop_id
    buf[62] = checksum(buf)
    return bytes(buf)
