"""
Storage Layer - SQLite Database Management

Parça 5/6/22 - Veri Modeli & Depolama
Idempotent, append-only, WAL modu
"""

from __future__ import annotations
import json
import aiosqlite
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


# DDL - Schema Definition
DDL_ORDERS = """
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    ts_open_ms INTEGER NOT NULL,
    account_id TEXT NOT NULL,
    product TEXT NOT NULL,
    timeframe INTEGER NOT NULL CHECK(timeframe IN (1,5,15)),
    direction INTEGER NOT NULL CHECK(direction IN (1,-1)),
    amount REAL NOT NULL,
    payout_pct REAL,
    client_req_id TEXT UNIQUE NOT NULL,
    permit_win_min REAL,
    permit_win_max REAL,
    status TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING','OPEN','SETTLED','FAILED')),
    extras_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_orders_acc_ts ON orders(account_id, ts_open_ms DESC);
CREATE INDEX IF NOT EXISTS idx_orders_prod_tf ON orders(product, timeframe, ts_open_ms DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_client_req ON orders(client_req_id);
"""

DDL_RESULTS = """
CREATE TABLE IF NOT EXISTS results (
    order_id TEXT PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
    ts_close_ms INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('win','lose','push','abort','canceled')),
    pnl REAL NOT NULL,
    duration_ms INTEGER,
    latency_ms INTEGER,
    extras_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_results_status_ts ON results(status, ts_close_ms DESC);
"""

DDL_FEATURES = """
CREATE TABLE IF NOT EXISTS features (
    order_id TEXT PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL,
    timeframe INTEGER NOT NULL,
    -- Temel göstergeler
    ema9 REAL, ema21 REAL, rsi14 REAL, macd_hist REAL,
    boll_width REAL, atr14 REAL, obv REAL, mfi14 REAL,
    adx14 REAL, cmf REAL, vwap_dist REAL,
    stoch_k REAL, stoch_d REAL,
    ichimoku_state TEXT, supertrend_state TEXT,
    -- Esnek alanlar
    extras_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_features_acc_tf ON features(account_id, timeframe);
"""

DDL_METRICS = """
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    key TEXT NOT NULL,
    value REAL NOT NULL,
    ts_ms INTEGER NOT NULL,
    tags TEXT,
    UNIQUE(scope, key, ts_ms)
);

CREATE INDEX IF NOT EXISTS idx_metrics_scope_key_ts ON metrics(scope, key, ts_ms DESC);
"""

DDL_STRATEGY_PERF = """
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
"""

DDL_CATALOG = """
CREATE TABLE IF NOT EXISTS instrument_cache (
    symbol TEXT PRIMARY KEY,
    kind TEXT DEFAULT 'forex',
    payout REAL,
    updated_at INTEGER NOT NULL
);
"""

DDL_AUDIT = """
CREATE TABLE IF NOT EXISTS config_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_ms INTEGER NOT NULL,
    scope TEXT,
    actor TEXT,
    patch_json TEXT NOT NULL,
    comment TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_ts ON config_audit(ts_ms DESC);
"""

DDL_VIEWS = """
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
"""


@dataclass
class OrderRecord:
    """Emir kaydı"""
    id: str
    ts_open_ms: int
    account_id: str
    product: str
    timeframe: int
    direction: int  # +1 call, -1 put
    amount: float
    payout_pct: Optional[float]
    client_req_id: str
    permit_win_min: Optional[float] = None
    permit_win_max: Optional[float] = None
    status: str = 'PENDING'
    extras: Optional[Dict[str, Any]] = None


@dataclass
class ResultRecord:
    """Sonuç kaydı"""
    order_id: str
    ts_close_ms: int
    status: str  # win|lose|push|abort|canceled
    pnl: float
    duration_ms: Optional[int] = None
    latency_ms: Optional[int] = None
    extras: Optional[Dict[str, Any]] = None


