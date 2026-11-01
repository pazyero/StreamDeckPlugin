# このスクリプトはWindowsログイン時やセットアップ完了後にローカルサーバーを起動する。
$ErrorActionPreference = "Stop"

# リポジトリ内のポータブルPythonとserver.pyへのパスを組み立てる。
$RepositoryRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $RepositoryRoot ".runtime\python\python.exe"
$ServerScript = Join-Path $RepositoryRoot "server\server.py"

# セットアップ前に実行された場合は、setup.batを先に実行するよう案内して終了する。
if (-not (Test-Path -LiteralPath $PythonExe)) {
    Write-Error "Portable Python is not installed. Run setup.bat first."
    exit 1
}

# サーバーがすでに起動している場合は二重起動せず、処理を終了する。
try {
    Invoke-RestMethod -Uri "http://127.0.0.1:8823/health" -TimeoutSec 2 | Out-Null
    exit 0
} catch {
}

# サーバーが未起動の場合だけPythonでserver.pyを起動する。
& $PythonExe "-u" $ServerScript
exit $LASTEXITCODE
