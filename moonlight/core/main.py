"""
MoonLight Core Engine - Main Entry Point

Servis başlatma ve yaşam döngüsü yönetimi
"""

from __future__ import annotations
import asyncio
import argparse
from pathlib import Path
from typing import Optional

from .config import load_config, AppConfig
from .storage import Storage
from .connector.mock import MockConnector
from .ensemble import Ensemble, EnsembleState
from .risk import RiskEngine, RiskLimits, AmountPolicy
from .executor import OrderExecutor
from .worker import Worker, WorkerConfig, Scheduler, SchedulerConfig
from .telemetry import StructuredLogger, get_metrics
from .strategies.registry import load_all as load_all_strategies


class MoonLightEngine:
    """
    MoonLight Ana Motor
    
    Sorumluluklar:
    - Konfigurasyon yükleme
    - Bileşenleri başlatma
    - Worker'ları organize etme
    - Graceful shutdown
    """
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self.config: Optional[AppConfig] = None
        self.storage: Optional[Storage] = None
        self.scheduler: Optional[Scheduler] = None
        self.logger = StructuredLogger("moonlight.engine")
        self._running = False
    
    async def initialize(self) -> None:
        """Sistemı başlat"""
        self.logger.info("engine.init", "Initializing MoonLight Engine")
        
        # 1. Konfig yükle
        self.config = load_config(self.config_path)
        self.logger.info("engine.config", "Configuration loaded", 
                        version=self.config.config_version,
                        mode=self.config.mode,
                        connector=self.config.connector)
        
        # 2. Storage başlat
        self.storage = Storage(self.config.storage.sqlite_path)
        await self.storage.init()
        self.logger.info("engine.storage", "Database initialized",
                        path=self.config.storage.sqlite_path)
        
        # 3. Stratejileri yükle
        load_all_strategies()
        from .strategies.registry import list_strategies
        loaded = list_strategies()
        self.logger.info("engine.strategies", "Strategies loaded", count=len(loaded))
        
        # 4. Scheduler oluştur
        scheduler_cfg = SchedulerConfig(
            tick_ms=self.config.engine.tick_interval_ms
        )
        
        # Worker factory
        def create_worker(account: str, product: str, timeframe: int):
            # Connector
            if self.config.connector == "mock":
                connector = MockConnector(account, seed=42)
            else:
                # TODO: Real connector
                raise NotImplementedError("Real connector not implemented yet")
            
            # Ensemble
            ensemble_state = EnsembleState()
            ensemble = Ensemble(ensemble_state, s_cap=2.0)
            
            # Risk
            limits = RiskLimits(
                max_daily_loss=self.config.limits.max_daily_loss,
                max_consec_losses=self.config.limits.max_consecutive_losses
            )
            amt_policy = AmountPolicy(mode="fixed", fixed_a=self.config.risk.default_lot)
            risk = RiskEngine(limits, amt_policy)
            
            # Executor
            locks = {}
            executor = OrderExecutor(connector, self.storage, risk, locks)
            
            # Providers (strateji ID'lerinden)
            # TODO: Gerçek provider'ları config'den yükle
            providers = []
            
            # Worker config
            worker_cfg = WorkerConfig(
                lookback=300,
                tick_ms=self.config.engine.tick_interval_ms
            )
            
            # Worker oluştur
            return Worker(
                account_id=account,
                product=product,
                timeframe=timeframe,
                connector=connector,
                storage=self.storage,
                indicators=None,  # TODO
                providers=providers,
                ensemble=ensemble,
                risk=risk,
                executor=executor,
                cfg=worker_cfg
            )
        
        self.scheduler = Scheduler(create_worker, scheduler_cfg)
        
        self.logger.info("engine.scheduler", "Scheduler initialized")
        
        # 5. API server başlat (opsiyonel, ayrı task olarak)
        # Burada başlatmıyoruz - main.run_api ile ayrı başlatılacak
        
        self._running = True
        self.logger.info("engine.ready", "MoonLight Engine ready")
    
    async def start_workers(self) -> None:
        """Konfigürasyona göre worker'ları başlat"""
        if not self.scheduler:
            self.logger.warn("engine.start", "Scheduler not initialized")
            return
        
        count = 0
        for product_cfg in self.config.products:
            if not product_cfg.enabled:
                continue
            
            for tf_cfg in product_cfg.timeframes:
                if not tf_cfg.enabled:
                    continue
                
                # Her hesap için worker başlat
                for account_cfg in self.config.accounts:
                    await self.scheduler.start_worker(
                        account_cfg.id,
                        product_cfg.product,
                        tf_cfg.tf
                    )
                    count += 1
        
        self.logger.info("engine.workers_started", "Workers started", count=count)
    
    async def stop(self) -> None:
        """Sistemi durdur"""
        self.logger.info("engine.stop", "Stopping MoonLight Engine")
        
        if self.scheduler:
            await self.scheduler.stop_all()
        
        if self.storage:
            await self.storage.close()
        
        self._running = False
        self.logger.info("engine.stopped", "Engine stopped gracefully")
    
    async def run(self) -> None:
        """Ana döngü (metrik snapshot vb.)"""
        metrics = get_metrics()
        snapshot_interval = self.config.telemetry.snapshot_interval_sec
        
        while self._running:
            await asyncio.sleep(snapshot_interval)
            
            # Metrik snapshot
            if self.config.telemetry.enabled:
                snapshot = metrics.snapshot()
                # TODO: Storage'a yaz
                self.logger.debug("engine.metrics", "Snapshot taken", count=len(snapshot))


def mask_email(email: str) -> str:
    """Quick email mask"""
    if '@' in email:
        user = email.split('@')[0]
        if len(user) > 2:
            return f"{user[0]}***@***"
    return "***@***"


async def main_async(config_path: str, start_workers: bool = True):
    """Async main"""
    engine = MoonLightEngine(config_path)
    
    try:
        await engine.initialize()
        
        if start_workers:
            await engine.start_workers()
        
        # Ana döngü
        await engine.run()
    
    except KeyboardInterrupt:
        print("\n✓ Shutting down...")
    
    finally:
        await engine.stop()


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="MoonLight Fixed-Time Trading AI")
    parser.add_argument("-c", "--config", default="configs/app.yaml",
                       help="Config file path")
    parser.add_argument("--no-workers", action="store_true",
                       help="Don't start workers automatically")
    parser.add_argument("--mode", choices=["paper", "live"],
                       help="Override mode")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MoonLight - Fixed Time Trading AI")
    print("=" * 60)
    print(f"Config: {args.config}")
    print()
    
    # Run
    try:
        asyncio.run(main_async(
            args.config,
            start_workers=not args.no_workers
        ))
    except KeyboardInterrupt:
        print("\n✓ Stopped by user")


if __name__ == "__main__":
    main()
