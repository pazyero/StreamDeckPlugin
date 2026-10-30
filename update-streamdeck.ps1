[CmdletBinding()]
param(
    [switch]$StartStreamDeck,
    [string]$Elevated = ""
)

$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdministrator = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdministrator -and $Elevated -ne "1") {
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -StartStreamDeck -Elevated 1"
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

$RepositoryRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourcePluginRoot = Join-Path $RepositoryRoot "streamdeck"
$PluginRoot = Join-Path $env:APPDATA "Elgato\StreamDeck\Plugins"
$StreamDeckExecutable = "C:\Program Files\Elgato\StreamDeck\StreamDeck.exe"

if (-not (Test-Path -LiteralPath $SourcePluginRoot)) {
    throw "Stream Deck source folder not found: $SourcePluginRoot"
}

$sourcePlugins = @(Get-ChildItem -LiteralPath $SourcePluginRoot -Directory |
    Where-Object { $_.Name -like "*.sdPlugin" })

if ($sourcePlugins.Count -eq 0) {
    throw "No *.sdPlugin folders found under: $SourcePluginRoot"
}

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

New-Item -ItemType Directory -Force -Path $PluginRoot | Out-Null

foreach ($sourcePlugin in $sourcePlugins) {
    $destinationPlugin = Join-Path $PluginRoot $sourcePlugin.Name
    New-Item -ItemType Directory -Force -Path $destinationPlugin | Out-Null

    & robocopy.exe $sourcePlugin.FullName $destinationPlugin /MIR /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -gt 7) {
        throw "Failed to copy $($sourcePlugin.Name) (robocopy exit code $LASTEXITCODE)"
    }

    Write-Host "$($sourcePlugin.Name) installed or updated at: $destinationPlugin"
}

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
