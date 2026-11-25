[CmdletBinding()]
param(
    [bool]$Clean = $true,
    [switch]$DebugBuild,
    [string]$Version = "",
    [string]$VirtualEnvPath = ".venv-build"
)

# Stop on native or PowerShell errors for reproducible CI and local builds.
$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "PowerShell 7 or newer is required."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$requirements = Join-Path $repoRoot "requirements-windows-build.txt"
$specFile = Join-Path $repoRoot "acteo.spec"
$schemaFile = Join-Path $repoRoot "schemas\settings.schema.json"
$entrypointFile = Join-Path $repoRoot "src\acteo\packaging_entrypoint.py"
$venvPath = if ([System.IO.Path]::IsPathRooted($VirtualEnvPath)) {
    $VirtualEnvPath
} else {
    Join-Path $repoRoot $VirtualEnvPath
}
$venvPython = Join-Path $venvPath "Scripts\python.exe"
$expectedExe = Join-Path $repoRoot "dist\Acteo\Acteo.exe"

foreach ($requiredFile in @($requirements, $specFile, $schemaFile, $entrypointFile)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required build file is missing: $requiredFile"
    }
}

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    Write-Host "Creating build virtual environment at $venvPath"
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.11 -m venv $venvPath
    } else {
        & python -m venv $venvPath
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create the build virtual environment."
    }
}

Write-Host "Installing reproducible build dependencies"
& $venvPython -m pip install --disable-pip-version-check --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Failed to upgrade pip." }
& $venvPython -m pip install --disable-pip-version-check -r $requirements
if ($LASTEXITCODE -ne 0) { throw "Failed to install build dependencies." }

if ($Clean) {
    Write-Host "Cleaning prior build outputs"
    foreach ($pyinstallerBuildDir in @("Acteo", "acteo")) {
        $buildOutput = Join-Path $repoRoot (Join-Path "build" $pyinstallerBuildDir)
        Remove-Item -LiteralPath $buildOutput -Recurse -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath (Join-Path $repoRoot "dist") -Recurse -Force -ErrorAction SilentlyContinue
}

if ($Version) {
    $env:ACTEO_VERSION = $Version
    Write-Host "Building Acteo version $Version"
}

$pyinstallerArgs = @("-m", "PyInstaller", "--clean", $specFile)
if ($DebugBuild) {
    $pyinstallerArgs = @("-m", "PyInstaller", "--clean", "--debug=all", $specFile)
}

Write-Host "Running PyInstaller"
& $venvPython @pyinstallerArgs
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed."
}

if (-not (Test-Path -LiteralPath $expectedExe -PathType Leaf)) {
    throw "PyInstaller completed but the expected executable was not produced: $expectedExe"
}

Write-Host "Acteo build completed: $expectedExe"
