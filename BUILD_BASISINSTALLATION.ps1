param([string]$PythonExe="C:\python\python.exe")
$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
if(-not(Test-Path $PythonExe)){throw "Python nicht gefunden: $PythonExe"}
& $PythonExe -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ erforderlich'; print(sys.version)"
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -r (Join-Path $Root "requirements_foundry_local.txt")
& $PythonExe (Join-Path $Root "TEST_LOKALE_KI.py") --prepare
Write-Host "Basisinstallation vorbereitet." -ForegroundColor Green
