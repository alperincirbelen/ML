# MoonLight - Başlangıç Kılavuzu

## 🚀 Hızlı Başlangıç (10 Adım)

### 1. Sistem Gereksinimleri

- **İşletim Sistemi**: Windows 10/11 (64-bit)
- **Python**: 3.10 veya üstü
- **RAM**: Minimum 8 GB (Önerilen: 16 GB)
- **Disk**: SSD önerilir, en az 2 GB boş alan
- **İnternet**: API erişimi için gerekli

### 2. Kurulum

```bash
# 1. Repository'yi klonla veya ZIP indir
git clone <repo-url>
cd moonlight

# 2. Python bağımlılıklarını yükle
pip install -r requirements.txt

# 3. Konfigürasyonu hazırla
cp configs/app.example.yaml configs/app.yaml
```

### 3. İlk Konfigürasyon

`configs/app.yaml` dosyasını düzenleyin:

```yaml
# Mod: paper ile başlayın
mode: paper

# Bağlayıcı: mock ile test edin
connector: mock

# En az bir hesap tanımlayın
accounts:
  - id: acc1
    username: your.email@example.com
    profile_store: profiles/acc1/

# Bir ürün ve timeframe seçin
products:
  - product: EURUSD
    enabled: true
    strategies: [5, 14, 15]  # EMA+RSI, Crossover, VWAP
    timeframes:
      - tf: 1
        enabled: true
        win_threshold: 0.72
        permit_min: 89
        permit_max: 93
```

### 4. Veritabanını Başlat

```bash
python -c "import asyncio; from moonlight.core.storage import Storage; asyncio.run(Storage('data/trades.db').init())"
```

### 5. Core Engine'i Test Et

```bash
python -m moonlight.core.main --config configs/app.yaml --no-workers
```

Çıktıda şunları görmelisiniz:
```
✓ Config loaded: 1.0.0
  Mode: paper
  Connector: mock
  Accounts: 1
  Products: 1
```

### 6. Worker'ları Başlat

```bash
python -m moonlight.core.main --config configs/app.yaml
```

### 7. API Server'ı Başlat (ayrı terminal)

```bash
cd moonlight
python -m moonlight.core.api.server
```

API docs: http://127.0.0.1:8750/docs

### 8. Flutter UI'yi Başlat (ayrı terminal)

```bash
cd ui_app
flutter pub get
flutter run -d windows
```

### 9. Dashboard'u İncele

UI açıldığında:
- ✅ Dashboard'da KPI kartları
- ✅ Connection status (Core ve WS)
- ✅ Kill Switch butonu

### 10. İlk Paper Test

1. Dashboard → Aktif worker sayısını kontrol et
2. İşlemler sekmesine git
3. 5-10 dakika bekle
4. İşlem geçmişini incele

## 📊 Strateji Seçimi

### Mevcut Stratejiler

| ID | Ad | Kategori | Açıklama |
|----|-----|----------|----------|
| 5 | EMA+RSI | Hybrid | EMA9/21 trend + RSI7 momentum |
| 14 | EMA Crossover | Trend | EMA9/21 kesişim |
| 15 | VWAP+RVOL | Volume | VWAP reclaim + hacim |
| 25 | Supertrend+ADX | Hybrid | Supertrend yön + ADX güç |

### Strateji Parametreleri Override

```yaml
products:
  - product: EURUSD
    strategies: [5]  # Yalnız EMA+RSI
    timeframes:
      - tf: 1
        enabled: true
        # Strateji 5 için özel parametreler
        strategy_params:
          5:
            ema_fast: 12  # Varsayılan: 9
            ema_slow: 26  # Varsayılan: 21
            rsi_up: 60    # Varsayılan: 55
```

## 🛡️ Risk Ayarları

### Temel Koruma

```yaml
limits:
  max_daily_loss: 5.0           # Günlük max kayıp
  max_consecutive_losses: 5     # Ardışık kayıp limiti
  
risk:
  default_lot: 1.0              # Sabit tutar
```

### Gelişmiş Koruma

```yaml
engine:
  latency_abort_ms: 2500        # 2.5s üstü gecikmede iptal

catalog:
  permit_mode: prefer_cache     # Payout kontrolü
  margin: 0.02                  # Güvenlik payı (%2)
```

## 📈 İlk Backtest

```bash
python -m moonlight.core.backtest \
  --config configs/app.yaml \
  --product EURUSD \
  --tf 1 \
  --bars 1000
```

## 🔍 Log ve Metrik İnceleme

### Log Dosyası
```bash
# Son 100 satır
tail -n 100 logs/moonlight.log

# Hata arama
grep "ERROR" logs/moonlight.log
```

### Metrik Kontrolü
```bash
# API üzerinden
curl http://127.0.0.1:8750/metrics
```

## ⚙️ Sık Ayarlar

### Win Threshold Ayarlama

Düşük ise: Çok işlem ama kalite düşük
```yaml
win_threshold: 0.65  # %65
```

Yüksek ise: Az işlem ama kalite yüksek
```yaml
win_threshold: 0.75  # %75
```

### Permit Penceresi

Dar: Sadece yüksek payout'ta işlem
```yaml
permit_min: 90
permit_max: 93
```

Geniş: Daha çok fırsat
```yaml
permit_min: 85
permit_max: 95
```

## 🆘 Sorun Giderme

### "Hiç işlem açmıyor"

**Kontrol:**
1. Worker'lar çalışıyor mu? → GET /workers
2. Permit penceresi uygun mu? → GET /metrics, payout_pct
3. Win threshold çok yüksek mi? → Konfig
4. Kill Switch açık mı? → GET /status

### "Sürekli 'skip' oluyor"

**Sebep:** Genellikle permit_window veya below_threshold

**Çözüm:**
- Permit penceresini genişlet (±2-3 puan)
- Win threshold'u azalt (-0.02)

### "Gecikme yüksek"

**Kontrol:**
- Aktif worker sayısı → Azalt
- tick_interval_ms → Artır (250 → 500)
- Mock connector kullanıyor musunuz?

## 📚 Sonraki Adımlar

1. ✅ Paper modda 1-2 hafta test
2. ✅ Backtest raporlarını incele
3. ✅ Win rate ve expectancy doğrula
4. ✅ Kalibrasyon kontrolü (p_hat vs gerçek)
5. ⚠️ Live'a geçiş için kriterleri kontrol et:
   - Min. 1000 işlem
   - Win rate ≥ hedef
   - Max DD kontrol altında
   - Guardrails test edildi

## 🔗 Yararlı Linkler

- [Konfigurasyon Kılavuzu](configuration.md)
- [Strateji Geliştirme](strategy_development.md)
- [API Referansı](api_reference.md)
- [Güvenlik ve Uyumluluk](security_compliance.md)

---

**Önemli:** Live moda geçmeden önce mutlaka paper modda yeterli test yapın!
