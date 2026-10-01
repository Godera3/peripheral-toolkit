param([switch]$Elevated)

if (-not $Elevated) {
    # Relaunch as administrator
    $scriptBlock = { & $PSCommandPath -Elevated }
    Start-Process powershell -Verb RunAs -ArgumentList "-NoExit -Command $scriptBlock"
    exit
}

$outDir = if ($env:AULA_CAPTURE_DIR) { $env:AULA_CAPTURE_DIR } else { Join-Path $PSScriptRoot "wireless" }
if (-not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
$tshark = (Get-Command tshark -ErrorAction SilentlyContinue).Source
if (-not $tshark) { $tshark = "C:\Program Files\Wireshark\tshark.exe" }
$captureTime = 8

$scenarios = @(
    @{Name="01_fixed_on"}
    @{Name="02_light_off"}
    @{Name="03_respire"}
    @{Name="04_rainbow"}
    @{Name="05_flash_away"}
    @{Name="06_raindrops"}
    @{Name="07_rainbow_wheel"}
    @{Name="08_ripples_shining"}
    @{Name="09_stars_twinkle"}
    @{Name="10_retro_snake"}
    @{Name="11_neon_stream"}
    @{Name="12_reaction"}
    @{Name="13_sine_wave"}
    @{Name="14_rotating_windmill"}
    @{Name="15_colorful_waterfall"}
    @{Name="16_blossoming"}
    @{Name="17_self_define"}
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  WIRELESS AULA Capture Script" -ForegroundColor Cyan
Write-Host "  (Running as Administrator)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

for ($i = 0; $i -lt $scenarios.Length; $i++) {
    $s = $scenarios[$i]
    $outFile = Join-Path $outDir "$($s.Name).pcapng"

    Write-Host "----------------------------------------" -ForegroundColor Yellow
    Write-Host "[$($i+1)/$($scenarios.Length)] $($s.Name)" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Yellow
    Write-Host "Switch to this mode in AULA software NOW!" -ForegroundColor Green
    Write-Host ""

    Read-Host "Press Enter when ready to start capture"

    Write-Host "Capturing for $captureTime seconds..." -ForegroundColor Cyan
    & $tshark -i "\\.\USBPcap1" -a duration:$captureTime -w $outFile 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "Saved: $outFile" -ForegroundColor Green
    } else {
        Write-Host "Error capturing (exit: $LASTEXITCODE)" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All done!" -ForegroundColor Cyan
Get-ChildItem -Path $outDir -Filter "*.pcapng" | Format-Table Name, Length
