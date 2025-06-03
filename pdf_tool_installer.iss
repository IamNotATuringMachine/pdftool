; Script for Inno Setup
; Defines how to build the installer for PDF Tool

#define MyAppName "PDF Tool"
#define MyAppVersion "1.0"
#define MyAppPublisher "Your Name/Company" ; You can change this
#define MyAppURL "https://www.example.com/" ; You can change this
#define MyAppExeName "pdf_tool.exe"
#define MyAppExePath "D:\\pdf\\dist" ; Path to the executable created by PyInstaller

[Setup]
AppId={{AUTO_GUID}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userappdata}\\{#MyAppName}
DisableProgramGroupPage=yes
; PrivilegesRequired directive removed for compatibility with older Inno Setup versions
; Installation will go to user's AppData folder which doesn't require admin privileges
OutputDir=D:\\pdf\\installer_output ; Where the final setup.exe will be saved
OutputBaseFilename=pdf_tool_setup
SetupIconFile=D:\pdf\Gartoon-Team-Gartoon-Apps-System-software-installer.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyAppExePath}\\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Add any other files your application needs here. For example:
; Source: "D:\\pdf\\dist\\another_file.dll"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"
Name: "{autodesktop}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent 