"""Indicator Service - Calculate technical indicators"""
from typing import List, Dict, Any
from models.market_data import MarketData, OHLCV
from models.indicator import Indicator, IndicatorType, IndicatorConfig
from utils.technical_indicators import (
    calculate_sma,
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_stochastic,
)


class IndicatorService:
    @staticmethod
    def calculate_indicator(
        market_data: MarketData,
        indicator_config: IndicatorConfig
    ) -> Indicator:
        """
        Calculate a single indicator based on configuration
        """
        close_prices = [candle.close for candle in market_data.data]
        high_prices = [candle.high for candle in market_data.data]
        low_prices = [candle.low for candle in market_data.data]
        
        indicator_type = indicator_config.type
        period = indicator_config.period
        params = indicator_config.params or {}
        
        if indicator_type == IndicatorType.SMA:
            values = calculate_sma(close_prices, period)
            name = f"SMA_{period}"
            
        elif indicator_type == IndicatorType.EMA:
            values = calculate_ema(close_prices, period)
            name = f"EMA_{period}"
            
        elif indicator_type == IndicatorType.RSI:
            values = calculate_rsi(close_prices, period)
            name = f"RSI_{period}"
            
        elif indicator_type == IndicatorType.MACD:
            fast = params.get("fast_period", 12)
            slow = params.get("slow_period", 26)
            signal = params.get("signal_period", 9)
            macd_line, signal_line, histogram = calculate_macd(close_prices, fast, slow, signal)
            values = macd_line  # Return MACD line as main value
            name = f"MACD_{fast}_{slow}_{signal}"
            
        elif indicator_type == IndicatorType.BOLLINGER_BANDS:
            std_dev = params.get("std_dev", 2.0)
            upper, middle, lower = calculate_bollinger_bands(close_prices, period, std_dev)
            values = middle  # Return middle band as main value
            name = f"BB_{period}_{std_dev}"
            
        elif indicator_type == IndicatorType.ATR:
            values = calculate_atr(high_prices, low_prices, close_prices, period)
            name = f"ATR_{period}"
            
        elif indicator_type == IndicatorType.STOCHASTIC:
            k_period = params.get("k_period", 14)
            d_period = params.get("d_period", 3)
            k_values, d_values = calculate_stochastic(high_prices, low_prices, close_prices, k_period, d_period)
            values = k_values  # Return %K as main value
            name = f"STOCH_{k_period}_{d_period}"
            
        else:
            raise ValueError(f"Unknown indicator type: {indicator_type}")
        
        return Indicator(
            name=name,
            type=indicator_type,
            values=values,
            config=indicator_config
        )
    
    @staticmethod
    def calculate_multiple_indicators(
        market_data: MarketData,
        configs: List[IndicatorConfig]
    ) -> Dict[str, Indicator]:
        """
        Calculate multiple indicators at once
        """
        indicators = {}
        for config in configs:
            indicator = IndicatorService.calculate_indicator(market_data, config)
            indicators[indicator.name] = indicator
        return indicators
    
    @staticmethod
    def get_latest_value(indicator: Indicator) -> float:
        """
        Get the most recent indicator value
        """
        if not indicator.values:
            return 0.0
        return indicator.values[-1]
