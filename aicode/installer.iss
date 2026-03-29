; ===================================================
;  Smart Document Categorizer - Inno Setup Script
;  Creates a professional setup.exe installer
; ===================================================

#define MyAppName "Smart Document Categorizer"
#define MyAppNameShort "SmartDocCategorizer"
#define MyAppVersion "1.0"
#define MyAppPublisher "Reda Ghareeb"
#define MyAppURL "https://github.com/redaghareeb"
#define MyAppExeName "SmartDocCategorizer.exe"

[Setup]
AppId={{B8F3A1D2-7C4E-4A9B-8D6F-2E5C1B3A4D7E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppNameShort}
DefaultGroupName={#MyAppName}
; Output setup.exe location and name
OutputDir=installer_output
OutputBaseFilename=SmartDocCategorizer_Setup_v{#MyAppVersion}
; Installer appearance
SetupIconFile=icon.ico
WizardStyle=modern
WizardSizePercent=120

; FIX: Reduced compression level to prevent 32-bit Out of Memory crashes
Compression=lzma2/normal
SolidCompression=yes
LZMANumBlockThreads=2

; Permissions
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Uninstaller
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
; Misc
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
; Size estimate
ExtraDiskSpaceRequired=0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startmenu"; Description: "Create Start Menu shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\SmartDocCategorizer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  Size: Int64;
begin
  if CurStep = ssPostInstall then
  begin
    Size := 0;
    RegWriteDWordValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1',
      'EstimatedSize', 3000000);
  end;
end;