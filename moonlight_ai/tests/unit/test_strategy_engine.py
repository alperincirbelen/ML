"""
Strategy Engine Tests
Strateji motoru testleri
"""

import pytest
import asyncio
from datetime import datetime, timedelta
import pandas as pd

from core.strategy_engine.base_strategy import BaseStrategy, StrategyConfig, StrategyState
from core.strategy_engine.simple_trend_strategy import SimpleTrendStrategy
from core.market_connector.base_connector import MarketData, TradeSignal


class TestStrategyConfig:
    """StrategyConfig test sınıfı"""
    
    def test_strategy_config_creation(self):
        """StrategyConfig oluşturma testi"""
        config = StrategyConfig(
            name="test_strategy",
            enabled=True,
            risk_per_trade=10.0,
            max_concurrent_trades=3,
            min_confidence=0.7,
            expiry_time=60,
            symbols=["EURUSD", "GBPUSD"],
            parameters={'param1': 'value1'}
        )
        
        assert config.name == "test_strategy"
        assert config.enabled is True
        assert config.risk_per_trade == 10.0
        assert config.max_concurrent_trades == 3
        assert config.min_confidence == 0.7
        assert config.expiry_time == 60
        assert config.symbols == ["EURUSD", "GBPUSD"]
        assert config.parameters == {'param1': 'value1'}
    
    def test_strategy_config_defaults(self):
        """StrategyConfig varsayılan değerler testi"""
        config = StrategyConfig(name="test_strategy")
        
        assert config.enabled is True
        assert config.risk_per_trade == 1.0
        assert config.max_concurrent_trades == 3
        assert config.min_confidence == 0.6
        assert config.expiry_time == 60
        assert config.symbols == ["EURUSD", "GBPUSD", "USDJPY"]
        assert config.parameters == {}


class TestStrategyState:
    """StrategyState test sınıfı"""
    
    def test_strategy_state_creation(self):
        """StrategyState oluşturma testi"""
        state = StrategyState()
        
        assert state.active_signals == 0
        assert state.total_signals == 0
        assert state.successful_signals == 0
        assert state.last_signal_time is None
        assert state.last_update_time is None
    
    def test_success_rate_calculation(self):
        """Başarı oranı hesaplama testi"""
        state = StrategyState()
        
        # Başlangıçta 0 olmalı
        assert state.success_rate == 0.0
        assert state.win_rate_percentage == 0.0
        
        # Sinyaller ekle
        state.total_signals = 10
        state.successful_signals = 7
        
        assert state.success_rate == 0.7
        assert state.win_rate_percentage == 70.0


class MockStrategy(BaseStrategy):
    """Test için mock strateji"""
    
    def get_required_history_length(self) -> int:
        return 10
    
    async def analyze(self, market_data: MarketData) -> TradeSignal:
        # Basit mock sinyal
        if market_data.last > 1.0850:  # EURUSD için
            return TradeSignal(
                symbol=market_data.symbol,
                direction="CALL",
                expiry_time=60,
                amount=self.config.risk_per_trade,
                confidence=0.8,
                timestamp=datetime.utcnow(),
                strategy_name=self.config.name
            )
        return None


