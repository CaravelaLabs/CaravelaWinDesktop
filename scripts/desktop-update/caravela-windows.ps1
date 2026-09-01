# caravela-windows.ps1 — Caravela product update hand-off.
#
# Copied into the branded checkout by rebrand.py. The branded
# updater-process.ts prefers this file over stock windows.ps1.
#
# hermes update follows git `origin`. Stock Hermes installs point origin at
# NousResearch/hermes-agent, so Update rebuilt the Hermes GUI. Pin origin to
# the Caravela product repo first, then run the upstream Windows hand-off
# (venv unlock, hermes update, desktop rebuild, relaunch).
#
# electron-builder productName=Caravela writes win-unpacked\Caravela.exe.
# A GitHub NSIS install also drops Program Files\Caravela\Caravela.exe.
# Clicking Update used to rebuild the git tree, miss Hermes.exe, report
# failure, and relaunch process.execPath (Program Files). This wrapper
# pins relaunch + Start Menu/Desktop at the unpacked Caravela.exe.
param(
    [string]$InstallRoot,
    [string]$Branch = "main",
    [int]$DesktopPid = 0,
    [string]$RelaunchExe = "",
    [switch]$NoUi,
    [switch]$NoMarkerCleanup,
    [switch]$SelfTestUi,
    [switch]$SelfTestPipeDrain,
    [switch]$SelfTestMarker,
    [switch]$RetargetShortcuts
)

$ErrorActionPreference = "Continue"
$ProductOrigin = "https://github.com/CaravelaLabs/CaravelaWinDesktop.git"

function Get-CaravelaUnpackedExe([string]$Root) {
    if (-not $Root) { return $null }
    $cands = @(
        (Join-Path $Root 'apps\desktop\release\win-unpacked\Caravela.exe'),
        (Join-Path $Root 'apps\desktop\release\win-arm64-unpacked\Caravela.exe'),
        (Join-Path $Root 'apps\desktop\release\win-unpacked\Hermes.exe'),
        (Join-Path $Root 'apps\desktop\release\win-arm64-unpacked\Hermes.exe')
    )
    foreach ($c in $cands) {
        if ($c -and (Test-Path -LiteralPath $c)) { return $c }
    }
    return $null
}

function Set-CaravelaShortcuts([string]$Exe) {
    if (-not $Exe -or -not (Test-Path -LiteralPath $Exe)) { return }
    try {
        $shell = New-Object -ComObject WScript.Shell
        $work = Split-Path -Parent $Exe
        $ico = Join-Path $work 'resources\icon.ico'
        $icon = if (Test-Path -LiteralPath $ico) { "$ico,0" } else { "$Exe,0" }
        $name = [System.IO.Path]::GetFileNameWithoutExtension($Exe)
        $dirs = @(
            [Environment]::GetFolderPath('Programs'),
            [Environment]::GetFolderPath('Desktop')
        )
        foreach ($d in $dirs) {
            if (-not $d) { continue }
            $p = Join-Path $d ($name + '.lnk')
            $sc = $shell.CreateShortcut($p)
            $sc.TargetPath = $Exe
            $sc.WorkingDirectory = $work
            $sc.IconLocation = $icon
            $sc.Description = $name
            $sc.Save()
        }
        $all = Join-Path $env:ProgramData 'Microsoft\Windows\Start Menu\Programs'
        foreach ($n in @($name, 'Caravela')) {
            $p = Join-Path $all ($n + '.lnk')
            if (Test-Path -LiteralPath $p) {
                try {
                    $sc = $shell.CreateShortcut($p)
                    $sc.TargetPath = $Exe
                    $sc.WorkingDirectory = $work
                    $sc.IconLocation = $icon
                    $sc.Description = $name
                    $sc.Save()
                } catch {}
            }
        }
    } catch {}
}

if ($InstallRoot -and (Test-Path (Join-Path $InstallRoot ".git"))) {
    try {
        $origin = (& git -C $InstallRoot remote get-url origin 2>$null)
        if ($origin -and ($origin -notmatch "CaravelaLabs/CaravelaWinDesktop")) {
            & git -C $InstallRoot remote set-url origin $ProductOrigin
        }
    } catch {}
}

$unpacked = Get-CaravelaUnpackedExe $InstallRoot
if ($unpacked) {
    $PSBoundParameters['RelaunchExe'] = $unpacked
    $RelaunchExe = $unpacked
}

if ($RetargetShortcuts) {
    $target = if ($unpacked) { $unpacked } elseif ($RelaunchExe) { $RelaunchExe } else { $null }
    if ($target) { Set-CaravelaShortcuts $target }
    exit 0
}

$upstream = Join-Path $PSScriptRoot "windows.ps1"
if (-not (Test-Path $upstream)) {
    throw "Caravela update wrapper missing $upstream"
}

& $upstream @PSBoundParameters
$code = $LASTEXITCODE
$unpacked = Get-CaravelaUnpackedExe $InstallRoot
if ($unpacked) { Set-CaravelaShortcuts $unpacked }
exit $code
