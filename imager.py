from asciimatics.widgets import Frame, TextBox, Layout, Label, Divider, Text, \
    CheckBox, RadioButtons, Button, PopUpDialog, TimePicker, DatePicker, DropdownList, PopupMenu
from asciimatics.screen import Screen
from asciimatics.scene import Scene
from asciimatics.exceptions import ResizeScreenError, NextScene, StopApplication, InvalidFields

from dataclasses import dataclass
from burn import ImageBurner

@dataclass
class DataHolder:
    burner:ImageBurner
    wifipw:str=""
    wifiname:str=""
    uniname:str=""
    unipw:str=""
    burntype:str=""


class WifiFrame(Frame):
    def __init__(self,screen,burner):
        super().__init__(screen=screen,height=screen.height,width=screen.width)
        layout=Layout([100],True)
        self.add_layout(layout)
        layout.add_widget(Text("University username (e.g. psxwy2):", "uniname"))
        layout.add_widget(Text("University password", "unipw",hide_char="*"))
        layout.add_widget(Text("Home wifi name", "wifiname"))
        layout.add_widget(Text("Home wifi password:", "wifipw",hide_char="*"))
        layout2 = Layout([1, 1, 1, 1])
        self.add_layout(layout2)
        layout2.add_widget(Button("OK", self.ok), 0)
        layout2.add_widget(Button("Cancel", self.cancel), 3)        
        self.fix()

    def ok(self):
        raise NextScene("burn")

    def cancel(self):
        raise NextScene("menu")

# on startup - a) set us as the burn callback for the burner
#              b) if we are burning, then show progress and disable cancel button
#                  and show N many progress bars
#              c) otherwise show warning message saying how
#                  many cards will be written and wait for okay


class BurnReadyFrame(Frame):
    def __init__(self,screen,dataholder):
        super().__init__(screen=screen,height=screen.height,width=screen.width)
        self.dataholder=dataholder
        layout=Layout([100],True)
        self.add_layout(layout)
        layout.add_widget(Label("About to burn. Press OK to continue"), 0)
        layout2=Layout([1,1,1,1],False)
        self.add_layout(layout2)
        layout2.add_widget(Button("OK", self.ok), 0)
        layout2.add_widget(Button("Cancel", self.cancel), 3)        
        self.fix()
    
    def ok(self):
        # make image
        # start burn (on first drive or on all drives depending on type)
        for (disk,model) in dataholder.burner.get_all_disks():
            dataholder.burner.burn_image_to_disk(source_image="test.img",target_disk=disk)
        raise NextScene("burn")

    def cancel(self):
        # back to menu
        raise NextScene("menu")

class BurnDoneFrame(Frame):
    def __init__(self,screen,dataholder):
        super().__init__(screen=screen,height=screen.height,width=screen.width)
        self.dataholder=dataholder
        layout=Layout([100],True)
        self.add_layout(layout)
        layout.add_widget(Label("Burn complete"), 0)
        layout2=Layout([1,1,1,1],False)
        self.add_layout(layout2)
        layout2.add_widget(Button("Menu", self.menu), 0)
        layout2.add_widget(Button("Repeat", self.repeat), 3)        
        self.fix()
    
    def menu(self):
        # make image
        # start burn (on first drive or on all drives depending on type)
        dataholder.burner.burn_image_to_disk(source_image="test.img",target_disk="\\\\.\\PHYSICALDRIVE2")
        raise NextScene("menu")

    def repeat(self):
        # back to menu
        raise NextScene("burn_ready")




class BurnFrame(Frame):
    def __init__(self,screen,dataholder):
        super().__init__(screen=screen,height=screen.height,width=screen.width)
        self.dataholder=dataholder
        layout=Layout([100],False)
        self.add_layout(layout)
        layout.add_widget(Label("Burning - press cancel to stop"), 0)
        self.progresses={}
        progress_layout=Layout([1,4],True)
        self.add_layout(progress_layout)
        self.progress_layout=progress_layout
        for (id,data) in self.dataholder.burner.get_progress():            
            dev_id=data["target"]
            progress_layout.add_widget(Label(dev_id+":"), 0)
            self.progresses[dev_id]=progress_layout.add_widget(Label("."), 1)
        layout2=Layout([1,1,1,1],False)
        self.add_layout(layout2)
        layout2.add_widget(Button("Cancel", self.cancel), 3)        
        self.fix()

    @property
    def frame_update_count(self):
        return 1

    def update(self,frame):
        progress=self.dataholder.burner.get_progress(only_updated=False)
        print(".")
        for _,data in progress:
            print("!!!")
            dev_id=data["target"]
            if dev_id not in self.progresses:
                self.progress_layout.add_widget(Label(dev_id+":"), 0)
                self.progresses[dev_id]=self.progress_layout.add_widget(Label("."), 1)
                self.fix()
            if data["finished"]==True:
                if data["result"]!=0:
                    self.progresses[dev_id].text="Failed: "+data["output"]
                print(data)
            else:
                percent_sent=data["bytes_transferred"]/data["total_size"]
                progress_count=int((percent_sent+0.5)//20)
                self.progresses[dev_id].text="."*progress_count
        super().update(frame)

    def cancel(self):
        # are you sure?
        dlg=PopUpDialog(self.screen,text="Cancel burn, are you sure?",buttons=["ok","cancel"])
        self.add_effect(dlg)

        # cancel any pending burns
        self.dataholder.burner.cancel()
        # back to menu
        raise NextScene("menu")

class MenuFrame(Frame):
    def __init__(self,screen,dataholder):
        super().__init__(screen=screen,height=screen.height,width=screen.width)
        menu_items=[("Burn lab image to SD card(s)",self.burn_lab),("Burn student image to single SD card",self.burn_student),("Set SD card to lab image",self.set_lab),("Set SD card to student image",self.set_student)]        
        layout=Layout([100],True)
        self.add_layout(layout)
        self.widgets=[]
        for label,cb in menu_items:
            self.widgets.append(layout.add_widget(Button(text=label,add_box=False,on_click=cb,name=label),0))
            print(label)
        self.fix()            

    def burn_lab(self):
        raise NextScene("burn_ready")
    def burn_student(self):
        raise NextScene("wifi")
    def set_lab(self):
        raise NextScene("burn_ready")
    def set_student(self):
        raise NextScene("wifi")


def main(screen, scene,holder):
    # Define your Scenes here
    # 1) Menu to choose what to do
    # 2) Form to input wifi + passwords
    # 3) Burn progress screen

    scenes = [Scene([MenuFrame(screen,holder)],name="menu"),Scene([WifiFrame(screen,holder)],name="wifi"),Scene([BurnReadyFrame(screen,holder)],name="burn_ready"),Scene([BurnFrame(screen,holder)],name="burn"),Scene([BurnDoneFrame(screen,holder)],name="burn_done")]

    # Run your program
    screen.play(scenes, stop_on_resize=True, start_scene=scene)

dataholder=DataHolder(burner=ImageBurner())
last_scene = None
while True:
    try:
        Screen.wrapper(main, arguments=[last_scene,dataholder])
        sys.exit(0)
    except ResizeScreenError as e:
        last_scene = e.scene