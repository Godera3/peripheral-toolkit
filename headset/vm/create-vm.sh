#!/usr/bin/env bash
# Builds the Windows 10 RE guest: 1532:0574 dongle gets passed through by hand
# once Windows is up, so the xHCI controller is added here rather than later.
set -euo pipefail

VM=win10-re
ISO_DIR=$HOME/VMs/iso
DISK_DIR=$HOME/VMs/disks
WIN_ISO=${1:-$(ls -1t "$ISO_DIR"/Win10*_x64*.iso 2>/dev/null | head -1 || true)}

[[ -n ${WIN_ISO:-} && -f $WIN_ISO ]] || { echo "no Windows 10 ISO in $ISO_DIR"; exit 1; }
virsh --connect qemu:///system dominfo "$VM" >/dev/null 2>&1 && { echo "$VM already defined"; exit 1; }

mkdir -p "$DISK_DIR"
[[ -f $DISK_DIR/$VM.qcow2 ]] || qemu-img create -f qcow2 "$DISK_DIR/$VM.qcow2" 60G

# 4 vCPU / 6 GB — the host has 15 GB and needs to stay usable while a capture runs.
# SATA + e1000e on purpose: both drivers ship in Windows 10, so setup needs no
# driver ISO. The virtio-win download trickles at ~68 KB/s and is not worth an
# install blocker; add it later only for clipboard/folder sharing.
virt-install --connect qemu:///system \
  --name "$VM" \
  --osinfo win10 \
  --machine q35 --boot uefi \
  --cpu host-passthrough --vcpus 4 --memory 6144 \
  --disk "path=$DISK_DIR/$VM.qcow2,format=qcow2,bus=sata,cache=writeback,discard=unmap" \
  --cdrom "$WIN_ISO" \
  --network network=default,model=e1000e \
  --controller usb,model=qemu-xhci \
  --graphics spice,listen=127.0.0.1,clipboard.copypaste=yes \
  --video qxl \
  --noautoconsole

echo
echo "Guest defined. Open it with:  virt-manager --connect qemu:///system"
