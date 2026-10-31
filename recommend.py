"""Zalecane akcje zwalniające miejsce na C: (tylko odczyt rozmiarów, nic nie jest usuwane).
Wiersz akcji: dict(key, title, sub, gain, changes, level). gain = bajty albo None, gdy zysku nie da się oszacować."""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import scanners as sc

GB = 1024 ** 3


def _file(path):
    try:
        return os.stat(path).st_size
    except OSError:
        return 0


def measure():
    """Rozmiary miejsc, z których da się odzyskać miejsce. Rozmiary chronionych folderów bywają zaniżone bez uprawnień administratora."""
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    win = Path(os.environ.get("WINDIR", r"C:\Windows"))
    user = Path(os.environ.get("USERPROFILE", ""))
    dirs = {
        "temp_user": Path(os.environ.get("TEMP", "")), "temp_sys": win / "Temp",
        "wu": win / "SoftwareDistribution" / "Download", "dumps": local / "CrashDumps",
        "minidump": win / "Minidump", "bin": Path("C:/$Recycle.Bin"), "winold": Path("C:/Windows.old"),
        "downloads": user / "Downloads",
    }
    with ThreadPoolExecutor(8) as ex:
        sizes = dict(zip(dirs, ex.map(lambda p: sc.dir_size(p) if p.is_dir() else 0, dirs.values())))
    sizes["hiber"] = _file(r"C:\hiberfil.sys")
    sizes["memdump"] = _file(win / "MEMORY.DMP")
    # tylko programy z C: (albo bez znanej lokalizacji); odinstalowanie programów z innych dysków nie zwolni miejsca na C:
    progs = [p for p in sc.scan_programs() if p["size"] >= GB and (not p["location"] or p["location"].strip('"')[:2].upper() == "C:")][:3]
    sizes["programs"] = [(p["name"], p["size"]) for p in progs]
    return sizes


def _gb(n):
    return sc.gb(n)


def build_actions(s):
    """Zamienia pomiary na listę zaleceń, od największego zysku."""
    rows = []
    if s["hiber"] > GB:
        rows.append(dict(key="hiber", title="Wyłącz hibernację", gain=s["hiber"], changes=True,
                         sub="Usuwa plik hiberfil.sys razem z szybkim startem. Na laptopie tracisz hibernację, cofniesz ją poleceniem powercfg /h on"))
    parts = [(n, v) for n, v in (("pliki tymczasowe", s["temp_user"] + s["temp_sys"]), ("cache Windows Update", s["wu"]),
                                 ("zrzuty awarii", s["dumps"] + s["minidump"] + s["memdump"]), ("Windows.old", s["winold"])) if v > 50 * 1024 ** 2]
    clean = sum(v for _, v in parts)
    if clean:
        rows.append(dict(key="cleanmgr", title="Oczyszczanie dysku", gain=clean, changes=True,
                         sub="Zaznacz w oknie: " + ", ".join(f"{n} {_gb(v)}" for n, v in sorted(parts, key=lambda x: -x[1]))))
    if s["bin"] > 50 * 1024 ** 2:
        rows.append(dict(key="bin", title="Opróżnij kosz", gain=s["bin"], changes=False,
                         sub="Sprawdź zawartość kosza i opróżnij go, jeśli nic z niego nie potrzebujesz"))
    rows.sort(key=lambda r: -r["gain"])
    rows.append(dict(key="dism", title="Czyszczenie składników Windows", gain=None, changes=True,
                     sub="Usuwa zastąpione składniki z WinSxS. Zysk zwykle kilka GB, dokładną wartość pokaże analiza DISM (kilkanaście minut)"))
    if s["programs"]:
        rows.append(dict(key="apps", title="Odinstaluj duże programy", gain=None, changes=False,
                         sub="Największe: " + ", ".join(f"{n} ({_gb(v)})" for n, v in s["programs"])))
    if s["downloads"] > GB:
        rows.append(dict(key="downloads", title="Przejrzyj folder Pobrane", gain=None, changes=False,
                         sub=f"Zajmuje {_gb(s['downloads'])}. Instalatory i archiwa zwykle można usunąć albo przenieść na D:"))
    rows.append(dict(key="analyze", title="Znajdź największe foldery na C:", gain=None, changes=False,
                     sub="Zakładka Dyski pokaże, co zajmuje miejsce poza Windows i programami"))
    rows.append(dict(key="storage", title="Włącz Czujnik pamięci", gain=None, changes=False,
                     sub="Windows sam czyści pliki tymczasowe i kosz w ustawionych odstępach"))
    for r in rows:
        r["level"] = "warn" if (r["gain"] or 0) >= 5 * GB else "info"
    return rows
