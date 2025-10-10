"""Strategy API Routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from models.market_data import MarketData
from models.signal import Signal
from services.strategy_service import StrategyService

router = APIRouter(prefix="/strategies", tags=["strategies"])


class ExecuteStrategyRequest(BaseModel):
    strategy_id: str
    market_data: MarketData
    parameters: Optional[Dict] = None


@router.get("/list")
async def list_strategies():
    """
    Get list of available trading strategies
    """
    try:
        strategies = StrategyService.get_predefined_strategies()
        return {"strategies": strategies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=Signal)
async def execute_strategy(request: ExecuteStrategyRequest):
    """
    Execute a trading strategy and get signal
    """
    try:
        signal = StrategyService.execute_strategy(
            request.strategy_id,
            request.market_data,
            request.parameters
        )
        return signal
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
