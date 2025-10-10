"""
Indicator Tests
"""

import pytest
import pandas as pd
import numpy as np
from moonlight.core.indicators.basic import sma, ema, rsi, macd, bollinger_bands, atr
from moonlight.core.indicators.advanced import adx, supertrend


def create_sample_data(n=100):
    """Test verisi üret"""
    return pd.DataFrame({
        'close': np.cumsum(np.random.randn(n)) * 0.01 + 100,
        'high': np.cumsum(np.random.randn(n)) * 0.01 + 100.5,
        'low': np.cumsum(np.random.randn(n)) * 0.01 + 99.5,
        'volume': np.random.randint(100, 1000, n)
    })


def test_sma():
    """SMA hesaplanmalı"""
    close = pd.Series([100, 101, 102, 103, 104])
    result = sma(close, 3)
    
    # İlk 2 NaN, sonraki değerler hesaplanmış olmalı
    assert pd.isna(result.iloc[0])
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == 101.0  # (100+101+102)/3
    assert result.iloc[3] == 102.0  # (101+102+103)/3


def test_ema():
    """EMA hesaplanmalı"""
    close = pd.Series([100, 101, 102, 103, 104])
    result = ema(close, 3)
    
    # İlk 2 NaN olmalı (min_periods=3)
    assert pd.isna(result.iloc[0])
    assert pd.isna(result.iloc[1])
    assert not pd.isna(result.iloc[2])


def test_rsi_range():
    """RSI 0-100 arası olmalı"""
    df = create_sample_data(100)
    result = rsi(df['close'], 14)
    
    # NaN olmayan değerler
    valid = result.dropna()
    
    assert valid.min() >= 0
    assert valid.max() <= 100


def test_macd():
    """MACD hesaplanmalı"""
    df = create_sample_data(100)
    macd_line, signal, hist = macd(df['close'])
    
    # Histogram = MACD - Signal
    valid_idx = ~(macd_line.isna() | signal.isna() | hist.isna())
    
    if valid_idx.any():
        assert np.allclose(
            hist[valid_idx],
            macd_line[valid_idx] - signal[valid_idx],
            rtol=1e-6
        )


def test_bollinger_bands():
    """Bollinger bantları hesaplanmalı"""
    df = create_sample_data(100)
    upper, mid, lower = bollinger_bands(df['close'], 20, 2.0)
    
    # Upper > Mid > Lower olmalı (çoğu durumda)
    valid = ~(upper.isna() | mid.isna() | lower.isna())
    
    if valid.any():
        assert (upper[valid] >= mid[valid]).all()
        assert (mid[valid] >= lower[valid]).all()


def test_atr_positive():
    """ATR pozitif olmalı"""
    df = create_sample_data(100)
    result = atr(df['high'], df['low'], df['close'], 14)
    
    valid = result.dropna()
    assert (valid > 0).all()


def test_adx_range():
    """ADX 0-100 arası olmalı"""
    df = create_sample_data(100)
    result = adx(df['high'], df['low'], df['close'], 14)
    
    valid = result.dropna()
    
    if len(valid) > 0:
        assert valid.min() >= 0
        assert valid.max() <= 100


def test_supertrend_direction():
    """Supertrend yönü ±1 olmalı"""
    df = create_sample_data(100)
    st_line, st_dir = supertrend(df['high'], df['low'], df['close'], 10, 3.0)
    
    valid = st_dir.dropna()
    
    if len(valid) > 0:
        assert set(valid.unique()).issubset({-1.0, 1.0})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
