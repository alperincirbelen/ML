from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class ProviderVote:
    pid: int
    vote: int  # -1, 0, +1
    score: float
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderContext:
    product: str
    timeframe: int
    payout: float


class StrategyProvider:
    """Base interface for strategy providers working on list-of-bars.

    Bars format: List[Dict[str, float]] with keys: ts, open, high, low, close, volume
    """

    def __init__(self, pid: int, params: Optional[Dict[str, Any]] = None):
        self.pid = pid
        self.params = params or {}

    def warmup_bars(self) -> int:
        raise NotImplementedError

    def evaluate(self, bars: List[Dict[str, float]], ctx: ProviderContext) -> Optional[ProviderVote]:
        raise NotImplementedError
