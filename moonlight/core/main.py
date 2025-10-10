"""
MoonLight Core Engine - Main Entry Point
Ana giriş noktası
"""

import asyncio
import sys
from pathlib import Path

# Core modülleri
from .config import ConfigLoader
from .storage import Storage, init_database
from .connector import ConnectorManager
from .risk import RiskEngine, RiskLimits, AmountPolicy, Guardrails, GuardrailsConfig
from .ensemble import Ensemble, EnsembleState
from .executor import OrderExecutor
from .worker import Scheduler, WorkerConfig
from .telemetry import setup_logger, Metrics
from .strategies.registry import StrategyRegistry
from .api import create_app


async def main(config_path: str = "configs/config.example.yaml"):
    """
    Ana uygulama
    """
    # Logger kur
    logger = setup_logger(
        "moonlight",
        "data/logs/moonlight.log",
        level="INFO"
    )
    
    logger.info("MoonLight Fixed-Time Trading AI başlatılıyor...")
    
    try:
        # 1) Konfigürasyon yükle
        logger.info(f"Konfigürasyon yükleniyor: {config_path}")
        config = ConfigLoader.load_yaml(config_path)
        
        # Doğrula
        is_valid, warnings = ConfigLoader.validate_config(config)
        
        if not is_valid:
            logger.error("Konfigürasyon doğrulama hatası!")
            return
        
        for warning in warnings:
            logger.warning(f"Config warning: {warning}")
        
        # 2) Veritabanı başlat
        logger.info("Veritabanı başlatılıyor...")
        await init_database(config.storage.sqlite_path)
        storage = Storage(config.storage.sqlite_path)
        
        # 3) Bileşenleri oluştur
        logger.info("Bileşenler başlatılıyor...")
        
        # Connector manager
        conn_manager = ConnectorManager()
        for account in config.accounts:
            await conn_manager.ensure(
                account.id,
                connector_type=config.connector.type.value
            )
        
        # Metrics
        metrics = Metrics()
        
        # Risk engine
        risk_limits = RiskLimits(
            max_daily_loss=config.risk.daily_loss_cap,
            max_consec_losses=config.risk.consec_loss_cap,
            a_min=1.0,
            a_cap=10.0
        )
        
        amount_policy = AmountPolicy(
            mode="fixed",
            fixed_a=config.risk.default_lot
        )
        
        risk_engine = RiskEngine(risk_limits, amount_policy)
        
        # Guardrails
        guardrails_cfg = GuardrailsConfig(
            cb_consecutive_losses=config.limits.max_consecutive_losses or 5
        )
        guardrails = Guardrails(guardrails_cfg)
        
        # Ensemble
        ensemble_state = EnsembleState()
        ensemble = Ensemble(ensemble_state)
        
        # Stratejileri yükle
        logger.info("Stratejiler yükleniyor...")
        StrategyRegistry.load_all()
        loaded_strategies = StrategyRegistry.list_ids()
        logger.info(f"Yüklenen stratejiler: {loaded_strategies}")
        
        # Scheduler
        def worker_factory(account_id, product, tf, **kwargs):
            from .worker import Worker
            
            connector = conn_manager.get(account_id)
            
            # Bu ürün için aktif stratejiler
            providers = []
            for prod_cfg in config.products:
                if prod_cfg.product == product:
                    for strat_id in prod_cfg.strategies:
                        try:
                            from .strategies.base import ProviderConfig
                            provider_cfg = ProviderConfig(
                                id=strat_id,
                                name=f"Strategy_{strat_id}",
                                group="unknown"
                            )
                            provider = StrategyRegistry.build(strat_id, cfg=provider_cfg)
                            providers.append(provider)
                        except Exception as e:
                            logger.warning(f"Strategy {strat_id} load failed: {e}")
            
            executor = OrderExecutor(
                connector=connector,
                storage=storage,
                risk_engine=risk_engine,
                guardrails=guardrails,
                locks={}
            )
            
            worker_cfg = WorkerConfig(
                lookback=config.engine.lookback,
                tick_ms=config.engine.tick_interval_ms
            )
            
            return Worker(
                account_id, product, tf,
                connector, storage, None, providers,
                ensemble, risk_engine, executor, worker_cfg
            )
        
        scheduler = Scheduler(worker_factory)
        
        # 4) API başlat
        logger.info("API başlatılıyor...")
        app = create_app(
            config, storage, scheduler, guardrails, metrics, conn_manager
        )
        
        # 5) Uvicorn ile servis başlat
        import uvicorn
        
        logger.info(f"Server starting on {config.ui.host}:{config.ui.port}")
        
        uvicorn_config = uvicorn.Config(
            app,
            host=config.ui.host,
            port=config.ui.port,
            log_level="info"
        )
        
        server = uvicorn.Server(uvicorn_config)
        await server.serve()
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    import sys
    
    config_file = sys.argv[1] if len(sys.argv) > 1 else "configs/config.example.yaml"
    
    asyncio.run(main(config_file))
