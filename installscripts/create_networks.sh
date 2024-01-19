#! /bin/bash
# write a networkmanager config file for each network

SSID=$1
PASSWORD=$2
PW_TYPE=$3


if [ ${PW_TYPE} == 'EDUROAM' ]; then
USERNAME=${SSID}
SSID=eduroam
fi

CONNFILE="/etc/NetworkManager/system-connections/${SSID}.nmconnection"
UUID=$(uuid -v4)

cat <<- EOF >${CONNFILE}
[connection]
id=${SSID}
uuid=${UUID}
type=wifi
interface-name=wlan0

[wifi]
mode=infrastructure
ssid=${SSID}

[ipv4]
method=auto

[ipv6]
addr-gen-mode=default
method=auto

EOF

if [ ${PW_TYPE} == 'WEP' ]; then
cat <<- EOF >>${CONNFILE}
[wifi-security]
key-mgmt=none
wep-key0=${PASSWORD}
wep-tx-keyidx=0
EOF
fi

if [ ${PW_TYPE} == 'WPA' ]; then
cat <<- EOF >>${CONNFILE}
[wifi-security]
key-mgmt=wpa-psk
psk=${PASSWORD}
EOF

fi

if [ ${PW_TYPE} == 'EDUROAM' ]; then
cat <<- EOF >>${CONNFILE}
[wifi-security]
key-mgmt=wpa-eap

[802-1x]
eap=peap;
identity=${USERNAME}@nottingham.ac.uk
anonymous-identity=anonymous@nottingham.ac.uk
domain-suffix-match=radius.nottingham.ac.uk	
#ca-cert=/home/joe/.cert/corp.crt
phase1-peapver=1
phase2-auth=mschapv2
password-flags=2
password=${PASSWORD}
EOF
fi


chmod 600 ${CONNFILE}
