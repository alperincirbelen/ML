"""
Simple Trend Strategy
Basit trend takip stratejisi - demo amaçlı
"""

import logging
from typing import Optional
from datetime import datetime

from .base_strategy import BaseStrategy, StrategyConfig
from ..market_connector.base_connector import MarketData, TradeSignal

logger = logging.getLogger(__name__)


class SimpleTrendStrategy(BaseStrategy):
    """
    Basit Trend Stratejisi
    
    Strateji mantığı:
    - Kısa vadeli EMA (5) ve uzun vadeli EMA (20) kullanır
    - EMA5 > EMA20 ise CALL sinyali
    - EMA5 < EMA20 ise PUT sinyali
    - RSI aşırı alım/satım seviyelerini kontrol eder
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strateji parametreleri
        self.ema_short_period = config.parameters.get('ema_short_period', 5)
        self.ema_long_period = config.parameters.get('ema_long_period', 20)
        self.rsi_period = config.parameters.get('rsi_period', 14)
        self.rsi_oversold = config.parameters.get('rsi_oversold', 30)
        self.rsi_overbought = config.parameters.get('rsi_overbought', 70)
        self.min_trend_strength = config.parameters.get('min_trend_strength', 0.0001)
        
        logger.info(f"SimpleTrendStrategy başlatıldı: {config.name}")
    
    def get_required_history_length(self) -> int:
        """Gerekli geçmiş veri sayısı"""
        return max(self.ema_long_period, self.rsi_period) + 5
    
    async def analyze(self, market_data: MarketData) -> Optional[TradeSignal]:
        """
        Piyasa analizi ve sinyal üretimi
        Args:
            market_data: Güncel piyasa verisi
        Returns: İşlem sinyali veya None
        """
        try:
            # Yeterli veri kontrolü
            if len(self.market_data_history[market_data.symbol]) < self.get_required_history_length():
                return None
            
            # DataFrame'e dönüştür
            df = self.get_market_data_df(market_data.symbol)
            if df is None or df.empty:
                return None
            
            # Teknik indikatörleri hesapla
            df = self.calculate_technical_indicators(df)
            
            # Son değerleri al
            current_data = df.iloc[-1]
            previous_data = df.iloc[-2] if len(df) > 1 else current_data
            
            # EMA değerleri
            ema_short = current_data.get('ema_5')
            ema_long = current_data.get('ema_20')
            prev_ema_short = previous_data.get('ema_5')
            prev_ema_long = previous_data.get('ema_20')
            
            # RSI değeri
            rsi = current_data.get('rsi')
            
            # Değerlerin geçerli olduğunu kontrol et
            if any(pd.isna(val) for val in [ema_short, ema_long, rsi, prev_ema_short, prev_ema_long]):
                return None
            
            # Trend yönünü belirle
            trend_direction = None
            confidence = 0.0
            
            # CALL sinyali koşulları
            if (ema_short > ema_long and 
                prev_ema_short <= prev_ema_long and  # Crossover
                rsi < self.rsi_overbought and
                abs(ema_short - ema_long) > self.min_trend_strength):
                
                trend_direction = "CALL"
                
                # Güven seviyesi hesaplama
                trend_strength = abs(ema_short - ema_long) / market_data.last
                rsi_factor = (70 - rsi) / 40  # RSI ne kadar düşükse o kadar iyi
                confidence = min(0.9, 0.5 + trend_strength * 1000 + rsi_factor * 0.3)
            
            # PUT sinyali koşulları
            elif (ema_short < ema_long and 
                  prev_ema_short >= prev_ema_long and  # Crossover
                  rsi > self.rsi_oversold and
                  abs(ema_short - ema_long) > self.min_trend_strength):
                
                trend_direction = "PUT"
                
                # Güven seviyesi hesaplama
                trend_strength = abs(ema_short - ema_long) / market_data.last
                rsi_factor = (rsi - 30) / 40  # RSI ne kadar yüksekse o kadar iyi
                confidence = min(0.9, 0.5 + trend_strength * 1000 + rsi_factor * 0.3)
            
            # Sinyal üret
            if trend_direction and confidence >= self.config.min_confidence:
                signal = TradeSignal(
                    symbol=market_data.symbol,
                    direction=trend_direction,
                    expiry_time=self.config.expiry_time,
                    amount=self.config.risk_per_trade,
                    confidence=confidence,
                    timestamp=datetime.utcnow(),
                    strategy_name=self.config.name
                )
                
                logger.info(f"Sinyal üretildi: {signal.symbol} {signal.direction} "
                           f"(Güven: {confidence:.3f}, EMA5: {ema_short:.5f}, "
                           f"EMA20: {ema_long:.5f}, RSI: {rsi:.1f})")
                
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"SimpleTrendStrategy analiz hatası: {e}")
            return None
    
    def get_strategy_info(self) -> dict:
        """Strateji bilgileri"""
        return {
            'name': self.config.name,
            'type': 'Trend Following',
            'description': 'EMA crossover ve RSI filtresi kullanan basit trend stratejisi',
            'parameters': {
                'ema_short_period': self.ema_short_period,
                'ema_long_period': self.ema_long_period,
                'rsi_period': self.rsi_period,
                'rsi_oversold': self.rsi_oversold,
                'rsi_overbought': self.rsi_overbought,
                'min_trend_strength': self.min_trend_strength,
                'min_confidence': self.config.min_confidence,
                'expiry_time': self.config.expiry_time
            },
            'symbols': self.config.symbols,
            'status': self.status
        }


# Pandas import'u için
try:
    import pandas as pd
except ImportError:
    logger.error("Pandas kütüphanesi gerekli - pip install pandas")
    pd = None