"""
Configuration tests
"""

import pytest
from moonlight.core.config import ConfigLoader, AppConfig


def test_config_example_loads():
    """Örnek konfigürasyon yüklenebilmeli"""
    config = ConfigLoader.load_yaml("configs/config.example.yaml")
    
    assert config is not None
    assert isinstance(config, AppConfig)
    assert config.config_version == "1.0.0"
    assert len(config.accounts) >= 1
    assert len(config.products) >= 1


def test_config_validation():
    """Konfigürasyon doğrulama"""
    config = ConfigLoader.load_yaml("configs/config.example.yaml")
    
    is_valid, warnings = ConfigLoader.validate_config(config)
    
    assert is_valid is True
    # Uyarılar olabilir ama geçerli olmalı


def test_invalid_permit_range():
    """Geçersiz permit aralığı hata vermeli"""
    with pytest.raises(ValueError):
        from moonlight.core.config.models import TimeframeConfig
        
        TimeframeConfig(
            tf=1,
            enabled=True,
            permit_min=95,
            permit_max=85  # Hata: max < min
        )


def test_invalid_timeframe():
    """Geçersiz timeframe hata vermeli"""
    with pytest.raises(ValueError):
        from moonlight.core.config.models import TimeframeConfig
        
        TimeframeConfig(
            tf=30,  # Hata: sadece 1, 5, 15 geçerli
            enabled=True
        )
