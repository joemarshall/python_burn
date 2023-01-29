#!/bin/bash

set +e 


# copy all of contents to where it should be (i.e. on main fs)
cp -rf /boot/contents/* /

# remove our systemd call command line assuming everything above worked
sed -i 's| systemd.run.*||g' /boot/cmdline.txt
