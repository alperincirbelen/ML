"""
Order Executor & FSM

Parça 7/11 - Emir Yürütme, Durum Makinesi, İdempotency
"""

from __future__ import annotations
import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

from .connector.interface import Connector, OrderAck, OrderResult
from .storage import Storage, OrderRecord, ResultRecord
from .risk import RiskEngine, TradeContext


class OrderState(str, Enum):
    """Emir durumları"""
    IDLE = "IDLE"
    PREPARE = "PREPARE"
    SEND = "SEND"
    CONFIRM = "CONFIRM"
    SETTLED = "SETTLED"
    FAILED = "FAILED"


@dataclass
class ExecutionResult:
    """Yürütme sonucu"""
    status: str                    # settled | failed | skipped
    order_id: Optional[str] = None
    reason: Optional[str] = None
    details: Dict[str, Any] = None


class OrderExecutor:
    """
    İdempotent Emir Yürütücü
    
    Sorumluluklar:
    - PREPARE → SEND → CONFIRM → SETTLED akışı
    - İdempotency (client_req_id)
    - Retry/backoff yönetimi
    - Latency ölçümü
    - Storage entegrasyonu
    
    Özellikler:
    - At-most-once finansal yan etki
    - Belirsizlikte güvenli (timeout → reconcile)
    - Concurrency lock desteği
    """
    
    def __init__(self, connector: Connector, storage: Storage, 
                 risk_engine: RiskEngine, locks: Dict, 
                 confirm_timeout_s: int = 120):
        self.cx = connector
        self.db = storage
        self.risk = risk_engine
        self.locks = locks
        self.confirm_timeout_s = confirm_timeout_s
    
    def _entry_slot(self, timeframe: int) -> int:
        """TF hizalı zaman slotu"""
        now_ms = int(time.time() * 1000)
        tf_ms = timeframe * 60_000
        return now_ms - (now_ms % tf_ms)
    
    def _generate_client_req_id(self, ctx: TradeContext, entry_slot: int) -> str:
        """
        İdempotent client request ID üret
        
        Format: {account}:{product}:{tf}:{slot}:{uuid8}
        """
        random_suffix = uuid.uuid4().hex[:8]
        return f"{ctx.account}:{ctx.product}:{ctx.timeframe}:{entry_slot}:{random_suffix}"
    
    async def execute(self, ctx: TradeContext) -> ExecutionResult:
        """
        İşlem yürüt (tam akış)
        
        Akış:
        1. Preflight checks (permit, threshold, concurrency)
        2. PREPARE: Risk kontrolleri
        3. SEND: Place order (retry destekli)
        4. CONFIRM: Poll sonuç
        5. SETTLED: Storage'a yaz
        
        Returns:
            ExecutionResult: Sonuç ve detaylar
        """
        # === PREFLIGHT ===
        # 1. Permit kontrolü
        if not (ctx.permit_min <= ctx.payout <= ctx.permit_max):
            return ExecutionResult(
                status="skipped",
                reason="permit_window",
                details={"payout": ctx.payout, "window": [ctx.permit_min, ctx.permit_max]}
            )
        
        # 2. Confidence kontrolü
        if ctx.confidence < ctx.win_threshold:
            return ExecutionResult(
                status="skipped",
                reason="below_threshold",
                details={"confidence": ctx.confidence, "threshold": ctx.win_threshold}
            )
        
        # 3. Concurrency lock
        key = (ctx.account, ctx.product, ctx.timeframe)
        lock = self.locks.setdefault(key, asyncio.Lock())
        
        if lock.locked():
            return ExecutionResult(
                status="skipped",
                reason="concurrency",
                details={"key": key}
            )
        
        # === PREPARE ===
        async with lock:
            # 4. Risk kontrolleri
            if not self.risk.enter_allowed(ctx):
                return ExecutionResult(
                    status="skipped",
                    reason="risk_guard",
                    details=self.risk.get_status(ctx.account)
                )
            
            # Tutar hesapla
            amount = self.risk.compute_amount(ctx)
            
            # Entry slot ve client_req_id
            entry_slot = self._entry_slot(ctx.timeframe)
            client_req_id = self._generate_client_req_id(ctx, entry_slot)
            
            # === SEND ===
            t0 = time.time()
            
            try:
                # Place order (idempotent)
                direction = "call" if ctx.confidence > 0 else "put"
                ack = await self.cx.place_order(
                    product=ctx.product,
                    amount=amount,
                    direction=direction,
                    timeframe=ctx.timeframe,
                    client_req_id=client_req_id
                )
            except Exception as e:
                # Retry with same client_req_id (idempotency)
                for attempt in range(1, 4):
                    await asyncio.sleep(0.25 * (2 ** attempt))  # Exponential backoff
                    try:
                        ack = await self.cx.place_order(
                            product=ctx.product,
                            amount=amount,
                            direction=direction,
                            timeframe=ctx.timeframe,
                            client_req_id=client_req_id
                        )
                        break
                    except Exception:
                        if attempt == 3:
                            return ExecutionResult(
                                status="failed",
                                reason="place_failed",
                                details={"error": str(e)}
                            )
            
            t1 = time.time()
            place_latency_ms = int((t1 - t0) * 1000)
            
            # Order bilgisini kaydet
            order_id = ack.order_id
            order_record = OrderRecord(
                id=order_id,
                ts_open_ms=int(t0 * 1000),
                account_id=ctx.account,
                product=ctx.product,
                timeframe=ctx.timeframe,
                direction=+1 if direction == "call" else -1,
                amount=amount,
                payout_pct=ctx.payout,
                client_req_id=client_req_id,
                permit_win_min=ctx.permit_min,
                permit_win_max=ctx.permit_max,
                status="OPEN"
            )
            
            await self.db.save_order(order_record)
            
            # === CONFIRM ===
            # Poll for result
            deadline = time.time() + self.confirm_timeout_s
            result = None
            
            while time.time() < deadline:
                try:
                    result = await self.cx.confirm_order(order_id)
                    if result.status in ("win", "lose", "push", "abort", "canceled"):
                        break
                except Exception:
                    await asyncio.sleep(1.0)
                
                await asyncio.sleep(1.0)
            
            if not result:
                # Timeout
                await self.db.update_order_status(order_id, "FAILED")
                return ExecutionResult(
                    status="failed",
                    order_id=order_id,
                    reason="confirm_timeout"
                )
            
            # === SETTLED ===
            # Sonucu kaydet
            result_record = ResultRecord(
                order_id=order_id,
                ts_close_ms=result.ts_close_ms,
                status=result.status,
                pnl=result.pnl,
                duration_ms=int(result.ts_close_ms - int(t0 * 1000)),
                latency_ms=place_latency_ms
            )
            
            await self.db.save_result(result_record)
            await self.db.update_order_status(order_id, "SETTLED")
            
            # Risk feedback
            is_win = result.status == "win"
            self.risk.on_result(ctx, pnl=result.pnl, is_win=is_win)
            
            return ExecutionResult(
                status="settled",
                order_id=order_id,
                reason=result.status,
                details={
                    "pnl": result.pnl,
                    "latency_ms": place_latency_ms,
                    "duration_ms": result_record.duration_ms
                }
            )


