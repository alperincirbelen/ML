"""
Indicator State Interpreters
Parça 8 - Durum çıkarımı
"""

import pandas as pd


def ichimoku_state(
    tenkan: pd.Series,
    kijun: pd.Series,
    span_a: pd.Series,
    span_b: pd.Series,
    close: pd.Series
) -> pd.Series:
    """
    Ichimoku durumu - basit sınıflandırma
    Returns: 'bullish' | 'bearish' | 'neutral'
    """
    above_cloud = (close > span_a) & (close > span_b)
    below_cloud = (close < span_a) & (close < span_b)
    tk_cross_up = tenkan > kijun
    tk_cross_dn = tenkan < kijun
    
    state = pd.Series('neutral', index=close.index)
    state = state.mask(above_cloud & tk_cross_up, 'bullish')
    state = state.mask(below_cloud & tk_cross_dn, 'bearish')
    
    return state


def supertrend_state(direction: pd.Series) -> pd.Series:
    """
    Supertrend durumu
    direction: 1 (bullish) or -1 (bearish)
    Returns: 'bullish' | 'bearish'
    """
    return direction.map({1: 'bullish', -1: 'bearish'})
