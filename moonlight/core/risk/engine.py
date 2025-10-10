"""
Risk Engine - Position sizing and limits
Parça 10, 18 - Risk motoru ve pozisyon boyutlandırma
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class RiskLimits:
    """Risk limitleri"""
    max_daily_loss: Optional[float] = 5.0
    max_consec_losses: Optional[int] = 5
    a_min: float = 1.0  # Minimum tutar
    a_cap: float = 10.0  # Maksimum tutar


@dataclass
class AmountPolicy:
    """Tutar hesaplama politikası"""
    mode: str = "fixed"  # fixed | fraction | kelly_lite | atr_norm
    fixed_a: float = 1.0
    frac: float = 0.02  # Balance'ın %2'si
    kelly_scale: float = 0.2  # Kelly'nin %20'si


@dataclass
class TradeContext:
    """İşlem bağlamı"""
    account: str
    product: str
    timeframe: int
    direction: str
    payout: float
    confidence: float
    prob_win: float  # p̂ - kalibre edilmiş kazanma olasılığı
    win_threshold: float
    permit_min: float
    permit_max: float
    balance: float = 1000.0
    concurrency_blocked: bool = False


class RiskEngine:
    """
    Risk motoru
    Giriş izinleri ve tutar hesaplama
    """
    
    def __init__(self, limits: RiskLimits, amt: AmountPolicy):
        self.limits = limits
        self.amt = amt
        self._loss_streak: Dict[str, int] = {}
        self._pnl_day: Dict[str, float] = {}
    
    def enter_allowed(self, ctx: TradeContext) -> bool:
        """
        Giriş izni kontrolü
        Tüm guardrails burada
        """
        # Permit penceresi
        if ctx.payout < ctx.permit_min or ctx.payout > ctx.permit_max:
            return False
        
        # Confidence eşiği
        if ctx.confidence < ctx.win_threshold:
            return False
        
        # Concurrency
        if ctx.concurrency_blocked:
            return False
        
        # Ardışık kayıp limiti
        max_losses = self.limits.max_consec_losses or 9999
        if self._loss_streak.get(ctx.account, 0) >= max_losses:
            return False
        
        # Günlük kayıp limiti
        max_daily = self.limits.max_daily_loss or 1e9
        if self._pnl_day.get(ctx.account, 0.0) <= -max_daily:
            return False
        
        return True
    
    def compute_amount(self, ctx: TradeContext) -> float:
        """
        Tutar hesapla - pozisyon boyutlandırma
        """
        if self.amt.mode == "fixed":
            a = self.amt.fixed_a
        
        elif self.amt.mode == "fraction":
            a = ctx.balance * self.amt.frac
        
        elif self.amt.mode == "kelly_lite":
            # Kelly Criterion: f* = (p(R+1) - 1) / R
            R = ctx.payout / 100.0  # Payout oranı
            p = max(0.0, min(1.0, ctx.prob_win))
            
            f_star = (p * (R + 1) - 1) / max(R, 1e-6)
            a = ctx.balance * max(0.0, f_star) * self.amt.kelly_scale
        
        else:
            a = self.amt.fixed_a
        
        # Sınırlar uygula
        a = max(self.limits.a_min, min(a, self.limits.a_cap))
        
        return float(a)
    
    def on_result(self, ctx: TradeContext, pnl: float, is_win: bool) -> None:
        """
        Sonuç geri bildirimi
        PnL ve streak sayaçlarını güncelle
        """
        # Günlük PnL
        current_pnl = self._pnl_day.get(ctx.account, 0.0)
        self._pnl_day[ctx.account] = current_pnl + pnl
        
        # Kayıp serisi
        if is_win:
            self._loss_streak[ctx.account] = 0
        else:
            current_streak = self._loss_streak.get(ctx.account, 0)
            self._loss_streak[ctx.account] = current_streak + 1
    
    def reset_daily(self, account: Optional[str] = None) -> None:
        """Günlük sayaçları sıfırla (gün sonu)"""
        if account:
            self._pnl_day[account] = 0.0
        else:
            self._pnl_day.clear()
    
    def get_daily_pnl(self, account: str) -> float:
        """Günlük PnL getir"""
        return self._pnl_day.get(account, 0.0)
    
    def get_loss_streak(self, account: str) -> int:
        """Ardışık kayıp sayısı"""
        return self._loss_streak.get(account, 0)
