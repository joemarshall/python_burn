from winpty import PtyProcess
import re
import threading
import subprocess
import os

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
        return [("//DEVNULL/ERROR","Fake drive")]
        result=subprocess.run(["wdd.exe","list"],capture_output=True)
        ret_val=[]
        lines=result.stdout.splitlines()
        col_devid=lines[0].find(b"DeviceID")
        col_model=lines[0].find(b"Model")
        col_partitions=lines[0].find(b"Partitions")
        for line in lines[1:]:
            if len(line)>col_model:
                dev_id=line[col_devid:col_model].strip()
                model=line[col_model:col_partitions].strip()
                if model.find(b"USB")!=-1:
                    ret_val.append((dev_id,model))
        return ret_val

    def _burn_thread(self,source_image,target_disk,id):
        total_size=os.path.getsize(source_image)
        proc=PtyProcess.spawn(["wdd.exe",f"if={source_image}",f"of={target_disk}","status=progress"])
        self.burns[id]={"process":proc}
        self.burns[id]["target"]=target_disk
        self.burns[id]["total_size"]=total_size
        self.burns[id]["finished"]=False
        self.burns[id]["updated"]=True
        self.burns[id]["time_taken"]=""
        self.burns[id]["speed"]=""
        self.burns[id]["bytes_transferred"]=0
        self.event.set()
        output=[]
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        while proc.isalive():
            line=proc.readline()
            output.append(ansi_escape.sub('', line))
            match=re.match(r".*\[H(\d+) bytes[^,]*,([^,]*),\w*(.*/s)",str(line))
            if match:
                bytes_transferred,time_taken,speed=match.groups()
                self.burns[id]["bytes_transferred"]=int(bytes_transferred)
                self.burns[id]["time_taken"]=time_taken
                self.burns[id]["speed"]=speed
                self.burns[id]["updated"]=True
                self.event.set()
        
        self.burns[id]["updated"]=True
        self.burns[id]["finished"]=True
        self.burns[id]["result"]=proc.exitstatus
        self.burns[id]["output"]="\n".join(output)
        self.event.set()

    def burn_image_to_disk(self,source_image=None,target_disk=None):
        self.burns[self.next_id]={}
        thd=threading.Thread(target=self._burn_thread,args=[source_image,target_disk,self.next_id],daemon=True)
        thd.start()
        # should fire event
        self.event.wait()
        self.next_id+=1

    def cancel(self):
        for p in self.burns.values():
            if "process" in p and p["process"].isalive():
                p["process"].terminate(force=True)
        self.burns={}

def burn_image_to_disk(source_image=None,target_disk=None,progress_callback=None):
    proc=PtyProcess.spawn(["wdd.exe",f"if=\\\\.\\PHYSICALDRIVE2",f"of=temp.img","status=progress"])
    while proc.isalive():
        print(line)
        match=re.match(r".*\[H(\d+) bytes[^,]*,([^,]*),\w*(.*/s)",str(line))
        if match:
            bytes_transferred,time_taken,speed=match.groups()
            if progress_callback:
                progress_callback(bytes_transferred,time_taken,speed)




if __name__=="__main__":
    i=ImageBurner()

#   get_all_disks()
    i.burn_image_to_disk(source_image="test.img",target_disk="\\\\.\\PHYSICALDRIVE2")
    while i.burning():
        print(".")
        print(i.wait())

