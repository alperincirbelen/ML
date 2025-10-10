"""
EMA Trend + RSI Strategy
Parça 13, 29 - ID: 5
"""

import pandas as pd
from ..base import ProviderConfig, ProviderContext
from ..registry import register
from ...ensemble.models import ProviderVote
from ...indicators.basic import ema, rsi


@register(5)
class EMA_RSI:
    """
    EMA Trend + RSI Stratejisi
    Mantık: EMA9 > EMA21 ve RSI7 > 55 → long
           EMA9 < EMA21 ve RSI7 < 45 → short
    """
    
    META = {
        "name": "EMA Trend + RSI",
        "group": "trend+osc",
        "description": "Trend takibi ve momentum doğrulaması"
    }
    
    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg
        p = self.cfg.params
        
        # Parametreler
        self.ema_fast = p.get('ema_fast', 9)
        self.ema_slow = p.get('ema_slow', 21)
        self.rsi_len = p.get('rsi_len', 7)
        self.rsi_up = p.get('rsi_up', 55)
        self.rsi_dn = p.get('rsi_dn', 45)
        self.w1 = p.get('w1', 1.0)  # EMA ağırlığı
        self.w2 = p.get('w2', 0.7)  # RSI ağırlığı
    
    def warmup_bars(self) -> int:
        """Gerekli bar sayısı"""
        return max(self.ema_slow, self.rsi_len) + 5
    
    def evaluate(
        self, 
        df: pd.DataFrame, 
        feats: Dict, 
        ctx: ProviderContext
    ) -> Optional[ProviderVote]:
        """Stratejiyi değerlendir"""
        
        if len(df) < self.warmup_bars():
            return None
        
        close = df['close']
        
        # İndikatörler
        e_fast = ema(close, self.ema_fast)
        e_slow = ema(close, self.ema_slow)
        r = rsi(close, self.rsi_len)
        
        # Son değerler
        ema_fast_now = e_fast.iloc[-1]
        ema_slow_now = e_slow.iloc[-1]
        rsi_now = r.iloc[-1]
        
        # NaN kontrolü
        if pd.isna(ema_fast_now) or pd.isna(ema_slow_now) or pd.isna(rsi_now):
            return None
        
        # Trend ve momentum
        trend_up = ema_fast_now > ema_slow_now
        trend_dn = ema_fast_now < ema_slow_now
        
        vote = 0
        
        if trend_up and rsi_now > self.rsi_up:
            vote = 1  # Long/Call
        elif trend_dn and rsi_now < self.rsi_dn:
            vote = -1  # Short/Put
        
        if vote == 0:
            return ProviderVote(pid=self.cfg.id, vote=0, score=0.0)
        
        # Skor hesapla
        # EMA eğimi
        if len(e_fast) >= 3:
            slope = (e_fast.iloc[-1] - e_fast.iloc[-3]) / max(1e-6, e_fast.iloc[-3])
        else:
            slope = 0.0
        
        # RSI normalize
        rsi_norm = (rsi_now - 50.0) / 50.0
        
        # Ağırlıklı toplam
        score = self.w1 * slope + self.w2 * rsi_norm
        
        return ProviderVote(
            pid=self.cfg.id,
            vote=vote,
            score=float(score),
            meta={
                "ema_fast": ema_fast_now,
                "ema_slow": ema_slow_now,
                "rsi": rsi_now,
                "slope": slope
            }
        )
