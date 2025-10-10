"""
Ensemble - Weighted voting and scoring
Parça 9, 11 - Ensemble ağırlıklı oylama
"""

import math
from typing import List
from .models import ProviderVote, EnsembleState, EnsembleResult


class Ensemble:
    """
    Ensemble katmanı
    Birden çok strateji oyunu birleştirir
    """
    
    def __init__(self, state: EnsembleState, s_cap: float = 2.0):
        self.st = state
        self.s_cap = s_cap  # Skor tavanı
    
    def _normalize(self, pid: int, x: float) -> float:
        """
        Skoru normalize et (z-score)
        """
        mu = self.st.mu.get(pid, 0.0)
        sigma = max(1e-6, self.st.sigma.get(pid, 1.0))
        
        z = (x - mu) / sigma
        # Clip to [-3, 3]
        z = max(-3.0, min(3.0, z))
        
        return z
    
    def combine(self, votes: List[ProviderVote]) -> EnsembleResult:
        """
        Oyları birleştir - ağırlıklı toplam
        """
        if not votes:
            return EnsembleResult(
                S=0.0,
                confidence=0.0,
                p_hat=0.5,
                direction=0,
                votes=[],
                reason="no_votes"
            )
        
        # Ağırlıklı toplam
        total_weight = 0.0
        weighted_sum = 0.0
        
        for v in votes:
            # Ağırlık (varsayılan eşit)
            w_i = self.st.w.get(v.pid, 1.0 / len(votes))
            
            # Normalize
            z_i = self._normalize(v.pid, v.score)
            
            # Katkı (vote * normalized_score * weight)
            contrib = w_i * v.vote * z_i
            
            # Tavan uygula
            contrib = max(-self.s_cap, min(self.s_cap, contrib))
            
            weighted_sum += contrib
            total_weight += w_i
        
        # Normalize et [-1, 1] aralığına
        if total_weight > 0:
            S = math.tanh(weighted_sum)
        else:
            S = 0.0
        
        confidence = abs(S)
        direction = 1 if S > 0 else (-1 if S < 0 else 0)
        
        # Platt kalibrasyon ile p̂ hesapla
        p_hat = self._calibrate(S)
        
        return EnsembleResult(
            S=S,
            confidence=confidence,
            p_hat=p_hat,
            direction=direction,
            votes=votes,
            reason="combined"
        )
    
    def _calibrate(self, S: float) -> float:
        """
        Platt kalibrasyon: p̂ = sigmoid(a*S + b)
        """
        z = self.st.a * S + self.st.b
        # Sigmoid with overflow protection
        z = max(-50, min(50, z))
        p_hat = 1.0 / (1.0 + math.exp(-z))
        
        return p_hat
    
    def update_weights(
        self, 
        provider_scores: Dict[int, float], 
        alpha: float = 0.1,
        w_max: float = 0.4
    ) -> None:
        """
        Ağırlıkları güncelle (online learning)
        Softmax ile yeni ağırlıklar
        """
        if not provider_scores:
            return
        
        keys = list(provider_scores.keys())
        vals = [provider_scores[k] for k in keys]
        
        # Softmax
        max_val = max(vals)
        exps = [math.exp(v - max_val) for v in vals]
        total = sum(exps)
        
        new_weights = {k: min(w_max, exps[i] / total) for i, k in enumerate(keys)}
        
        # Karışım güncellemesi (exponential moving average)
        for k in keys:
            old_w = self.st.w.get(k, 1.0 / len(keys))
            self.st.w[k] = (1 - alpha) * old_w + alpha * new_weights[k]
        
        # Normalize
        total_w = sum(self.st.w.values())
        if total_w > 0:
            for k in self.st.w:
                self.st.w[k] /= total_w
