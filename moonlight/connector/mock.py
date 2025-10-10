from __future__ import annotations
import time
import math
import random
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class MockState:
    seed: int = 42
    last_price: float = 1.0000


class MockConnector:
    """
    Simple deterministic-ish market and order simulator for paper runs.
    Methods are synchronous and do not perform any network I/O.
    """

    def __init__(self, account_id: str, seed: int = 42):
        self.account_id = account_id
        self.state = MockState(seed=seed)
        random.seed(seed)

    # --- Market data ---
    def get_candles(self, product: str, timeframe: int, n: int = 200) -> List[Dict[str, Any]]:
        """
        Generate a synthetic OHLCV time series using a noisy sinusoid.
        timeframe in minutes; n number of bars; newest last.
        """
        now_ms = int(time.time() * 1000)
        tf_ms = timeframe * 60_000
        out: List[Dict[str, Any]] = []
        p = self.state.last_price
        for i in range(n, 0, -1):  # build from oldest to newest
            t = now_ms - i * tf_ms
            base = 0.001 * math.sin((now_ms // tf_ms + i) / 7.0)
            noise = (random.random() - 0.5) * 0.0006
            close = max(0.1, p + base + noise)
            high = max(close, p) + 0.00025
            low = min(close, p) - 0.00025
            vol = random.randint(500, 1500)
            # open equals previous close for simplicity
            open_ = p
            out.append({"ts": t, "open": open_, "high": high, "low": low, "close": close, "volume": vol})
            p = close
        self.state.last_price = p
        return out

    def get_current_win_rate(self, product: str) -> float:
        """Return a pseudo payout% in [85,95]."""
        base = 90.0
        jitter = (random.random() - 0.5) * 6.0
        return max(70.0, min(95.0, base + jitter))

    # --- Trading ---
    def place_order(
        self,
        *,
        product: str,
        amount: float,
        direction: str,  # 'call' | 'put'
        timeframe: int,
        client_req_id: str,
    ) -> Dict[str, Any]:
        order_id = f"MOCK-{int(time.time()*1000)}-{random.randint(1000,9999)}"
        return {"order_id": order_id, "client_req_id": client_req_id, "ts_open_ms": int(time.time() * 1000)}

    def confirm_order(self, order_id: str) -> Dict[str, Any]:
        # Simple 55% win bias with randomness. Latency ~120ms
        win = random.random() > 0.45
        pnl = 0.9 if win else -1.0
        return {
            "order_id": order_id,
            "status": "win" if win else "lose",
            "pnl": pnl,
            "ts_close_ms": int(time.time() * 1000) + 60_000,
            "latency_ms": 120,
        }
