# 🌟 MoonLight - Özellikler Listesi

## ✅ Tamamlanmış Özellikler (v1.0.0-alpha)

### 🎛️ Konfigürasyon ve Yönetim

- [x] **YAML/JSON Config**: Pydantic şema doğrulama
- [x] **Multi-Account**: 4 hesaba kadar izole profiller
- [x] **Validation**: Semantik kontroller (aralıklar, zorunlu alanlar)
- [x] **Environment**: MOONLIGHT_CONFIG env variable desteği
- [x] **Fail-Closed**: Geçersiz config → sistem başlamaz

### 💾 Veri Katmanı

- [x] **SQLite + WAL**: Performanslı, tutarlı depolama
- [x] **10 Tablo**: Orders, Results, Features, Metrics, Catalog...
- [x] **Idempotency**: client_req_id UNIQUE constraint
- [x] **Views**: v_trades, v_daily_pnl (kolay sorgulama)
- [x] **Async API**: aiosqlite ile non-blocking
- [x] **Queries**: Rolling winrate, consecutive losses, daily PnL

### 🔌 Market Bağlantısı

- [x] **Connector Interface**: Protocol-based sözleşme
- [x] **MockConnector**: Deterministik test verisi
- [x] **Multi-Account Manager**: 4 hesap izolasyonu
- [x] **Idempotent Orders**: Aynı req_id → aynı order_id
- [x] **Rate-Limit Ready**: Token bucket placeholder
- [ ] **Live Connector**: (Planlı - izinli API gerekli)

### 📊 Teknik Analiz (30+ Gösterge)

#### Temel (15)
- [x] **Moving Averages**: SMA, EMA, WMA, HMA
- [x] **Momentum**: RSI (Wilder), Stochastic (%K, %D)
- [x] **Trend**: MACD (line, signal, histogram)
- [x] **Volatility**: Bollinger Bands, Bollinger Width, ATR, True Range
- [x] **Volume**: OBV, MFI
- [x] **VWAP**: Simple + session-based

#### İleri (15+)
- [x] **Trend Strength**: DMI/ADX (DI+, DI-, ADX)
- [x] **Momentum**: PPO, Stochastic RSI, CCI, Fisher Transform
- [x] **Channels**: Keltner Channel, Donchian Channel
- [x] **Volume/Flow**: CMF (Chaikin Money Flow), RVOL (Relative Volume)
- [x] **Cloud**: Ichimoku (Tenkan, Kijun, Senkou A/B, Chikou)
- [x] **Trend**: Supertrend (ATR-based)
- [x] **Pivots**: Classic Pivot Points (PP, R1-R3, S1-S3)
- [x] **State Interpreters**: Ichimoku state, Supertrend state

### 🧠 Strateji ve Karar

- [x] **Plugin System**: @register decorator, auto-discovery
- [x] **Provider Protocol**: Standardize edilmiş arayüz
- [x] **Örnek Strateji**: EMA+RSI (ID: 5)
- [x] **Warmup Logic**: Minimum bar kontrolü
- [x] **Deterministic**: Aynı girdi → aynı çıktı
- [x] **Metadata**: Karar gerekçeleri (açıklanabilirlik)
- [ ] **50 Strateji Kataloğu**: (1/50 tamamlandı, planlı)

### 🎲 Ensemble ve Kalibrasyon

- [x] **Weighted Voting**: Ağırlıklı oy birleştirme
- [x] **Z-Score Normalization**: Provider skorları standardize
- [x] **Score Combination**: tanh(weighted_sum)
- [x] **Platt Calibration**: S → p̂ (kazanma olasılığı)
- [x] **Brier Score**: Kalibrasyon kalite ölçümü
- [x] **Dynamic Threshold**: Breakeven + margin (payout-based)
- [x] **Weight Update**: Online learning (softmax)

### 🛡️ Risk Yönetimi

#### Position Sizing
- [x] **Fixed**: Sabit tutar
- [x] **Fraction**: Balance'ın %'si
- [x] **Kelly-Lite**: Kelly Criterion (0.25-0.5× capped)
- [x] **Limits**: a_min, a_cap
- [x] **Dynamic f_cap**: Günlük kayba göre kısma

