"""
Connector interface - Protocol definition
Parça 6 - Bağlayıcı sözleşmesi
"""

from typing import Protocol, List, Dict, Any, Optional


class Connector(Protocol):
    """
    Bağlayıcı arayüzü - tüm connector'lar bu sözleşmeyi uygular
    Sadece izinli/resmî API uçları kullanılır
    """
    
    account_id: str
    
    async def login(
        self, username: str, password: str, otp: Optional[str] = None
    ) -> None:
        """Oturum aç - 2FA/OTP kullanıcı etkileşimi gerektirir"""
        ...
    
    async def refresh_token(self) -> None:
        """Oturum token'ını yenile"""
        ...
    
    async def get_candles(
        self, 
        product: str, 
        timeframe: int, 
        n: int = 200,
        until_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Mum verilerini getir
        Returns: [{"ts_ms", "open", "high", "low", "close", "volume"}, ...]
        """
        ...
    
    async def get_current_win_rate(self, product: str) -> float:
        """
        Güncel payout/win rate getir (%)
        Returns: 0-100 arası değer
        """
        ...
    
    async def get_quote(self, product: str) -> Dict[str, Any]:
        """
        Anlık fiyat teklifi
        Returns: {"ts", "bid", "ask", "mid"}
        """
        ...
    
    async def get_instruments(self) -> List[Dict[str, Any]]:
        """
        Mevcut ürünler listesi
        Returns: [{"symbol", "kind", "payout_pct"}, ...]
        """
        ...
    
    async def place_order(
        self,
        *,
        product: str,
        amount: float,
        direction: str,  # 'call' or 'put'
        timeframe: int,
        client_req_id: str  # Idempotency key
    ) -> Dict[str, Any]:
        """
        Emir yerleştir - idempotent
        Returns: {"order_id", "client_req_id", "ts_open_ms"}
        """
        ...
    
    async def confirm_order(self, order_id: str) -> Dict[str, Any]:
        """
        Emir sonucunu kontrol et / onayla
        Returns: {"order_id", "status", "pnl", "ts_close_ms", "latency_ms"}
        """
        ...
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Emir iptali (platform destekliyorsa)
        Returns: {"order_id", "status"}
        """
        ...
    
    async def heartbeat(self) -> None:
        """Kalp atışı - oturum canlılığı kontrolü"""
        ...
    
    async def close(self) -> None:
        """Bağlantıyı kapat"""
        ...
