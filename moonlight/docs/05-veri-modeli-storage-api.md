# 5. Veri Modeli (SQLite) & Storage API

## 5.1 Tasarım İlkeleri

- **Güvenilirlik**: At least once kayıt, idempotent upsert, çökme sonrası kurtarma (reconcile)
- **Performans**: WAL modu, uygun indeksler, toplu ekleme (batch), tek yazıcı prensibi
- **Esneklik**: Sabit kolonlar + extras_json ile şema esnekliği (SQLite JSON1)
- **İzole Profiller**: account_id alanı tüm tablolarda zorunlu; 4 hesap aynı DB'de şema ortak, veriler account_id ile ayrılır

## 5.2 SQLite Ayarları (Önerilen)

```sql
PRAGMA journal_mode=WAL;        -- daha iyi eşzamanlılık
PRAGMA synchronous=NORMAL;      -- WAL ile önerilir
PRAGMA foreign_keys=ON;         -- referans bütünlüğü
PRAGMA temp_store=MEMORY;       -- küçük temp'ler RAM'de
PRAGMA page_size=4096;          -- modern diskler için uygun
PRAGMA cache_size=-20000;       -- ~20MB sayfa önbelleği
```

## 5.3 Şema (DDL)

```sql
-- ORDERS: Emir verildiği anda yazılır
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    ts_open_ms INTEGER NOT NULL,
    account_id TEXT NOT NULL,
    product TEXT NOT NULL,
    timeframe INTEGER NOT NULL CHECK(timeframe IN (1,5,15)),
    direction TEXT NOT NULL CHECK(direction IN ('call','put')),
    amount REAL NOT NULL,
    client_req_id TEXT UNIQUE NOT NULL,
    permit_win_min REAL,
    permit_win_max REAL,
    extras_json TEXT
);

-- RESULTS: Emir kapandığında yazılır (1:1)
CREATE TABLE IF NOT EXISTS results (
    order_id TEXT PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
    ts_close_ms INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('win','lose','abort')),
    pnl REAL NOT NULL,
    duration_ms INTEGER,
    latency_ms INTEGER,
    extras_json TEXT
);

-- FEATURES: İşlem anındaki özellikler (sabit kolonlar + esnek JSON)
CREATE TABLE IF NOT EXISTS features (
    order_id TEXT PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    timeframe INTEGER NOT NULL,
    ema9 REAL,
    ema21 REAL,
    rsi14 REAL,
    macd_hist REAL,
    boll_width REAL,
    atr14 REAL,
    obv REAL,
    mfi14 REAL,
    adx14 REAL,
    cmf REAL,
    vwap_dist REAL,
    stoch_k REAL,
    stoch_d REAL,
    ichimoku_state TEXT,
    supertrend_state TEXT,
    extras_json TEXT
);

-- METRICS: Zaman içinde izlenen değerler (winrate, DD, latency, vb.)
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,  -- global / acc:<id> / prod:<symbol> / tf:<n>
    key TEXT NOT NULL,
    value REAL NOT NULL,
    ts_ms INTEGER NOT NULL,
    tags TEXT,
    UNIQUE(scope, key, ts_ms)
);

-- STRATEGY PERFORMANCE: Ağırlık güncelleme için özetler
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

-- İNDEKSLER
CREATE INDEX IF NOT EXISTS idx_orders_acc_ts ON orders(account_id, ts_open_ms);
CREATE INDEX IF NOT EXISTS idx_orders_prod_tf ON orders(product, timeframe);
CREATE INDEX IF NOT EXISTS idx_results_status_ts ON results(status, ts_close_ms);
CREATE INDEX IF NOT EXISTS idx_features_acc_tf ON features(account_id, timeframe);
CREATE INDEX IF NOT EXISTS idx_metrics_scope_key_ts ON metrics(scope, key, ts_ms);

-- Görünümler (Kolay raporlama)
CREATE VIEW IF NOT EXISTS v_trades AS
SELECT o.id, o.account_id, o.product, o.timeframe, o.direction, o.amount, 
       o.ts_open_ms, r.ts_close_ms, r.status, r.pnl, r.duration_ms, r.latency_ms
FROM orders o
LEFT JOIN results r ON r.order_id = o.id;
```

## 5.4 Storage API (Python, aiosqlite)

