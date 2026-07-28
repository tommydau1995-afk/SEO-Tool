#define MyAppName "SEO AI Studio V4.3 Pro"
#define MyAppVersion "4.3.0"
#define MyAppPublisher "Nhan Digital"
#define MyAppExeName "SEO_AI_Studio_V43.exe"

[Setup]
AppId={{D8C76F9C-C29E-4F74-8A1D-E3F64531E432}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SEO AI Studio V4.3 Pro
DefaultGroupName=SEO AI Studio V4.3 Pro
OutputDir=installer_output
OutputBaseFilename=SEO_AI_Studio_V43_Setup
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
Source: "dist\SEO_AI_Studio_V43.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\SEO AI Studio V4.3 Pro"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\SEO AI Studio V4.3 Pro"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Mở SEO AI Studio V4.3 Pro"; Flags: nowait postinstall skipifsilent
