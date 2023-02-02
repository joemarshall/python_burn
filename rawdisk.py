import win32file
import winioctlcon
import os
import struct
import pywintypes
import wmi
import pythoncom
import time
import threading

def get_disk_volumes(target_device):
    pythoncom.CoInitialize()
    volume_list=[]
    wm = wmi.WMI ()

    for disk in wm.Win32_DiskDrive():
        if disk.DeviceID==target_device:
            for partition in disk.associators ("Win32_DiskDriveToDiskPartition"):
                for logical_disk in partition.associators ("Win32_LogicalDiskToPartition"):
                      volume_list.append(f"\\\\.\\{logical_disk.Caption}")
    return volume_list

def copy_to_disk(src_img,target_device,progress_callback,id):
    out_handle=None
    in_handle=None
    volumes=[]
    try:
        out_handle=win32file.CreateFile(target_device,win32file.GENERIC_WRITE,win32file.FILE_SHARE_READ|win32file.FILE_SHARE_WRITE,None,win32file.OPEN_EXISTING,win32file.FILE_ATTRIBUTE_NORMAL,None)
        if out_handle==win32file.INVALID_HANDLE_VALUE:
            out_handle=win32file.CreateFile(target_device,win32file.GENERIC_WRITE,win32file.didisFILE_SHARE_READ|win32file.FILE_SHARE_WRITE,None,win32file.CREATE_ALWAYS,win32file.FILE_ATTRIBUTE_NORMAL,None)
        if out_handle==win32file.INVALID_HANDLE_VALUE:
            raise RuntimeError(f"Couldn't open output disk {target_device}")
        geometry=get_drive_geometry(out_handle)
        sector_size=geometry[-3]
        # unmount and lock any volumes on disk
        dev_number= struct.unpack("3L",
                                win32file.DeviceIoControl(out_handle,winioctlcon.IOCTL_STORAGE_GET_DEVICE_NUMBER,
                                None,12))[1]
        volumes=[]
        for x in get_disk_volumes(target_device):
            volume_handle=win32file.CreateFile(x,win32file.GENERIC_READ,win32file.FILE_SHARE_READ|win32file.FILE_SHARE_WRITE,None,win32file.OPEN_EXISTING,win32file.FILE_ATTRIBUTE_NORMAL,None)
            volumes.append(volume_handle)
            print(x,target_device,volume_handle)

        for volume_handle in volumes:
            win32file.DeviceIoControl(volume_handle,winioctlcon.FSCTL_DISMOUNT_VOLUME,None,None)
            win32file.DeviceIoControl(volume_handle,winioctlcon.FSCTL_LOCK_VOLUME,None,None)

        in_size=os.stat(src_img).st_size
        print("Opening for read:",src_img,target_device)
        in_handle=win32file.CreateFile(src_img,win32file.GENERIC_READ,win32file.FILE_SHARE_READ|win32file.FILE_SHARE_WRITE,None,win32file.OPEN_EXISTING,win32file.FILE_ATTRIBUTE_NORMAL,None)
        print(in_handle)
        read_buffer_size=(8388608//sector_size)*sector_size
        print("Bufsize: ",read_buffer_size)
        data_written=0
        while data_written<in_size:
            res, data = win32file.ReadFile(in_handle, read_buffer_size)
            if res!=0:
                raise IOError(f"Error reading from {src_img}:{res}")
            if data_written==0:
                # disk id that will almost certainly be different between multiple burns 
                # we hack the disk id because windows can't mount multiple disks with the 
                # same ID
                disk_id=hash((os.getpid(),threading.get_native_id()))&0xffffffff
                print("Writing 4 byte disk ID: %x"%disk_id)
                data=data[0:0x1b8]+struct.pack(">L",disk_id)+data[0x1bc:]
            res,bytes_written=win32file.WriteFile(out_handle,data)
            if res!=0:
                raise IOError(f"Error writing to {target_device}:{res}")        
            data_written+=bytes_written
            if not progress_callback(data_written,in_size,id):
                # cancelled
                raise RuntimeError("Cancelled by user")

    except pywintypes.error as e:
        raise RuntimeError(str(e))
    finally:
        if out_handle:
            win32file.CloseHandle(out_handle)
        if in_handle:
            win32file.CloseHandle(in_handle)
        for volume_handle in volumes:
#            win32file.DeviceIoControl(volume_handle,winioctlcon.FSCTL_UNLOCK_VOLUME,None,None)
            win32file.CloseHandle(volume_handle)
        time.sleep(1)
        win32file.GetLogicalDrives() # forces a rescan
        time.sleep(1)





def get_drive_geometry(handle):
    """
    Retrieves information about the physical disk's geometry.
    https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ns-winioctl-disk_geometry_ex

    Returns a tuple of:
        Cylinders-Lo
        Cylinders-Hi
        Media Type
        Tracks Per Cylinder
        Sectors Per Track
        Bytes Per Sector
        Disk Size
        Extra Data
    """
    return struct.unpack("8L", win32file.DeviceIoControl(
            handle,  # handle
            winioctlcon.IOCTL_DISK_GET_DRIVE_GEOMETRY_EX,  # ioctl api
            b"",  # in buffer
            32  # out buffer
        ))   


if __name__=="__main__":
    print(get_disk_volumes("\\\\.\\PHYSICALDRIVE2"))