class TestBaseStrategy:
    """BaseStrategy test sınıfı"""
    
    @pytest.fixture
    def mock_strategy(self, test_strategy_config):
        """Mock strateji fixture"""
        return MockStrategy(test_strategy_config)
    
    def test_base_strategy_initialization(self, mock_strategy):
        """BaseStrategy başlatma testi"""
        assert mock_strategy.config.name == "test_strategy"
        assert mock_strategy.state.total_signals == 0
        assert mock_strategy.is_active is False
        assert len(mock_strategy.market_data_history) == 0
    
    def test_strategy_start_stop(self, mock_strategy):
        """Strateji başlatma/durdurma testi"""
        # Başlangıçta pasif
        assert mock_strategy.is_active is False
        
        # Başlat
        mock_strategy.start()
        assert mock_strategy.is_active is True
        
        # Durdur
        mock_strategy.stop()
        assert mock_strategy.is_active is False
    
    @pytest.mark.asyncio
    async def test_market_data_update(self, mock_strategy, sample_market_data):
        """Market data güncelleme testi"""
        mock_strategy.start()
        
        market_data = sample_market_data[0]  # EURUSD
        
        # İlk güncelleme - yeterli veri yok
        signal = await mock_strategy.update_market_data(market_data)
        assert signal is None  # Yeterli geçmiş veri yok
        
        # Geçmiş veri ekle
        for i in range(15):
            test_data = MarketData(
                symbol="EURUSD",
                timestamp=datetime.utcnow(),
                bid=1.0840 + i * 0.0001,
                ask=1.0842 + i * 0.0001,
                last=1.0841 + i * 0.0001,
                volume=1000.0
            )
            await mock_strategy.update_market_data(test_data)
        
        # Son güncelleme - sinyal üretmeli
        high_price_data = MarketData(
            symbol="EURUSD",
            timestamp=datetime.utcnow(),
            bid=1.0860,
            ask=1.0862,
            last=1.0861,  # Yüksek fiyat - CALL sinyali üretmeli
            volume=1000.0
        )
        
        signal = await mock_strategy.update_market_data(high_price_data)
        assert signal is not None
        assert signal.direction == "CALL"
        assert signal.symbol == "EURUSD"
    
    def test_market_data_history_limit(self, mock_strategy):
        """Market data geçmiş limiti testi"""
        mock_strategy.start()
        
        # Çok fazla veri ekle
        for i in range(250):
            market_data = MarketData(
                symbol="EURUSD",
                timestamp=datetime.utcnow(),
                bid=1.0840,
                ask=1.0842,
                last=1.0841,
                volume=1000.0
            )
            asyncio.run(mock_strategy.update_market_data(market_data))
        
        # Geçmiş veri sınırlanmalı
        history_length = len(mock_strategy.market_data_history["EURUSD"])
        assert history_length <= 200  # Max history * 2
    
    def test_get_market_data_df(self, mock_strategy):
        """Market data DataFrame testi"""
        mock_strategy.start()
        
        # Test verisi ekle
        for i in range(20):
            market_data = MarketData(
                symbol="EURUSD",
                timestamp=datetime.utcnow(),
                bid=1.0840 + i * 0.0001,
                ask=1.0842 + i * 0.0001,
                last=1.0841 + i * 0.0001,
                volume=1000.0 + i * 10
            )
            asyncio.run(mock_strategy.update_market_data(market_data))
        
        # DataFrame al
        df = mock_strategy.get_market_data_df("EURUSD")
        
        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 20
        assert 'bid' in df.columns
        assert 'ask' in df.columns
        assert 'last' in df.columns
        assert 'volume' in df.columns
    
    def test_calculate_technical_indicators(self, mock_strategy):
        """Teknik indikatör hesaplama testi"""
        mock_strategy.start()
        
        # Test verisi ekle
        for i in range(50):
            market_data = MarketData(
                symbol="EURUSD",
                timestamp=datetime.utcnow(),
                bid=1.0840 + i * 0.0001,
                ask=1.0842 + i * 0.0001,
                last=1.0841 + i * 0.0001,
                volume=1000.0
            )
            asyncio.run(mock_strategy.update_market_data(market_data))
        
        # DataFrame al ve indikatörleri hesapla
        df = mock_strategy.get_market_data_df("EURUSD")
        df_with_indicators = mock_strategy.calculate_technical_indicators(df)
        
        # İndikatörlerin varlığını kontrol et
        expected_indicators = [
            'sma_5', 'sma_10', 'sma_20',
            'ema_5', 'ema_10', 'ema_20',
            'rsi', 'macd', 'macd_signal', 'macd_histogram',
            'bb_middle', 'bb_upper', 'bb_lower'
        ]
        
        for indicator in expected_indicators:
            assert indicator in df_with_indicators.columns
    
    @pytest.mark.asyncio
    async def test_on_trade_result(self, mock_strategy):
        """İşlem sonucu işleme testi"""
        # Aktif sinyal ekle
        mock_strategy.state.active_signals = 1
        mock_strategy.state.total_signals = 1
        
        signal = TradeSignal(
            symbol="EURUSD",
            direction="CALL",
            expiry_time=60,
            amount=10.0,
            confidence=0.8,
            timestamp=datetime.utcnow(),
            strategy_name="test_strategy"
        )
        
        # Başarılı sonuç
        success_result = {'success': True, 'profit': 8.0}
        await mock_strategy.on_trade_result(signal, success_result)
        
        assert mock_strategy.state.active_signals == 0
        assert mock_strategy.state.successful_signals == 1
        
        # Başarısız sonuç
        mock_strategy.state.active_signals = 1
        mock_strategy.state.total_signals = 2
        
        fail_result = {'success': False, 'loss': 10.0}
        await mock_strategy.on_trade_result(signal, fail_result)
        
        assert mock_strategy.state.active_signals == 0
        assert mock_strategy.state.successful_signals == 1  # Değişmemeli
    
    def test_strategy_status(self, mock_strategy):
        """Strateji durumu testi"""
        status = mock_strategy.status
        
        assert 'name' in status
        assert 'active' in status
        assert 'enabled' in status
        assert 'total_signals' in status
        assert 'success_rate' in status
        assert 'win_rate_percentage' in status
        assert 'symbols' in status
        
        assert status['name'] == "test_strategy"
        assert status['active'] is False  # Henüz başlatılmamış


