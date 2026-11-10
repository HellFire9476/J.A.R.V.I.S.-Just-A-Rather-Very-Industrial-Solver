
$ErrorActionPreference = "Stop"

# Version fixe pour garantir la reproductibilite
$Version = "v3.51.0"
$BaseUrl = "https://raw.githubusercontent.com/tabler/tabler-icons/$Version"

# Dossiers du projet
$Root = Split-Path -Parent $PSScriptRoot
$IconDir = Join-Path $Root "assets\icons\navigation"
$LicenseDir = Join-Path $Root "assets\licenses"

New-Item -ItemType Directory -Force -Path $IconDir | Out-Null
New-Item -ItemType Directory -Force -Path $LicenseDir | Out-Null

# Liste des icones necessaires
$Icons = @(
    "layout-dashboard",
    "building-factory-2",
    "hierarchy-2",
    "shovel",
    "bolt",
    "book-2",
    "flask-2"
)

# TLS 1.2 pour Windows PowerShell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Write-Host "`nJ.A.R.V.I.S. - TELECHARGEMENT DES ICONES" -ForegroundColor Cyan
Write-Host "Version Tabler : $Version`n" -ForegroundColor Gray

foreach ($Icon in $Icons) {
    $Url = "$BaseUrl/icons/outline/$Icon.svg"
    $Destination = Join-Path $IconDir "$Icon.svg"

    Write-Host "Telechargement : $Icon ..." -ForegroundColor Yellow

    Invoke-WebRequest `
        -Uri $Url `
        -OutFile $Destination `
        -UseBasicParsing

    Write-Host "  OK" -ForegroundColor Green
}

# Licence officielle
Write-Host "`nTelechargement de la licence MIT..." -ForegroundColor Yellow

Invoke-WebRequest `
    -Uri "$BaseUrl/LICENSE" `
    -OutFile (Join-Path $LicenseDir "TABLER_LICENSE.txt") `
    -UseBasicParsing

# Informations de provenance
@"
Tabler Icons
Version : 3.51.0
Source : https://github.com/tabler/tabler-icons
Licence : MIT

Les fichiers SVG de ce dossier proviennent de Tabler Icons.
La licence MIT originale est conservee dans TABLER_LICENSE.txt.
"@ | Set-Content `
    -Path (Join-Path $LicenseDir "TABLER_ATTRIBUTION.txt") `
    -Encoding UTF8

Write-Host "`n====================================" -ForegroundColor Cyan
Write-Host "Telechargement termine !" -ForegroundColor Green
Write-Host "Icônes : $IconDir"
Write-Host "Licence : $LicenseDir"
Write-Host "====================================" -ForegroundColor Cyan
