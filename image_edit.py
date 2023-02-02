import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from passlib.hash import lmhash
from partitions import get_fat_partition_offset
from contextlib import contextmanager
import struct
import re
import os
import stat


def hard_delete(redo_function, path, excinfo):
    if os.path.exists(path):
        os.chmod(path, stat.S_IWRITE)
    redo_function(path)


def add_contents_to_card(device_name):
    volume_re = r"\* Volume \d+\s+([A-z]).*"
    print(device_name)
    disk_num = int(
        re.match(r"\\\\\.\\PHYSICALDRIVE(\d+)", device_name).group(1))
    print(disk_num)
    process_output = subprocess.run(
        "diskpart.exe", input="select disk %d\nonline disk\nselect partition 1\nlist volume\nexit" % disk_num, capture_output=True, text=True)
    print("***", process_output.stdout.splitlines())
    drive_letter = None
    for x in process_output.stdout.splitlines():
        match = re.match(volume_re, x)
        if match:
            drive_letter = match.group(1)
            break
    print(f"Found drive letter straight away: {drive_letter}")
    if drive_letter is None:
        process_output = subprocess.run(
            "diskpart.exe", input="select disk %d\nonline disk\nselect partition 1\nassign\nlist volume\nexit" % disk_num, capture_output=True, text=True)
        if process_output.returncode != 0:
            print(process_output.returncode)
            raise RuntimeError("Couldn't mount card")
        else:
            lines = process_output.stdout.splitlines()
            drive_letter = None
            for x in lines:
                match = re.match(r"\* Volume \d+\s+([A-z]).*", x)
                if match:
                    drive_letter = match.group(1)
                    break
    if drive_letter is None:
        raise RuntimeError("Couldn't find drive letter")
    print("Drive letter:", drive_letter)
    add_contents_to_mounted_drive(drive_letter)


def add_contents_to_mounted_drive(drive_letter):
    if os.path.exists(f"{drive_letter}:\\contents"):
        shutil.rmtree(f"{drive_letter}:\\contents", onerror=hard_delete)
    if os.path.exists(f"{drive_letter}:\\installscripts"):
        shutil.rmtree(f"{drive_letter}:\\installscripts", onerror=hard_delete)
    shutil.copytree(
        "./contents", f"{drive_letter}:\\contents\\", dirs_exist_ok=True)
