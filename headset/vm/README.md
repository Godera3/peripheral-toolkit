# Windows 10 RE guest

Synapse 4 + Chroma run here and nowhere else. The point is ground truth for
`1532:0574`: what Synapse actually sends, byte for byte, so the Linux side can
be diffed against it instead of guessed at.

Razer ships a signed kernel driver with Synapse (`rzpnk.sys` family — the class
of driver that has been abused for BYOVD attacks and is blacklisted on Linux).
A throwaway guest is the only place it should ever be installed.

## Host side

| Item | Value |
| --- | --- |
| Stack | QEMU 8.2.2 / libvirt 10.0 / virt-manager 4.1 (apt, Ubuntu noble) |
| Guest | Windows 10 22H2 x64, `win10-re` |
| RAM / vCPU | 6144 MB / 4 |
| Disk | `~/VMs/disks/win10-re.qcow2`, 60 GB qcow2, **SATA** (in-box driver) |
| Network | libvirt `default` NAT (192.168.122.0/24), **e1000e** — Synapse needs a Razer ID login once |
| ISO dir | `~/VMs/iso/` — `Win10_22H2_English_x64*.iso` |

SATA and e1000e are deliberate: both drivers are in the Windows 10 image, so
setup needs no third CD. virtio-win trickles from fedorapeople at ~68 KB/s here;
it is only worth adding later for clipboard and folder sharing, neither of which
blocks a capture session.

Build it: `./create-vm.sh` (idempotent guard: refuses if the domain already exists).

## Install

1. `virt-manager --connect qemu:///system`, open `win10-re`.
2. Product key: skip. Edition: **Windows 10 Pro**, custom install, single 60 GB disk.
3. At "Let's connect you to a network", pick **I don't have internet → Continue
   with limited setup** so you get a local account instead of a Microsoft one.
4. Check the NIC works: `ipconfig` shows a 192.168.122.x lease from dnsmasq.

## Snapshots

`virsh snapshot-create-as win10-re <name> --description "..."` — **qcow2 only,
take them at these four points**:

| Name | When |
| --- | --- |
| `clean-os` | Windows installed, guest tools on, nothing else |
| `pre-synapse` | capture tooling installed (USBPcap, Wireshark, procmon, 7-Zip) |
| `synapse-installed` | Synapse 4 + Chroma installed and logged in, before touching any setting |
| `per-experiment` | optional, if one captures trashes a setting you need reverted |

Revert with `virsh snapshot-revert win10-re clean-os`.

## Dongle passthrough

1. Headset on and paired over 2.4 GHz, dongle in a USB port.
2. In the VM window: **Virtual Machine → Redirect USB device → `1532:0574`**.
3. Linux loses the dongle (and its audio) until you un-redirect. That is
   expected — a capture session needs the host out of the way.

libvirt detaches `snd-usb-audio` / `usbhid` from the host automatically. If
redirect ever fails, `sudo systemctl restart libvirtd` and re-plug.

## Capture

Inside the guest: **USBPcap** (installs a filter driver during Wireshark setup —
tick "Install USBPcap") then Wireshark on the `USBPcap1` interface filtered with
`usb.idVendor == 0x1532`. Audio isochronous traffic floods the capture; the
vendor HID interface is where everything interesting lives.

Get captures out to Linux without guest tools: run
`python3 -m http.server 8000` in the folder holding the pcaps on the host, then
open `http://192.168.122.1:8000/` in the guest's browser and save them back to
Linux. (Once virtio-win lands, `virtio-win-guest-tools.exe` adds clipboard and
drag-and-drop and this becomes unnecessary.) Decode on the host:

```bash
tshark -r session.pcapng -Y 'usb.idVendor == 0x1532' \
  -T fields -e frame.number -e usb.src -e usb.dst -e usb.capdata
```

Keep the experiment order in `../captures/PLAN.md` — one Synapse action per
capture file, or the pcaps become unreadable.
