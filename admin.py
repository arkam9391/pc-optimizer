"""Analiza wymagająca administratora. Skrypt jest WYŁĄCZNIE do odczytu; wynik trafia do pliku JSON w %TEMP%."""
import base64
import json
import os
import subprocess
import tempfile
import time

OUT = os.path.join(tempfile.gettempdir(), "pcopt_admin.json")

_READ_ONLY_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$o = [ordered]@{}
$o.disks = @(Get-PhysicalDisk | ForEach-Object { $r = $_ | Get-StorageReliabilityCounter
  [pscustomobject]@{Name=$_.FriendlyName; Media=[string]$_.MediaType; Health=[string]$_.HealthStatus; Temp=$r.Temperature;
    Wear=$r.Wear; ReadErr=$r.ReadErrorsTotal; WriteErr=$r.WriteErrorsTotal; Hours=$r.PowerOnHours} })
$o.smart = @(Get-CimInstance -Namespace root\wmi -ClassName MSStorageDriver_FailurePredictStatus | ForEach-Object {
  [pscustomobject]@{Instance=$_.InstanceName; PredictFailure=$_.PredictFailure} })
$o.shadow = (vssadmin list shadowstorage | Out-String)
$o.exclusions = @((Get-MpPreference).ExclusionPath) + @((Get-MpPreference).ExclusionProcess)
$o.boot = @(Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-Diagnostics-Performance/Operational'; Id=100} -MaxEvents 6 | ForEach-Object {
  $d = @{}; ([xml]$_.ToXml()).Event.EventData.Data | ForEach-Object { $d[$_.Name] = $_.'#text' }
  [pscustomobject]@{Time=$_.TimeCreated.ToString('yyyy-MM-dd HH:mm'); BootSec=[math]::Round([int]$d.BootTime/1000); MainPathSec=[math]::Round([int]$d.MainPathBootTime/1000); PostBootSec=[math]::Round([int]$d.BootPostBootTime/1000)} })
$o.hiber = (powercfg /a | Out-String)
$tmp = '__OUT__.tmp'
$o | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $tmp
Move-Item -Force $tmp '__OUT__'
"""


def run_elevated(script: str, visible=False, keep_open=False):
    """Uruchamia skrypt PowerShell z podniesieniem uprawnień (UAC). Zwraca True, jeśli użytkownik potwierdził UAC."""
    enc = base64.b64encode(script.encode("utf-16-le")).decode()
    args = "'-NoProfile','-ExecutionPolicy','Bypass'" + (",'-NoExit'" if keep_open else "") + f",'-EncodedCommand','{enc}'"
    style = "" if visible else " -WindowStyle Hidden"
    outer = f"try {{ Start-Process powershell -Verb RunAs{style} -ArgumentList {args} -ErrorAction Stop }} catch {{ exit 1 }}"
    r = subprocess.run(["powershell", "-NoProfile", "-Command", outer], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return r.returncode == 0


def scan_admin(progress=None):
    try:
        os.remove(OUT)
    except OSError:
        pass
    script = _READ_ONLY_SCRIPT.replace("__OUT__", OUT)
    if progress:
        progress("Potwierdź okno kontroli konta użytkownika (UAC)…")
    if not run_elevated(script):
        raise RuntimeError("Nie przyznano uprawnień administratora (UAC odrzucone).")
    t0 = time.time()
    while time.time() - t0 < 420:
        if os.path.exists(OUT):
            time.sleep(0.5)
            with open(OUT, encoding="utf-8-sig") as f:
                return json.load(f)
        if progress:
            progress(f"Analiza w toku ({int(time.time() - t0)} s)… DISM może potrwać do kilku minut.")
        time.sleep(2)
    raise RuntimeError("Przekroczono czas oczekiwania na wynik analizy.")
