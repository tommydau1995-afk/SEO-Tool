#define MyAppName "SEO AI Studio V4"
#define MyAppVersion "4.0.0"
#define MyAppPublisher "Nhan Digital"
#define MyAppExeName "SEO_AI_Studio_V4.exe"

[Setup]
AppId={{1E291A69-ED5E-44C4-B623-048D2A70A0C4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SEO AI Studio V4
DefaultGroupName=SEO AI Studio V4
OutputDir=installer_output
OutputBaseFilename=SEO_AI_Studio_V4_Setup
SetupIconFile=assets\seo_ai_studio_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng ngoài Desktop"; Flags: unchecked

[Files]
Source: "dist\SEO_AI_Studio_V4.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\SEO AI Studio V4"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\SEO AI Studio V4"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Mở SEO AI Studio V4"; Flags: nowait postinstall skipifsilent
