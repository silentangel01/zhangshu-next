param(
    [string]$ProjectRoot = "F:\zhangshu",
    [int]$TestPort = 18765,
    [int]$TimeoutSecs = 30
)

$ErrorActionPreference = "Stop"

# ── Paths ──
$BackendExe = Join-Path $ProjectRoot "frontend\src-tauri\binaries\zhangshu-backend\zhangshu-backend.exe"
$FrontendDist = Join-Path $ProjectRoot "frontend\dist"

# ── Verify backend exe exists ──
if (-not (Test-Path $BackendExe)) {
    Write-Host "[ERROR] Packaged backend not found: $BackendExe" -ForegroundColor Red
    Write-Host "  Run 'npm run tauri:build:backend' first." -ForegroundColor Yellow
    exit 1
}

# ── Find a free port if default is occupied ──
$portInUse = $false
try {
    $conn = New-Object System.Net.Sockets.TcpClient
    $conn.Connect("127.0.0.1", $TestPort)
    $conn.Close()
    $portInUse = $true
} catch {
    # Port is free
}

if ($portInUse) {
    Write-Host "[WARN] Port $TestPort is in use, searching for free port..." -ForegroundColor Yellow
    $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    $TestPort = $listener.LocalEndpoint.Port
    $listener.Stop()
    Write-Host "[INFO] Using free port: $TestPort" -ForegroundColor Yellow
}

# ── Create temp directories ──
$TempBase = Join-Path $env:TEMP "zhangshu-smoke-$(Get-Date -Format 'yyyyMMddHHmmss')"
$TempData = Join-Path $TempBase "data"
$TempLogs = Join-Path $TempBase "logs"

New-Item -ItemType Directory -Path $TempData -Force | Out-Null
New-Item -ItemType Directory -Path $TempLogs -Force | Out-Null

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Packaged Backend Smoke Test" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Backend: $BackendExe"
Write-Host "Port:    $TestPort"
Write-Host "Data:    $TempData"
Write-Host ""

# ── State ──
$BackendProcess = $null
$BackendPid = 0

