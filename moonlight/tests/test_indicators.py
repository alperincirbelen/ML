"""
Indicator tests
"""

import pytest
import pandas as pd
import numpy as np
from moonlight.core.indicators.basic import sma, ema, rsi, macd, bollinger_bands, atr


def generate_test_data(n: int = 100) -> pd.DataFrame:
    """Test verisi üret"""
    np.random.seed(42)
    
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.2)
    low = close - np.abs(np.random.randn(n) * 0.2)
    open_price = close + np.random.randn(n) * 0.1
    volume = np.random.randint(1000, 10000, n)
    
    return pd.DataFrame({
        'open': open_price,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })


def test_sma():
    """SMA testi"""
    df = generate_test_data()
    
    sma_20 = sma(df['close'], 20)
    
    assert len(sma_20) == len(df)
    assert pd.isna(sma_20.iloc[0:19]).all()  # İlk 19 NaN olmalı
    assert not pd.isna(sma_20.iloc[19])  # 20. değer hesaplanmış olmalı


def test_ema():
    """EMA testi"""
    df = generate_test_data()
    
    ema_20 = ema(df['close'], 20)
    
    assert len(ema_20) == len(df)
    assert not pd.isna(ema_20.iloc[-1])  # Son değer hesaplanmış


def test_rsi():
    """RSI testi"""
    df = generate_test_data()
    
    rsi_14 = rsi(df['close'], 14)
    
    assert len(rsi_14) == len(df)
    
    # RSI 0-100 arasında olmalı
    valid_values = rsi_14.dropna()
    assert (valid_values >= 0).all()
    assert (valid_values <= 100).all()


def test_macd():
    """MACD testi"""
    df = generate_test_data()
    
    macd_line, signal_line, hist = macd(df['close'])
    
    assert len(macd_line) == len(df)
    assert len(signal_line) == len(df)
    assert len(hist) == len(df)
    
    # Histogram = MACD - Signal
    valid_idx = ~(macd_line.isna() | signal_line.isna() | hist.isna())
    diff = (macd_line - signal_line)[valid_idx]
    np.testing.assert_array_almost_equal(diff, hist[valid_idx], decimal=6)


def test_bollinger():
    """Bollinger Bands testi"""
    df = generate_test_data()
    
    upper, mid, lower = bollinger_bands(df['close'], 20, 2.0)
    
    assert len(upper) == len(df)
    
    # Upper > Mid > Lower (geçerli değerlerde)
    valid_idx = ~(upper.isna() | mid.isna() | lower.isna())
    assert (upper[valid_idx] >= mid[valid_idx]).all()
    assert (mid[valid_idx] >= lower[valid_idx]).all()


def test_atr():
    """ATR testi"""
    df = generate_test_data()
    
    atr_14 = atr(df['high'], df['low'], df['close'], 14)
    
    assert len(atr_14) == len(df)
    
    # ATR pozitif olmalı
    valid_values = atr_14.dropna()
    assert (valid_values >= 0).all()
