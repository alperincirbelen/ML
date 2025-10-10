"""
Worker - Per (account, product, timeframe) task
Parça 12 - İşlem döngüsü worker'ı
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


@dataclass
class WorkerConfig:
    """Worker konfigürasyonu"""
    lookback: int = 300
    grace_ms: int = 500
    tick_ms: int = 250
    jitter_ms: int = 100
    entry_cutoff_s: int = 5
    overrun_skip: bool = True


class Worker:
    """
    Worker - her (account, product, tf) için bir döngü
    """
    
    def __init__(
        self,
        account_id: str,
        product: str,
        timeframe: int,
        connector,
        storage,
        indicators,
        providers,
        ensemble,
        risk,
        executor,
        cfg: WorkerConfig
    ):
        self.account = account_id
        self.product = product
        self.tf = timeframe
        
        self.connector = connector
        self.storage = storage
        self.ind = indicators
        self.providers = providers
        self.ensemble = ensemble
        self.risk = risk
        self.executor = executor
        self.cfg = cfg
        
        self._running = False
        self._last_close_slot: Optional[int] = None
    
    def _tf_slot(self, ts_ms: int) -> int:
        """TF slotuna hizala"""
        tf_ms = self.tf * 60_000
        return ts_ms - (ts_ms % tf_ms)
    
    async def run(self) -> None:
        """Ana worker döngüsü"""
        self._running = True
        
        try:
            while self._running:
                now = int(time.time() * 1000)
                slot = self._tf_slot(now)
                
                if self._last_close_slot is None:
                    self._last_close_slot = slot
                
                # Yeni bar kapanışı
                if slot > self._last_close_slot:
                    await self._on_close(self._last_close_slot)
                    self._last_close_slot = slot
                
                # Tick interval
                await asyncio.sleep(self.cfg.tick_ms / 1000.0)
        
        except asyncio.CancelledError:
            self._running = False
        except Exception as e:
            # Log error
            print(f"Worker error: {e}")
            self._running = False
    
    async def _on_close(self, close_slot_ms: int) -> None:
        """
        Bar kapanışında çalışan işlem
        Fetch → Features → Strategies → Ensemble → Risk → Execute
        """
        try:
            # 1) Veri çek
            candles = await self.connector.get_candles(
                self.product, 
                self.tf, 
                n=self.cfg.lookback
            )
            
            if not candles or len(candles) < 30:
                return
            
            # DataFrame'e dönüştür
            df = pd.DataFrame(candles)
            
            # 2) Payout getir
            payout = await self.connector.get_current_win_rate(self.product)
            
            # 3) Stratejileri değerlendir
            votes = []
            for provider in self.providers:
                try:
                    vote = provider.evaluate(df, {}, None)
                    if vote:
                        votes.append(vote)
                except Exception as e:
                    # Strateji hatası - atla
                    print(f"Strategy {provider.cfg.id} error: {e}")
            
            if not votes:
                return
            
            # 4) Ensemble
            result = self.ensemble.combine(votes)
            
            if result.direction == 0:
                return
            
            # 5) Trade context oluştur
            from ..risk.engine import TradeContext
            ctx = TradeContext(
                account=self.account,
                product=self.product,
                timeframe=self.tf,
                direction='call' if result.direction > 0 else 'put',
                payout=payout,
                confidence=result.confidence,
                prob_win=result.p_hat,
                win_threshold=0.70,  # Config'den alınmalı
                permit_min=89.0,  # Config'den alınmalı
                permit_max=93.0,  # Config'den alınmalı
                balance=1000.0  # Config/DB'den alınmalı
            )
            
            # 6) Execute
            exec_result = await self.executor.execute(ctx)
            
            # Log sonucu
            print(f"Worker [{self.account}:{self.product}:{self.tf}] -> {exec_result}")
        
        except Exception as e:
            print(f"Worker _on_close error: {e}")
    
    def stop(self) -> None:
        """Worker'ı durdur"""
        self._running = False
