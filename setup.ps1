# 一括セットアップ。ポータブルPython、依存ライブラリ、選択プラグイン、サーバー自動起動を設定する。
[CmdletBinding()]
param(
    [ValidateSet("Dial", "Mic", "Both", "None")]
    [string]$Plugins = ""
)

    # 同時実行されるsetup.batを防ぎ、プラグイン・サーバー・Python環境が競合しないようにする。
    $setupMutex = New-Object System.Threading.Mutex($false, "Global\DialAudioMixerSetup")
    if (-not $setupMutex.WaitOne(30000)) {
        throw "Another setup is already running. Wait for it to finish, then run setup.bat again."
    }

    # スクリプトの処理中断設定と、リポジトリ配下の各パスを定義する。
    $ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeRoot = Join-Path $RepositoryRoot ".runtime"
$PythonRoot = Join-Path $RuntimeRoot "python"
$PythonExe = Join-Path $PythonRoot "python.exe"
$ServerRoot = Join-Path $RepositoryRoot "server"

# 再実行時は既存サーバーを停止し、古いモジュール設定やライブラリ読み込みを残さない。
try {
    $listeners = Get-NetTCPConnection -LocalPort 8823 -State Listen -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
        try {
            $processId = $listener.OwningProcess
            $process = Get-Process -Id $processId -ErrorAction Stop
            $expectedPython = [System.IO.Path]::GetFullPath($PythonExe).ToLowerInvariant()
            $actualProcessPath = if ($process.Path) {
                [System.IO.Path]::GetFullPath($process.Path).ToLowerInvariant()
            } else {
                ""
            }
            if ($actualProcessPath -eq $expectedPython) {
                Stop-Process -Id $processId -Force -ErrorAction Stop
                Write-Host "Stopped the existing local server (PID $processId)."
            }
        } catch {
            Write-Warning "Could not stop the existing server process: $($_.Exception.Message)"
        }
    }
} catch {
    # 古いWindows環境や権限不足でもセットアップを継続できるよう、取得失敗は警告だけにする。
    Write-Warning "Could not inspect the port 8823 listener."
}

# ポート解放前にサーバーを再起動しないよう、リスナーが消えるまで短時間待機する。
$serverStopDeadline = (Get-Date).AddSeconds(5)
while ((Get-Date) -lt $serverStopDeadline) {
    $remainingListeners = @(Get-NetTCPConnection -LocalPort 8823 -State Listen -ErrorAction SilentlyContinue)
    if ($remainingListeners.Count -eq 0) { break }
    Start-Sleep -Milliseconds 100
}

# 64ビットWindows x64以外では、互換性を保証できないためインストールを停止する。
if ([System.Environment]::Is64BitOperatingSystem -ne $true -or
    [System.Environment]::Is64BitProcess -ne $true) {
    throw "This installer supports 64-bit Windows x64 only."
}

# Stream Deck Softwareが必要なため、事前インストールと正常起動可能な状態を確認する。
$streamDeckExecutable = "C:\Program Files\Elgato\StreamDeck\StreamDeck.exe"
if (-not (Test-Path -LiteralPath $streamDeckExecutable)) {
    throw "Stream Deck Software was not found. Install Stream Deck Software first, then run setup.bat."
}

# HTTPSでPythonやライブラリを安全に取得できるようTLS 1.2を指定する。
[Net.ServicePointManager]::SecurityProtocol =
    [Net.SecurityProtocolType]::Tls12

# Plugins引数が指定されていない場合は、各機能を y/nで個別に選択する。
if ([string]::IsNullOrWhiteSpace($Plugins)) {
    Write-Host ""
    Write-Host "Select plugins to install (y/n):"
    Write-Host ""

    function ConvertToYesNo {
        param([string]$Value)
        if ($Value.Trim().ToLowerInvariant() -in @("y", "yes")) {
            return $true
        }
        if ($Value.Trim().ToLowerInvariant() -in @("", "n", "no")) {
            return $false
        }
        return $null
    }

    function ReadYesNo {
        param([string]$Prompt)
        while ($true) {
            $choice = Read-Host $Prompt
            $result = ConvertToYesNo $choice
            if ($null -ne $result) {
                return $result
            }
            Write-Host "Please enter y or n."
        }
    }

    $installMicChoice = ReadYesNo "Install Mic Controller? (y/n)"
    $installDialChoice = ReadYesNo "Install Dial Audio Mixer? (y/n)"

    if ($installMicChoice -and $installDialChoice) {
        $Plugins = "Both"
    } elseif ($installMicChoice) {
        $Plugins = "Mic"
    } elseif ($installDialChoice) {
        $Plugins = "Dial"
    } else {
        $Plugins = "None"
    }
}

