[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$dependencyRoot = Join-Path $repoRoot 'deps\kordoc'
$packagePath = Join-Path $dependencyRoot 'package.json'
$lockPath = Join-Path $dependencyRoot 'package-lock.json'
if (-not (Test-Path -LiteralPath $packagePath -PathType Leaf)) {
    throw 'Document tools package.json is missing.'
}
$nodeCommand = Get-Command node.exe -ErrorAction Stop
$npmCommand = Get-Command npm.cmd -ErrorAction Stop
$nodeVersion = (& $nodeCommand.Source --version).Trim()
if ($nodeVersion -notmatch '^v(\d+)\.' -or [int]$Matches[1] -lt 20) {
    throw 'Document tools require an existing Node.js 20 or newer installation.'
}
$manifest = Get-Content -LiteralPath $packagePath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.dependencies.kordoc -ne '4.21.30') {
    throw 'Review a changed kordoc version before installing it.'
}
if ($manifest.dependencies.'pdfjs-dist' -ne '4.10.38') {
    throw 'Review a changed PDF parser version before installing it.'
}

# Explicit user-invoked installer only. No lifecycle scripts, OCR/native extras,
# global installs, MCP setup, or automatic updates.
$installCommand = if (Test-Path -LiteralPath $lockPath -PathType Leaf) { 'ci' } else { 'install' }
& $npmCommand.Source $installCommand --prefix $dependencyRoot --cache (Join-Path $repoRoot 'out\npm-cache') --ignore-scripts --omit=optional --no-fund --no-audit
if ($LASTEXITCODE -ne 0) { throw "npm $installCommand failed: $LASTEXITCODE" }
$installedPath = Join-Path $dependencyRoot 'node_modules\kordoc\package.json'
$installed = Get-Content -LiteralPath $installedPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($installed.version -ne '4.21.30') { throw 'Installed kordoc version does not match the reviewed version.' }
$installedPdfPath = Join-Path $dependencyRoot 'node_modules\pdfjs-dist\package.json'
$installedPdf = Get-Content -LiteralPath $installedPdfPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($installedPdf.version -ne '4.10.38') { throw 'Installed PDF parser version does not match the reviewed version.' }
Write-Output "Installed project-local kordoc $($installed.version), pdfjs-dist $($installedPdf.version) ($nodeVersion)."
Write-Output 'Existing MCP installations and client settings were not changed.'