#      shutil.copytree("./contents",f"{drive_letter}:\\\\contents\\",dirs_exist_ok=True,ignore=shutil.ignore_patterns(".git"))
    shutil.copytree("./installscripts", f"{drive_letter}:\\",
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git"))
    # make command line run install_contents.sh
    cmd_line = Path(f"{drive_letter}:\\") / "cmdline.txt"
    cmd_line_text = cmd_line.read_text().strip()
    cmd_line_text = re.sub(r" systemd.\S+", "", cmd_line_text)
    cmd_line_text += " systemd.run=/boot/install_contents.sh systemd.run_success_action=reboot systemd.run_failure_action=reboot "
    cmd_line.write_text(cmd_line_text, newline="\n")
    print(cmd_line, cmd_line_text)

    # enable UART on GPIO pins for debug purposes
    config_file = Path(f"{drive_letter}:\\config.txt")
    config_txt = config_file.read_text()
    new_config_txt = ""
    found_setting = False
    for line in config_txt.splitlines():
        match = re.match("\s*(\w+)\s*=([^#]*)", line)
        if match:
            k, v = match.groups()
            if k == "enable_uart":
                if v == "1":
                    found_setting = True
                else:
                    # skip bad setting
                    continue
        new_config_txt += line+"\n"
    if not found_setting:
        new_config_txt += "enable_uart=1\n"
    config_file.write_text(new_config_txt, newline="\n")
    # write burn date file to /boot
    burndate_file = Path(f"{drive_letter}:\\burning-date.txt")
    burndate_file.write_text("")
    # write image date file to /boot as git date of startup scripts folder

    git_date_result = subprocess.run(["git", "show", "-s", "--format=%ci"], capture_output=True, cwd=Path(
        ".") / "contents" / "home" / "pi" / "grove-startup-scripts", text=True)
    git_time = datetime.strptime(
        git_date_result.stdout.strip(), "%Y-%m-%d %H:%M:%S %z")
    imgdate_file = Path(f"{drive_letter}:\\image-date.txt")
    imgdate_file.write_text(git_time.strftime("%d%m%Y"))


def create_wpa_supplicant(options):
    conf_file = Path(__file__).parent / "installscripts" / \
        "wpa_supplicant.conf"
    conf_file.parent.mkdir(exist_ok=True, parents=True)

    if options.labimage == True:
        shutil.copyfile("userconf.lab.conf", "installscripts/userconf.txt")
        shutil.copyfile("wpa_supplicant.lab.conf", conf_file)
    else:
        shutil.copyfile("userconf.student.conf", "installscripts/userconf.txt")
        if options.hash:
            unipw = "hash:"+lmhash.hash(options.unipw)
        else:
            unipw = f'"{options.unipw}"'
        conf_file.write_text("""
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
country=GB
    
network={
  ssid="MRTHotspot"
  proto=RSN
  key_mgmt=WPA-PSK
  pairwise=CCMP TKIP
  group=CCMP TKIP
  psk="MRTHotspot"
}

network={
  ssid="eduroam"
  key_mgmt=WPA-EAP
  pairwise=CCMP
  group=CCMP TKIP
  eap=PEAP
  identity="%s@nottingham.ac.uk"
  domain_suffix_match="radius.nottingham.ac.uk"
  phase2="auth=MSCHAPV2"
  password=%s
  anonymous_identity="anonymous@nottingham.ac.uk"
}

network={
ssid="%s"
proto=RSN
key_mgmt=WPA-PSK
pairwise=CCMP TKIP
group=CCMP TKIP
psk="%s"
}
""" % (options.uniname, unipw, options.wifiname, options.wifipw), newline="\n")


def pack_4(value):
    pack = [b for b in struct.pack(b">L", value)]
    return pack


def pack_8(value):
    pack = [b for b in struct.pack(b">Q", value)]
    return pack


def vhd_chs(size):
    # CHS calculation as defined by the VHD spec
    sectors = divro(size, 512)

    if sectors > (65535 * 16 * 255):
        sectors = 65535 * 16 * 255

    if sectors >= 65535 * 16 * 63:
        spt = 255
        cth = sectors / spt
        heads = 16
    else:
        spt = 17
        cth = sectors / spt
        heads = (cth + 1023) / 1024

        if heads < 4:
            heads = 4

        if (cth >= (heads * 1024)) or (heads > 16):
            spt = 31
            cth = sectors / spt
            heads = 16

        if cth >= (heads * 1024):
            spt = 63
            cth = sectors / spt
            heads = 16

    cylinders = cth / heads

    return (cylinders, heads, spt)

# in windows you can mount a fat partition from an image if it is a vhd file


def add_vhd_footer(img_file):
    # append VHD fixed footer for this file
    img_path = Path(img_file)
    remove_vhd_footer(img_file)
    img_size = img_path.stat().st_size
    with open(img_path, "ab") as img:
        ftr = []
        ftr.extend([ord(c) for c in "conectix"])
        ftr.extend([0, 0, 0, 0])  # features = zero
        ftr.extend([0, 1, 0, 0])  # version 1.0
        # data offset -1 for fixed disks
        ftr.extend([0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff])
        ftr.extend([0, 0, 0, 0])  # arbitrary time stamp
        ftr.extend([ord('p'), ord('i'), ord('m'), 0])  # creator name
        ftr.extend([0, 1, 0, 0x03])  # creator version
        ftr.extend([0, 0, 0, 0])  # creator OS = windows
#        ftr.extend([0x57, 0x69, 0x32, 0x6B])  # creator OS = windows
        ftr.extend(pack_8(img_size))  # original size
        ftr.extend(pack_8(img_size))  # current size
        sectors = 1
        cylinders = img_size//512
        heads = 1
        divisor = 2
        while cylinders >= 32768:
            if cylinders % divisor == 0:
                if heads < 16:
                    heads *= divisor
                    cylinders //= divisor
                elif sectors < 128:
                    sectors *= divisor
                    cylinders //= divisor
                elif heads <= 128:
                    heads *= divisor
                    cylinders //= divisor
            else:
                print(cylinders, heads, sectors, divisor)
                divisor += 1
        print(cylinders, heads, sectors, img_size, cylinders*heads*sectors*512)
        # cylinder x 2 bytes, heads, sectors
        ftr.extend([(cylinders >> 8) & 0xff, cylinders & 0xff, heads, sectors])
        ftr.extend([0, 0, 0, 2])  # disk type 1 (hd, fixed)
        checksum_pos = len(ftr)
        ftr.extend([0, 0, 0, 0])  # checksum
        ftr.extend([0x80, 0x5d, 0xa5, 0x3e, 0xa2, 0x25, 0x11, 0xed,
                   0xa8, 0xfc, 0x02, 0x42, 0xac, 0x12, 0x00, 0x02])  # UID
        ftr.extend([0])
        ftr.extend([0]*427)
        assert (len(ftr) == 512)
        out_bytes = bytes(ftr)
        # checksum
        checksum = 0
        for b in out_bytes:
            checksum += b
        checksum = checksum ^ 0xffffffff
        ftr[checksum_pos:checksum_pos+4] = pack_4(checksum)
        out_bytes = bytes(ftr)
        img.write(out_bytes)
        # now disk has a virtual disk footer so it can be mounted as disk

# if there is a vhd footer, remove it


def remove_vhd_footer(img_file):
    img_path = Path(img_file)
    # first check for VHDK header
    with open(img_path, "r+b") as img:
        img.seek(-512, 2)
        hdr = img.read(512)
        if hdr[28:32] == b'pim\x00':
            img.seek(-512, 2)
            img.truncate()


@contextmanager
def mount_image_fat(img_file):
    # make the img file a vhd file
    orig_path = Path(img_file).absolute()
    img_path = Path(orig_path)
    if not img_path.name.endswith(".vhd"):
        img_path = Path(str(orig_path)+".vhd")
        orig_path.rename(img_path)
    try:
        add_vhd_footer(img_path)
        # mount it using diskpart
        volume_re = r"\* Volume \d+\s+([A-z]).*"
        print('select vdisk FILE="%s"\nattach vdisk\nassign\nselect partition 1\nlist volume\nexit' % str(img_path))
        process_output = subprocess.run(
            "diskpart.exe", input='select vdisk FILE="%s"\nattach vdisk\nassign\nselect partition 1\nlist volume\nexit' % str(img_path), capture_output=True, text=True)
        drive_letter = None
        for x in process_output.stdout.splitlines():
            match = re.match(volume_re, x)
            if match:
                drive_letter = match.group(1)
                break
        print("Found drive letter:", drive_letter)
        try:
            yield drive_letter
        finally:
            process_output = subprocess.run(
                "diskpart.exe", input='select vdisk FILE="%s"\ndetach vdisk\nexit' % str(img_path), capture_output=True, text=True)
            remove_vhd_footer(img_path)
    finally:
        # rename back (in separate block in case diskpart fails)
        if orig_path != img_path:
            img_path.rename(orig_path)


if __name__ == "__main__":
    from imager import DataHolder
    dataholder=DataHolder(burner=None)
    dataholder.labimage=False
    dataholder.wifipw="<YOUR_WIFI_PASSWORD>"
    dataholder.wifiname="<YOUR WIFI NAME>"
    dataholder.uniname="<YOUR_UNI_NAME e.g. pszjm2>@nottingham.ac.uk"
    dataholder.unipw="<YOUR UNI PASSWORD>"
    dataholder.hash=False
    create_wpa_supplicant(dataholder)

    with mount_image_fat("2022-09-22-raspios-bullseye-armhf-lite.img.patched.230201.img") as drive_letter:
        print(os.listdir("%s:" % drive_letter))
#        add_contents_to_mounted_drive(drive_letter)
        print(Path("%s:\\wpa_supplicant.conf" % drive_letter).read_text())
