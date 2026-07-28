#define MyAppName "SEO AI Studio V4.4"
#define MyAppVersion "4.4.0"
#define MyAppPublisher "Nhan Digital"
#define MyAppExeName "SEO_AI_Studio_V44.exe"
#define MyGuideName "Huong_Dan_Su_Dung_SEO_AI_Studio_V44.pdf"

[Setup]
AppId={{29A2FC54-1946-4499-9B18-CF59113EAE21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SEO AI Studio V4.4
DefaultGroupName=SEO AI Studio V4.4
OutputDir=installer_output
OutputBaseFilename=SEO_AI_Studio_V44_Setup
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
Source: "dist\SEO_AI_Studio_V44.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "output\pdf\{#MyGuideName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\SEO AI Studio V4.4"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\Hướng dẫn SEO AI Studio V4.4"; Filename: "{app}\{#MyGuideName}"
Name: "{autodesktop}\SEO AI Studio V4.4"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Mở SEO AI Studio V4.4"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#MyGuideName}"; Description: "Mở hướng dẫn cho người mới"; Flags: postinstall shellexec skipifsilent unchecked
