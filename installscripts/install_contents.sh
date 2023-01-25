# Mount root filesystem as writable, then create a tmpfs directory in which we
# can create the device nodes we need to access the root partition

# copy all of contents to where it should be (i.e. on main fs)
cp -rf /boot/contents/* /

if test -f "/boot/cmdline.txt.original"; then
  cp -f /boot/cmdline.txt.original /cmdline.txt
fi

sleep 2
reboot -f