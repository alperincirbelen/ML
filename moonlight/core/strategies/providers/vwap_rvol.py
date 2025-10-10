"""
VWAP Reclaim + RVOL Strategy

Parça 13/29 - Strateji ID: 15-20 (varyantları)
Kategori: Volume + Trend
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from ..base import StrategyProvider, ProviderConfig, ProviderContext, ProviderVote
from ..registry import register
from ...indicators.basic import vwap
from ...indicators.advanced import rvol


@register(pid=15, metadata={
    "name": "VWAP Reclaim + RVOL",
    "group": "volume",
    "description": "VWAP geri kazanımı + hacim doğrulaması"
})
class VWAPReclaimRVOL(StrategyProvider):
    """
    VWAP Reclaim + RVOL Stratejisi
    
    Mantık:
    - Fiyat VWAP altından üstüne reclaim ve RVOL > threshold → CALL
    - Fiyat VWAP üstünden altına düşme ve RVOL > threshold → PUT
    
    Skor: Reclaim gücü + RVOL normalize kombinasyonu
    """
    
    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg
        p = cfg.params
        
        self.rvol_lb = p.get('rvol_lb', 20)
        self.rvol_thr = p.get('rvol_thr', 1.3)
        self.alpha = p.get('alpha', 1.0)  # Reclaim ağırlığı
        self.beta = p.get('beta', 0.5)    # RVOL ağırlığı
        self.min_dist = p.get('min_dist_vwap', 0.001)  # Minimum VWAP mesafesi
    
    def warmup_bars(self) -> int:
        return max(20, self.rvol_lb) + 5
    
    def evaluate(self, df: pd.DataFrame, feats: Dict[str, Any], 
                ctx: ProviderContext) -> Optional[ProviderVote]:
        # Warm-up kontrolü
        if len(df) < self.warmup_bars():
            return None
        
        high = df['high']
        low = df['low']
        close = df['close']
        volume = df['volume']
        
        # VWAP hesapla
        vwap_val = vwap(high, low, close, volume)
        
        # RVOL hesapla
        rvol_val = rvol(volume, self.rvol_lb)
        
        # Son değerler ve önceki
        if len(close) < 2 or len(vwap_val) < 2:
            return None
        
        close_now = close.iloc[-1]
        close_prev = close.iloc[-2]
        vwap_now = vwap_val.iloc[-1]
        vwap_prev = vwap_val.iloc[-2]
        rvol_now = rvol_val.iloc[-1]
        
        # NaN kontrolü
        if any(pd.isna([close_now, close_prev, vwap_now, vwap_prev, rvol_now])):
            return None
        
        # Reclaim tespiti
        reclaim_up = close_prev < vwap_prev and close_now > vwap_now
        reclaim_dn = close_prev > vwap_prev and close_now < vwap_now
        
        vote = 0
        
        # CALL sinyali
        if reclaim_up and rvol_now > self.rvol_thr:
            dist = abs(close_now - vwap_now) / vwap_now
            if dist >= self.min_dist:
                vote = +1
        
        # PUT sinyali
        elif reclaim_dn and rvol_now > self.rvol_thr:
            dist = abs(close_now - vwap_now) / vwap_now
            if dist >= self.min_dist:
                vote = -1
        
        # Sinyal yoksa
        if vote == 0:
            return ProviderVote(
                pid=self.cfg.id,
                vote=0,
                score=0.0,
                meta={"vwap": vwap_now, "rvol": rvol_now, "reclaim": False}
            )
        
        # Skor hesapla
        reclaim_strength = abs(close_now - vwap_now) / vwap_now
        rvol_excess = rvol_now - 1.0
        score = self.alpha * reclaim_strength + self.beta * rvol_excess
        
        return ProviderVote(
            pid=self.cfg.id,
            vote=vote,
            score=float(score),
            meta={
                "vwap": vwap_now,
                "close": close_now,
                "rvol": rvol_now,
                "reclaim_strength": reclaim_strength,
                "vote_reason": "vwap_reclaim_up" if vote > 0 else "vwap_reclaim_dn"
            }
        )


# Varyantlar (farklı RVOL eşikleri)
@register(pid=16, metadata={"name": "VWAP+RVOL (1.15)", "group": "volume"})
class VWAPReclaimRVOL_115(VWAPReclaimRVOL):
    def __init__(self, cfg: ProviderConfig):
        super().__init__(cfg)
        self.rvol_thr = 1.15


@register(pid=17, metadata={"name": "VWAP+RVOL (1.2)", "group": "volume"})
class VWAPReclaimRVOL_120(VWAPReclaimRVOL):
    def __init__(self, cfg: ProviderConfig):
        super().__init__(cfg)
        self.rvol_thr = 1.2


@register(pid=18, metadata={"name": "VWAP+RVOL (1.5)", "group": "volume"})
class VWAPReclaimRVOL_150(VWAPReclaimRVOL):
    def __init__(self, cfg: ProviderConfig):
        super().__init__(cfg)
        self.rvol_thr = 1.5
