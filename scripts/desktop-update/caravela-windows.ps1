# caravela-windows.ps1 — Caravela product update hand-off.
#
# Copied into the branded checkout by rebrand.py. The branded
# updater-process.ts prefers this file over stock windows.ps1.
#
# hermes update follows git `origin`. Stock Hermes installs point origin at
# NousResearch/hermes-agent, so Update rebuilt the Hermes GUI. Pin origin to
# the Caravela product repo first, then run the upstream Windows hand-off
# (venv unlock, hermes update, desktop rebuild, relaunch).
param(
    [string]$InstallRoot,
    [string]$Branch = "main",
    [int]$DesktopPid = 0,
    [string]$RelaunchExe = "",
    [switch]$NoUi,
    [switch]$NoMarkerCleanup,
    [switch]$SelfTestUi,
    [switch]$SelfTestPipeDrain,
    [switch]$SelfTestMarker
)

$ErrorActionPreference = "Continue"
$ProductOrigin = "https://github.com/CaravelaLabs/CaravelaWinDesktop.git"

if ($InstallRoot -and (Test-Path (Join-Path $InstallRoot ".git"))) {
    try {
        $origin = (& git -C $InstallRoot remote get-url origin 2>$null)
        if ($origin -and ($origin -notmatch "CaravelaLabs/CaravelaWinDesktop")) {
            & git -C $InstallRoot remote set-url origin $ProductOrigin
        }
    } catch {}
}

$upstream = Join-Path $PSScriptRoot "windows.ps1"
if (-not (Test-Path $upstream)) {
    throw "Caravela update wrapper missing $upstream"
}

& $upstream @PSBoundParameters
exit $LASTEXITCODE
