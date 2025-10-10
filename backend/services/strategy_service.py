"""Strategy Service - Execute trading strategies"""
from typing import Dict, List
from datetime import datetime
from models.market_data import MarketData
from models.indicator import Indicator, IndicatorType, IndicatorConfig
from models.strategy import Strategy, StrategyConfig, StrategyResult, StrategyType
from models.signal import Signal, SignalType, SignalStrength
from services.indicator_service import IndicatorService
import uuid


class StrategyService:
    @staticmethod
    def get_predefined_strategies() -> List[Dict]:
        """
        Get list of predefined trading strategies
        """
        return [
            {
                "id": "trend_follow_ema",
                "name": "EMA Crossover",
                "description": "Buy when fast EMA crosses above slow EMA, sell on opposite",
                "type": StrategyType.TREND_FOLLOWING,
                "indicators": ["EMA_9", "EMA_21"],
                "parameters": {
                    "fast_period": 9,
                    "slow_period": 21
                }
            },
            {
                "id": "rsi_oversold",
                "name": "RSI Oversold/Overbought",
                "description": "Buy when RSI < 30, sell when RSI > 70",
                "type": StrategyType.MEAN_REVERSION,
                "indicators": ["RSI_14"],
                "parameters": {
                    "oversold": 30,
                    "overbought": 70,
                    "period": 14
                }
            },
            {
                "id": "macd_signal",
                "name": "MACD Signal Cross",
                "description": "Buy when MACD crosses above signal line, sell on opposite",
                "type": StrategyType.MOMENTUM,
                "indicators": ["MACD_12_26_9"],
                "parameters": {
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9
                }
            },
            {
                "id": "bollinger_breakout",
                "name": "Bollinger Band Breakout",
                "description": "Buy when price breaks above upper band, sell below lower band",
                "type": StrategyType.BREAKOUT,
                "indicators": ["BB_20_2.0"],
                "parameters": {
                    "period": 20,
                    "std_dev": 2.0
                }
            }
        ]
    
    @staticmethod
    def execute_ema_crossover(
        market_data: MarketData,
        fast_period: int = 9,
        slow_period: int = 21
    ) -> Signal:
        """
        Execute EMA Crossover strategy
        """
        # Calculate EMAs
        fast_ema_config = IndicatorConfig(type=IndicatorType.EMA, period=fast_period)
        slow_ema_config = IndicatorConfig(type=IndicatorType.EMA, period=slow_period)
        
        fast_ema = IndicatorService.calculate_indicator(market_data, fast_ema_config)
        slow_ema = IndicatorService.calculate_indicator(market_data, slow_ema_config)
        
        # Get latest values
        fast_val = fast_ema.values[-1]
        slow_val = slow_ema.values[-1]
        prev_fast = fast_ema.values[-2] if len(fast_ema.values) > 1 else fast_val
        prev_slow = slow_ema.values[-2] if len(slow_ema.values) > 1 else slow_val
        
        current_price = market_data.data[-1].close
        
        # Determine signal
        signal_type = SignalType.HOLD
        confidence = 0.5
        strength = SignalStrength.WEAK
        
        # Bullish crossover
        if prev_fast <= prev_slow and fast_val > slow_val:
            signal_type = SignalType.BUY
            diff_percent = ((fast_val - slow_val) / slow_val) * 100
            confidence = min(0.5 + (diff_percent * 10), 0.95)
            strength = SignalStrength.STRONG if confidence > 0.8 else SignalStrength.MODERATE
        
        # Bearish crossover
        elif prev_fast >= prev_slow and fast_val < slow_val:
            signal_type = SignalType.SELL
            diff_percent = ((slow_val - fast_val) / fast_val) * 100
            confidence = min(0.5 + (diff_percent * 10), 0.95)
            strength = SignalStrength.STRONG if confidence > 0.8 else SignalStrength.MODERATE
        
        return Signal(
            id=str(uuid.uuid4()),
            symbol=market_data.symbol,
            timeframe=market_data.timeframe.value,
            signal_type=signal_type,
            strength=strength,
            confidence=round(confidence, 3),
            price=current_price,
            strategy_name="EMA Crossover",
            indicators={
                f"EMA_{fast_period}": fast_val,
                f"EMA_{slow_period}": slow_val
            }
        )
    
    @staticmethod
    def execute_rsi_strategy(
        market_data: MarketData,
        period: int = 14,
        oversold: float = 30,
        overbought: float = 70
    ) -> Signal:
        """
        Execute RSI Oversold/Overbought strategy
        """
        # Calculate RSI
        rsi_config = IndicatorConfig(type=IndicatorType.RSI, period=period)
        rsi = IndicatorService.calculate_indicator(market_data, rsi_config)
        
        rsi_val = rsi.values[-1]
        current_price = market_data.data[-1].close
        
        # Determine signal
        signal_type = SignalType.HOLD
        confidence = 0.5
        strength = SignalStrength.WEAK
        
        if rsi_val < oversold:
            signal_type = SignalType.BUY
            confidence = 0.5 + ((oversold - rsi_val) / oversold) * 0.4
            strength = SignalStrength.STRONG if rsi_val < 20 else SignalStrength.MODERATE
        
        elif rsi_val > overbought:
            signal_type = SignalType.SELL
            confidence = 0.5 + ((rsi_val - overbought) / (100 - overbought)) * 0.4
            strength = SignalStrength.STRONG if rsi_val > 80 else SignalStrength.MODERATE
        
        return Signal(
            id=str(uuid.uuid4()),
            symbol=market_data.symbol,
            timeframe=market_data.timeframe.value,
            signal_type=signal_type,
            strength=strength,
            confidence=round(confidence, 3),
            price=current_price,
            strategy_name="RSI Strategy",
            indicators={
                f"RSI_{period}": rsi_val
            }
        )
    
    @staticmethod
    def execute_strategy(
        strategy_id: str,
        market_data: MarketData,
        parameters: Dict = None
    ) -> Signal:
        """
        Execute a strategy by ID
        """
        params = parameters or {}
        
        if strategy_id == "trend_follow_ema":
            return StrategyService.execute_ema_crossover(
                market_data,
                params.get("fast_period", 9),
                params.get("slow_period", 21)
            )
        
        elif strategy_id == "rsi_oversold":
            return StrategyService.execute_rsi_strategy(
                market_data,
                params.get("period", 14),
                params.get("oversold", 30),
                params.get("overbought", 70)
            )
        
        else:
            raise ValueError(f"Unknown strategy: {strategy_id}")
