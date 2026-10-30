@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0update-streamdeck.ps1" -StartStreamDeck
set "UPDATE_EXIT_CODE=%ERRORLEVEL%"
if not "%UPDATE_EXIT_CODE%"=="0" (
  echo Stream Deck plugin update failed.
  pause
  endlocal
  exit /b %UPDATE_EXIT_CODE%
)
echo Stream Deck plugins are up to date.
endlocal
exit /b 0
