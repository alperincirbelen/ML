"""
EMA Crossover Strategy

Parça 13/29 - Strateji ID: 14
Kategori: Trend
"""

import pandas as pd
from typing import Optional, Dict, Any
from ..base import StrategyProvider, ProviderConfig, ProviderContext, ProviderVote
from ..registry import register
from ...indicators.basic import ema
from ...indicators.advanced import adx


@register(pid=14, metadata={
    "name": "EMA 9/21 Crossover",
    "group": "trend",
    "description": "Klasik EMA kesişim stratejisi"
})
class EMACrossover(StrategyProvider):
    """
    EMA 9/21 Crossover
    
    Mantık:
    - EMA9 yukarı keserse → CALL
    - EMA9 aşağı keserse → PUT
    - Confirm_bars ile whipsaw azaltma
    - ADX filtresi opsiyonel
    """
    
    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg
        p = cfg.params
        
        self.fast_len = p.get('fast_len', 9)
        self.slow_len = p.get('slow_len', 21)
        self.confirm_bars = p.get('confirm_bars', 1)
        self.use_adx = p.get('use_adx', True)
        self.adx_min = p.get('adx_min', 20)
    
    def warmup_bars(self) -> int:
        if self.use_adx:
            return max(self.slow_len, 14) + self.confirm_bars + 5
        return self.slow_len + self.confirm_bars + 5
    
    def evaluate(self, df: pd.DataFrame, feats: Dict[str, Any], 
                ctx: ProviderContext) -> Optional[ProviderVote]:
        # Warm-up
        if len(df) < self.warmup_bars():
            return None
        
        close = df['close']
        high = df['high']
        low = df['low']
        
        # EMA hesapla
        ema_fast = ema(close, self.fast_len)
        ema_slow = ema(close, self.slow_len)
        
        # Kesişim tespiti
        diff = ema_fast - ema_slow
        
        # Son değerler ve önceki
        if len(diff) < self.confirm_bars + 2:
            return None
        
        # Confirm bars kadar önce kesişim var mı?
        prev_idx = -(self.confirm_bars + 1)
        now_idx = -1
        
        diff_prev = diff.iloc[prev_idx]
        diff_now = diff.iloc[now_idx]
        
        # NaN kontrolü
        if pd.isna(diff_prev) or pd.isna(diff_now):
            return None
        
        # Kesişim tespiti
        cross_up = diff_prev <= 0 and diff_now > 0
        cross_dn = diff_prev >= 0 and diff_now < 0
        
        vote = 0
        if cross_up:
            vote = +1
        elif cross_dn:
            vote = -1
        
        # ADX filtresi
        if vote != 0 and self.use_adx:
            adx_val = adx(high, low, close, 14)
            adx_now = adx_val.iloc[-1]
            
            if pd.isna(adx_now) or adx_now < self.adx_min:
                vote = 0  # Trend zayıf, sinyal iptal
        
        if vote == 0:
            return ProviderVote(
                pid=self.cfg.id,
                vote=0,
                score=0.0,
                meta={
                    "ema_fast": ema_fast.iloc[-1],
                    "ema_slow": ema_slow.iloc[-1],
                    "diff": diff_now
                }
            )
        
        # Skor: Kesişim gücü (fark değişimi)
        slope = diff_now - diff_prev
        score = slope / max(1e-9, abs(close.iloc[-1]))  # Normalize
        
        return ProviderVote(
            pid=self.cfg.id,
            vote=vote,
            score=float(score),
            meta={
                "ema_fast": ema_fast.iloc[-1],
                "ema_slow": ema_slow.iloc[-1],
                "diff": diff_now,
                "slope": slope,
                "cross": "up" if vote > 0 else "down"
            }
        )
