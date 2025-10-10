"""
Pytest Configuration
Test konfigürasyonu ve fixtures
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import yaml

from core.engine import MoonLightEngine
from core.authentication.auth_manager import AuthManager, UserCredentials
from core.strategy_engine.simple_trend_strategy import SimpleTrendStrategy
from core.strategy_engine.base_strategy import StrategyConfig
from core.risk_manager.risk_manager import RiskManager
from core.persistence.data_manager import DataManager


@pytest.fixture(scope="session")
def event_loop():
    """Event loop fixture for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Temporary directory fixture"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_config(temp_dir):
    """Test configuration fixture"""
    return {
        'system': {
            'name': 'MoonLight AI Test',
            'version': '0.1.0',
            'environment': 'testing',
            'debug': True,
            'log_level': 'DEBUG'
        },
        'database': {
            'type': 'sqlite',
            'path': f'{temp_dir}/test_moonlight.db',
            'backup_enabled': False
        },
        'security': {
            'jwt_secret_key': 'test-secret-key-12345',
            'jwt_algorithm': 'HS256',
            'jwt_expiration': 3600,
            'encryption_key': 'test-encryption-key-67890-abcdef',
            'max_login_attempts': 3,
            'lockout_duration': 60
        },
        'risk_management': {
            'max_daily_loss': 50.0,
            'max_position_size': 5.0,
            'max_concurrent_trades': 2,
            'max_daily_trades': 20,
            'stop_loss_percentage': 5.0,
            'take_profit_percentage': 10.0,
            'max_drawdown_percentage': 15.0,
            'risk_per_trade_percentage': 1.0
        },
        'api': {
            'host': 'localhost',
            'port': 8080,
            'ssl_enabled': False
        },
        'websocket': {
            'host': 'localhost',
            'port': 8081,
            'max_connections': 10
        }
    }


@pytest.fixture
def test_config_file(test_config, temp_dir):
    """Test configuration file fixture"""
    config_file = Path(temp_dir) / 'test_config.yaml'
    with open(config_file, 'w') as f:
        yaml.dump(test_config, f)
    return str(config_file)


@pytest.fixture
async def auth_manager(test_config):
    """AuthManager fixture"""
    return AuthManager(test_config['security'])


@pytest.fixture
async def data_manager(test_config):
    """DataManager fixture"""
    dm = DataManager(test_config['database'])
    await dm.initialize()
    yield dm
    await dm.close()


@pytest.fixture
async def risk_manager(test_config):
    """RiskManager fixture"""
    return RiskManager(test_config)


@pytest.fixture
async def test_engine(test_config_file):
    """Test engine fixture"""
    engine = MoonLightEngine(test_config_file)
    await engine.initialize()
    yield engine
    await engine.shutdown()


@pytest.fixture
def test_user_credentials():
    """Test user credentials fixture"""
    return UserCredentials(
        email="test@moonlight.ai",
        password="test123",
        broker="test_broker",
        demo_account=True
    )


@pytest.fixture
def test_strategy_config():
    """Test strategy configuration fixture"""
    return StrategyConfig(
        name="test_strategy",
        enabled=True,
        risk_per_trade=5.0,
        max_concurrent_trades=2,
        min_confidence=0.6,
        expiry_time=60,
        symbols=["EURUSD", "GBPUSD"],
        parameters={
            'ema_short_period': 5,
            'ema_long_period': 20,
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70
        }
    )


@pytest.fixture
async def test_strategy(test_strategy_config):
    """Test strategy fixture"""
    return SimpleTrendStrategy(test_strategy_config)


@pytest.fixture
def sample_market_data():
    """Sample market data fixture"""
    from core.market_connector.base_connector import MarketData
    from datetime import datetime
    
    return [
        MarketData(
            symbol="EURUSD",
            timestamp=datetime.utcnow(),
            bid=1.08450,
            ask=1.08452,
            last=1.08451,
            volume=1000.0
        ),
        MarketData(
            symbol="GBPUSD",
            timestamp=datetime.utcnow(),
            bid=1.26450,
            ask=1.26452,
            last=1.26451,
            volume=800.0
        )
    ]


@pytest.fixture
def sample_trade_signal():
    """Sample trade signal fixture"""
    from core.market_connector.base_connector import TradeSignal
    from datetime import datetime
    
    return TradeSignal(
        symbol="EURUSD",
        direction="CALL",
        expiry_time=60,
        amount=10.0,
        confidence=0.75,
        timestamp=datetime.utcnow(),
        strategy_name="test_strategy"
    )


# Test utilities
class MockMarketConnector:
    """Mock market connector for testing"""
    
    def __init__(self):
        self.is_connected = False
        self.is_authenticated = False
        self.subscribed_symbols = []
        self.callbacks = {}
    
    async def connect(self):
        self.is_connected = True
        return True
    
    async def disconnect(self):
        self.is_connected = False
    
    async def authenticate(self, credentials):
        self.is_authenticated = True
        return True
    
    async def subscribe_market_data(self, symbols):
        self.subscribed_symbols.extend(symbols)
        return True
    
    async def place_trade(self, signal):
        # Mock trade result
        return {
            'success': True,
            'trade_id': f'mock_trade_{signal.symbol}_{signal.timestamp}',
            'symbol': signal.symbol,
            'direction': signal.direction,
            'amount': signal.amount,
            'profit': signal.amount * 0.8 if signal.direction == 'CALL' else 0,
            'loss': 0 if signal.direction == 'CALL' else signal.amount,
            'status': 'completed'
        }
    
    async def get_balance(self):
        return {'balance': 1000.0, 'demo': True}
    
    async def get_trade_history(self, limit=100):
        return []
    
    def add_callback(self, event_type, callback):
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)


@pytest.fixture
def mock_market_connector():
    """Mock market connector fixture"""
    return MockMarketConnector()


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow
pytest.mark.asyncio_timeout = 30  # 30 second timeout for async tests