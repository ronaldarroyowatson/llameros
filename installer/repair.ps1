Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "common.ps1")

$sourceRoot = Get-LlamerosSourceRoot
$installRoot = Get-LlamerosInstallRoot
$version = Get-LlamerosVersionFromSource

$detectScript = Join-Path $PSScriptRoot "detect_previous_install.ps1"
$stateBefore = (& $detectScript | Select-Object -Last 1).Trim()

Write-InstallerLog -Message "Repair started. state_before=$stateBefore install=$installRoot"

if ($stateBefore -eq "none") {
    Write-InstallerLog -Message "Repair aborted because no installation exists." -Level "ERROR"
    Write-Output "none"
    exit 1
}

if (-not (Test-Path $installRoot)) {
    Ensure-Directory -Path $installRoot
}

$requiredRelativePaths = Get-RequiredInstallRelativePaths
$restoredCount = 0

foreach ($relativePath in $requiredRelativePaths) {
    $targetPath = Join-Path $installRoot $relativePath
    if (Test-Path $targetPath) {
        continue
    }

    $sourcePath = Join-Path $sourceRoot $relativePath
    if ($relativePath -eq "bin\\llameros.cmd") {
        Ensure-Directory -Path (Join-Path $installRoot "bin")
        $launcherContent = "@echo off`r`npython `"%~dp0..\src\main.py`" %*"
        Set-Content -Path $targetPath -Value $launcherContent -Encoding ascii
        $restoredCount += 1
        continue
    }

    if (Test-Path $sourcePath) {
        $targetParent = Split-Path -Parent $targetPath
        if ($targetParent) {
            Ensure-Directory -Path $targetParent
        }

        Copy-Item -Path $sourcePath -Destination $targetPath -Force
        $restoredCount += 1
    }
}

if ($stateBefore -eq "corrupted") {
    Copy-LlamerosPayload -SourceRoot $sourceRoot -InstallRoot $installRoot
}

$registerPathScript = Join-Path $PSScriptRoot "register_path.ps1"
& $registerPathScript -BinPath (Join-Path $installRoot "bin") | Out-Null

$registerRegistryScript = Join-Path $PSScriptRoot "register_registry.ps1"
& $registerRegistryScript -InstallPath $installRoot -Version $version -Reinstall | Out-Null

$stateAfter = (& $detectScript | Select-Object -Last 1).Trim()
if ($stateAfter -ne "installed") {
    Write-InstallerLog -Message "Repair failed integrity validation. state_after=$stateAfter" -Level "ERROR"
    Write-Output "corrupted"
    exit 1
}

Write-InstallerLog -Message "Repair completed. restored_files=$restoredCount state_after=$stateAfter"
Write-Output "repaired"
exit 0
