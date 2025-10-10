"""
Basic Technical Indicators
Parça 7 - Temel göstergeler
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


def sma(s: pd.Series, length: int = 20) -> pd.Series:
    """Simple Moving Average"""
    return s.rolling(length, min_periods=length).mean()


def ema(s: pd.Series, length: int = 20) -> pd.Series:
    """Exponential Moving Average"""
    return s.ewm(span=length, adjust=False, min_periods=length).mean()


def wma(s: pd.Series, length: int = 20) -> pd.Series:
    """Weighted Moving Average"""
    weights = np.arange(1, length + 1)
    
    def _wma(window):
        if len(window) < length:
            return np.nan
        return np.dot(window, weights) / weights.sum()
    
    return s.rolling(length).apply(_wma, raw=True)


def hma(s: pd.Series, length: int = 20) -> pd.Series:
    """
    Hull Moving Average
    HMA = WMA(2*WMA(n/2) - WMA(n), sqrt(n))
    """
    n1 = int(length)
    n2 = max(1, int(length / 2))
    n3 = max(1, int(np.sqrt(length)))
    
    wma_n = wma(s, n1)
    wma_n2 = wma(s, n2)
    hull = 2 * wma_n2 - wma_n
    
    return wma(hull, n3)


def rsi(s: pd.Series, length: int = 14) -> pd.Series:
    """
    Relative Strength Index (Wilder)
    """
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_values = 100 - (100 / (1 + rs))
    
    return rsi_values


def stochastic(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    k: int = 14, 
    k_smooth: int = 3, 
    d: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator (%K, %D)
    """
    ll = low.rolling(k, min_periods=k).min()
    hh = high.rolling(k, min_periods=k).max()
    
    k_raw = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    k_line = k_raw.rolling(k_smooth, min_periods=k_smooth).mean()
    d_line = k_line.rolling(d, min_periods=d).mean()
    
    return k_line, d_line


def macd(
    s: pd.Series, 
    fast: int = 12, 
    slow: int = 26, 
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD (Moving Average Convergence Divergence)
    Returns: (macd_line, signal_line, histogram)
    """
    ema_fast = ema(s, fast)
    ema_slow = ema(s, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd_line - signal_line
    
    return macd_line, signal_line, hist


def bollinger_bands(
    s: pd.Series, 
    length: int = 20, 
    mult: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands
    Returns: (upper, middle, lower)
    """
    mid = sma(s, length)
    std = s.rolling(length, min_periods=length).std(ddof=0)
    
    upper = mid + mult * std
    lower = mid - mult * std
    
    return upper, mid, lower


def bollinger_width(s: pd.Series, length: int = 20, mult: float = 2.0) -> pd.Series:
    """Bollinger Band Width - volatilite ölçüsü"""
    upper, mid, lower = bollinger_bands(s, length, mult)
    return (upper - lower) / mid


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """True Range"""
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def atr(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    length: int = 14
) -> pd.Series:
    """
    Average True Range (Wilder)
    """
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1/length, adjust=False, min_periods=length).mean()


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume"""
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()


def mfi(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    volume: pd.Series, 
    length: int = 14
) -> pd.Series:
    """
    Money Flow Index
    """
    tp = (high + low + close) / 3.0
    raw = tp * volume
    
    pos = np.where(tp.diff() > 0, raw, 0.0)
    neg = np.where(tp.diff() < 0, raw, 0.0)
    
    pos_mf = pd.Series(pos, index=tp.index).rolling(length, min_periods=length).sum()
    neg_mf = pd.Series(neg, index=tp.index).rolling(length, min_periods=length).sum()
    
    mr = pos_mf / neg_mf.replace(0, np.nan)
    mfi_values = 100 - (100 / (1 + mr))
    
    return mfi_values


def vwap(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    volume: pd.Series,
    session: Optional[pd.Series] = None
) -> pd.Series:
    """
    Volume Weighted Average Price
    """
    tp = (high + low + close) / 3.0
    
    if session is None:
        # Kümülatif VWAP
        cum_pv = (tp * volume).cumsum()
        cum_v = volume.cumsum().replace(0, np.nan)
        return cum_pv / cum_v
    else:
        # Seans bazlı VWAP
        pv = tp * volume
        groups = session.ne(session.shift()).cumsum()
        vwap_series = (
            pv.groupby(groups).cumsum() / 
            volume.groupby(groups).cumsum().replace(0, np.nan)
        )
        vwap_series.index = tp.index
        return vwap_series
