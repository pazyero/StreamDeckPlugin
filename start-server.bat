@echo off
setlocal
rem リポジトリ内に配置したポータブルPythonの実行ファイルを指定する。
set "PYTHON_EXE=%~dp0.runtime\python\python.exe"
if not exist "%PYTHON_EXE%" (
  echo Portable Python is not installed.
  echo Run setup.bat first.
  pause
  endlocal
  exit /b 1
)
rem Flaskサーバーを直接起動し、ローカルAPIをポート8823で提供する。
"%PYTHON_EXE%" "%~dp0server\server.py"
set "SERVER_EXIT_CODE=%ERRORLEVEL%"
rem サーバー起動または実行中にエラーが発生した場合は終了コードと案内を表示する。
if not "%SERVER_EXIT_CODE%"=="0" (
  echo Server stopped with an error.
  pause
  endlocal
  exit /b %SERVER_EXIT_CODE%
)
endlocal
