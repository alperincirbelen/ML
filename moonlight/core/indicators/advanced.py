"""
Advanced Technical Indicators
Parça 8 - İleri göstergeler
"""

import pandas as pd
import numpy as np
from typing import Tuple
from .basic import ema, atr, rsi


def dmi(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    length: int = 14
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    DMI/ADX - Directional Movement Index
    Returns: (di_plus, di_minus, adx)
    """
    # Directional Movement
    up_move = high.diff()
    down_move = -low.diff()
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    # True Range
    from .basic import true_range
    tr = true_range(high, low, close)
    
    # Wilder smoothing
    plus_dm_smooth = pd.Series(plus_dm, index=high.index).ewm(
        alpha=1/length, adjust=False, min_periods=length
    ).mean()
    minus_dm_smooth = pd.Series(minus_dm, index=high.index).ewm(
        alpha=1/length, adjust=False, min_periods=length
    ).mean()
    tr_smooth = tr.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    
    # Directional Indicators
    di_plus = 100 * (plus_dm_smooth / tr_smooth.replace(0, np.nan))
    di_minus = 100 * (minus_dm_smooth / tr_smooth.replace(0, np.nan))
    
    # ADX
    dx = 100 * (di_plus - di_minus).abs() / (di_plus + di_minus).replace(0, np.nan)
    adx = dx.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    
    return di_plus, di_minus, adx


def ppo(
    close: pd.Series, 
    fast: int = 12, 
    slow: int = 26, 
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Percentage Price Oscillator
    Returns: (ppo_line, signal_line, histogram)
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    
    ppo_line = 100 * (ema_fast - ema_slow) / ema_slow
    signal_line = ppo_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = ppo_line - signal_line
    
    return ppo_line, signal_line, hist


def stoch_rsi(
    close: pd.Series, 
    rsi_len: int = 14, 
    stoch_len: int = 14, 
    k: int = 3, 
    d: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic RSI
    Returns: (%K, %D)
    """
    rsi_values = rsi(close, rsi_len)
    
    ll = rsi_values.rolling(stoch_len, min_periods=stoch_len).min()
    hh = rsi_values.rolling(stoch_len, min_periods=stoch_len).max()
    
    stoch_rsi_raw = 100 * (rsi_values - ll) / (hh - ll).replace(0, np.nan)
    k_line = stoch_rsi_raw.rolling(k, min_periods=k).mean()
    d_line = k_line.rolling(d, min_periods=d).mean()
    
    return k_line, d_line


def cci(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    length: int = 20, 
    c: float = 0.015
) -> pd.Series:
    """Commodity Channel Index"""
    tp = (high + low + close) / 3.0
    sma_tp = tp.rolling(length, min_periods=length).mean()
    
    # Mean Deviation
    mad = tp.rolling(length).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    
    cci_values = (tp - sma_tp) / (c * mad)
    return cci_values


def fisher(close: pd.Series, length: int = 9) -> pd.Series:
    """Fisher Transform"""
    # Normalize to [-1, 1]
    min_val = close.rolling(length, min_periods=length).min()
    max_val = close.rolling(length, min_periods=length).max()
    
    value = 2 * ((close - min_val) / (max_val - min_val).replace(0, np.nan)) - 1
    value = value.clip(-0.999, 0.999)  # Avoid log(0)
    
    fisher_values = 0.5 * np.log((1 + value) / (1 - value))
    
    return fisher_values


def keltner_channel(
    close: pd.Series, 
    high: pd.Series, 
    low: pd.Series, 
    ema_len: int = 20, 
    atr_len: int = 10, 
    mult: float = 1.5
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Keltner Channel
    Returns: (upper, mid, lower)
    """
    mid = ema(close, ema_len)
    atr_val = atr(high, low, close, atr_len)
    
    upper = mid + mult * atr_val
    lower = mid - mult * atr_val
    
    return upper, mid, lower


def donchian(
    high: pd.Series, 
    low: pd.Series, 
    length: int = 20
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Donchian Channel
    Returns: (upper, mid, lower)
    """
    upper = high.rolling(length, min_periods=length).max()
    lower = low.rolling(length, min_periods=length).min()
    mid = (upper + lower) / 2
    
    return upper, mid, lower


def cmf(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    volume: pd.Series, 
    length: int = 20
) -> pd.Series:
    """Chaikin Money Flow"""
    mfm = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    mfv = mfm * volume
    
    cmf_values = (
        mfv.rolling(length, min_periods=length).sum() / 
        volume.rolling(length, min_periods=length).sum()
    )
    
    return cmf_values


def rvol(volume: pd.Series, lookback: int = 20) -> pd.Series:
    """
    Relative Volume
    Current volume / average volume
    """
    avg_vol = volume.rolling(lookback, min_periods=lookback).mean()
    return volume / avg_vol.replace(0, np.nan)


def ichimoku(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series,
    conv: int = 9, 
    base: int = 26, 
    span_b: int = 52
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Ichimoku Cloud
    Returns: (tenkan, kijun, senkou_a, senkou_b, chikou)
    """
    # Tenkan-sen (Conversion Line)
    tenkan = (
        high.rolling(conv, min_periods=conv).max() + 
        low.rolling(conv, min_periods=conv).min()
    ) / 2
    
    # Kijun-sen (Base Line)
    kijun = (
        high.rolling(base, min_periods=base).max() + 
        low.rolling(base, min_periods=base).min()
    ) / 2
    
    # Senkou Span A (26 periods ahead)
    senkou_a = ((tenkan + kijun) / 2).shift(base)
    
    # Senkou Span B (26 periods ahead)
    senkou_b = (
        (high.rolling(span_b, min_periods=span_b).max() + 
         low.rolling(span_b, min_periods=span_b).min()) / 2
    ).shift(base)
    
    # Chikou Span (26 periods behind)
    chikou = close.shift(-base)
    
    return tenkan, kijun, senkou_a, senkou_b, chikou


def supertrend(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series, 
    atr_len: int = 10, 
    mult: float = 3.0
) -> Tuple[pd.Series, pd.Series]:
    """
    Supertrend Indicator
    Returns: (st_line, direction) where direction ∈ {1, -1}
    """
    atr_val = atr(high, low, close, atr_len)
    hl2 = (high + low) / 2
    
    basic_ub = hl2 + mult * atr_val
    basic_lb = hl2 - mult * atr_val
    
    # Initialize
    final_ub = basic_ub.copy()
    final_lb = basic_lb.copy()
    supertrend_line = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(1, index=close.index)  # 1: bullish, -1: bearish
    
    for i in range(1, len(close)):
        # Upper band
        if basic_ub.iloc[i] < final_ub.iloc[i-1] or close.iloc[i-1] > final_ub.iloc[i-1]:
            final_ub.iloc[i] = basic_ub.iloc[i]
        else:
            final_ub.iloc[i] = final_ub.iloc[i-1]
        
        # Lower band
        if basic_lb.iloc[i] > final_lb.iloc[i-1] or close.iloc[i-1] < final_lb.iloc[i-1]:
            final_lb.iloc[i] = basic_lb.iloc[i]
        else:
            final_lb.iloc[i] = final_lb.iloc[i-1]
        
        # Supertrend direction
        if close.iloc[i] <= final_ub.iloc[i]:
            supertrend_line.iloc[i] = final_ub.iloc[i]
            direction.iloc[i] = -1
        else:
            supertrend_line.iloc[i] = final_lb.iloc[i]
            direction.iloc[i] = 1
    
    return supertrend_line, direction


def pivots_classic(
    high: pd.Series, 
    low: pd.Series, 
    close: pd.Series
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Classic Pivot Points
    Returns: (pp, r1, r2, r3, s1, s2, s3)
    """
    pp = (high + low + close) / 3
    
    r1 = 2 * pp - low
    s1 = 2 * pp - high
    
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    
    r3 = high + 2 * (pp - low)
    s3 = low - 2 * (high - pp)
    
    return pp, r1, r2, r3, s1, s2, s3
