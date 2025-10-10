# MoonLight - Mimari Genel Bakış

## 🏗️ Yüksek Seviyeli Mimari

```
┌─────────────────────────────────────────────────────────────┐
│                     Flutter Desktop UI                       │
│                    (Windows 10/11)                          │
└──────────────────┬──────────────────────────────────────────┘
                   │ REST/WebSocket (Loopback 127.0.0.1)
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                  FastAPI Server                             │
│              (Loopback API Layer)                           │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                   Core Engine                               │
│                 (Python asyncio)                            │
│                                                             │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐               │
│  │  Scheduler │→ │  Worker  │→ │ Executor │               │
│  └────────────┘  └──────────┘  └──────────┘               │
│         │              │              │                     │
│  ┌──────▼──────┐ ┌────▼────┐  ┌──────▼─────┐              │
│  │ Strategies  │ │Ensemble │  │    Risk    │              │
│  │  (Plugin)   │ │& Calib. │  │ Guardrails │              │
│  └─────────────┘ └─────────┘  └────────────┘              │
│                                                             │
│  ┌─────────────────────────────────────────┐               │
│  │         Storage (SQLite WAL)            │               │
│  │  orders | results | metrics | catalog  │               │
│  └─────────────────────────────────────────┘               │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│                  Connector Layer                            │
│           mock (test) | olymp (izinli API)                  │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Modüler Yapı

### Core Engine (Python)
- **Scheduler**: Worker yaşam döngüsü yönetimi
- **Worker**: Her (account, product, TF) için izole işlem döngüsü
- **Strategies**: Plugin sistemi ile genişletilebilir strateji kataloğu
- **Ensemble**: Çoklu strateji oylama ve güven skoru
- **Risk**: Guardrails, limitler, cool-down
- **Executor**: İdempotent emir akışı (FSM)
- **Storage**: SQLite ile append-only kayıt
- **Telemetry**: Metrik ve yapılandırılmış log

### Connector
- **Interface**: Protokol tanımı (type-safe)
- **Mock**: Test ve paper trading
- **Olymp**: Gerçek API (yalnız izinli uçlar)

### API Layer
- **REST**: Durum, kontrol, sorgu endpoint'leri
- **WebSocket**: Canlı metrik, işlem güncellemeleri, uyarılar

### UI (Flutter)
- **Dashboard**: KPI'lar, canlı akış, grafikler
- **Accounts**: Çoklu hesap yönetimi
- **Products**: Ürün/TF konfigürasyonu
- **Strategies**: Katalog, parametre override
- **Settings**: Risk, limit, telemetri ayarları

## 🔄 Veri Akışı

### Karar Akışı
```
1. Worker tetiklenir (TF kapanışı)
   ↓
2. Connector'dan candles + payout
   ↓
3. Indicators hesaplanır
   ↓
4. Strategies değerlendirilir → Votes
   ↓
5. Ensemble birleştirir → S, confidence, p_hat
   ↓
6. Router kontrol eder:
   - Permit penceresi (payout)
   - Win threshold (p_hat)
   - Risk guardrails
   ↓
7. Decision: order | hold | skip
   ↓
8. Executor (eğer order):
   PREPARE → SEND → CONFIRM → SETTLED
   ↓
9. Storage: orders + results
   ↓
