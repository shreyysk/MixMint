# Removes EVERY admin account on the live site and creates one new admin.
# Usage (PowerShell, in D:\mixmint2.0, venv activated):
#   powershell -ExecutionPolicy Bypass -File .\scripts\reset_admin.ps1 -EnvFile ".\vercel-production.env" -Email "you@gmail.com"
param(
    [Parameter(Mandatory = $true)][string]$EnvFile,
    [Parameter(Mandatory = $true)][string]$Email
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $EnvFile)) { throw "Env file not found: $EnvFile" }
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], "Process") }
}
$env:CELERY_TASK_ALWAYS_EAGER = "True"

Write-Host "This deletes ALL current admin accounts on the LIVE site and makes $Email the only admin." -ForegroundColor Yellow
if ((Read-Host 'Type "yes" to continue') -ne "yes") { Write-Host "Cancelled."; exit 1 }

$p1 = Read-Host "New admin password" -AsSecureString
$p2 = Read-Host "Type it again" -AsSecureString
$plain1 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p1))
$plain2 = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p2))
if ($plain1 -ne $plain2) { throw "Passwords don't match. Run it again." }

$env:NEW_ADMIN_EMAIL = $Email
$env:NEW_ADMIN_PASSWORD = $plain1
try {
    Get-Content .\scripts\reset_admin.py -Raw | python manage.py shell
} finally {
    Remove-Item Env:NEW_ADMIN_PASSWORD -ErrorAction SilentlyContinue
}
