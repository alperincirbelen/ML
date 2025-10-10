#!/usr/bin/env python3
"""
MoonLight Paper Trading Quick Start

Paper modda hızlı test için kullanışlı script
"""

import asyncio
import argparse
from pathlib import Path

from moonlight.core.config import load_config
from moonlight.core.storage import Storage
from moonlight.core.connector.mock import MockConnector
from moonlight.core.telemetry import StructuredLogger
from moonlight.core.strategies.registry import load_all


async def run_paper_session(config_path: str, duration_minutes: int = 10):
    """
    Paper trading session çalıştır
    
    Args:
        config_path: Konfig dosya yolu
        duration_minutes: Çalıştırma süresi (dakika)
    """
    logger = StructuredLogger("paper", level="INFO", log_file="logs/paper.log")
    
    # Konfig yükle
    logger.info("paper.start", "Loading configuration", path=config_path)
    config = load_config(config_path)
    
    if config.mode != "paper":
        logger.warn("paper.mode", "Config mode is not 'paper', forcing paper mode")
        config.mode = "paper"
    
    # Storage başlat
    storage = Storage(config.storage.sqlite_path)
    await storage.init()
    logger.info("paper.storage", "Database initialized")
    
    # Stratejileri yükle
    load_all()
    from moonlight.core.strategies.registry import list_strategies
    loaded_strategies = list_strategies()
    logger.info("paper.strategies", "Strategies loaded", count=len(loaded_strategies))
    
    # Mock connector
    connector = MockConnector("paper_test", seed=42)
    await connector.login("paper@test.com", "test")
    logger.info("paper.connector", "Mock connector ready")
    
    # Basit loop: her 30 saniyede bir durum raporu
    logger.info("paper.session", f"Running paper session for {duration_minutes} minutes")
    
    iterations = duration_minutes * 2  # 30 sn aralıklar
    
    for i in range(iterations):
        await asyncio.sleep(30)
        
        # Durum kontrolü
        open_orders = await storage.open_orders()
        recent = await storage.recent_trades(limit=5)
        
        logger.info("paper.tick", 
                   f"Iteration {i+1}/{iterations}",
                   open_orders=len(open_orders),
                   recent_trades=len(recent))
        
        # Basit metrik
        if recent:
            wins = sum(1 for t in recent if t.get('status') == 'win')
            wr = wins / len(recent) if recent else 0
            logger.info("paper.metrics", "Recent performance", 
                       trades=len(recent), win_rate=f"{wr:.2%}")
    
    logger.info("paper.end", "Session completed")
    
    await connector.close()
    await storage.close()


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="MoonLight Paper Trading")
    parser.add_argument("-c", "--config", default="configs/app.yaml",
                       help="Config file path")
    parser.add_argument("-d", "--duration", type=int, default=10,
                       help="Duration in minutes")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MoonLight - Paper Trading Session")
    print("=" * 60)
    print(f"Config: {args.config}")
    print(f"Duration: {args.duration} minutes")
    print()
    
    try:
        asyncio.run(run_paper_session(args.config, args.duration))
        print("\n✓ Paper session completed successfully")
    
    except KeyboardInterrupt:
        print("\n✓ Stopped by user")
    
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


if __name__ == "__main__":
    main()
