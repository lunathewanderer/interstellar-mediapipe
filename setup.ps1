param([string]$PythonExe)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (Test-Path -LiteralPath '.venv\Scripts\python.exe') {
    Write-Host 'Using the existing project environment.'
} elseif ($PythonExe) {
    & $PythonExe -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
} elseif (Get-Command pymanager -ErrorAction SilentlyContinue) {
    & pymanager exec -V:3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 first: pymanager install 3.12' }
} else {
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 not found. Follow README.md installation steps.' }
}
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $projectPython -c "import sys,struct; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8, 'Use 64-bit Python 3.12'"
if ($LASTEXITCODE -ne 0) { throw 'The project requires a 64-bit Python 3.12 environment.' }
& $projectPython -m pip install pip==25.3
if ($LASTEXITCODE -ne 0) { throw 'pip installation failed. Check Internet access.' }
& $projectPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. See docs/TROUBLESHOOTING.md.' }
& $projectPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependencies are inconsistent.' }
& $projectPython tools/download_model.py
if ($LASTEXITCODE -ne 0) { throw 'Model download failed.' }
& $projectPython -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Automated checks failed.' }
Write-Host 'Setup complete. Next: double-click Run.bat or run python main.py'
