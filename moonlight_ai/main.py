"""
MoonLight AI Main Application
Ana uygulama başlatıcısı
"""

import asyncio
import argparse
import logging
import signal
import sys
from pathlib import Path

from core.engine import get_engine
from core.authentication.auth_manager import UserCredentials
from core.strategy_engine.simple_trend_strategy import SimpleTrendStrategy
from core.strategy_engine.base_strategy import StrategyConfig
from api.bridge.api_server import APIServer
from api.websocket.ws_server import WebSocketServer

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Logging ayarları"""
    # Log dizinini oluştur
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / 'moonlight.log')
        ]
    )


async def setup_demo_strategy(engine) -> None:
    """Demo strateji kurulumu"""
    try:
        # Basit trend stratejisi
        strategy_config = StrategyConfig(
            name="demo_trend",
            enabled=True,
            risk_per_trade=5.0,  # $5 per trade
            max_concurrent_trades=2,
            min_confidence=0.65,
            expiry_time=60,  # 1 dakika
            symbols=["EURUSD", "GBPUSD", "USDJPY"],
            parameters={
                'ema_short_period': 5,
                'ema_long_period': 20,
                'rsi_period': 14,
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'min_trend_strength': 0.0001
            }
        )
        
        strategy = SimpleTrendStrategy(strategy_config)
        engine.add_strategy(strategy)
        
        logger.info("Demo strateji eklendi")
        
    except Exception as e:
        logger.error(f"Demo strateji kurulum hatası: {e}")


async def run_server_mode(args) -> None:
    """Sunucu modunda çalıştır"""
    try:
        # Engine'i başlat
        engine = get_engine(args.config)
        
        if not await engine.initialize():
            logger.error("Engine başlatma başarısız")
            return
        
        # Demo strateji ekle
        await setup_demo_strategy(engine)
        
        # API sunucusu
        api_config = engine.config.get('api', {})
        api_server = APIServer(api_config)
        
        # WebSocket sunucusu
        ws_config = engine.config.get('websocket', {})
        ws_server = WebSocketServer(ws_config)
        
        # Sunucuları başlat
        await ws_server.start()
        
        logger.info("🌙 MoonLight AI başarıyla başlatıldı!")
        logger.info(f"📡 API Server: http://{api_config.get('host', 'localhost')}:{api_config.get('port', 8000)}")
        logger.info(f"🔌 WebSocket Server: ws://{ws_config.get('host', 'localhost')}:{ws_config.get('port', 8001)}")
        logger.info("📖 API Dokümantasyonu: http://localhost:8000/docs")
        
        # API sunucusunu başlat (blocking)
        await api_server.start()
        
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından durduruldu")
    except Exception as e:
        logger.error(f"Sunucu hatası: {e}")
    finally:
        # Temizlik
        if 'ws_server' in locals():
            await ws_server.stop()
        if 'engine' in locals():
            await engine.shutdown()


async def run_demo_mode(args) -> None:
    """Demo modunda çalıştır"""
    try:
        logger.info("🎯 Demo modu başlatılıyor...")
        
        # Engine'i başlat
        engine = get_engine(args.config)
        
        if not await engine.initialize():
            logger.error("Engine başlatma başarısız")
            return
        
        # Demo kullanıcı girişi
        demo_credentials = UserCredentials(
            email="demo@moonlight.ai",
            password="demo123",
            broker="demo",
            demo_account=True
        )
        
        if not await engine.authenticate_user(demo_credentials):
            logger.error("Demo kullanıcı girişi başarısız")
            return
        
        logger.info("✅ Demo kullanıcı girişi başarılı")
        
        # Demo strateji ekle
        await setup_demo_strategy(engine)
        
        # Market connector simülasyonu (gerçek uygulamada gerçek connector kullanılacak)
        logger.info("📊 Market connector simülasyonu başlatılıyor...")
        
        # Demo veri üretimi
        from core.market_connector.base_connector import MarketData
        from datetime import datetime
        import random
        
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        base_prices = {"EURUSD": 1.0850, "GBPUSD": 1.2650, "USDJPY": 149.50}
        
        logger.info("🚀 Demo işlem başlatılıyor...")
        
        # Sonsuz döngü - demo veri üretimi
        while True:
            for symbol in symbols:
                # Rastgele fiyat değişimi
                base_price = base_prices[symbol]
                change = random.uniform(-0.001, 0.001)
                new_price = base_price + change
                base_prices[symbol] = new_price
                
                # Spread hesapla
                spread = random.uniform(0.0001, 0.0003)
                bid = new_price - spread/2
                ask = new_price + spread/2
                
                # Market data oluştur
                market_data = MarketData(
                    symbol=symbol,
                    timestamp=datetime.utcnow(),
                    bid=bid,
                    ask=ask,
                    last=new_price,
                    volume=random.uniform(100, 1000)
                )
                
                # Stratejilere gönder
                await engine._on_market_data(market_data)
            
            # 1 saniye bekle
            await asyncio.sleep(1.0)
        
    except KeyboardInterrupt:
        logger.info("Demo modu durduruldu")
    except Exception as e:
        logger.error(f"Demo modu hatası: {e}")
    finally:
        if 'engine' in locals():
            await engine.shutdown()


async def main():
    """Ana fonksiyon"""
    parser = argparse.ArgumentParser(description='MoonLight AI - Fixed Time Trading System')
    parser.add_argument('--mode', choices=['server', 'demo'], default='server',
                       help='Çalışma modu (varsayılan: server)')
    parser.add_argument('--config', default='config/config.yaml',
                       help='Konfigürasyon dosyası (varsayılan: config/config.yaml)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Log seviyesi (varsayılan: INFO)')
    parser.add_argument('--host', default='localhost',
                       help='API sunucu host (varsayılan: localhost)')
    parser.add_argument('--port', type=int, default=8000,
                       help='API sunucu port (varsayılan: 8000)')
    
    args = parser.parse_args()
    
    # Logging ayarla
    setup_logging(args.log_level)
    
    # Başlık
    print("=" * 60)
    print("🌙 MoonLight AI - Fixed Time Trading System")
    print("=" * 60)
    print(f"Mod: {args.mode}")
    print(f"Konfigürasyon: {args.config}")
    print(f"Log Seviyesi: {args.log_level}")
    print("=" * 60)
    print()
    
    # Signal handler
    def signal_handler(signum, frame):
        logger.info(f"Signal alındı: {signum}")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.mode == 'server':
            await run_server_mode(args)
        elif args.mode == 'demo':
            await run_demo_mode(args)
        else:
            logger.error(f"Bilinmeyen mod: {args.mode}")
            sys.exit(1)
    
    except Exception as e:
        logger.error(f"Uygulama hatası: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())