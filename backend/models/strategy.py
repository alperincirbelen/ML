from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class StrategyType(str, Enum):
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    BREAKOUT = "breakout"
    CUSTOM = "custom"

class StrategyConfig(BaseModel):
    name: str
    type: StrategyType
    indicators: List[str]
    parameters: Dict[str, Any]
    rules: Dict[str, Any]

class StrategyResult(BaseModel):
    strategy_name: str
    timestamp: datetime
    signal: Optional[str] = None  # "BUY", "SELL", "HOLD"
    confidence: float = 0.0
    indicators_used: List[str]
    metadata: Optional[Dict[str, Any]] = None

class Strategy(BaseModel):
    id: str
    name: str
    description: str
    type: StrategyType
    config: StrategyConfig
    is_active: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
