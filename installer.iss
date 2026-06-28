; Inno Setup skript – inštalátor pre "Voľba poradia vystúpenia kandidátov na dekana"
; Verzia sa odovzdáva pri kompilácii: ISCC.exe /DMyAppVersion=1.1.0 installer.iss

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

#define MyAppName "Voľba poradia dekana"
#define MyAppExeName "VolbaPoradiaDekana.exe"
#define MyAppPublisher "Juraj Jablonický"
#define MyAppURL "https://github.com/Juraj145/GenerovanieNahodnejVolby_DEKAN"

[Setup]
AppId={{B3A1F6E2-7C4D-4E9A-9C21-9D2D6F0A1B77}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\GNV_DEKAN
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_out
OutputBaseFilename=VolbaPoradiaDekana_Setup
SetupIconFile=app.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "slovak"; MessagesFile: "compiler:Languages\Slovak.isl"

[Tasks]
Name: "desktopicon"; Description: "Vytvoriť ikonu na ploche"; GroupDescription: "Doplnkové úlohy:"

[Files]
Source: "dist\VolbaPoradiaDekana\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Odinštalovať {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Spustiť {#MyAppName}"; Flags: nowait postinstall skipifsilent
