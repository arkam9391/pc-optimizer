"""Skan dysków: pojemność, typ (SSD/HDD), rozmiary folderów i duże pliki."""
import os
from concurrent.futures import ThreadPoolExecutor

import psutil

from scanners import ps_json


def scan_drives():
    info = ps_json(
        "Get-Partition | Where-Object DriveLetter | ForEach-Object { $pd = Get-Disk -Number $_.DiskNumber | Get-PhysicalDisk; "
        "[pscustomobject]@{Letter=[string]$_.DriveLetter; Media=[string]$pd.MediaType; Model=[string]$pd.FriendlyName; "
        "Health=[string]$pd.HealthStatus; Label=[string](Get-Volume -DriveLetter $_.DriveLetter).FileSystemLabel} } | ConvertTo-Json"
    ) or []
    by = {i["Letter"].upper(): i for i in info}
    drives = []
    for p in psutil.disk_partitions(all=False):
        if "cdrom" in p.opts or not p.fstype:
            continue
        try:
            u = psutil.disk_usage(p.mountpoint)
        except OSError:
            continue
        i = by.get(p.device[0].upper(), {})
        drives.append({"letter": p.device[0].upper(), "mount": p.mountpoint, "total": u.total, "used": u.used,
                       "free": u.free, "percent": u.percent, "media": i.get("Media") or "?",
                       "model": i.get("Model") or "", "health": i.get("Health") or "?", "label": i.get("Label") or ""})
    return drives


def _walk(path, big_bytes):
    size, big, stack = 0, [], [path]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for e in it:
                    try:
                        if e.is_symlink() or e.is_junction():
                            continue
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        else:
                            s = e.stat(follow_symlinks=False).st_size
                            size += s
                            if s >= big_bytes:
                                big.append((e.path, s))
                    except OSError:
                        pass
        except OSError:
            pass
    return size, big


def scan_folder(path, big_mb=300):
    """Rozmiary elementów folderu (równolegle) i duże pliki w jego wnętrzu."""
    big_bytes = big_mb * 1024 ** 2
    items, big, jobs = [], [], []
    try:
        entries = list(os.scandir(path))
    except OSError as e:
        return {"path": path, "items": [], "big": [], "total": 0, "error": str(e)}
    with ThreadPoolExecutor(8) as ex:
        for e in entries:
            try:
                if e.is_symlink() or e.is_junction():
                    continue
                if e.is_dir(follow_symlinks=False):
                    jobs.append((e, ex.submit(_walk, e.path, big_bytes)))
                else:
                    s = e.stat(follow_symlinks=False).st_size
                    items.append({"name": e.name, "path": e.path, "size": s, "is_dir": False})
                    if s >= big_bytes:
                        big.append((e.path, s))
            except OSError:
                pass
        for e, f in jobs:
            s, b = f.result()
            items.append({"name": e.name, "path": e.path, "size": s, "is_dir": True})
            big += b
    items.sort(key=lambda x: -x["size"])
    big.sort(key=lambda x: -x[1])
    return {"path": path, "items": items, "big": big[:30], "total": sum(i["size"] for i in items)}
