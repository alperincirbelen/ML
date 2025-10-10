"""
Base Strategy Class
Tüm işlem stratejileri için temel sınıf
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

from ..market_connector.base_connector import MarketData, TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    """Strateji konfigürasyonu"""
    name: str
    enabled: bool = True
    risk_per_trade: float = 1.0  # Yüzde
    max_concurrent_trades: int = 3
    min_confidence: float = 0.6  # Minimum güven seviyesi
    expiry_time: int = 60  # Saniye
    symbols: List[str] = None
    parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        if self.parameters is None:
            self.parameters = {}


@dataclass
class StrategyState:
    """Strateji durumu"""
    active_signals: int = 0
    total_signals: int = 0
    successful_signals: int = 0
    last_signal_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """Başarı oranı"""
        if self.total_signals == 0:
            return 0.0
        return self.successful_signals / self.total_signals
    
    @property
    def win_rate_percentage(self) -> float:
        """Kazanma oranı yüzdesi"""
        return self.success_rate * 100


class BaseStrategy(ABC):
    """
    Temel strateji sınıfı
    Tüm işlem stratejileri bu sınıftan türetilmelidir
    """
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.state = StrategyState()
        self.market_data_history: Dict[str, List[MarketData]] = {}
        self.is_active = False
        self._last_prices: Dict[str, float] = {}
        
        logger.info(f"Strateji başlatıldı: {self.config.name}")
    
    @abstractmethod
    async def analyze(self, market_data: MarketData) -> Optional[TradeSignal]:
        """
        Piyasa verisi analizi ve sinyal üretimi
        Args:
            market_data: Güncel piyasa verisi
        Returns: İşlem sinyali veya None
        """
        pass
    
    @abstractmethod
    def get_required_history_length(self) -> int:
        """
        Analiz için gereken geçmiş veri sayısı
        Returns: Minimum gerekli bar sayısı
        """
        pass
    
    async def update_market_data(self, market_data: MarketData) -> Optional[TradeSignal]:
        """
        Piyasa verisi güncelleme ve analiz
        Args:
            market_data: Yeni piyasa verisi
        Returns: Üretilen sinyal (varsa)
        """
        try:
            # Strateji aktif değilse sinyal üretme
            if not self.is_active or not self.config.enabled:
                return None
            
            # Sembol kontrolü
            if market_data.symbol not in self.config.symbols:
                return None
            
            # Geçmiş verilere ekle
            if market_data.symbol not in self.market_data_history:
                self.market_data_history[market_data.symbol] = []
            
            self.market_data_history[market_data.symbol].append(market_data)
            
            # Geçmiş veri sınırını koru
            max_history = max(self.get_required_history_length() * 2, 100)
            if len(self.market_data_history[market_data.symbol]) > max_history:
                self.market_data_history[market_data.symbol] = \
                    self.market_data_history[market_data.symbol][-max_history:]
            
            # Son fiyatı güncelle
            self._last_prices[market_data.symbol] = market_data.last
            
            # Yeterli veri var mı kontrol et
            if len(self.market_data_history[market_data.symbol]) < self.get_required_history_length():
                return None
            
            # Maksimum eşzamanlı işlem kontrolü
            if self.state.active_signals >= self.config.max_concurrent_trades:
                return None
            
            # Analiz yap
            signal = await self.analyze(market_data)
            
            # Sinyal doğrulama
            if signal and self._validate_signal(signal):
                self.state.total_signals += 1
                self.state.active_signals += 1
                self.state.last_signal_time = datetime.utcnow()
                
                logger.info(f"Sinyal üretildi: {signal.symbol} {signal.direction} "
                           f"(Güven: {signal.confidence:.2f})")
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Strateji güncelleme hatası ({self.config.name}): {e}")
            return None
        finally:
            self.state.last_update_time = datetime.utcnow()
    
    def _validate_signal(self, signal: TradeSignal) -> bool:
        """
        Sinyal doğrulama
        Args:
            signal: Doğrulanacak sinyal
        Returns: Geçerli ise True
        """
        try:
            # Temel kontroller
            if not signal.symbol or signal.symbol not in self.config.symbols:
                return False
            
            if signal.direction not in ["CALL", "PUT"]:
                return False
            
            if signal.confidence < self.config.min_confidence:
                logger.debug(f"Düşük güven seviyesi: {signal.confidence:.2f} < {self.config.min_confidence}")
                return False
            
            if signal.amount <= 0:
                return False
            
            if signal.expiry_time <= 0:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Sinyal doğrulama hatası: {e}")
            return False
    
    def get_market_data_df(self, symbol: str, limit: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Piyasa verilerini DataFrame olarak al
        Args:
            symbol: Sembol
            limit: Maksimum kayıt sayısı
        Returns: Pandas DataFrame veya None
        """
        try:
            if symbol not in self.market_data_history:
                return None
            
            data = self.market_data_history[symbol]
            if limit:
                data = data[-limit:]
            
            if not data:
                return None
            
            # DataFrame'e dönüştür
            df_data = []
            for md in data:
                df_data.append({
                    'timestamp': md.timestamp,
                    'bid': md.bid,
                    'ask': md.ask,
                    'last': md.last,
                    'volume': md.volume,
                    'spread': md.spread,
                    'mid_price': md.mid_price
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('timestamp', inplace=True)
            return df
            
        except Exception as e:
            logger.error(f"DataFrame oluşturma hatası: {e}")
            return None
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Teknik indikatörler hesapla
        Args:
            df: Fiyat verileri DataFrame
        Returns: İndikatörler eklenmiş DataFrame
        """
        try:
            if df is None or df.empty:
                return df
            
            # Basit hareketli ortalamalar
            df['sma_5'] = df['last'].rolling(window=5).mean()
            df['sma_10'] = df['last'].rolling(window=10).mean()
            df['sma_20'] = df['last'].rolling(window=20).mean()
            
            # Üstel hareketli ortalamalar
            df['ema_5'] = df['last'].ewm(span=5).mean()
            df['ema_10'] = df['last'].ewm(span=10).mean()
            df['ema_20'] = df['last'].ewm(span=20).mean()
            
            # RSI (Relative Strength Index)
            delta = df['last'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            ema12 = df['last'].ewm(span=12).mean()
            ema26 = df['last'].ewm(span=26).mean()
            df['macd'] = ema12 - ema26
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            df['bb_middle'] = df['last'].rolling(window=20).mean()
            bb_std = df['last'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            return df
            
        except Exception as e:
            logger.error(f"Teknik indikatör hesaplama hatası: {e}")
            return df
    
    async def on_trade_result(self, signal: TradeSignal, result: Dict[str, Any]) -> None:
        """
        İşlem sonucu bildirimi
        Args:
            signal: Orijinal sinyal
            result: İşlem sonucu
        """
        try:
            # Aktif sinyal sayısını azalt
            if self.state.active_signals > 0:
                self.state.active_signals -= 1
            
            # Başarılı işlem sayısını güncelle
            if result.get('success', False) or result.get('profit', 0) > 0:
                self.state.successful_signals += 1
                logger.info(f"Başarılı işlem: {signal.symbol} {signal.direction}")
            else:
                logger.info(f"Başarısız işlem: {signal.symbol} {signal.direction}")
            
        except Exception as e:
            logger.error(f"İşlem sonucu işleme hatası: {e}")
    
    def start(self) -> None:
        """Stratejiyi başlat"""
        self.is_active = True
        logger.info(f"Strateji başlatıldı: {self.config.name}")
    
    def stop(self) -> None:
        """Stratejiyi durdur"""
        self.is_active = False
        logger.info(f"Strateji durduruldu: {self.config.name}")
    
    def reset_state(self) -> None:
        """Strateji durumunu sıfırla"""
        self.state = StrategyState()
        self.market_data_history.clear()
        self._last_prices.clear()
        logger.info(f"Strateji durumu sıfırlandı: {self.config.name}")
    
    @property
    def status(self) -> Dict[str, Any]:
        """Strateji durumu"""
        return {
            'name': self.config.name,
            'active': self.is_active,
            'enabled': self.config.enabled,
            'active_signals': self.state.active_signals,
            'total_signals': self.state.total_signals,
            'success_rate': self.state.success_rate,
            'win_rate_percentage': self.state.win_rate_percentage,
            'last_signal_time': self.state.last_signal_time.isoformat() if self.state.last_signal_time else None,
            'last_update_time': self.state.last_update_time.isoformat() if self.state.last_update_time else None,
            'symbols': self.config.symbols,
            'min_confidence': self.config.min_confidence
        }