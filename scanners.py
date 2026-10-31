"""Moduły skanujące (tylko odczyt, nic nie modyfikują w systemie)."""
import json
import os
import subprocess
import winreg
from datetime import datetime, timezone
from pathlib import Path

import psutil

_NOWINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def ps_json(script: str, timeout: int = 120):
    """Uruchamia PowerShell i zwraca sparsowany JSON (lista lub None)."""
    cmd = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
           "$ErrorActionPreference='SilentlyContinue';" + script)
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                           capture_output=True, text=True, encoding="utf-8",
                           timeout=timeout, creationflags=_NOWINDOW)
    except (subprocess.TimeoutExpired, OSError):
        return None
    out = r.stdout.strip()
    if not out:
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, list) else [data]


def gb(n):
    return f"{n / 1024**3:.1f}".replace(".", ",") + " GB"


def dir_size(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path, onerror=lambda e: None):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


# ---------- Przegląd ----------
def scan_overview():
    vm = psutil.virtual_memory()
    disks = []
    for p in psutil.disk_partitions(all=False):
        if "cdrom" in p.opts or not p.fstype:
            continue
        try:
            u = psutil.disk_usage(p.mountpoint)
        except OSError:
            continue
        disks.append({"drive": p.device, "total": u.total, "free": u.free, "percent": u.percent})
    return {
        "ram_percent": vm.percent, "ram_total": vm.total, "ram_free": vm.available,
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "disks": disks,
        "top_ram": top_processes(),
    }


def top_processes(n=8):
    procs = []
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            procs.append((p.info["name"], p.info["memory_info"].rss))
        except (psutil.Error, AttributeError):
            pass
    agg = {}
    for name, rss in procs:
        agg[name] = agg.get(name, 0) + rss
    return sorted(agg.items(), key=lambda x: -x[1])[:n]


# ---------- Dane techniczne ----------
def scan_hardware():
    q = lambda cls, props: ps_json(f"Get-CimInstance {cls} | Select-Object {props} | ConvertTo-Json -Depth 3") or []
    hw = {}
    cpu = q("Win32_Processor", "Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,L2CacheSize,L3CacheSize,SocketDesignation")
    hw["Procesor"] = [(c["Name"].strip(), f"{c['NumberOfCores']} rdzeni / {c['NumberOfLogicalProcessors']} wątków · "
                       f"{c['MaxClockSpeed']} MHz · L3 {c['L3CacheSize']//1024} MB · {c['SocketDesignation']}") for c in cpu]
    ram = q("Win32_PhysicalMemory", "BankLabel,Capacity,Speed,Manufacturer,PartNumber,SMBIOSMemoryType")
    typ = {26: "DDR4", 24: "DDR3", 34: "DDR5"}
    hw["Pamięć RAM"] = [(f"Moduł {m.get('BankLabel','')}", f"{gb(int(m['Capacity']))} · {typ.get(m.get('SMBIOSMemoryType'),'?')} · "
                         f"{m.get('Speed')} MT/s · {(m.get('Manufacturer') or '').strip()} {(m.get('PartNumber') or '').strip()}") for m in ram]
    gpu = q("Win32_VideoController", "Name,AdapterRAM,DriverVersion,VideoModeDescription")
    hw["Grafika"] = [(g["Name"], f"sterownik {g['DriverVersion']} · {g.get('VideoModeDescription') or 'nieaktywna'}") for g in gpu]
    dsk = q("Win32_DiskDrive", "Model,Size,InterfaceType,MediaType,Status")
    pd = ps_json("Get-PhysicalDisk | Select-Object FriendlyName,MediaType,HealthStatus | ConvertTo-Json") or []
    health = {d["FriendlyName"]: f"{d['MediaType']} · zdrowie: {d['HealthStatus']}" for d in pd}
    hw["Dyski"] = [(d["Model"], f"{gb(int(d['Size']))} · {d['InterfaceType']} · {health.get(d['Model'], d.get('MediaType') or '')}") for d in dsk]
    bb = q("Win32_BaseBoard", "Manufacturer,Product,Version")
    bios = q("Win32_BIOS", "Manufacturer,SMBIOSBIOSVersion,ReleaseDate")
    cs = q("Win32_ComputerSystem", "Manufacturer,Model,SystemType")
    rows = [("Komputer", f"{c['Manufacturer']} {c['Model']} ({c['SystemType']})") for c in cs]
    rows += [("Płyta główna", f"{b['Manufacturer']} {b['Product']} {b.get('Version') or ''}") for b in bb]
    rows += [("BIOS", f"{b['Manufacturer']} {b['SMBIOSBIOSVersion']}") for b in bios]
    hw["Płyta i BIOS"] = rows
    os_ = q("Win32_OperatingSystem", "Caption,Version,BuildNumber,OSArchitecture,InstallDate,LastBootUpTime")
    hw["System"] = [(o["Caption"], f"wersja {o['Version']} · {o['OSArchitecture']}") for o in os_]
    bat = q("Win32_Battery", "EstimatedChargeRemaining,BatteryStatus")
    if bat:
        hw["System"].append(("Bateria", f"{bat[0]['EstimatedChargeRemaining']}%"))
    net = q("Win32_NetworkAdapter | Where-Object {$_.PhysicalAdapter -and $_.NetEnabled}", "Name,Speed,MACAddress")
    hw["Sieć"] = [(n["Name"], f"MAC {n.get('MACAddress')}") for n in net]
    return hw


