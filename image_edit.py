import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from passlib.hash import lmhash
from partitions import get_fat_partition_offset
from contextlib import contextmanager

import re
import os
import stat

def hard_delete(redo_function,path,excinfo):
    if os.path.exists(path):
      os.chmod(path ,stat.S_IWRITE)
    redo_function(path)
   

def add_contents_to_card(device_name):
  volume_re=r"\* Volume \d+\s+([A-z]).*"
  print(device_name)
  disk_num=int(re.match(r"\\\\\.\\PHYSICALDRIVE(\d+)",device_name).group(1))
  print(disk_num)
  process_output=subprocess.run("diskpart.exe",input=
                 "select disk %d\nselect partition 1\nlist volume\nexit"%disk_num,capture_output=True,text=True)
  print("***",process_output.stdout.splitlines())
  drive_letter=None
  for x in process_output.stdout.splitlines():
     match=re.match(volume_re,x)
     if match:
        drive_letter=match.group(1)
        break
  print(f"Found drive letter straight away: {drive_letter}")
  if drive_letter is None:
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
  print("Drive letter:",drive_letter)
  if os.path.exists(f"{drive_letter}:\\contents"):
    shutil.rmtree(f"{drive_letter}:\\contents",onerror=hard_delete)
  if os.path.exists(f"{drive_letter}:\\installscripts"):
    shutil.rmtree(f"{drive_letter}:\\installscripts",onerror=hard_delete)
  shutil.copytree("./contents",f"{drive_letter}:\\contents\\",dirs_exist_ok=True)
#      shutil.copytree("./contents",f"{drive_letter}:\\\\contents\\",dirs_exist_ok=True,ignore=shutil.ignore_patterns(".git"))
  shutil.copytree("./installscripts",f"{drive_letter}:\\",dirs_exist_ok=True,ignore=shutil.ignore_patterns(".git"))
  # make command line run install_contents.sh
  cmd_line=Path(f"{drive_letter}:\\") / "cmdline.txt"
  cmd_line_text=cmd_line.read_text().strip()
  cmd_line_text=re.sub(r" systemd.\S+","",cmd_line_text)
  cmd_line_text+=" systemd.run=/boot/install_contents.sh systemd.run_success_action=reboot systemd.run_failure_action=reboot "
  cmd_line.write_text(cmd_line_text,newline="\n")
  print(cmd_line,cmd_line_text)

  # enable UART on GPIO pins for debug purposes
  config_file=Path(f"{drive_letter}:\\config.txt")
  config_txt=config_file.read_text()
  new_config_txt=""
  found_setting=False
  for line in config_txt.splitlines():
    match=re.match("\s*(\w+)\s*=([^#]*)",line)
    if match:
       k,v=match.groups()
       if k=="enable_uart":
          if v=="1":
             found_setting=True
          else:
             # skip bad setting
             continue
    new_config_txt+=line+"\n"
  if not found_setting:
     new_config_txt+="enable_uart=1\n"
  config_file.write_text(new_config_txt,newline="\n")
  # write burn date file to /boot
  burndate_file=Path(f"{drive_letter}:\\burning-date.txt")
  burndate_file.write_text("")
  # write image date file to /boot as git date of startup scripts folder
  
  git_date_result=subprocess.run(["git","show","-s","--format=%ci"],capture_output=True,cwd=Path(".") / "contents" / "home" / "pi" / "grove-startup-scripts",text=True)
  git_time=datetime.strptime(git_date_result.stdout.strip(), "%Y-%m-%d %H:%M:%S %z")
  imgdate_file=Path(f"{drive_letter}:\\image-date.txt")
  imgdate_file.write_text(git_time.strftime("%d%m%Y"))
    
def create_wpa_supplicant(options):
    conf_file=Path(__file__).parent / "installscripts" / "wpa_supplicant.conf"
    conf_file.parent.mkdir(exist_ok=True,parents=True)

    if options.labimage==True:
      shutil.copyfile("userconf.lab.conf","installscripts/userconf.txt")
      shutil.copyfile("wpa_supplicant.lab.conf",conf_file)
    else:
      shutil.copyfile("userconf.student.conf","installscripts/userconf.txt")
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


if __name__=="__main__":
   add_contents_to_card("\\\\.\\PHYSICALDRIVE2")