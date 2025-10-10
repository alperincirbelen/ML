"""
Order Finite State Machine
Parça 7, 11 - Emir durum makinesi (FSM)
"""

import asyncio
import time
import uuid
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any


class OrderState(Enum):
    """Emir durumları"""
    IDLE = "idle"
    PREPARE = "prepare"
    SEND = "send"
    CONFIRM = "confirm"
    SETTLED = "settled"
    FAILED = "failed"


@dataclass
class PlaceRequest:
    """Emir yerleştirme isteği"""
    account_id: str
    product: str
    timeframe: int
    direction: str  # 'call' or 'put'
    amount: float
    duration_sec: int = 60
    payout: Optional[float] = None
    client_req_id: Optional[str] = None
    
    def __post_init__(self):
        if self.client_req_id is None:
            # Benzersiz ID üret
            self.client_req_id = self.generate_client_req_id()
    
    def generate_client_req_id(self) -> str:
        """
        Idempotency anahtarı üret
        Format: {account}:{product}:{tf}:{slot}:{uuid8}
        """
        now_ms = int(time.time() * 1000)
        tf_ms = self.timeframe * 60_000
        slot = now_ms - (now_ms % tf_ms)
        
        return f"{self.account_id}:{self.product}:{self.timeframe}:{slot}:{uuid.uuid4().hex[:8]}"


class OrderFSM:
    """
    Emir Durum Makinesi
    PREPARE → SEND → CONFIRM → SETTLED/FAILED
    """
    
    def __init__(
        self,
        connector,
        storage,
        max_send_retries: int = 5,
        max_confirm_retries: int = 10,
        confirm_timeout_sec: int = 120
    ):
        self.connector = connector
        self.storage = storage
        self.max_send_retries = max_send_retries
        self.max_confirm_retries = max_confirm_retries
        self.confirm_timeout_sec = confirm_timeout_sec
        
        self.state = OrderState.IDLE
        self._current_order_id: Optional[str] = None
    
    async def execute(self, request: PlaceRequest) -> Dict[str, Any]:
        """
        Emir akışını yürüt
        Returns: {"status": "settled"|"failed", "order_id": ..., "reason": ...}
        """
        self.state = OrderState.PREPARE
        
        try:
            # PREPARE - preflight kontrolleri
            # (Guardrails zaten dışarıda çağrılmış olmalı)
            
            # SEND - emir yerleştir
            self.state = OrderState.SEND
            ack = await self._send_with_retry(request)
            
            if not ack:
                self.state = OrderState.FAILED
                return {
                    "status": "failed",
                    "reason": "send_failed",
                    "order_id": None
                }
            
            order_id = ack.get("order_id")
            self._current_order_id = order_id
            
            # Storage'a kaydet
            from ..storage.models import Order
            order = Order(
                id=order_id,
                ts_open_ms=int(time.time() * 1000),
                account_id=request.account_id,
                product=request.product,
                timeframe=request.timeframe,
                direction=request.direction,
                amount=request.amount,
                client_req_id=request.client_req_id,
                payout_pct=request.payout
            )
            await self.storage.save_order(order)
            
            # CONFIRM - sonucu bekle
            self.state = OrderState.CONFIRM
            result = await self._confirm_with_poll(order_id)
            
            if result:
                # SETTLED
                self.state = OrderState.SETTLED
                
                # Result kaydet
                from ..storage.models import Result
                res = Result(
                    order_id=order_id,
                    ts_close_ms=result.get("ts_close_ms", int(time.time() * 1000)),
                    status=result.get("status", "abort"),
                    pnl=float(result.get("pnl", 0.0)),
                    duration_ms=result.get("duration_ms"),
                    latency_ms=result.get("latency_ms")
                )
                await self.storage.save_result(res)
                
                return {
                    "status": "settled",
                    "order_id": order_id,
                    "outcome": result.get("status"),
                    "pnl": result.get("pnl")
                }
            else:
                self.state = OrderState.FAILED
                return {
                    "status": "failed",
                    "reason": "confirm_timeout",
                    "order_id": order_id
                }
        
        except Exception as e:
            self.state = OrderState.FAILED
            return {
                "status": "failed",
                "reason": f"exception: {str(e)}",
                "order_id": self._current_order_id
            }
        
        finally:
            self.state = OrderState.IDLE
            self._current_order_id = None
    
    async def _send_with_retry(
        self, 
        request: PlaceRequest
    ) -> Optional[Dict[str, Any]]:
        """
        Exponential backoff ile emir gönder
        """
        for attempt in range(self.max_send_retries):
            try:
                ack = await self.connector.place_order(
                    product=request.product,
                    amount=request.amount,
                    direction=request.direction,
                    timeframe=request.timeframe,
                    client_req_id=request.client_req_id
                )
                return ack
            
            except Exception as e:
                # Exponential backoff
                if attempt < self.max_send_retries - 1:
                    backoff = (0.5 * (2 ** attempt))  # 0.5, 1, 2, 4, 8 sn
                    jitter = backoff * 0.15 * (2 * random.random() - 1)
                    await asyncio.sleep(backoff + jitter)
                else:
                    # Son deneme başarısız
                    return None
        
        return None
    
    async def _confirm_with_poll(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Polling ile sonucu bekle
        """
        deadline = time.time() + self.confirm_timeout_sec
        poll_interval = 1.0  # İlk 10 saniye 1sn
        attempt = 0
        
        while time.time() < deadline:
            try:
                result = await self.connector.confirm_order(order_id)
                
                status = result.get("status")
                if status in ("win", "lose", "push", "abort", "canceled"):
                    return result
                
                # Henüz sonuçlanmadı, devam et
                await asyncio.sleep(poll_interval)
                
                # Poll interval'ı artır (10 denemeden sonra)
                attempt += 1
                if attempt > 10:
                    poll_interval = 2.0
            
            except Exception:
                # Geçici hata, devam et
                await asyncio.sleep(poll_interval)
        
        # Timeout
        return None
