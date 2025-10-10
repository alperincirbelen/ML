from __future__ import annotations
from typing import List, Dict, Any

from .strategies.base import StrategyProvider, ProviderContext
from .ensemble import Ensemble
from .executor import OrderExecutor, TradeCtx


class Worker:
    def __init__(
        self,
        *,
        account_id: str,
        product: str,
        timeframe: int,
        connector,
        providers: List[StrategyProvider],
        ensemble: Ensemble,
        executor: OrderExecutor,
        permit_min: float,
        permit_max: float,
        win_threshold: float,
    ):
        self.acc = account_id
        self.product = product
        self.tf = timeframe
        self.cx = connector
        self.providers = providers
        self.ens = ensemble
        self.exec = executor
        self.permit_min = permit_min
        self.permit_max = permit_max
        self.win_threshold = win_threshold

    def run_once(self, lookback: int = 300) -> Dict[str, Any]:
        bars = self.cx.get_candles(self.product, self.tf, n=lookback)
        payout = self.cx.get_current_win_rate(self.product)
        ctx = ProviderContext(product=self.product, timeframe=self.tf, payout=payout)
        votes = []
        for p in self.providers:
            v = p.evaluate(bars, ctx)
            if v is not None:
                votes.append(v)
        comb = self.ens.combine(votes)
        direction = 'call' if comb['dir'] > 0 else ('put' if comb['dir'] < 0 else None)
        if not direction:
            return {"status": "hold", "reason": "no-direction"}
        tctx = TradeCtx(
            account=self.acc,
            product=self.product,
            timeframe=self.tf,
            direction=direction,
            payout=payout,
            confidence=comb['confidence'],
            p_hat=comb['p_hat'],
            win_threshold=self.win_threshold,
            permit_min=self.permit_min,
            permit_max=self.permit_max,
        )
        res = self.exec.execute(tctx)
        return res
