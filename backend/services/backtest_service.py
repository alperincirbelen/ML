"""Backtest Service - Test strategies on historical data"""
from typing import Dict, List
from models.market_data import MarketData
from models.signal import Signal, SignalType
from services.strategy_service import StrategyService


class BacktestResult:
    def __init__(self):
        self.trades = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0
        self.win_rate = 0.0
        self.profit_factor = 0.0
        self.initial_capital = 10000.0
        self.final_capital = 10000.0
        self.roi_percent = 0.0


class BacktestService:
    @staticmethod
    def run_backtest(
        strategy_id: str,
        market_data: MarketData,
        initial_capital: float = 10000.0,
        position_size: float = 0.1,  # 10% of capital per trade
        parameters: Dict = None
    ) -> Dict:
        """
        Run a simple backtest on historical data
        """
        result = BacktestResult()
        result.initial_capital = initial_capital
        
        capital = initial_capital
        position = None
        entry_price = 0.0
        
        # Process each candle
        for i in range(20, len(market_data.data)):  # Start after warm-up period
            # Create a slice of market data up to current point
            historical_data = MarketData(
                symbol=market_data.symbol,
                timeframe=market_data.timeframe,
                data=market_data.data[:i+1],
                last_updated=market_data.last_updated
            )
            
            # Get signal from strategy
            signal = StrategyService.execute_strategy(strategy_id, historical_data, parameters)
            current_price = market_data.data[i].close
            
            # Execute trades based on signals
            if signal.signal_type == SignalType.BUY and position is None:
                # Enter long position
                position_value = capital * position_size
                position = position_value / current_price
                entry_price = current_price
                
                result.trades.append({
                    "type": "BUY",
                    "price": current_price,
                    "timestamp": market_data.data[i].timestamp,
                    "confidence": signal.confidence
                })
                
            elif signal.signal_type == SignalType.SELL and position is not None:
                # Exit long position
                exit_value = position * current_price
                profit = exit_value - (position * entry_price)
                capital += profit
                
                result.total_trades += 1
                if profit > 0:
                    result.winning_trades += 1
                    result.total_profit += profit
                else:
                    result.losing_trades += 1
                    result.total_loss += abs(profit)
                
                result.trades.append({
                    "type": "SELL",
                    "price": current_price,
                    "timestamp": market_data.data[i].timestamp,
                    "profit": profit,
                    "confidence": signal.confidence
                })
                
                position = None
        
        # Close any open position at the end
        if position is not None:
            final_price = market_data.data[-1].close
            exit_value = position * final_price
            profit = exit_value - (position * entry_price)
            capital += profit
            result.total_trades += 1
            
            if profit > 0:
                result.winning_trades += 1
                result.total_profit += profit
            else:
                result.losing_trades += 1
                result.total_loss += abs(profit)
        
        # Calculate metrics
        result.final_capital = capital
        result.roi_percent = ((capital - initial_capital) / initial_capital) * 100
        
        if result.total_trades > 0:
            result.win_rate = (result.winning_trades / result.total_trades) * 100
        
        if result.total_loss > 0:
            result.profit_factor = result.total_profit / result.total_loss
        else:
            result.profit_factor = result.total_profit if result.total_profit > 0 else 0
        
        return {
            "strategy_id": strategy_id,
            "symbol": market_data.symbol,
            "timeframe": market_data.timeframe.value,
            "initial_capital": result.initial_capital,
            "final_capital": round(result.final_capital, 2),
            "roi_percent": round(result.roi_percent, 2),
            "total_trades": result.total_trades,
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
            "win_rate": round(result.win_rate, 2),
            "total_profit": round(result.total_profit, 2),
            "total_loss": round(result.total_loss, 2),
            "profit_factor": round(result.profit_factor, 2),
            "trades": result.trades[-10:]  # Return last 10 trades
        }
