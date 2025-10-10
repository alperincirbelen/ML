from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from enum import Enum

class IndicatorType(str, Enum):
    SMA = "sma"
    EMA = "ema"
    RSI = "rsi"
    MACD = "macd"
    BOLLINGER_BANDS = "bollinger_bands"
    ATR = "atr"
    STOCHASTIC = "stochastic"

class IndicatorConfig(BaseModel):
    type: IndicatorType
    period: int = 14
    params: Optional[Dict[str, Any]] = None

class Indicator(BaseModel):
    name: str
    type: IndicatorType
    values: List[float]
    config: IndicatorConfig
