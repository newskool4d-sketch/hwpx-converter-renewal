[CmdletBinding()]
param(
    [ValidateSet('all', 'full', 'text', 'none')]
    [string]$Stack = 'all',
    [switch]$Build
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$spec = Join-Path $repo 'anyway_to_hwpx_gui.spec'
$stacks = if ($Stack -eq 'all') { @('full', 'text', 'none') } else { @($Stack) }

# Python may print the Unicode user-profile path through a mojibake console
# encoding. Resolve the user site from APPDATA instead so installed packages
# remain discoverable by child Python processes and PyInstaller.
$pythonVersion = (& python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
$userSite = Join-Path ([Environment]::GetFolderPath('ApplicationData')) ("Python\Python{0}\site-packages" -f $pythonVersion)
if (Test-Path -LiteralPath $userSite -PathType Container) {
    $existingPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = if ([string]::IsNullOrWhiteSpace($existingPythonPath)) {
        $userSite
    } else {
        "$userSite;$existingPythonPath"
    }
}

# Keep this helper read-only by default.  -Build opts into PyInstaller output,
# but every generated file is isolated below C:\tmp\hwpx-gui-<stack>.
$imports = @{
    full = @('PyInstaller', 'tkinterdnd2', 'fitz', 'pdfplumber', 'pypdf', 'opendataloader_pdf')
    text = @('PyInstaller', 'tkinterdnd2', 'fitz', 'pdfplumber', 'pypdf')
    none = @('PyInstaller', 'tkinterdnd2')
}

function Test-PythonImport([string]$ModuleName) {
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & python -c "import $ModuleName" *> $null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

if (-not (Test-Path -LiteralPath $spec -PathType Leaf)) {
    throw "Missing spec: $spec"
}

foreach ($currentStack in $stacks) {
    $missing = @($imports[$currentStack] | Where-Object { -not (Test-PythonImport $_) })
    if ($missing.Count -gt 0) {
        Write-Output ("[SKIP] {0}: missing Python package(s): {1}" -f $currentStack, ($missing -join ', '))
        continue
    }

    Write-Output ("[PASS] {0}: required imports are available" -f $currentStack)
    if (-not $Build) {
        continue
    }

    $root = Join-Path 'C:\tmp' ("hwpx-gui-{0}" -f $currentStack)
    if (Test-Path -LiteralPath $root) {
        throw "Refusing to overwrite existing packaging directory: $root"
    }
    $dist = Join-Path $root 'dist'
    $work = Join-Path $root 'work'
    New-Item -ItemType Directory -Force -Path $dist, $work | Out-Null

    $previousStack = $env:HWPX_GUI_PDF_STACK
    try {
        $env:HWPX_GUI_PDF_STACK = $currentStack
        & python -m PyInstaller --clean --noconfirm `
            --distpath $dist --workpath $work --specpath $repo $spec
        if ($LASTEXITCODE -ne 0) {
            throw "PyInstaller failed for stack '$currentStack' (exit $LASTEXITCODE)"
        }
    }
    finally {
        if ($null -eq $previousStack) {
            Remove-Item Env:HWPX_GUI_PDF_STACK -ErrorAction SilentlyContinue
        }
        else {
            $env:HWPX_GUI_PDF_STACK = $previousStack
        }
    }

    $exe = Join-Path $dist 'anyway_to_hwpx_gui.exe'
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "PyInstaller reported success but executable is missing: $exe"
    }
    Write-Output ("[PASS] {0}: executable {1}" -f $currentStack, $exe)
}
