"""
Ensemble & Confidence Layer

Parça 9/11 - Sinyal Birleştirme ve Olasılık Kalibrasyonu
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ProviderVote:
    """Strateji oyu (strategies.base'den import edilebilir)"""
    pid: int
    vote: int  # -1, 0, +1
    score: float
    meta: Dict = field(default_factory=dict)


@dataclass
class EnsembleState:
    """Ensemble durumu ve parametreleri"""
    mu: Dict[int, float] = field(default_factory=dict)      # Provider skor ortalaması
    sigma: Dict[int, float] = field(default_factory=dict)   # Provider skor std sapması
    w: Dict[int, float] = field(default_factory=dict)       # Provider ağırlıkları
    a: float = 1.0   # Platt kalibrasyon a parametresi
    b: float = 0.0   # Platt kalibrasyon b parametresi


@dataclass
class EnsembleResult:
    """Ensemble karar sonucu"""
    S: float                # Ham skor (-1 ile +1 arası)
    confidence: float       # Güven (0-1 arası, |S|)
    p_hat: float           # Kalibre edilmiş kazanma olasılığı
    direction: int         # -1, 0, +1
    votes: List[Dict]      # Provider detayları
    details: Dict = field(default_factory=dict)


class Ensemble:
    """
    Ensemble Karar Motoru
    
    Sorumluluklar:
    - Çoklu strateji oylarını birleştirme
    - Skor normalizasyonu ve ağırlıklandırma
    - Platt kalibrasyonu (S → p_hat)
    - Ağırlık güncelleme (performance-based)
    
    Özellikler:
    - Ağırlıklı toplam + tanh normalizasyon
    - Outlier kırpma (s_cap)
    - Dinamik ağırlık uyarlama
    """
    
    def __init__(self, state: EnsembleState, s_cap: float = 2.0):
        self.st = state
        self.s_cap = s_cap  # Katkı tavanı
    
    def _normalize(self, pid: int, score: float) -> float:
        """
        Skoru normalize et (z-score)
        
        Provider'ın geçmiş skorlarına göre standardize eder
        """
        mu = self.st.mu.get(pid, 0.0)
        sigma = max(1e-6, self.st.sigma.get(pid, 1.0))
        
        z = (score - mu) / sigma
        # Clip aşırı değerler
        z = max(-3.0, min(3.0, z))
        
        return z
    
    def combine(self, votes: List[ProviderVote]) -> EnsembleResult:
        """
        Oyları birleştir ve karar üret
        
        Args:
            votes: Provider oyları
        
        Returns:
            EnsembleResult: Birleştirilmiş karar
        """
        if not votes:
            return EnsembleResult(
                S=0.0,
                confidence=0.0,
                p_hat=0.5,
                direction=0,
                votes=[],
                details={"reason": "no_votes"}
            )
        
        # Ağırlıklı toplam hesapla
        total = 0.0
        total_weight = 0.0
        vote_details = []
        
        for v in votes:
            # Ağırlık (varsayılan: eşit)
            w = self.st.w.get(v.pid, 1.0 / len(votes))
            
            # Normalize skor
            z = self._normalize(v.pid, v.score)
            
            # Katkı hesapla
            contrib = w * v.vote * z
            
            # Katkı tavanı uygula
            contrib = max(-self.s_cap, min(self.s_cap, contrib))
            
            total += contrib
            total_weight += w
            
            vote_details.append({
                "pid": v.pid,
                "vote": v.vote,
                "score": v.score,
                "weight": w,
                "normalized": z,
                "contribution": contrib
            })
        
        # Ensemble skoru (tanh normalizasyon)
        S = math.tanh(total)
        confidence = abs(S)
        
        # Platt kalibrasyonu S → p_hat
        # p_hat = 1 / (1 + exp(-(a*S + b)))
        logit = self.st.a * S + self.st.b
        logit = max(-50, min(50, logit))  # Overflow önleme
        p_hat = 1.0 / (1.0 + math.exp(-logit))
        
        # Yön
        if S > 0:
            direction = +1
        elif S < 0:
            direction = -1
        else:
            direction = 0
        
        return EnsembleResult(
            S=S,
            confidence=confidence,
            p_hat=p_hat,
            direction=direction,
            votes=vote_details,
            details={
                "total_contrib": total,
                "total_weight": total_weight,
                "n_votes": len(votes)
            }
        )
    
    def update_calibration(self, S_list: List[float], y_list: List[int]) -> None:
        """
        Platt kalibrasyonunu güncelle
        
        Args:
            S_list: Ensemble skorları
            y_list: Gerçek sonuçlar (1: win, 0: lose)
        
        Not: Basit implementasyon - production'da sklearn.calibration kullanılabilir
        """
        if len(S_list) < 100:
            return  # Yeterli veri yok
        
        # Basit lojistik regresyon (SGD benzeri)
        # Gerçek implementasyonda sklearn.linear_model.LogisticRegression
        # veya scipy.optimize kullanılmalı
        
        # Şimdilik varsayılan değerler
        self.st.a = 1.0
        self.st.b = 0.0
    
    def update_weights(self, provider_scores: Dict[int, float], 
                      alpha: float = 0.1, w_max: float = 0.4) -> None:
        """
        Ağırlıkları güncelle (performance-based)
        
        Args:
            provider_scores: {pid: performance_score} (0-1 arası)
            alpha: Öğrenme oranı
            w_max: Maksimum ağırlık
        """
        if not provider_scores:
            return
        
        keys = list(provider_scores.keys())
        values = [provider_scores[k] for k in keys]
        
        # Softmax ile yeni ağırlıklar
        max_val = max(values)
        exps = [math.exp(v - max_val) for v in values]
        sum_exp = sum(exps)
        
        new_weights = {k: min(w_max, exps[i] / sum_exp) 
                      for i, k in enumerate(keys)}
        
        # Karışımlı güncelleme (momentum)
        for k in keys:
            old_w = self.st.w.get(k, 1.0 / len(keys))
            self.st.w[k] = (1 - alpha) * old_w + alpha * new_weights[k]
        
        # Normalize
        total = sum(self.st.w.values())
        if total > 0:
            for k in self.st.w:
                self.st.w[k] /= total


# Test
if __name__ == "__main__":
    from ..base import ProviderVote
    
    # Ensemble testi
    state = EnsembleState()
    ens = Ensemble(state, s_cap=2.0)
    
    # Örnek oylar
    votes = [
        ProviderVote(pid=5, vote=+1, score=0.6, meta={}),
        ProviderVote(pid=15, vote=+1, score=0.8, meta={}),
        ProviderVote(pid=25, vote=0, score=0.1, meta={}),
    ]
    
    result = ens.combine(votes)
    
    print("✓ Ensemble Result:")
    print(f"  S: {result.S:.4f}")
    print(f"  Confidence: {result.confidence:.4f}")
    print(f"  p_hat: {result.p_hat:.4f}")
    print(f"  Direction: {result.direction}")
    print(f"  Votes: {len(result.votes)}")
