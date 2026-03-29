[Setup]
AppName=Smart Categorizer AI Core
AppVersion=1.0
DefaultDirName={autopf}\SmartCategorizer_AICore
OutputDir=installer_output
OutputBaseFilename=Smart_Categorizer_AI_Core_Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin

[Files]
Source: "install_ai_core.bat"; DestDir: "{app}"; Flags: ignoreversion

[Run]
; Run the batch script silently to install everything
Filename: "{app}\install_ai_core.bat"; Flags: waituntilterminated runhidden