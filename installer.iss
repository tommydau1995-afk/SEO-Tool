#define MyAppName "SEO AI Studio V2"
#define MyAppVersion "2.0.0"
#define MyAppExeName "SEO_AI_Studio_V2.exe"

[Setup]
AppId={{4AC9F433-7087-49CC-8F6F-AFB8F4557CB2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\SEO AI Studio V2
DefaultGroupName=SEO AI Studio V2
OutputDir=installer_output
OutputBaseFilename=SEO_AI_Studio_V2_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài Desktop"

[Files]
Source: "dist\SEO_AI_Studio_V2.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\SEO AI Studio V2"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\SEO AI Studio V2"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Mở SEO AI Studio V2"; Flags: nowait postinstall skipifsilent
