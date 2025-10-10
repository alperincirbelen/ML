"""Indicators API Routes"""
from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
from models.market_data import MarketData
from models.indicator import Indicator, IndicatorConfig, IndicatorType
from services.indicator_service import IndicatorService

router = APIRouter(prefix="/indicators", tags=["indicators"])


class CalculateIndicatorRequest(BaseModel):
    market_data: MarketData
    indicator_config: IndicatorConfig


class CalculateMultipleRequest(BaseModel):
    market_data: MarketData
    configs: List[IndicatorConfig]


@router.post("/calculate", response_model=Indicator)
async def calculate_indicator(request: CalculateIndicatorRequest):
    """
    Calculate a single technical indicator
    """
    try:
        indicator = IndicatorService.calculate_indicator(
            request.market_data,
            request.indicator_config
        )
        return indicator
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-multiple")
async def calculate_multiple_indicators(request: CalculateMultipleRequest):
    """
    Calculate multiple indicators at once
    """
    try:
        indicators = IndicatorService.calculate_multiple_indicators(
            request.market_data,
            request.configs
        )
        return {"indicators": indicators}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_indicator_types():
    """
    Get list of available indicator types
    """
    return {
        "indicators": [
            {
                "type": IndicatorType.SMA,
                "name": "Simple Moving Average",
                "description": "Average price over a specified period",
                "default_period": 14
            },
            {
                "type": IndicatorType.EMA,
                "name": "Exponential Moving Average",
                "description": "Weighted average giving more importance to recent prices",
                "default_period": 14
            },
            {
                "type": IndicatorType.RSI,
                "name": "Relative Strength Index",
                "description": "Momentum oscillator measuring speed and magnitude of price changes",
                "default_period": 14
            },
            {
                "type": IndicatorType.MACD,
                "name": "MACD",
                "description": "Trend-following momentum indicator",
                "default_period": 12
            },
            {
                "type": IndicatorType.BOLLINGER_BANDS,
                "name": "Bollinger Bands",
                "description": "Volatility bands around a moving average",
                "default_period": 20
            },
            {
                "type": IndicatorType.ATR,
                "name": "Average True Range",
                "description": "Measures market volatility",
                "default_period": 14
            },
            {
                "type": IndicatorType.STOCHASTIC,
                "name": "Stochastic Oscillator",
                "description": "Momentum indicator comparing closing price to price range",
                "default_period": 14
            },
        ]
    }
