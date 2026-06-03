param(
    [string]$ProjectRoot = "F:\zhangshu",
    [switch]$SkipFrontend,
    [switch]$SkipBackend,
    [switch]$SkipTauri,
    [switch]$SkipInstaller,
    [switch]$SkipPackagedBackendSmoke,
    [string]$DownloadBaseUrl = ""
)

$ErrorActionPreference = "Stop"

$FrontendDir = Join-Path $ProjectRoot "frontend"
$BackendDir = Join-Path $ProjectRoot "backend"
$TauriDir = Join-Path $FrontendDir "src-tauri"
$ReleaseDir = Join-Path $ProjectRoot "release"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  章枢桌面版 - 一键构建安装程序" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 0a: Read and verify version consistency ──
Write-Host "── Step 0: Version consistency check ──" -ForegroundColor Yellow

$PkgJsonPath = Join-Path $FrontendDir "package.json"
$PkgJson = Get-Content $PkgJsonPath -Raw | ConvertFrom-Json
$AppVersion = $PkgJson.version
if ([string]::IsNullOrWhiteSpace($AppVersion)) {
    Write-Host "[ERROR] Cannot read version from package.json" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] package.json version: $AppVersion" -ForegroundColor Green

# Verify Cargo.toml version
$CargoTomlPath = Join-Path $TauriDir "Cargo.toml"
$CargoLines = Get-Content $CargoTomlPath
$CargoVersion = $null
foreach ($line in $CargoLines) {
    if ($line -match '^\s*version\s*=\s*"(.+)"') {
        $CargoVersion = $Matches[1]
        break
    }
}
if ([string]::IsNullOrWhiteSpace($CargoVersion)) {
    Write-Host "[ERROR] Cannot parse version from Cargo.toml" -ForegroundColor Red
    exit 1
}
if ($CargoVersion -ne $AppVersion) {
    Write-Host "[ERROR] Version mismatch: package.json=$AppVersion, Cargo.toml=$CargoVersion" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Cargo.toml version:   $CargoVersion" -ForegroundColor Green

# Verify tauri.conf.json version
$TauriConfPath = Join-Path $TauriDir "tauri.conf.json"
$TauriConf = Get-Content $TauriConfPath -Raw | ConvertFrom-Json
$TauriVersion = $TauriConf.version
if ($TauriVersion -ne $AppVersion) {
    Write-Host "[ERROR] Version mismatch: package.json=$AppVersion, tauri.conf.json=$TauriVersion" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] tauri.conf.json version: $TauriVersion" -ForegroundColor Green
Write-Host "[OK] All versions consistent: $AppVersion" -ForegroundColor Green
Write-Host ""

# ── Step 0b: Check prerequisites ──
$Python = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "[ERROR] Python venv not found: $Python" -ForegroundColor Red
    exit 1
}

# Find Inno Setup compiler
$IsccExe = $null
$IsccPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
)
foreach ($path in $IsccPaths) {
    if (Test-Path $path) {
        $IsccExe = $path
        break
    }
}
# Also check PATH
if (-not $IsccExe) {
    $IsccExe = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
}

if (-not $IsccExe -and -not $SkipInstaller) {
    Write-Host "[WARNING] Inno Setup 6 not found!" -ForegroundColor Yellow
    Write-Host "  Download from: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    Write-Host "  Install to default location, then re-run this script." -ForegroundColor Yellow
    Write-Host "  Or use -SkipInstaller to skip installer compilation." -ForegroundColor Yellow
    $SkipInstaller = $true
}

if ($IsccExe) {
    Write-Host "[OK] Inno Setup: $IsccExe" -ForegroundColor Green
}

# ── Step 1: Build frontend ──
if (-not $SkipFrontend) {
    Write-Host ""
    Write-Host "── Step 1/5: Build frontend ──" -ForegroundColor Yellow
    Set-Location $FrontendDir
    npm run tauri:build:frontend
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Frontend build failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Frontend built" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "── Step 1/5: Frontend (skipped) ──" -ForegroundColor DarkGray
}

# ── Step 2: Build backend (PyInstaller --onedir) ──
if (-not $SkipBackend) {
    Write-Host ""
    Write-Host "── Step 2/5: Build backend (PyInstaller --onedir) ──" -ForegroundColor Yellow
    Set-Location $FrontendDir
    npm run tauri:build:backend
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Backend build failed!" -ForegroundColor Red
        exit 1
    }
    # Verify output
    $BackendOutput = Join-Path $TauriDir "binaries\zhangshu-backend\zhangshu-backend.exe"
    if (-not (Test-Path $BackendOutput)) {
        Write-Host "[ERROR] Backend exe not found: $BackendOutput" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Backend built" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "── Step 2/5: Backend (skipped) ──" -ForegroundColor DarkGray
}

