-- MoonLight Database Schema
-- Parça 5, 6, 22 - SQLite DDL
-- Version: 1.0.0

-- Hesaplar (accounts) - kullanıcı kimliği maskeli
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    username_mask TEXT,
    profile_path TEXT,
    state TEXT CHECK(state IN ('connected', 'disconnected', 'otp_required')),
    last_login_ms INTEGER,
    balance REAL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_accounts_state ON accounts(state);

-- Ürünler (products)
CREATE TABLE IF NOT EXISTS products (
    symbol TEXT PRIMARY KEY,
    kind TEXT DEFAULT 'forex'  -- forex|crypto|metal|stock|index
);

-- Emirler (orders) - FTT giriş kaydı
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    ts_open_ms INTEGER NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    product TEXT NOT NULL REFERENCES products(symbol) ON DELETE RESTRICT,
    timeframe INTEGER NOT NULL CHECK(timeframe IN (1, 5, 15)),
    direction TEXT NOT NULL CHECK(direction IN ('call', 'put')),
    amount REAL NOT NULL,
    payout_pct REAL,
    client_req_id TEXT NOT NULL UNIQUE,  -- Idempotency
    permit_win_min REAL,
    permit_win_max REAL,
    status TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'OPEN', 'SETTLED', 'FAILED')),
    extras_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_acc_time ON orders(account_id, ts_open_ms DESC);
CREATE INDEX IF NOT EXISTS idx_orders_prod_tf ON orders(product, timeframe, ts_open_ms DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_client_req ON orders(client_req_id);

-- Sonuçlar (results) - FTT sonuç
CREATE TABLE IF NOT EXISTS results (
    order_id TEXT PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
    ts_close_ms INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('win', 'lose', 'push', 'abort', 'canceled')),
    pnl REAL NOT NULL,
    duration_ms INTEGER,
    latency_ms INTEGER,
    extras_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_results_status ON results(status);
CREATE INDEX IF NOT EXISTS idx_results_ts ON results(ts_close_ms DESC);

-- Özellikler (features) - işlem anındaki indikatörler
CREATE TABLE IF NOT EXISTS features (
    order_id TEXT PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    timeframe INTEGER NOT NULL,
    -- Temel indikatörler
    ema9 REAL, ema21 REAL, rsi14 REAL, macd_hist REAL,
    boll_width REAL, atr14 REAL, obv REAL, mfi14 REAL,
    adx14 REAL, cmf REAL, vwap_dist REAL,
    stoch_k REAL, stoch_d REAL,
    -- İleri indikatörler
    ichimoku_state TEXT, supertrend_state TEXT,
    extras_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_features_acc_tf ON features(account_id, timeframe);

-- İşlem atlamaları (trade_skips) - neden bazlı
CREATE TABLE IF NOT EXISTS trade_skips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_ms INTEGER NOT NULL,
    account_id TEXT,
    product TEXT,
    timeframe INTEGER,
    reason TEXT NOT NULL,  -- permit|confidence|concurrency|risk_guard|overrun|latency_guard
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_skips_ts ON trade_skips(ts_ms DESC);
CREATE INDEX IF NOT EXISTS idx_skips_reason ON trade_skips(reason);

-- Metrikler - ham veri
CREATE TABLE IF NOT EXISTS metrics_raw (
    ts_ms INTEGER NOT NULL,
    scope TEXT NOT NULL,  -- global|acc:<id>|prod:<symbol>|tf:<n>
    key TEXT NOT NULL,
    value REAL NOT NULL,
    PRIMARY KEY(ts_ms, scope, key)
);

CREATE INDEX IF NOT EXISTS idx_metrics_scope ON metrics_raw(scope, key, ts_ms DESC);

-- Metrikler - 5 dakikalık rollup
CREATE TABLE IF NOT EXISTS metrics_rollup_5m (
    bucket_ms INTEGER NOT NULL,
    scope TEXT NOT NULL,
    key TEXT NOT NULL,
    cnt INTEGER NOT NULL,
    avg REAL,
    p50 REAL,
    p90 REAL,
    p99 REAL,
    min REAL,
    max REAL,
    PRIMARY KEY(bucket_ms, scope, key)
);

CREATE INDEX IF NOT EXISTS idx_metrics5_scope ON metrics_rollup_5m(scope, key, bucket_ms DESC);

-- Strateji performansı
CREATE TABLE IF NOT EXISTS strategy_perf (
    strategy_id INTEGER NOT NULL,
    account_id TEXT NOT NULL,
    product TEXT NOT NULL,
    timeframe INTEGER NOT NULL,
    window_n INTEGER NOT NULL,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    updated_ms INTEGER NOT NULL,
    PRIMARY KEY(strategy_id, account_id, product, timeframe, window_n)
);

-- Ensemble kalibrasyonu
CREATE TABLE IF NOT EXISTS ensemble_calibration (
    scope TEXT PRIMARY KEY,  -- acc:prod:tf
    a REAL NOT NULL,
    b REAL NOT NULL,
    ece REAL,
    brier REAL,
    updated_ms INTEGER
);

-- Konfig değişiklik izleri (audit)
CREATE TABLE IF NOT EXISTS config_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_ms INTEGER NOT NULL,
    actor TEXT,
    scope TEXT,
    patch_json TEXT NOT NULL,
    comment TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_ts ON config_audit(ts_ms DESC);

-- Ürün/Payout önbelleği (catalog)
CREATE TABLE IF NOT EXISTS instrument_cache (
    symbol TEXT PRIMARY KEY,
    kind TEXT,
    payout REAL,
    updated_at INTEGER
);

-- Kritik olaylar indeksi
CREATE TABLE IF NOT EXISTS trade_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_ms INTEGER NOT NULL,
    level TEXT CHECK(level IN ('INFO', 'WARN', 'ERROR')),
    chan TEXT,  -- trade|system|security|connector|worker|api
    event TEXT,
    account TEXT,
    product TEXT,
    timeframe INTEGER,
    order_id TEXT,
    message TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON trade_events(ts_ms DESC);
CREATE INDEX IF NOT EXISTS idx_events_event ON trade_events(event);

-- Şema migrasyonları
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_ms INTEGER NOT NULL
);

-- Görünümler (Views) - kolay raporlama için
CREATE VIEW IF NOT EXISTS v_trades AS
SELECT 
    o.id,
    o.ts_open_ms,
    o.account_id,
    o.product,
    o.timeframe,
    o.direction,
    o.amount,
    o.payout_pct,
    o.client_req_id,
    r.ts_close_ms,
    r.status,
    r.pnl,
    r.duration_ms,
    r.latency_ms
FROM orders o
LEFT JOIN results r ON r.order_id = o.id;

-- Günlük PnL görünümü
CREATE VIEW IF NOT EXISTS v_daily_pnl AS
SELECT 
    account_id,
    DATE(ts_close_ms / 1000, 'unixepoch') as trade_date,
    COUNT(*) as trade_count,
    SUM(CASE WHEN status = 'win' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN status = 'lose' THEN 1 ELSE 0 END) as losses,
    SUM(pnl) as total_pnl,
    AVG(pnl) as avg_pnl
FROM v_trades
WHERE status IN ('win', 'lose')
GROUP BY account_id, DATE(ts_close_ms / 1000, 'unixepoch');
