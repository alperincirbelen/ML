from __future__ import annotations
from typing import List, Dict
from .strategies.base import ProviderVote


class Ensemble:
    def __init__(self, weights: Dict[int, float] | None = None):
        self.weights = weights or {}

    def combine(self, votes: List[ProviderVote]) -> Dict:
        if not votes:
            return {"S": 0.0, "confidence": 0.0, "dir": 0, "p_hat": 0.5}
        num = 0.0
        den = 0.0
        for v in votes:
            w = self.weights.get(v.pid, 1.0)
            num += w * v.vote * max(-1.0, min(1.0, v.score))
            den += abs(w)
        S = 0.0 if den == 0 else max(-1.0, min(1.0, num / den))
        conf = abs(S)
        # naive calibration to a probability-like number
        p_hat = 0.5 + 0.5 * conf
        direction = 1 if S > 0 else (-1 if S < 0 else 0)
        return {"S": S, "confidence": conf, "dir": direction, "p_hat": p_hat}
