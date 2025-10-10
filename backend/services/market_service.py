"""Market Data Service - Mock data generator for testing"""
import random
from datetime import datetime, timedelta
from typing import List
from models.market_data import OHLCV, MarketData, TimeFrame


class MarketService:
    @staticmethod
    def generate_mock_data(
        symbol: str,
        timeframe: TimeFrame = TimeFrame.M5,
        num_candles: int = 100,
        base_price: float = 50000.0,
        volatility: float = 0.02
    ) -> MarketData:
        """
        Generate realistic mock OHLCV data for testing
        """
        candles = []
        current_time = datetime.utcnow()
        current_price = base_price
        
        # Determine time delta based on timeframe
        time_deltas = {
            TimeFrame.M1: timedelta(minutes=1),
            TimeFrame.M5: timedelta(minutes=5),
            TimeFrame.M15: timedelta(minutes=15),
            TimeFrame.M30: timedelta(minutes=30),
            TimeFrame.H1: timedelta(hours=1),
            TimeFrame.H4: timedelta(hours=4),
            TimeFrame.D1: timedelta(days=1),
        }
        
        time_delta = time_deltas.get(timeframe, timedelta(minutes=5))
        
        for i in range(num_candles):
            timestamp = current_time - (time_delta * (num_candles - i))
            
            # Generate realistic price movements
            price_change = current_price * volatility * random.uniform(-1, 1)
            current_price += price_change
            
            # Generate OHLC from current price
            candle_volatility = current_price * volatility * 0.5
            open_price = current_price + random.uniform(-candle_volatility, candle_volatility)
            close_price = current_price + random.uniform(-candle_volatility, candle_volatility)
            
            high_price = max(open_price, close_price) + abs(random.uniform(0, candle_volatility))
            low_price = min(open_price, close_price) - abs(random.uniform(0, candle_volatility))
            
            # Generate volume
            volume = random.uniform(1000000, 5000000)
            
            candle = OHLCV(
                timestamp=timestamp,
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=round(volume, 2)
            )
            candles.append(candle)
        
        return MarketData(
            symbol=symbol,
            timeframe=timeframe,
            data=candles,
            last_updated=datetime.utcnow()
        )
    
    @staticmethod
    def get_latest_price(market_data: MarketData) -> float:
        """
        Get the latest closing price from market data
        """
        if not market_data.data:
            return 0.0
        return market_data.data[-1].close
