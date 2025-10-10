# MoonLight - Deployment Kılavuzu

## 🚀 Deployment Stratejisi

### Ortamlar

1. **Development (Dev)**
   - Lokal makine
   - Mock connector
   - Debug logging
   - Hızlı iterasyon

2. **Staging (Stage)**
   - Paper mode
   - Real data (opsiyonel)
   - Production-like config
   - Validasyon testleri

3. **Canary**
   - Live mode
   - Tek hesap/ürün
   - %5-10 trafik
   - Yakın izleme

4. **Production (Prod)**
   - Live mode
   - Tüm hesaplar
   - Full monitoring
   - Rollback hazır

## 📦 Paketleme

### Python Core

#### Opsiyon 1: Standart Package
```bash
# Wheel oluştur
python setup.py bdist_wheel

# Kurulum
pip install dist/moonlight-1.0.0-py3-none-any.whl
```

#### Opsiyon 2: PyInstaller (Tek EXE)
```bash
# PyInstaller kur
pip install pyinstaller

# Spec dosyası ile build
pyinstaller packaging/moonlight.spec

# Çıktı: dist/moonlight.exe
```

### Flutter UI

#### Windows Desktop
```bash
cd ui_app

# Release build
flutter build windows --release

# Çıktı: build/windows/runner/Release/
```

#### MSIX Package (Microsoft Store)
```bash
# MSIX config
flutter pub run msix:create

# Çıktı: build/windows/runner/Release/*.msix
```

## 🔧 Windows Service Kurulumu

### NSSM ile (Non-Sucking Service Manager)

```powershell
# 1. NSSM indir: https://nssm.cc/download

# 2. Service oluştur
nssm install MoonLightCore "C:\MoonLight\venv\Scripts\python.exe" ^
  "-m moonlight.core.main --config C:\MoonLight\configs\app.yaml"

# 3. Çalışma dizini ayarla
nssm set MoonLightCore AppDirectory "C:\MoonLight"

# 4. Başlangıç tipini ayarla
nssm set MoonLightCore Start SERVICE_AUTO_START

# 5. Başlat
nssm start MoonLightCore

# 6. Durum kontrol
nssm status MoonLightCore
```

### Servis Yönetimi

```powershell
# Durdur
nssm stop MoonLightCore

# Yeniden başlat
nssm restart MoonLightCore

# Kaldır
nssm remove MoonLightCore confirm
```

## 🗂️ Dizin Yapısı (Production)

```
C:\MoonLight\                    # Ana klasör
├─ venv\                         # Virtual environment
├─ moonlight\                    # Kod
│  ├─ core\
│  └─ ui_app\
├─ configs\
│  ├─ app.yaml                   # Ana config (GİZLİ!)
│  └─ app.example.yaml
├─ data\
│  └─ trades.db                  # SQLite (GİZLİ!)
├─ logs\
│  └─ moonlight.log              # Loglar (PII maskeli)
├─ profiles\
│  ├─ acc1\                      # Hesap profilleri (GİZLİ!)
│  ├─ acc2\
│  ├─ acc3\
│  └─ acc4\
└─ backups\                      # Yedekler (ŞİFRELİ!)
```

## 🔐 Güvenlik Ayarları

### 1. Dosya İzinleri

```powershell
# Yalnız kullanıcı erişimi
icacls C:\MoonLight\configs /inheritance:r /grant:r "%USERNAME%:(OI)(CI)F"
icacls C:\MoonLight\data /inheritance:r /grant:r "%USERNAME%:(OI)(CI)F"
icacls C:\MoonLight\profiles /inheritance:r /grant:r "%USERNAME%:(OI)(CI)F"
```

### 2. Firewall Kuralı (Loopback)

Varsayılan olarak gerekmez (127.0.0.1). Remote erişim için:

```powershell
# İnbound rule (DİKKATLİ!)
New-NetFirewallRule -DisplayName "MoonLight API" -Direction Inbound `
  -LocalPort 8750,8751 -Protocol TCP -Action Allow -Profile Private
```

### 3. BitLocker (Disk Şifreleme)

```powershell
# BitLocker durumu
manage-bde -status C:

# Etkinleştir (Admin gerekli)
manage-bde -on C: -RecoveryPassword
```

## 📊 Monitoring Kurulumu

### Prometheus (Opsiyonel)

```yaml
# configs/app.yaml
telemetry:
  enabled: true
  prometheus_port: 9090
```

Prometheus config:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'moonlight'
    static_configs:
      - targets: ['127.0.0.1:9090']
```

### Grafana Dashboard (Opsiyonel)

1. Prometheus data source ekle
2. Dashboard import: `dashboards/moonlight.json`
3. Paneller:
   - Order rate
   - Win rate
   - Latency (p50/p90/p99)
   - Daily PnL
   - Guardrail triggers

## 🔄 Deployment Süreci

### Stage → Canary

```bash
# 1. Config hazırla
cp configs/app.stage.yaml configs/app.canary.yaml
vim configs/app.canary.yaml  # mode: live, tek hesap

# 2. Backup al
python -m moonlight.tools.backup --full

# 3. Deployment test
python -m moonlight.core.main --config configs/app.canary.yaml --no-workers

# 4. Smoke test
curl http://127.0.0.1:8750/status

# 5. Worker'ları başlat (dikkatli!)
# UI veya API üzerinden kademeli

# 6. İzleme (24-48 saat)
# Metrikler, alerts, daily reports
```

### Canary → Production

