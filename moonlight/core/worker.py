"""
Worker & Scheduler

Parça 12 - Worker döngüsü, TF hizalama, back pressure
"""

from __future__ import annotations
import asyncio
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable
import pandas as pd

from .connector.interface import Connector
from .storage import Storage
from .ensemble import Ensemble, ProviderVote
from .risk import RiskEngine, TradeContext
from .executor import OrderExecutor
from .strategies.base import ProviderContext


@dataclass
class WorkerConfig:
    """Worker ayarları"""
    lookback: int = 300              # Bar sayısı
    grace_ms: int = 500              # Kapanış sonrası bekleme
    tick_ms: int = 250               # Tick aralığı (TF=1 için)
    jitter_ms: int = 100             # Rastgele gecikme
    entry_cutoff_s: int = 5          # Kapanışa yakın giriş yasağı
    overrun_skip: bool = True        # Geciken işi atla


class Worker:
    """
    İşlem Worker'ı
    
    Her (account, product, timeframe) için bir worker
    
    Sorumluluklar:
    - TF hizalı tetikleme
    - Veri çekme → Feature hesaplama → Strateji değerlendirme
    - Ensemble → Risk → Executor zinciri
    - Metrik ve log üretimi
    """
    
    def __init__(self, 
                 account_id: str,
                 product: str,
                 timeframe: int,
                 connector: Connector,
                 storage: Storage,
                 indicators: Any,  # Indicator fonksiyonları
                 providers: List[Any],  # Strategy providers
                 ensemble: Ensemble,
                 risk: RiskEngine,
                 executor: OrderExecutor,
                 cfg: WorkerConfig):
        
        self.account = account_id
        self.product = product
        self.tf = timeframe
        
        self.cx = connector
        self.db = storage
        self.ind = indicators
        self.providers = providers
        self.ens = ensemble
        self.risk = risk
        self.exec = executor
        self.cfg = cfg
        
        self._running = False
        self._last_close_slot: Optional[int] = None
    
    def _tf_slot(self, ts_ms: int) -> int:
        """Timestamp'i TF slotuna hizala"""
        tf_ms = self.tf * 60_000
        return ts_ms - (ts_ms % tf_ms)
    
    async def run(self) -> None:
        """Ana worker döngüsü"""
        self._running = True
        
        try:
            while self._running:
                now_ms = int(time.time() * 1000)
                slot = self._tf_slot(now_ms)
                
                # İlk çalıştırma
                if self._last_close_slot is None:
                    self._last_close_slot = slot
                
                # Yeni kapanış var mı?
                if slot > self._last_close_slot:
                    # Kapanış işle
                    await self._on_close(self._last_close_slot)
                    self._last_close_slot = slot
                
                # Tick bekle
                await asyncio.sleep(self.cfg.tick_ms / 1000.0)
        
        except asyncio.CancelledError:
            self._running = False
    
    async def _on_close(self, close_slot_ms: int) -> None:
        """
        Bar kapanışı işleme
        
        1. Fetch candles
        2. Compute features
        3. Evaluate strategies
        4. Ensemble decision
        5. Risk & Execute
        """
        try:
            # 1. Veri çek
            candles = await self.cx.get_candles(self.product, self.tf, n=self.cfg.lookback)
            
            if not candles or len(candles) < 30:
                return  # Yeterli veri yok
            
            # DataFrame'e çevir
            df = pd.DataFrame([c.model_dump() for c in candles])
            df = df.sort_values('ts_ms')
            
            # 2. Features (basit - indicator'ları kullan)
            # Gerçek implementasyonda tüm göstergeler hesaplanır
            feats = {}
            
            # 3. Providers'ı çalıştır
            votes: List[ProviderVote] = []
            
            payout = await self.cx.get_current_win_rate(self.product)
            ctx = ProviderContext(
                product=self.product,
                timeframe=self.tf,
                payout=payout
            )
            
            for provider in self.providers:
                try:
                    vote = provider.evaluate(df, feats, ctx)
                    if vote is not None:
                        votes.append(vote)
                except Exception as e:
                    # Provider hatası - atla ve logla
                    print(f"Provider {getattr(provider, 'cfg', '?').id} error: {e}")
            
            if not votes:
                return  # Hiç sinyal yok
            
            # 4. Ensemble
            result = self.ens.combine(votes)
            
            if result.direction == 0:
                return  # Nötr karar
            
            # 5. Trade context oluştur
            trade_ctx = TradeContext(
                account=self.account,
                product=self.product,
                timeframe=self.tf,
                payout=payout / 100.0,  # Ratio'ya çevir
                confidence=result.confidence,
                prob_win=result.p_hat,
                balance=100.0,  # Mock - gerçek implementasyonda connector'dan alınır
                permit_min=85.0,  # Config'den gelir
                permit_max=95.0,
                win_threshold=0.70  # Config'den gelir
            )
            
            # 6. Execute
            exec_result = await self.exec.execute(trade_ctx)
            
            # Log (basit print - gerçek implementasyonda structured log)
            print(f"[{self.account}:{self.product}:{self.tf}] "
                  f"Decision: {exec_result.status} | "
                  f"Reason: {exec_result.reason}")
        
        except Exception as e:
            print(f"Worker error [{self.account}:{self.product}:{self.tf}]: {e}")
    
    def stop(self) -> None:
        """Worker'ı durdur"""
        self._running = False


@dataclass
class SchedulerConfig:
    """Scheduler ayarları"""
    tick_ms: int = 250
    jitter_ms: int = 100


class Scheduler:
    """
    Worker Zamanlayıcı
    
    Sorumluluklar:
    - Worker'ları başlatma/durdurma
    - Yaşam döngüsü yönetimi
    - Hata toleransı
    """
    
    def __init__(self, worker_factory: Callable, cfg: SchedulerConfig):
        self.worker_factory = worker_factory
        self.cfg = cfg
        self.workers: Dict[tuple, asyncio.Task] = {}
    
    def _key(self, acc: str, prod: str, tf: int) -> tuple:
        """Worker anahtarı"""
        return (acc, prod, tf)
    
    async def start_worker(self, account: str, product: str, timeframe: int) -> None:
        """Worker başlat"""
        key = self._key(account, product, timeframe)
        
        # Zaten çalışıyor mu?
        if key in self.workers:
            task = self.workers[key]
            if not task.done():
                return  # Zaten aktif
        
        # Yeni worker oluştur
        worker = self.worker_factory(account, product, timeframe)
        task = asyncio.create_task(
            worker.run(),
            name=f"worker:{account}:{product}:{timeframe}"
        )
        
        self.workers[key] = task
    
    async def stop_worker(self, account: str, product: str, timeframe: int) -> None:
        """Worker durdur"""
        key = self._key(account, product, timeframe)
        task = self.workers.get(key)
        
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            del self.workers[key]
    
    async def stop_all(self) -> None:
        """Tüm worker'ları durdur"""
        for key in list(self.workers.keys()):
            await self.stop_worker(*key)
    
    def list_workers(self) -> List[Dict]:
        """Aktif worker listesi"""
        result = []
        for (acc, prod, tf), task in self.workers.items():
            result.append({
                "account": acc,
                "product": prod,
                "timeframe": tf,
                "running": not task.done()
            })
        return result


# Test
if __name__ == "__main__":
    print("✓ Worker and Scheduler modules loaded")
    print("  Use main.py to run the full system")
