# 🏗️ MoonLight Architecture

## Sistem Mimarisi

MoonLight, katmanlı ve modüler bir mimari ile tasarlanmıştır.

```
┌─────────────────────────────────────────────────────┐
│                  UI (Flutter)                       │
│              REST / WebSocket                       │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│                 API Layer                           │
│         FastAPI (REST + WebSocket)                  │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│              Core Engine (Python)                   │
│  ┌──────────┬──────────┬──────────┬──────────┐    │
│  │ Worker   │ Strategy │ Ensemble │   Risk   │    │
│  │Scheduler │ Plugins  │  Engine  │  Manager │    │
│  └──────────┴──────────┴──────────┴──────────┘    │
│  ┌──────────┬──────────┬──────────┬──────────┐    │
│  │   FSM    │Connector │ Storage  │Telemetry │    │
│  │ Executor │ Manager  │ (SQLite) │  Metrics │    │
│  └──────────┴──────────┴──────────┴──────────┘    │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│           External Services                         │
│    Market Data API  |  Order API (izinli)          │
└─────────────────────────────────────────────────────┘
```

## Veri Akışı

### 1. Karar Akışı (Decision Flow)

```
Scheduler → Worker → Connector.get_candles()
                  ↓
              Indicators (EMA, RSI, ADX...)
                  ↓
              Strategies (Plugins)
                  ↓
              Ensemble (Voting + Confidence)
                  ↓
              Risk Checks (Permit, Threshold, Guardrails)
                  ↓
              Executor (FSM) → Connector.place_order()
                  ↓
              Storage (Order + Result + Features)
```

### 2. Durum Akışı (State Flow)

```
IDLE → PREPARE → SEND → CONFIRM → SETTLED
         ↓         ↓        ↓         ↓
      Guards   Retry    Poll     Store
         ↓         ↓        ↓         ↓
      FAILED   FAILED   FAILED   METRICS
```

## Modüller

### Config
- **Sorumluluk**: Konfigürasyon yükleme ve doğrulama
- **Teknoloji**: Pydantic, YAML
- **Fail-Closed**: Geçersiz config → sistem başlamaz

### Storage
- **Sorumluluk**: Kalıcı veri yönetimi
- **Teknoloji**: SQLite + WAL mode
- **Tablolar**: orders, results, features, metrics, instrument_cache

### Connector
- **Sorumluluk**: Market veri ve emir köprüsü
- **Tipler**: MockConnector (test), OlympConnector (gerçek)
- **Güvenlik**: Sadece izinli API uçları

### Indicators
- **Sorumluluk**: Teknik analiz hesaplamaları
- **Teknoloji**: Pandas, NumPy
- **30+ Gösterge**: EMA, RSI, MACD, Bollinger, ADX, Ichimoku, Supertrend...

### Strategies
- **Sorumluluk**: Sinyal üretimi
- **Mimari**: Plugin sistemi (Registry pattern)
- **Örnekler**: EMA+RSI, VWAP+RVOL, Supertrend+ADX

### Ensemble
- **Sorumluluk**: Çoklu sinyal birleştirme
- **Algoritma**: Ağırlıklı oylama + Platt kalibrasyon
- **Çıktı**: Skor (S), Güven, Olasılık (p̂), Yön

### Risk
- **Sorumluluk**: Pozisyon boyutu ve koruma
- **Politikalar**: Fixed, Fraction, Kelly-lite
- **Guardrails**: Daily loss cap, consecutive loss, Kill-Switch, Circuit Breaker

### Executor
- **Sorumluluk**: Emir yürütme (FSM)
- **İdempotency**: client_req_id ile tekrar koruması
- **Durumlar**: PREPARE → SEND → CONFIRM → SETTLED/FAILED

### Worker
- **Sorumluluk**: Her (account, product, tf) için döngü
- **Zamanlama**: TF hizalama, bar kapanış tetikleme
- **İzolasyon**: Hesap bazlı, paralel çalışma

### Scheduler
- **Sorumluluk**: Worker yaşam döngüsü
- **Politika**: DRR (Deficit Round Robin) adil paylaşım
- **Kapasite**: 4 hesap × N ürün × 3 TF