**Kabul Kriterleri:**
- [ ] Min. 1000 işlem
- [ ] Win rate ≥ hedef
- [ ] Max DD kontrol altında
- [ ] Guardrail testleri geçti
- [ ] No critical alerts
- [ ] Latency p90 < 2s

**Rollout:**
```bash
# Kademeli
# %10 → %25 → %50 → %100
# Her adımda 24h+ gözlem
```

## 🔙 Rollback Planı

### Hızlı Geri Alma

```powershell
# 1. Kill Switch
Invoke-WebRequest -Method POST -Uri http://127.0.0.1:8750/killswitch `
  -Body '{"open": true}' -ContentType "application/json"

# 2. Service durdur
nssm stop MoonLightCore

# 3. Config geri al
copy configs\app.yaml.backup configs\app.yaml

# 4. Database geri yükle (son yedek)
copy backups\trades_20251010.db data\trades.db

# 5. Service başlat
nssm start MoonLightCore

# 6. Doğrula
curl http://127.0.0.1:8750/status
```

## 💾 Yedekleme Stratejisi

### Otomatik Yedekleme

```powershell
# Windows Task Scheduler ile günlük yedek (03:00)
schtasks /create /tn "MoonLight Backup" /tr "C:\MoonLight\scripts\backup.bat" ^
  /sc daily /st 03:00 /ru SYSTEM
```

`scripts/backup.bat`:
```batch
@echo off
set BACKUP_DIR=C:\MoonLight\backups
set DATE=%date:~-4,4%%date:~-10,2%%date:~-7,2%

REM Database backup
copy C:\MoonLight\data\trades.db %BACKUP_DIR%\trades_%DATE%.db

REM Config backup
copy C:\MoonLight\configs\app.yaml %BACKUP_DIR%\config_%DATE%.yaml

REM Logs backup (compress)
powershell Compress-Archive -Path C:\MoonLight\logs\*.log ^
  -DestinationPath %BACKUP_DIR%\logs_%DATE%.zip

REM Cleanup (30 gün üstü sil)
forfiles /p %BACKUP_DIR% /m *.db /d -30 /c "cmd /c del @path"
```

### Manuel Yedek

```bash
python -m moonlight.tools.backup --output backups/manual_backup.zip
```

## 📈 Performance Tuning

### Düşük Kaynak Modu

```yaml
engine:
  tick_interval_ms: 500       # 250 → 500
  queue_maxsize: 1000         # 2000 → 1000

limits:
  max_parallel_global: 4      # Azalt
  max_parallel_per_account: 1

telemetry:
  snapshot_interval_sec: 60   # 30 → 60
```

### Yüksek Performans Modu

```yaml
engine:
  tick_interval_ms: 100       # Daha sık
  queue_maxsize: 5000         # Daha büyük

# Daha fazla paralellik (dikkatli!)
limits:
  max_parallel_global: 12
  max_parallel_per_account: 3
```

## 🔍 Health Checks

### Automated Health Check Script

```powershell
# scripts/health_check.ps1
$API = "http://127.0.0.1:8750"

# Status check
$status = Invoke-RestMethod -Uri "$API/status"
if ($status.service.state -ne "running") {
    Write-Error "Service not running!"
    exit 1
}

# Workers check
$workers = Invoke-RestMethod -Uri "$API/workers"
if ($workers.Count -eq 0) {
    Write-Warning "No active workers"
}

# Metrics check
$metrics = Invoke-RestMethod -Uri "$API/metrics"
Write-Host "Daily PnL: $($metrics.global.pnl_day)"
Write-Host "Open Orders: $($metrics.global.open_orders)"

Write-Host "✓ Health check passed"
```

### Cron (Görev Zamanlayıcı)

```powershell
# Her 5 dakikada health check
schtasks /create /tn "MoonLight Health" /tr "powershell C:\MoonLight\scripts\health_check.ps1" ^
  /sc minute /mo 5
```

## 🆘 Disaster Recovery

### Tam Sistem Kaybı

1. **Yedeklerden Geri Yükle**
   ```bash
   # Son config
   copy backups\config_latest.yaml configs\app.yaml
   
   # Son database
   copy backups\trades_latest.db data\trades.db
   ```

2. **Kimlik Bilgilerini Yeniden Gir**
   ```python
   import keyring
   keyring.set_password("moonlight-olymp", "user@mail.com", "password")
   ```

3. **Doğrulama**
   ```bash
   python quick_test.py
   ```

4. **Kademeli Başlat**
   - Önce paper mode
   - Sonra canary (tek hesap)
   - Son olarak production

## 📞 Support Contacts

### Kritik Sorun (SEV-1)
- ⚠️ Kill switch aktif et
- 📦 Destek paketi oluştur
- 📞 Operasyon ekibine bildir

### Rutin Destek
- 📧 support@moonlight.local
- 📚 Dokümantasyon: `/docs`
- 🐛 Issues: GitHub (eğer public)

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] Config reviewed and validated
- [ ] Secrets stored in keyring
- [ ] Backup taken
- [ ] Tests passed (pytest)
- [ ] Health check script ready
- [ ] Rollback plan documented

### Deployment
- [ ] Service installed
- [ ] Smoke test passed
- [ ] API accessible
- [ ] Logs rotating
- [ ] Metrics collecting

### Post-Deployment
- [ ] 24h monitoring
- [ ] Daily reports
- [ ] Alert validation
- [ ] Performance tuning
- [ ] User training

---

**MoonLight v1.0.0** - Production-ready deployment framework.

For questions: deployment@moonlight.local