# ── Step 2.5: Smoke test packaged backend ──
if (-not $SkipPackagedBackendSmoke) {
    Write-Host ""
    Write-Host "── Step 2.5/5: Smoke test packaged backend ──" -ForegroundColor Yellow
    Set-Location $ProjectRoot
    powershell -ExecutionPolicy Bypass -File .\scripts\smoke_packaged_backend.ps1 -ProjectRoot $ProjectRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Packaged backend smoke test failed!" -ForegroundColor Red
        Write-Host "  The PyInstaller backend is missing required modules (e.g. cloud routers)." -ForegroundColor Red
        Write-Host "  Fix the issue before building the installer." -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Smoke test passed" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "── Step 2.5/5: Smoke test (skipped) ──" -ForegroundColor DarkGray
}

# ── Step 3: Build Tauri exe + updater helper ──
if (-not $SkipTauri) {
    Write-Host ""
    Write-Host "── Step 3/5: Build Tauri desktop exe + updater helper ──" -ForegroundColor Yellow
    Set-Location $TauriDir
    $env:NO_PROXY = "*"
    cargo build --release
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Tauri build failed!" -ForegroundColor Red
        exit 1
    }
    $TauriExe = Join-Path $TauriDir "target\release\zhangshu-desktop.exe"
    if (-not (Test-Path $TauriExe)) {
        Write-Host "[ERROR] Tauri exe not found: $TauriExe" -ForegroundColor Red
        exit 1
    }
    $UpdaterExe = Join-Path $TauriDir "target\release\zhangshu-updater.exe"
    if (-not (Test-Path $UpdaterExe)) {
        Write-Host "[ERROR] Updater helper not found: $UpdaterExe" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Tauri exe built" -ForegroundColor Green
    Write-Host "[OK] Updater helper built" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "── Step 3/5: Tauri exe + updater (skipped) ──" -ForegroundColor DarkGray
}

# ── Step 4: Compile Inno Setup installer ──
if (-not $SkipInstaller) {
    Write-Host ""
    Write-Host "── Step 4/5: Compile installer (v$AppVersion) ──" -ForegroundColor Yellow
    $IssFile = Join-Path $ProjectRoot "build\installer\zhangshu.iss"
    & $IsccExe /DMyAppVersion=$AppVersion $IssFile
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Inno Setup compilation failed!" -ForegroundColor Red
        exit 1
    }
    $InstallerName = "章枢_Setup_${AppVersion}_windows_x64.exe"
    $InstallerExe = Join-Path $ReleaseDir $InstallerName
    if (Test-Path $InstallerExe) {
        $Size = [math]::Round((Get-Item $InstallerExe).Length / 1MB, 1)
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Green
        Write-Host "  Installer built successfully!" -ForegroundColor Green
        Write-Host "  Output: $InstallerExe" -ForegroundColor Green
        Write-Host "  Size:   ${Size} MB" -ForegroundColor Green
        Write-Host "============================================" -ForegroundColor Green

        # ── Step 5: Generate release manifest ──
        Write-Host ""
        Write-Host "── Step 5/5: Generate release manifest ──" -ForegroundColor Yellow
        Set-Location $ProjectRoot
        $ManifestArgs = @{
            ProjectRoot    = $ProjectRoot
            Version        = $AppVersion
            InstallerPath  = $InstallerExe
        }
        if (-not [string]::IsNullOrWhiteSpace($DownloadBaseUrl)) {
            $ManifestArgs["DownloadBaseUrl"] = $DownloadBaseUrl
        }
        powershell -ExecutionPolicy Bypass -File .\scripts\generate_update_manifest.ps1 @ManifestArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[WARNING] Manifest generation failed (non-fatal)" -ForegroundColor Yellow
        } else {
            Write-Host "[OK] Release manifest generated" -ForegroundColor Green
        }
    } else {
        Write-Host "[WARNING] Installer exe not found at expected path: $InstallerExe" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "── Step 4/5: Installer (skipped) ──" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Build artifacts ready for manual installer compilation." -ForegroundColor Yellow
}

Set-Location $ProjectRoot
