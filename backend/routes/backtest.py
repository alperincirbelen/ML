"""Backtest API Routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from models.market_data import MarketData
from services.backtest_service import BacktestService

router = APIRouter(prefix="/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    strategy_id: str
    market_data: MarketData
    initial_capital: float = 10000.0
    position_size: float = 0.1
    parameters: Optional[Dict] = None


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """
    Run a backtest on historical data
    """
    try:
        result = BacktestService.run_backtest(
            strategy_id=request.strategy_id,
            market_data=request.market_data,
            initial_capital=request.initial_capital,
            position_size=request.position_size,
            parameters=request.parameters
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
