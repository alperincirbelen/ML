# MoonLight - Fixed Time İşlem AI

**MoonLight**, Windows 10/11 üzerinde çalışan, çoklu hesap destekli, modüler bir Fixed-Time (binary/turbo) işlem yapay zekâsı projesidir.

## 🎯 Özellikler

- ✅ **Çoklu Hesap**: Aynı anda 4 hesaba kadar eşzamanlı işlem desteği
- ✅ **Modüler Strateji Sistemi**: 50+ strateji ile esnek karar mekanizması
- ✅ **Risk Yönetimi**: Günlük kayıp limiti, ardışık kayıp kontrolü, circuit breaker
- ✅ **Paper & Live Mod**: Demo hesapta test, gerçek hesapta kademeli geçiş
- ✅ **Backtest Engine**: Tarihsel veri üzerinde detaylı performans analizi
- ✅ **Ensemble & Calibration**: Çoklu strateji oylama ve olasılık kalibrasyonu
- ✅ **Güvenli Kimlik Yönetimi**: Windows DPAPI/Keyring ile şifreli saklama
- ✅ **Telemetri & İzleme**: Yapılandırılmış JSON log ve metrik sistemi
- ✅ **Flutter Desktop UI**: Modern, tema destekli masaüstü arayüz

## 📋 Gereksinimler

- **OS**: Windows 10/11 (64-bit)
- **Python**: 3.10+
- **RAM**: Minimum 8 GB (Önerilen: 16 GB)
- **Disk**: SSD önerilir
- **Flutter**: 3.x (Desktop için)

## 🚀 Hızlı Başlangıç

### 1. Kurulum

```bash
# Python bağımlılıklarını yükle
pip install -r requirements.txt

# Veritabanını başlat
python -m moonlight.core.storage init
```

### 2. Konfigurasyon

```bash
# Örnek konfigürasyonu kopyala
cp configs/app.example.yaml configs/app.yaml

# Ayarları düzenle (hesaplar, ürünler, stratejiler)
notepad configs/app.yaml
```

### 3. Paper Modda Test

```bash
# Mock connector ile paper mod
python -m moonlight.core.main --config configs/app.yaml --mode paper
```

### 4. UI'yi Başlat

```bash
cd ui_app
flutter run -d windows
```

## 📁 Proje Yapısı

```
moonlight/
├─ core/               # Python çekirdek motor
│  ├─ api/            # REST/WebSocket API
│  ├─ connector/      # Olymp Trade bağlayıcı
│  ├─ indicators/     # Teknik göstergeler
│  ├─ strategies/     # Strateji eklentileri
│  ├─ ensemble.py     # Sinyal birleştirme
│  ├─ risk.py         # Risk yönetimi
│  ├─ worker.py       # İşlem worker'ları
│  ├─ storage.py      # Veri katmanı
│  └─ main.py         # Ana servis
├─ ui_app/            # Flutter masaüstü UI
├─ docs/              # Dokümantasyon
├─ configs/           # Yapılandırma dosyaları
├─ data/              # Veritabanı ve veriler
├─ logs/              # Log dosyaları
└─ tests/             # Test dosyaları
```

## ⚙️ Konfigurasyon

### Temel Ayarlar

```yaml
config_version: "1.0.0"
mode: paper  # paper | live
connector: mock  # mock | olymp

ensemble_threshold: 0.70
limits:
  max_parallel_global: null
  max_parallel_per_account: null
  max_daily_loss: 5
  max_consecutive_losses: 5

accounts:
  - id: acc1
    username: user1@mail.com
    profile_store: profiles/acc1/
```

### Strateji Seçimi

```yaml
products:
  - product: EURUSD
    enabled: true
    strategies: [5, 14, 15, 25]  # Strateji ID'leri
    timeframes:
      - tf: 1
        enabled: true
        win_threshold: 0.72
        permit_min: 89
        permit_max: 93
```

## 🛡️ Güvenlik

- ✅ Kimlik bilgileri Windows Credential Manager'da şifreli
- ✅ Loglarda PII maskeleme
- ✅ Loopback-only API (127.0.0.1)
- ✅ TLS desteği (opsiyonel)
- ✅ Audit trail ve değişiklik izleme

## 📊 Stratejiler

