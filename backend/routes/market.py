"""Market Data API Routes"""
from fastapi import APIRouter, HTTPException
from models.market_data import MarketData, MarketDataCreate, TimeFrame
from services.market_service import MarketService

router = APIRouter(prefix="/market", tags=["market"])


@router.post("/generate", response_model=MarketData)
async def generate_market_data(request: MarketDataCreate):
    """
    Generate mock market data for testing
    """
    try:
        market_data = MarketService.generate_mock_data(
            symbol=request.symbol,
            timeframe=request.timeframe,
            num_candles=request.num_candles
        )
        return market_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols")
async def get_available_symbols():
    """
    Get list of available trading symbols
    """
    return {
        "symbols": [
            {"symbol": "BTC/USDT", "name": "Bitcoin", "base_price": 50000},
            {"symbol": "ETH/USDT", "name": "Ethereum", "base_price": 3000},
            {"symbol": "EUR/USD", "name": "Euro/Dollar", "base_price": 1.10},
            {"symbol": "GBP/USD", "name": "Pound/Dollar", "base_price": 1.30},
            {"symbol": "AAPL", "name": "Apple Inc.", "base_price": 180},
        ]
    }


@router.get("/timeframes")
async def get_available_timeframes():
    """
    Get list of available timeframes
    """
    return {
        "timeframes": [
            {"value": TimeFrame.M1, "label": "1 Minute"},
            {"value": TimeFrame.M5, "label": "5 Minutes"},
            {"value": TimeFrame.M15, "label": "15 Minutes"},
            {"value": TimeFrame.M30, "label": "30 Minutes"},
            {"value": TimeFrame.H1, "label": "1 Hour"},
            {"value": TimeFrame.H4, "label": "4 Hours"},
            {"value": TimeFrame.D1, "label": "1 Day"},
        ]
    }