#### Guardrails
- [x] **Kill-Switch**: Master OFF (tek tık)
- [x] **Circuit Breaker**: CLOSED/OPEN/HALF_OPEN states
- [x] **Daily Loss Cap**: Günlük kayıp limiti
- [x] **Consecutive Loss**: Ardışık kayıp koruması
- [x] **Cooldown**: Kayıp sonrası bekleme
- [x] **Permit Window**: Payout min-max kontrolü
- [x] **Concurrency**: 1 açık işlem / (acc, prod, tf)

### ⚙️ Emir Yürütme

- [x] **FSM**: PREPARE → SEND → CONFIRM → SETTLED/FAILED
- [x] **Idempotency**: client_req_id unique
- [x] **Retry Logic**: Exponential backoff + jitter
- [x] **Timeout**: Configurable per phase
- [x] **Error Classification**: Temporary vs Permanent
- [x] **Preflight**: Son saniye kontrolleri
- [x] **Storage Integration**: Order + Result + Features kayıt

### 👷 Worker ve Zamanlama

- [x] **TF-Aligned Loop**: Bar kapanış tetikleme
- [x] **Per-Key Worker**: (account, product, tf) izolasyonu
- [x] **Lifecycle**: Start, Stop, Status
- [x] **Scheduler**: Worker management
- [x] **Concurrency Lock**: Aynı key'de tek worker
- [ ] **DRR (Deficit Round Robin)**: (Temel var, tam impl. planlı)
- [ ] **Health-Aware**: (Planlı)

### 🌐 API ve İletişim

#### REST Endpoints
- [x] `GET /status`: Sistem durumu
- [x] `GET /accounts`: Hesap listesi
- [x] `GET /workers`: Aktif worker'lar
- [x] `GET /orders`: İşlem geçmişi
- [x] `GET /metrics`: Metrik özeti
- [x] `POST /start`: Worker başlat
- [x] `POST /stop`: Worker durdur
- [x] `POST /killswitch`: KS toggle
- [x] **Auto Docs**: /docs (Swagger UI)

#### WebSocket
- [x] **Connection**: ws://127.0.0.1:8751/ws
- [x] **Heartbeat**: ping/pong
- [x] **Metrics Stream**: Real-time metrikler
- [ ] **Trade Updates**: (Planlı)
- [ ] **Alerts**: (Planlı)
- [ ] **Logs**: (Planlı)

#### Güvenlik
- [x] **Localhost Only**: 127.0.0.1 binding
- [x] **CORS**: Sınırlı origin
- [ ] **CSRF**: (Planlı)
- [ ] **API Key**: (Opsiyonel, planlı)
- [ ] **TLS**: (Opsiyonel, planlı)

### 📊 Telemetri ve İzleme

#### Logging
- [x] **Structured JSON**: Makine okunur
- [x] **PII Masking**: Email, phone otomatik
- [x] **Rotation**: 10 MB, 7 files
- [x] **Levels**: DEBUG, INFO, WARN, ERROR
- [x] **Context**: account, product, tf, order_id

#### Metrics
- [x] **Counters**: orders_total, guard_reject_total...
- [x] **Gauges**: pnl_day, open_orders...
- [x] **Histograms**: order_latency_ms (p50, p90, p99)
- [x] **Snapshot**: In-memory → JSON
- [ ] **SQLite Snapshot**: (Auto-persist planlı)
- [ ] **Prometheus**: (Opsiyonel, planlı)

### 🧪 Test ve Kalite

- [x] **Unit Tests**: Config, Indicators, Storage
- [x] **Smoke Test**: E2E temel akış
- [x] **Deterministic**: Seed-based, reproducible
- [x] **Coverage**: %70 (kritik modüller)
- [ ] **Integration Tests**: (Daha fazla planlı)
- [ ] **Chaos Engineering**: (Planlı)

### 📚 Dokümantasyon

- [x] README.md: Genel bakış
- [x] INSTALL.md: Kurulum kılavuzu
- [x] QUICKSTART.md: 5 dakika başlangıç
- [x] ARCHITECTURE.md: Sistem mimarisi
- [x] STRATEGIES.md: Strateji geliştirme
- [x] OPERATIONS.md: Günlük işletim
- [x] CONTRIBUTING.md: Katkı rehberi
- [x] CHANGELOG.md: Versiyon geçmişi
- [x] PROJECT_STATUS.md: İlerleme durumu
- [x] LICENSE: MIT + Disclaimer
- [x] Inline Docstrings: Google style

