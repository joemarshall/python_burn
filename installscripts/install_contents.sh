#!/bin/bash

SCRIPT_PATH=$(dirname "$0")

mount -o remount,rw /
# copy etc/rc.local from contents 
# this will run init_task.sh on next boot
cp -f $SCRIPT_PATH/contents/etc/rc.local /etc/rc.local

mount -o remount,rw,fmask=0777,dmask=0777 $SCRIPT_PATH
# remove our systemd call command line
/usr/bin/sed -i 's| systemd.run.*||g' $SCRIPT_PATH/cmdline.txt
mount -o remount,ro $SCRIPT_PATH
mount -o remount,ro /
sync
sleep 5
reboot -f
sleep 5
exit 0

