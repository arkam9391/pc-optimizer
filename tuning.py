"""Odczyt ustawień wpływających na wydajność (tylko odczyt). Wiersz: (klucz statusu, element, stan, zalecenie)."""
import os
import winreg
from datetime import datetime

import psutil

import disks
import scanners as sc


def _reg(hive, path, name):
    try:
        with winreg.OpenKey(hive, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def scan_tuning():
    rows = []
    days = (datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds() / 86400
    fast = _reg(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Power", "HiberbootEnabled")
    rows.append(("warn" if days > 7 else "ok", "Czas od ostatniego restartu", f"{days:.0f} dni",
                 "Uruchom ponownie system" + (" (szybki start sprawia, że „Zamknij” go nie odświeża)" if fast else "")))
    rows.append(("info" if fast else "ok", "Szybki start", "włączony" if fast else "wyłączony",
                 "Wyłącz razem z hibernacją, jeśli nie jest potrzebna" if fast else "Bez uwag"))
    hf = r"C:\hiberfil.sys"
    try:
        size = os.stat(hf).st_size
    except OSError:
        size = 0
    rows.append(("warn" if size > 4 * 1024 ** 3 else "ok", "Plik hibernacji", sc.gb(size) if size else "brak",
                 "powercfg /h off zwolni to miejsce (utracisz hibernację)" if size else "Bez uwag"))
    media = {d["letter"]: d["media"] for d in disks.scan_drives()}
    pf = sc.ps_json("Get-CimInstance Win32_PageFileUsage | Select-Object Name,AllocatedBaseSize,CurrentUsage | ConvertTo-Json") or []
    for p in pf:
        letter = p["Name"][0].upper()
        slow = media.get(letter) == "HDD"
        rows.append(("warn" if slow else "ok", "Plik wymiany", f"{p['Name']} · {p['AllocatedBaseSize']} MB ({media.get(letter, '?')})",
                     "Przenieś na SSD (C:), np. 4096–8192 MB" if slow else "Bez uwag"))
    vfx = _reg(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting")
    vfx = 0 if vfx is None else vfx
    names = {0: "wybór Windows (domyślne)", 1: "najlepszy wygląd", 2: "najlepsza wydajność", 3: "ustawienia niestandardowe"}
    rows.append(("info" if vfx in (0, 1) else "ok", "Efekty wizualne", names.get(vfx, "?"),
                 "Opcjonalnie: najlepsza wydajność (drobny zysk)" if vfx in (0, 1) else "Bez uwag"))
    plan = sc.subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, encoding="oem",
                             creationflags=sc._NOWINDOW).stdout
    plan = plan.split("(")[-1].strip(") \r\n") if "(" in plan else "?"
    rows.append(("info", "Plan zasilania", plan, "Przy zasilaniu z sieci możesz wybrać „Wysoka wydajność”"))
    progs = [p["name"] for p in sc.scan_programs()]
    db = [n for n in progs if "driver booster" in n.lower()]
    rows.append(("bad" if db else "ok", "Driver Booster", db[0] if db else "nie znaleziono",
                 "Odinstaluj (zadanie SkipUAC obchodzi UAC)" if db else "Bez uwag"))
    start = sc.scan_startup()
    heavy = [s["name"] for s in start if s["impact"] == "Duży"]
    edge = [s["name"] for s in start if s["name"].startswith("MicrosoftEdgeAutoLaunch")]
    rows.append(("warn" if len(start) > 12 else "ok", "Autostart", f"{len(start)} pozycji, w tym {len(heavy)} o dużym wpływie",
                 "Wyłącz niepotrzebne w Menedżerze zadań (odwracalne)"))
    if edge:
        rows.append(("info", "Edge uruchamia się w tle", "włączone", "Wyłącz w ustawieniach Edge lub autostarcie"))
    return rows