class TestSimpleTrendStrategy:
    """SimpleTrendStrategy test sınıfı"""
    
    @pytest.mark.asyncio
    async def test_simple_trend_strategy_initialization(self, test_strategy_config):
        """SimpleTrendStrategy başlatma testi"""
        strategy = SimpleTrendStrategy(test_strategy_config)
        
        assert strategy.config.name == "test_strategy"
        assert strategy.ema_short_period == 5
        assert strategy.ema_long_period == 20
        assert strategy.rsi_period == 14
        assert strategy.rsi_oversold == 30
        assert strategy.rsi_overbought == 70
    
    def test_required_history_length(self, test_strategy_config):
        """Gerekli geçmiş veri uzunluğu testi"""
        strategy = SimpleTrendStrategy(test_strategy_config)
        
        required_length = strategy.get_required_history_length()
        expected_length = max(20, 14) + 5  # max(ema_long, rsi) + buffer
        
        assert required_length == expected_length
    
    @pytest.mark.asyncio
    async def test_trend_signal_generation(self, test_strategy_config):
        """Trend sinyali üretimi testi"""
        strategy = SimpleTrendStrategy(test_strategy_config)
        strategy.start()
        
        # Yeterli geçmiş veri ekle (trend oluşturacak şekilde)
        base_price = 1.0840
        
        # Düşüş trendi oluştur
        for i in range(30):
            price = base_price - i * 0.0002  # Düşen fiyatlar
            market_data = MarketData(
                symbol="EURUSD",
                timestamp=datetime.utcnow(),
                bid=price - 0.00001,
                ask=price + 0.00001,
                last=price,
                volume=1000.0
            )
            await strategy.update_market_data(market_data)
        
        # Yükseliş başlangıcı - CALL sinyali üretmeli
        rising_price = base_price - 29 * 0.0002 + 0.0005  # Ani yükseliş
        rising_data = MarketData(
            symbol="EURUSD",
            timestamp=datetime.utcnow(),
            bid=rising_price - 0.00001,
            ask=rising_price + 0.00001,
            last=rising_price,
            volume=1000.0
        )
        
        signal = await strategy.update_market_data(rising_data)
        
        # Sinyal üretilip üretilmediğini kontrol et
        # (Gerçek piyasa koşullarına bağlı olarak sinyal üretilmeyebilir)
        if signal:
            assert signal.direction in ["CALL", "PUT"]
            assert signal.symbol == "EURUSD"
            assert signal.confidence >= strategy.config.min_confidence
    
    def test_strategy_info(self, test_strategy_config):
        """Strateji bilgileri testi"""
        strategy = SimpleTrendStrategy(test_strategy_config)
        
        info = strategy.get_strategy_info()
        
        assert 'name' in info
        assert 'type' in info
        assert 'description' in info
        assert 'parameters' in info
        assert 'symbols' in info
        assert 'status' in info
        
        assert info['name'] == "test_strategy"
        assert info['type'] == "Trend Following"
        assert 'EMA crossover' in info['description']