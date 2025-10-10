from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Dict, Any

_DDL = """
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  ts_open_ms INTEGER NOT NULL,
  account_id TEXT NOT NULL,
  product TEXT NOT NULL,
  timeframe INTEGER NOT NULL,
  direction TEXT NOT NULL,
  amount REAL NOT NULL,
  client_req_id TEXT UNIQUE NOT NULL,
  permit_win_min REAL,
  permit_win_max REAL
);

CREATE TABLE IF NOT EXISTS results (
  order_id TEXT PRIMARY KEY REFERENCES orders(id) ON DELETE CASCADE,
  ts_close_ms INTEGER NOT NULL,
  status TEXT NOT NULL,
  pnl REAL NOT NULL,
  duration_ms INTEGER,
  latency_ms INTEGER
);
"""


class SQLiteStorage:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.executescript(_DDL)
            db.commit()

    def save_order(self, order: Dict[str, Any]) -> None:
        sql = (
            "INSERT OR IGNORE INTO orders(id, ts_open_ms, account_id, product, timeframe, direction, amount, client_req_id, permit_win_min, permit_win_max) "
            "VALUES(:id,:ts_open_ms,:account_id,:product,:timeframe,:direction,:amount,:client_req_id,:permit_win_min,:permit_win_max)"
        )
        with sqlite3.connect(self.path) as db:
            db.execute(sql, order)
            db.commit()

    def save_result(self, res: Dict[str, Any]) -> None:
        sql = (
            "INSERT OR REPLACE INTO results(order_id, ts_close_ms, status, pnl, duration_ms, latency_ms) "
            "VALUES(:order_id,:ts_close_ms,:status,:pnl,:duration_ms,:latency_ms)"
        )
        with sqlite3.connect(self.path) as db:
            db.execute(sql, res)
            db.commit()
