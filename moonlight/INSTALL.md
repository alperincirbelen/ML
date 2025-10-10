# 💿 MoonLight Kurulum Kılavuzu

## Sistem Gereksinimleri

### Zorunlu
- **OS**: Windows 10 (64-bit) veya Windows 11
- **Python**: 3.10 veya üzeri
- **RAM**: En az 8 GB
- **Disk**: En az 10 GB boş SSD alanı
- **İnternet**: Stabil bağlantı

### Önerilen
- **CPU**: 4 çekirdek / 8 thread
- **RAM**: 16 GB
- **Disk**: 20 GB boş SSD
- **Ekran**: 1920x1080 (UI için)

## Adım Adım Kurulum

### 1. Python Kurulumu

```bash
# Python 3.10+ kontrol
python --version

# Yoksa indirin: https://www.python.org/downloads/
# ✅ "Add Python to PATH" seçeneğini işaretleyin
```

### 2. Proje İndirme

```bash
# Git ile
git clone https://github.com/yourusername/moonlight.git
cd moonlight

# Veya ZIP indir ve çıkart
```

### 3. Sanal Ortam (Virtual Environment)

```bash
# Oluştur
python -m venv venv

# Aktif et
venv\Scripts\activate

# Doğrula
where python
# Çıktı: ...\moonlight\venv\Scripts\python.exe
```

### 4. Bağımlılıkları Yükle

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Requirements yükle
pip install -r requirements.txt

# Doğrula
pip list | findstr moonlight
```

### 5. Klasörleri Oluştur

```bash
# Otomatik oluşur, elle de yapabilirsiniz
mkdir data\db
mkdir data\logs
mkdir data\backups
mkdir data\profiles\acc1
mkdir data\profiles\acc2
mkdir data\profiles\acc3
mkdir data\profiles\acc4
```

### 6. Konfigürasyon

```bash
# Örnek dosyayı kopyala
copy configs\config.example.yaml configs\config.yaml

# Düzenle
notepad configs\config.yaml
```

**Düzenlemeler:**

```yaml
# 1. Hesap bilgileri
accounts:
  - id: acc1
    username: senin_email@example.com  # Değiştir
    profile_store: data/profiles/acc1/

# 2. Güvenlik (başlangıç)
features:
  paper_mode: true        # Demo mod
  trade_enabled: false    # Henüz emir verme
  read_only: false

# 3. Connector
connector:
  type: mock  # İlk testler için mock

# 4. Limitler
limits:
  max_parallel_global: 1  # Başlangıç için 1
  max_parallel_per_account: 1
```

### 7. Veritabanı Başlat

```bash
python -c "import asyncio; from moonlight.core.storage import init_database; asyncio.run(init_database('data/db/moonlight.db'))"
```

Çıktı: "Database initialized" veya sessiz başarı.

### 8. Kimlik Bilgilerini Kaydet (Opsiyonel)

```python
# Python shell aç
python

>>> import keyring
>>> keyring.set_password("moonlight-olymp", "senin_email@example.com", "PAROLA")
>>> exit()
```

**Güvenlik**: Parolalar Windows Credential Manager'da şifreli saklanır.

### 9. İlk Çalıştırma

```bash
python -m moonlight.core.main configs/config.yaml
```

**Beklenen Çıktı:**
```
MoonLight Fixed-Time Trading AI başlatılıyor...
Konfigürasyon yükleniyor: configs/config.yaml
Veritabanı başlatılıyor...
Bileşenler başlatılıyor...
Stratejiler yükleniyor...
Yüklenen stratejiler: [5]
API başlatılıyor...
Server starting on 127.0.0.1:8750
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8750
```

### 10. Test

Yeni bir terminal:

```bash
# API test
curl http://127.0.0.1:8750/status

# Beklenen: {"api_version":"1.0", "service":{"state":"running",...}, ...}
```

### 11. Smoke Test

```bash
python tests/smoke_test.py
```

**Beklenen**: Tüm testler ✅ geçmeli.

## İleri Kurulum

### Windows Service Olarak (Opsiyonel)

```bash
# NSSM (Non-Sucking Service Manager) indir
# https://nssm.cc/download

# Service kur
nssm install MoonLightCore "C:\path\to\venv\Scripts\python.exe" "-m moonlight.core.main configs\config.yaml"

# Başlat
nssm start MoonLightCore

# Durum
nssm status MoonLightCore
```

### PyInstaller ile EXE (Opsiyonel)

```bash
# PyInstaller yükle
pip install pyinstaller

# EXE oluştur
pyinstaller --onefile --name moonlight moonlight/core/main.py

# Çalıştır
dist\moonlight.exe configs\config.yaml
```

## Sorun Giderme

### "ModuleNotFoundError"

```bash
# Virtual environment aktif mi kontrol et
where python

# Değilse aktif et
venv\Scripts\activate

# Requirements tekrar yükle
pip install -r requirements.txt
```

### "Database locked"

```bash
# Başka bir süreç kullanıyor olabilir
# Tüm Python süreçlerini kapat ve tekrar dene

# Veya WAL checkpoint
sqlite3 data\db\moonlight.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

### "Port already in use"

```yaml
# config.yaml'da port değiştir
ui:
  port: 8751  # 8750 yerine
```

### "Permission denied"

```bash
# Yönetici olarak çalıştır
# Veya klasör izinlerini kontrol et
icacls data /grant %username%:F /T
```

## Kaldırma

```bash
# 1. Servisi durdur (varsa)
nssm stop MoonLightCore
nssm remove MoonLightCore confirm

# 2. Virtual environment deaktif et
deactivate

# 3. Klasörü sil
cd ..
rmdir /S /Q moonlight

# 4. Credential Manager temizle (opsiyonel)
# Windows → Credential Manager → Generic Credentials
# "moonlight-olymp" girişlerini sil
```

## Destek

### Loglar
- `data/logs/moonlight.log`: Ana log
- Son 100 satır: `tail -n 100 data/logs/moonlight.log`

### Dokümantasyon
- `README.md`: Genel bakış
- `docs/ARCHITECTURE.md`: Mimari
- `docs/STRATEGIES.md`: Strateji kılavuzu
- `docs/OPERATIONS.md`: Bu dosya

### Community
- GitHub Issues: Hata raporları
- Discussions: Sorular ve tartışmalar

---

**Başarılar!** 🌙
