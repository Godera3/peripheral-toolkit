$outDir = Split-Path -Parent $PSCommandPath
$tshark = "C:\Program Files\Wireshark\tshark.exe"
$captureTime = 8  # seconds per capture

$scenarios = @(
    @{Name="01_red";         Prompt="Change AULA RGB to SOLID RED, then press Enter"}
    @{Name="02_green";       Prompt="Change AULA RGB to SOLID GREEN, then press Enter"}
    @{Name="03_blue";        Prompt="Change AULA RGB to SOLID BLUE, then press Enter"}
    @{Name="04_breathing";   Prompt="Change AULA RGB to BREATHING effect, then press Enter"}
    @{Name="05_rainbow";     Prompt="Change AULA RGB to RAINBOW WAVE effect, then press Enter"}
    @{Name="06_brightness";  Prompt="Change AULA BRIGHTNESS, then press Enter"}
    @{Name="07_pollingrate"; Prompt="Change AULA POLLING RATE, then press Enter"}
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AULA USB Capture Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will capture USB traffic while you change settings."
Write-Host "Output folder: $outDir"
Write-Host ""
Write-Host "Steps:"
Write-Host "  1. Script starts tshark capture"
Write-Host "  2. Change the setting in AULA software"
Write-Host "  3. Script stops capture after $captureTime seconds"
Write-Host "  4. Repeats for next setting"
Write-Host ""

for ($i = 0; $i -lt $scenarios.Length; $i++) {
    $s = $scenarios[$i]
    $outFile = Join-Path $outDir "$($s.Name).pcapng"

    Write-Host "----------------------------------------" -ForegroundColor Yellow
    Write-Host "[$($i+1)/$($scenarios.Length)] $($s.Name)" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Yellow
    Write-Host $s.Prompt -ForegroundColor Green
    Write-Host ""

    # Ask user to press Enter when ready
    Read-Host "Press Enter when AULA is open and ready"

    Write-Host "Starting capture... (will run for $captureTime seconds)" -ForegroundColor Cyan

    # Start tshark in background - capture from USBPcap1 interface
    $proc = Start-Process -FilePath $tshark -ArgumentList "-i `"\\.\USBPcap1`" -w `"$outFile`" -a duration:$captureTime" -NoNewWindow -PassThru

    Write-Host "CAPTURE RUNNING - Change the setting in AULA software NOW!" -ForegroundColor Magenta -BackgroundColor Black

    # Wait for capture to complete
    $proc.WaitForExit()

    if ($proc.ExitCode -eq 0) {
        Write-Host "Capture saved: $outFile" -ForegroundColor Green
    } else {
        Write-Host "Capture may have errors (exit code: $($proc.ExitCode))" -ForegroundColor Red
    }

    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All captures complete!" -ForegroundColor Cyan
Write-Host "  Files saved to: $outDir" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# List the files
Get-ChildItem -Path $outDir -Filter "*.pcapng" | Format-Table Name, Length
