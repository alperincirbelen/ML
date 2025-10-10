"""
Risk Management & Guardrails

Parça 6/8/10 - Risk Yönetimi, Limitler ve Koruma Bariyerleri
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime, timezone


@dataclass
class RiskLimits:
    """Risk limitleri"""
    max_daily_loss: Optional[float] = 5.0
    max_consec_losses: Optional[int] = 5
    a_min: float = 1.0      # Minimum tutar
    a_cap: float = 10.0     # Maksimum tutar


@dataclass
class AmountPolicy:
    """Tutar belirleme politikası"""
    mode: str = "fixed"           # fixed | fraction | kelly_lite | atr_norm
    fixed_a: float = 1.0
    frac: float = 0.02            # Balance fraksiyonu (%2)
    kelly_scale: float = 0.2      # Kelly fraksiyonu (20% of Kelly)


@dataclass
class TradeContext:
    """İşlem bağlamı"""
    account: str
    product: str
    timeframe: int
    payout: float              # Payout ratio (0.9 = %90)
    confidence: float          # Ensemble confidence (0-1)
    prob_win: float           # p_hat - kalibre olasılık
    balance: float = 100.0
    permit_min: float = 0.0
    permit_max: float = 100.0
    win_threshold: float = 0.70
    concurrency_blocked: bool = False


class RiskEngine:
    """
    Risk Yönetimi Motoru
    
    Sorumluluklar:
    - Giriş izin kontrolü (permit, threshold, concurrency, limits)
    - Tutar hesaplama (fixed, fraction, Kelly)
    - Günlük/ardışık kayıp takibi
    - Cool-down yönetimi
    
    Fail-closed: Şüphede emir yok
    """
    
    def __init__(self, limits: RiskLimits, amt_policy: AmountPolicy):
        self.limits = limits
        self.amt = amt_policy
        
        # Hesap bazlı durumlar
        self._loss_streak: Dict[str, int] = {}
        self._pnl_day: Dict[str, float] = {}
        self._last_trade_ts: Dict[str, int] = {}
        self._cooldown_until: Dict[str, int] = {}
    
    def enter_allowed(self, ctx: TradeContext) -> bool:
        """
        Giriş izin kontrolü
        
        Kontroller (sırayla):
        1. Payout permit penceresi
        2. Confidence eşiği
        3. Concurrency kilidi
        4. Ardışık kayıp limiti
        5. Günlük kayıp limiti
        6. Cool-down
        
        Returns:
            True: İzin verildi
            False: Reddedildi (sebep loglanmalı)
        """
        # 1. Permit penceresi
        if ctx.payout < ctx.permit_min or ctx.payout > ctx.permit_max:
            return False
        
        # 2. Confidence eşiği
        if ctx.confidence < ctx.win_threshold:
            return False
        
        # 3. Concurrency
        if ctx.concurrency_blocked:
            return False
        
        # 4. Ardışık kayıp
        if self.limits.max_consec_losses:
            streak = self._loss_streak.get(ctx.account, 0)
            if streak >= self.limits.max_consec_losses:
                return False
        
        # 5. Günlük kayıp
        if self.limits.max_daily_loss:
            pnl = self._pnl_day.get(ctx.account, 0.0)
            if pnl <= -self.limits.max_daily_loss:
                return False
        
        # 6. Cool-down
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        cooldown = self._cooldown_until.get(ctx.account, 0)
        if now_ms < cooldown:
            return False
        
        return True
    
    def compute_amount(self, ctx: TradeContext) -> float:
        """
        İşlem tutarını hesapla
        
        Args:
            ctx: İşlem bağlamı
        
        Returns:
            Tutar (a_min ile a_cap arası sınırlı)
        """
        if self.amt.mode == "fixed":
            a = self.amt.fixed_a
        
        elif self.amt.mode == "fraction":
            a = ctx.balance * self.amt.frac
        
        elif self.amt.mode == "kelly_lite":
            # Kelly criterion: f* = (p*(R+1) - 1) / R
            # R = payout ratio
            R = ctx.payout
            p = max(0.0, min(1.0, ctx.prob_win))
            
            f_star = (p * (R + 1) - 1) / max(R, 1e-6)
            f_star = max(0.0, f_star)  # Negatif Kelly'yi sıfırla
            
            a = ctx.balance * f_star * self.amt.kelly_scale
        
        else:
            # Varsayılan: fixed
            a = self.amt.fixed_a
        
        # Sınırları uygula
        a = max(self.limits.a_min, min(a, self.limits.a_cap))
        
        return float(a)
    
    def on_result(self, ctx: TradeContext, pnl: float, is_win: bool) -> None:
        """
        İşlem sonucunu kaydet ve durum güncelle
        
        Args:
            ctx: İşlem bağlamı
            pnl: Kar/zarar
            is_win: Kazandı mı?
        """
        account = ctx.account
        
        # Günlük PnL güncelle
        self._pnl_day[account] = self._pnl_day.get(account, 0.0) + pnl
        
        # Ardışık kayıp güncelle
        if is_win:
            self._loss_streak[account] = 0
        else:
            self._loss_streak[account] = self._loss_streak.get(account, 0) + 1
        
        # Kayıp sonrası cool-down
        if not is_win:
            streak = self._loss_streak[account]
            # Artan cool-down: 30s → 60s → 120s (max 5dk)
            cooldown_sec = min(300, 30 * (2 ** (streak - 1)))
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            self._cooldown_until[account] = now_ms + (cooldown_sec * 1000)
    
    def reset_daily(self, account: str) -> None:
        """Günlük sayaçları sıfırla (gün başında çağrılır)"""
        self._pnl_day[account] = 0.0
        # Not: Ardışık kayıp gün geçişinde sıfırlanmaz
    
    def get_status(self, account: str) -> Dict:
        """Hesap risk durumu"""
        return {
            "account": account,
            "pnl_day": self._pnl_day.get(account, 0.0),
            "loss_streak": self._loss_streak.get(account, 0),
            "cooldown_until": self._cooldown_until.get(account, 0)
        }


# Test
if __name__ == "__main__":
    # Risk engine testi
    limits = RiskLimits(max_daily_loss=5.0, max_consec_losses=3, a_min=1.0, a_cap=10.0)
    amt_policy = AmountPolicy(mode="fixed", fixed_a=1.0)
    
    risk = RiskEngine(limits, amt_policy)
    
    # Test context
    ctx = TradeContext(
        account="acc1",
        product="EURUSD",
        timeframe=1,
        payout=0.9,
        confidence=0.75,
        prob_win=0.65,
        balance=100.0,
        permit_min=85.0,
        permit_max=95.0,
        win_threshold=0.70,
        concurrency_blocked=False
    )
    
    # İzin kontrolü
    allowed = risk.enter_allowed(ctx)
    print(f"✓ Entry allowed: {allowed}")
    
    # Tutar hesapla
    amount = risk.compute_amount(ctx)
    print(f"✓ Amount: {amount}")
    
    # Kayıp simüle et
    risk.on_result(ctx, pnl=-1.0, is_win=False)
    risk.on_result(ctx, pnl=-1.0, is_win=False)
    risk.on_result(ctx, pnl=-1.0, is_win=False)
    
    # Ardışık kayıp sonrası kontrol
    allowed = risk.enter_allowed(ctx)
    print(f"✓ After 3 losses, entry allowed: {allowed}")
    
    status = risk.get_status("acc1")
    print(f"✓ Risk status: {status}")
