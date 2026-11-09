; LocalAiStudio — installateur Windows (Inno Setup 6.1+ gratuit : https://jrsoftware.org/isdl.php)
; Compilation : double-cliquez sur build-installer.bat (ou : ISCC.exe LocalAiStudio.iss)
; Produit : Output\Installer-LocalAiStudio.exe
;
; Root = dossier contenant backend\ et frontend\  (kit .zip : ".." ; depot source : "..\..")
#ifndef Root
  #define Root ".."
#endif
#define KitDir ".."
#define AppVersion "1.0.0"

[Setup]
AppId={{6C1C3C7E-6E0B-4C2F-9E57-1A5A0C0A11A5}
AppName=LocalAiStudio
AppVersion={#AppVersion}
AppPublisher=LocalAiStudio
DefaultDirName={sd}\LocalAiStudio
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=Installer-LocalAiStudio
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DiskSpaceRequiredMB=4000
UninstallDisplayName=LocalAiStudio
SetupLogging=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer le raccourci LocalAiStudio sur le Bureau"; GroupDescription: "Raccourcis :"
Name: "textmodel"; Description: "Modèle de texte local qwen2.5-coder 14B pour les sites web (≈ 9 Go)"; GroupDescription: "Moteurs IA locaux (gratuits) :"
Name: "comfyui"; Description: "Installer ComfyUI Desktop (photos, retouches, pubs, vidéos)"; GroupDescription: "Moteurs IA locaux (gratuits) :"
Name: "models"; Description: "Modèles photo et vidéo : FLUX.1 dev + Wan 2.2 (≈ 35 Go)"; GroupDescription: "Moteurs IA locaux (gratuits) :"

[Files]
Source: "{#Root}\backend\*"; DestDir: "{app}\backend"; Excludes: "__pycache__,.venv,*.pyc,tests,.env,.env.*,.pytest_cache,pytest.ini,.api_key,.boot_token,bench_runs,*.key,*.pem"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Root}\frontend\*"; DestDir: "{app}\frontend"; Excludes: "node_modules,dist,.vite,.env,.env.*,yarn-error.log,.screenshots"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#KitDir}\*.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#KitDir}\*.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#KitDir}\*.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#KitDir}\requirements-local.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "env.template"; DestDir: "{app}\backend"; DestName: ".env"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{autodesktop}\LocalAiStudio"; Filename: "{app}\start-localaistudio.bat"; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 13; Tasks: desktopicon
Name: "{autoprograms}\LocalAiStudio"; Filename: "{app}\start-localaistudio.bat"; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 13
Name: "{autoprograms}\LocalAiStudio — Tunnel preview"; Filename: "{app}\tunnel-preview.bat"; WorkingDir: "{app}"

[Run]
Filename: "{tmp}\python-setup.exe"; Parameters: "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0"; StatusMsg: "Installation de Python 3.11…"; Flags: waituntilterminated; Check: NeedPython
Filename: "msiexec.exe"; Parameters: "/i ""{tmp}\node-setup.msi"" /qn /norestart"; StatusMsg: "Installation de Node.js…"; Flags: waituntilterminated; Check: NeedNode
Filename: "msiexec.exe"; Parameters: "/i ""{tmp}\mongodb-setup.msi"" /qn /norestart ADDLOCAL=""ServerService"" SHOULD_INSTALL_COMPASS=""0"""; StatusMsg: "Installation de MongoDB (base de données)…"; Flags: waituntilterminated; Check: NeedMongo
Filename: "{tmp}\ollama-setup.exe"; Parameters: "/VERYSILENT /NORESTART /SUPPRESSMSGBOXES"; StatusMsg: "Installation d'Ollama (moteur de texte local)…"; Flags: waituntilterminated; Check: NeedOllama
Filename: "{tmp}\comfyui-setup.exe"; Parameters: "/S"; StatusMsg: "Installation de ComfyUI Desktop…"; Flags: waituntilterminated; Tasks: comfyui
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\install.ps1"" -Unattended {code:TextModelFlag}"; WorkingDir: "{app}"; StatusMsg: "Installation des dépendances et du modèle de texte (5 à 30 min selon la connexion)…"; Flags: waituntilterminated
Filename: "{app}\start-localaistudio.bat"; Description: "Lancer LocalAiStudio maintenant"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}\backend\.venv"
Type: filesandordirs; Name: "{app}\frontend\node_modules"

[Code]
const
  URL_PYTHON  = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe';
  URL_NODE    = 'https://nodejs.org/dist/v20.18.0/node-v20.18.0-x64.msi';
  URL_MONGO   = 'https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-7.0.14-signed.msi';
  URL_OLLAMA  = 'https://ollama.com/download/OllamaSetup.exe';
  URL_COMFY   = 'https://download.comfy.org/windows/nsis/x64';
  HF          = 'https://huggingface.co/Comfy-Org/';

var
  DownloadPage: TDownloadWizardPage;
  ModelsPage: TInputDirWizardPage;
  HasPython, HasNode, HasMongo, HasOllama: Boolean;

function CmdOk(const Cmd: String): Boolean;
var R: Integer;
begin
  Result := Exec(ExpandConstant('{cmd}'), '/c ' + Cmd + ' >nul 2>nul', '', SW_HIDE, ewWaitUntilTerminated, R) and (R = 0);
end;

function NeedPython: Boolean; begin Result := not HasPython; end;
function NeedNode: Boolean; begin Result := not HasNode; end;
function NeedMongo: Boolean; begin Result := not HasMongo; end;
function NeedOllama: Boolean; begin Result := not HasOllama; end;

function TextModelFlag(Param: String): String;
begin
  if WizardIsTaskSelected('textmodel') then Result := '' else Result := '-SkipTextModel';
end;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if ProgressMax <> 0 then
    Log(Format('%s : %d / %d', [FileName, Progress, ProgressMax]));
  Result := True;
end;

procedure InitializeWizard;
begin
  HasPython := CmdOk('python --version');
  HasNode := CmdOk('node --version');
  HasMongo := RegKeyExists(HKLM, 'SYSTEM\CurrentControlSet\Services\MongoDB');
  HasOllama := CmdOk('where ollama') or FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe'));

  ModelsPage := CreateInputDirPage(wpSelectTasks, 'Dossier des modèles ComfyUI',
    'Où ComfyUI range-t-il ses modèles ?',
    'Les fichiers FLUX et Wan 2.2 seront rangés dans ce dossier (sous-dossiers checkpoints, diffusion_models, text_encoders, vae). ' +
    'ComfyUI Desktop utilise par défaut Documents\ComfyUI\models.', False, '');
  ModelsPage.Add('');
  ModelsPage.Values[0] := ExpandConstant('{userdocs}\ComfyUI\models');

  DownloadPage := CreateDownloadPage('Téléchargement des composants',
    'Python, Node.js, MongoDB, Ollama, ComfyUI et les modèles IA sont téléchargés (barre de progression ci-dessous).', @OnDownloadProgress);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = ModelsPage.ID) and not WizardIsTaskSelected('models');
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID <> wpReady then exit;
  DownloadPage.Clear;
  if not HasPython then DownloadPage.Add(URL_PYTHON, 'python-setup.exe', '');
  if not HasNode then DownloadPage.Add(URL_NODE, 'node-setup.msi', '');
  if not HasMongo then DownloadPage.Add(URL_MONGO, 'mongodb-setup.msi', '');
  if not HasOllama then DownloadPage.Add(URL_OLLAMA, 'ollama-setup.exe', '');
  if WizardIsTaskSelected('comfyui') then DownloadPage.Add(URL_COMFY, 'comfyui-setup.exe', '');
  if WizardIsTaskSelected('models') then
  begin
    DownloadPage.Add(HF + 'flux1-dev/resolve/main/flux1-dev-fp8.safetensors', 'flux1-dev-fp8.safetensors', '');
    DownloadPage.Add(HF + 'Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors', 'wan2.2_ti2v_5B_fp16.safetensors', '');
    DownloadPage.Add(HF + 'Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors', 'umt5_xxl_fp8_e4m3fn_scaled.safetensors', '');
    DownloadPage.Add(HF + 'Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan2.2_vae.safetensors', 'wan2.2_vae.safetensors', '');
  end;
  DownloadPage.Show;
  try
    try
      DownloadPage.Download;
    except
      if DownloadPage.AbortedByUser then
        Log('Téléchargement annulé par l''utilisateur.')
      else
        SuppressibleMsgBox(AddPeriod(GetExceptionMessage), mbCriticalError, MB_OK, IDOK);
      Result := False;
    end;
  finally
    DownloadPage.Hide;
  end;
end;

procedure PlaceModel(const FileName, SubDir: String);
var Src, Dir: String;
begin
  Src := ExpandConstant('{tmp}\') + FileName;
  if not FileExists(Src) then exit;
  Dir := AddBackslash(ModelsPage.Values[0]) + SubDir;
  ForceDirectories(Dir);
  if FileExists(Dir + '\' + FileName) then exit;
  if not RenameFile(Src, Dir + '\' + FileName) then
    FileCopy(Src, Dir + '\' + FileName, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and WizardIsTaskSelected('models') then
  begin
    WizardForm.StatusLabel.Caption := 'Rangement des modèles dans ComfyUI…';
    PlaceModel('flux1-dev-fp8.safetensors', 'checkpoints');
    PlaceModel('wan2.2_ti2v_5B_fp16.safetensors', 'diffusion_models');
    PlaceModel('umt5_xxl_fp8_e4m3fn_scaled.safetensors', 'text_encoders');
    PlaceModel('wan2.2_vae.safetensors', 'vae');
  end;
end;
