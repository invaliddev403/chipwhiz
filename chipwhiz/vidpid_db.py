# vidpid_db.py

# Vendor names for common USB vendor IDs
VIDS = {
    "0781": "SanDisk",
    "05AC": "Apple",
    "046D": "Logitech",
    "04E8": "Samsung",
    "045E": "Microsoft",
    "090C": "Silicon Motion",
    "0BDA": "Realtek",
    "0930": "Toshiba",
    "054C": "Sony",
    "0BC2": "Seagate"
}

# Product names for known VID:PID combinations
PIDS = {
    "0781:5595": "SanDisk Ultra USB 3.0",
    "0781:5567": "SanDisk Cruzer Blade",
    "05AC:12A8": "Apple iPhone",
    "046D:C52B": "Logitech Unifying Receiver",
    "04E8:6860": "Samsung Android Phone [Media Transfer Mode]",
    "045E:07B2": "Microsoft Surface Dock",
    "0BDA:0129": "Realtek USB 2.0 Card Reader",
    "0930:6545": "Toshiba TransMemory USB 3.0",
    "054C:05BA": "Sony Storage Media",
    "0BC2:2322": "Seagate External Drive"
}

def lookup_vid(vid):
    return VIDS.get(vid.upper(), "Unknown Vendor")

def lookup_pid(vid, pid):
    return PIDS.get(f"{vid.upper()}:{pid.upper()}", "Unknown Product")
