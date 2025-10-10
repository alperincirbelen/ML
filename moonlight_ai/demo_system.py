"""
MoonLight AI Demo System
Sistem demo ve test scripti
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

# Proje kök dizinini Python path'ine ekle
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.engine import get_engine
from core.authentication.auth_manager import UserCredentials
from core.strategy_engine.simple_trend_strategy import SimpleTrendStrategy
from core.strategy_engine.base_strategy import StrategyConfig
from core.market_connector.base_connector import MarketData, TradeSignal

# Logging ayarla
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DemoMarketConnector:
    """Demo market connector - gerçek veri simülasyonu"""
    
    def __init__(self):
        self.is_connected = False
        self.is_authenticated = False
        self.callbacks = {}
        self.symbols = []
        self.running = False
        
        # Simülasyon verileri
        self.base_prices = {
            "EURUSD": 1.0850,
            "GBPUSD": 1.2650,
            "USDJPY": 149.50
        }
        
        self.price_history = {symbol: [] for symbol in self.base_prices.keys()}
    
    async def connect(self):
        """Bağlantı simülasyonu"""
        await asyncio.sleep(0.1)
        self.is_connected = True
        logger.info("📡 Demo market connector bağlandı")
        return True
    
    async def disconnect(self):
        """Bağlantı kesme"""
        self.is_connected = False
        self.running = False
        logger.info("📡 Demo market connector bağlantısı kesildi")
    
    async def authenticate(self, credentials):
        """Kimlik doğrulama simülasyonu"""
        await asyncio.sleep(0.1)
        self.is_authenticated = True
        logger.info("🔐 Demo market connector kimlik doğrulaması başarılı")
        return True
    
    async def subscribe_market_data(self, symbols):
        """Market data aboneliği"""
        self.symbols = symbols
        logger.info(f"📊 Market data aboneliği: {', '.join(symbols)}")
        
        # Veri akışını başlat
        asyncio.create_task(self._start_data_feed())
        return True
    
    async def place_trade(self, signal):
        """İşlem açma simülasyonu"""
        await asyncio.sleep(0.1)
        
        # Rastgele sonuç (gerçekçi başarı oranı)
        success_rate = 0.65  # %65 başarı oranı
        is_successful = random.random() < success_rate
        
        if is_successful:
            profit = signal.amount * 0.85  # %85 payout
            result = {
                'success': True,
                'trade_id': f'demo_trade_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}',
                'symbol': signal.symbol,
                'direction': signal.direction,
                'amount': signal.amount,
                'profit': profit,
                'loss': 0.0,
                'payout_percentage': 85.0,
                'start_time': datetime.utcnow().isoformat(),
                'expiry_time': signal.expiry_time,
                'status': 'completed'
            }
            logger.info(f"✅ Demo işlem başarılı: {signal.symbol} {signal.direction} "
                       f"Kar: ${profit:.2f}")
        else:
            result = {
                'success': False,
                'trade_id': f'demo_trade_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}',
                'symbol': signal.symbol,
                'direction': signal.direction,
                'amount': signal.amount,
                'profit': 0.0,
                'loss': signal.amount,
                'payout_percentage': 0.0,
                'start_time': datetime.utcnow().isoformat(),
                'expiry_time': signal.expiry_time,
                'status': 'completed'
            }
            logger.info(f"❌ Demo işlem başarısız: {signal.symbol} {signal.direction} "
                       f"Zarar: ${signal.amount:.2f}")
        
        # Callback'i çağır
        if 'trade_result' in self.callbacks:
            for callback in self.callbacks['trade_result']:
                await callback(result)
        
        return result
    
    async def get_balance(self):
        """Bakiye simülasyonu"""
        return {'balance': 1000.0, 'demo': True}
    
    async def get_trade_history(self, limit=100):
        """İşlem geçmişi simülasyonu"""
        return []
    
    def add_callback(self, event_type, callback):
        """Callback ekle"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    async def _start_data_feed(self):
        """Veri akışını başlat"""
        self.running = True
        logger.info("📈 Demo veri akışı başlatıldı")
        
        while self.running:
            try:
                for symbol in self.symbols:
                    # Rastgele fiyat değişimi
                    base_price = self.base_prices[symbol]
                    
                    # Trend simülasyonu
                    trend_factor = random.uniform(-0.0005, 0.0005)
                    noise_factor = random.uniform(-0.0002, 0.0002)
                    
                    new_price = base_price + trend_factor + noise_factor
                    self.base_prices[symbol] = new_price
                    
                    # Spread hesapla
                    spread = random.uniform(0.00005, 0.0002)
                    bid = new_price - spread/2
                    ask = new_price + spread/2
                    
                    # Market data oluştur
                    market_data = MarketData(
                        symbol=symbol,
                        timestamp=datetime.utcnow(),
                        bid=bid,
                        ask=ask,
                        last=new_price,
                        volume=random.uniform(500, 2000)
                    )
                    
                    # Geçmişe ekle
                    self.price_history[symbol].append(new_price)
                    if len(self.price_history[symbol]) > 1000:
                        self.price_history[symbol] = self.price_history[symbol][-1000:]
                    
                    # Callback'leri çağır
                    if 'market_data' in self.callbacks:
                        for callback in self.callbacks['market_data']:
                            await callback(market_data)
                
                # 1 saniye bekle
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Veri akışı hatası: {e}")
                await asyncio.sleep(1.0)


