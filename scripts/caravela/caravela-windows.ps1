# caravela-windows.ps1 — Caravela product update hand-off.
#
# The Desktop updater prefers this file over stock windows.ps1.
# Stock `hermes update` does `git reset --hard` to origin. Origin used to be
# CaravelaWinDesktop, a snapshot that lagged Hermes for months, and the exe
# detector only knew Hermes.exe — so Update either skipped the pack or packed
# Caravela.exe and reported that nothing compiled.
#
# Every click:
#   1. Save scripts/caravela to %LOCALAPPDATA% (survives the reset).
#   2. Fetch NousResearch/hermes-agent main.
#   3. Re-apply the brand from that kit (not a frozen diff).
#   4. Point origin at a local bare of that branded commit so windows.ps1's
#      reset cannot throw the brand away.
#   5. Run the stock hand-off (venv unlock, deps, one desktop build, relaunch).
# If the fetch or brand fails, fall through to the product repo already on GitHub.
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
$HermesOrigin = "https://github.com/NousResearch/hermes-agent.git"

function Get-CaravelaUnpackedExe([string]$Root) {
    if (-not $Root) { return $null }
    $names = @('Caravela.exe', 'Hermes.exe')
    $dirs = @('win-unpacked', 'win-arm64-unpacked', 'win-ia32-unpacked')
    foreach ($n in $names) {
        foreach ($d in $dirs) {
            $c = Join-Path $Root "apps\desktop\release\$d\$n"
            if (Test-Path -LiteralPath $c) { return $c }
        }
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
        $name = 'Caravela'
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
    } catch {}
}

function Sync-BrandKit([string]$Root) {
    $kit = Join-Path $env:LOCALAPPDATA 'Caravela\brand-kit'
    $src = Join-Path $Root 'scripts\caravela'
    if (Test-Path -LiteralPath (Join-Path $src 'apply_brand.py')) {
        New-Item -ItemType Directory -Force -Path $kit | Out-Null
        Copy-Item -Recurse -Force (Join-Path $src '*') $kit
    }
    return $kit
}

function Invoke-CaravelaSync([string]$Root) {
    if (-not $Root -or -not (Test-Path -LiteralPath (Join-Path $Root '.git'))) { return $false }
    $kit = Sync-BrandKit $Root
    if (-not (Test-Path -LiteralPath (Join-Path $kit 'apply_brand.py'))) {
        Write-Output "Caravela brand kit missing; Update will use the product repo as-is"
        return $false
    }
    $prev = (& git -C $Root rev-parse HEAD).Trim()
    & git -C $Root fetch --depth 1 $HermesOrigin "+main:refs/remotes/hermes-upstream/main"
    if ($LASTEXITCODE -ne 0) {
        Write-Output "Hermes fetch failed; Update will use the product repo as-is"
        return $false
    }
    & git -C $Root reset --hard hermes-upstream/main
    if ($LASTEXITCODE -ne 0) {
        & git -C $Root reset --hard $prev
        return $false
    }
    & git -C $Root clean -fd
    $py = Join-Path $Root 'venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $py)) { $py = 'python' }
    & $py (Join-Path $kit 'apply_brand.py') $Root
    if ($LASTEXITCODE -ne 0) {
        Write-Output "Brand apply failed; restoring previous checkout"
        & git -C $Root reset --hard $prev
        return $false
    }
    & $py (Join-Path $kit 'rebrand.py') $Root
    if ($LASTEXITCODE -ne 0) {
        Write-Output "Rebrand failed; restoring previous checkout"
        & git -C $Root reset --hard $prev
        return $false
    }
    $brandSrc = Join-Path $kit 'assets\brand\caravela'
    if (Test-Path -LiteralPath $brandSrc) {
        $dest = Join-Path $Root 'apps\desktop\public\brand\caravela'
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Copy-Item -Force (Join-Path $brandSrc '*') $dest
    }
    & git -C $Root add -A
    $tree = (& git -C $Root write-tree).Trim()
    $env:GIT_AUTHOR_NAME = 'Caravela'
    $env:GIT_AUTHOR_EMAIL = 'darioluis11@gmail.com'
    $env:GIT_COMMITTER_NAME = 'Caravela'
    $env:GIT_COMMITTER_EMAIL = 'darioluis11@gmail.com'
    $parent = (& git -C $Root rev-parse HEAD).Trim()
    $commit = (& git -C $Root commit-tree $tree -p $parent -m "Caravela brand").Trim()
    if (-not $commit) {
        & git -C $Root reset --hard $prev
        return $false
    }
    & git -C $Root reset --hard $commit
    $bare = Join-Path $env:LOCALAPPDATA 'Caravela\live.git'
    if (-not (Test-Path -LiteralPath (Join-Path $bare 'HEAD'))) {
        & git init --bare $bare
    }
    & git -C $Root push --force $bare "${commit}:refs/heads/main"
    if ($LASTEXITCODE -ne 0) {
        Write-Output "Could not pin branded commit; Update will use the product repo"
        & git -C $Root remote set-url origin $ProductOrigin
        return $false
    }
    & git -C $Root remote set-url origin $bare
    Write-Output "Caravela branded on Hermes $parent"
    return $true
}

if ($InstallRoot -and (Test-Path (Join-Path $InstallRoot ".git"))) {
    try {
        $origin = (& git -C $InstallRoot remote get-url origin 2>$null)
        if ($origin -and ($origin -notmatch "CaravelaLabs/CaravelaWinDesktop") -and ($origin -notmatch "live\.git")) {
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

if (-not ($SelfTestUi -or $SelfTestPipeDrain -or $SelfTestMarker)) {
    [void](Invoke-CaravelaSync $InstallRoot)
    $unpacked = Get-CaravelaUnpackedExe $InstallRoot
    if ($unpacked) {
        $PSBoundParameters['RelaunchExe'] = $unpacked
        $RelaunchExe = $unpacked
    }
}

& $upstream @PSBoundParameters
$code = $LASTEXITCODE
$unpacked = Get-CaravelaUnpackedExe $InstallRoot
if ($unpacked) { Set-CaravelaShortcuts $unpacked }
if ($InstallRoot -and (Test-Path (Join-Path $InstallRoot '.git'))) {
    & git -C $InstallRoot remote set-url origin $ProductOrigin
}
exit $code
