#define AppVersion GetEnv("OPENCLAW_VERSION")
#define SourceExe GetEnv("OPENCLAW_SOURCE_EXE")
#define ReleaseDir GetEnv("OPENCLAW_RELEASE_DIR")

[Setup]
AppId={{2B90A7A8-6AA1-4D1C-A47A-3D5B693F0BE6}
AppName=OpenClaw
AppVersion={#AppVersion}
AppPublisher=John Graven
DefaultDirName={localappdata}\Programs\OpenClaw
DefaultGroupName=OpenClaw
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#ReleaseDir}
OutputBaseFilename=OpenClaw-Build-{#AppVersion}-Windows-Setup
SetupIconFile=..\..\static\img\openclaw.ico
UninstallDisplayIcon={app}\OpenClaw.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes
VersionInfoVersion={#AppVersion}

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "OpenClaw.exe"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\BUILD_NOTES.md"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Icons]
Name: "{group}\OpenClaw"; Filename: "{app}\OpenClaw.exe"
Name: "{autodesktop}\OpenClaw"; Filename: "{app}\OpenClaw.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\OpenClaw.exe"; Description: "Launch OpenClaw"; Flags: nowait postinstall skipifsilent