# ── Cleanup function (called in finally block) ──
function Invoke-Cleanup {
    if ($BackendProcess -and -not $BackendProcess.HasExited) {
        Write-Host "[INFO] Stopping backend (PID: $BackendPid)..." -ForegroundColor Yellow
        try { $BackendProcess.Kill() } catch {}
        try { $BackendProcess.WaitForExit(5000) } catch {}
    }
    if (Test-Path $TempBase) {
        Remove-Item -Path $TempBase -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# ── Start backend using System.Diagnostics.Process ──
# Do NOT copy parent env — ProcessStartInfo with UseShellExecute=$false
# inherits parent env automatically. We only set smoke-specific vars.
Write-Host "[INFO] Starting packaged backend..." -ForegroundColor Yellow

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $BackendExe
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true

# Set only the smoke test environment variables.
# The child process inherits PATH, SystemRoot, etc. from the parent automatically.
$psi.EnvironmentVariables["ZHANGSHU_BACKEND_HOST"] = "127.0.0.1"
$psi.EnvironmentVariables["ZHANGSHU_BACKEND_PORT"] = $TestPort.ToString()
$psi.EnvironmentVariables["ZHANGSHU_DATA_DIR"] = $TempData
$psi.EnvironmentVariables["ZHANGSHU_LOG_DIR"] = $TempLogs
$psi.EnvironmentVariables["ZHANGSHU_FRONTEND_DIST"] = $FrontendDist
$psi.EnvironmentVariables["ZHANGSHU_DB_FILENAME"] = "zhangshu.sqlite3"
$psi.EnvironmentVariables["ZHANGSHU_CLOUD_API_BASE_URL"] = "https://api.emailbs.xin"
$psi.EnvironmentVariables["ZHANGSHU_SKIP_DOTENV"] = "1"
$psi.EnvironmentVariables["PYTHONUNBUFFERED"] = "1"

try {
    $BackendProcess = [System.Diagnostics.Process]::Start($psi)
    $BackendPid = $BackendProcess.Id
    Write-Host "[INFO] Backend PID: $BackendPid" -ForegroundColor Yellow

    # Drain stdout/stderr asynchronously to prevent blocking
    $stdoutTask = $BackendProcess.StandardOutput.ReadToEndAsync()
    $stderrTask = $BackendProcess.StandardError.ReadToEndAsync()
} catch {
    Write-Host "[FAIL] Failed to start backend process: $_" -ForegroundColor Red
    Invoke-Cleanup
    exit 1
}

# ── All remaining logic wrapped in try/finally for cleanup ──
try {
    # ── Wait for /health ──
    Write-Host "[INFO] Waiting for /health endpoint..." -ForegroundColor Yellow
    $HealthUrl = "http://127.0.0.1:$TestPort/health"
    $Deadline = (Get-Date).AddSeconds($TimeoutSecs)
    $Healthy = $false

    while ((Get-Date) -lt $Deadline) {
        if ($BackendProcess.HasExited) {
            Write-Host "[FAIL] Backend process exited unexpectedly (exit code: $($BackendProcess.ExitCode))" -ForegroundColor Red
            try {
                $stderrContent = $stderrTask.Result
                if ($stderrContent) { Write-Host "[INFO] stderr:" -ForegroundColor Yellow; Write-Host $stderrContent }
            } catch {}
            Invoke-Cleanup
            exit 1
        }
        try {
            $Response = Invoke-WebRequest -Uri $HealthUrl -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            if ($Response.StatusCode -eq 200) {
                $Healthy = $true
                break
            }
        } catch {}
        Start-Sleep -Milliseconds 200
    }

    if (-not $Healthy) {
        Write-Host "[FAIL] Backend did not become healthy within ${TimeoutSecs}s" -ForegroundColor Red
        try {
            $stderrContent = $stderrTask.Result
            if ($stderrContent) { Write-Host "[INFO] stderr:" -ForegroundColor Yellow; Write-Host $stderrContent }
        } catch {}
        Invoke-Cleanup
        exit 1
    }

    Write-Host "[OK] Backend is healthy" -ForegroundColor Green

    # ── Helper: assert response is JSON, not HTML ──
    function Assert-JsonResponse {
        param($Response, $TestName)
        $Body = $Response.Content
        if ($Body -like "*<html*" -or $Body -like "*<!DOCTYPE*" -or $Body -like '*id="app"*') {
            Write-Host "[FAIL] $TestName returned HTML (SPA fallback leaked)" -ForegroundColor Red
            Write-Host $Body.Substring(0, [Math]::Min(200, $Body.Length))
            return $false
        }
        $ct = $Response.Headers["Content-Type"]
        if (-not $ct -or $ct -notlike "*application/json*") {
            Write-Host "[FAIL] $TestName Content-Type is not JSON: $ct" -ForegroundColor Red
            return $false
        }
        return $true
    }

    # ── Test 1: /api/cloud/account/status ──
    Write-Host ""
    Write-Host "── Test 1: /api/cloud/account/status ──" -ForegroundColor Yellow
    $CloudStatusUrl = "http://127.0.0.1:$TestPort/api/cloud/account/status"

    try {
        $Response = Invoke-WebRequest -Uri $CloudStatusUrl -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    } catch {
        Write-Host "[FAIL] Request failed: $_" -ForegroundColor Red
        Invoke-Cleanup
        exit 1
    }

    if ($Response.StatusCode -ne 200) {
        Write-Host "[FAIL] Expected status 200, got $($Response.StatusCode)" -ForegroundColor Red
        Invoke-Cleanup
        exit 1
    }

    if (-not (Assert-JsonResponse $Response "account/status")) {
        Invoke-Cleanup
        exit 1
    }

    $Body = $Response.Content
    try {
        $Json = $Body | ConvertFrom-Json
    } catch {
        Write-Host "[FAIL] Response is not valid JSON:" -ForegroundColor Red
        Write-Host $Body.Substring(0, [Math]::Min(200, $Body.Length))
        Invoke-Cleanup
        exit 1
    }

    $MissingFields = @()
    if ($null -eq $Json.logged_in) { $MissingFields += "logged_in" }
    if ($null -eq $Json.cloud_available) { $MissingFields += "cloud_available" }
    if (-not (Get-Member -InputObject $Json -Name "email" -MemberType NoteProperty)) { $MissingFields += "email" }
    if (-not (Get-Member -InputObject $Json -Name "display_name" -MemberType NoteProperty)) { $MissingFields += "display_name" }

    if ($MissingFields.Count -gt 0) {
        Write-Host "[FAIL] Missing required fields: $($MissingFields -join ', ')" -ForegroundColor Red
        Invoke-Cleanup
        exit 1
    }

    if ($Json.cloud_available -ne $true) {
        Write-Host "[FAIL] Expected cloud_available=true, got: $($Json.cloud_available)" -ForegroundColor Red
        Invoke-Cleanup
        exit 1
    }

    Write-Host "[OK] account/status returned valid JSON with cloud_available=true" -ForegroundColor Green

    # ── Test 2: Unknown /api/* should not return HTML ──
    Write-Host ""
    Write-Host "── Test 2: Unknown /api/* should not return HTML ──" -ForegroundColor Yellow
    $MissingApiUrl = "http://127.0.0.1:$TestPort/api/__missing_packaged_smoke__"

    try {
        $Response = Invoke-WebRequest -Uri $MissingApiUrl -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        $StatusCode = $Response.StatusCode
        $Body = $Response.Content
    } catch {
        $Exception = $_.Exception
        if ($Exception.Response) {
            $StatusCode = [int]$Exception.Response.StatusCode
            $Reader = New-Object System.IO.StreamReader($Exception.Response.GetResponseStream())
            $Body = $Reader.ReadToEnd()
            $Reader.Close()
        } else {
            Write-Host "[FAIL] Request failed unexpectedly: $_" -ForegroundColor Red
            Invoke-Cleanup
            exit 1
        }
    }

    if ($Body -like "*<html*" -or $Body -like "*<!DOCTYPE*" -or $Body -like '*id="app"*') {
        Write-Host "[FAIL] Unknown /api/* returned HTML (SPA fallback leaked)" -ForegroundColor Red
        Write-Host $Body.Substring(0, [Math]::Min(200, $Body.Length))
        Invoke-Cleanup
        exit 1
    }

    Write-Host "[OK] Unknown /api/* did not return HTML (status: $StatusCode)" -ForegroundColor Green

    # ── Test 3: /api/cloud/network/diagnose returns JSON ──
    Write-Host ""
    Write-Host "── Test 3: /api/cloud/network/diagnose ──" -ForegroundColor Yellow
    $DiagnoseUrl = "http://127.0.0.1:$TestPort/api/cloud/network/diagnose"

    try {
        $Response = Invoke-WebRequest -Uri $DiagnoseUrl -Method POST -ContentType "application/json" -Body "{}" -TimeoutSec 30 -UseBasicParsing -ErrorAction Stop
        $DiagStatus = $Response.StatusCode
        $DiagBody = $Response.Content
    } catch {
        $Exception = $_.Exception
        if ($Exception.Response) {
            $DiagStatus = [int]$Exception.Response.StatusCode
            $Reader = New-Object System.IO.StreamReader($Exception.Response.GetResponseStream())
            $DiagBody = $Reader.ReadToEnd()
            $Reader.Close()
        } else {
            Write-Host "[FAIL] Diagnose request failed unexpectedly: $_" -ForegroundColor Red
            Invoke-Cleanup
            exit 1
        }
    }

    # Must not be HTML or 404
    if ($DiagBody -like "*<html*" -or $DiagBody -like "*<!DOCTYPE*" -or $DiagBody -like '*id="app"*') {
        Write-Host "[FAIL] Diagnose endpoint returned HTML" -ForegroundColor Red
        Invoke-Cleanup
        exit 1
    }

    if ($DiagStatus -eq 404) {
        Write-Host "[FAIL] Diagnose endpoint returned 404 (router not loaded?)" -ForegroundColor Red
        Invoke-Cleanup
        exit 1
    }

    # Should be parseable JSON
    try {
        $null = $DiagBody | ConvertFrom-Json
    } catch {
        Write-Host "[FAIL] Diagnose response is not valid JSON:" -ForegroundColor Red
        Write-Host $DiagBody.Substring(0, [Math]::Min(200, $DiagBody.Length))
        Invoke-Cleanup
        exit 1
    }

    Write-Host "[OK] Diagnose endpoint returned JSON (status: $DiagStatus)" -ForegroundColor Green

    # ── Test 4: Login with invalid credentials returns structured JSON error ──
    Write-Host ""
    Write-Host "── Test 4: Login with invalid credentials ──" -ForegroundColor Yellow
    $LoginUrl = "http://127.0.0.1:$TestPort/api/cloud/auth/login"
    $LoginBody = '{"email":"invalid_smoke_test@example.com","password":"wrongpassword123"}'

    try {
        $Response = Invoke-WebRequest -Uri $LoginUrl -Method POST -ContentType "application/json" -Body $LoginBody -TimeoutSec 15 -UseBasicParsing -ErrorAction Stop
        $LoginStatus = $Response.StatusCode
        $LoginResp = $Response.Content
    } catch {
        $Exception = $_.Exception
        if ($Exception.Response) {
            $LoginStatus = [int]$Exception.Response.StatusCode
            $Reader = New-Object System.IO.StreamReader($Exception.Response.GetResponseStream())
            $LoginResp = $Reader.ReadToEnd()
            $Reader.Close()
        } else {
            Write-Host "[FAIL] Login request failed unexpectedly: $_" -ForegroundColor Red
            Invoke-Cleanup
            exit 1
        }
    }

    # 401 is expected for invalid credentials
    if ($LoginResp -like "*<html*" -or $LoginResp -like "*<!DOCTYPE*") {
        Write-Host "[FAIL] Login endpoint returned HTML" -ForegroundColor Red
        Invoke-Cleanup
        exit 1
    }

    if ($LoginStatus -eq 404) {
        Write-Host "[FAIL] Login endpoint returned 404 (router not loaded?)" -ForegroundColor Red
        Invoke-Cleanup
        exit 1
    }

    if ($LoginStatus -eq 500) {
        Write-Host "[FAIL] Login endpoint returned 500 (internal error)" -ForegroundColor Red
        Write-Host $LoginResp.Substring(0, [Math]::Min(300, $LoginResp.Length))
        Invoke-Cleanup
        exit 1
    }

    # Must be JSON
    try {
        $null = $LoginResp | ConvertFrom-Json
    } catch {
        Write-Host "[FAIL] Login response is not valid JSON:" -ForegroundColor Red
        Write-Host $LoginResp.Substring(0, [Math]::Min(200, $LoginResp.Length))
        Invoke-Cleanup
        exit 1
    }

    Write-Host "[OK] Login with invalid creds returned structured JSON (status: $LoginStatus)" -ForegroundColor Green

    Write-Host ""
    Write-Host "============================================" -ForegroundColor Green
    Write-Host "  All smoke tests passed!" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green

    Invoke-Cleanup
    exit 0
} catch {
    Write-Host "[FAIL] Unexpected error: $_" -ForegroundColor Red
    Invoke-Cleanup
    exit 1
}
