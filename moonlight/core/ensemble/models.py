"""
Ensemble data models
Parça 9 - Ensemble veri modelleri
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ProviderVote:
    """Strateji sağlayıcı oyu"""
    pid: int  # Provider/Strategy ID
    vote: int  # -1 (short/put), 0 (neutral), +1 (long/call)
    score: float  # Ham güven skoru
    meta: Dict = field(default_factory=dict)


@dataclass
class EnsembleState:
    """Ensemble durumu - ağırlıklar ve normalizasyon"""
    mu: Dict[int, float] = field(default_factory=dict)  # Mean
    sigma: Dict[int, float] = field(default_factory=dict)  # Std
    w: Dict[int, float] = field(default_factory=dict)  # Weights
    a: float = 1.0  # Platt kalibrasyon a
    b: float = 0.0  # Platt kalibrasyon b


@dataclass
class EnsembleResult:
    """Ensemble sonucu"""
    S: float  # Ensemble skoru [-1, 1]
    confidence: float  # |S| - güven
    p_hat: float  # Kalibre edilmiş kazanma olasılığı
    direction: int  # -1, 0, +1
    votes: List[ProviderVote] = field(default_factory=list)
    reason: str = ""
