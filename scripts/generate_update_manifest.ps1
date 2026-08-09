param(
    [Parameter(Mandatory)]
    [string]$Version,

    [Parameter(Mandatory)]
    [string]$InstallerPath,

    [string]$ProjectRoot = "F:\zhangshu",

    [string]$DownloadBaseUrl = "",

    [string]$Channel = "stable",

    [string]$Platform = "windows",

    [string]$Arch = "x64"
)

$ErrorActionPreference = "Stop"

# Validate version is valid semver
if ($Version -notmatch '^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$') {
    Write-Host "[ERROR] Invalid version format: $Version" -ForegroundColor Red
    exit 1
}

# Validate installer exists
if (-not (Test-Path $InstallerPath)) {
    Write-Host "[ERROR] Installer not found: $InstallerPath" -ForegroundColor Red
    exit 1
}

# Compute SHA256 and file size
Write-Host "Computing SHA256 for installer..." -ForegroundColor Cyan
$HashObj = Get-FileHash -Path $InstallerPath -Algorithm SHA256
$Sha256 = $HashObj.Hash.ToLower()
$SizeBytes = (Get-Item $InstallerPath).Length

Write-Host "  SHA256:  $Sha256" -ForegroundColor Green
Write-Host "  Size:    $SizeBytes bytes ($([math]::Round($SizeBytes / 1MB, 1)) MB)" -ForegroundColor Green

# Build download URL
$InstallerFileName = [System.IO.Path]::GetFileName($InstallerPath)
if ([string]::IsNullOrWhiteSpace($DownloadBaseUrl)) {
    # No base URL provided — use a placeholder that makes it clear this needs to be filled in
    $DownloadUrl = "https://RELEASE_HOST/zhangshu/releases/$InstallerFileName"
    Write-Host "[WARNING] No -DownloadBaseUrl provided. Using placeholder URL." -ForegroundColor Yellow
    Write-Host "  Re-run with -DownloadBaseUrl 'https://your-cdn.com/path' for production." -ForegroundColor Yellow
} else {
    $BaseUrl = $DownloadBaseUrl.TrimEnd('/')
    $DownloadUrl = "$BaseUrl/$InstallerFileName"
}

# Validate download URL is HTTPS (unless explicitly local/dev)
if ($DownloadUrl -notmatch '^https://') {
    Write-Host "[ERROR] Download URL must be HTTPS: $DownloadUrl" -ForegroundColor Red
    exit 1
}

# Read release notes from CHANGELOG if available
$ChangelogPath = Join-Path $ProjectRoot "CHANGELOG.md"
$ReleaseNotes = @()
if (Test-Path $ChangelogPath) {
    $Lines = Get-Content $ChangelogPath
    $InSection = $false
    foreach ($line in $Lines) {
        if ($line -match "^## \[$Version\]") {
            $InSection = $true
            continue
        }
        if ($InSection -and $line -match "^## ") {
            break
        }
        if ($InSection -and $line.Trim() -ne "" -and $line -notmatch "^#") {
            $ReleaseNotes += $line.Trim()
        }
    }
}
if ($ReleaseNotes.Count -eq 0) {
    $ReleaseNotes = @("版本更新与稳定性改进")
}

# Build manifest object
$Manifest = [ordered]@{
    schemaVersion       = 1
    channel             = $Channel
    platform            = $Platform
    arch                = $Arch
    version             = $Version
    minSupportedVersion = "0.8.0"
    publishedAt         = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    installer           = [ordered]@{
        url       = $DownloadUrl
        sha256    = $Sha256
        sizeBytes = $SizeBytes
    }
    releaseNotes        = $ReleaseNotes
    critical            = $false
}

# Write manifest to release directory
$ReleaseDir = Join-Path $ProjectRoot "release"
if (-not (Test-Path $ReleaseDir)) {
    New-Item -ItemType Directory -Path $ReleaseDir -Force | Out-Null
}

$ManifestFileName = "latest.$Platform-$Arch.json"
$ManifestPath = Join-Path $ReleaseDir $ManifestFileName

$Manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $ManifestPath -Encoding UTF8

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Release manifest generated!" -ForegroundColor Green
Write-Host "  Path: $ManifestPath" -ForegroundColor Green
Write-Host "  Version: $Version" -ForegroundColor Green
Write-Host "  SHA256: $Sha256" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
