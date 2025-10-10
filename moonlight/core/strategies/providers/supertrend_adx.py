"""
Supertrend + ADX Strategy

Parça 13/29 - Strateji ID: 25-30 (varyantları)
Kategori: Trend + Volatilite (Hybrid)
"""

import pandas as pd
from typing import Optional, Dict, Any
from ..base import StrategyProvider, ProviderConfig, ProviderContext, ProviderVote
from ..registry import register
from ...indicators.advanced import supertrend, adx


@register(pid=25, metadata={
    "name": "Supertrend + ADX",
    "group": "hybrid",
    "description": "Supertrend yön + ADX güç doğrulaması"
})
class SupertrendADX(StrategyProvider):
    """
    Supertrend + ADX Stratejisi
    
    Mantık:
    - Supertrend bullish ve ADX > threshold → CALL
    - Supertrend bearish ve ADX > threshold → PUT
    
    Skor: ADX gücü + fiyat-ST mesafesi kombinasyonu
    """
    
    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg
        p = cfg.params
        
        self.st_len = p.get('st_len', 10)
        self.st_mult = p.get('st_mult', 3.0)
        self.adx_len = p.get('adx_len', 14)
        self.adx_thr = p.get('adx_thr', 22)
    
    def warmup_bars(self) -> int:
        return max(self.st_len, self.adx_len) * 2 + 10
    
    def evaluate(self, df: pd.DataFrame, feats: Dict[str, Any], 
                ctx: ProviderContext) -> Optional[ProviderVote]:
        # Warm-up
        if len(df) < self.warmup_bars():
            return None
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Supertrend
        st_line, st_dir = supertrend(high, low, close, self.st_len, self.st_mult)
        
        # ADX
        adx_val = adx(high, low, close, self.adx_len)
        
        # Son değerler
        st_direction = st_dir.iloc[-1]
        adx_now = adx_val.iloc[-1]
        st_now = st_line.iloc[-1]
        close_now = close.iloc[-1]
        
        # NaN kontrolü
        if pd.isna(st_direction) or pd.isna(adx_now):
            return None
        
        # Vote
        vote = 0
        
        if st_direction == 1 and adx_now > self.adx_thr:
            vote = +1  # Bullish + güçlü trend
        elif st_direction == -1 and adx_now > self.adx_thr:
            vote = -1  # Bearish + güçlü trend
        
        if vote == 0:
            return ProviderVote(
                pid=self.cfg.id,
                vote=0,
                score=0.0,
                meta={"st_dir": int(st_direction), "adx": adx_now}
            )
        
        # Skor: ADX normalize + fiyat-ST mesafesi
        adx_norm = (adx_now - self.adx_thr) / 30.0  # 0-1 arası
        dist_to_st = (close_now - st_now) / close_now
        
        score = adx_norm + 0.5 * dist_to_st * st_direction
        
        return ProviderVote(
            pid=self.cfg.id,
            vote=vote,
            score=float(score),
            meta={
                "st_direction": int(st_direction),
                "adx": adx_now,
                "st_line": st_now,
                "close": close_now,
                "dist_pct": dist_to_st * 100
            }
        )


# Varyantlar (farklı ADX eşikleri)
@register(pid=26, metadata={"name": "ST+ADX (ADX20)", "group": "hybrid"})
class SupertrendADX_20(SupertrendADX):
    def __init__(self, cfg: ProviderConfig):
        super().__init__(cfg)
        self.adx_thr = 20


@register(pid=27, metadata={"name": "ST+ADX (ADX24)", "group": "hybrid"})
class SupertrendADX_24(SupertrendADX):
    def __init__(self, cfg: ProviderConfig):
        super().__init__(cfg)
        self.adx_thr = 24


@register(pid=28, metadata={"name": "ST+ADX (ADX26)", "group": "hybrid"})
class SupertrendADX_26(SupertrendADX):
    def __init__(self, cfg: ProviderConfig):
        super().__init__(cfg)
        self.adx_thr = 26
