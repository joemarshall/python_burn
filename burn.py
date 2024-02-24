from winpty import PtyProcess
import re
import threading
import subprocess
import os
import wmi
import pythoncom

from image_edit import add_contents_to_raw_disk
import rawdisk

class ImageBurner:
    def __init__(self):
        self.burns={}
        self.next_id=1
        self.event=threading.Event()
        self.location_cache={}
        self.drive_list=[]
        self.drive_scan_thread=threading.Thread(target=self.disk_scan_thread_fn)
        self.drive_scan_thread.daemon=True # we don't care if it is killed
        self.drive_scan_thread.start()


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

    def _get_disk_path(self,wm,device):
        props,rval=device.GetDeviceProperties(["DEVPKEY_Device_LocationPaths","DEVPKEY_Device_Parent"])
        if rval==0:
            if props[0].type!=0:
                return props[0].data
            if props[1].type!=0:
                for x in wm.query(f"select * from Win32_PnPEntity where PNPDeviceID='{props[1].data}'"):
                    return self._get_disk_path(wm,x)
        return None

    def _rewrite_location(self,location):
        for path in location:
            parts=re.findall(r"(\w+)\((\d+)\)(?#|$)",path)
            if "USBROOT" in [x for x,y in parts]:
                location=None
                for name,part_num in parts:
                    if name=="USBROOT":
                        location=[int(part_num)]
                    elif location is not None:
                        location.append(int(part_num))
                return location
        return []

    def disk_scan_thread_fn(self):
        pythoncom.CoInitializeEx(0)
        while True:
            self.rescan_disks()

    def rescan_disks(self):
        drive_list=[]
        wm = wmi.WMI ()
        for disk in wm.Win32_DiskDrive():
            # 7 = removable drive
            if disk.Capabilities is not None and 7 in disk.Capabilities:
                if disk.Signature in self.location_cache:
                    location = self.location_cache[disk.Signature]
                else:
                    location="Unknown"
                    for x in disk.associators(): # CreationClassName='Win32_PNPEntity'
                        if x.CreationClassName=="Win32_PnPEntity":
                            l=self._get_disk_path(wm,x)
                            if l!=None:
                                location=self._rewrite_location(l)                            
                                self.location_cache[disk.Signature]=location
                                break
                drive_list.append((disk.DeviceID,disk.Model,location))
        self.drive_list=drive_list

    def get_all_disks(self):
        return self.drive_list

    def _burn_progress(self,current,total,id):
        if id in self.burns:
            self.burns[id]["bytes_transferred"]=current
            self.burns[id]["updated"]=True
            self.event.set()
            return self.burns[id]["cancelled"]==False
        else:
            return False

    def _burn_thread(self,source_image,target_disk,id,contents_only,prepatched):
        try:
            if not contents_only:
                self.burns[id]["text"]="Burning image"
                rawdisk.copy_to_disk(source_image,target_disk,self._burn_progress,id)
            self.burns[id]["text"]="Copying contents"
            if not prepatched:
                add_contents_to_raw_disk(target_disk)
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

    def burn_image_to_disk(self,source_image=None,target_disk=None,contents_only=False,prepatched=False):
        id=self.next_id
        self.next_id+=1
        self.burns[id]={}
        total_size=os.path.getsize(source_image) 
        self.burns[id]["cancelled"]=False
        self.burns[id]["text"]=""
        self.burns[id]["finished"]=False
        self.burns[id]["total_size"]=total_size
        self.burns[id]["target"]=target_disk
        self.burns[id]["thd"]=threading.Thread(target=self._burn_thread,args=[source_image,target_disk,id,contents_only,prepatched],daemon=True)
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

    def clear(self):
        self.burns={}


if __name__=="__main__":
    import time

    i=ImageBurner()
    import timeit
    time.sleep(5)
    print(timeit.timeit("i.get_all_disks()",number=20,globals=locals())/20)
    print(i.get_all_disks())
    # for disk,model in i.get_all_disks():
    #     i.burn_image_to_disk(source_image="raspios.img",target_disk=disk)
    # while i.burning():
    #     print(".")
    #     print(i.get_progress())
    #     time.sleep(5)

