"""
Connector Module - Market Data & Order Interface

Parça 5/6 - Bağlayıcı Tasarımı
Yalnız izinli/resmî API'ler; anti-bot atlatma YOK
"""

from .interface import Connector, Candle, Quote, OrderAck, OrderResult
from .mock import MockConnector

__all__ = [
    'Connector',
    'Candle',
    'Quote',
    'OrderAck',
    'OrderResult',
    'MockConnector'
]