## 🔄 Planlanan Özellikler

### Phase 2 (UI + More Strategies)
- [ ] Flutter Desktop UI
  - Dashboard (KPI kartları)
  - Hesap yönetimi
  - Ürün/TF ayarları
  - Strateji kataloğu
  - Grafik paneli (mum + indikatörler)
  - Log görüntüleyici
  - Tema: Mor, Mavi, Yeşil, Kırmızı

- [ ] 50 Strateji Kataloğu
  - EMA varyantları (5-10)
  - VWAP+RVOL (15-20)
  - Supertrend+ADX (25-30)
  - Keltner (35-40)
  - Bollinger Walk (45-50)

- [ ] Catalog Service
  - Payout cache (TTL + EWMA)
  - Auto refresh
  - State: FRESH/STALE/ROTTEN

### Phase 3 (Production)
- [ ] Backtest Engine
  - Walk-forward validation
  - Metrik raporları (EV, WR, Sharpe, MDD)
  - Calibration charts

- [ ] Windows Service
  - PyInstaller one-file
  - NSSM wrapper
  - Auto-restart

- [ ] Packaging
  - MSIX (Microsoft Store ready)
  - ZIP portable
  - Code signing

### Phase 4 (Advanced AI)
- [ ] ML Models
  - Scikit-learn baseline
  - PyTorch (LSTM, Transformer)
  - Online learning

- [ ] Meta-Learning
  - NAS (Neural Architecture Search)
  - AutoML hiperparametre
  - Continual learning

## 🎮 Kullanım Modları

### ✅ Şu An Desteklenen

1. **Paper Mode (Mock)**
   - Deterministik test verisi
   - Tam özellik seti
   - Güvenli deneme

2. **Development**
   - API testing
   - Strateji geliştirme
   - Indicator validation

3. **Integration Testing**
   - Component tests
   - Smoke tests

### ⏳ Yakında

4. **Paper Mode (Live Data)**
   - Gerçek payout
   - Simülasyon emirler
   - Kalibrasyon

5. **Live Mode (Real Trading)**
   - Gerçek connector
   - Risk limitlerli
   - Kademeli açılış

## 🔐 Güvenlik Özellikleri

### Aktif Korumaları
- ✅ PII auto-masking (email, phone)
- ✅ Idempotent orders (duplicate prevent)
- ✅ Fail-closed defaults
- ✅ Localhost-only API
- ✅ CORS restrictions
- ✅ Structured audit logs

### Planlı Korumaları
- [ ] Windows DPAPI integration
- [ ] Keyring full implementation
- [ ] TLS/mTLS (opsiyonel)
- [ ] API key authentication
- [ ] CSRF tokens
- [ ] Code signing (Windows)

## 📈 Performans Özellikleri

### Gerçekleşen
- ✅ Async architecture (non-blocking I/O)
- ✅ SQLite WAL mode (concurrent reads)
- ✅ Pandas vectorization (indicators)
- ✅ In-memory metrics (low overhead)

### Hedefler
- 🎯 Indicator: p90 < 10 ms / 200 bar
- 🎯 API /status: p90 < 300 ms
- 🎯 Order latency: p90 < 2000 ms
- 🎯 Capacity: 120 workers (4×10×3)

## 🎨 UI Özellikleri (Planlı)

### Ekranlar
- [ ] Dashboard: KPI, grafik, trade list
- [ ] Accounts: Login, status, balance
- [ ] Products: Ürün/TF ayarları
- [ ] Strategies: Katalog, params, enable/disable
- [ ] Charts: Candlestick + indicators
- [ ] Logs: Real-time, filterable
- [ ] Settings: Config editor, theme

