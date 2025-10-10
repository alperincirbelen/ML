"""
Mock Connector - Test and paper trading
Parça 6 - Test ve paper trading için mock bağlayıcı
"""

import asyncio
import math
import random
import time
from typing import Any, Dict, List, Optional


class MockConnector:
    """
    Mock connector - gerçek API çağrısı yapmaz
    Paper trading ve test için deterministik veri üretir
    """
    
    def __init__(self, account_id: str, seed: int = 42):
        self.account_id = account_id
        random.seed(seed + hash(account_id))  # Hesap bazlı seed
        self._price = 1.0000
        self._logged_in = False
        self._access_token: Optional[str] = None
    
    async def login(
        self, username: str, password: str, otp: Optional[str] = None
    ) -> None:
        """Mock login - her zaman başarılı"""
        await asyncio.sleep(0.1)  # Gerçekçi gecikme
        self._logged_in = True
        self._access_token = f"MOCK_TOKEN_{self.account_id}_{int(time.time())}"
    
    async def refresh_token(self) -> None:
        """Token yenileme - mock"""
        await asyncio.sleep(0.05)
        self._access_token = f"MOCK_TOKEN_{self.account_id}_{int(time.time())}"
    
    async def get_candles(
        self, 
        product: str, 
        timeframe: int, 
        n: int = 200,
        until_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Sentetik mum verisi üret
        Sinüzoidal trend + gürültü ile gerçekçi OHLCV
        """
        await asyncio.sleep(0.05)  # API gecikmesi simülasyonu
        
        now = until_ms or int(time.time() * 1000)
        candles = []
        
        p = self._price
        for i in range(n):
            t = now - (n - 1 - i) * timeframe * 60_000
            
            # Sinüzoidal trend + gürültü
            base = math.sin(i / 10.0) * 0.001
            noise = (random.random() - 0.5) * 0.0005
            
            close = max(0.5, p + base + noise)
            high = max(close, p) + abs(random.gauss(0, 0.0002))
            low = min(close, p) - abs(random.gauss(0, 0.0002))
            open_price = p
            volume = random.randint(100, 1000)
            
            candles.append({
                "ts_ms": t,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume
            })
            
            p = close
        
        self._price = p
        return candles
    
    async def get_current_win_rate(self, product: str) -> float:
        """
        Mock payout - 88-92% arasında dalgalanır
        """
        await asyncio.sleep(0.02)
        return 90.0 + (random.random() - 0.5) * 4
    
    async def get_quote(self, product: str) -> Dict[str, Any]:
        """Anlık fiyat teklifi"""
        await asyncio.sleep(0.01)
        
        self._price += (random.random() - 0.5) * 0.0003
        spread = 0.0001
        
        return {
            "ts": int(time.time() * 1000),
            "bid": self._price - spread,
            "ask": self._price + spread,
            "mid": self._price
        }
    
    async def get_instruments(self) -> List[Dict[str, Any]]:
        """Mock ürün listesi"""
        await asyncio.sleep(0.05)
        
        return [
            {"symbol": "EURUSD", "kind": "forex", "payout_pct": 90.0},
            {"symbol": "GBPUSD", "kind": "forex", "payout_pct": 89.0},
            {"symbol": "BTCUSD", "kind": "crypto", "payout_pct": 91.0},
            {"symbol": "XAUUSD", "kind": "metal", "payout_pct": 88.0},
        ]
    
    async def place_order(
        self,
        *,
        product: str,
        amount: float,
        direction: str,
        timeframe: int,
        client_req_id: str
    ) -> Dict[str, Any]:
        """
        Mock emir yerleştirme
        Idempotent - aynı client_req_id için aynı order_id döner
        """
        await asyncio.sleep(0.1 + random.random() * 0.1)  # 100-200ms gecikme
        
        # client_req_id'den deterministik order_id üret
        order_id = f"MOCK-{hash(client_req_id) % 1000000:06d}"
        
        return {
            "order_id": order_id,
            "client_req_id": client_req_id,
            "ts_open_ms": int(time.time() * 1000)
        }
    
    async def confirm_order(self, order_id: str) -> Dict[str, Any]:
        """
        Mock sonuç - basit win/lose simülasyonu
        %45-55 arası rastgele (uzun vadede %50'ye yakın)
        """
        await asyncio.sleep(0.05 + random.random() * 0.1)
        
        # Basit win/lose simülasyonu
        win = random.random() > 0.48  # Hafif kazanma eğilimi
        pnl = 0.9 if win else -1.0
        
        return {
            "order_id": order_id,
            "status": "win" if win else "lose",
            "pnl": pnl,
            "ts_close_ms": int(time.time() * 1000) + 60_000,
            "latency_ms": int((0.1 + random.random() * 0.1) * 1000)
        }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Mock iptal"""
        await asyncio.sleep(0.05)
        return {"order_id": order_id, "status": "canceled"}
    
    async def heartbeat(self) -> None:
        """Mock heartbeat"""
        await asyncio.sleep(0.01)
    
    async def close(self) -> None:
        """Bağlantıyı kapat"""
        self._logged_in = False
        self._access_token = None
