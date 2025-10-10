"""
Base Market Connector
Tüm piyasa bağlantı sınıfları için temel sınıf
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """Piyasa verisi veri yapısı"""
    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    last: float
    volume: float
    
    @property
    def spread(self) -> float:
        """Bid-Ask spread"""
        return self.ask - self.bid
    
    @property
    def mid_price(self) -> float:
        """Orta fiyat"""
        return (self.bid + self.ask) / 2


@dataclass
class TradeSignal:
    """İşlem sinyali veri yapısı"""
    symbol: str
    direction: str  # "CALL" veya "PUT"
    expiry_time: int  # saniye
    amount: float
    confidence: float  # 0.0 - 1.0
    timestamp: datetime
    strategy_name: str


class BaseConnector(ABC):
    """
    Temel piyasa bağlantı sınıfı
    Tüm broker/platform bağlantıları bu sınıftan türetilmelidir
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_connected = False
        self.is_authenticated = False
        self.callbacks: Dict[str, List[Callable]] = {
            'market_data': [],
            'trade_result': [],
            'connection_status': [],
            'error': []
        }
        self._running = False
        
    @abstractmethod
    async def connect(self) -> bool:
        """
        Platform/broker'a bağlan
        Returns: Bağlantı başarılı ise True
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Bağlantıyı kapat"""
        pass
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """
        Kimlik doğrulama
        Args:
            credentials: {"email": "...", "password": "..."}
        Returns: Kimlik doğrulama başarılı ise True
        """
        pass
    
    @abstractmethod
    async def subscribe_market_data(self, symbols: List[str]) -> bool:
        """
        Piyasa verisi aboneliği
        Args:
            symbols: Takip edilecek sembol listesi
        Returns: Abonelik başarılı ise True
        """
        pass
    
    @abstractmethod
    async def place_trade(self, signal: TradeSignal) -> Dict[str, Any]:
        """
        İşlem aç
        Args:
            signal: İşlem sinyali
        Returns: İşlem sonucu
        """
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """
        Hesap bakiyesi
        Returns: {"balance": 1000.0, "demo": True}
        """
        pass
    
    @abstractmethod
    async def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        İşlem geçmişi
        Args:
            limit: Maksimum kayıt sayısı
        Returns: İşlem listesi
        """
        pass
    
    def add_callback(self, event_type: str, callback: Callable) -> None:
        """
        Olay dinleyici ekle
        Args:
            event_type: 'market_data', 'trade_result', 'connection_status', 'error'
            callback: Çağrılacak fonksiyon
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
        else:
            logger.warning(f"Bilinmeyen olay türü: {event_type}")
    
    def remove_callback(self, event_type: str, callback: Callable) -> None:
        """Olay dinleyici kaldır"""
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)
    
    async def _emit_event(self, event_type: str, data: Any) -> None:
        """Olay yayınla"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Callback hatası ({event_type}): {e}")
    
    async def start(self) -> None:
        """Bağlantıyı başlat"""
        if self._running:
            logger.warning("Bağlantı zaten çalışıyor")
            return
            
        self._running = True
        logger.info("Market connector başlatılıyor...")
        
        try:
            # Bağlan
            if not await self.connect():
                raise Exception("Bağlantı başarısız")
            
            await self._emit_event('connection_status', {'connected': True})
            logger.info("Market connector başarıyla başlatıldı")
            
        except Exception as e:
            self._running = False
            logger.error(f"Market connector başlatma hatası: {e}")
            await self._emit_event('error', {'error': str(e)})
            raise
    
    async def stop(self) -> None:
        """Bağlantıyı durdur"""
        if not self._running:
            return
            
        self._running = False
        logger.info("Market connector durduruluyor...")
        
        try:
            await self.disconnect()
            await self._emit_event('connection_status', {'connected': False})
            logger.info("Market connector durduruldu")
            
        except Exception as e:
            logger.error(f"Market connector durdurma hatası: {e}")
    
    @property
    def status(self) -> Dict[str, Any]:
        """Bağlantı durumu"""
        return {
            'running': self._running,
            'connected': self.is_connected,
            'authenticated': self.is_authenticated,
            'config': self.config.get('name', 'Unknown')
        }