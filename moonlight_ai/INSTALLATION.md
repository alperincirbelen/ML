# MoonLight AI - Kurulum Rehberi

## Sistem Gereksinimleri

### Minimum Gereksinimler
- **İşletim Sistemi**: Windows 10/11, Linux, macOS
- **Python**: 3.9 veya üzeri
- **RAM**: 4 GB (8 GB önerilir)
- **Disk Alanı**: 1 GB boş alan
- **İnternet**: Stabil internet bağlantısı

### Önerilen Gereksinimler
- **İşletim Sistemi**: Windows 11, Ubuntu 20.04+
- **Python**: 3.11+
- **RAM**: 8 GB veya üzeri
- **Disk Alanı**: 5 GB boş alan
- **CPU**: 4 çekirdek veya üzeri

## Kurulum Adımları

### 1. Python Kurulumu

#### Windows
1. [Python.org](https://python.org) adresinden Python 3.11+ indirin
2. Kurulum sırasında "Add Python to PATH" seçeneğini işaretleyin
3. Kurulumu tamamlayın

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv
```

#### macOS
```bash
# Homebrew ile
brew install python@3.11

# Veya Python.org'dan indirin
```

### 2. Proje İndirme

```bash
# Git ile klonlama (önerilir)
git clone https://github.com/your-repo/moonlight-ai.git
cd moonlight-ai

# Veya ZIP olarak indirip çıkarın
```

### 3. Sanal Ortam Oluşturma

```bash
# Sanal ortam oluştur
python -m venv moonlight_env

# Sanal ortamı aktifleştir
# Windows:
moonlight_env\Scripts\activate

# Linux/macOS:
source moonlight_env/bin/activate
```

### 4. Bağımlılıkları Yükleme

```bash
# Gerekli paketleri yükle
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Konfigürasyon

```bash
# Konfigürasyon dosyasını kopyala
cp config/config.yaml.example config/config.yaml

# Konfigürasyonu düzenle (isteğe bağlı)
nano config/config.yaml  # Linux/macOS
notepad config/config.yaml  # Windows
```

### 6. Veritabanı Kurulumu

```bash
# Veritabanı dizinini oluştur
mkdir -p data

# İlk çalıştırmada otomatik olarak oluşturulacak
```

## Konfigürasyon

### Temel Ayarlar

`config/config.yaml` dosyasındaki önemli ayarlar:

```yaml
# Sistem Ayarları
system:
  environment: "development"  # development, testing, production
  debug: true
  log_level: "INFO"

# API Ayarları
api:
  host: "localhost"
  port: 8000
  ssl_enabled: false

# WebSocket Ayarları
websocket:
  host: "localhost"
  port: 8001

# Güvenlik Ayarları
security:
  jwt_secret_key: "your-secret-key-change-this"
  encryption_key: "your-encryption-key-change-this"

# Risk Yönetimi
risk_management:
  max_daily_loss: 100.0
  max_position_size: 10.0
  max_concurrent_trades: 3
```

### Güvenlik Ayarları

**ÖNEMLİ**: Üretim ortamında mutlaka değiştirin:

```yaml
security:
  jwt_secret_key: "güçlü-rastgele-anahtar-buraya"
  encryption_key: "32-karakter-base64-anahtar"
  max_login_attempts: 5
  lockout_duration: 300
```

## İlk Çalıştırma

### 1. Sunucu Modu

```bash
# Ana sunucuyu başlat
python run_server.py

# Veya doğrudan
python main.py --mode server
```

Sunucu başlatıldıktan sonra:
- API: http://localhost:8000
- WebSocket: ws://localhost:8001
- Dokümantasyon: http://localhost:8000/docs

### 2. Demo Modu

```bash
# Demo modunu başlat
python run_demo.py

# Veya doğrudan
python main.py --mode demo
```

### 3. İstemci

```bash
# CLI istemci
python run_client.py --mode cli

# GUI istemci
python run_client.py --mode gui
```

## Doğrulama

### 1. Sistem Durumu Kontrolü

```bash
# API durumu
curl http://localhost:8000/health

# Beklenen çıktı:
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "engine_state": "stopped"
}
```

### 2. Temel Örnek Çalıştırma

```bash
python examples/basic_usage.py
```

### 3. Log Kontrolü

```bash
# Log dosyalarını kontrol edin
tail -f logs/moonlight.log
```

## Sorun Giderme

### Yaygın Hatalar

#### 1. Port Kullanımda Hatası
```
OSError: [Errno 98] Address already in use
```

**Çözüm**:
```bash
# Portu kullanan işlemi bul
lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# İşlemi sonlandır veya farklı port kullan
python main.py --port 8001
```

#### 2. Modül Bulunamadı Hatası
```
ModuleNotFoundError: No module named 'aiohttp'
```

**Çözüm**:
```bash
# Sanal ortamın aktif olduğundan emin olun
pip install -r requirements.txt
```

#### 3. Veritabanı Hatası
```
sqlite3.OperationalError: database is locked
```

**Çözüm**:
```bash
# Veritabanı dosyasını sil ve yeniden oluştur
rm data/moonlight.db
# Uygulamayı yeniden başlat
```

#### 4. İzin Hatası (Linux/macOS)
```
PermissionError: [Errno 13] Permission denied
```

**Çözüm**:
```bash
# Dosya izinlerini düzelt
chmod +x run_server.py
chmod +x run_client.py

# Veya sudo kullanmayın, sanal ortam kullanın
```

### Log Seviyeleri

Sorun giderme için log seviyesini artırın:

```bash
python main.py --log-level DEBUG
```

### Performans Optimizasyonu

#### 1. Üretim Ayarları

```yaml
system:
  environment: "production"
  debug: false
  log_level: "WARNING"

database:
  backup_enabled: true
  backup_interval: 3600
```

#### 2. Sistem Kaynakları

```bash
# Sistem kaynaklarını izle
htop  # Linux
taskmgr  # Windows
```

## Güncelleme

```bash
# Git ile güncelleme
git pull origin main

# Bağımlılıkları güncelle
pip install -r requirements.txt --upgrade

# Veritabanı migrasyonu (gerekirse)
python -c "from core.persistence.data_manager import DataManager; import asyncio; asyncio.run(DataManager({}).maintenance())"
```

## Yedekleme

### Otomatik Yedekleme

Sistem otomatik olarak veritabanı yedekleri oluşturur:
- Konum: `data/moonlight.db.backup_YYYYMMDD_HHMMSS`
- Sıklık: Saatte bir (konfigürasyonla değiştirilebilir)

### Manuel Yedekleme

```bash
# Veritabanı yedeği
cp data/moonlight.db data/backup_$(date +%Y%m%d_%H%M%S).db

# Konfigürasyon yedeği
cp -r config config_backup_$(date +%Y%m%d_%H%M%S)

# Log yedeği
tar -czf logs_backup_$(date +%Y%m%d_%H%M%S).tar.gz logs/
```

## Kaldırma

```bash
# Sanal ortamı deaktive et
deactivate

# Proje dizinini sil
rm -rf moonlight-ai

# Sanal ortamı sil
rm -rf moonlight_env
```

## Destek

Sorunlar için:
1. Bu dokümantasyonu kontrol edin
2. Log dosyalarını inceleyin
3. GitHub Issues'da arama yapın
4. Yeni issue oluşturun

**Önemli Dosyalar**:
- Konfigürasyon: `config/config.yaml`
- Loglar: `logs/moonlight.log`
- Veritabanı: `data/moonlight.db`
- Yedekler: `data/moonlight.db.backup_*`