param(
    [switch] $RemoveUserData,
    [switch] $Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "common.ps1")

$registryBase = Get-LlamerosRegistryBase
$installRoot = Get-LlamerosInstallRoot
if (Test-Path $registryBase) {
    $props = Get-ItemProperty -Path $registryBase -ErrorAction SilentlyContinue
    if ($null -ne $props -and $props.PSObject.Properties.Name -contains "InstallPath") {
        $installRoot = [string]$props.InstallPath
    }
}

Write-InstallerLog -Message "Uninstall started. install=$installRoot"

$binPath = Join-Path $installRoot "bin"
$currentSession = Remove-PathEntryFromValues -PathValue $env:Path -PathToRemove $binPath
$env:Path = $currentSession

if ($env:LLAMEROS_PATH_PERSIST_FILE) {
    $persistFile = $env:LLAMEROS_PATH_PERSIST_FILE
    $persistCurrent = ""
    if (Test-Path $persistFile) {
        $persistCurrent = Get-Content -Path $persistFile -Raw
    }
    $persistUpdated = Remove-PathEntryFromValues -PathValue $persistCurrent -PathToRemove $binPath
    Set-Content -Path $persistFile -Value $persistUpdated -Encoding ascii
}
else {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $updatedUserPath = Remove-PathEntryFromValues -PathValue $userPath -PathToRemove $binPath
    [Environment]::SetEnvironmentVariable("Path", $updatedUserPath, "User")
}

Write-InstallerLog -Message "PATH entries removed."

$startMenuFolder = Join-Path (Get-LlamerosStartMenuRoot) "Llameros"
if (Test-Path $startMenuFolder) {
    Remove-Item -Path $startMenuFolder -Recurse -Force
    Write-InstallerLog -Message "Start Menu folder removed."
}

if (Test-Path $registryBase) {
    Remove-Item -Path $registryBase -Recurse -Force
    Write-InstallerLog -Message "Registry key removed."
}

$userDataRoot = Get-LlamerosUserDataRoot
if (Test-Path $userDataRoot) {
    $deleteUserData = $RemoveUserData

    if (-not $RemoveUserData -and -not $Force) {
        $answer = Read-Host "User data detected at $userDataRoot. Remove it? (y/N)"
        if ($answer -match "^[Yy]$") {
            $deleteUserData = $true
        }
    }

    if ($deleteUserData) {
        Remove-Item -Path $userDataRoot -Recurse -Force
        Write-InstallerLog -Message "User data removed."
    }
    else {
        Write-InstallerLog -Message "User data retained after confirmation."
    }
}

if (Test-Path $installRoot) {
    $installerLogPath = Get-InstallerLogPath
    if (Test-Path $installerLogPath) {
        Remove-Item -Path $installerLogPath -Force -ErrorAction SilentlyContinue
    }

    $watchdogLogPath = Join-Path $installRoot "llameros.log"
    if (Test-Path $watchdogLogPath) {
        Remove-Item -Path $watchdogLogPath -Force -ErrorAction SilentlyContinue
    }

    Remove-Item -Path $installRoot -Recurse -Force
}

Write-Output "uninstalled"
exit 0
