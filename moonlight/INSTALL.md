# MoonLight - Kurulum Kılavuzu

## 📋 Sistem Gereksinimleri

### Minimum Gereksinimler
- **OS**: Windows 10 (64-bit) veya Windows 11
- **CPU**: 4 çekirdek (Intel i5 veya eşdeğeri)
- **RAM**: 8 GB
- **Disk**: 10 GB boş alan (SSD önerilir)
- **Python**: 3.10, 3.11 veya 3.12
- **Flutter**: 3.16+ (UI için)

### Önerilen Sistem
- **CPU**: 8 çekirdek (Intel i7/Ryzen 7)
- **RAM**: 16 GB
- **Disk**: 20 GB SSD
- **İnternet**: Kararlı bağlantı

## 🔧 Adım Adım Kurulum

### 1. Python Kurulumu

```bash
# Python 3.10+ yüklü mü kontrol et
python --version

# Yoksa: https://python.org adresinden indirin
# "Add Python to PATH" seçeneğini işaretleyin
```

### 2. MoonLight İndir

**Seçenek A: Git ile**
```bash
git clone https://github.com/your-org/moonlight.git
cd moonlight
```

**Seçenek B: ZIP ile**
1. Repository'den ZIP indir
2. Çıkart → `C:\MoonLight\`
3. CMD/PowerShell ile klasöre git

### 3. Virtual Environment (Önerilir)

```bash
# Virtual environment oluştur
python -m venv venv

# Aktif et
venv\Scripts\activate

# (venv) prefix görmelisiniz
```

### 4. Bağımlılıkları Yükle

```bash
# Python paketleri
pip install --upgrade pip
pip install -r requirements.txt
```

**Not:** `ta-lib` kurulumu için binary gerekebilir:
- İndir: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
- Kur: `pip install TA_Lib‑0.4.XX‑cpXX‑cpXXm‑win_amd64.whl`

### 5. Klasör Yapısını Oluştur

```bash
# Otomatik oluşturma
python -c "from pathlib import Path; [Path(p).mkdir(parents=True, exist_ok=True) for p in ['data', 'logs', 'profiles/acc1', 'profiles/acc2', 'profiles/acc3', 'profiles/acc4']]"
```

### 6. Konfigürasyon

```bash
# Örnek konfigürasyonu kopyala
copy configs\app.example.yaml configs\app.yaml

# Düzenle (Notepad veya VS Code)
notepad configs\app.yaml
```

**Minimum Değişiklikler:**
```yaml
accounts:
  - id: acc1
    username: your.email@example.com  # Değiştir
    profile_store: profiles/acc1/

mode: paper  # İlk test için paper modda kalın
connector: mock  # Mock ile başlayın
```

### 7. Veritabanı Başlatma

```bash
python -c "import asyncio; from moonlight.core.storage import Storage; asyncio.run(Storage('data/trades.db').init()); print('✓ Database initialized')"
```

Başarılı ise:
```
✓ Database initialized
```

### 8. İlk Çalıştırma Testi

```bash
python -m moonlight.core.main --config configs/app.yaml --no-workers
```

Beklenen çıktı:
```
============================================================
MoonLight - Fixed Time Trading AI
============================================================
Config: configs/app.yaml

✓ Config loaded: 1.0.0
  Mode: paper
  Connector: mock
  Accounts: 1
  Products: 1
✓ Database initialized
✓ Strategies loaded: 8
✓ Scheduler initialized
✓ MoonLight Engine ready
```

`Ctrl+C` ile durdurun.

### 9. Flutter UI Kurulumu (Opsiyonel)

```bash
cd ui_app

# Bağımlılıkları yükle
flutter pub get

# Windows masaüstü desteği kontrol
flutter doctor

# Çalıştır
flutter run -d windows
```

### 10. İlk Paper Test

```bash
# Ana klasörde
python run_paper.py --config configs/app.yaml --duration 10
```

10 dakika paper trading simülasyonu çalışacak.

## 🧪 Kurulum Doğrulama

### Test Paketi Çalıştır

```bash
pytest tests/ -v
```

Tüm testler geçmeli:
```
tests/test_config.py::test_load_example_config PASSED
tests/test_storage.py::test_save_order PASSED
tests/test_indicators.py::test_rsi_range PASSED
...
```

### API Test

```bash
# Ayrı terminalde API başlat
python -m moonlight.core.api.server

