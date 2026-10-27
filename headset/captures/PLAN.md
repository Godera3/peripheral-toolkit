# Capture plan — Barracuda X Chroma (`1532:0574`) under Synapse 4

Method: one Synapse action per capture file, named `NN_<action>.pcapng`, all in
`headset/captures/`. Two actions in one file and the pcaps stop being readable.

Before the first capture: revert the `synapse-installed` snapshot, and set every
control to a known state (EQ Custom flat, sidetone off, power-save 15 min, DND
off, lighting on at full brightness), so each later change produces exactly one
delta.

## What is already documented (verify, don't rediscover)

From openrazer#2704 — two owners on this PID, one of them with a Synapse 4 +
USBPcap capture on Windows 11.

Unsolicited events, report ID `0x02`, vendor page `0xFF14`:

```
02 0A 60 <seq> 00 00 05 00 80 80 <PROP> 02 01 <VALUE> ...
byte 62 = XOR(bytes[1..61])
```

| PROP | Meaning |
| --- | --- |
| `0x20` | dongle link (01 reachable / 00 off or on Bluetooth) |
| `0x21` | battery percent |
| `0x27` | do not disturb |
| `0x2A` | actively charging |
| `0x40` | lighting state (00 off / 0C on) |
| `0x55` | mic mute |
| `0x13` | EQ preset (FF custom, 07 game, 08 music, 09 movie) |

Host → device framing:

```
GET  02 00 60 00 00 00 04 00 00 80 <PROP>
SET  02 00 60 00 00 00 <LEN> 00 00 80 <PROP|0x80> 00 <DATALEN> <DATA...>
byte 62 = XOR(bytes[0..61])
```

## The five things worth the VM

1. **Does the firmware accept SET at all?** Earlier Linux attempts on this
   device got silence for every host→device write. A Synapse capture proves the
   frame; our own test must prove the device obeys it. Start here — if SET
   works, the whole toolkit gets bidirectional.
2. **Full property map.** Only ~12 IDs are known out of a space that is clearly
   larger (`0x13` EQ, `0x15` curve, `0x18`/`0x19` sidetone, `0x2C` power-save,
   `0x40` lighting…). Every unaccounted UI control in Synapse is a candidate
   new ID, and each one captures as a clean `SET`.
3. **Lighting: who computes the effects?** The RGB is plain HID LampArray
   (usage page `0x59`, reports `0x31`–`0x36`). Synapse computes and streams.
   Capture "Quick Effects" and see whether audio-reactive/ambient modes arrive
   as `0x34` LampMultiUpdate streams at a fixed rate (host-side, easy to
   reproduce) or as vendor `0x02` writes (firmware, needs reversing).
4. **Dongle / headset firmware query.** openbarracuda found a firmware-version
   read on the sibling dongle (`0x0584`). If `0574` answers one too, the toolkit
   can log firmware revisions — useful, because every byte in this table may
   drift between revisions.
5. **Binding of `0x40` lighting state.** Whether the toolkit can switch lighting
   off over the dongle without touching LampArray, and whether that state
   survives a headset power cycle.

## Experiment list

Ordered cheapest first; each row is one capture file.

| # | In Synapse / Chroma | Delta expected | Proves |
| --- | --- | --- | --- |
| 01 | Start Synapse with headset already connected, touch nothing | `0x20`→`0x27`→`0x55`→`0x21` burst | connect snapshot exists on our firmware |
| 02 | Poll battery: settings → power tab, leave open 3 min | `0x21` repeats every ~60 s | heartbeat interval |
| 03 | Plug the USB-C cable in, let it reach 100 % | `0x2A` 01 → 00 with cable attached | "charging" ≠ "plugged" |
| 04 | Press mic-mute on the earcup, then Synapse's mic mute toggle | `0x55` both ways | who drives mute: HID or UAC `SET_CUR` |
| 05 | Cycle EQ preset Game → Music → Movie → Custom | `0x13` = 07/08/09/FF | preset IDs |
| 06 | Move one EQ band (31 Hz) +1, then back | `0x15`/`0x95`, 10 signed int8 | curve payload layout |
| 07 | Sidetone on, slider 0 → 50 → 100 %, off | `0x18`/`0x98`, `0x19`/`0x99` | mapping of the 0–15 scale |
| 08 | Wireless power saving 15 → 30 → off | `0x2C`/`0xAC` = 0F/1E/00 | minute encoding |
| 09 | DND toggle in the Razer Audio mobile app (Bluetooth), re-dongle | `0x27` | which side owns DND |
| 10 | Chroma: static single colour, all 6 lamps | `0x36` autonomous 0, `0x34` multi-update | LampArray host mode |
| 11 | Chroma: brightness 100 → 50 → 0 | `0x34` values only? | brightness vs `0x40` |
| 12 | Chroma: Wave effect, 10 s | rate + frame shape of `0x34` | host-computed effects |
| 13 | Chroma: audio-reactive / ambient, 10 s | same, plus audio path | whether the app reads WASAPI |
| 14 | Headset power off, wait, power on | `0x20` 00 → 01 | liveness signal, not USB presence |
| 15 | Toggle "lighting off when display sleeps" | any host- or firmware-side write | Synapse policy vs device setting |

## After each capture

```bash
tshark -r 05_eq.pcapng -Y 'usb.idVendor == 0x1532' \
  -T fields -e frame.number -e usb.src -e usb.dst -e usb.capdata > 05_eq.txt
```

Diff the extracted frames against the table above; anything that does not match
is new, and belongs in `PROTOCOL.md` next to this file.