# ポータブルPythonが未配置の場合だけ、埋め込み版をダウンロードしてpipを有効化する。
if (-not (Test-Path -LiteralPath $PythonExe)) {
    New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
    $pythonUrl = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
    $pythonZip = Join-Path $RuntimeRoot "python-3.12.10-embed-amd64.zip"
    Write-Host "Downloading portable Python..."
    Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZip
    Expand-Archive -LiteralPath $pythonZip -DestinationPath $PythonRoot -Force
    Remove-Item -LiteralPath $pythonZip -Force

    $pthFile = Get-ChildItem -LiteralPath $PythonRoot -Filter "python*._pth" | Select-Object -First 1
    if ($null -eq $pthFile) { throw "Portable Python configuration file was not created." }
    @("python312.zip", ".", "Lib\site-packages", "import site") |
        Set-Content -LiteralPath $pthFile.FullName -Encoding ASCII

    $getPip = Join-Path $RuntimeRoot "get-pip.py"
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip
    & $PythonExe $getPip "--no-warn-script-location"
    Remove-Item -LiteralPath $getPip -Force
}

# 再実行時に埋め込みPythonが存在するがpipだけ不足している状態も修復する。
& $PythonExe -m pip --version *> $null
if ($LASTEXITCODE -ne 0) {
    New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
    $getPip = Join-Path $RuntimeRoot "get-pip.py"
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip
    & $PythonExe $getPip "--no-warn-script-location"
    Remove-Item -LiteralPath $getPip -Force
}

# サーバーに必要な共通ライブラリと、選択に応じたhidapiライブラリを一覧化する。
$requirements = @(
    "flask",
    "psutil",
    "pywin32",
    "pycaw",
    "comtypes",
    "Pillow"
)
if ($Plugins -eq "Mic" -or $Plugins -eq "Both") {
    $requirements += "hidapi==0.14.0.post4"
}

# ポータブルPythonを使用して依存ライブラリをインストールする。
Write-Host "Installing server dependencies..."
& $PythonExe -m pip install --disable-pip-version-check --upgrade $requirements
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

# 選択したプラグインをサーバー側の設定ファイルに保存し、不要な機能をロードしないようにする。
$installDial = $Plugins -eq "Dial" -or $Plugins -eq "Both"
$installMic = $Plugins -eq "Mic" -or $Plugins -eq "Both"
@{
    dial = $installDial
    mic = $installMic
} | ConvertTo-Json -Depth 3 |
    Set-Content -LiteralPath (Join-Path $ServerRoot "installed_plugins.json") -Encoding UTF8

# Stream Deckへ選択したプラグインを一括登録するため、更新スクリプトを呼び出す。
$updateArguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
    (Join-Path $RepositoryRoot "update-streamdeck.ps1"), "-StartStreamDeck")
if ($installDial) { $updateArguments += "-InstallDial" }
if ($installMic) { $updateArguments += "-InstallMic" }
if (-not $installDial -and -not $installMic) { $updateArguments += "-NoSelection" }
& powershell.exe @updateArguments
if ($LASTEXITCODE -ne 0) { throw "Stream Deck plugin installation failed." }

# インストール完了後にローカルサーバーを起動し、必要なら起動完了を最大15秒待機する。
Write-Host ""
Write-Host "Starting the local server..."

# 再実行時は停止済みのため、新しい設定と依存ライブラリを読み込むサーバーを必ず起動する。
Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RepositoryRoot\server-launcher.ps1`"" `
    -WorkingDirectory $RepositoryRoot

$serverReady = $false

if (-not $serverReady) {
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:8823/health" -TimeoutSec 2 | Out-Null
            $serverReady = $true
            break
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
}
if (-not $serverReady) {
    throw "The server did not start. Check start-server.bat for Python or dependency errors."
}

# Windowsログイン時にサーバーを自動起動するショートカットをスタートアップへ作成する。
$startupFolder = [Environment]::GetFolderPath("Startup")
$startupShortcut = Join-Path $startupFolder "DialAudioMixer-Server.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($startupShortcut)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$RepositoryRoot\server-launcher.ps1`""
$shortcut.WorkingDirectory = $RepositoryRoot
$shortcut.Save()

Write-Host ""
Write-Host "Setup complete."
Write-Host "The server is running and will start automatically after Windows sign-in."
