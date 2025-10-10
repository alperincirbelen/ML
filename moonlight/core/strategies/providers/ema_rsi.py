"""
EMA Trend + RSI Strategy

Parça 13/29 - Strateji ID: 5, 6, 7, 8, 9, 10 (varyantları)
Kategori: Trend + Osilatör (Hybrid)
"""

import pandas as pd
from ..base import StrategyProvider, ProviderConfig, ProviderContext, ProviderVote
from ..registry import register
from ...indicators.basic import ema, rsi


@register(pid=5, metadata={
    "name": "EMA Trend + RSI",
    "group": "hybrid",
    "description": "EMA9>EMA21 & RSI7 trend-momentum doğrulaması"
})
class EMATrendRSI(StrategyProvider):
    """
    EMA Trend + RSI Stratejisi
    
    Mantık:
    - EMA9 > EMA21 ve RSI7 > rsi_up → CALL vote=+1
    - EMA9 < EMA21 ve RSI7 < rsi_dn → PUT vote=-1
    - Aksi halde vote=0
    
    Skor: EMA eğimi + RSI normalize kombinasyonu
    """
    
    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg
        p = cfg.params
        
        # Parametreler (varsayılanlar)
        self.ema_fast = p.get('ema_fast', 9)
        self.ema_slow = p.get('ema_slow', 21)
        self.rsi_len = p.get('rsi_len', 7)
        self.rsi_up = p.get('rsi_up', 55)
        self.rsi_dn = p.get('rsi_dn', 45)
        self.w1 = p.get('w1', 1.0)  # EMA eğim ağırlığı
        self.w2 = p.get('w2', 0.7)  # RSI ağırlığı
    
    def warmup_bars(self) -> int:
        """Minimum bar ihtiyacı"""
        return max(self.ema_slow, self.rsi_len) + 5
    
    def evaluate(self, df: pd.DataFrame, feats: Dict, ctx: ProviderContext) -> Optional[ProviderVote]:
        """Sinyal değerlendirme"""
        # Warm-up kontrolü
        if len(df) < self.warmup_bars():
            return None
        
        close = df['close']
        
        # EMA hesapla
        ema_fast_val = ema(close, self.ema_fast)
        ema_slow_val = ema(close, self.ema_slow)
        
        # RSI hesapla
        rsi_val = rsi(close, self.rsi_len)
        
        # Son değerler
        fast_now = ema_fast_val.iloc[-1]
        slow_now = ema_slow_val.iloc[-1]
        rsi_now = rsi_val.iloc[-1]
        
        # NaN kontrolü
        if pd.isna(fast_now) or pd.isna(slow_now) or pd.isna(rsi_now):
            return None
        
        # Trend belirleme
        trend_up = fast_now > slow_now
        trend_dn = fast_now < slow_now
        
        # Vote hesapla
        vote = 0
        if trend_up and rsi_now > self.rsi_up:
            vote = +1
        elif trend_dn and rsi_now < self.rsi_dn:
            vote = -1
        
        # Sinyal yoksa dön
        if vote == 0:
            return ProviderVote(
                pid=self.cfg.id,
                vote=0,
                score=0.0,
                meta={"ema_fast": fast_now, "ema_slow": slow_now, "rsi": rsi_now}
            )
        
        # Skor hesapla (eğim + RSI normalize)
        # EMA eğimi (son 3 bar)
        if len(ema_fast_val) >= 3:
            slope = (ema_fast_val.iloc[-1] - ema_fast_val.iloc[-3]) / max(1e-9, abs(ema_fast_val.iloc[-3]))
        else:
            slope = 0.0
        
        # RSI normalize (-1 ile +1 arası)
        rsi_norm = (rsi_now - 50.0) / 50.0
        
        # Toplam skor
        score = self.w1 * slope + self.w2 * rsi_norm
        
        return ProviderVote(
            pid=self.cfg.id,
            vote=vote,
            score=float(score),
            meta={
                "ema_fast": fast_now,
                "ema_slow": slow_now,
                "rsi": rsi_now,
                "slope": slope,
                "rsi_norm": rsi_norm
            }
        )


# Diğer varyantlar (farklı parametrelerle)
@register(pid=6, metadata={"name": "EMA Trend + RSI (Conservative)", "group": "hybrid"})
class EMATrendRSI_Conservative(EMATrendRSI):
    """Muhafazakar parametrelerle"""
    def __init__(self, cfg: ProviderConfig):
        super().__init__(cfg)
        self.rsi_up = cfg.params.get('rsi_up', 58)
        self.rsi_dn = cfg.params.get('rsi_dn', 42)


@register(pid=7, metadata={"name": "EMA Trend + RSI (Aggressive)", "group": "hybrid"})
class EMATrendRSI_Aggressive(EMATrendRSI):
    """Agresif parametrelerle"""
    def __init__(self, cfg: ProviderConfig):
        super().__init__(cfg)
        self.rsi_up = cfg.params.get('rsi_up', 52)
        self.rsi_dn = cfg.params.get('rsi_dn', 48)


# Test
if __name__ == "__main__":
    # Test verisi
    n = 100
    df = pd.DataFrame({
        'ts_ms': range(n),
        'open': np.cumsum(np.random.randn(n)) * 0.01 + 100,
        'high': np.cumsum(np.random.randn(n)) * 0.01 + 100.5,
        'low': np.cumsum(np.random.randn(n)) * 0.01 + 99.5,
        'close': np.cumsum(np.random.randn(n)) * 0.01 + 100,
        'volume': np.random.randint(100, 1000, n)
    })
    
    # Strateji test
    from ..registry import build
    
    strategy = build(5, params={'ema_fast': 9, 'ema_slow': 21, 'rsi_len': 7})
    ctx = ProviderContext(product="EURUSD", timeframe=1, payout=90.0)
    
    vote = strategy.evaluate(df, {}, ctx)
    
    if vote:
        print(f"✓ Strategy Vote: {vote.vote}, Score: {vote.score:.4f}")
        print(f"  Meta: {vote.meta}")
    else:
        print("✓ No signal (warm-up or neutral)")
