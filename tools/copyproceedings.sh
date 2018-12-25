#!/bin/bash

sleep 2
mount /dev/sdf1 /media/usb1 || exit 1
mount /dev/sdg1 /media/usb2 || exit 1

cp proceedings-cla2015.pdf /media/usb1 &
cp proceedings-cla2015.pdf /media/usb2 &

wait
sync
umount /media/usb1
umount /media/usb2

sleep 2

echo "ok"
