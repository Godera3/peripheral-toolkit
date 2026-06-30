#!/bin/sh
# Restore usbhid driver to AULA F75 dongle interface 1
# Retries with delay in case USB subsystem is busy
for i in 1 2 3; do
    echo "1-5:1.1" > /sys/bus/usb/drivers/usbhid/bind 2>/dev/null && exit 0
    sleep 0.3
done
exit 1
