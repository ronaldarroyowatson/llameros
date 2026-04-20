Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "common.ps1")

$registryBase = Get-LlamerosRegistryBase
$registryInstallPath = $null

if (Test-Path $registryBase) {
    $props = Get-ItemProperty -Path $registryBase -ErrorAction SilentlyContinue
    if ($null -ne $props -and $props.PSObject.Properties.Name -contains "InstallPath") {
        $registryInstallPath = [string]$props.InstallPath
    }
}

$installPath = if ($registryInstallPath) { $registryInstallPath } else { Get-LlamerosInstallRoot }
$installExists = Test-Path $installPath
$versionExists = Test-Path (Join-Path $installPath "VERSION")
$registryExists = Test-Path $registryBase

if (-not $registryExists -and -not $installExists -and -not $versionExists) {
    Write-Output "none"
    exit 0
}

if ($registryExists -and $installExists -and $versionExists) {
    Write-Output "installed"
    exit 0
}

Write-Output "corrupted"
exit 0
