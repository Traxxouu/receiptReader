; ─────────────────────────────────────────────
; Receipt Reader - Windows Installer (NSIS)
; Compile avec : makensis installer.nsi
; ─────────────────────────────────────────────

!include "MUI2.nsh"
!include "LogicLib.nsh"

; ── Infos générales
Name "Receipt Reader"
OutFile "ReceiptReaderSetup.exe"
InstallDir "$PROGRAMFILES64\ReceiptReader"
InstallDirRegKey HKCU "Software\ReceiptReader" ""
RequestExecutionLevel admin
Unicode True

; ── Variables
Var PythonFound
Var OllamaFound

; ── Interface MUI
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"
!define MUI_HEADERIMAGE
!define MUI_BGCOLOR "FFFFFF"
!define MUI_TEXTCOLOR "1A1A1A"
!define MUI_WELCOMEFINISHPAGE_BITMAP "${NSISDIR}\Contrib\Graphics\Wizard\win.bmp"

; ── Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
Page custom InstallPage InstallPageLeave
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ── Langue
!insertmacro MUI_LANGUAGE "French"

; ── Page d'installation personnalisée
Function InstallPage
    nsDialogs::Create 1018
    Pop $0

    ${NSD_CreateLabel} 0 0 100% 20u "Composants a installer :"
    Pop $0

    ${NSD_CreateCheckBox} 10 30 100% 12u "Python 3.11 (requis)"
    Pop $0
    SendMessage $0 ${BM_SETCHECK} 1 0

    ${NSD_CreateCheckBox} 10 50 100% 12u "Ollama (moteur IA local)"
    Pop $0
    SendMessage $0 ${BM_SETCHECK} 1 0

    ${NSD_CreateCheckBox} 10 70 100% 12u "Receipt Reader + dependances Python"
    Pop $0
    SendMessage $0 ${BM_SETCHECK} 1 0

    ${NSD_CreateLabel} 0 100 100% 30u "Une connexion internet est necessaire pour telecharger les composants."
    Pop $0

    nsDialogs::Show
FunctionEnd

Function InstallPageLeave
FunctionEnd

; ── Section principale
Section "Installation" SecMain
    SetOutPath "$INSTDIR"

    ; ── Télécharger et installer Python si absent
    DetailPrint "Verification de Python..."
    nsExec::ExecToStack 'python --version'
    Pop $PythonFound
    ${If} $PythonFound != 0
        DetailPrint "Telechargement de Python 3.11..."
        inetc::get /CAPTION "Telechargement de Python..." \
            "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" \
            "$TEMP\python_installer.exe" /END
        DetailPrint "Installation de Python..."
        ExecWait '"$TEMP\python_installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0'
        Delete "$TEMP\python_installer.exe"
    ${Else}
        DetailPrint "Python deja installe."
    ${EndIf}

    ; ── Télécharger et installer Ollama si absent
    DetailPrint "Verification d'Ollama..."
    nsExec::ExecToStack 'ollama --version'
    Pop $OllamaFound
    ${If} $OllamaFound != 0
        DetailPrint "Telechargement d'Ollama..."
        inetc::get /CAPTION "Telechargement d'Ollama..." \
            "https://ollama.com/download/OllamaSetup.exe" \
            "$TEMP\OllamaSetup.exe" /END
        DetailPrint "Installation d'Ollama..."
        ExecWait '"$TEMP\OllamaSetup.exe" /S'
        Delete "$TEMP\OllamaSetup.exe"
    ${Else}
        DetailPrint "Ollama deja installe."
    ${EndIf}

    ; ── Cloner le repo
    DetailPrint "Telechargement de Receipt Reader..."
    nsExec::ExecToLog 'git clone https://github.com/Traxxouu/receiptReader "$INSTDIR\app"'
    ${If} ${Errors}
        ; Si git pas dispo, télécharger le zip
        DetailPrint "Git non trouve, telechargement du zip..."
        inetc::get /CAPTION "Telechargement..." \
            "https://github.com/Traxxouu/receiptReader/archive/refs/heads/main.zip" \
            "$TEMP\receiptreader.zip" /END
        nsExec::ExecToLog 'powershell -Command "Expand-Archive -Path $TEMP\receiptreader.zip -DestinationPath $INSTDIR -Force"'
        Rename "$INSTDIR\receiptReader-main" "$INSTDIR\app"
        Delete "$TEMP\receiptreader.zip"
    ${EndIf}

    ; ── Installer les dépendances Python
    DetailPrint "Installation des dependances Python..."
    nsExec::ExecToLog 'python -m pip install --upgrade pip'
    nsExec::ExecToLog 'python -m pip install -r "$INSTDIR\app\requirements.txt"'

    ; ── Télécharger le modèle Ollama
    DetailPrint "Telechargement du modele IA (llama3.2, ~2GB, patience...)..."
    nsExec::ExecToLog 'ollama pull llama3.2'

    ; ── Créer le lanceur .bat
    FileOpen $0 "$INSTDIR\ReceiptReader.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "start /B ollama serve > nul 2>&1$\r$\n"
    FileWrite $0 "timeout /t 2 /nobreak > nul$\r$\n"
    FileWrite $0 'python "$INSTDIR\app\app.py"$\r$\n'
    FileClose $0

    ; ── Créer raccourci bureau
    CreateShortcut "$DESKTOP\Receipt Reader.lnk" "$INSTDIR\ReceiptReader.bat" "" "$INSTDIR\app\icon.ico"

    ; ── Créer raccourci menu démarrer
    CreateDirectory "$SMPROGRAMS\Receipt Reader"
    CreateShortcut "$SMPROGRAMS\Receipt Reader\Receipt Reader.lnk" "$INSTDIR\ReceiptReader.bat"
    CreateShortcut "$SMPROGRAMS\Receipt Reader\Desinstaller.lnk" "$INSTDIR\uninstall.exe"

    ; ── Écrire les infos de désinstallation
    WriteUninstaller "$INSTDIR\uninstall.exe"
    WriteRegStr HKCU "Software\ReceiptReader" "" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ReceiptReader" \
        "DisplayName" "Receipt Reader"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ReceiptReader" \
        "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ReceiptReader" \
        "DisplayVersion" "1.0"

SectionEnd

; ── Section désinstallation
Section "Uninstall"
    RMDir /r "$INSTDIR\app"
    Delete "$INSTDIR\ReceiptReader.bat"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"

    Delete "$DESKTOP\Receipt Reader.lnk"
    RMDir /r "$SMPROGRAMS\Receipt Reader"

    DeleteRegKey HKCU "Software\ReceiptReader"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ReceiptReader"
SectionEnd
