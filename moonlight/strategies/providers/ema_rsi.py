from __future__ import annotations
from typing import List, Dict, Optional
from dataclasses import dataclass

from ...strategies.base import StrategyProvider, ProviderContext, ProviderVote
from ...indicators.basic import ema, rsi


@dataclass
class _Params:
    ema_fast: int = 20
    ema_slow: int = 50
    rsi_len: int = 14
    rsi_up: float = 55.0
    rsi_dn: float = 45.0
    w1: float = 1.0
    w2: float = 0.7


class EMA_RSI(StrategyProvider):
    """Trend confirmation with EMA(fast/slow) + RSI filter.

    vote:
      +1 if ema_fast>ema_slow and RSI>rsi_up
      -1 if ema_fast<ema_slow and RSI<rsi_dn
      else 0

    score: weighted slope + normalized RSI distance from 50
    """

    def __init__(self, pid: int, params: Optional[Dict] = None):
        super().__init__(pid, params)
        p = _Params(**(params or {}))
        self.p = p

    def warmup_bars(self) -> int:
        return max(self.p.ema_slow, self.p.rsi_len) + 5

    def evaluate(self, bars: List[Dict[str, float]], ctx: ProviderContext) -> Optional[ProviderVote]:
        if len(bars) < self.warmup_bars():
            return None
        closes = [b["close"] for b in bars]
        e_fast = ema(closes, self.p.ema_fast)
        e_slow = ema(closes, self.p.ema_slow)
        r = rsi(closes, self.p.rsi_len)
        i_last = len(closes) - 1
        e_fast_last = e_fast[i_last]
        e_slow_last = e_slow[i_last]
        r_last = r[i_last]
        if e_fast_last is None or e_slow_last is None or r_last is None:
            return None
        vote = 0
        if e_fast_last > e_slow_last and r_last > self.p.rsi_up:
            vote = 1
        elif e_fast_last < e_slow_last and r_last < self.p.rsi_dn:
            vote = -1
        if vote == 0:
            return ProviderVote(pid=self.pid, vote=0, score=0.0, meta={"reason": "no-trend/weak-rsi"})
        # slope of ema_fast over last 3 bars (relative)
        def _rel(x0: float, x1: float) -> float:
            denom = x0 if abs(x0) > 1e-9 else (1e-9 if x0 >= 0 else -1e-9)
            return (x1 - x0) / denom

        last3 = [v for v in e_fast[-3:] if v is not None]
        slope = 0.0
        if len(last3) == 3:
            slope = _rel(last3[0], last3[-1])
        r_comp = (r_last - 50.0) / 50.0
        score = float(self.p.w1 * slope + self.p.w2 * r_comp)
        return ProviderVote(pid=self.pid, vote=vote, score=score, meta={"ema_fast": e_fast_last, "ema_slow": e_slow_last, "rsi": r_last})
