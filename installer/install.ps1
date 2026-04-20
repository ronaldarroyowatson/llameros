param(
    [switch] $Reinstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "common.ps1")

$sourceRoot = Get-LlamerosSourceRoot
$installRoot = Get-LlamerosInstallRoot
$version = Get-LlamerosVersionFromSource

Write-InstallerLog -Message "Install started. source=$sourceRoot install=$installRoot version=$version"

$detectScript = Join-Path $PSScriptRoot "detect_previous_install.ps1"
$previousState = (& $detectScript | Select-Object -Last 1).Trim()
Write-InstallerLog -Message "Previous install state: $previousState"

if ($previousState -eq "installed" -and -not $Reinstall) {
    Write-InstallerLog -Message "Install skipped because an installation already exists."
    Write-Output "installed"
    exit 0
}

$parentDir = Split-Path -Parent $installRoot
if ($parentDir) {
    Ensure-Directory -Path $parentDir
}

Copy-LlamerosPayload -SourceRoot $sourceRoot -InstallRoot $installRoot
Write-InstallerLog -Message "Payload copied to install root."

$startMenuFolder = Join-Path (Get-LlamerosStartMenuRoot) "Llameros"
Ensure-Directory -Path $startMenuFolder

$shortcutPath = Join-Path $startMenuFolder "Llameros.lnk"
$launcherPath = Join-Path $installRoot "bin\llameros.cmd"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $launcherPath
$shortcut.WorkingDirectory = $installRoot
$shortcut.Description = "Llameros watchdog"
$shortcut.Save()
Write-InstallerLog -Message "Start Menu shortcut created at $shortcutPath"

$registerPathScript = Join-Path $PSScriptRoot "register_path.ps1"
& $registerPathScript -BinPath (Join-Path $installRoot "bin") | Out-Null
Write-InstallerLog -Message "PATH registration completed."

$registerRegistryScript = Join-Path $PSScriptRoot "register_registry.ps1"
$useReinstall = $Reinstall -or $previousState -ne "none"
& $registerRegistryScript -InstallPath $installRoot -Version $version -Reinstall:$useReinstall | Out-Null
Write-InstallerLog -Message "Registry registration completed."

Write-InstallerLog -Message "Installation completed."
Write-Output "installed"
exit 0
