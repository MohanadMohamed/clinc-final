# Development/test artifact only. Does not install, migrate, provision or start services.
[CmdletBinding()]
param(
    [string]$Python = '',
    [Parameter(Mandatory)][ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$')][string]$BuildId
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if ($env:OS -ne 'Windows_NT') { throw 'Windows build must execute on Windows' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if (-not $Python) { $Python = Join-Path $root '.build-venv/Scripts/python.exe' }
$Python = (Resolve-Path $Python).Path
$output = Join-Path $root "artifacts/windows/$BuildId"
if (Test-Path $output) { throw 'BuildId already exists; choose a new ID. No output will be overwritten.' }
function Assert-NativeSuccess([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed (exit $LASTEXITCODE)" }
}
Push-Location $root
try {
    & $Python -c "import sys,sysconfig; assert sys.platform == 'win32' and sys.version_info[:2] == (3,14) and sysconfig.get_platform() == 'win-amd64' and sys._is_gil_enabled(), 'Use GIL-enabled CPython 3.14 x64'"
    Assert-NativeSuccess 'Python prerequisite check'
    & $Python -c "from desktop.packaging.build_support import verify_build_dependencies; verify_build_dependencies()"
    Assert-NativeSuccess 'Pinned Windows build dependencies'
    & $Python -m pip check
    Assert-NativeSuccess 'Dependency check'
    & node -e "if (process.versions.node.split('.')[0] !== '22') process.exit(1)"
    Assert-NativeSuccess 'Node 22 prerequisite check'
    # Build in production clinic mode even if a demo variable was set in the shell.
    $previousDemo = $env:VITE_DEMO_MODE
    $env:VITE_DEMO_MODE = 'false'
    try {
        Push-Location (Join-Path $root 'frontend')
        try {
            & npm.cmd ci
            Assert-NativeSuccess 'Frontend dependency installation'
            & npm.cmd run build
            Assert-NativeSuccess 'React production build'
        } finally { Pop-Location }
    } finally { $env:VITE_DEMO_MODE = $previousDemo }
    New-Item -ItemType Directory -Path $output | Out-Null
    # Windows PowerShell 5.1 wraps redirected native stderr as error records.
    # PyInstaller writes normal INFO output there; judge it by its exit code.
    $previousErrorAction = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Python -m PyInstaller --noconfirm --distpath (Join-Path $output 'client') --workpath (Join-Path $output 'work') (Join-Path $PSScriptRoot 'ClinicClient.spec') 2>&1 | Tee-Object -FilePath (Join-Path $output 'build.log')
        $buildExitCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousErrorAction }
    if ($buildExitCode -ne 0) { throw "PyInstaller failed (exit $buildExitCode)" }
    Assert-NativeSuccess 'PyInstaller'
    & $Python -m desktop.packaging.build_support --output $output
    Assert-NativeSuccess 'Payload staging'
    & (Join-Path $output 'client/ClinicClient/ClinicClient.exe') --check-config --config (Join-Path $output 'profiles/doctor-client.example.toml')
    Assert-NativeSuccess 'Packaged client configuration check'
    Write-Output "Prepared test artifact: $output. GUI/TLS/Windows workflow testing remains required."
} finally { Pop-Location }
