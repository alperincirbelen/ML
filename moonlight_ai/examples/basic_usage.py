"""
MoonLight AI Basic Usage Example
Temel kullanım örneği
"""

import asyncio
import logging
from pathlib import Path
import sys

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.engine import get_engine
from core.authentication.auth_manager import UserCredentials
from core.strategy_engine.simple_trend_strategy import SimpleTrendStrategy
from core.strategy_engine.base_strategy import StrategyConfig
from core.market_connector.base_connector import MarketData
from datetime import datetime
import random

# Logging ayarla
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_example():
    """Temel kullanım örneği"""
    try:
        logger.info("🌙 MoonLight AI Temel Kullanım Örneği")
        
        # 1. Engine'i başlat
        engine = get_engine()
        await engine.initialize()
        logger.info("✅ Engine başlatıldı")
        
        # 2. Kullanıcı girişi
        credentials = UserCredentials(
            email="demo@example.com",
            password="demo123",
            broker="demo_broker",
            demo_account=True
        )
        
        success = await engine.authenticate_user(credentials)
        if success:
            logger.info("✅ Kullanıcı girişi başarılı")
        else:
            logger.error("❌ Kullanıcı girişi başarısız")
            return
        
        # 3. Strateji oluştur ve ekle
        strategy_config = StrategyConfig(
            name="example_strategy",
            enabled=True,
            risk_per_trade=10.0,
            max_concurrent_trades=3,
            min_confidence=0.7,
            expiry_time=60,
            symbols=["EURUSD", "GBPUSD"],
            parameters={
                'ema_short_period': 5,
                'ema_long_period': 20,
                'rsi_period': 14
            }
        )
        
        strategy = SimpleTrendStrategy(strategy_config)
        engine.add_strategy(strategy)
        logger.info("✅ Strateji eklendi")
        
        # 4. Market data simülasyonu
        logger.info("📊 Market data simülasyonu başlatılıyor...")
        
        base_prices = {"EURUSD": 1.0850, "GBPUSD": 1.2650}
        
        for i in range(50):  # 50 tick simüle et
            for symbol in ["EURUSD", "GBPUSD"]:
                # Rastgele fiyat değişimi
                change = random.uniform(-0.0005, 0.0005)
                base_prices[symbol] += change
                
                # Market data oluştur
                market_data = MarketData(
                    symbol=symbol,
                    timestamp=datetime.utcnow(),
                    bid=base_prices[symbol] - 0.0001,
                    ask=base_prices[symbol] + 0.0001,
                    last=base_prices[symbol],
                    volume=random.uniform(100, 1000)
                )
                
                # Engine'e gönder
                await engine._on_market_data(market_data)
            
            # Kısa bekleme
            await asyncio.sleep(0.1)
        
        # 5. Strateji durumunu kontrol et
        logger.info("📊 Strateji Durumu:")
        for name, strategy in engine.strategies.items():
            status = strategy.status
            logger.info(f"  {name}:")
            logger.info(f"    Aktif: {status['active']}")
            logger.info(f"    Toplam Sinyal: {status['total_signals']}")
            logger.info(f"    Başarı Oranı: %{status['win_rate_percentage']:.1f}")
        
        # 6. Risk durumunu kontrol et
        if engine.risk_manager:
            risk_report = engine.risk_manager.get_risk_report()
            logger.info("⚠️ Risk Durumu:")
            logger.info(f"    Risk Seviyesi: {risk_report['metrics']['risk_level']}")
            logger.info(f"    Aktif İşlem: {risk_report['metrics']['active_trades']}")
            logger.info(f"    Toplam İşlem: {risk_report['metrics']['total_trades']}")
        
        logger.info("✅ Örnek tamamlandı")
        
    except Exception as e:
        logger.error(f"❌ Örnek hatası: {e}")
    
    finally:
        # Temizlik
        if 'engine' in locals():
            await engine.shutdown()


if __name__ == "__main__":
    asyncio.run(basic_example())