import sys
sys.dont_write_bytecode = True
import datetime
import argparse
import wmi
import re
import winreg

sys.path.append("chipwhiz")
import scsi
import controller
import flash
import vidpid_db

_version = "ChipWhiz/CHIE v0.1 *ALPHA* by ID403 // 2025/05/01"

def get_usb_device_info_by_letter(letter):
    letter = letter.upper() + ':'
    c = wmi.WMI()
    for drive in c.Win32_DiskDrive():
        if drive.InterfaceType != 'USB':
            continue
        for part in drive.associators("Win32_DiskDriveToDiskPartition"):
            for logical in part.associators("Win32_LogicalDiskToPartition"):
                if logical.DeviceID.upper() == letter:
                    pnpid = drive.PNPDeviceID
                    serial = extract_serial(pnpid)
                    vidpid = extract_vid_pid(pnpid) or extract_vid_pid_from_parent(pnpid) or extract_vid_pid_from_registry(serial)
                    vid, pid = (vidpid.split(":") if ":" in vidpid else ("", ""))
                    return {
                        "VIDPID": vidpid,
                        "VID": vid,
                        "PID": pid,
                        "Manufacturer": drive.Manufacturer or drive.Caption,
                        "Product": drive.Model,
                        "Serial": serial,
                        "VendorName": vidpid_db.lookup_vid(vid) if vid else "",
                        "ProductName": vidpid_db.lookup_pid(vid, pid) if vid and pid else ""
                    }
    return None

def extract_vid_pid(pnpid):
    m = re.search(r'VID_([0-9A-F]{4})&PID_([0-9A-F]{4})', pnpid, re.I)
    return f"{m.group(1)}:{m.group(2)}" if m else None

def extract_vid_pid_from_parent(pnpid):
    c = wmi.WMI()
    for device in c.Win32_PnPEntity():
        if device.PNPDeviceID and pnpid.split('\\')[0] in device.PNPDeviceID:
            vidpid = extract_vid_pid(device.PNPDeviceID)
            if vidpid:
                return vidpid
    return None

def extract_vid_pid_from_registry(serial):
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum\USB") as usb_root:
            for i in range(0, winreg.QueryInfoKey(usb_root)[0]):
                devkey_name = winreg.EnumKey(usb_root, i)
                if not devkey_name.startswith("VID_"):
                    continue
                with winreg.OpenKey(usb_root, devkey_name) as dev_key:
                    for j in range(0, winreg.QueryInfoKey(dev_key)[0]):
                        inst_key_name = winreg.EnumKey(dev_key, j)
                        if serial.lower() in inst_key_name.lower():
                            match = re.search(r'VID_([0-9A-F]{4})&PID_([0-9A-F]{4})', devkey_name, re.I)
                            if match:
                                return f"{match.group(1)}:{match.group(2)}"
    except Exception:
        pass
    return "Unavailable"

def extract_serial(pnpid):
    parts = pnpid.split('\\')
    return parts[-1] if len(parts) >= 3 else "Unavailable"

def ProcessDevice(deviceName, report=[], verbose=False, friendlyName=""):
    if friendlyName == "":
        friendlyName = deviceName

    try:
        report.append(("Device", friendlyName))

        if len(friendlyName) == 2 and friendlyName[1] == ":":
            info = get_usb_device_info_by_letter(friendlyName[0])
            if info:
                report.append(("VID:PID", info["VIDPID"]))
                report.append(("Manufacturer", info.get("Manufacturer", "")))
                report.append(("Product", info.get("Product", "")))
                report.append(("Serial", info.get("Serial", "")))
                report.append(("Vendor Name", info.get("VendorName", "")))
                report.append(("Product Name", info.get("ProductName", "")))

        with scsi.Device(deviceName) as dctl:
            capacity = scsi.GetCapacity(dctl)
            report.append(("Capacity", capacity, "size"))

            detected = False
            for ctl in controller.DetectController(dctl, verbose=verbose):
                ctl.ProcessDevice(dctl, report)
                detected = True
            if not detected:
                report.append(("Controller", "Unknown"))
    except Exception as e:
        report.append(("Error", e))

    return report

def ProcessDeviceByLetter(deviceLetter, report=[], verbose=False):
    letter = deviceLetter[0].upper()
    device = "\\\\.\\" + letter + ":"
    return ProcessDevice(device, report, verbose, friendlyName=letter + ":")

def FormatValue(value, format):
    if value == None:
        return "Unavailable"

    if format == "X":
        return "%X" % value
    if format == "size":
        return "%d byte(s)" % value
    if format == "fid":
        return flash.GetFlashInfo(value)

    return value

def PrintReport(report, filename=None):
    rawreport = []
    for entry in report:
        key = entry[0]
        value = FormatValue(entry[1], entry[2]) if len(entry) > 2 else entry[1]
        rawreport.append((key, value))

    keywidth = 0
    for entry in rawreport:
        keywidth = max(keywidth, len(entry[0]))

    f = open(filename, "wt") if filename else None
    if f:
        f.write(_version + "\n")

    for entry in rawreport:
        key, value = entry
        line = f"{key:{keywidth}}: {value}"
        print(line)
        if f:
            f.write(line + "\n")

    if f:
        f.close()

def SetCommonParams(parser):
    parser.add_argument("device", help="Device name (e.g. F: or /dev/sdb)", type=str)
    parser.add_argument("-b", "--benchmark", help="Perform IO benchmark", action="store_true")
    parser.add_argument("-r", "--report", help="Write report to file", dest="report")
    parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true")
    parser.add_argument("-p", "--plugin", help="Force plugin(s)", type=str)

def Main():
    print(_version)
    controller.LoadPlugins()
    print("Supported controllers: %s" % (" ,".join(controller.GetPlugins())))
    print("")

    parser = argparse.ArgumentParser()
    SetCommonParams(parser)
    args = parser.parse_known_args()[0]
    plugins = args.plugin.split(",") if args.plugin else None
    if plugins:
        controller.UnloadPlugins(keep=plugins)
        print("Selected controllers: %s" % (" ,".join(controller.GetPlugins())))

    for plugin in controller.plugins:
        controller.plugins[plugin].AddParameters(parser)
    args = parser.parse_args()

    report = ProcessDeviceByLetter(args.device, verbose=args.verbose)

    if args.benchmark:
        pass

    PrintReport(report, args.report)

Main()
