import subprocess
import shutil

from pathlib import Path
from passlib.hash import lmhash
from partitions import get_fat_partition_offset
from contextlib import contextmanager

import re

def add_contents_to_card(device_name):
  print(device_name)
  disk_num=int(re.match(r"\\\\\.\\PHYSICALDRIVE(\d+)",device_name).group(1))
  print(disk_num)
  process_output=subprocess.run("diskpart.exe",input=
                 "select disk %d\nselect partition 1\nassign\nlist volume\nexit"%disk_num,capture_output=True,text=True)
  if process_output.returncode!=0:
     print(process_output.returncode)
     raise RuntimeError("Couldn't mount card") 
  else:
      lines=process_output.stdout.splitlines()
      drive_letter=None
      for x in lines:
        match=re.match(r"\* Volume \d+\s+([A-z]).*",x)
        if match:
           drive_letter=match.group(1)
           break
      if drive_letter is None:
         raise RuntimeError("Couldn't find drive letter")
      shutil.copytree("./contents",f"{drive_letter}:\\\\contents\\",dirs_exist_ok=True)
#      shutil.copytree("./contents",f"{drive_letter}:\\\\contents\\",dirs_exist_ok=True,ignore=shutil.ignore_patterns(".git"))
      shutil.copytree("./installscripts",f"{drive_letter}:\\",dirs_exist_ok=True,ignore=shutil.ignore_patterns(".git"))
      # make command line run install_contents.sh
      cmd_line=Path(f"{drive_letter}:\\") / "cmdline.txt"
      cmd_line_bak=Path(f"{drive_letter}:\\") / "cmdline.txt.original"
      if not cmd_line_bak.exists():
         shutil.copy(cmd_line,cmd_line_bak)
      cmd_line_text=cmd_line_bak.read_text().strip()
      cmd_line_text+=" systemd.run='bash /boot/install_contents.sh' systemd.run_success_action=reboot systemd.unit=kernel-command-line.target"
      cmd_line.write_text(cmd_line_text)
    
def create_wpa_supplicant(options):
    conf_file=Path(__file__).parent / "contents" / "etc"/ "wpa_supplicant"/"wpa_supplicant.conf"
    conf_file.parent.mkdir(exist_ok=True,parents=True)

    if options.labimage==True:
      shutil.copyfile("userconf.lab","installscripts/userconf")
      shutil.copyfile("wpa_supplicant.lab.conf",conf_file)
    else:
      shutil.copyfile("userconf.student.conf","installscripts/userconf")
      unihash=lmhash.hash(options.unipw)
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
    password=hash:%s
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
  """%(options.uniname,unihash,options.wifiname,options.wifipw),newline="\n")
