"""
Advanced Technical Indicators

Parça 8 - İleri Göstergeler
ADX, Supertrend, Ichimoku, Keltner, Donchian, RVOL, CMF, PPO
"""

import pandas as pd
import numpy as np
from typing import Tuple
from .basic import ema, atr, sma


def dmi(high: pd.Series, low: pd.Series, close: pd.Series, 
        length: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Directional Movement Index
    
    Returns:
        (+DI, -DI, ADX)
    """
    # +DM ve -DM hesapla
    high_diff = high.diff()
    low_diff = -low.diff()
    
    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
    
    plus_dm_series = pd.Series(plus_dm, index=high.index)
    minus_dm_series = pd.Series(minus_dm, index=low.index)
    
    # TR
    tr = high - low
    tr = pd.concat([tr, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    
    # Wilder smoothing
    plus_dm_smooth = plus_dm_series.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    minus_dm_smooth = minus_dm_series.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    tr_smooth = tr.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    
    # DI hesapla
    plus_di = 100 * plus_dm_smooth / tr_smooth.replace(0, np.nan)
    minus_di = 100 * minus_dm_smooth / tr_smooth.replace(0, np.nan)
    
    return plus_di, minus_di, None  # ADX ayrı fonksiyon


def adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """
    Average Directional Index
    
    Returns:
        ADX değeri (0-100)
    """
    plus_di, minus_di, _ = dmi(high, low, close, length)
    
    # DX
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    
    # ADX - Wilder smoothing
    adx_val = dx.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    
    return adx_val


def ppo(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Percentage Price Oscillator
    
    Returns:
        (PPO line, Signal line, Histogram)
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    
    ppo_line = 100 * (ema_fast - ema_slow) / ema_slow.replace(0, np.nan)
    signal_line = ppo_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = ppo_line - signal_line
    
    return ppo_line, signal_line, histogram


def stoch_rsi(close: pd.Series, rsi_len: int = 14, stoch_len: int = 14,
              k: int = 3, d: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic RSI
    
    Returns:
        (%K, %D)
    """
    from .basic import rsi, stochastic
    
    rsi_values = rsi(close, rsi_len)
    
    # Stochastic uygula
    rsi_high = rsi_values.rolling(stoch_len, min_periods=stoch_len).max()
    rsi_low = rsi_values.rolling(stoch_len, min_periods=stoch_len).min()
    
    stoch_rsi_raw = 100 * (rsi_values - rsi_low) / (rsi_high - rsi_low).replace(0, np.nan)
    k_line = stoch_rsi_raw.rolling(k, min_periods=k).mean()
    d_line = k_line.rolling(d, min_periods=d).mean()
    
    return k_line, d_line


def cci(high: pd.Series, low: pd.Series, close: pd.Series, 
        length: int = 20, c: float = 0.015) -> pd.Series:
    """
    Commodity Channel Index
    
    Returns:
        CCI değeri
    """
    typical_price = (high + low + close) / 3.0
    tp_sma = sma(typical_price, length)
    
    # Mean deviation
    mad = typical_price.rolling(length, min_periods=length).apply(
        lambda x: np.mean(np.abs(x - x.mean())), raw=True
    )
    
    cci_val = (typical_price - tp_sma) / (c * mad)
    
    return cci_val


def fisher(close: pd.Series, length: int = 9) -> pd.Series:
    """Fisher Transform"""
    # Normalize -1 to 1
    high_roll = close.rolling(length, min_periods=length).max()
    low_roll = close.rolling(length, min_periods=length).min()
    
    value = 2 * (close - low_roll) / (high_roll - low_roll).replace(0, np.nan) - 1
    value = value.clip(-0.999, 0.999)  # Prevent inf
    
    fisher_val = 0.5 * np.log((1 + value) / (1 - value))
    
    return fisher_val


def keltner_channel(close: pd.Series, high: pd.Series, low: pd.Series,
                    ema_len: int = 20, atr_len: int = 10, mult: float = 1.5) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Keltner Channel
    
    Returns:
        (Upper, Middle, Lower)
    """
    mid = ema(close, ema_len)
    atr_val = atr(high, low, close, atr_len)
    
    upper = mid + mult * atr_val
    lower = mid - mult * atr_val
    
    return upper, mid, lower


def donchian(high: pd.Series, low: pd.Series, length: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Donchian Channel
    
    Returns:
        (Upper, Middle, Lower)
    """
    upper = high.rolling(length, min_periods=length).max()
    lower = low.rolling(length, min_periods=length).min()
    mid = (upper + lower) / 2
    
    return upper, mid, lower


def cmf(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
        length: int = 20) -> pd.Series:
    """
    Chaikin Money Flow
    
    Returns:
        CMF değeri (-1 ile +1 arası)
    """
    mfm = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    mfv = mfm * volume
    
    cmf_val = mfv.rolling(length, min_periods=length).sum() / volume.rolling(length, min_periods=length).sum()
    
    return cmf_val


def rvol(volume: pd.Series, lookback: int = 20) -> pd.Series:
    """
    Relative Volume
    
    Returns:
        Hacim / Ortalama Hacim
    """
    avg_vol = volume.rolling(lookback, min_periods=lookback).mean()
    return volume / avg_vol.replace(0, np.nan)


def ichimoku(high: pd.Series, low: pd.Series, close: pd.Series,
             conv: int = 9, base: int = 26, span_b: int = 52) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Ichimoku Cloud
    
    Returns:
        (Tenkan, Kijun, Senkou A, Senkou B, Chikou)
    """
    # Tenkan-sen (Conversion Line)
    tenkan = (high.rolling(conv, min_periods=conv).max() + 
              low.rolling(conv, min_periods=conv).min()) / 2
    
    # Kijun-sen (Base Line)
    kijun = (high.rolling(base, min_periods=base).max() + 
             low.rolling(base, min_periods=base).min()) / 2
    
    # Senkou Span A (Leading Span A) - shifted forward
    senkou_a = ((tenkan + kijun) / 2).shift(base)
    
    # Senkou Span B (Leading Span B) - shifted forward
    senkou_b = ((high.rolling(span_b, min_periods=span_b).max() + 
                 low.rolling(span_b, min_periods=span_b).min()) / 2).shift(base)
    
    # Chikou Span (Lagging Span) - shifted backward
    chikou = close.shift(-base)
    
    return tenkan, kijun, senkou_a, senkou_b, chikou


def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
               atr_len: int = 10, mult: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """
    Supertrend
    
    Returns:
        (ST line, direction) direction: 1 (bullish), -1 (bearish)
    """
    atr_val = atr(high, low, close, atr_len)
    hl_avg = (high + low) / 2
    
    upper_band = hl_avg + mult * atr_val
    lower_band = hl_avg - mult * atr_val
    
    st = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=float)
    
    # İlk değerler
    st.iloc[0] = lower_band.iloc[0]
    direction.iloc[0] = 1
    
    for i in range(1, len(close)):
        # Direction belirleme
        if close.iloc[i] > st.iloc[i-1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < st.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]
        
        # ST line hesapla
        if direction.iloc[i] == 1:
            st.iloc[i] = max(lower_band.iloc[i], st.iloc[i-1]) if direction.iloc[i-1] == 1 else lower_band.iloc[i]
        else:
            st.iloc[i] = min(upper_band.iloc[i], st.iloc[i-1]) if direction.iloc[i-1] == -1 else upper_band.iloc[i]
    
    return st, direction


def pivots_classic(high: pd.Series, low: pd.Series, close: pd.Series) -> Tuple[pd.Series, ...]:
    """
    Classic Pivot Points
    
    Returns:
        (PP, R1, R2, R3, S1, S2, S3)
    """
    pp = (high + low + close) / 3
    
    r1 = 2 * pp - low
    s1 = 2 * pp - high
    
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    
    r3 = high + 2 * (pp - low)
    s3 = low - 2 * (high - pp)
    
    return pp, r1, r2, r3, s1, s2, s3


# Test
if __name__ == "__main__":
    # Örnek veri
    n = 100
    data = pd.DataFrame({
        'close': np.cumsum(np.random.randn(n)) * 0.01 + 100,
        'high': np.cumsum(np.random.randn(n)) * 0.01 + 100.5,
        'low': np.cumsum(np.random.randn(n)) * 0.01 + 99.5,
        'volume': np.random.randint(100, 1000, n)
    })
    
    # Test ileri göstergeler
    data['adx14'] = adx(data['high'], data['low'], data['close'], 14)
    
    st_line, st_dir = supertrend(data['high'], data['low'], data['close'], 10, 3.0)
    data['st_line'] = st_line
    data['st_dir'] = st_dir
    
    kc_upper, kc_mid, kc_lower = keltner_channel(data['close'], data['high'], data['low'])
    data['kc_upper'] = kc_upper
    
    data['rvol'] = rvol(data['volume'], 20)
    data['cmf'] = cmf(data['high'], data['low'], data['close'], data['volume'], 20)
    
    print("✓ Advanced indicator calculations completed")
    print(f"  ADX range: {data['adx14'].min():.2f} - {data['adx14'].max():.2f}")
    print(f"  Supertrend dir: {st_dir.iloc[-5:].tolist()}")
    print(f"  RVOL last: {data['rvol'].iloc[-1]:.2f}")