### Telemetry
- **Sorumluluk**: Loglama ve metrikler
- **Format**: JSON log (PII maskeli)
- **Metrikler**: Counters, Gauges, Histograms

### API
- **Sorumluluk**: UI/dış kontrol arayüzü
- **Protokol**: REST + WebSocket
- **Güvenlik**: Yalnız localhost, CSRF koruması

## Güvenlik Katmanları

1. **Kimlik**: DPAPI/Keyring - parola şifreleme
2. **Ağ**: Localhost only (127.0.0.1)
3. **Veri**: PII maskeleme, log redaksiyonu
4. **Emir**: Idempotency, guardrails
5. **Operasyon**: Kill-Switch, Circuit Breaker

## Performans Hedefleri

- **Indicator hesap**: p90 < 10 ms / 200 bar
- **Strategy eval**: p90 < 5 ms
- **API /status**: p90 < 300 ms (mock), < 800 ms (live)
- **Order total latency**: p90 < 2000 ms

## Ölçeklenebilirlik

- **Hesaplar**: 1-4 (Windows tek makine)
- **Ürünler**: 5-20 (önerilen)
- **Worker'lar**: 4 acc × 10 prod × 3 tf = 120 (maksimum yük)
- **CPU**: < %40 ortalama, < %80 pik

## Veri Modeli

### Orders
- Emir açıldığında kaydedilir
- Idempotency: `client_req_id UNIQUE`
- Durum: PENDING → OPEN → SETTLED

### Results
- Emir kapandığında kaydedilir
- Outcome: win | lose | push | abort
- PnL ve latency bilgileri

### Features
- İşlem anındaki indikatör değerleri
- ML training için kullanılır
- Esnek JSON alanı (extras)

### Metrics
- Zaman serisi metrikler
- 30 sn snapshot'lar
- Scope: global | acc | prod | tf

## Konfigürasyon Yönetimi

### Öncelik Sırası
1. Runtime overrides (ops)
2. Environment variables
3. config.yaml
4. Defaults (kod içi)

### Hot-Reload
- ❌ **Varsayılan**: Kapalı (restart gerekir)
- ✅ **İleride**: Güvenli alanlar için hot-reload

### Validation
- Şema: Pydantic
- Semantik: Aralık kontrolleri (permit_min ≤ permit_max)
- Güvenlik: Sırlar config'te yok

## Dağıtım

### Development
```bash
python -m moonlight.core.main configs/config.yaml
```

### Production (Windows Service)
- PyInstaller ile EXE
- NSSM ile Windows Service
- Otomatik yeniden başlatma

## Monitoring

### Loglar
- **Konum**: `data/logs/moonlight.log`
- **Format**: JSON (structured)
- **Rotasyon**: 10 MB, 7 dosya
- **Seviyeler**: DEBUG | INFO | WARN | ERROR

### Metrikler
- `orders_total`: Toplam emirler
- `guard_reject_total{reason}`: Ret nedenleri
- `order_latency_ms`: Gecikme dağılımı
- `pnl_day{account}`: Günlük PnL

### Alarmlar
- **Kritik**: Kill-Switch, CB trip, Daily loss cap
- **Uyarı**: Latency yüksek, Permit dışı, 429 fırtınası
- **Bilgi**: Config değişimi, Worker start/stop

## Test Stratejisi

### Unit Tests
- Indicators: Doğruluk, warm-up, NaN handling
- Risk: Limit kontrolü, sizing
- FSM: State transitions, retry

### Integration Tests
- Connector + Storage
- Strategy + Ensemble
- Worker + Scheduler

### E2E Tests
- Config → Worker → Order → Result
- Paper mode tam akış
- Guardrails senaryoları

### Chaos Tests
- 429/5xx fırtınası
- Bağlantı kesilmesi
- Yüksek gecikme
- Disk dolu

## Sonraki Adımlar

1. ✅ Core modülleri (tamamlandı)
2. 🔄 UI (Flutter - Windows desktop)
3. 🔄 Advanced strategies (daha fazla plugin)
4. 🔄 ML integration (PyTorch - opsiyonel)
5. 🔄 Windows Service packaging
6. 🔄 Auto-update mechanism

---

**Not**: Bu mimari, 30+ parçalık kapsamlı proje belgesine (ML.docx) dayanır.
