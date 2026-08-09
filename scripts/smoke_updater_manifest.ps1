param(
    [string]$ProjectRoot = "F:\zhangshu",
    [string]$Platform = "windows",
    [string]$Arch = "x64"
)

$ErrorActionPreference = "Stop"

$ReleaseDir = Join-Path $ProjectRoot "release"
$ManifestFileName = "latest.$Platform-$Arch.json"
$ManifestPath = Join-Path $ReleaseDir $ManifestFileName

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Updater Manifest Smoke Test" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$Passed = 0
$Failed = 0

function Test-Check {
    param([string]$Name, [bool]$Condition, [string]$Detail = "")
    if ($Condition) {
        Write-Host "  [PASS] $Name" -ForegroundColor Green
        $script:Passed++
    } else {
        Write-Host "  [FAIL] $Name" -ForegroundColor Red
        if ($Detail) {
            Write-Host "         $Detail" -ForegroundColor Red
        }
        $script:Failed++
    }
}

# 1. Manifest file exists
Test-Check "Manifest file exists" (Test-Path $ManifestPath) "Expected: $ManifestPath"
if (-not (Test-Path $ManifestPath)) {
    Write-Host ""
    Write-Host "Cannot continue: manifest file not found." -ForegroundColor Red
    exit 1
}

# 2. Manifest is valid JSON
$ManifestContent = Get-Content $ManifestPath -Raw -Encoding UTF8
$Manifest = $null
try {
    $Manifest = $ManifestContent | ConvertFrom-Json
    Test-Check "Manifest is valid JSON" $true
} catch {
    Test-Check "Manifest is valid JSON" $false $_.Exception.Message
    exit 1
}

# 3. Required fields exist
Test-Check "schemaVersion exists" ($null -ne $Manifest.schemaVersion)
Test-Check "schemaVersion is 1" ($Manifest.schemaVersion -eq 1)
Test-Check "channel exists" (-not [string]::IsNullOrWhiteSpace($Manifest.channel))
Test-Check "platform exists" ($Manifest.platform -eq $Platform)
Test-Check "arch exists" ($Manifest.arch -eq $Arch)
Test-Check "version exists" (-not [string]::IsNullOrWhiteSpace($Manifest.version))

# 4. Version is valid semver
$SemverPattern = '^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$'
Test-Check "version is valid semver" ($Manifest.version -match $SemverPattern) "Got: $($Manifest.version)"

# 5. minSupportedVersion exists and is valid semver
Test-Check "minSupportedVersion exists" (-not [string]::IsNullOrWhiteSpace($Manifest.minSupportedVersion))
Test-Check "minSupportedVersion is valid semver" ($Manifest.minSupportedVersion -match $SemverPattern)

# 6. publishedAt exists and looks like ISO 8601
Test-Check "publishedAt exists" (-not [string]::IsNullOrWhiteSpace($Manifest.publishedAt))
$Iso8601Pattern = '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
Test-Check "publishedAt looks like ISO 8601" ($Manifest.publishedAt -match $Iso8601Pattern) `
    "Got: $($Manifest.publishedAt)"

# 7. Installer object exists with required fields
Test-Check "installer.url exists" (-not [string]::IsNullOrWhiteSpace($Manifest.installer.url))
Test-Check "installer.sha256 exists" (-not [string]::IsNullOrWhiteSpace($Manifest.installer.sha256))
Test-Check "installer.sizeBytes exists" ($Manifest.installer.sizeBytes -gt 0)

# 8. SHA256 is 64 hex chars
$Sha256Pattern = '^[a-f0-9]{64}$'
Test-Check "installer.sha256 is 64 hex chars" ($Manifest.installer.sha256 -match $Sha256Pattern) "Got: $($Manifest.installer.sha256)"

# 9. Download URL is HTTPS
Test-Check "installer.url is HTTPS" ($Manifest.installer.url -match '^https://')

# 9b. Installer URL host is in the trusted allowlist
$AllowedInstallerHosts = @("downloads.zhangshu.xin", "downloads.emailbs.xin")
$InstallerUri = [System.Uri]$Manifest.installer.url
$InstallerHost = $InstallerUri.Host
Test-Check "installer.url host is in allowlist" ($AllowedInstallerHosts -contains $InstallerHost) `
    "Got: $InstallerHost, Allowed: $($AllowedInstallerHosts -join ', ')"

# 9c. sizeBytes is a reasonable value (> 1 MB, < 500 MB)
Test-Check "installer.sizeBytes is reasonable" ($Manifest.installer.sizeBytes -gt 1048576 -and $Manifest.installer.sizeBytes -lt 524288000) `
    "Got: $($Manifest.installer.sizeBytes)"

# 10. releaseNotes is an array
Test-Check "releaseNotes is an array" ($Manifest.releaseNotes -is [System.Array] -or $Manifest.releaseNotes -is [System.Object[]])

# 11. critical is boolean
Test-Check "critical is boolean" ($Manifest.critical -is [bool])

# 12. If installer file exists locally, verify SHA256 matches
$InstallerFileName = [System.IO.Path]::GetFileName($Manifest.installer.url)
$LocalInstaller = Join-Path $ReleaseDir $InstallerFileName
if (Test-Path $LocalInstaller) {
    Write-Host ""
    Write-Host "  Local installer found, verifying SHA256..." -ForegroundColor Cyan
    $ActualHash = (Get-FileHash -Path $LocalInstaller -Algorithm SHA256).Hash.ToLower()
    Test-Check "SHA256 matches local installer" ($ActualHash -eq $Manifest.installer.sha256) `
        "Expected: $($Manifest.installer.sha256), Got: $ActualHash"

    $ActualSize = (Get-Item $LocalInstaller).Length
    Test-Check "sizeBytes matches local installer" ($ActualSize -eq $Manifest.installer.sizeBytes) `
        "Expected: $($Manifest.installer.sizeBytes), Got: $ActualSize"
} else {
    Write-Host ""
    Write-Host "  Local installer not found (skipping hash verification)" -ForegroundColor DarkGray
}

# Summary
Write-Host ""
Write-Host "============================================" -ForegroundColor $(if ($Failed -eq 0) { "Green" } else { "Red" })
Write-Host "  Results: $Passed passed, $Failed failed" -ForegroundColor $(if ($Failed -eq 0) { "Green" } else { "Red" })
Write-Host "============================================" -ForegroundColor $(if ($Failed -eq 0) { "Green" } else { "Red" })

if ($Failed -gt 0) {
    exit 1
}
