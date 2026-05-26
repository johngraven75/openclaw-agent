@echo off
setlocal
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\OpenClaw Agent"
set "DESKTOP=%USERPROFILE%\Desktop"
set "ONEDRIVE_DESKTOP=%USERPROFILE%\OneDrive\Documents\Desktop"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
copy /Y "%~dp0OpenClaw.exe" "%INSTALL_DIR%\OpenClaw.exe" >nul
copy /Y "%~dp0BUILD_NOTES_openclaw_build107.md" "%INSTALL_DIR%\BUILD_NOTES_openclaw_build107.md" >nul
copy /Y "%~dp0README.md" "%INSTALL_DIR%\README.md" >nul
if not exist "%DESKTOP%" mkdir "%DESKTOP%"
(
  echo @echo off
  echo start "" "%LOCALAPPDATA%\Programs\OpenClaw Agent\OpenClaw.exe"
) > "%DESKTOP%\START OpenClaw Build 1.0.7.bat"
if exist "%ONEDRIVE_DESKTOP%" (
  (
    echo @echo off
    echo start "" "%LOCALAPPDATA%\Programs\OpenClaw Agent\OpenClaw.exe"
  ) > "%ONEDRIVE_DESKTOP%\START OpenClaw Build 1.0.7.bat"
)
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop') + '\OpenClaw Build 1.0.7.lnk'); $s.TargetPath=$env:LOCALAPPDATA + '\Programs\OpenClaw Agent\OpenClaw.exe'; $s.WorkingDirectory=$env:LOCALAPPDATA + '\Programs\OpenClaw Agent'; $s.IconLocation=$env:LOCALAPPDATA + '\Programs\OpenClaw Agent\OpenClaw.exe'; $s.Save()" >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "$desktop=$env:USERPROFILE + '\Desktop'; if(Test-Path $desktop){$s=(New-Object -COM WScript.Shell).CreateShortcut($desktop + '\OpenClaw Build 1.0.7.lnk'); $s.TargetPath=$env:LOCALAPPDATA + '\Programs\OpenClaw Agent\OpenClaw.exe'; $s.WorkingDirectory=$env:LOCALAPPDATA + '\Programs\OpenClaw Agent'; $s.IconLocation=$env:LOCALAPPDATA + '\Programs\OpenClaw Agent\OpenClaw.exe'; $s.Save()}" >nul 2>nul
start "" "%INSTALL_DIR%\OpenClaw.exe"
exit /b 0
