from __future__ import annotations
from typing import List, Optional


def ema(values: List[float], length: int) -> List[Optional[float]]:
    """Exponentially weighted moving average (classic EMA)."""
    if length <= 0:
        raise ValueError("length must be >= 1")
    out: List[Optional[float]] = [None] * len(values)
    if not values:
        return out
    k = 2.0 / (length + 1.0)
    # Initialize with SMA
    if len(values) >= length:
        sma = sum(values[:length]) / float(length)
        out[length - 1] = sma
        prev = sma
        for i in range(length, len(values)):
            v = values[i]
            prev = (v - prev) * k + prev
            out[i] = prev
    return out


def rsi(values: List[float], length: int = 14) -> List[Optional[float]]:
    """Wilder RSI implementation, returns [0..100]."""
    if length <= 0:
        raise ValueError("length must be >= 1")
    n = len(values)
    out: List[Optional[float]] = [None] * n
    if n < length + 1:
        return out
    gains = [0.0] * n
    losses = [0.0] * n
    for i in range(1, n):
        delta = values[i] - values[i - 1]
        if delta >= 0:
            gains[i] = delta
        else:
            losses[i] = -delta
    avg_gain = sum(gains[1 : length + 1]) / length
    avg_loss = sum(losses[1 : length + 1]) / length
    # First RSI at index length
    rs = avg_gain / avg_loss if avg_loss > 0 else float("inf")
    out[length] = 100.0 - (100.0 / (1.0 + rs)) if rs != float("inf") else 100.0
    g = avg_gain
    l = avg_loss
    for i in range(length + 1, n):
        g = (g * (length - 1) + gains[i]) / length
        l = (l * (length - 1) + losses[i]) / length
        if l == 0:
            out[i] = 100.0
        else:
            rs = g / l
            out[i] = 100.0 - (100.0 / (1.0 + rs))
    return out
