# 🌙 MoonLight - Fixed-Time Trading AI

**Windows 10/11 için modüler, güvenli ve akıllı sabit zamanlı (Fixed Time) işlem yapay zekası**

## 🎯 Özellikler

- ✅ **4 Hesaba Kadar Eşzamanlı**: İzole profiller ile çoklu hesap desteği
- ✅ **Modüler Strateji Sistemi**: Plugin tabanlı, genişletilebilir
- ✅ **Güvenli ve Uyumlu**: DPAPI/Keyring, PII maskeleme, TOS uyumlu
- ✅ **Paper ve Live Mod**: Demo hesap ile test, kademeli gerçek hesap
- ✅ **Risk Yönetimi**: Günlük kayıp limiti, ardışık kayıp koruması, Kill-Switch
- ✅ **Ensemble AI**: Çoklu strateji birleştirme ve güven skoru
- ✅ **Gelişmiş İndikatörler**: 30+ teknik gösterge (EMA, RSI, MACD, ADX, Ichimoku, Supertrend...)
- ✅ **Telemetri ve İzleme**: JSON log, metrikler, WebSocket canlı akış

## 📋 Gereksinimler

- **İşletim Sistemi**: Windows 10/11 (64-bit)
- **Python**: 3.10 veya üzeri
- **Donanım**: 
  - CPU: 4C/8T (önerilen)
  - RAM: 8 GB (minimum), 16 GB (önerilen)
  - Disk: SSD, en az 10 GB boş alan

## 🚀 Hızlı Başlangıç

### 1. Kurulum

```bash
# Repository'yi klonla
git clone <repository-url>
cd moonlight

# Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate  # Windows

# Bağımlılıkları yükle
pip install -r requirements.txt
```

### 2. Konfigürasyon

```bash
# Örnek konfigürasyonu kopyala
copy configs\config.example.yaml configs\config.yaml

# config.yaml'ı düzenle (hesap bilgileri, ürünler, stratejiler)
notepad configs\config.yaml
```

**Önemli Ayarlar:**

- `features.paper_mode`: **true** (başlangıç için)
- `features.trade_enabled`: **false** (güvenlik - test sonrası açılır)
- `limits.max_parallel_global`: Test için **1-2** başlat
- `accounts`: Hesap bilgilerinizi girin

### 3. Veritabanı Başlatma

```bash
python -c "import asyncio; from moonlight.core.storage import init_database; asyncio.run(init_database('data/db/moonlight.db'))"
```

### 4. Çalıştırma

```bash
# Core engine'i başlat
python -m moonlight.core.main configs/config.yaml
```

API şu adreste çalışacak: `http://127.0.0.1:8750`

### 5. API Test

```bash
# Durum kontrolü
curl http://127.0.0.1:8750/status

# Hesaplar
curl http://127.0.0.1:8750/accounts

# Aktif worker'lar
curl http://127.0.0.1:8750/workers
```

## 📁 Proje Yapısı

```
moonlight/
├── core/                      # Ana motor
│   ├── api/                   # REST/WebSocket API
│   ├── config/                # Konfigürasyon yönetimi
│   ├── connector/             # Market bağlantıları (mock/olymp)
│   ├── ensemble/              # Ensemble ve kalibrasyon
│   ├── executor/              # Emir FSM ve yürütücü
│   ├── indicators/            # Teknik göstergeler
│   ├── risk/                  # Risk yönetimi ve guardrails
│   ├── storage/               # SQLite veritabanı
│   ├── strategies/            # Strateji plugin sistemi
│   ├── telemetry/             # Loglama ve metrikler
│   ├── worker/                # Worker ve scheduler
│   └── main.py                # Ana giriş noktası
├── configs/                   # Konfigürasyon dosyaları
├── data/                      # Veri depolama
│   ├── db/                    # SQLite veritabanı
│   ├── logs/                  # Log dosyaları
│   ├── profiles/              # Hesap profilleri
│   └── backups/               # Yedekler
├── docs/                      # Dokümantasyon
├── tests/                     # Test dosyaları
└── requirements.txt           # Python bağımlılıkları
```

## 🛡️ Güvenlik İlkeleri

1. **Sırlar**: Windows Credential Manager/DPAPI ile şifreli
2. **PII**: Log ve metriklerde maskeleme
3. **Erişim**: Yalnız localhost (127.0.0.1)
4. **Uyumluluk**: Sadece izinli/resmî API uçları
5. **Fail-Closed**: Şüphede dur, emir verme

