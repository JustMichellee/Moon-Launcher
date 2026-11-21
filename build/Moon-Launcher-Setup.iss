; Moon Launcher Windows Setup Installer Script (Inno Setup 6)

#define MyAppName "Moon Launcher"
#define MyAppVersion "2.5.1"
#define MyAppPublisher "JustMichellee"
#define MyAppURL "https://github.com/JustMichellee/Moon-Launcher"
#define MyAppExeName "Moon-Launcher-GUI.exe"
#define MyAppCliExeName "Moon-Launcher-CLI.exe"

[Setup]
AppId={{5C880629-FDF6-4E2F-A544-B5219C17E45E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/releases
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=no
LicenseFile=..\LICENSE
PrivilegesRequiredOverridesAllowed=dialog commandline
PrivilegesRequired=lowest
OutputDir=..\dist\releases
OutputBaseFilename=Moon-Launcher-Setup-v{#MyAppVersion}
SetupIconFile=..\assets\moon-icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=no
CloseApplications=yes
ChangesAssociations=yes
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop shortcut for Moon Launcher (GUI)"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "desktopcliicon"; Description: "Create a Desktop shortcut for Moon Launcher (CLI)"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associateprotocol"; Description: "Register moon:// URI Protocol (for friend invites and one-click pack install)"; GroupDescription: "System Integration:"; Flags: checkedonce
Name: "addtopath"; Description: "Add Moon Launcher CLI to Windows PATH (run Moon-Launcher-CLI from any terminal)"; GroupDescription: "System Integration:"; Flags: checkedonce

[Files]
; Main Executables
Source: "..\dist\Moon-Launcher-GUI.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\Moon-Launcher-CLI.exe"; DestDir: "{app}"; Flags: ignoreversion

; Metadata & Defaults (never overwrite existing user settings)
Source: "..\assets\moon-icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\default_icon.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\minecraft_default_icon.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\assets\minecraft_title_logo.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\version.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\friends.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "..\launcher_config.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

; Bundled Resources
Source: "..\gui\*"; DestDir: "{app}\gui"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\skins\Player.png"; DestDir: "{app}\skins"; Flags: ignoreversion onlyifdoesntexist
Source: "..\moon-sync-mod\moon-sync-1.0.0.jar"; DestDir: "{app}\moon-sync-mod"; Flags: ignoreversion
Source: "..\moon-sync-mod\moon-sync-forge-legacy-1.0.0.jar"; DestDir: "{app}\moon-sync-mod"; Flags: ignoreversion
Source: "..\moon-sync-mod\moon-ingame-fabric-1.20.1-1.0.0.jar"; DestDir: "{app}\moon-sync-mod"; Flags: ignoreversion
Source: "..\moon-sync-mod\moon-ingame-fabric-1.21.1-1.0.0.jar"; DestDir: "{app}\moon-sync-mod"; Flags: ignoreversion

[Icons]
; Start Menu & Windows Search shortcuts (always installed so app appears in Windows)
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\moon-icon.ico"; Comment: "Launch Moon Launcher Desktop Studio"
Name: "{group}\{#MyAppName} (CLI)"; Filename: "{app}\{#MyAppCliExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\moon-icon.ico"; Comment: "Launch Moon Launcher Interactive CLI"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop shortcuts
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\moon-icon.ico"; Comment: "Launch Moon Launcher Desktop Studio"; Tasks: desktopicon
Name: "{autodesktop}\{#MyAppName} (CLI)"; Filename: "{app}\{#MyAppCliExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\moon-icon.ico"; Comment: "Launch Moon Launcher Interactive CLI"; Tasks: desktopcliicon

[Registry]
; Register App Paths so Windows Run / Search / Shell resolves Moon Launcher executables anywhere
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppExeName}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppCliExeName}"; ValueType: string; ValueData: "{app}\{#MyAppCliExeName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#MyAppCliExeName}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"; Flags: uninsdeletekey

; Register moon:// URL Protocol handler
Root: HKA; Subkey: "Software\Classes\moon"; ValueType: string; ValueData: "URL:Moon Launcher Protocol"; Flags: uninsdeletekey; Tasks: associateprotocol
Root: HKA; Subkey: "Software\Classes\moon"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""; Flags: uninsdeletevalue; Tasks: associateprotocol
Root: HKA; Subkey: "Software\Classes\moon\DefaultIcon"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"",0"; Flags: uninsdeletekey; Tasks: associateprotocol
Root: HKA; Subkey: "Software\Classes\moon\shell"; Flags: uninsdeletekey; Tasks: associateprotocol
Root: HKA; Subkey: "Software\Classes\moon\shell\open"; Flags: uninsdeletekey; Tasks: associateprotocol
Root: HKA; Subkey: "Software\Classes\moon\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: associateprotocol

; Optionally add install directory to user PATH
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}')); Tasks: addtopath

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#MyAppCliExeName}"; Description: "Launch {#MyAppName} (CLI)"; Flags: nowait postinstall unchecked skipifsilent

[Code]
function NeedsAddPath(Param: string): Boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + UpperCase(Param) + ';', ';' + UpperCase(OrigPath) + ';') = 0;
end;
