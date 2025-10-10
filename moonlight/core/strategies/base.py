"""
Strategy Base Classes and Provider Interface

Parça 13 - Strateji Kataloğu (Plugin Sistemi)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Protocol
import pandas as pd


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


@dataclass
class ProviderVote:
    """Strateji oyu/sinyali"""
    pid: int                          # Provider ID
    vote: int                         # -1 (put/short), 0 (neutral), +1 (call/long)
    score: float                      # Ham güven skoru (normalize edilecek)
    meta: Dict[str, Any] = field(default_factory=dict)  # Açıklama alanları


class StrategyProvider(Protocol):
    """
    Strateji Sağlayıcı Arayüzü
    
    Tüm stratejiler bu protokolü uygulamalıdır.
    
    Sorumluluklar:
    - Bar verisi → Sinyal/Vote üretimi
    - Warm-up ihtiyacını bildirme
    - Deterministik davranış (aynı girdi → aynı çıktı)
    - Meta alanlarla açıklanabilirlik
    
    Kısıtlar:
    - Ağ/disk erişimi yasak
    - Yan etkisiz (side-effect free)
    - Süre bütçesi: p90 < 3ms / 200 bar
    """
    
    cfg: ProviderConfig
    
    def warmup_bars(self) -> int:
        """Minimum gerekli bar sayısı"""
        ...
    
    def evaluate(self, df: pd.DataFrame, feats: Dict[str, Any], 
                ctx: ProviderContext) -> Optional[ProviderVote]:
        """
        Sinyal değerlendirmesi
        
        Args:
            df: OHLCV DataFrame (ts_ms, open, high, low, close, volume)
            feats: Önceden hesaplanmış göstergeler
            ctx: Bağlam (product, tf, payout)
        
        Returns:
            ProviderVote veya None (sinyal yok)
        """
        ...


@dataclass
class StrategyMetadata:
    """Strateji meta bilgisi"""
    id: int
    name: str
    group: str
    description: str
    warmup_bars: int
    params_schema: Dict[str, Any]
    notes: str = ""
