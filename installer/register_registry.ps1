param(
    [string] $InstallPath,
    [string] $Version,
    [switch] $Reinstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "common.ps1")

if ([string]::IsNullOrWhiteSpace($InstallPath)) {
    $InstallPath = Get-LlamerosInstallRoot
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = Get-LlamerosVersionFromSource
}

$registryBase = Get-LlamerosRegistryBase
if (-not (Test-Path $registryBase)) {
    New-Item -Path $registryBase -Force | Out-Null
}

$currentProps = Get-ItemProperty -Path $registryBase -ErrorAction SilentlyContinue
$hasInstallPath = $null -ne $currentProps -and $currentProps.PSObject.Properties.Name -contains "InstallPath"
$hasVersion = $null -ne $currentProps -and $currentProps.PSObject.Properties.Name -contains "Version"
$hasInstallDate = $null -ne $currentProps -and $currentProps.PSObject.Properties.Name -contains "InstallDate"

if ($Reinstall -or -not $hasInstallPath) {
    Set-ItemProperty -Path $registryBase -Name "InstallPath" -Value $InstallPath
}

if ($Reinstall -or -not $hasVersion) {
    Set-ItemProperty -Path $registryBase -Name "Version" -Value $Version
}

if ($Reinstall -or -not $hasInstallDate) {
    Set-ItemProperty -Path $registryBase -Name "InstallDate" -Value ([DateTime]::UtcNow.ToString("o"))
}

Write-Output $registryBase
