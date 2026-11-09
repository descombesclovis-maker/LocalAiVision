; LocalAiStudio — installateur Windows NSIS (compilé automatiquement, aussi sous Linux : makensis)
; makensis -DROOT=<dossier contenant backend et frontend> LocalAiStudio.nsi
; Alternative Inno Setup : LocalAiStudio.iss + build-installer.bat
Unicode true
ManifestDPIAware true
!ifndef ROOT
  !define ROOT ".."
!endif
!define KIT ".."
!define APP "LocalAiStudio"
!define VERSION "1.0.0"
!define UNINST "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP}"
!define HF "https://huggingface.co/Comfy-Org"
!addplugindir /x86-unicode "nsis-plugins\x86-unicode"

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "Sections.nsh"
!include "x64.nsh"

Name "${APP}"
OutFile "Output\Installer-${APP}.exe"
InstallDir "C:\${APP}"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
BrandingText "${APP} ${VERSION} · IA 100 % locale et gratuite"
ShowInstDetails show

Var ModelsDir

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_WELCOMEPAGE_TITLE "Installer ${APP}"
!define MUI_WELCOMEPAGE_TEXT "Cet assistant installe ${APP} (LocalAiWeb + LocalAiVision) sur votre PC.$\r$\n$\r$\nIl télécharge et installe automatiquement Python, Node.js, MongoDB, Ollama, ComfyUI Desktop et les modèles IA (FLUX, Wan 2.2, Qwen), avec une barre de progression pour chaque fichier, puis crée le raccourci sur le Bureau.$\r$\n$\r$\nPrévoyez environ 60 Go d'espace libre et une bonne connexion (les modèles pèsent environ 45 Go)."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!define MUI_PAGE_HEADER_TEXT "Dossier des modèles ComfyUI"
!define MUI_PAGE_HEADER_SUBTEXT "Où ComfyUI range-t-il ses modèles ?"
!define MUI_DIRECTORYPAGE_TEXT_TOP "Les modèles FLUX et Wan 2.2 seront rangés dans ce dossier (sous-dossiers checkpoints, diffusion_models, text_encoders, vae). ComfyUI Desktop utilise par défaut Documents\ComfyUI\models."
!define MUI_DIRECTORYPAGE_VARIABLE $ModelsDir
!define MUI_PAGE_CUSTOMFUNCTION_PRE SkipModelsDir
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\start-localaistudio.bat"
!define MUI_FINISHPAGE_RUN_TEXT "Lancer ${APP} maintenant"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\INSTALLATION.md"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Ouvrir le guide"
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "French"

; ---------------------------------------------------------------- helpers
!macro Download URL DEST LABEL
  DetailPrint "Téléchargement : ${LABEL}"
  inetc::get /CAPTION "${LABEL}" /RESUME "Connexion interrompue : réessayer ?" "${URL}" "${DEST}" /END
  Pop $0
  ${If} $0 != "OK"
    DetailPrint "Échec du téléchargement de ${LABEL} : $0"
    MessageBox MB_ICONEXCLAMATION|MB_OK "Échec du téléchargement de ${LABEL} ($0).$\r$\nVous pourrez relancer l'installateur plus tard : les éléments déjà installés seront conservés."
  ${EndIf}
!macroend

!macro Model URL SUB FILE LABEL
  CreateDirectory "$ModelsDir\${SUB}"
  ${IfNot} ${FileExists} "$ModelsDir\${SUB}\${FILE}"
    !insertmacro Download "${URL}" "$ModelsDir\${SUB}\${FILE}" "${LABEL}"
  ${Else}
    DetailPrint "${LABEL} : déjà présent"
  ${EndIf}
!macroend

Function .onInit
  ${If} ${RunningX64}
    SetRegView 64
  ${Else}
    MessageBox MB_ICONSTOP "${APP} nécessite Windows 64 bits."
    Abort
  ${EndIf}
  StrCpy $ModelsDir "$DOCUMENTS\ComfyUI\models"
FunctionEnd

; ---------------------------------------------------------------- sections
Section "${APP} (obligatoire)" SecCore
  SectionIn RO
  SetOutPath "$INSTDIR\backend"
  File /r /x __pycache__ /x .venv /x *.pyc /x tests /x .env /x .env.* /x .pytest_cache /x pytest.ini /x .api_key /x .boot_token /x bench_runs /x *.key /x *.pem "${ROOT}\backend\*.*"
  SetOutPath "$INSTDIR\frontend"
  File /r /x node_modules /x dist /x .vite /x .env /x .env.* /x yarn-error.log /x .screenshots "${ROOT}\frontend\*.*"
  SetOutPath "$INSTDIR"
  File "${KIT}\*.ps1"
  File "${KIT}\*.bat"
  File "${KIT}\*.md"
  File "${KIT}\requirements-local.txt"
  ${IfNot} ${FileExists} "$INSTDIR\backend\.env"
    File "/oname=$INSTDIR\backend\.env" "env.template"
  ${EndIf}
  CreateDirectory "$SMPROGRAMS\${APP}"
  CreateShortCut "$SMPROGRAMS\${APP}\${APP}.lnk" "$INSTDIR\start-localaistudio.bat" "" "$SYSDIR\shell32.dll" 13
  CreateShortCut "$SMPROGRAMS\${APP}\Tunnel preview.lnk" "$INSTDIR\tunnel-preview.bat"
  CreateShortCut "$SMPROGRAMS\${APP}\Désinstaller.lnk" "$INSTDIR\Uninstall.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "${UNINST}" "DisplayName" "${APP}"
  WriteRegStr HKLM "${UNINST}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "${UNINST}" "Publisher" "${APP}"
  WriteRegStr HKLM "${UNINST}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKLM "${UNINST}" "InstallLocation" "$INSTDIR"