class Storage:
    """
    SQLite Storage Layer
    
    Sorumluluklar:
    - Veritabanı yaşam döngüsü (init, close)
    - İdempotent kayıt (orders, results, features, metrics)
    - Rolling win rate ve streak hesaplamaları
    - Append-only ilkeleri
    """
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._initialized = False
    
    async def init(self) -> None:
        """Veritabanını başlat, DDL uygula"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiosqlite.connect(self.db_path) as db:
            # WAL modu (daha iyi concurrency)
            await db.execute("PRAGMA journal_mode=WAL;")
            await db.execute("PRAGMA foreign_keys=ON;")
            await db.execute("PRAGMA synchronous=NORMAL;")
            
            # Tabloları oluştur
            await db.executescript(DDL_ORDERS)
            await db.executescript(DDL_RESULTS)
            await db.executescript(DDL_FEATURES)
            await db.executescript(DDL_METRICS)
            await db.executescript(DDL_STRATEGY_PERF)
            await db.executescript(DDL_CATALOG)
            await db.executescript(DDL_AUDIT)
            await db.executescript(DDL_VIEWS)
            
            await db.commit()
        
        self._initialized = True
    
    async def save_order(self, order: OrderRecord) -> None:
        """
        Emir kaydı - idempotent
        
        client_req_id UNIQUE kısıtı sayesinde tekrar denemeler güvenli
        """
        sql = """
        INSERT OR IGNORE INTO orders(
            id, ts_open_ms, account_id, product, timeframe, direction,
            amount, payout_pct, client_req_id, permit_win_min, permit_win_max,
            status, extras_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        
        extras_json = json.dumps(order.extras) if order.extras else None
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, (
                order.id, order.ts_open_ms, order.account_id, order.product,
                order.timeframe, order.direction, order.amount, order.payout_pct,
                order.client_req_id, order.permit_win_min, order.permit_win_max,
                order.status, extras_json
            ))
            await db.commit()
    
    async def save_result(self, result: ResultRecord) -> None:
        """
        Sonuç kaydı - idempotent upsert
        """
        sql = """
        INSERT OR REPLACE INTO results(
            order_id, ts_close_ms, status, pnl, duration_ms, latency_ms, extras_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        
        extras_json = json.dumps(result.extras) if result.extras else None
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, (
                result.order_id, result.ts_close_ms, result.status, result.pnl,
                result.duration_ms, result.latency_ms, extras_json
            ))
            await db.commit()
    
    async def update_order_status(self, order_id: str, status: str) -> None:
        """Emir durumunu güncelle"""
        sql = "UPDATE orders SET status = ? WHERE id = ?;"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, (status, order_id))
            await db.commit()
    
    async def save_features(self, order_id: str, account_id: str, timeframe: int, 
                           features: Dict[str, Any]) -> None:
        """Özellik kaydet"""
        base_cols = [
            'ema9', 'ema21', 'rsi14', 'macd_hist', 'boll_width', 'atr14',
            'obv', 'mfi14', 'adx14', 'cmf', 'vwap_dist', 'stoch_k', 'stoch_d',
            'ichimoku_state', 'supertrend_state'
        ]
        
        payload = {
            'order_id': order_id,
            'account_id': account_id,
            'timeframe': timeframe,
            **{k: features.get(k) for k in base_cols},
            'extras_json': json.dumps(features)
        }
        
        cols = ','.join(payload.keys())
        placeholders = ','.join(['?' for _ in payload])
        sql = f"INSERT OR REPLACE INTO features({cols}) VALUES({placeholders});"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, tuple(payload.values()))
            await db.commit()
    
    async def record_metric(self, scope: str, key: str, value: float, 
                           ts_ms: int, tags: Optional[str] = None) -> None:
        """Metrik kaydet"""
        sql = "INSERT OR IGNORE INTO metrics(scope, key, value, ts_ms, tags) VALUES(?,?,?,?,?);"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, (scope, key, value, ts_ms, tags))
            await db.commit()
    
    async def rolling_winrate(self, account_id: str, product: str, 
                              timeframe: int, last_n: int = 100) -> Optional[float]:
        """
        Son N işlemdeki kazanma oranı
        
        Returns:
            float: 0.0-1.0 arası kazanma oranı, veri yoksa None
        """
        sql = """
        SELECT AVG(CASE WHEN status='win' THEN 1.0 WHEN status='lose' THEN 0.0 ELSE NULL END)
        FROM (
            SELECT r.status
            FROM orders o JOIN results r ON r.order_id = o.id
            WHERE o.account_id=? AND o.product=? AND o.timeframe=?
              AND r.status IN ('win','lose')
            ORDER BY r.ts_close_ms DESC
            LIMIT ?
        )
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(sql, (account_id, product, timeframe, last_n)) as cur:
                row = await cur.fetchone()
                return row[0] if row and row[0] is not None else None
    
    async def consec_losses(self, account_id: str, product: str, 
                           timeframe: int, last_n: int = 50) -> int:
        """
        Ardışık kayıp sayısı
        
        Returns:
            int: Mevcut ardışık kayıp serisi
        """
        sql = """
        SELECT status FROM (
            SELECT r.status FROM orders o JOIN results r ON r.order_id=o.id
            WHERE o.account_id=? AND o.product=? AND o.timeframe=?
              AND r.status IN ('win','lose')
            ORDER BY r.ts_close_ms DESC LIMIT ?
        );
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(sql, (account_id, product, timeframe, last_n)) as cur:
                rows = await cur.fetchall()
        
        # En son sonuçtan başla, ardışık kayıpları say
        count = 0
        for (status,) in rows:
            if status == 'lose':
                count += 1
            else:
                break
        
        return count
    
    async def daily_pnl(self, account_id: str, day_start_ms: int) -> float:
        """Günlük PnL toplamı"""
        sql = """
        SELECT COALESCE(SUM(r.pnl), 0.0)
        FROM orders o JOIN results r ON r.order_id = o.id
        WHERE o.account_id = ? AND o.ts_open_ms >= ?
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(sql, (account_id, day_start_ms)) as cur:
                row = await cur.fetchone()
                return row[0] if row else 0.0
    
    async def open_orders(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Açık emirleri getir"""
        if account_id:
            sql = "SELECT * FROM orders WHERE account_id=? AND status IN ('PENDING','OPEN')"
            params = (account_id,)
        else:
            sql = "SELECT * FROM orders WHERE status IN ('PENDING','OPEN')"
            params = ()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cur:
                rows = await cur.fetchall()
                return [dict(row) for row in rows]
    
    async def recent_trades(self, limit: int = 20, 
                           account_id: Optional[str] = None,
                           product: Optional[str] = None,
                           timeframe: Optional[int] = None) -> List[Dict[str, Any]]:
        """Son işlemler"""
        sql = "SELECT * FROM v_trades WHERE 1=1"
        params = []
        
        if account_id:
            sql += " AND account_id=?"
            params.append(account_id)
        if product:
            sql += " AND product=?"
            params.append(product)
        if timeframe:
            sql += " AND timeframe=?"
            params.append(timeframe)
        
        sql += " ORDER BY ts_open_ms DESC LIMIT ?"
        params.append(limit)
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, tuple(params)) as cur:
                rows = await cur.fetchall()
                return [dict(row) for row in rows]
    
    async def update_catalog(self, symbol: str, kind: str, payout: float, ts_ms: int) -> None:
        """Katalog (payout cache) güncelle"""
        sql = """
        INSERT OR REPLACE INTO instrument_cache(symbol, kind, payout, updated_at)
        VALUES (?, ?, ?, ?);
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, (symbol, kind, payout, ts_ms))
            await db.commit()
    
    async def get_catalog(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Katalog girdisini getir"""
        sql = "SELECT * FROM instrument_cache WHERE symbol=?"
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, (symbol,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None
    
    async def close(self) -> None:
        """Kaynakları temizle"""
        # SQLite connection pool yok, her işlem kendi bağlantısı
        pass


# Test ve kullanım örneği
if __name__ == "__main__":
    import asyncio
    
    async def test_storage():
        """Storage katmanını test et"""
        db = Storage("test_trades.db")
        await db.init()
        
        # Test order
        order = OrderRecord(
            id="test_001",
            ts_open_ms=int(datetime.now().timestamp() * 1000),
            account_id="acc1",
            product="EURUSD",
            timeframe=1,
            direction=1,
            amount=10.0,
            payout_pct=90.0,
            client_req_id="test_req_001",
            permit_win_min=89.0,
            permit_win_max=93.0
        )
        
        await db.save_order(order)
        print("✓ Order saved")
        
        # Test result
        result = ResultRecord(
            order_id="test_001",
            ts_close_ms=int(datetime.now().timestamp() * 1000) + 60000,
            status="win",
            pnl=9.0,
            duration_ms=60000,
            latency_ms=150
        )
        
        await db.save_result(result)
        await db.update_order_status("test_001", "SETTLED")
        print("✓ Result saved")
        
        # Test queries
        wr = await db.rolling_winrate("acc1", "EURUSD", 1, 100)
        print(f"✓ Win rate: {wr}")
        
        trades = await db.recent_trades(limit=10)
        print(f"✓ Recent trades: {len(trades)}")
        
        await db.close()
        print("✓ Storage test completed")
    
    asyncio.run(test_storage())
