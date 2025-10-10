"""
Connector Protocol - Sözleşme Tanımı

Tüm connector'lar bu arayüzü uygulamalıdır
"""

from typing import Protocol, List, Dict, Any, Optional
from pydantic import BaseModel


class Candle(BaseModel):
    """Mum verisi"""
    ts_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


class Quote(BaseModel):
    """Anlık fiyat"""
    ts_ms: int
    bid: float
    ask: float
    
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2


class OrderAck(BaseModel):
    """Emir onayı"""
    order_id: str
    client_req_id: str
    ts_open_ms: int
    status: str = "PENDING"
    expires_at_ms: Optional[int] = None


class OrderResult(BaseModel):
    """Emir sonucu"""
    order_id: str
    status: str  # win | lose | abort | canceled | push
    pnl: float
    ts_close_ms: int
    latency_ms: int


class Connector(Protocol):
    """
    Trading Connector Protocol
    
    Sorumluluklar:
    - Kimlik doğrulama ve oturum yönetimi
    - Piyasa verisi (mumlar, fiyatlar, payout)
    - Emir yerleştirme ve onaylama
    - İdempotency ve rate-limit uyumu
    
    Kısıtlar:
    - Yalnız izinli/resmî API'ler kullanılabilir
    - Anti-bot/2FA bypass yasaktır
    - TOS'a uyum zorunludur
    """
    
    account_id: str
    
    async def login(self, username: str, password: str, 
                    otp: Optional[str] = None) -> None:
        """
        Oturum aç
        
        Args:
            username: Kullanıcı adı veya e-posta
            password: Parola (keyring'den gelir)
            otp: 2FA/OTP kodu (kullanıcı manuel girer)
        
        Raises:
            AuthError: Kimlik doğrulama başarısız
            OtpRequiredError: OTP gerekli
        """
        ...
    
    async def refresh_token(self) -> None:
        """Oturum token'ını yenile"""
        ...
    
    async def get_candles(self, product: str, timeframe: int, n: int = 200,
                         until_ms: Optional[int] = None) -> List[Candle]:
        """
        Mumları getir
        
        Args:
            product: Sembol (ör. "EURUSD")
            timeframe: Dakika (1/5/15)
            n: Mum sayısı
            until_ms: Son zaman (None = şimdi)
        
        Returns:
            Zaman sıralı mum listesi
        """
        ...
    
    async def get_current_win_rate(self, product: str) -> float:
        """
        Güncel payout oranı
        
        Returns:
            Payout yüzdesi (0-100 arası, örn. 90.0)
        """
        ...
    
    async def get_quote(self, product: str) -> Quote:
        """Anlık fiyat teklifi"""
        ...
    
    async def place_order(self, *, product: str, amount: float, direction: str,
                         timeframe: int, client_req_id: str) -> OrderAck:
        """
        Emir yerleştir (idempotent)
        
        Args:
            product: Sembol
            amount: Tutar
            direction: 'call' (+1) veya 'put' (-1)
            timeframe: Vade (dakika)
            client_req_id: Tekil istek ID (idempotency key)
        
        Returns:
            OrderAck: Emir onayı
            
        Raises:
            TemporaryError: 429/5xx, yeniden denenebilir
            PermanentError: İzin dışı, iş kuralı reddi
        """
        ...
    
    async def confirm_order(self, order_id: str) -> OrderResult:
        """
        Emir sonucunu kontrol et (polling için)
        
        Returns:
            OrderResult: Sonuç varsa, yoksa None
        """
        ...
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Emri iptal et (platform destekliyorsa)"""
        ...
    
    async def heartbeat(self) -> None:
        """Oturum canlılık testi"""
        ...
    
    async def close(self) -> None:
        """Bağlantıyı kapat, kaynakları temizle"""
        ...