# ---------- Autostart ----------
HEAVY = ("onedrive", "teams", "spotify", "discord", "steam", "adobe", "epic", "skype", "dropbox", "zoom", "update", "launcher", "updater")
LIGHT = ("security", "defender", "realtek", "intel", "nvidia", "synaptics", "touchpad", "audio")


def rate(name, cmd):
    s = f"{name} {cmd}".lower()
    if any(k in s for k in LIGHT):
        return "Mały"
    if any(k in s for k in HEAVY):
        return "Duży"
    return "Średni"


def scan_startup():
    items = []
    keys = [(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKLM Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM Run (32-bit)")]
    for hive, path, label in keys:
        try:
            with winreg.OpenKey(hive, path) as k:
                i = 0
                while True:
                    try:
                        name, val, _ = winreg.EnumValue(k, i)
                    except OSError:
                        break
                    i += 1
                    items.append({"name": name, "command": str(val), "source": label, "impact": rate(name, str(val))})
        except OSError:
            pass
    folders = [Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup",
               Path(os.environ.get("PROGRAMDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\StartUp"]
    for f in folders:
        if f.is_dir():
            for p in f.iterdir():
                if p.name.lower() != "desktop.ini":
                    items.append({"name": p.stem, "command": str(p), "source": "Folder Autostart", "impact": rate(p.stem, str(p))})
    order = {"Duży": 0, "Średni": 1, "Mały": 2}
    items.sort(key=lambda x: order[x["impact"]])
    return items


# ---------- Pliki zbędne ----------
def scan_junk():
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    win = Path(os.environ.get("WINDIR", r"C:\Windows"))
    targets = [
        ("Temp użytkownika", Path(os.environ.get("TEMP", ""))),
        ("Temp systemu", win / "Temp"),
        ("Cache Windows Update", win / "SoftwareDistribution" / "Download"),
        ("Zrzuty awarii", local / "CrashDumps"),
        ("Cache Chrome", local / "Google/Chrome/User Data/Default/Cache"),
        ("Cache Edge", local / "Microsoft/Edge/User Data/Default/Cache"),
        ("Cache miniatur", local / "Microsoft/Windows/Explorer"),
        ("Prefetch", win / "Prefetch"),
    ]
    res = [{"name": n, "path": str(p), "size": dir_size(p)} for n, p in targets if p.is_dir()]
    res.sort(key=lambda x: -x["size"])
    return res


def scan_big_files(root="C:\\Users", min_mb=500, limit=15):
    found = []
    for r, _, files in os.walk(root, onerror=lambda e: None):
        for f in files:
            p = os.path.join(r, f)
            try:
                s = os.path.getsize(p)
            except OSError:
                continue
            if s >= min_mb * 1024**2:
                found.append((p, s))
    return sorted(found, key=lambda x: -x[1])[:limit]


# ---------- Programy ----------
def scan_programs():
    paths = [(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")]
    progs, seen = [], set()
    for hive, path in paths:
        try:
            root = winreg.OpenKey(hive, path)
        except OSError:
            continue
        for i in range(winreg.QueryInfoKey(root)[0]):
            try:
                with winreg.OpenKey(root, winreg.EnumKey(root, i)) as k:
                    def g(n):
                        try:
                            return winreg.QueryValueEx(k, n)[0]
                        except OSError:
                            return None
                    name = g("DisplayName")
                    if not name or g("SystemComponent") == 1 or (name, g("DisplayVersion")) in seen:
                        continue
                    seen.add((name, g("DisplayVersion")))
                    kb = g("EstimatedSize") or 0
                    progs.append({"name": name, "version": g("DisplayVersion") or "", "publisher": g("Publisher") or "",
                                  "date": g("InstallDate") or "", "size": int(kb) * 1024 if isinstance(kb, int) else 0})
            except OSError:
                continue
    progs.sort(key=lambda x: -x["size"])
    return progs


def scan_system_notes():
    notes = []
    info = ps_json("(Get-CimInstance Win32_OperatingSystem | Select-Object Caption,BuildNumber) | ConvertTo-Json") or []
    if info and "Windows 10" in info[0].get("Caption", ""):
        notes.append(("bad", "Windows 10 jest poza standardowym wsparciem Microsoftu (od 14.10.2025)."))
    plan = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, encoding="oem", creationflags=_NOWINDOW).stdout
    if plan:
        notes.append(("info", "Plan zasilania: " + plan.split("(")[-1].strip(") \r\n")))
    return notes
