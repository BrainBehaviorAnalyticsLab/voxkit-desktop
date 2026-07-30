#define AppName "VoxKit"

; AppVersion is read from config/VERSION (single source of truth).
#define VersionFile "..\..\config\VERSION"
#define VersionHandle FileOpen(VersionFile)
#if VersionHandle
  #define AppVersion Trim(FileRead(VersionHandle))
  #expr FileClose(VersionHandle)
#else
  #error "Could not open config/VERSION"
#endif
#define AppPublisher "Brain Behavior Analytics Lab"
#define AppURL "https://github.com/BrainBehaviorAnalyticsLab/voxkit-desktop"
#define AppExeName "VoxKit.exe"

[Setup]
AppId={{A3F2C1D4-8B7E-4F6A-9D2E-1C5B3A7E8F90}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=VoxKit-setup-windowsOS
SetupIconFile=..\..\assets\voxkit.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