### Mevcut Strateji Aileleri

- **Trend**: EMA Crossover, Triple MA, GMMA, Supertrend+ADX
- **Mean Reversion**: Bollinger Walk, RSI Band
- **Breakout**: Keltner Break, Donchian Channel
- **Volume**: VWAP Reclaim, RVOL
- **Hybrid**: EMA+RSI, Supertrend+ADX

### Strateji Ekleme

```python
# core/strategies/providers/my_strategy.py
from core.strategies.base import StrategyProvider

@register(pid=101)
class MyStrategy(StrategyProvider):
    def evaluate(self, df, feats, ctx):
        # Sinyal mantığı
        return ProviderVote(pid=101, vote=1, score=0.75)
```

## 📈 Backtesting

```bash
# CLI ile backtest
python -m moonlight.backtest --config configs/app.yaml \
  --product EURUSD --tf 1 --from 2025-01-01 --to 2025-03-31
```

## 🎛️ Risk Yönetimi

### Koruma Bariyerleri

- **Kill Switch**: Tek tıkla tüm işlemleri durdur
- **Circuit Breaker**: Ardışık kayıplarda otomatik durma
- **Günlük Limit**: Maksimum günlük kayıp kontrolü
- **Concurrency**: Aynı (hesap, ürün, TF) için tek açık işlem
- **Permit Penceresi**: Payout aralığı dışında işlem yok

## 📡 API

### REST Endpoints

- `GET /status` - Sistem durumu
- `GET /accounts` - Hesap listesi
- `GET /workers` - Aktif worker'lar
- `POST /start` - Worker başlat
- `POST /stop` - Worker durdur
- `GET /orders` - İşlem geçmişi

### WebSocket Channels

- `metrics` - Canlı metrikler
- `trade_updates` - İşlem güncellemeleri
- `alerts` - Uyarılar
- `logs` - Sistem logları

## 🧪 Test

```bash
# Unit testler
pytest tests/unit/

# Integration testler
pytest tests/integration/

# E2E testler
pytest tests/e2e/
```

## 📝 Uyumluluk ve Etik

⚠️ **ÖNEMLİ**: Bu yazılım yalnızca izinli/resmî API'ler kullanır:
- ❌ Anti-bot atlatma YOK
- ❌ 2FA bypass YOK
- ❌ Scraping/RPA YOK
- ✅ Yalnız kendi hesaplarınıza erişim
- ✅ Platform TOS ve yerel mevzuata uyum kullanıcı sorumluluğundadır

## 🔧 Geliştirme

### Gerekli Araçlar

- Python 3.10+
- Flutter SDK 3.x
- SQLite3
- Git

### Geliştirme Modu

```bash
# Canlı reload ile çalıştır
python -m moonlight.core.main --dev --reload
```

## 📚 Dokümantasyon

- [Mimari Genel Bakış](docs/architecture.md)
- [Konfigurasyon Kılavuzu](docs/configuration.md)
- [Strateji Geliştirme](docs/strategy_development.md)
- [API Referansı](docs/api_reference.md)
- [Güvenlik ve Uyumluluk](docs/security_compliance.md)

## 📞 Destek

### Destek Paketi Oluşturma

```bash
# Otomatik destek paketi (log + metrik + konfig)
python -m moonlight.support pack --since 24h
```

## 📄 Lisans

Bu proje eğitim ve araştırma amaçlıdır. Platform kullanım şartları ve yerel mevzuata uyum kullanıcı sorumluluğundadır.

## 🎨 Renk Paleti

- **Mor (Primary)**: #6D28D9
- **Mavi (Accent)**: #2563EB
- **Yeşil (Success)**: #10B981
- **Kırmızı (Danger)**: #EF4444
- **Siyah (Dark BG)**: #0B0F17
- **Beyaz (Light BG)**: #FFFFFF

## 🏗️ Sürüm

**v1.0.0** - İlk MVP Sürümü
- Core engine (Python asyncio)
- Multi-account support (4 hesap)
- 50+ strateji kataloğu
- Paper & backtest modu
- Flutter Windows UI
- Risk yönetimi ve guardrails

---

**MoonLight** - Yapay zeka destekli, güvenli ve uyumlu fixed-time trading.
