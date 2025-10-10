"""
Strategy Provider Base
Parça 13 - Strateji temel arayüzü
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Protocol
import pandas as pd
from ..ensemble.models import ProviderVote


@dataclass
class ProviderContext:
    """Strateji bağlamı"""
    product: str
    timeframe: int
    payout: float
    seed: Optional[int] = None


@dataclass
class ProviderConfig:
    """Strateji konfigürasyonu"""
    id: int
    name: str
    group: str
    params: Dict[str, Any] = field(default_factory=dict)


class StrategyProvider(Protocol):
    """
    Strateji sağlayıcı arayüzü
    Tüm stratejiler bu sözleşmeyi uygular
    """
    
    cfg: ProviderConfig
    
    def warmup_bars(self) -> int:
        """Gerekli minimum bar sayısı"""
        ...
    
    def evaluate(
        self, 
        df: pd.DataFrame, 
        feats: Dict[str, Any], 
        ctx: ProviderContext
    ) -> Optional[ProviderVote]:
        """
        Stratejiyi değerlendir
        
        Args:
            df: OHLCV DataFrame (ts_ms, open, high, low, close, volume)
            feats: Hesaplanmış indikatörler
            ctx: Bağlam (product, tf, payout)
        
        Returns:
            ProviderVote veya None (sinyal yok)
        """
        ...
