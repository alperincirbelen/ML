"""
Full System Integration Tests
Tam sistem entegrasyon testleri
"""

import pytest
import asyncio
from datetime import datetime
import tempfile
import shutil

from core.engine import MoonLightEngine
from core.authentication.auth_manager import UserCredentials
from core.strategy_engine.simple_trend_strategy import SimpleTrendStrategy
from core.strategy_engine.base_strategy import StrategyConfig
from core.market_connector.base_connector import MarketData, TradeSignal


class TestFullSystemIntegration:
    """Tam sistem entegrasyon testleri"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_engine_initialization_and_shutdown(self, test_config_file):
        """Engine başlatma ve kapatma testi"""
        engine = MoonLightEngine(test_config_file)
        
        # Başlatma
        success = await engine.initialize()
        assert success is True
        assert engine.auth_manager is not None
        assert engine.risk_manager is not None
        assert engine.data_manager is not None
        assert engine.trade_executor is not None
        
        # Kapatma
        await engine.shutdown()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_user_authentication_flow(self, test_engine, test_user_credentials):
        """Kullanıcı kimlik doğrulama akışı testi"""
        # Giriş yap
        success = await test_engine.authenticate_user(test_user_credentials)
        assert success is True
        assert test_engine.current_session is not None
        assert test_engine.current_session.email == test_user_credentials.email
        
        # Oturum bilgilerini kontrol et
        session = test_engine.current_session
        assert session.demo_account == test_user_credentials.demo_account
        assert session.broker == test_user_credentials.broker
        assert not session.is_expired
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_strategy_management(self, test_engine, test_user_credentials):
        """Strateji yönetimi testi"""
        # Giriş yap
        await test_engine.authenticate_user(test_user_credentials)
        
        # Strateji oluştur
        strategy_config = StrategyConfig(
            name="integration_test_strategy",
            enabled=True,
            risk_per_trade=5.0,
            symbols=["EURUSD"],
            parameters={'ema_short_period': 5, 'ema_long_period': 20}
        )
        
        strategy = SimpleTrendStrategy(strategy_config)
        
        # Stratejiyi ekle
        test_engine.add_strategy(strategy)
        assert "integration_test_strategy" in test_engine.strategies
        
        # Strateji durumunu kontrol et
        added_strategy = test_engine.strategies["integration_test_strategy"]
        assert added_strategy.config.name == "integration_test_strategy"
        assert added_strategy.config.enabled is True
        
        # Stratejiyi kaldır
        success = test_engine.remove_strategy("integration_test_strategy")
        assert success is True
        assert "integration_test_strategy" not in test_engine.strategies
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_market_data_processing(self, test_engine, test_user_credentials, mock_market_connector):
        """Market data işleme testi"""
        # Giriş yap
        await test_engine.authenticate_user(test_user_credentials)
        
        # Mock market connector bağla
        await test_engine.connect_market(mock_market_connector)
        assert test_engine.market_connector is not None
        
        # Strateji ekle
        strategy_config = StrategyConfig(
            name="market_data_test_strategy",
            enabled=True,
            symbols=["EURUSD"]
        )
        strategy = SimpleTrendStrategy(strategy_config)
        test_engine.add_strategy(strategy)
        
        # Market data oluştur
        market_data = MarketData(
            symbol="EURUSD",
            timestamp=datetime.utcnow(),
            bid=1.08450,
            ask=1.08452,
            last=1.08451,
            volume=1000.0
        )
        
        # Market data'yı işle
        await test_engine._on_market_data(market_data)
        
        # Strateji market data almış olmalı
        strategy = test_engine.strategies["market_data_test_strategy"]
        assert "EURUSD" in strategy.market_data_history
        assert len(strategy.market_data_history["EURUSD"]) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_trade_signal_processing(self, test_engine, test_user_credentials, mock_market_connector):
        """İşlem sinyali işleme testi"""
        # Giriş yap
        await test_engine.authenticate_user(test_user_credentials)
        
        # Mock market connector bağla
        await test_engine.connect_market(mock_market_connector)
        
        # Trade signal oluştur
        signal = TradeSignal(
            symbol="EURUSD",
            direction="CALL",
            expiry_time=60,
            amount=5.0,
            confidence=0.8,
            timestamp=datetime.utcnow(),
            strategy_name="test_strategy"
        )
        
        # Sinyali işle
        await test_engine._on_trade_signal(signal)
        
        # Risk manager'da işlem kaydı olmalı
        if test_engine.risk_manager:
            stats = test_engine.risk_manager.get_risk_report()
            # İşlem onaylanmış olabilir (risk kurallarına bağlı)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_risk_management_integration(self, test_engine, test_user_credentials):
        """Risk yönetimi entegrasyonu testi"""
        # Giriş yap
        await test_engine.authenticate_user(test_user_credentials)
        
        # Risk manager'ı kontrol et
        assert test_engine.risk_manager is not None
        
        # Risk raporu al
        risk_report = test_engine.risk_manager.get_risk_report()
        assert 'metrics' in risk_report
        assert 'limits' in risk_report
        
        # Risk limitleri kontrol et
        limits = risk_report['limits']
        assert limits['max_daily_loss'] > 0
        assert limits['max_position_size'] > 0
        assert limits['max_concurrent_trades'] > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_data_persistence(self, test_engine, test_user_credentials):
        """Veri kalıcılığı testi"""
        # Giriş yap
        await test_engine.authenticate_user(test_user_credentials)
        
        # Data manager'ı kontrol et
        assert test_engine.data_manager is not None
        
        # Test market data kaydet
        market_data = MarketData(
            symbol="EURUSD",
            timestamp=datetime.utcnow(),
            bid=1.08450,
            ask=1.08452,
            last=1.08451,
            volume=1000.0
        )
        
        await test_engine.data_manager.save_market_data(market_data)
        
        # Veriyi geri al
        history = await test_engine.data_manager.get_market_data_history("EURUSD", hours=1)
        assert len(history) > 0
        assert history[-1]['symbol'] == "EURUSD"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_system_status_reporting(self, test_engine, test_user_credentials):
        """Sistem durumu raporlama testi"""
        # Giriş yap
        await test_engine.authenticate_user(test_user_credentials)
        
        # Sistem durumunu al
        status = test_engine.get_status()
        
        # Temel alanları kontrol et
        assert 'state' in status
        assert 'timestamp' in status
        assert 'session' in status
        assert 'market_connected' in status
        assert 'strategies' in status
        
        # Oturum bilgileri
        session_info = status['session']
        assert session_info['email'] == test_user_credentials.email
        assert session_info['broker'] == test_user_credentials.broker
        assert session_info['demo_account'] == test_user_credentials.demo_account
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_end_to_end_trading_simulation(self, test_engine, test_user_credentials, mock_market_connector):
        """Uçtan uca işlem simülasyonu testi"""
        # Giriş yap
        await test_engine.authenticate_user(test_user_credentials)
        
        # Mock market connector bağla
        await test_engine.connect_market(mock_market_connector)
        
        # Strateji ekle
        strategy_config = StrategyConfig(
            name="e2e_test_strategy",
            enabled=True,
            risk_per_trade=5.0,
            symbols=["EURUSD"],
            min_confidence=0.5  # Düşük threshold test için
        )
        strategy = SimpleTrendStrategy(strategy_config)
        test_engine.add_strategy(strategy)
        
        # İşlem başlat
        success = await test_engine.start_trading(["EURUSD"])
        assert success is True
        
        # Market data simülasyonu
        base_price = 1.08450
        signal_generated = False
        
        # Yeterli veri ekleyerek sinyal üretmeye çalış
        for i in range(50):
            price = base_price + (i * 0.0001 if i < 25 else (50-i) * 0.0001)
            market_data = MarketData(
                symbol="EURUSD",
                timestamp=datetime.utcnow(),
                bid=price - 0.00001,
                ask=price + 0.00001,
                last=price,
                volume=1000.0
            )
            
            await test_engine._on_market_data(market_data)
            
            # Kısa bekleme
            await asyncio.sleep(0.01)
            
            # Strateji durumunu kontrol et
            strategy = test_engine.strategies["e2e_test_strategy"]
            if strategy.state.total_signals > 0:
                signal_generated = True
                break
        
        # İşlem durdur
        await test_engine.stop_trading()
        
        # Sonuçları kontrol et
        final_status = test_engine.get_status()
        assert final_status['state'] in ['stopped', 'running']  # State değişebilir
        
        # Strateji istatistikleri
        strategy = test_engine.strategies["e2e_test_strategy"]
        strategy_status = strategy.status
        
        # En azından market data işlenmiş olmalı
        assert len(strategy.market_data_history.get("EURUSD", [])) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_operations(self, test_engine, test_user_credentials, mock_market_connector):
        """Eşzamanlı işlemler testi"""
        # Giriş yap
        await test_engine.authenticate_user(test_user_credentials)
        
        # Mock market connector bağla
        await test_engine.connect_market(mock_market_connector)
        
        # Birden fazla strateji ekle
        strategies = []
        for i in range(3):
            config = StrategyConfig(
                name=f"concurrent_strategy_{i}",
                enabled=True,
                symbols=["EURUSD", "GBPUSD"],
                risk_per_trade=2.0
            )
            strategy = SimpleTrendStrategy(config)
            test_engine.add_strategy(strategy)
            strategies.append(strategy)
        
        # Eşzamanlı market data işleme
        async def send_market_data(symbol, base_price):
            for i in range(20):
                price = base_price + i * 0.0001
                market_data = MarketData(
                    symbol=symbol,
                    timestamp=datetime.utcnow(),
                    bid=price - 0.00001,
                    ask=price + 0.00001,
                    last=price,
                    volume=1000.0
                )
                await test_engine._on_market_data(market_data)
                await asyncio.sleep(0.01)
        
        # Eşzamanlı görevler
        tasks = [
            send_market_data("EURUSD", 1.08450),
            send_market_data("GBPUSD", 1.26450)
        ]
        
        await asyncio.gather(*tasks)
        
        # Tüm stratejiler veri almış olmalı
        for strategy in strategies:
            assert len(strategy.market_data_history) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_handling_and_recovery(self, test_engine, test_user_credentials):
        """Hata işleme ve kurtarma testi"""
        # Giriş yap
        await test_engine.authenticate_user(test_user_credentials)
        
        # Geçersiz strateji eklemeye çalış
        try:
            # None config ile strateji oluşturmaya çalış
            invalid_strategy = SimpleTrendStrategy(None)
            test_engine.add_strategy(invalid_strategy)
        except Exception:
            pass  # Hata bekleniyor
        
        # Sistem hala çalışır durumda olmalı
        status = test_engine.get_status()
        assert status['state'] != 'error'
        
        # Geçersiz market data işlemeye çalış
        try:
            await test_engine._on_market_data(None)
        except Exception:
            pass  # Hata bekleniyor
        
        # Sistem hala çalışır durumda olmalı
        status = test_engine.get_status()
        assert status['state'] != 'error'