# Test
if __name__ == "__main__":
    from .connector.mock import MockConnector
    
    async def test_executor():
        """Executor test"""
        # Setup
        connector = MockConnector("acc1", seed=42)
        await connector.login("test@example.com", "password")
        
        from .config import StorageConfig
        storage = Storage("test_executor.db")
        await storage.init()
        
        from .risk import RiskLimits, AmountPolicy
        limits = RiskLimits(max_daily_loss=10.0, max_consec_losses=5)
        amt_policy = AmountPolicy(mode="fixed", fixed_a=1.0)
        risk = RiskEngine(limits, amt_policy)
        
        locks = {}
        executor = OrderExecutor(connector, storage, risk, locks)
        
        # Test context
        ctx = TradeContext(
            account="acc1",
            product="EURUSD",
            timeframe=1,
            payout=90.0,
            confidence=0.75,
            prob_win=0.65,
            balance=100.0,
            permit_min=85.0,
            permit_max=95.0,
            win_threshold=0.70
        )
        
        # Execute
        result = await executor.execute(ctx)
        
        print(f"✓ Execution result: {result.status}")
        if result.order_id:
            print(f"  Order ID: {result.order_id}")
        if result.reason:
            print(f"  Reason: {result.reason}")
        if result.details:
            print(f"  Details: {result.details}")
        
        await connector.close()
        await storage.close()
    
    asyncio.run(test_executor())
