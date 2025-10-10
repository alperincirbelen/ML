"""
MoonLight AI Core Engine
Ana sistem motoru - tüm bileşenleri koordine eder
"""

import asyncio
import logging
import signal
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import yaml

from .market_connector.base_connector import BaseConnector, MarketData, TradeSignal
from .authentication.auth_manager import AuthManager, UserCredentials, AuthSession
from .strategy_engine.base_strategy import BaseStrategy
from .risk_manager.risk_manager import RiskManager
from .executor.trade_executor import TradeExecutor
from .persistence.data_manager import DataManager

logger = logging.getLogger(__name__)


class EngineState:
    """Motor durumu"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class MoonLightEngine:
    """
    MoonLight AI Ana Motoru
    Tüm sistem bileşenlerini koordine eder ve yönetir
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.state = EngineState.STOPPED
        
        # Bileşenler
        self.auth_manager: Optional[AuthManager] = None
        self.market_connector: Optional[BaseConnector] = None
        self.strategies: Dict[str, BaseStrategy] = {}
        self.risk_manager: Optional[RiskManager] = None
        self.trade_executor: Optional[TradeExecutor] = None
        self.data_manager: Optional[DataManager] = None
        
        # Olay dinleyicileri
        self.event_handlers: Dict[str, List[Callable]] = {
            'market_data': [],
            'trade_signal': [],
            'trade_result': [],
            'error': [],
            'state_change': []
        }
        
        # Aktif oturum
        self.current_session: Optional[AuthSession] = None
        
        # Async görevler
        self._tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
        logger.info("MoonLight Engine başlatıldı")
    
    def _load_config(self) -> Dict[str, Any]:
        """Konfigürasyon dosyasını yükle"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Konfigürasyon yüklendi: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"Konfigürasyon yükleme hatası: {e}")
            # Varsayılan konfigürasyon
            return {
                'system': {'name': 'MoonLight AI', 'version': '0.1.0'},
                'risk_management': {},
                'logging': {'level': 'INFO'}
            }
    
    async def initialize(self) -> bool:
        """
        Sistem bileşenlerini başlat
        Returns: Başlatma başarılı ise True
        """
        try:
            self._set_state(EngineState.STARTING)
            logger.info("Sistem bileşenleri başlatılıyor...")
            
            # Authentication Manager
            self.auth_manager = AuthManager(self.config.get('security', {}))
            
            # Risk Manager
            self.risk_manager = RiskManager(self.config)
            
            # Data Manager
            self.data_manager = DataManager(self.config.get('database', {}))
            await self.data_manager.initialize()
            
            # Trade Executor
            self.trade_executor = TradeExecutor(self.config)
            
            logger.info("Sistem bileşenleri başarıyla başlatıldı")
            return True
            
        except Exception as e:
            logger.error(f"Sistem başlatma hatası: {e}")
            self._set_state(EngineState.ERROR)
            return False
    
    async def authenticate_user(self, credentials: UserCredentials) -> bool:
        """
        Kullanıcı kimlik doğrulama
        Args:
            credentials: Kullanıcı kimlik bilgileri
        Returns: Kimlik doğrulama başarılı ise True
        """
        try:
            if not self.auth_manager:
                raise Exception("AuthManager başlatılmamış")
            
            session = await self.auth_manager.authenticate(credentials)
            if session:
                self.current_session = session
                logger.info(f"Kullanıcı girişi başarılı: {credentials.email}")
                return True
            else:
                logger.warning(f"Kullanıcı girişi başarısız: {credentials.email}")
                return False
                
        except Exception as e:
            logger.error(f"Kimlik doğrulama hatası: {e}")
            return False
    
    async def connect_market(self, connector: BaseConnector) -> bool:
        """
        Piyasa bağlantısı kurma
        Args:
            connector: Market connector instance
        Returns: Bağlantı başarılı ise True
        """
        try:
            if not self.current_session:
                raise Exception("Kullanıcı girişi yapılmamış")
            
            # Market connector'ı ayarla
            self.market_connector = connector
            
            # Olay dinleyicilerini ekle
            self.market_connector.add_callback('market_data', self._on_market_data)
            self.market_connector.add_callback('trade_result', self._on_trade_result)
            self.market_connector.add_callback('error', self._on_error)
            
            # Bağlantıyı başlat
            await self.market_connector.start()
            
            # Kimlik doğrulama
            credentials = {
                'email': self.current_session.email,
                'password': '***'  # Gerçek şifre auth_manager'da saklanır
            }
            
            if not await self.market_connector.authenticate(credentials):
                raise Exception("Market connector kimlik doğrulama başarısız")
            
            logger.info("Piyasa bağlantısı kuruldu")
            return True
            
        except Exception as e:
            logger.error(f"Piyasa bağlantı hatası: {e}")
            return False
    
    def add_strategy(self, strategy: BaseStrategy) -> None:
        """
        Strateji ekle
        Args:
            strategy: Strateji instance
        """
        try:
            self.strategies[strategy.config.name] = strategy
            logger.info(f"Strateji eklendi: {strategy.config.name}")
        except Exception as e:
            logger.error(f"Strateji ekleme hatası: {e}")
    
    def remove_strategy(self, strategy_name: str) -> bool:
        """
        Strateji kaldır
        Args:
            strategy_name: Strateji adı
        Returns: Kaldırma başarılı ise True
        """
        try:
            if strategy_name in self.strategies:
                strategy = self.strategies[strategy_name]
                strategy.stop()
                del self.strategies[strategy_name]
                logger.info(f"Strateji kaldırıldı: {strategy_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Strateji kaldırma hatası: {e}")
            return False
    
    async def start_trading(self, symbols: List[str]) -> bool:
        """
        İşlem başlatma
        Args:
            symbols: Takip edilecek semboller
        Returns: Başlatma başarılı ise True
        """
        try:
            if not self.market_connector:
                raise Exception("Market connector bağlı değil")
            
            if not self.strategies:
                raise Exception("Aktif strateji yok")
            
            # Piyasa verisi aboneliği
            if not await self.market_connector.subscribe_market_data(symbols):
                raise Exception("Piyasa verisi aboneliği başarısız")
            
            # Stratejileri başlat
            for strategy in self.strategies.values():
                if strategy.config.enabled:
                    strategy.start()
            
            # Ana döngüyü başlat
            self._tasks.append(asyncio.create_task(self._main_loop()))
            
            self._set_state(EngineState.RUNNING)
            logger.info(f"İşlem başlatıldı - Semboller: {symbols}")
            return True
            
        except Exception as e:
            logger.error(f"İşlem başlatma hatası: {e}")
            self._set_state(EngineState.ERROR)
            return False
    
    async def stop_trading(self) -> None:
        """İşlem durdurma"""
        try:
            self._set_state(EngineState.STOPPING)
            logger.info("İşlem durduruluyor...")
            
            # Shutdown event'ini ayarla
            self._shutdown_event.set()
            
            # Stratejileri durdur
            for strategy in self.strategies.values():
                strategy.stop()
            
            # Görevleri iptal et
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Görevlerin bitmesini bekle
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            self._tasks.clear()
            
            # Market connector'ı durdur
            if self.market_connector:
                await self.market_connector.stop()
            
            self._set_state(EngineState.STOPPED)
            logger.info("İşlem durduruldu")
            
        except Exception as e:
            logger.error(f"İşlem durdurma hatası: {e}")
            self._set_state(EngineState.ERROR)
    
    async def _main_loop(self) -> None:
        """Ana işlem döngüsü"""
        try:
            logger.info("Ana işlem döngüsü başlatıldı")
            
            while not self._shutdown_event.is_set():
                try:
                    # Periyodik görevler
                    await self._periodic_tasks()
                    
                    # Kısa bekleme
                    await asyncio.sleep(1.0)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Ana döngü hatası: {e}")
                    await asyncio.sleep(5.0)
            
            logger.info("Ana işlem döngüsü durduruldu")
            
        except Exception as e:
            logger.error(f"Ana döngü kritik hatası: {e}")
            self._set_state(EngineState.ERROR)
    
    async def _periodic_tasks(self) -> None:
        """Periyodik görevler"""
        try:
            # Süresi dolmuş oturumları temizle
            if self.auth_manager:
                await self.auth_manager.cleanup_expired_sessions()
            
            # Veri tabanı bakımı
            if self.data_manager:
                await self.data_manager.maintenance()
                
        except Exception as e:
            logger.error(f"Periyodik görev hatası: {e}")
    
    async def _on_market_data(self, market_data: MarketData) -> None:
        """Piyasa verisi olay işleyicisi"""
        try:
            # Stratejilere gönder
            for strategy in self.strategies.values():
                if strategy.is_active and market_data.symbol in strategy.config.symbols:
                    signal = await strategy.update_market_data(market_data)
                    
                    if signal:
                        await self._on_trade_signal(signal)
            
            # Olay dinleyicilerini bilgilendir
            await self._emit_event('market_data', market_data)
            
        except Exception as e:
            logger.error(f"Piyasa verisi işleme hatası: {e}")
    
    async def _on_trade_signal(self, signal: TradeSignal) -> None:
        """İşlem sinyali olay işleyicisi"""
        try:
            if not self.risk_manager or not self.trade_executor:
                logger.warning("Risk manager veya trade executor mevcut değil")
                return
            
            # Bakiye kontrolü
            balance_info = await self.market_connector.get_balance()
            current_balance = balance_info.get('balance', 0.0)
            
            # Risk doğrulaması
            validation = await self.risk_manager.validate_trade(signal, current_balance)
            
            if validation['approved']:
                # Pozisyon boyutunu güncelle
                signal.amount = validation['suggested_amount']
                
                # İşlemi yürüt
                result = await self.trade_executor.execute_trade(signal)
                
                if result.get('success', False):
                    # Risk manager'a kaydet
                    trade_id = await self.risk_manager.register_trade(signal)
                    result['trade_id'] = trade_id
                
                await self._emit_event('trade_result', result)
            else:
                logger.info(f"İşlem reddedildi: {validation['reason']}")
            
            # Sinyal olayını yayınla
            await self._emit_event('trade_signal', {
                'signal': signal,
                'validation': validation
            })
            
        except Exception as e:
            logger.error(f"İşlem sinyali işleme hatası: {e}")
    
    async def _on_trade_result(self, result: Dict[str, Any]) -> None:
        """İşlem sonucu olay işleyicisi"""
        try:
            trade_id = result.get('trade_id')
            if trade_id and self.risk_manager:
                await self.risk_manager.close_trade(trade_id, result)
            
            # Veri tabanına kaydet
            if self.data_manager:
                await self.data_manager.save_trade_result(result)
            
            await self._emit_event('trade_result', result)
            
        except Exception as e:
            logger.error(f"İşlem sonucu işleme hatası: {e}")
    
    async def _on_error(self, error_data: Dict[str, Any]) -> None:
        """Hata olay işleyicisi"""
        try:
            logger.error(f"Sistem hatası: {error_data}")
            await self._emit_event('error', error_data)
        except Exception as e:
            logger.error(f"Hata işleme hatası: {e}")
    
    def _set_state(self, new_state: str) -> None:
        """Motor durumunu değiştir"""
        old_state = self.state
        self.state = new_state
        
        logger.info(f"Motor durumu değişti: {old_state} -> {new_state}")
        
        # Durum değişikliği olayını yayınla
        asyncio.create_task(self._emit_event('state_change', {
            'old_state': old_state,
            'new_state': new_state,
            'timestamp': datetime.utcnow()
        }))
    
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Olay dinleyici ekle"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)
        else:
            logger.warning(f"Bilinmeyen olay türü: {event_type}")
    
    def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """Olay dinleyici kaldır"""
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
    
    async def _emit_event(self, event_type: str, data: Any) -> None:
        """Olay yayınla"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Olay işleyici hatası ({event_type}): {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Sistem durumu"""
        status = {
            'state': self.state,
            'timestamp': datetime.utcnow().isoformat(),
            'session': None,
            'market_connected': False,
            'strategies': {},
            'risk_metrics': None
        }
        
        # Oturum bilgisi
        if self.current_session:
            status['session'] = {
                'email': self.current_session.email,
                'broker': self.current_session.broker,
                'demo_account': self.current_session.demo_account,
                'expires_at': self.current_session.expires_at.isoformat(),
                'time_remaining': self.current_session.time_remaining
            }
        
        # Market bağlantısı
        if self.market_connector:
            status['market_connected'] = self.market_connector.is_connected
        
        # Strateji durumları
        for name, strategy in self.strategies.items():
            status['strategies'][name] = strategy.status
        
        # Risk metrikleri
        if self.risk_manager:
            status['risk_metrics'] = self.risk_manager.get_risk_report()
        
        return status
    
    async def shutdown(self) -> None:
        """Sistemi kapat"""
        try:
            logger.info("Sistem kapatılıyor...")
            
            # İşlemleri durdur
            if self.state == EngineState.RUNNING:
                await self.stop_trading()
            
            # Oturumu kapat
            if self.current_session and self.auth_manager:
                await self.auth_manager.logout(self.current_session.token)
            
            # Veri tabanı bağlantısını kapat
            if self.data_manager:
                await self.data_manager.close()
            
            logger.info("Sistem kapatıldı")
            
        except Exception as e:
            logger.error(f"Sistem kapatma hatası: {e}")


# Singleton instance
_engine_instance: Optional[MoonLightEngine] = None


def get_engine(config_path: str = "config/config.yaml") -> MoonLightEngine:
    """
    Engine singleton instance
    Args:
        config_path: Konfigürasyon dosyası yolu
    Returns: MoonLightEngine instance
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = MoonLightEngine(config_path)
    return _engine_instance


async def main():
    """Ana fonksiyon - test amaçlı"""
    # Logging ayarla
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Engine'i başlat
    engine = get_engine()
    
    # Signal handler'ları ayarla
    def signal_handler(signum, frame):
        logger.info(f"Signal alındı: {signum}")
        asyncio.create_task(engine.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Sistem bileşenlerini başlat
        if await engine.initialize():
            logger.info("MoonLight AI başarıyla başlatıldı")
            
            # Sonsuz döngü - gerçek uygulamada API server burada çalışır
            while engine.state != EngineState.STOPPED:
                await asyncio.sleep(1.0)
        else:
            logger.error("Sistem başlatma başarısız")
            
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından durduruldu")
    except Exception as e:
        logger.error(f"Beklenmeyen hata: {e}")
    finally:
        await engine.shutdown()


if __name__ == "__main__":
    asyncio.run(main())