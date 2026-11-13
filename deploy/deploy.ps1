<#
  Deploys city maps: pushes the committed code to GitHub, then the server pulls it and rebuilds.

    .\deploy\deploy.ps1

  Commit your changes first. Uncommitted changes are NOT deployed.
  On the server, the same thing can be done by hand with: /srv/citymaps/deploy/update.sh
#>
param(
    [string] $Server = "root@194.164.199.244",
    [string] $Key = "$HOME\.ssh\cv_deploy_ed25519",
    [string] $RemoteDir = "/srv/citymaps"
)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$sshOpts = @("-o", "IdentitiesOnly=yes")
if (Test-Path $Key) { $sshOpts += @("-i", $Key) }

$dirty = git -C $root status --porcelain
if ($dirty) { Write-Warning "Uncommitted changes will not be deployed:`n$($dirty -join "`n")" }

Write-Host "==> Pushing to GitHub"
git -C $root push origin main
if ($LASTEXITCODE -ne 0) { throw "git push failed" }

Write-Host "==> Server pulls and rebuilds"
ssh @sshOpts $Server "sh $RemoteDir/deploy/update.sh"
if ($LASTEXITCODE -ne 0) { throw "Remote deploy failed" }

Write-Host "==> Deployed: https://citymaps.mi-fan.fr"
