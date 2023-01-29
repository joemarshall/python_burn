from winpty import PtyProcess
import re
import threading
import subprocess
import os
import wmi

from image_edit import add_contents_to_card
import rawdisk

class ImageBurner:
    def __init__(self):
        self.burns={}
        self.next_id=1
        self.event=threading.Event()

    def get_progress(self,only_updated=False):
        updates=[]
        if len(self.burns)>0:
            for id,data in self.burns.items():
                if only_updated and data["updated"]:
                    data["updated"]=False
                    updates.append((id,data))
                else:
                    updates.append((id,data))
        return updates
    
    def get_burn_ids(self):
        return list(self.burns.keys())

    def wait(self):
        if len(self.burns)>0:
            self.event.wait()
            for id,data in self.burns.items():
                if data["updated"]:
                    data["updated"]=False
                    self.event.clear()
                    return id,data
        return None

    def burning(self):
        return (len(self.burns)>0)

    def get_all_disks(self):
        drive_list=[]
        wm = wmi.WMI ()
        for disk in wm.Win32_DiskDrive():
            # 7 = removable drive
            if 7 in disk.Capabilities:
                drive_list.append((disk.DeviceID,disk.Model))
        return drive_list

    def _burn_progress(self,current,total,id):
        if id in self.burns:
            self.burns[id]["bytes_transferred"]=current
            self.burns[id]["updated"]=True
            self.event.set()
            return self.burns[id]["cancelled"]==False
        else:
            return False

    def _burn_thread(self,source_image,target_disk,id,contents_only):
        try:
            if not contents_only:
                self.burns[id]["text"]="Burning image"
                rawdisk.copy_to_disk(source_image,target_disk,self._burn_progress,id)
            self.burns[id]["text"]="Copying contents"
            add_contents_to_card(target_disk)
            if not contents_only:
                self.burns[id]["output"]="Burnt and patched successfully"
            else:
                self.burns[id]["output"]="Patched successfully"
            self.burns[id]["result"]=0
        except RuntimeError as r:
            self.burns[id]["result"]=1
            self.burns[id]["output"]=str(r)
        except IOError as r:
            self.burns[id]["result"]=2
            self.burns[id]["output"]=str(r)
        self.burns[id]["finished"]=True
        self.event.set()

    def burn_image_to_disk(self,source_image=None,target_disk=None,contents_only=False):
        id=self.next_id
        self.next_id+=1
        self.burns[id]={}
        total_size=os.path.getsize(source_image) 
        self.burns[id]["cancelled"]=False
        self.burns[id]["text"]=""
        self.burns[id]["finished"]=False
        self.burns[id]["total_size"]=total_size
        self.burns[id]["target"]=target_disk
        self.burns[id]["thd"]=threading.Thread(target=self._burn_thread,args=[source_image,target_disk,id,contents_only],daemon=True)
        self.burns[id]["updated"]=True
        self.burns[id]["bytes_transferred"]=0
        self.burns[id]["thd"].start()
        # should fire event
        self.event.wait()

    def cancel(self):
        for x in self.burns.keys():
            self.burns[x]["cancelled"]=True
        ended=False
        # wait for cancelled transfers to stop
        while not ended:
            ended=True
            for x in self.burns.keys():
                if self.burns[x]["finished"]==False:
                    ended=False
        self.burns={}


if __name__=="__main__":
    i=ImageBurner()
    print(i.get_all_disks())
    # i.burn_image_to_disk(source_image="raspios.img",target_disk="\\\\.\\PHYSICALDRIVE2")
    # while i.burning():
    #     print(".")
    #     print(i.wait())

