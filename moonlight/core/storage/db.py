"""
SQLite database layer with async support
Parça 5, 6, 22 - Asenkron veritabanı katmanı
"""

import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from .models import Order, Result, Feature, Metric


async def init_database(db_path: str) -> None:
    """
    Veritabanını başlat ve şemayı uygula
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    schema_file = Path(__file__).parent / 'schema.sql'
    
    async with aiosqlite.connect(db_path) as db:
        # WAL modu ve ayarlar
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        await db.execute("PRAGMA temp_store=MEMORY;")
        
        # Şemayı uygula
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        await db.executescript(schema_sql)
        await db.commit()
        
        # Versiyon kaydı
        await db.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, applied_ms) VALUES (?, ?)",
            ("1.0.0", int(datetime.now().timestamp() * 1000))
        )
        await db.commit()


class Storage:
    """
    Ana depolama sınıfı - tüm veritabanı işlemleri
    Parça 5, 6, 22
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def init(self) -> None:
        """Veritabanını başlat"""
        await init_database(self.db_path)
    
    async def save_order(self, order: Order) -> None:
        """
        Emir kaydı - idempotent
        client_req_id UNIQUE constraint ile çift kayıt önlenir
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
                'PENDING', extras_json
            ))
            await db.commit()
    
    async def save_result(self, result: Result) -> None:
        """
        Sonuç kaydı ve order durumunu güncelle
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Result ekle
            await db.execute("""
                INSERT OR REPLACE INTO results(
                    order_id, ts_close_ms, status, pnl, duration_ms, latency_ms, extras_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                result.order_id, result.ts_close_ms, result.status, result.pnl,
                result.duration_ms, result.latency_ms,
                json.dumps(result.extras) if result.extras else None
            ))
            
            # Order durumunu SETTLED yap
            await db.execute("""
                UPDATE orders SET status = 'SETTLED' WHERE id = ?;
            """, (result.order_id,))
            
            await db.commit()
    
    async def save_features(self, feature: Feature) -> None:
        """Feature kaydı"""
        cols = [
            'order_id', 'account_id', 'timeframe',
            'ema9', 'ema21', 'rsi14', 'macd_hist', 'boll_width', 'atr14',
            'obv', 'mfi14', 'adx14', 'cmf', 'vwap_dist',
            'stoch_k', 'stoch_d', 'ichimoku_state', 'supertrend_state',
            'extras_json'
        ]
        
        values = (
            feature.order_id, feature.account_id, feature.timeframe,
            feature.ema9, feature.ema21, feature.rsi14, feature.macd_hist,
            feature.boll_width, feature.atr14, feature.obv, feature.mfi14,
            feature.adx14, feature.cmf, feature.vwap_dist, feature.stoch_k,
            feature.stoch_d, feature.ichimoku_state, feature.supertrend_state,
            json.dumps(feature.extras) if feature.extras else None
        )
        
        placeholders = ','.join(['?' for _ in cols])
        sql = f"INSERT OR REPLACE INTO features({','.join(cols)}) VALUES ({placeholders});"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, values)
            await db.commit()
    
    async def record_metric(self, metric: Metric) -> None:
        """Metrik kaydı"""
        sql = "INSERT OR IGNORE INTO metrics_raw(ts_ms, scope, key, value) VALUES(?, ?, ?, ?);"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, (metric.ts_ms, metric.scope, metric.key, metric.value))
            await db.commit()
    
    async def rolling_winrate(
        self, account_id: str, product: str, timeframe: int, last_n: int = 100
    ) -> Optional[float]:
        """
        Kayan pencere win rate hesaplama
        """
        sql = """
        SELECT AVG(CASE WHEN status='win' THEN 1.0 WHEN status='lose' THEN 0.0 ELSE NULL END)
        FROM (
            SELECT r.status
            FROM orders o 
            JOIN results r ON r.order_id = o.id
            WHERE o.account_id = ? AND o.product = ? AND o.timeframe = ?
                AND r.status IN ('win', 'lose')
            ORDER BY r.ts_close_ms DESC
            LIMIT ?
        );
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(sql, (account_id, product, timeframe, last_n)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row and row[0] is not None else None
    
    async def consecutive_losses(
        self, account_id: str, product: str, timeframe: int, last_n: int = 50
    ) -> int:
        """
        Ardışık kayıp sayısı
        """
        sql = """
        SELECT status FROM (
            SELECT r.status 
            FROM orders o 
            JOIN results r ON r.order_id = o.id
            WHERE o.account_id = ? AND o.product = ? AND o.timeframe = ?
            ORDER BY r.ts_close_ms DESC 
            LIMIT ?
        );
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(sql, (account_id, product, timeframe, last_n)) as cursor:
                rows = await cursor.fetchall()
        
        count = 0
        for (status,) in rows:
            if status == 'lose':
                count += 1
            else:
                break
        
        return count
    
    async def daily_pnl(self, account_id: str) -> float:
        """
        Günlük PnL hesaplama (bugün, UTC)
        """
        from datetime import datetime, timezone
        
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_start_ms = int(today_start.timestamp() * 1000)
        
        sql = """
        SELECT COALESCE(SUM(r.pnl), 0.0)
        FROM orders o
        JOIN results r ON r.order_id = o.id
        WHERE o.account_id = ? AND r.ts_close_ms >= ?;
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(sql, (account_id, today_start_ms)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0.0
    
    async def get_open_orders(self, account_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Açık emirleri getir"""
        if account_id:
            sql = """
            SELECT id, account_id, product, timeframe, direction, amount, ts_open_ms, client_req_id
            FROM orders
            WHERE account_id = ? AND status IN ('PENDING', 'OPEN')
            ORDER BY ts_open_ms DESC;
            """
            params = (account_id,)
        else:
            sql = """
            SELECT id, account_id, product, timeframe, direction, amount, ts_open_ms, client_req_id
            FROM orders
            WHERE status IN ('PENDING', 'OPEN')
            ORDER BY ts_open_ms DESC;
            """
            params = ()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        'id': r[0], 'account_id': r[1], 'product': r[2],
                        'timeframe': r[3], 'direction': r[4], 'amount': r[5],
                        'ts_open_ms': r[6], 'client_req_id': r[7]
                    }
                    for r in rows
                ]
    
    async def get_recent_trades(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Son işlemleri getir"""
        sql = """
        SELECT * FROM v_trades
        ORDER BY ts_open_ms DESC
        LIMIT ?;
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def update_instrument_cache(
        self, symbol: str, kind: str, payout: float, updated_at: int
    ) -> None:
        """Katalog güncelle"""
        sql = """
        INSERT OR REPLACE INTO instrument_cache(symbol, kind, payout, updated_at)
        VALUES (?, ?, ?, ?);
        """
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, (symbol, kind, payout, updated_at))
            await db.commit()
    
    async def get_instrument_cache(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Katalogdan ürün bilgisi getir"""
        sql = "SELECT * FROM instrument_cache WHERE symbol = ?;"
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, (symbol,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
