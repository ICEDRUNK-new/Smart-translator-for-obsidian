[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectPath,
    [string]$Python = 'python',
    [string]$VenvPath = (Join-Path (Split-Path -Parent $PSScriptRoot) '.venv')
)

$ErrorActionPreference = 'Stop'

$project = Get-Item -LiteralPath $ProjectPath -ErrorAction Stop
if (-not $project.PSIsContainer -or -not (Test-Path -LiteralPath (Join-Path $project.FullName 'pdf2zh\__init__.py'))) {
    throw "PDFMathTranslate source directory is invalid: $ProjectPath"
}

& $Python -c 'import sys; assert (3, 11) <= sys.version_info[:2] < (3, 13), sys.version'
if ($LASTEXITCODE -ne 0) { throw 'PDFMathTranslate requires Python 3.11 or 3.12.' }

& $Python -m venv $VenvPath
if ($LASTEXITCODE -ne 0) { throw 'Failed to create the Python virtual environment.' }

$venvPython = Join-Path $VenvPath 'Scripts\python.exe'
& $venvPython -m pip install --no-cache-dir --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Failed to update pip.' }

& $venvPython -m pip install --no-cache-dir 'peewee==3.18.2'
if ($LASTEXITCODE -ne 0) { throw 'Failed to install the compatible peewee version.' }

& $venvPython -m pip install --no-cache-dir 'tencentcloud-sdk-python-tmt==3.1.121'
if ($LASTEXITCODE -ne 0) { throw 'Failed to install the compatible Tencent TMT SDK version.' }

& $venvPython -m pip install --no-cache-dir $project.FullName
if ($LASTEXITCODE -ne 0) { throw 'Failed to install PDFMathTranslate and its dependencies.' }

Write-Host ''
Write-Host 'Python environment is ready.' -ForegroundColor Green
Write-Host "Set the plugin's Python executable to: $venvPython"