async def run_demo():
    """Demo sistemi çalıştır"""
    try:
        print("🌙 MoonLight AI Demo Sistemi")
        print("=" * 50)
        
        # Engine'i başlat
        engine = get_engine()
        await engine.initialize()
        logger.info("✅ Engine başlatıldı")
        
        # Demo kullanıcı girişi
        demo_credentials = UserCredentials(
            email="demo@moonlight.ai",
            password="demo123",
            broker="demo_broker",
            demo_account=True
        )
        
        success = await engine.authenticate_user(demo_credentials)
        if not success:
            logger.error("❌ Demo kullanıcı girişi başarısız")
            return
        
        logger.info("✅ Demo kullanıcı girişi başarılı")
        
        # Demo market connector
        market_connector = DemoMarketConnector()
        await engine.connect_market(market_connector)
        logger.info("✅ Demo market connector bağlandı")
        
        # Demo strateji oluştur
        strategy_config = StrategyConfig(
            name="demo_trend_strategy",
            enabled=True,
            risk_per_trade=10.0,
            max_concurrent_trades=2,
            min_confidence=0.7,
            expiry_time=60,
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
        logger.info("✅ Demo strateji eklendi")
        
        # İşlem başlat
        success = await engine.start_trading(["EURUSD", "GBPUSD", "USDJPY"])
        if not success:
            logger.error("❌ İşlem başlatma başarısız")
            return
        
        logger.info("🚀 Demo işlem başlatıldı")
        
        # Demo çalıştırma süresi
        demo_duration = 300  # 5 dakika
        start_time = datetime.utcnow()
        
        print(f"\n📊 Demo {demo_duration} saniye çalışacak...")
        print("📈 Gerçek zamanlı sinyal ve işlem takibi:")
        print("-" * 50)
        
        # Ana döngü
        while (datetime.utcnow() - start_time).total_seconds() < demo_duration:
            try:
                # Sistem durumunu göster
                status = engine.get_status()
                
                # Strateji istatistikleri
                for name, strategy in engine.strategies.items():
                    strategy_status = strategy.status
                    if strategy_status['total_signals'] > 0:
                        print(f"📊 {name}: "
                              f"Sinyal: {strategy_status['total_signals']}, "
                              f"Başarı: %{strategy_status['win_rate_percentage']:.1f}")
                
                # Risk durumu
                if engine.risk_manager:
                    risk_report = engine.risk_manager.get_risk_report()
                    metrics = risk_report['metrics']
                    print(f"⚠️  Risk: Günlük P&L: ${metrics['daily_pnl']:.2f}, "
                          f"Aktif: {metrics['active_trades']}, "
                          f"Seviye: {metrics['risk_level'].upper()}")
                
                print("-" * 50)
                
                # 30 saniye bekle
                await asyncio.sleep(30.0)
                
            except KeyboardInterrupt:
                print("\n⚠️ Demo kullanıcı tarafından durduruldu")
                break
            except Exception as e:
                logger.error(f"Demo döngü hatası: {e}")
                await asyncio.sleep(5.0)
        
        # Demo sonuçları
        print(f"\n🏁 Demo tamamlandı!")
        print("=" * 50)
        
        # Final istatistikler
        for name, strategy in engine.strategies.items():
            strategy_status = strategy.status
            print(f"📊 {name} Final İstatistikleri:")
            print(f"   Toplam Sinyal: {strategy_status['total_signals']}")
            print(f"   Başarı Oranı: %{strategy_status['win_rate_percentage']:.1f}")
            print(f"   Son Güncelleme: {strategy_status['last_update_time']}")
        
        # Risk raporu
        if engine.risk_manager:
            risk_report = engine.risk_manager.get_risk_report()
            metrics = risk_report['metrics']
            print(f"\n⚠️ Final Risk Raporu:")
            print(f"   Günlük P&L: ${metrics['daily_pnl']:.2f}")
            print(f"   Toplam İşlem: {metrics['total_trades']}")
            print(f"   Kazanma Oranı: %{metrics['win_rate']:.1f}")
            print(f"   Risk Seviyesi: {metrics['risk_level'].upper()}")
        
        # İşlem durdur
        await engine.stop_trading()
        logger.info("🛑 Demo işlem durduruldu")
        
    except Exception as e:
        logger.error(f"❌ Demo sistemi hatası: {e}")
    finally:
        # Temizlik
        if 'engine' in locals():
            await engine.shutdown()
        logger.info("🧹 Demo sistemi temizlendi")


async def main():
    """Ana fonksiyon"""
    try:
        await run_demo()
    except KeyboardInterrupt:
        print("\n👋 Demo sistemi kapatıldı")
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")


if __name__ == "__main__":
    asyncio.run(main())