```python
# core/storage.py
import json, aiosqlite
from typing import Dict, Any, Optional, List

class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA foreign_keys=ON;")
            # DDL uygulanır (yukarıdaki SQL)
            await db.commit()

    async def save_order(self, order: Dict[str, Any]) -> None:
        sql = """
        INSERT OR IGNORE INTO orders(id, ts_open_ms, account_id, product, timeframe, 
                                   direction, amount, client_req_id, permit_win_min, 
                                   permit_win_max, extras_json)
        VALUES(:id,:ts_open_ms,:account_id,:product,:timeframe,:direction,:amount,
               :client_req_id,:permit_win_min,:permit_win_max,:extras_json);
        """
        async with aiosqlite.connect(self.db_path) as db:
            payload = {**order, 'extras_json': json.dumps(order.get('extras', {}))}
            await db.execute(sql, payload)
            await db.commit()

    async def save_features(self, order_id: str, feats: Dict[str, Any], 
                          account_id: str, timeframe: int) -> None:
        base_cols = ['ema9','ema21','rsi14','macd_hist','boll_width','atr14',
                    'obv','mfi14','adx14','cmf','vwap_dist','stoch_k','stoch_d',
                    'ichimoku_state','supertrend_state']
        payload = {
            'order_id': order_id,
            'account_id': account_id,
            'timeframe': timeframe,
            **{k: feats.get(k) for k in base_cols},
            'extras_json': json.dumps(feats)
        }
        cols = ','.join(payload.keys())
        params = ':' + ',:'.join(payload.keys())
        sql = f"INSERT OR REPLACE INTO features({cols}) VALUES({params});"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, payload)
            await db.commit()

    async def save_result(self, result: Dict[str, Any]) -> None:
        sql = """
        INSERT OR REPLACE INTO results(order_id, ts_close_ms, status, pnl, 
                                     duration_ms, latency_ms, extras_json)
        VALUES(:order_id,:ts_close_ms,:status,:pnl,:duration_ms,:latency_ms,:extras_json);
        """
        async with aiosqlite.connect(self.db_path) as db:
            payload = {**result, 'extras_json': json.dumps(result.get('extras', {}))}
            await db.execute(sql, payload)
            await db.commit()

    async def record_metric(self, scope: str, key: str, value: float, 
                          ts_ms: int, tags: Optional[str] = None):
        sql = "INSERT OR IGNORE INTO metrics(scope, key, value, ts_ms, tags) VALUES(?,?,?,?,?);"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, (scope, key, value, ts_ms, tags))
            await db.commit()

    async def rolling_winrate(self, account_id: str, product: str, 
                            timeframe: int, last_n: int = 100) -> Optional[float]:
        sql = """
        SELECT AVG(CASE WHEN status='win' THEN 1.0 WHEN status='lose' THEN 0.0 ELSE NULL END)
        FROM (
            SELECT r.status
            FROM orders o
            JOIN results r ON r.order_id = o.id
            WHERE o.account_id=? AND o.product=? AND o.timeframe=?
            ORDER BY r.ts_close_ms DESC
            LIMIT ?
        )
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(sql, (account_id, product, timeframe, last_n)) as cur:
                row = await cur.fetchone()
                return row[0] if row else None

    async def consec_losses(self, account_id: str, product: str, 
                          timeframe: int, last_n: int = 50) -> int:
        sql = """
        SELECT status FROM (
            SELECT r.status
            FROM orders o
            JOIN results r ON r.order_id=o.id
            WHERE o.account_id=? AND o.product=? AND o.timeframe=?
            ORDER BY r.ts_close_ms DESC
            LIMIT ?
        );
        """
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(sql, (account_id, product, timeframe, last_n)) as cur:
                rows = [r[0] for r in await cur.fetchall()]
                cnt = 0
                for s in rows:
                    if s == 'lose':
                        cnt += 1
                    else:
                        break
                return cnt
```

## 5.5 Atomik Akış (Order + Features + Result)

- **Akış**: save_order() → save_features() → (işlem bittiğinde) save_result()
- **Kısmi yazımda kurtarma**: Boot'ta reconcile görevi orders içinde results olmayanları kontrol eder; connector'dan teyit alıp results tablosunu tamamlar

## 5.6 CSV/Parquet Dataset (ML)

- **CSV satırı**: id, ts, account, product, tf, direction, amount, ema9, ema21, rsi14, macd_hist, boll_width, atr14, obv, mfi14, status
- **Politika**: Günlük batch append; büyük dosyalar için per day dosyalar; uzun vadede Parquet arşivi (sütun sıkıştırma)
- **UI dışa aktarım**: "Veriyi dışa aktar (CSV/Parquet)" butonu

## 5.7 Bakım & Yedekleme

- **PRAGMA optimize**: Periyodik VACUUM (uygulama idle iken)
- **.backup API**: Günlük şifreli yedek (isteğe bağlı)
- **Arşivleme**: 90 günden eski features satırlarını Parquet'e taşı → DB'yi incelt
- **Bütünlük testleri**: Başlangıçta PRAGMA integrity_check; (opsiyonel)

## 5.8 Performans İpuçları

- **Tek süreçte tek yazıcı kalıbı**: Storage istekleri bir asyncio.Queue üzerinden batch işlenebilir
- **Toplu yazımlarda**: BEGIN IMMEDIATE; ...; COMMIT;
- **Sadece gereken kolon setlerini doldur**: Geri kalanı extras_json

## 5.9 Kabul Kriterleri

- DDL, indeksler ve görünüm hazır
- Storage API, idempotent upsert ve rolling win rate / consec losses sorguları tanımlandı
- Kurtarma (reconcile), WAL, yedekleme ve bakım politikası belirlendi
- ML dataset dışa aktarım (CSV/Parquet) tasarlandı