SectionEnd

Section "Python, Node.js, MongoDB et Ollama" SecTools
  SectionIn RO
  nsExec::ExecToStack 'cmd /c python --version'
  Pop $0
  ${If} $0 != 0
    !insertmacro Download "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" "$TEMP\python-setup.exe" "Python 3.11"
    DetailPrint "Installation de Python 3.11…"
    ExecWait '"$TEMP\python-setup.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0'
  ${Else}
    DetailPrint "Python : déjà installé"
  ${EndIf}
  nsExec::ExecToStack 'cmd /c node --version'
  Pop $0
  ${If} $0 != 0
    !insertmacro Download "https://nodejs.org/dist/v20.18.0/node-v20.18.0-x64.msi" "$TEMP\node-setup.msi" "Node.js 20 LTS"
    DetailPrint "Installation de Node.js…"
    ExecWait 'msiexec /i "$TEMP\node-setup.msi" /qn /norestart'
  ${Else}
    DetailPrint "Node.js : déjà installé"
  ${EndIf}
  ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Services\MongoDB" "ImagePath"
  ${If} $0 == ""
    !insertmacro Download "https://fastdl.mongodb.org/windows/mongodb-windows-x86_64-7.0.14-signed.msi" "$TEMP\mongodb-setup.msi" "MongoDB 7"
    DetailPrint "Installation de MongoDB (service Windows)…"
    ExecWait 'msiexec /i "$TEMP\mongodb-setup.msi" /qn /norestart ADDLOCAL="ServerService" SHOULD_INSTALL_COMPASS="0"'
  ${Else}
    DetailPrint "MongoDB : déjà installé"
  ${EndIf}
  ${IfNot} ${FileExists} "$LOCALAPPDATA\Programs\Ollama\ollama.exe"
    !insertmacro Download "https://ollama.com/download/OllamaSetup.exe" "$TEMP\ollama-setup.exe" "Ollama"
    DetailPrint "Installation d'Ollama…"
    ExecWait '"$TEMP\ollama-setup.exe" /VERYSILENT /NORESTART /SUPPRESSMSGBOXES'
  ${Else}
    DetailPrint "Ollama : déjà installé"
  ${EndIf}
SectionEnd

Section "ComfyUI Desktop (photos, retouches, pubs, vidéos)" SecComfy
  !insertmacro Download "https://download.comfy.org/windows/nsis/x64" "$TEMP\comfyui-setup.exe" "ComfyUI Desktop"
  DetailPrint "Installation de ComfyUI Desktop…"
  ExecWait '"$TEMP\comfyui-setup.exe" /S'
SectionEnd

Section "Modèles photo et vidéo : FLUX.1 dev + Wan 2.2 (≈ 35 Go)" SecModels
  AddSize 36000000
  !insertmacro Model "${HF}/flux1-dev/resolve/main/flux1-dev-fp8.safetensors" "checkpoints" "flux1-dev-fp8.safetensors" "FLUX.1 dev fp8 (17 Go)"
  !insertmacro Model "${HF}/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors" "diffusion_models" "wan2.2_ti2v_5B_fp16.safetensors" "Wan 2.2 TI2V 5B (10 Go)"
  !insertmacro Model "${HF}/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" "text_encoders" "umt5_xxl_fp8_e4m3fn_scaled.safetensors" "Encodeur UMT5 (6,7 Go)"
  !insertmacro Model "${HF}/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan2.2_vae.safetensors" "vae" "wan2.2_vae.safetensors" "VAE Wan 2.2 (1,4 Go)"
SectionEnd

Section "Modèle de texte qwen2.5-coder 14B pour les sites (≈ 9 Go)" SecText
SectionEnd

Section "Raccourci sur le Bureau" SecDesktop
  SetShellVarContext current
  CreateShortCut "$DESKTOP\${APP}.lnk" "$INSTDIR\start-localaistudio.bat" "" "$SYSDIR\shell32.dll" 13
SectionEnd

Section "-Dépendances" SecDeps
  ${If} ${SectionIsSelected} ${SecText}
    StrCpy $1 ""
  ${Else}
    StrCpy $1 "-SkipTextModel"
  ${EndIf}
  DetailPrint "Installation des dépendances Python et de l'interface (5 à 30 min, une fenêtre affiche l'avancement)…"
  ExecWait 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\install.ps1" -Unattended $1' $0
  DetailPrint "Dépendances : code de sortie $0"
SectionEnd

Function SkipModelsDir
  ${IfNot} ${SectionIsSelected} ${SecModels}
    Abort
  ${EndIf}
FunctionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Application LocalAiStudio (backend FastAPI + interface React)."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecTools} "Installés seulement s'ils sont absents de votre PC."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecComfy} "Moteur local des photos, retouches, publicités et vidéos (utilise votre carte NVIDIA)."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecModels} "FLUX.1 dev pour les photos, Wan 2.2 pour les vidéos et la vidéo d'en-tête des sites."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecText} "Modèle Ollama utilisé pour écrire les sites web, 100 % local."
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Icône LocalAiStudio sur le Bureau pour tout démarrer d'un double-clic."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "Uninstall"
  SetRegView 64
  SetShellVarContext current
  Delete "$DESKTOP\${APP}.lnk"
  RMDir /r "$SMPROGRAMS\${APP}"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKLM "${UNINST}"
SectionEnd
