; Instalator PC Optimizer (Inno Setup 6). Parametry podaje build.ps1: /DAppVersion /DSourceDir /DOutDir
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6C1F7E2A-4B53-4D0E-9A41-5E0C8D7B2F13}
AppName=PC Optimizer
AppVersion={#AppVersion}
AppPublisher=PC Optimizer
DefaultDirName={autopf}\PC Optimizer
DefaultGroupName=PC Optimizer
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={#OutDir}
OutputBaseFilename=PCOptimizer-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\PCOptimizer.exe
CloseApplications=yes
RestartApplications=yes

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "Utwórz skrót na pulpicie"; GroupDescription: "Skróty:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\PC Optimizer"; Filename: "{app}\PCOptimizer.exe"
Name: "{autodesktop}\PC Optimizer"; Filename: "{app}\PCOptimizer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PCOptimizer.exe"; Description: "Uruchom PC Optimizer"; Flags: nowait postinstall skipifsilent
