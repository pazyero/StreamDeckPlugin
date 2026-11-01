@echo off
setlocal
rem setup.ps1を実行し、Python環境・ライブラリ・選択したプラグイン・サーバーをまとめてセットアップする。
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
set "SETUP_EXIT_CODE=%ERRORLEVEL%"
rem セットアップ失敗時はエラーコードを呼び出し元へ返し、終了前に結果を確認できるよう表示する。
if not "%SETUP_EXIT_CODE%"=="0" (
  echo Setup failed.
  pause
  endlocal
  exit /b %SETUP_EXIT_CODE%
)
echo Setup completed successfully.
pause
endlocal
exit /b 0
