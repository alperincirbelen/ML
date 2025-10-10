# 3. Yüksek Seviyeli Mimari (Windows Servis + 4 Hesap + UI)

## 3.1 Mimari Katmanlar

### 3.1.1 UI (Flutter / Windows masaüstü)
- **Ekranlar**: Dashboard, İşlem Menüsü, Gelişmiş Ayarlar, Strateji Kataloğu, Grafik Paneli, Loglar
- **İletişim**: localhost üstünden REST + WebSocket (loopback, opsiyonel TLS)
- **Rol**: Ayarları düzenler, başlat/durdur komutları, anlık metrik/günlükleri gösterir

### 3.1.2 Core Engine (Python / asyncio, Windows Service)
- **Scheduler**: Hesap×Ürün×TF için worker oluşturma/yaşam döngüsü
- **Workers**: Sinyal → guardrails → emir akışı (Her worker anahtarı = (account, product, timeframe))
- **Strategy Engine (plugin)**: Signal provider'lar (ID kataloğu)
- **Ensemble & Confidence**: Ağırlıklandırma + eşiğe göre karar
- **Risk Manager**: Lot/tutar, permit, guardrails, cool down
- **Order Executor**: Idempotent emir, retry/abort, latency ölçümü
- **Connector(s)**: Olymp Trade izinli uçlarıyla HTTP/WS
- **Storage**: SQLite (orders, results, features, metrics, configs) + CSV/Parquet
- **Telemetry**: Metrikler, structured log, alarm üretimi

### 3.1.3 Profil/Account İzolasyonu
- profiles/accX/ → cookie/token kasası, session ayarları, config override, DB sorgularında account_id filtresi

## 3.2 Veri & Denetim Akışı

```
UI --(REST: /config, /start, /stop, /accounts, /workers, /orders)--→ Core
UI ←────────────(WS: metrics, logs, trade_updates, alerts)────────── Core
Core ↔ Connector (HTTP/WS): login, candles, quotes/payout, place/confirm order
Core → Storage: orders/results/features/metrics (WAL + indeks)
```

## 3.3 Süreç Yaşam Döngüsü

### A) Servis başlatma
1. Config yükle → JSON şema doğrula → keyring'den parolaları çek
2. Hesap profilleri aç → Connector login() (gerekirse OTP)
3. Scheduler, aktif (hesap×ürün×TF) için worker'ları ayağa kaldırır
4. UI bağlanır; /status ve /metrics akışı başlar

### B) Worker döngüsü (her (acc, prod, tf))
1. **Veri Çek**: get_candles(n) (+ varsa quote/payout)
2. **Feature Hesapla**: İndikatörler/kanallar/volatilite/hacim
3. **Sinyal**: Aktif stratejilerden oy/skor al
4. **Ensemble**: Kombine et → confidence∈[0,1]
5. **Guardrails**: permit penceresi, win threshold, concurrency, cool down, limitler
6. **Emir** (şart sağlanırsa): place_order() → confirm_order(); latency ölç
7. **Kayıt & Yayın**: orders/results/features yaz; metrik/log/olayları WS ile UI'a gönder

### C) Hot reload
- config.json değişirse güvenli alanlar anında uygulanır
- Kapsamlı değişimde etkilenen worker'lar kontrollü yeniden başlatılır

## 3.4 Eşzamanlılık, Kilitleme ve Performans

- **asyncio tabanlı işleyiş**: Her hesap için bağımsız worker havuzu
- **Concurrency kuralı**: Aynı (hesap, ürün, TF) için tek açık işlem (re-entrancy lock)
- **Kuyruklar**: asyncio.Queue ile sinyal/emir/telemetry back pressure yönetimi
- **Rate limit/Retry**: Connector seviyesinde throttling, exponential backoff + jitter
- **Zamanlama**: TF=1 için ~250ms tik; TF=5/15 mum kapanışına hizalı
- **Hedef kapasite**: 100–300+ aktif anahtar; CPU <%70 (donanıma bağlı); IO beklemelerinde bloklamasız

## 3.5 UI ↔ Core API Taslağı (Loopback)

### REST (örnek)
- `GET /status` → servis, hesap, worker özetleri
- `GET /accounts` → bağlı hesaplar/profiller
- `POST /start` / `POST /stop` → global veya scoped (hesap/ürün/TF)
- `GET /workers` → aktif (acc, prod, tf) listesi
- `POST /orders/cancel` → (platform destekliyorsa) erken kapatma isteği
- `GET /logs?level=INFO&tail=500` → son loglar
- `PUT /config` → doğrulama + atomik devreye alma (sadece güvenli alanlar)

### WebSocket (kanallar)
- **metrics** (win rate, PnL, DD, latency, rvol, adx vb.)
- **trade_updates** (NEW/SETTLED/ABORT)
- **alerts** (guardrail tetik, kill switch, bağlantı)
- **logs** (system/trade, redakte edilmiş)

## 3.6 Modül ve Dizin Yapısı (özet)

```
moonlight/
├─ core/
│ ├─ api/ (REST/WS loopback server)
│ ├─ connector/ (olymp interface + mock)
│ ├─ indicators/ (basic, advanced, states)
│ ├─ strategies/ (plugin providers)
│ ├─ ensemble.py
│ ├─ risk.py
│ ├─ worker.py
│ ├─ scheduler.py
│ ├─ storage.py
│ ├─ telemetry.py
│ └─ main.py (service bootstrap)
├─ ui_app/ (Flutter desktop)
│ ├─ lib/screens, widgets, theme, services
├─ data/ (trades.db, ml_dataset.csv)
├─ docs/ (config.schema.json, examples)
└─ tests/
```

## 3.7 Durum Makineleri (özet)

- **Order FSM**: IDLE → PREPARE → SEND → (RETRY?) → CONFIRM → (SETTLED | ABORT)
- **Worker FSM**: INIT → RUNNING → (RELOAD?) → STOPPING → STOPPED
- **Connector FSM**: DISCONNECTED → AUTHENTICATING → CONNECTED → (REAUTH/RECONNECT)

## 3.8 Güvenlik/İzolasyon Bağlantıları

- UI yalnız loopback dinler; dış ağdan görünmez
- Her hesap için ayrı cookie/token ve oturum; DB'de account_id zorunludur
- Keyring/DPAPI'de parolalar; loglarda PII maskelenir

## 3.9 Performans Bütçeleri & Telemetry

- **Emir round trip hedefi**: <2s (ağa bağlı)
- **Worker döngüsü**: TF=1'de <1s işlem
- **Metrikler**: win rate (demo/gerçek ayrı), expectancy, DD, latency, error rate; WS ile anlık yayın

## 3.10 Kabul Kriterleri

- Katmanlar, akışlar, API taslağı, FSM'ler ve kilitleme stratejisi tanımlandı
- Performans hedefleri ve telemetry gereksinimleri belirlendi
- Windows servis + loopback UI topolojisi net
