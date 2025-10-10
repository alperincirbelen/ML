from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class TimeFrame(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

class OHLCV(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class MarketData(BaseModel):
    symbol: str
    timeframe: TimeFrame
    data: List[OHLCV]
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class MarketDataCreate(BaseModel):
    symbol: str
    timeframe: TimeFrame = TimeFrame.M5
    num_candles: int = 100
