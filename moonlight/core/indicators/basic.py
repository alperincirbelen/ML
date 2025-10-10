"""
Basic Technical Indicators

Parça 7 - Temel Göstergeler
Hareketli ortalamalar, RSI, MACD, Bollinger, ATR, hacim göstergeleri
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


def sma(s: pd.Series, length: int = 20) -> pd.Series:
    """Basit Hareketli Ortalama"""
    return s.rolling(length, min_periods=length).mean()


def ema(s: pd.Series, length: int = 20) -> pd.Series:
    """Üssel Hareketli Ortalama"""
    return s.ewm(span=length, adjust=False, min_periods=length).mean()


def wma(s: pd.Series, length: int = 20) -> pd.Series:
    """Ağırlıklı Hareketli Ortalama"""
    weights = np.arange(1, length + 1)
    
    def weighted_mean(x):
        if len(x) < length:
            return np.nan
        return np.dot(x, weights) / weights.sum()
    
    return s.rolling(length).apply(weighted_mean, raw=True)


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
    Relative Strength Index (Wilder smoothing)
    
    Returns:
        0-100 arası değer
    """
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Wilder smoothing (EMA benzeri)
    avg_gain = gain.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))
    
    return rsi_val


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k: int = 14, k_smooth: int = 3, d: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator (%K, %D)
    
    Returns:
        (%K line, %D line)
    """
    ll = low.rolling(k, min_periods=k).min()
    hh = high.rolling(k, min_periods=k).max()
    
    k_raw = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    k_line = k_raw.rolling(k_smooth, min_periods=k_smooth).mean()
    d_line = k_line.rolling(d, min_periods=d).mean()
    
    return k_line, d_line


def macd(s: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD (Moving Average Convergence Divergence)
    
    Returns:
        (MACD line, Signal line, Histogram)
    """
    ema_fast = ema(s, fast)
    ema_slow = ema(s, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def bollinger_bands(s: pd.Series, length: int = 20, mult: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands
    
    Returns:
        (Upper, Middle, Lower)
    """
    mid = sma(s, length)
    std = s.rolling(length, min_periods=length).std(ddof=0)
    upper = mid + mult * std
    lower = mid - mult * std
    
    return upper, mid, lower


def bollinger_width(s: pd.Series, length: int = 20, mult: float = 2.0) -> pd.Series:
    """Bollinger Bant Genişliği (normalize)"""
    upper, mid, lower = bollinger_bands(s, length, mult)
    return (upper - lower) / mid.replace(0, np.nan)


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """True Range"""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Average True Range (Wilder smoothing)"""
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1/length, adjust=False, min_periods=length).mean()


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume"""
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()


def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, 
        length: int = 14) -> pd.Series:
    """
    Money Flow Index
    
    Returns:
        0-100 arası değer
    """
    typical_price = (high + low + close) / 3.0
    raw_money_flow = typical_price * volume
    
    # Pozitif ve negatif money flow
    pos_flow = np.where(typical_price.diff() > 0, raw_money_flow, 0.0)
    neg_flow = np.where(typical_price.diff() < 0, raw_money_flow, 0.0)
    
    pos_mf = pd.Series(pos_flow, index=typical_price.index).rolling(length, min_periods=length).sum()
    neg_mf = pd.Series(neg_flow, index=typical_price.index).rolling(length, min_periods=length).sum()
    
    money_ratio = pos_mf / neg_mf.replace(0, np.nan)
    mfi_val = 100 - (100 / (1 + money_ratio))
    
    return mfi_val


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
         session: Optional[pd.Series] = None) -> pd.Series:
    """
    Volume Weighted Average Price
    
    Args:
        session: Session ID (değiştiğinde sıfırlanır), None ise kümülatif
    """
    typical_price = (high + low + close) / 3.0
    
    if session is None:
        # Kümülatif VWAP
        cum_pv = (typical_price * volume).cumsum()
        cum_v = volume.cumsum().replace(0, np.nan)
        return cum_pv / cum_v
    else:
        # Session bazlı VWAP
        pv = typical_price * volume
        groups = session.ne(session.shift()).cumsum()
        vwap_series = pv.groupby(groups).cumsum() / volume.groupby(groups).cumsum().replace(0, np.nan)
        vwap_series.index = typical_price.index
        return vwap_series


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
    
    # Test göstergeleri
    data['sma20'] = sma(data['close'], 20)
    data['ema20'] = ema(data['close'], 20)
    data['rsi14'] = rsi(data['close'], 14)
    data['atr14'] = atr(data['high'], data['low'], data['close'], 14)
    
    upper, mid, lower = bollinger_bands(data['close'], 20, 2.0)
    data['bb_upper'] = upper
    data['bb_mid'] = mid
    data['bb_lower'] = lower
    
    macd_line, sig, hist = macd(data['close'])
    data['macd'] = macd_line
    data['macd_hist'] = hist
    
    print("✓ Indicator calculations completed")
    print(f"  RSI range: {data['rsi14'].min():.2f} - {data['rsi14'].max():.2f}")
    print(f"  ATR last: {data['atr14'].iloc[-1]:.6f}")
    print(f"  BB width: {bollinger_width(data['close']).iloc[-1]:.4f}")
