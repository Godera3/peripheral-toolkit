#!/usr/bin/env python3
"""Replay exact SET_REPORT bytes from a wireless pcapng capture."""
import sys, subprocess, time, usb.core, usb.util

if len(sys.argv) != 2:
    print("Usage: replay_capture.py <pcapng>")
    sys.exit(1)

pcap = sys.argv[1]

# Extract SET_REPORT data and timestamps
cmd = ['tshark', '-r', pcap, '-Y', 'usb.transfer_type == 0x02 && usb.data_len == 28',
       '-T', 'fields', '-e', 'frame.time_relative', '-e', 'usb.data_fragment']
out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)

records = []
for line in out.strip().split('\n'):
    if not line.strip():
        continue
    t_str, data = line.split('\t')
    records.append((float(t_str), bytes.fromhex(data.replace(':', ''))))

print(f'Replaying {len(records)} SET_REPORT transfers from {pcap}')

dev = usb.core.find(idVendor=0x3554, idProduct=0xfa09)
if dev is None:
    print('Wireless dongle not found')
    sys.exit(1)

iface = 1
if dev.is_kernel_driver_active(iface):
    dev.detach_kernel_driver(iface)

try:
    base_time = None
    for i, (t, data) in enumerate(records):
        if base_time is None:
            base_time = time.time()
            target_time = base_time
        else:
            target_time = base_time + (t - records[0][0])
        sleep_time = target_time - time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
        n = dev.ctrl_transfer(0x21, 0x09, (0x02 << 8) | 0x13, 1, data, 5000)
        if n != len(data):
            print(f'Warning: fragment {i} transferred {n} bytes instead of {len(data)}')
finally:
    usb.util.dispose_resources(dev)

print('Done')
