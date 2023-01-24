from fs.copy import copy_fs
from pathlib import Path
from passlib.hash import lmhash

def add_contents_to_image(img_file):
    src=str( (Path(__file__).parent) / "contents/")
    copy_fs(src,"fat://{img_file}/offset=4194304/")
    
def create_wpa_supplicant(wifipw,wifiname,uniname,unipw):
    src=Path(__file__).parent) / "contents" / "etc"/ "wpa_supplicant.conf"
    src.parent.mkdir(exist_ok=True,parents=True)
    unihash=lmhash.hash(unipw)
    src.write_text("""
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev

    
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
"""%(uniname,unihash,wifiname,wifipw))
