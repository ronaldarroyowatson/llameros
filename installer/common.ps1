Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-LlamerosInstallRoot {
    if ($env:LLAMEROS_INSTALL_ROOT) {
        return $env:LLAMEROS_INSTALL_ROOT
    }
    return (Join-Path $env:ProgramFiles "Llameros")
}

function Get-LlamerosSourceRoot {
    if ($env:LLAMEROS_SOURCE_ROOT) {
        return $env:LLAMEROS_SOURCE_ROOT
    }
    return (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
}

function Get-LlamerosRegistryBase {
    if ($env:LLAMEROS_REGISTRY_BASE) {
        return $env:LLAMEROS_REGISTRY_BASE
    }
    return "HKCU:\Software\Llameros"
}

function Get-LlamerosStartMenuRoot {
    if ($env:LLAMEROS_START_MENU_ROOT) {
        return $env:LLAMEROS_START_MENU_ROOT
    }
    return (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs")
}

function Get-LlamerosUserDataRoot {
    if ($env:LLAMEROS_USER_DATA_ROOT) {
        return $env:LLAMEROS_USER_DATA_ROOT
    }
    return (Join-Path $env:LOCALAPPDATA "Llameros\user-data")
}

function Get-LlamerosVersionFromSource {
    $versionFile = Join-Path (Get-LlamerosSourceRoot) "VERSION"
    if (Test-Path $versionFile) {
        return ((Get-Content -Path $versionFile -Raw).Trim())
    }
    return "0.0.0"
}

function Ensure-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    if (-not (Test-Path $Path)) {
        New-Item -Path $Path -ItemType Directory -Force | Out-Null
    }
}

function Get-InstallerLogPath {
    if ($env:LLAMEROS_INSTALL_LOG) {
        return $env:LLAMEROS_INSTALL_LOG
    }
    return (Join-Path (Get-LlamerosInstallRoot) "installer.log")
}

function Write-InstallerLog {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Message,
        [ValidateSet("INFO", "WARNING", "ERROR")]
        [string] $Level = "INFO"
    )

    $logPath = Get-InstallerLogPath
    $parent = Split-Path -Parent $logPath
    if ($parent) {
        Ensure-Directory -Path $parent
    }

    $timestamp = [DateTime]::UtcNow.ToString("o")
    Add-Content -Path $logPath -Value "$timestamp [installer.common] [$Level] $Message"
}

function Copy-LlamerosPayload {
    param(
        [Parameter(Mandatory = $true)]
        [string] $SourceRoot,
        [Parameter(Mandatory = $true)]
        [string] $InstallRoot
    )

    Ensure-Directory -Path $InstallRoot

    $copyTargets = @("src", "config", "VERSION", "requirements.txt", "README.md", "LICENSE")
    foreach ($target in $copyTargets) {
        $sourcePath = Join-Path $SourceRoot $target
        if (-not (Test-Path $sourcePath)) {
            continue
        }

        $destPath = Join-Path $InstallRoot $target
        if (Test-Path $sourcePath -PathType Container) {
            Ensure-Directory -Path $destPath
            Copy-Item -Path (Join-Path $sourcePath "*") -Destination $destPath -Recurse -Force
        }
        else {
            $destParent = Split-Path -Parent $destPath
            if ($destParent) {
                Ensure-Directory -Path $destParent
            }
            Copy-Item -Path $sourcePath -Destination $destPath -Force
        }
    }

    $binDir = Join-Path $InstallRoot "bin"
    Ensure-Directory -Path $binDir
    $launcherPath = Join-Path $binDir "llameros.cmd"
    $launcherContent = "@echo off`r`npython `"%~dp0..\src\main.py`" %*"
    Set-Content -Path $launcherPath -Value $launcherContent -Encoding ascii
}

function Get-NormalizedPathList {
    param([string] $PathValue)

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return @()
    }

    $items = @()
    foreach ($item in ($PathValue -split ";")) {
        $trimmed = $item.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }

        $normalized = $trimmed.TrimEnd("\\")
        if ([string]::IsNullOrWhiteSpace($normalized)) {
            continue
        }

        $items += $normalized
    }

    return $items
}

function Remove-PathEntryFromValues {
    param(
        [string] $PathValue,
        [string] $PathToRemove
    )

    $normalizedRemove = $PathToRemove.Trim().TrimEnd("\\")
    if ([string]::IsNullOrWhiteSpace($normalizedRemove)) {
        return ($PathValue.Trim().TrimEnd(";"))
    }

    $kept = @()
    foreach ($item in (Get-NormalizedPathList -PathValue $PathValue)) {
        if (-not $item.Equals($normalizedRemove, [System.StringComparison]::OrdinalIgnoreCase)) {
            $kept += $item
        }
    }

    return ($kept -join ";")
}

function Get-RequiredInstallRelativePaths {
    return @(
        "src\\main.py",
        "config\\rules.yaml",
        "VERSION",
        "bin\\llameros.cmd"
    )
}
