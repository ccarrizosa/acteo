#define AppName "Acteo"
#ifndef AppVersion
#define AppVersion "0.1.0"
#endif

[Setup]
AppId={{A1B8FE18-38E4-46AB-9DCA-4F4AD5D8B2A1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Acteo
AppCopyright=Copyright (C) Acteo contributors
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\Acteo.exe
PrivilegesRequired=lowest
OutputDir=dist\installer
OutputBaseFilename=Acteo-{#AppVersion}-Setup
Compression=lzma
SolidCompression=yes
LicenseFile=LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\Acteo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Acteo.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Acteo.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\Acteo.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
