"""
Data models for storage
Parça 5, 6, 22 - Veri modelleri
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Order:
    """
    Emir kaydı - giriş anında oluşturulur
    """
    id: str
    ts_open_ms: int
    account_id: str
    product: str
    timeframe: int  # 1, 5, or 15
    direction: str  # 'call' or 'put'
    amount: float
    client_req_id: str  # Idempotency key
    permit_win_min: Optional[float] = None
    permit_win_max: Optional[float] = None
    payout_pct: Optional[float] = None
    extras: Optional[Dict[str, Any]] = None


@dataclass
class Result:
    """
    Sonuç kaydı - emir kapandığında oluşturulur
    """
    order_id: str
    ts_close_ms: int
    status: str  # 'win', 'lose', 'push', 'abort', 'canceled'
    pnl: float
    duration_ms: Optional[int] = None
    latency_ms: Optional[int] = None
    extras: Optional[Dict[str, Any]] = None


@dataclass
class Feature:
    """
    İşlem anındaki özellikler (indikatörler)
    """
    order_id: str
    account_id: str
    timeframe: int
    
    # Temel indikatörler
    ema9: Optional[float] = None
    ema21: Optional[float] = None
    rsi14: Optional[float] = None
    macd_hist: Optional[float] = None
    boll_width: Optional[float] = None
    atr14: Optional[float] = None
    obv: Optional[float] = None
    mfi14: Optional[float] = None
    adx14: Optional[float] = None
    cmf: Optional[float] = None
    vwap_dist: Optional[float] = None
    stoch_k: Optional[float] = None
    stoch_d: Optional[float] = None
    
    # İleri indikatörler
    ichimoku_state: Optional[str] = None
    supertrend_state: Optional[str] = None
    
    # Esnek JSON alanı
    extras: Optional[Dict[str, Any]] = None


@dataclass
class Metric:
    """
    Zaman serisi metrik kaydı
    """
    scope: str  # global | acc:<id> | prod:<symbol> | tf:<n>
    key: str
    value: float
    ts_ms: int
    tags: Optional[str] = None


@dataclass
class InstrumentCache:
    """
    Katalog - ürün payout önbelleği
    """
    symbol: str
    kind: str
    payout: float
    updated_at: int  # timestamp ms
