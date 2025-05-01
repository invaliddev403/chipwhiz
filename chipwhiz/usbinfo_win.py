import ctypes
import ctypes.wintypes as wintypes
import sys
import re
import winreg
import os

# Constants from Windows SDK
DIGCF_PRESENT = 0x2
DIGCF_DEVICEINTERFACE = 0x10
SPDRP_DEVICEDESC = 0x00000000
SPDRP_HARDWAREID = 0x00000001
SPDRP_LOCATION_PATHS = 0x00000023

GUID_DEVINTERFACE_DISK = ctypes.c_byte * 16

guid_disk = GUID_DEVINTERFACE_DISK(*[int(x, 16) for x in (
    "53F56307", "B6BF", "11D0", "94", "F2", "00", "A0", "C9", "1E", "FB", "8B", "00", "00", "00", "00", "00"
)])

setupapi = ctypes.windll.LoadLibrary("setupapi.dll")
cfgmgr32 = ctypes.windll.LoadLibrary("cfgmgr32.dll")

class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("ClassGuid", ctypes.c_byte * 16),
        ("DevInst", wintypes.DWORD),
        ("Reserved", ctypes.POINTER(ctypes.c_ulong))
    ]

class USBInfo:
    def __init__(self):
        self.devices = self._get_usb_devices()

    def _get_usb_devices(self):
        devices = []
        DIGCF_ALLCLASSES = 0x00000004
        hdevinfo = setupapi.SetupDiGetClassDevsW(None, None, None, DIGCF_PRESENT | DIGCF_ALLCLASSES)
        if hdevinfo == -1:
            return devices

        index = 0
        devinfo = SP_DEVINFO_DATA()
        devinfo.cbSize = ctypes.sizeof(SP_DEVINFO_DATA)

        while setupapi.SetupDiEnumDeviceInfo(hdevinfo, index, ctypes.byref(devinfo)):
            index += 1
            buffer = ctypes.create_unicode_buffer(1000)
            required_size = wintypes.DWORD()

            if setupapi.SetupDiGetDeviceRegistryPropertyW(hdevinfo, ctypes.byref(devinfo), SPDRP_HARDWAREID,
                                                           None, ctypes.cast(buffer, ctypes.c_void_p),
                                                           ctypes.sizeof(buffer), ctypes.byref(required_size)):
                hardware_id = buffer.value

                loc_buf = ctypes.create_unicode_buffer(1000)
                if setupapi.SetupDiGetDeviceRegistryPropertyW(hdevinfo, ctypes.byref(devinfo), SPDRP_LOCATION_PATHS,
                                                               None, ctypes.cast(loc_buf, ctypes.c_void_p),
                                                               ctypes.sizeof(loc_buf), ctypes.byref(required_size)):
                    location = loc_buf.value
                else:
                    location = ""

                match = re.search(r"VID_([0-9A-F]{4})&PID_([0-9A-F]{4})", hardware_id, re.IGNORECASE)
                if match:
                    vid = match.group(1)
                    pid = match.group(2)
                    devices.append({
                        "VID": vid,
                        "PID": pid,
                        "HardwareID": hardware_id,
                        "Location": location
                    })

        setupapi.SetupDiDestroyDeviceInfoList(hdevinfo)
        return devices

    def get_device_by_drive(self, drive_letter):
        # Get volume device path: \\?\Volume{...}
        import win32file
        path = f"{drive_letter.upper()}:\\"
        volume_name = win32file.QueryDosDevice(drive_letter.upper() + ":")

        for dev in self.devices:
            if dev['Location'] and dev['Location'] in volume_name:
                return dev
        return None

if __name__ == "__main__":
    usbinfo = USBInfo()
    for dev in usbinfo.devices:
        print(f"VID:PID = {dev['VID']}:{dev['PID']} | {dev['Location']} | {dev['HardwareID']}")
