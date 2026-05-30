# ===========================================================================
# AUTOMATED FFMEG & DENO INSTALLER - MangaTranslate
# ===========================================================================

$ErrorActionPreference = "Stop"

Write-Host "=====================================" -ForegroundColor Magenta
Write-Host "   AUTOMATED DEPENDENCY INSTALLER   " -ForegroundColor Magenta
Write-Host "=====================================" -ForegroundColor Magenta
Write-Host ""

$binDir = $PSScriptRoot
if (!(Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}

# Resolve paths
$ffmpegExePath = Join-Path $binDir "ffmpeg.exe"
$ffprobeExePath = Join-Path $binDir "ffprobe.exe"
$denoExePath = Join-Path $binDir "deno.exe"

# Enforce TLS 1.2 & Disable PowerShell progress bar overhead (Saves massive download time!)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'
$webClient = New-Object System.Net.WebClient

# 1. Install FFmpeg if missing
$ffmpegInPath = Get-Command ffmpeg -ErrorAction SilentlyContinue
$localFfmpeg = Test-Path $ffmpegExePath

if ($ffmpegInPath -or $localFfmpeg) {
    Write-Host "[INFO] FFmpeg terdeteksi dan siap digunakan." -ForegroundColor Green
} else {
    Write-Host "[INFO] FFmpeg tidak ditemukan. Mengunduh static build FFmpeg otomatis..." -ForegroundColor Yellow
    try {
        Write-Host "Mengunduh FFmpeg essentials build (Kecepatan Penuh)..." -ForegroundColor Cyan
        $url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        $zipFile = Join-Path $binDir "ffmpeg.zip"
        
        $webClient.DownloadFile($url, $zipFile)
        
        Write-Host "Mengekstrak berkas FFmpeg..." -ForegroundColor Cyan
        $tempDir = Join-Path $binDir "temp_ffmpeg"
        if (Test-Path $tempDir) {
            Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
        }
        Expand-Archive -Path $zipFile -DestinationPath $tempDir -Force
        
        $ffmpegExe = Get-ChildItem -Path $tempDir -Filter "ffmpeg.exe" -Recurse | Select-Object -First 1
        $ffprobeExe = Get-ChildItem -Path $tempDir -Filter "ffprobe.exe" -Recurse | Select-Object -First 1
        
        if ($ffmpegExe) {
            Copy-Item $ffmpegExe.FullName -Destination $ffmpegExePath -Force
        }
        if ($ffprobeExe) {
            Copy-Item $ffprobeExe.FullName -Destination $ffprobeExePath -Force
        }
        
        # Clean up
        Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
        Remove-Item -Force $zipFile -ErrorAction SilentlyContinue
        
        Write-Host "[SUCCESS] FFmpeg static build berhasil dipasang!" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Gagal mengunduh/memasang FFmpeg: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# 2. Install Deno if missing
$denoInPath = Get-Command deno -ErrorAction SilentlyContinue
$localDeno = Test-Path $denoExePath

if ($denoInPath -or $localDeno) {
    Write-Host "[INFO] Deno JS Runtime terdeteksi dan siap digunakan." -ForegroundColor Green
} else {
    Write-Host "[INFO] Deno JS Runtime tidak ditemukan. Mengunduh static build Deno otomatis..." -ForegroundColor Yellow
    try {
        Write-Host "Mengunduh Deno portable (Kecepatan Penuh)..." -ForegroundColor Cyan
        $url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
        $zipFile = Join-Path $binDir "deno.zip"
        
        $webClient.DownloadFile($url, $zipFile)
        
        Write-Host "Mengekstrak berkas Deno..." -ForegroundColor Cyan
        $tempDir = Join-Path $binDir "temp_deno"
        if (Test-Path $tempDir) {
            Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
        }
        Expand-Archive -Path $zipFile -DestinationPath $tempDir -Force
        
        $denoExe = Get-ChildItem -Path $tempDir -Filter "deno.exe" -Recurse | Select-Object -First 1
        if ($denoExe) {
            Copy-Item $denoExe.FullName -Destination $denoExePath -Force
        }
        
        # Clean up
        Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
        Remove-Item -Force $zipFile -ErrorAction SilentlyContinue
        
        Write-Host "[SUCCESS] Deno JS Runtime portable berhasil dipasang!" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Gagal mengunduh/memasang Deno: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "[SUCCESS] Semua dependensi eksternal siap!" -ForegroundColor Green
exit 0