## ⚙️ Modüller

### Connector (Bağlayıcı)
- `MockConnector`: Test ve paper trading
- `OlympConnector`: (Geliştirilecek) Resmî API entegrasyonu

### Indicators (Göstergeler)
- **Temel**: SMA, EMA, WMA, HMA, RSI, MACD, Bollinger, ATR, Stochastic
- **İleri**: ADX, Supertrend, Ichimoku, Keltner, Donchian, VWAP, RVOL, CMF

### Risk Management
- Günlük kayıp limiti
- Ardışık kayıp koruması
- Pozisyon boyutlandırma (Fixed, Fraction, Kelly-lite)
- Kill-Switch ve Circuit Breaker

### Strategies (Stratejiler)
- Plugin sistemi ile genişletilebilir
- Örnek: EMA+RSI, VWAP+RVOL, Supertrend+ADX, Keltner Break, Bollinger Walk

## 📊 Kullanım Senaryoları

### Paper Mode (Demo)
```yaml
features:
  paper_mode: true
  trade_enabled: false
  read_only: false

connector:
  type: mock  # Deterministik test verisi
```

### Live Mode (Gerçek - Dikkatli!)
```yaml
features:
  paper_mode: false
  trade_enabled: true  # Paper testleri geçtikten sonra
  read_only: false

connector:
  type: olymp  # Gerçek bağlantı
  base_url: "..."  # İzinli uçlar
```

## 🧪 Test

```bash
# Birim testleri
pytest tests/ -v

# Smoke test
python tests/smoke_test.py

# Coverage
pytest --cov=moonlight.core tests/
```

## 📈 Monitoring

### Metrikler
- `orders_total`: Toplam emir sayısı
- `orders_outcome_total{outcome}`: Win/lose dağılımı
- `order_latency_ms`: Gecikme istatistikleri
- `guard_reject_total{reason}`: Ret nedenleri

### Loglar
- `data/logs/moonlight.log`: Ana log (JSON format)
- PII maskeli, yapılandırılmış
- Otomatik rotasyon (10 MB, 7 dosya)

## ⚠️ Uyarılar

1. **TOS Uyumu**: Yalnız izinli API kullanın
2. **Demo Önce**: Paper modda en az 1000 işlem test edin
3. **Limitler**: Başlangıçta düşük paralellik ayarlayın
4. **Kill-Switch**: Her zaman hazır bulundurun
5. **Yedek**: Düzenli veritabanı yedeği alın

## 📚 Dokümantasyon

- **Parça 1-32**: Kapsamlı proje belgeleri (ML.docx)
- **API Referansı**: `http://127.0.0.1:8750/docs` (FastAPI otomatik)
- **Stratejiler**: `docs/strategies.md`
- **Runbook**: `docs/operations.md`

## 🔧 Geliştirme

### Yeni Strateji Ekleme

```python
# moonlight/core/strategies/providers/my_strategy.py

from ..base import ProviderConfig, ProviderContext
from ..registry import register
from ...ensemble.models import ProviderVote

@register(101)  # Benzersiz ID
class MyStrategy:
    META = {"name": "My Strategy", "group": "custom"}
    
    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg
    
    def warmup_bars(self) -> int:
        return 50
    
    def evaluate(self, df, feats, ctx):
        # Strateji mantığı
        return ProviderVote(pid=self.cfg.id, vote=1, score=0.8)
```

## 🆘 Destek

Sorunlar için:
1. `data/logs/` klasöründeki logları kontrol edin
2. `/api/metrics` endpoint'ini inceleyin
3. Kill-Switch ile sistemi durdurun
4. Konfigürasyonu gözden geçirin

## 📜 Lisans

Bu proje eğitim ve araştırma amaçlıdır.
Finansal işlemlerde kullanımdan doğan riskler kullanıcıya aittir.

## 🙏 Teşekkürler

MoonLight projesi, modern yazılım mimarisi ve finansal teknoloji en iyi uygulamalarını bir araya getirir.

---

**Önemli**: Bu yazılım yatırım tavsiyesi vermez. Tüm kararlar kullanıcı sorumluluğundadır.
Platform kurallarına ve yerel mevzuata uyum zorunludur.
