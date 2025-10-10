from __future__ import annotations
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Any

from .storage.sqlite import SQLiteStorage
from .risk import RiskEngine


@dataclass
class TradeCtx:
    account: str
    product: str
    timeframe: int
    direction: str   # 'call' | 'put'
    payout: float
    confidence: float
    p_hat: float
    win_threshold: float
    permit_min: float
    permit_max: float
    balance: float = 100.0


class OrderExecutor:
    def __init__(self, connector, storage: SQLiteStorage, risk: RiskEngine):
        self.cx = connector
        self.db = storage
        self.risk = risk

    def execute(self, ctx: TradeCtx) -> Dict[str, Any]:
        if not self.risk.enter_allowed(payout=ctx.payout, confidence=ctx.confidence, p_hat=ctx.p_hat):
            return {"status": "skipped", "reason": "guard"}
        amount = self.risk.compute_amount(balance=ctx.balance)
        entry_slot = int(time.time() * 1000)
        client_req_id = f"{ctx.account}:{ctx.product}:{ctx.timeframe}:{entry_slot}:{uuid.uuid4().hex[:8]}"
        t0 = time.time()
        ack = self.cx.place_order(
            product=ctx.product,
            amount=amount,
            direction=ctx.direction,
            timeframe=ctx.timeframe,
            client_req_id=client_req_id,
        )
        t1 = time.time()
        order_id = ack["order_id"]
        self.db.save_order(
            {
                "id": order_id,
                "ts_open_ms": int(t0 * 1000),
                "account_id": ctx.account,
                "product": ctx.product,
                "timeframe": ctx.timeframe,
                "direction": ctx.direction,
                "amount": amount,
                "client_req_id": client_req_id,
                "permit_win_min": ctx.permit_min,
                "permit_win_max": ctx.permit_max,
            }
        )
        res = self.cx.confirm_order(order_id)
        self.db.save_result(
            {
                "order_id": order_id,
                "ts_close_ms": res.get("ts_close_ms", int(time.time() * 1000)),
                "status": res.get("status", "abort"),
                "pnl": float(res.get("pnl", 0.0)),
                "duration_ms": int(res.get("ts_close_ms", 0) - int(t0 * 1000)),
                "latency_ms": int((t1 - t0) * 1000),
            }
        )
        return {"status": res.get("status", "abort"), "order_id": order_id}
