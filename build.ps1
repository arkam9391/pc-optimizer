# Buduje PCOptimizer.exe (PyInstaller) i instalator z wyborem folderu (Inno Setup).
# Uzycie: powershell -File build.ps1   (wersja z version.py). Wynik: dist\PCOptimizer-Setup-<wersja>.exe + .sha256
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$ver = (Select-String -Path version.py -Pattern '__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value

# Budowa w krotkiej sciezce (Windows ogranicza sciezki do 260 znakow, PySide6 ma gleboko zagniezdzone pliki)
$work = Join-Path $env:TEMP "pcopt-build"
if (Test-Path $work) { Remove-Item $work -Recurse -Force }
New-Item -ItemType Directory $work | Out-Null

python make_icon.py
if ($LASTEXITCODE) { throw "Generowanie ikony nie powiodlo sie" }
python -m PyInstaller --noconfirm --clean --windowed --name PCOptimizer --icon "$PSScriptRoot\icon.ico" `
    --distpath "$work\dist" --workpath "$work\build" --specpath "$work" main.py
if ($LASTEXITCODE) { throw "PyInstaller nie powiodl sie" }

$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Brak Inno Setup 6 (winget install JRSoftware.InnoSetup)" }
& $iscc "/DAppVersion=$ver" "/DSourceDir=$work\dist\PCOptimizer" "/DOutDir=$PSScriptRoot\dist" installer.iss
if ($LASTEXITCODE) { throw "Inno Setup nie powiodl sie" }

$setup = "dist\PCOptimizer-Setup-$ver.exe"
$hash = (Get-FileHash $setup -Algorithm SHA256).Hash.ToLower()
"$hash  $(Split-Path $setup -Leaf)" | Set-Content "$setup.sha256" -Encoding ascii
"Gotowe: $setup ($hash)"
