from __future__ import annotations
from dataclasses import dataclass


@dataclass
class RiskLimits:
    permit_min: float = 80.0  # payout % min
    permit_max: float = 95.0  # payout % max
    win_threshold: float = 0.70  # min confidence-to-probability gate
    fixed_amount: float = 1.0  # fixed stake


class RiskEngine:
    def __init__(self, limits: RiskLimits):
        self.limits = limits

    def enter_allowed(self, *, payout: float, confidence: float, p_hat: float) -> bool:
        if payout < self.limits.permit_min or payout > self.limits.permit_max:
            return False
        if p_hat < self.limits.win_threshold:
            return False
        return True

    def compute_amount(self, balance: float | None = None) -> float:
        return float(self.limits.fixed_amount)
