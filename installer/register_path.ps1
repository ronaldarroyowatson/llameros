param(
    [string] $BinPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "common.ps1")

if ([string]::IsNullOrWhiteSpace($BinPath)) {
    $BinPath = Join-Path (Get-LlamerosInstallRoot) "bin"
}

$normalizedBin = $BinPath.Trim().TrimEnd("\\")
if ([string]::IsNullOrWhiteSpace($normalizedBin)) {
    throw "BinPath cannot be empty."
}

$currentSession = $env:Path
$sessionEntries = Get-NormalizedPathList -PathValue $currentSession
if (-not ($sessionEntries | Where-Object { $_.Equals($normalizedBin, [System.StringComparison]::OrdinalIgnoreCase) })) {
    $sessionEntries += $normalizedBin
    $env:Path = $sessionEntries -join ";"
}

if ($env:LLAMEROS_PATH_PERSIST_FILE) {
    $persistFile = $env:LLAMEROS_PATH_PERSIST_FILE
    $persistDir = Split-Path -Parent $persistFile
    if ($persistDir) {
        Ensure-Directory -Path $persistDir
    }

    $persistCurrent = ""
    if (Test-Path $persistFile) {
        $persistCurrent = (Get-Content -Path $persistFile -Raw)
    }

    $persistEntries = Get-NormalizedPathList -PathValue $persistCurrent
    if (-not ($persistEntries | Where-Object { $_.Equals($normalizedBin, [System.StringComparison]::OrdinalIgnoreCase) })) {
        $persistEntries += $normalizedBin
    }

    Set-Content -Path $persistFile -Value ($persistEntries -join ";") -Encoding ascii
}
else {
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $userEntries = Get-NormalizedPathList -PathValue $userPath
    if (-not ($userEntries | Where-Object { $_.Equals($normalizedBin, [System.StringComparison]::OrdinalIgnoreCase) })) {
        $userEntries += $normalizedBin
        [Environment]::SetEnvironmentVariable("Path", ($userEntries -join ";"), "User")
    }
}

Write-Output $normalizedBin
