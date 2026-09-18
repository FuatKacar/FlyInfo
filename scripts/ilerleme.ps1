# Uzun hesaplamaların ilerlemesini canlı gösterir (Ctrl+C ile çıkılır).
# Kullanım (proje klasöründe):
#   powershell -ExecutionPolicy Bypass -File scripts\ilerleme.ps1                 # senaryo hesabı
#   powershell -ExecutionPolicy Bypass -File scripts\ilerleme.ps1 zaman_profili   # zaman profili
param([string]$Gunluk = "hesapla")

$log = Join-Path $PSScriptRoot "..\artifacts\$Gunluk.log"
$total = 225

while ($true) {
    if (-not (Test-Path $log)) {
        Write-Host "Günlük dosyası bulunamadı: $log"
        break
    }
    $lines = Get-Content $log -Encoding UTF8
    $done = @($lines | Where-Object { $_ -match "hesaplandı|mevcut" }).Count
    $last = $lines | Where-Object { $_ -match "^\[" } | Select-Object -Last 1
    $elapsed = 0
    if ($last -match "^\[\s*(\d+) sn\]") { $elapsed = [int]$Matches[1] }

    $percent = [math]::Round(100 * $done / $total, 1)
    $remaining = "-"
    # Hız yalnızca bu oturumda gerçekten hesaplanan senaryolardan ölçülür ("mevcut" olanlar anında geçer)
    $computed = @($lines | Where-Object { $_ -match "hesaplandı" }).Count
    if ($computed -ge 1) {
        $seconds = ($elapsed / $computed) * ($total - $done)
        $remaining = "{0} sa {1} dk" -f [math]::Floor($seconds / 3600), [math]::Floor(($seconds % 3600) / 60)
    }
    $bar = ("#" * [math]::Floor($percent / 2)).PadRight(50, ".")

    Clear-Host
    Write-Host "Senaryo hesaplaması"
    Write-Host "[$bar] %$percent  ($done / $total)"
    Write-Host "Tahmini kalan süre: $remaining"
    Write-Host ""
    Write-Host "Son satır: $last"
    if ($lines -match "CIKIS=") {
        Write-Host ""
        Write-Host "Hesaplama bitti."
        break
    }
    Start-Sleep -Seconds 10
}
