"""
Order Executor - High-level order execution
Parça 11 - Emir yürütücü (üst katman)
"""

import asyncio
import time
from typing import Dict, Any
from .fsm import OrderFSM, PlaceRequest
from ..risk.engine import TradeContext


class OrderExecutor:
    """
    Emir yürütücü
    Risk kontrolü + FSM koordinasyonu
    """
    
    def __init__(
        self,
        connector,
        storage,
        risk_engine,
        guardrails,
        locks: Dict[tuple, asyncio.Lock]
    ):
        self.connector = connector
        self.storage = storage
        self.risk = risk_engine
        self.guardrails = guardrails
        self.locks = locks  # (account_id, product, tf) -> Lock
        
        self.fsm = OrderFSM(connector, storage)
    
    async def execute(self, ctx: TradeContext) -> Dict[str, Any]:
        """
        İşlem yürüt
        Preflight → FSM → Result
        """
        # Preflight kontrolleri
        if not self._preflight_ok(ctx):
            return {"status": "skipped", "reason": "preflight"}
        
        # Concurrency lock
        key = (ctx.account, ctx.product, ctx.timeframe)
        lock = self.locks.setdefault(key, asyncio.Lock())
        
        if lock.locked():
            return {"status": "skipped", "reason": "concurrency"}
        
        async with lock:
            # Son dakika risk kontrolü
            if not self.risk.enter_allowed(ctx):
                return {"status": "skipped", "reason": "risk_guard"}
            
            # Tutar hesapla
            amount = self.risk.compute_amount(ctx)
            
            # Emir isteği oluştur
            request = PlaceRequest(
                account_id=ctx.account,
                product=ctx.product,
                timeframe=ctx.timeframe,
                direction=ctx.direction,
                amount=amount,
                duration_sec=ctx.timeframe * 60,
                payout=ctx.payout
            )
            
            # FSM'e delege et
            result = await self.fsm.execute(request)
            
            # Risk engine'e geri bildirim
            if result.get("status") == "settled":
                outcome = result.get("outcome")
                pnl = result.get("pnl", 0.0)
                is_win = (outcome == "win")
                
                self.risk.on_result(ctx, pnl, is_win)
            
            return result
    
    def _preflight_ok(self, ctx: TradeContext) -> bool:
        """
        Preflight kontrolleri (son saniye)
        """
        # Permit penceresi
        if ctx.payout < ctx.permit_min or ctx.payout > ctx.permit_max:
            return False
        
        # Confidence eşiği
        if ctx.confidence < ctx.win_threshold:
            return False
        
        # Guardrails (KS/CB)
        allowed, _ = self.guardrails.pre_trade_check(ctx.account)
        if not allowed:
            return False
        
        return True
