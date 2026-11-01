# Stream Deck用プラグインを選択してインストール・更新するスクリプト。
[CmdletBinding()]
param(
    [switch]$StartStreamDeck,
    [string]$Elevated = "",
    [switch]$InstallDial,
    [switch]$InstallMic,
    [switch]$NoSelection
)

# エラーを例外として扱い、スクリプト配下のパスにアクセスする。
$ErrorActionPreference = "Stop"

# 現在の権限を確認し、管理者権限がない場合はUAC経由で再実行する。
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdministrator = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdministrator -and $Elevated -ne "1") {
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -StartStreamDeck -Elevated 1"
    if ($InstallDial) { $arguments += " -InstallDial" }
    if ($InstallMic) { $arguments += " -InstallMic" }
    if ($NoSelection) { $arguments += " -NoSelection" }
    $launcherProcess = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $arguments `
        -Verb RunAs `
        -PassThru

    if ($null -eq $launcherProcess) {
        Write-Error "Failed to start the elevated update process."
        exit 125
    }

    if (-not $launcherProcess.WaitForExit(30000)) {
        Write-Warning "The elevated update process exceeded 30 seconds."
        exit 124
    }

    exit $launcherProcess.ExitCode
}

# リポジトリのソースとStream Deckユーザープラグインフォルダーを特定する。
$RepositoryRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourcePluginRoot = Join-Path $RepositoryRoot "streamdeck"
$PluginRoot = Join-Path $env:APPDATA "Elgato\StreamDeck\Plugins"
$StreamDeckExecutable = "C:\Program Files\Elgato\StreamDeck\StreamDeck.exe"

if (-not (Test-Path -LiteralPath $SourcePluginRoot)) {
    throw "Stream Deck source folder not found: $SourcePluginRoot"
}

# 引数で選択されたプラグインだけをコピー対象に絞り込む。
$sourcePlugins = @(Get-ChildItem -LiteralPath $SourcePluginRoot -Directory |
    Where-Object { $_.Name -like "*.sdPlugin" })

$selectionWasSpecified = $InstallDial -or $InstallMic -or $NoSelection
if (-not $selectionWasSpecified) {
    # 選択引数がない既存呼び出し向けに、互換性として両プラグインを選択する。
    $InstallDial = $true
    $InstallMic = $true
}

$sourcePlugins = @($sourcePlugins | Where-Object {
    ($InstallDial -and $_.Name -eq "com.shay.dialaudiomixer.sdPlugin") -or
    ($InstallMic -and $_.Name -eq "com.shay.miccontroller.sdPlugin")
})

if ($sourcePlugins.Count -eq 0) {
    if (-not $NoSelection) {
        throw "No *.sdPlugin folders found under: $SourcePluginRoot"
    }
}

# コピー前に実行中のStream Deck Softwareを停止し、プラグイン更新中の競合を防ぐ。
$runningProcesses = @(Get-Process -Name "StreamDeck" -ErrorAction SilentlyContinue)

foreach ($process in $runningProcesses) {
    try {
        Stop-Process -Id $process.Id -Force
    } catch {
        throw "Stream Deck (PID $($process.Id)) could not be stopped: $($_.Exception.Message)"
    }
}

if ($runningProcesses.Count -gt 0) {
    $deadline = (Get-Date).AddSeconds(5)
    while ((Get-Process -Name "StreamDeck" -ErrorAction SilentlyContinue).Count -gt 0 -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 100
    }
    if ((Get-Process -Name "StreamDeck" -ErrorAction SilentlyContinue).Count -gt 0) {
        throw "Stream Deck did not exit within 5 seconds."
    }
}

# Stream Deckのユーザープラグインフォルダーを作成し、インストール先へ追加する。
New-Item -ItemType Directory -Force -Path $PluginRoot | Out-Null

# 選択されなかった既存プラグインは削除し、選択結果とインストール状態を一致させる。
$knownPluginNames = @(
    "com.shay.dialaudiomixer.sdPlugin",
    "com.shay.miccontroller.sdPlugin"
)
foreach ($knownPluginName in $knownPluginNames) {
    $destinationPlugin = Join-Path $PluginRoot $knownPluginName
    $shouldInstall = ($knownPluginName -eq "com.shay.dialaudiomixer.sdPlugin" -and $InstallDial) -or
                     ($knownPluginName -eq "com.shay.miccontroller.sdPlugin" -and $InstallMic)
    if (-not $shouldInstall -and (Test-Path -LiteralPath $destinationPlugin)) {
        Remove-Item -LiteralPath $destinationPlugin -Recurse -Force
        Write-Host "Removed unselected plugin: $knownPluginName"
    }
}

# robocopyで各プラグインを完全同期し、更新や不要ファイル削除も反映する。
foreach ($sourcePlugin in $sourcePlugins) {
    $destinationPlugin = Join-Path $PluginRoot $sourcePlugin.Name
    New-Item -ItemType Directory -Force -Path $destinationPlugin | Out-Null

    & robocopy.exe $sourcePlugin.FullName $destinationPlugin /MIR /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -gt 7) {
        throw "Failed to copy $($sourcePlugin.Name) (robocopy exit code $LASTEXITCODE)"
    }

    Write-Host "$($sourcePlugin.Name) installed or updated at: $destinationPlugin"
}

# インストール時または更新時にStream Deck Softwareを再起動する。
if ($StartStreamDeck -or $runningProcesses.Count -gt 0) {
    if (-not (Test-Path -LiteralPath $StreamDeckExecutable)) {
        throw "Stream Deck executable not found: $StreamDeckExecutable"
    }
    Start-Process -FilePath $StreamDeckExecutable
    if ($runningProcesses.Count -gt 0) {
        Write-Host "Stream Deck restarted."
    } else {
        Write-Host "Stream Deck started."
    }
}
