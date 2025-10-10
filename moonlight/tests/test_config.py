"""
Configuration Tests
"""

import pytest
from pathlib import Path
from moonlight.core.config import load_config, AppConfig, ModeEnum, ConnectorEnum


def test_load_example_config():
    """Örnek konfig yüklenebilmeli"""
    config_path = Path(__file__).parent.parent / "configs" / "app.example.yaml"
    
    if not config_path.exists():
        pytest.skip("Example config not found")
    
    cfg = load_config(config_path)
    
    assert cfg.config_version == "1.0.0"
    assert cfg.mode == ModeEnum.PAPER
    assert cfg.connector == ConnectorEnum.MOCK
    assert len(cfg.accounts) >= 1
    assert len(cfg.products) >= 1


def test_config_validation():
    """Konfig validasyonu çalışmalı"""
    # Geçersiz ensemble_threshold
    with pytest.raises(ValueError):
        AppConfig(
            config_version="1.0.0",
            ensemble_threshold=1.5,  # > 1.0, geçersiz
            accounts=[],
            products=[]
        )


def test_account_ids_unique():
    """Hesap ID'leri benzersiz olmalı"""
    from moonlight.core.config import AccountConfig
    
    with pytest.raises(ValueError, match="unique"):
        AppConfig(
            config_version="1.0.0",
            accounts=[
                AccountConfig(id="acc1", username="user1", profile_store="p1"),
                AccountConfig(id="acc1", username="user2", profile_store="p2"),  # Duplicate
            ],
            products=[]
        )


def test_permit_range_validation():
    """Permit aralığı doğru olmalı"""
    from moonlight.core.config import TimeframeConfig
    
    with pytest.raises(ValueError):
        TimeframeConfig(
            tf=1,
            permit_min=95,
            permit_max=85  # min > max, geçersiz
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