# Başka terminalde test
curl http://127.0.0.1:8750/status
```

JSON yanıt görmelisiniz.

## 🔒 Güvenlik Kurulumu

### 1. Kimlik Bilgileri (İlk Kullanım)

```python
# Python interaktif
import keyring

# Parola kaydet
keyring.set_password("moonlight-olymp", "your.email@example.com", "YourPassword")

# Doğrula
pw = keyring.get_password("moonlight-olymp", "your.email@example.com")
print("✓ Password stored securely" if pw else "✗ Failed")
```

### 2. Dosya İzinleri

```powershell
# Windows ACL (opsiyonel, gelişmiş)
icacls data /inheritance:r /grant:r "%USERNAME%:(OI)(CI)F"
icacls logs /inheritance:r /grant:r "%USERNAME%:(OI)(CI)F"
icacls profiles /inheritance:r /grant:r "%USERNAME%:(OI)(CI)F"
```

### 3. Firewall (Opsiyonel)

Loopback-only olduğu için genelde gerekmez. Remote erişim isterseniz:

```powershell
# İnbound rule (dikkatli kullanın!)
netsh advfirewall firewall add rule name="MoonLight API" dir=in action=allow protocol=TCP localport=8750
```

## 🐛 Sorun Giderme

### Sorun: "ModuleNotFoundError"

**Çözüm:**
```bash
# Virtual environment aktif mi?
venv\Scripts\activate

# Bağımlılıklar yüklü mü?
pip install -r requirements.txt
```

### Sorun: "Config validation failed"

**Çözüm:**
```bash
# YAML syntax kontrolü
python -c "import yaml; yaml.safe_load(open('configs/app.yaml'))"

# Şema doğrulama
python -c "from moonlight.core.config import load_config; load_config('configs/app.yaml')"
```

### Sorun: "Database locked"

**Çözüm:**
```bash
# Eski bağlantıları kapat
taskkill /F /IM python.exe

# WAL dosyalarını temizle
del data\trades.db-wal
del data\trades.db-shm
```

### Sorun: Flutter "Unable to locate Android SDK"

**Çözüm:**
UI yalnız Windows desktop için. Android kurulumu gerekmez:
```bash
flutter config --no-enable-android
flutter config --enable-windows-desktop
```

## 📦 Production Kurulumu (İleri)

### Windows Service Olarak Çalıştırma

```powershell
# NSSM (Non-Sucking Service Manager) ile
nssm install MoonLightCore "C:\MoonLight\venv\Scripts\python.exe" "-m moonlight.core.main --config C:\MoonLight\configs\app.yaml"

# Servisi başlat
nssm start MoonLightCore
```

### Otomatik Başlatma

```powershell
# Görev Zamanlayıcı ile sistem açılışında
schtasks /create /tn "MoonLight" /tr "C:\MoonLight\venv\Scripts\python.exe -m moonlight.core.main" /sc onstart /ru SYSTEM
```

## 🆘 Destek

### Log Dosyalarını İnceleyin
```bash
type logs\moonlight.log | findstr "ERROR"
```

### Destek Paketi Oluşturun
```bash
POST http://127.0.0.1:8750/api/support-pack
```

### Sık Karşılaşılan Hatalar

| Hata | Sebep | Çözüm |
|------|-------|-------|
| Import error | Bağımlılık eksik | `pip install -r requirements.txt` |
| Config error | Geçersiz YAML | Syntax kontrolü |
| DB locked | Çoklu süreç | Eski süreçleri kapat |
| Port kullanımda | 8750/8751 meşgul | Port değiştir veya süreci kapat |

---

## ✅ Kurulum Tamamlandı!

Başarılı kurulum sonrası:
- ✅ Python paketleri yüklü
- ✅ Konfig hazır ve doğrulanmış
- ✅ Veritabanı başlatılmış
- ✅ Testler geçiyor
- ✅ API erişilebilir
- ✅ (Opsiyonel) UI çalışıyor

**Sonraki adım:** [Başlangıç Kılavuzu](getting_started.md)

---

**Yardıma mı ihtiyacınız var?** Destek paketi oluşturun ve log dosyalarını inceleyin.