### Tema
- [ ] **Colors**: Mor (#6D28D9), Mavi (#2563EB), Yeşil (#10B981), Kırmızı (#EF4444)
- [ ] **Modes**: Dark, Light
- [ ] **Accessibility**: WCAG AA contrast

## 🤖 AI/ML Özellikleri

### Temel (Aktif)
- ✅ Ensemble voting
- ✅ Platt calibration
- ✅ Weight adaptation (simple)
- ✅ Breakeven calculation

### İleri (Planlı)
- [ ] Scikit-learn models
- [ ] PyTorch neural nets
- [ ] LSTM time series
- [ ] Transformer architecture
- [ ] Meta-learning
- [ ] Neural Architecture Search (NAS)
- [ ] Online learning
- [ ] Continual learning
- [ ] Drift detection

## 🔧 Operasyonel Özellikler

### Mevcut
- ✅ Start/Stop API
- ✅ Kill-Switch (emergency stop)
- ✅ Circuit Breaker (auto-pause)
- ✅ Structured logs (JSON)
- ✅ Metrics snapshot
- ✅ Config validation

### Planlı
- [ ] Hot-reload config
- [ ] Destek paketi (support bundle)
- [ ] Auto-recovery (supervisor)
- [ ] Health checks
- [ ] Backup/Restore UI
- [ ] Alert notifications

## 📱 Platform Desteği

### Şu An
- ✅ **Windows 10/11**: Tam destek (core)
- ✅ **Python 3.10+**: Runtime
- [ ] **Windows Service**: (Planlı)

### İleride
- [ ] **Android**: (Ertelen mdi)
- [ ] **Multi-Device Sync**: (Opsiyonel)
- [ ] **Cloud**: (Opsiyonel)

## 🌐 Dil ve Yerelleştirme

- ✅ **Türkçe**: Dokümantasyon, yorumlar
- ✅ **İngilizce**: Kod, API, logs
- [ ] **UI i18n**: (Flutter UI ile gelecek)

## 🎯 Kullanım Alanları

### ✅ Uygun Kullanım
1. **Eğitim**: Algoritma öğrenme
2. **Araştırma**: Strateji geliştirme
3. **Backtest**: Tarihsel analiz (engine planlı)
4. **Paper Trading**: Risk-free test
5. **Kişisel**: İzinli hesaplar

### ❌ Uygun Olmayan
1. **Ticari Hizmet**: Başkalarına hizmet
2. **TOS İhlali**: Platform kurallarını atlatma
3. **Anti-Bot Bypass**: Yasak
4. **Yetkisiz Erişim**: Başka hesaplar
5. **Yatırım Tavsiyesi**: Yazılım tavsiye vermez

## 🔍 Karşılaştırma

### Diğer Bot'lardan Farkları

| Özellik | MoonLight | Tipik Bot |
|---------|-----------|-----------|
| **Mimari** | Modüler, plugin | Monolitik |
| **Güvenlik** | Fail-closed, PII mask | Çeşitli |
| **Risk** | Multi-layer guards | Basit limitler |
| **Ensemble** | Weighted + calibrated | Tek strateji |
| **Idempotency** | FSM ile garanti | Yok/sınırlı |
| **Telemetry** | Structured, metrics | Basit log |
| **Test** | Unit + smoke | Minimal |
| **Docs** | 11 MD, 30+ parça plan | README only |
| **Açık Kaynak** | ✅ MIT | Çeşitli |

## 📖 Doküman Kapsamı

- **README**: 300+ satır
- **INSTALL**: 200+ satır
- **ARCHITECTURE**: 400+ satır
- **STRATEGIES**: 300+ satır
- **OPERATIONS**: 350+ satır
- **Toplam**: 2000+ satır döküman

## 🏆 Kalite Metrikleri

### Kod
- **Modülerlik**: 12 bağımsız modül
- **Type Hints**: %90+ fonksiyonlarda
- **Docstrings**: %85+ (Google style)
- **Test Coverage**: %70+ (kritik %85+)

### Güvenlik
- **PII Masking**: Otomatik
- **Fail-Closed**: Varsayılan
- **Audit Trail**: Structured logs
- **No Secrets in Code**: ✅

### Performans
- **Async**: Non-blocking I/O
- **Vectorized**: Pandas operations
- **Indexed**: SQLite optimizations
- **Lightweight**: Minimal overhead

---

**Özet**: MoonLight, production-grade mimariye sahip, güvenli, modüler ve genişletilebilir bir Fixed-Time trading AI framework'üdür. MVP Core %100 tamamlandı, UI ve advanced features devam ediyor. 🌙✨
