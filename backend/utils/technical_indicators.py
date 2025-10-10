"""
Technical Indicators Calculation Module
Implements common trading indicators without external TA-Lib dependency
"""
import numpy as np
import pandas as pd
from typing import Tuple, List


def calculate_sma(data: List[float], period: int = 14) -> List[float]:
    """
    Calculate Simple Moving Average
    """
    if len(data) < period:
        return [np.nan] * len(data)
    
    df = pd.Series(data)
    sma = df.rolling(window=period).mean()
    return sma.fillna(0).tolist()


def calculate_ema(data: List[float], period: int = 14) -> List[float]:
    """
    Calculate Exponential Moving Average
    """
    if len(data) < period:
        return [np.nan] * len(data)
    
    df = pd.Series(data)
    ema = df.ewm(span=period, adjust=False).mean()
    return ema.fillna(0).tolist()


def calculate_rsi(data: List[float], period: int = 14) -> List[float]:
    """
    Calculate Relative Strength Index
    """
    if len(data) < period + 1:
        return [np.nan] * len(data)
    
    df = pd.Series(data)
    delta = df.diff()
    
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.fillna(50).tolist()


def calculate_macd(
    data: List[float], 
    fast_period: int = 12, 
    slow_period: int = 26, 
    signal_period: int = 9
) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence)
    Returns: (macd_line, signal_line, histogram)
    """
    if len(data) < slow_period:
        empty = [np.nan] * len(data)
        return empty, empty, empty
    
    df = pd.Series(data)
    
    ema_fast = df.ewm(span=fast_period, adjust=False).mean()
    ema_slow = df.ewm(span=slow_period, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return (
        macd_line.fillna(0).tolist(),
        signal_line.fillna(0).tolist(),
        histogram.fillna(0).tolist()
    )


def calculate_bollinger_bands(
    data: List[float], 
    period: int = 20, 
    std_dev: float = 2.0
) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate Bollinger Bands
    Returns: (upper_band, middle_band, lower_band)
    """
    if len(data) < period:
        empty = [np.nan] * len(data)
        return empty, empty, empty
    
    df = pd.Series(data)
    
    middle_band = df.rolling(window=period).mean()
    std = df.rolling(window=period).std()
    
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    
    return (
        upper_band.fillna(0).tolist(),
        middle_band.fillna(0).tolist(),
        lower_band.fillna(0).tolist()
    )


def calculate_atr(
    high: List[float], 
    low: List[float], 
    close: List[float], 
    period: int = 14
) -> List[float]:
    """
    Calculate Average True Range
    """
    if len(high) < period or len(low) < period or len(close) < period:
        return [np.nan] * len(close)
    
    df = pd.DataFrame({
        'high': high,
        'low': low,
        'close': close
    })
    
    df['prev_close'] = df['close'].shift(1)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['prev_close'])
    df['tr3'] = abs(df['low'] - df['prev_close'])
    
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    atr = df['tr'].rolling(window=period).mean()
    
    return atr.fillna(0).tolist()


def calculate_stochastic(
    high: List[float], 
    low: List[float], 
    close: List[float], 
    k_period: int = 14,
    d_period: int = 3
) -> Tuple[List[float], List[float]]:
    """
    Calculate Stochastic Oscillator
    Returns: (%K, %D)
    """
    if len(high) < k_period or len(low) < k_period or len(close) < k_period:
        empty = [np.nan] * len(close)
        return empty, empty
    
    df = pd.DataFrame({
        'high': high,
        'low': low,
        'close': close
    })
    
    df['lowest_low'] = df['low'].rolling(window=k_period).min()
    df['highest_high'] = df['high'].rolling(window=k_period).max()
    
    df['%K'] = 100 * (df['close'] - df['lowest_low']) / (df['highest_high'] - df['lowest_low'])
    df['%D'] = df['%K'].rolling(window=d_period).mean()
    
    return (
        df['%K'].fillna(50).tolist(),
        df['%D'].fillna(50).tolist()
    )
