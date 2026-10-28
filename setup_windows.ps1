<#
  FALCON setup for Windows (PowerShell)

  Run from the project folder:
      Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
      .\setup_windows.ps1
#>
$ErrorActionPreference = "Continue"
Write-Host "== FALCON setup ==" -ForegroundColor Cyan

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "The Python launcher 'py' was not found. Install Python 3.10 from python.org and tick 'Add python.exe to PATH'." -ForegroundColor Red
    exit 1
}
$version = "-3.10"
& py $version -c "import sys" *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Python 3.10 not found; using your default Python 3 (fine for this stage)."
    $version = "-3"
}
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment .venv ..."
    & py $version -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

# The Pellet bundled with owlready2 0.51+ is compiled for Java 25, so an older Java is not enough.
$javaMajor = 0
if (Get-Command java -ErrorAction SilentlyContinue) {
    $line = (cmd /c "java -version 2>&1" | Select-Object -First 1)
    if ($line -match 'version "(\d+)') { $javaMajor = [int]$Matches[1] }
}
if ($javaMajor -lt 25) {
    Write-Warning "Java 25 or newer is needed for Pellet (found: $javaMajor). Installing Eclipse Temurin 25 with winget..."
    winget install --id EclipseAdoptium.Temurin.25.JDK -e --accept-source-agreements --accept-package-agreements
    Write-Host "Close this window, open a new PowerShell in the project folder, and run .\setup_windows.ps1 again." -ForegroundColor Yellow
    exit 0
}
& .\.venv\Scripts\python.exe check_environment.py
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python -m unittest discover -s tests -v"
Write-Host "  python run_all.py"
