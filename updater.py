"""Aktualizacje z GitHub Releases: sprawdzenie najnowszego wydania, pobranie instalatora z weryfikacją SHA-256."""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request

from version import GITHUB_REPO, INSTALLER_PREFIX, __version__

API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
_HEADERS = {"User-Agent": "PCOptimizer-updater", "Accept": "application/vnd.github+json"}


def _vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:4])


def check_update():
    """Zwraca {"version", "notes", "url", "sha_url", "page"} gdy jest nowsze wydanie, None gdy aktualne, {"__error__": ...} przy błędzie."""
    try:
        req = urllib.request.Request(API, headers=_HEADERS)
        rel = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
    except Exception as e:
        return {"__error__": f"Nie udało się sprawdzić aktualizacji: {e}"}
    ver = (rel.get("tag_name") or "").lstrip("vV")
    if _vtuple(ver) <= _vtuple(__version__):
        return None
    assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
    exe = next((n for n in assets if n.startswith(INSTALLER_PREFIX) and n.endswith(".exe")), None)
    if not exe:
        return {"__error__": "Wydanie nie zawiera instalatora"}
    return {"version": ver, "notes": (rel.get("body") or "").strip(), "url": assets[exe],
            "sha_url": assets.get(exe + ".sha256"), "page": rel.get("html_url")}


def download_installer(info, progress=None):
    """Pobiera instalator do %TEMP% i sprawdza sumę SHA-256. Zwraca ścieżkę albo rzuca wyjątek."""
    if not info.get("sha_url"):
        raise RuntimeError("Wydanie nie ma pliku sumy kontrolnej (.sha256), pomijam instalację")
    want = urllib.request.urlopen(urllib.request.Request(info["sha_url"], headers=_HEADERS), timeout=15).read().decode().split()[0].lower()
    path = os.path.join(tempfile.gettempdir(), os.path.basename(info["url"]))
    h = hashlib.sha256()
    with urllib.request.urlopen(urllib.request.Request(info["url"], headers=_HEADERS), timeout=30) as r, open(path, "wb") as f:
        total, got = int(r.headers.get("Content-Length") or 0), 0
        while chunk := r.read(1 << 18):
            f.write(chunk); h.update(chunk); got += len(chunk)
            if progress and total:
                progress(f"Pobieranie: {got * 100 // total}%")
    if h.hexdigest() != want:
        os.remove(path)
        raise RuntimeError("Suma kontrolna instalatora się nie zgadza, plik usunięto")
    return path


def run_installer(path):
    """Uruchamia instalator po cichu w tym samym folderze; program zamyka się, instalator uruchamia go ponownie."""
    subprocess.Popen([path, "/SILENT", "/SUPPRESSMSGBOXES", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"],
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
