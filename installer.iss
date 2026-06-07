; installer.iss
; Inno Setup Script for Goofy Focus
; Use Inno Setup Compiler (ISCC) or the Inno Setup GUI to compile this into a standalone Setup EXE.

[Setup]
AppName=Goofy Focus
AppVersion=1.0.0
AppPublisher=Arun Kumar M
DefaultDirName={localappdata}\GoofyFocus
DefaultGroupName=Goofy Focus
UninstallDisplayIcon={app}\GoofyFocus.exe
Compression=lzma2
SolidCompression=yes
OutputDir=dist
OutputBaseFilename=GoofyFocusSetup
SetupIconFile=assets\icon.ico
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\GoofyFocus\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Goofy Focus"; Filename: "{app}\GoofyFocus.exe"
Name: "{group}\{cm:UninstallProgram,Goofy Focus}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Goofy Focus"; Filename: "{app}\GoofyFocus.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\GoofyFocus.exe"; Description: "{cm:LaunchProgram,Goofy Focus}"; Flags: nowait postinstall skipifsilent
