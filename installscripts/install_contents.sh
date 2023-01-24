cd /

bb="/PiBakery/busybox"

mount="$bb mount"
umount="$bb umount"
mkdir="$bb mkdir"
mknod="$bb mknod"
sync="$bb sync"
cat="$bb cat"
cp="$bb cp"
rm="$bb rm"
rmdir="$bb rmdir"
reboot="$bb reboot"
sleep="$bb sleep"
echo="$bb echo"
mv="$bb mv"

# Mount root filesystem as writable, then create a tmpfs directory in which we
# can create the device nodes we need to access the root partition
$mount -o remount,rw / / # Two slashes are essential!
$mkdir /tmp
$mkdir /root
$mount -t tmpfs tmpfs /tmp

# Access the root fs
$mknod /tmp/mmcblk0p2 b 179 2
$mount -o rw -t ext4 /tmp/mmcblk0p2 /root

# copy all of contents to where it should be
cp -r /contents /

# Sync and unmount root fs
$sync
$umount /root
$rmdir /root

# Remove device node and tmp dir
$rm /tmp/mmcblk0p2
$umount /tmp
$rmdir /tmp

# Reset cmdline.txt back to the original version
$rm -f /cmdline.txt
$mv -f /cmdline.txt.original /cmdline.txt

# Sync filesystems, mount read-only, and reboot
$sync
$mount -o remount,ro /
$sync

$sleep 2
$reboot -f