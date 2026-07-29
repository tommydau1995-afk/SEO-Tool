#define MyAppName "SEO AI Studio V4.7"
#define MyAppVersion "4.7.0"
#define MyAppPublisher "Nhan Digital"
#define MyAppExeName "SEO_AI_Studio_V47.exe"
#define MyGuideName "Huong_Dan_Chi_Tiet_SEO_AI_Studio_V47.pdf"

[Setup]
AppId={{A9B9B7A8-2B33-4EB8-B5A5-6547D797E0CA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SEO AI Studio V4.7
DefaultGroupName=SEO AI Studio V4.7
OutputDir=installer_output
OutputBaseFilename=SEO_AI_Studio_V47_Setup
SetupIconFile=assets\seo_ai_studio_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
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
Source: "dist\SEO_AI_Studio_V47.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "output\pdf\{#MyGuideName}"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
Type: files; Name: "{app}\SEO_AI_Studio_V46.exe"
Type: files; Name: "{app}\Huong_Dan_Chi_Tiet_SEO_AI_Studio_V46.pdf"

[Icons]
Name: "{autoprograms}\SEO AI Studio V4.7"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\Hướng dẫn chi tiết SEO AI Studio V4.7"; Filename: "{app}\{#MyGuideName}"
Name: "{autodesktop}\SEO AI Studio V4.7"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Mở SEO AI Studio V4.7"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#MyGuideName}"; Description: "Mở hướng dẫn chi tiết"; Flags: postinstall shellexec skipifsilent unchecked
