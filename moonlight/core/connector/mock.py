"""
Mock Connector - Test ve Paper Trading için

Deterministik, gerçek ağ erişimi olmayan simülatör
"""

import asyncio
import math
import random
import time
from typing import List, Dict, Any, Optional

from .interface import Connector, Candle, Quote, OrderAck, OrderResult


class MockConnector:
    """
    Mock Connector - Paper/Test Modu
    
    Özellikler:
    - Deterministik sinüzoidal fiyat üretimi
    - Basit win/loss simülasyonu
    - İdempotent order handling
    - Gerçek ağ gecikmesi yok
    """
    
    def __init__(self, account_id: str, seed: int = 42, base_winrate: float = 0.55):
        self.account_id = account_id
        self._seed = seed
        self._base_winrate = base_winrate
        random.seed(seed)
        
        # Simülasyon durumu
        self._price = 1.0000
        self._access_token: Optional[str] = None
        self._orders: Dict[str, OrderAck] = {}  # client_req_id -> OrderAck
    
    async def login(self, username: str, password: str, otp: Optional[str] = None) -> None:
        """Mock login - her zaman başarılı"""
        await asyncio.sleep(0.05)  # Gerçekçi gecikme simülasyonu
        self._access_token = f"MOCK_TOKEN_{self.account_id}_{int(time.time())}"
    
    async def refresh_token(self) -> None:
        """Mock token yenileme"""
        await asyncio.sleep(0.03)
        if self._access_token:
            self._access_token = f"MOCK_TOKEN_{self.account_id}_{int(time.time())}"
    
    async def get_candles(self, product: str, timeframe: int, n: int = 200,
                         until_ms: Optional[int] = None) -> List[Candle]:
        """
        Mock mumlar - sinüzoidal hareket + rastgele gürültü
        
        Gerçekçi özellikler:
        - Trend + gürültü kombinasyonu
        - ATR benzeri volatilite
        - Pozitif hacim
        """
        await asyncio.sleep(0.02)  # API gecikmesi simülasyonu
        
        now = until_ms or int(time.time() * 1000)
        tf_ms = timeframe * 60_000
        
        candles = []
        price = self._price
        
        for i in range(n):
            ts = now - (n - i - 1) * tf_ms
            
            # Sinüzoidal trend + gürültü
            trend = math.sin(i / 20.0) * 0.002
            noise = (random.random() - 0.5) * 0.001
            
            close = max(0.5, price + trend + noise)
            high = close + random.random() * 0.0003
            low = close - random.random() * 0.0003
            open_price = price
            volume = random.randint(100, 2000)
            
            candles.append(Candle(
                ts_ms=ts,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=float(volume)
            ))
            
            price = close
        
        self._price = price
        return candles
    
    async def get_current_win_rate(self, product: str) -> float:
        """Mock payout - %88-92 arası rastgele dalgalanma"""
        await asyncio.sleep(0.01)
        base = 90.0
        variation = (random.random() - 0.5) * 4  # ±2 puan
        return base + variation
    
    async def get_quote(self, product: str) -> Quote:
        """Mock anlık fiyat"""
        await asyncio.sleep(0.01)
        
        # Küçük rastgele hareket
        self._price += (random.random() - 0.5) * 0.0003
        
        spread = 0.0001
        return Quote(
            ts_ms=int(time.time() * 1000),
            bid=self._price - spread / 2,
            ask=self._price + spread / 2
        )
    
    async def place_order(self, *, product: str, amount: float, direction: str,
                         timeframe: int, client_req_id: str) -> OrderAck:
        """
        Mock emir yerleştir - idempotent
        
        Aynı client_req_id → aynı order_id
        """
        await asyncio.sleep(0.08)  # Gerçekçi gecikme
        
        # İdempotency kontrolü
        if client_req_id in self._orders:
            return self._orders[client_req_id]
        
        # Yeni emir
        order_id = f"MOCK_{self.account_id}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        ts_open = int(time.time() * 1000)
        expires_at = ts_open + (timeframe * 60 * 1000)
        
        ack = OrderAck(
            order_id=order_id,
            client_req_id=client_req_id,
            ts_open_ms=ts_open,
            status="OPEN",
            expires_at_ms=expires_at
        )
        
        self._orders[client_req_id] = ack
        return ack
    
    async def confirm_order(self, order_id: str) -> OrderResult:
        """
        Mock emir sonucu - basit win/loss simülasyonu
        
        Win oranı: base_winrate civarında rastgele
        """
        await asyncio.sleep(0.06)
        
        # Basit kazanma kuralı (seed bazlı deterministik ama rastgele görünümlü)
        win_prob = self._base_winrate + (random.random() - 0.5) * 0.1
        is_win = random.random() < win_prob
        
        # PnL hesapla (fixed-time binary mantığı)
        if is_win:
            pnl = 0.9  # %90 payout varsayımı
            status = "win"
        else:
            pnl = -1.0
            status = "lose"
        
        # Nadiren push
        if random.random() < 0.02:
            pnl = 0.0
            status = "push"
        
        return OrderResult(
            order_id=order_id,
            status=status,
            pnl=pnl,
            ts_close_ms=int(time.time() * 1000),
            latency_ms=random.randint(80, 200)
        )
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Mock iptal"""
        await asyncio.sleep(0.05)
        return {"order_id": order_id, "status": "canceled"}
    
    async def heartbeat(self) -> None:
        """Mock heartbeat - her zaman başarılı"""
        await asyncio.sleep(0.01)
    
    async def close(self) -> None:
        """Temizlik"""
        self._access_token = None
        self._orders.clear()


# Test
if __name__ == "__main__":
    async def test_mock():
        """Mock connector test"""
        conn = MockConnector("acc1", seed=42)
        
        await conn.login("test@example.com", "password")
        print("✓ Login OK")
        
        candles = await conn.get_candles("EURUSD", 1, n=50)
        print(f"✓ Candles: {len(candles)}")
        
        payout = await conn.get_current_win_rate("EURUSD")
        print(f"✓ Payout: {payout:.2f}%")
        
        ack = await conn.place_order(
            product="EURUSD",
            amount=10.0,
            direction="call",
            timeframe=1,
            client_req_id="test_req_123"
        )
        print(f"✓ Order placed: {ack.order_id}")
        
        # İdempotency testi
        ack2 = await conn.place_order(
            product="EURUSD",
            amount=10.0,
            direction="call",
            timeframe=1,
            client_req_id="test_req_123"
        )
        assert ack.order_id == ack2.order_id, "Idempotency failed!"
        print("✓ Idempotency OK")
        
        result = await conn.confirm_order(ack.order_id)
        print(f"✓ Result: {result.status}, PnL: {result.pnl}")
        
        await conn.close()
        print("✓ Mock connector test completed")
    
    asyncio.run(test_mock())
