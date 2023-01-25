import win32file
import winioctlcon
import os
import struct
import pywintypes

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
        drives=win32file.GetLogicalDrives()
        for x in range(26):
            if drives&(1<<x)!=0:
                volume_letter=chr(ord("A")+x)
                print(volume_letter)
                drive_type=win32file.GetDriveType(f"{volume_letter}:\\")
                if drive_type==win32file.DRIVE_REMOVABLE:
                    drive_path=f"\\\\.\\{volume_letter}:"
                    print(drive_path)
                    volume_handle=win32file.CreateFile(drive_path,win32file.GENERIC_READ,win32file.FILE_SHARE_READ|win32file.FILE_SHARE_WRITE,None,win32file.OPEN_EXISTING,win32file.FILE_ATTRIBUTE_NORMAL,None)
                    volume_dev= struct.unpack("3L",
                                    win32file.DeviceIoControl(volume_handle,winioctlcon.IOCTL_STORAGE_GET_DEVICE_NUMBER,
                                    None,12))[1]
                    if volume_dev==dev_number:
                        volumes.append(volume_handle)
                    else:
                        win32file.CloseHandle(volume_handle)

        for volume_handle in volumes:
            result=win32file.DeviceIoControl(volume_handle,winioctlcon.FSCTL_DISMOUNT_VOLUME,None,None)
    #        if result!=0:
    #            raise IOError(f"Couldn't dismount drive {volume_handle}:{result}")
            result=win32file.DeviceIoControl(volume_handle,winioctlcon.FSCTL_LOCK_VOLUME,None,None)
            print(result)
    #        if result!=0:
    #            raise IOError(f"Couldn't lock drive {volume_handle}:{result}")

        in_size=os.stat(src_img).st_size
        in_handle=win32file.CreateFile(src_img,win32file.GENERIC_READ,win32file.FILE_SHARE_READ|win32file.FILE_SHARE_WRITE,None,win32file.OPEN_EXISTING,win32file.FILE_ATTRIBUTE_NORMAL,None)
        print(in_handle)
        read_buffer_size=(8388608//sector_size)*sector_size
        print("Bufsize: ",read_buffer_size)
        data_written=0
        while data_written<in_size:
            res, data = win32file.ReadFile(in_handle, read_buffer_size)
            if res!=0:
                raise IOError(f"Error reading from {src_img}:{res}")
            res,bytes_written=win32file.WriteFile(out_handle,data)
            if res!=0:
                raise IOError(f"Error writing to {target_device}:{res}")        
            data_written+=bytes_written
            if not progress_callback(data_written,in_size,id):
                # cancelled
                raise RuntimeError("Cancelled by user")
    except pywintypes.error as e:
        raise RuntimeError(str(e))

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


