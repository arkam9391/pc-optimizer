"""Skan sterowników: odczyt zainstalowanych + sprawdzenie najnowszej wersji w Microsoft Update Catalog."""
import html
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from descriptions import describe
from scanners import ps_json

CATALOG = "https://www.catalog.update.microsoft.com/Search.aspx?q="
IMPORTANT = {"DISPLAY", "NET", "MEDIA", "SYSTEM", "BLUETOOTH", "HDC", "SCSIADAPTER", "USB", "HIDCLASS", "FIRMWARE", "BIOS"}
VENDOR_LINKS = {
    "nvidia": "https://www.nvidia.com/Download/index.aspx",
    "intel": "https://www.intel.com/content/www/us/en/download-center/home.html",
    "lenovo": "https://support.lenovo.com/pl/pl/downloads",
    "realtek": "https://www.realtek.com/Download",
}


def _hw_key(hwid):
    """Wyciąga identyfikator do wyszukiwania w katalogu, np. VEN_10DE&DEV_1C8D."""
    s = hwid if isinstance(hwid, str) else (hwid[0] if hwid else "")
    m = re.search(r"VEN_[0-9A-F]{4}&DEV_[0-9A-F]{4}", s, re.I) or re.search(r"VID_[0-9A-F]{4}&PID_[0-9A-F]{4}", s, re.I)
    return m.group(0).upper() if m else None


def _vtuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:4])


def _parse_date(s):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            pass
    return None


def catalog_latest(key):
    """Zwraca najnowszy wpis katalogu dla klucza sprzętu (zgodny z Windows 10) albo None."""
    try:
        req = urllib.request.Request(CATALOG + urllib.parse.quote(key), headers={"User-Agent": "Mozilla/5.0"})
        page = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
    except Exception:
        return "error"
    best = None
    for row in re.findall(r'<tr id="[^"]+_R\d+".*?</tr>', page, re.S):
        c = [html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip() for x in re.findall(r"<td.*?</td>", row, re.S)]
        if len(c) < 6 or not c[3].startswith("Drivers") or "Windows 10" not in c[2]:
            continue
        date = _parse_date(c[4])
        ver = c[5] if c[5] and c[5] != "n/a" else (re.search(r"(\d+\.\d+\.\d+(?:\.\d+)?)\s*$", c[1]) or [None, ""])[1]
        if not date or not ver:
            continue
        if best is None or (date, _vtuple(ver)) > (best["date"], _vtuple(best["version"])):
            best = {"title": c[1], "date": date, "version": ver}
    return best


def scan_drivers(progress=None):
    raw = ps_json(
        "Get-CimInstance Win32_PnPSignedDriver | Where-Object {$_.DeviceName -and $_.DriverVersion} | "
        "Select-Object DeviceName,DeviceClass,DriverVersion,DriverProviderName,Manufacturer,HardWareID,"
        "@{n='Date';e={if($_.DriverDate){$_.DriverDate.ToString('yyyy-MM-dd')}}} | ConvertTo-Json -Depth 2",
        timeout=180) or []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    seen, items = set(), []
    for d in raw:
        cls = (d.get("DeviceClass") or "").upper()
        prov = (d.get("DriverProviderName") or d.get("Manufacturer") or "").strip()
        if cls not in IMPORTANT or (prov.lower() == "microsoft" and cls not in {"DISPLAY", "NET", "MEDIA", "BLUETOOTH"}):
            continue
        key = (d["DeviceName"], d["DriverVersion"])
        if key in seen:
            continue
        seen.add(key)
        date = _parse_date(d.get("Date"))
        if date and date.year < 1995:  # pusta data sterownika bywa zapisana jako 1601/1970, nie pokazujemy jej
            date = None
        link = next((u for k, u in VENDOR_LINKS.items() if k in prov.lower() or k in d["DeviceName"].lower()), None)
        hw = _hw_key(d.get("HardWareID"))
        items.append({"name": d["DeviceName"], "cls": cls.title(), "version": d["DriverVersion"],
                      "date": date.strftime("%Y-%m-%d") if date else "—", "provider": prov, "hwkey": hw,
                      "desc": describe(d["DeviceName"], cls), "link": link,
                      "age": (now - date).days / 365 if date else None,
                      "latest": None, "status": "unknown",
                      "catalog": CATALOG + urllib.parse.quote(hw) if hw else None})
    items = [i for i in items if i["hwkey"] or "microsoft" not in i["provider"].lower()]
    keys = sorted({i["hwkey"] for i in items if i["hwkey"]})
    done = [0]

    def look(k):
        r = catalog_latest(k)
        done[0] += 1
        if progress:
            progress(f"Sprawdzam najnowsze wersje: {done[0]}/{len(keys)}")
        return k, r

    with ThreadPoolExecutor(6) as ex:
        found = dict(ex.map(look, keys))
    for i in items:
        r = found.get(i["hwkey"])
        if r is None:
            i["status"] = "ok" if i["hwkey"] else "unknown"
            i["note"] = "Brak nowszego sterownika w katalogu Microsoft" if i["hwkey"] else "Brak identyfikatora sprzętu"
        elif r == "error":
            i["status"], i["note"] = "unknown", "Nie udało się połączyć z katalogiem Microsoft"
        else:
            i["latest"] = {"version": r["version"], "date": r["date"].strftime("%Y-%m-%d"), "title": r["title"]}
            newer = _vtuple(r["version"]) > _vtuple(i["version"]) and (i["date"] == "—" or r["date"].strftime("%Y-%m-%d") >= i["date"])
            i["status"] = "newer" if newer else "ok"
            i["note"] = "Dostępna nowsza wersja" if newer else "Masz aktualną wersję"
    order = {"newer": 0, "unknown": 1, "ok": 2}
    items.sort(key=lambda x: (order[x["status"]], x["cls"], x["name"]))
    return items
