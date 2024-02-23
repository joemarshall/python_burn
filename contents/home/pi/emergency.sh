#! /bin/bash

## Emergency reset script
# if update script exists and is >0 length then exit and let it do its thing
test -s /home/pi/grove-startup-scripts/checkUpdate.sh && exit

cd /tmp
rm -rf grove-startup-scripts
git clone https://github.com/joemarshall/grove-startup-scripts.git
if [ $? -eq 0 ]
then
    cd /home/pi
    chown pi:pi -R /home/pi/grove-startup-scripts
    rm -rf /home/pi/grove-startup-scripts
    mv /tmp/grove-startup-scripts /home/pi/grove-startup-scripts
fi
