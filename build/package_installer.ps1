[CmdletBinding()]
param(
    [string]$Version = "",
    [string]$InnoSetupCompiler = ""
)

$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "PowerShell 7 or newer is required."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$issFile = Join-Path $repoRoot "build\acteo.iss"
$appDirectory = Join-Path $repoRoot "dist\Acteo"
$licenseFile = Join-Path $repoRoot "LICENSE"

foreach ($requiredFile in @($issFile, $licenseFile)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required installer file is missing: $requiredFile"
    }
}
if (-not (Test-Path -LiteralPath $appDirectory -PathType Container)) {
    throw "PyInstaller directory bundle is missing: $appDirectory"
}
if (-not (Test-Path -LiteralPath (Join-Path $appDirectory "Acteo.exe") -PathType Leaf)) {
    throw "PyInstaller executable is missing: $(Join-Path $appDirectory 'Acteo.exe')"
}

if (-not $Version) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $pythonCommand = "py"
        $pythonArguments = @("-3.11", "-c", 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["tool"]["poetry"]["version"])')
    } else {
        $pythonCommand = "python"
        $pythonArguments = @("-c", 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["tool"]["poetry"]["version"])')
    }
    $Version = (& $pythonCommand @pythonArguments).Trim()
}

if (-not $InnoSetupCompiler) {
    $candidates = @(
        $env:INNO_SETUP_COMPILER,
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    ) | Where-Object { $_ }
    $InnoSetupCompiler = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
if (-not $InnoSetupCompiler) {
    throw "Inno Setup compiler ISCC.exe was not found. Install Inno Setup or pass -InnoSetupCompiler."
}

New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot "dist\installer") | Out-Null
Write-Host "Building Inno Setup installer for Acteo $Version"
& $InnoSetupCompiler "/DAppVersion=$Version" $issFile
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed."
}

$installer = Join-Path $repoRoot "dist\installer\Acteo-$Version-Setup.exe"
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {
    throw "Inno Setup completed but the installer was not produced: $installer"
}
Write-Host "Acteo installer completed: $installer"