10. Telemetry: metrics + logs
```

### Kontrol Akışı
```
UI → POST /start → Scheduler → Worker(s)
UI → POST /killswitch → Global flag → All workers pause
UI ← WS /ws ← Telemetry ← Workers/Executor
```

## 🔐 Güvenlik Katmanları

1. **Secrets**: Windows DPAPI/Keyring
2. **API**: Loopback-only (127.0.0.1)
3. **PII**: Otomatik maskeleme (log/telemetry)
4. **Audit**: Tüm kararlar iz bırakır
5. **Fail-closed**: Şüphede emir yok

## 🎯 Concurrency Model

### İzolasyon Seviyeleri
- **Hesap**: Ayrı oturum, token, rate-limit bucket
- **Ürün**: Farklı ürünler paralel çalışabilir
- **TF**: 1/5/15 dk bağımsız worker'lar
- **Kısıt**: Aynı (account, product, TF) için tek açık işlem

### Paralellik
```
max_parallel_global: Tüm hesaplarda toplam
max_parallel_per_account: Hesap başına limit
rate_limit_per_min: Dakikalık istek kotası
```

## 📊 Veri Modeli

### SQLite Tables
- **orders**: Emir kayıtları (idempotent, client_req_id UNIQUE)
- **results**: Sonuçlar (order_id FK)
- **features**: İndikatör snapshot'ları
- **metrics**: Zaman serisi metrikler
- **instrument_cache**: Payout cache (TTL)
- **config_audit**: Konfig değişiklik izleri

### Views
- **v_trades**: orders ⋈ results (UI için)

## 🚦 Guardrails (Koruma Bariyerleri)

1. **Kill Switch**: Master OFF anahtarı
2. **Circuit Breaker**: Ardışık kayıplarda otomatik durdurma
3. **Daily Loss Cap**: Günlük maksimum kayıp
4. **Concurrency**: (acc, prod, TF) başına tek işlem
5. **Permit Window**: Payout aralığı kontrolü
6. **Cool-down**: Kayıp sonrası bekleme
7. **Latency Guard**: Yüksek gecikmede iptal

## 📈 Karar Mekanizması

### Ensemble Voting
```python
S = tanh(Σ w_i * vote_i * score_i)
confidence = |S|
p_hat = sigmoid(a*S + b)  # Platt calibration
```

### Threshold Logic
```python
w* = 1 / (1 + payout_ratio)  # Break-even
win_needed = max(win_threshold, w* + margin)

if p_hat >= win_needed:
    decision = "order"
else:
    decision = "hold"
```

## 🧪 Test Katmanları

1. **Unit**: Indicators, strategies, risk, FSM
2. **Integration**: Mock connector + full pipeline
3. **E2E**: API + UI akışları
4. **Paper**: Canlı veri, simüle işlemler
5. **Backtest**: Tarihsel veri, walk-forward

## 📡 Telemetri

### Metrik Türleri
- **Counter**: orders_total, errors_total
- **Gauge**: pnl_day, open_orders
- **Histogram**: latency_ms (p50/p90/p99)

### Log Channels
- **trade**: İşlem olayları
- **system**: Servis durumu
- **security**: Kimlik, OTP (maskeli)
- **connector**: API çağrıları

## 🎨 UI Tema

### Renk Paleti
- **Primary**: #6D28D9 (Mor)
- **Accent**: #2563EB (Mavi)
- **Success**: #10B981 (Yeşil)
- **Danger**: #EF4444 (Kırmızı)
- **Dark BG**: #0B0F17 (Siyah)

### Durum Renkleri
- **Win**: Yeşil
- **Lose**: Kırmızı
- **Pause**: Amber
- **Running**: Mavi

## 🔧 Konfigurasyon Hiyerarşisi

```
Global (app.yaml)
  ↓
Account overrides
  ↓
Product overrides
  ↓
Timeframe overrides
  ↓
Runtime (hot-reload)
```

## 🛡️ Uyumluluk

### İlkeler
✅ Yalnız izinli/resmî API'ler
✅ Kullanıcı kendi hesapları
✅ 2FA/OTP kullanıcı manuel girer
✅ Platform TOS'a uyum
✅ PII maskeleme ve veri koruma

### Yasaklar
❌ Anti-bot atlatma
❌ 2FA bypass
❌ Scraping/RPA
❌ Yetkisiz hesap erişimi
❌ Rate-limit aşımı zorlaması

## 📚 Parça Haritası

Bu mimari, 32 parçalık detaylı plana dayanır:

- **Parça 1-4**: Kapsam, mimari, konfig, kimlik
- **Parça 5-12**: Connector, storage, FSM, risk, strateji, worker
- **Parça 13-18**: Telemetry, UI, çoklu hesap, sizing
- **Parça 19-24**: Versiyonlama, ops, runbook, alarm
- **Parça 25-32**: Güvenlik, go-live, kalibrasyon, destek

---

**MoonLight v1.0.0** - Modüler, güvenli, uyumlu fixed-time trading AI.
