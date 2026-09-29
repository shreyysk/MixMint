# Removes every account from the LIVE MixMint site EXCEPT admin accounts.
# R2 files (audio, covers), platform settings and offers are NOT touched.
# Usage (PowerShell, from D:\mixmint2.0, with the venv activated):
#   .\scripts\wipe_production.ps1 -EnvFile "$HOME\Downloads\vercel-production.env"
# It shows what will be deleted, asks you to type "yes", and saves a JSON backup first.
# Add -AdminEmail you@example.com to create (or reset the password of) an admin account too.
param(
    [Parameter(Mandatory = $true)][string]$EnvFile,
    [string]$AdminEmail = ""
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $EnvFile)) { throw "Env file not found: $EnvFile" }

# Load KEY=VALUE lines into this PowerShell session only (nothing is written anywhere).
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], "Process")
    }
}
$env:CELERY_TASK_ALWAYS_EAGER = "True"

$argsList = @("manage.py", "wipe_everything", "--users", "--confirm", "DELETE-EVERYTHING")
if ($AdminEmail) { $argsList += @("--admin-email", $AdminEmail) }
python @argsList
