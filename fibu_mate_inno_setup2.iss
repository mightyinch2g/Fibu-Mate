#define MyAppName "FiBu Mate"
#define MyAppVersion "0.4.37"
#define MyAppPublisher "Wagnerm"
#define MyAppExeName "FiBuMate.exe"

#define SourceDir "C:\python\dist\FiBuMate"
#define AssetDir "C:\python\bin\Imgs"
#define OutputDir "G:\BUC\FM Anwendung"

[Setup]
AppId={{7F4D6F5E-8F67-4A5B-9E9C-0F1B0A7E0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppVerName={#MyAppName} {#MyAppVersion}

DefaultDirName={localappdata}\FibuMate
UsePreviousAppDir=yes
DisableDirPage=no

DefaultGroupName=FiBu Mate
DisableProgramGroupPage=no

OutputDir={#OutputDir}
OutputBaseFilename=FiBu_Mate_Installer

SetupIconFile={#AssetDir}\FMLogo_App.ico
WizardImageFile={#AssetDir}\FMLogo_Installer_Large.bmp
WizardSmallImageFile={#AssetDir}\FMLogo_Installer_Small.bmp

UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=FiBu Mate Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

CloseApplications=yes
RestartIfNeededByRun=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Verknüpfungen:"; Flags: unchecked

[Dirs]
Name: "{app}\config"
Name: "{app}\logs"
Name: "{app}\cache"
Name: "{app}\Backup"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FiBu Mate"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\FiBu Mate"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "FiBu Mate jetzt starten"; Flags: nowait postinstall skipifsilent

[Code]
procedure CreateLocalConfig();
var
  ConfigPath: string;
  JsonText: string;
begin
  ConfigPath := ExpandConstant('{app}\config\local_config.json');

  JsonText :=
    '{' + #13#10 +
    '  "app_name": "FiBu Mate",' + #13#10 +
    '  "app_version": "{#MyAppVersion}",' + #13#10 +
    '  "install_dir": "' + ExpandConstant('{app}') + '",' + #13#10 +
    '  "deployment_mode": "local_per_user",' + #13#10 +
    '  "network_root": "G:\\BUC\\FM Anwendung",' + #13#10 +
    '  "output_dir": "G:\\BUC\\FM Anwendung\\Dateiausgabe",' + #13#10 +
    '  "database_dir": "G:\\BUC\\FM Anwendung\\Datenbasen",' + #13#10 +
    '  "database_config_path": "G:\\BUC\\FM Anwendung\\Fibu_Mate_Doc\\Config\\database_config.json",' + #13#10 +
    '  "database_path": "G:\\BUC\\FM Anwendung\\Datenbasen\\fibu_mate.db",' + #13#10 +
    '  "release_dir": "G:\\BUC\\FM Anwendung\\Fibu_Mate_Doc\\Releases",' + #13#10 +
    '  "update_manifest_path": "G:\\BUC\\FM Anwendung\\Fibu_Mate_Doc\\Releases\\latest.json",' + #13#10 +
    '  "logs_dir": "G:\\BUC\\FM Anwendung\\Fibu_Mate_Doc\\Logs",' + #13#10 +
    '  "patching_enabled": false,' + #13#10 +
    '  "sqlite_enabled": true' + #13#10 +
    '}';

  SaveStringToFile(ConfigPath, JsonText, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    CreateLocalConfig();
  end;
end;