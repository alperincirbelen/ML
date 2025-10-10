"""
Backtest Engine
Geçmişe dönük test motoru
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd

from core.strategy_engine.base_strategy import BaseStrategy
from core.market_connector.base_connector import MarketData, TradeSignal
from core.risk_manager.risk_manager import RiskManager

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtest konfigürasyonu"""
    start_date: datetime
    end_date: datetime
    initial_balance: float = 1000.0
    commission: float = 0.0
    slippage: float = 0.0
    symbols: List[str] = None
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["EURUSD", "GBPUSD", "USDJPY"]


@dataclass
class BacktestTrade:
    """Backtest işlemi"""
    signal: TradeSignal
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: float = 0.0
    exit_price: float = 0.0
    profit_loss: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    status: str = "open"  # open, closed, cancelled
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """İşlem süresi (saniye)"""
        if self.exit_time:
            return int((self.exit_time - self.entry_time).total_seconds())
        return None
    
    @property
    def is_profitable(self) -> bool:
        """Karlı mı?"""
        return self.profit_loss > 0


@dataclass
class BacktestResult:
    """Backtest sonucu"""
    config: BacktestConfig
    trades: List[BacktestTrade]
    final_balance: float
    total_return: float
    total_return_percentage: float
    max_drawdown: float
    max_drawdown_percentage: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    start_time: datetime
    end_time: datetime
    duration_days: int


class BacktestEngine:
    """
    Backtest Motoru
    Stratejileri geçmiş verilerle test eder
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.current_time = config.start_date
        self.balance = config.initial_balance
        self.initial_balance = config.initial_balance
        
        # İşlem takibi
        self.trades: List[BacktestTrade] = []
        self.open_trades: Dict[str, BacktestTrade] = {}
        
        # Performance tracking
        self.balance_history: List[Tuple[datetime, float]] = []
        self.drawdown_history: List[Tuple[datetime, float]] = []
        self.peak_balance = config.initial_balance
        
        # Risk manager (backtest için)
        self.risk_manager: Optional[RiskManager] = None
        
        logger.info(f"BacktestEngine başlatıldı: {config.start_date} - {config.end_date}")
    
    def set_risk_manager(self, risk_manager: RiskManager) -> None:
        """Risk manager ayarla"""
        self.risk_manager = risk_manager
    
    async def run_backtest(self, 
                          strategy: BaseStrategy, 
                          data_provider,
                          progress_callback: Optional[callable] = None) -> BacktestResult:
        """
        Backtest çalıştır
        Args:
            strategy: Test edilecek strateji
            data_provider: Veri sağlayıcı
            progress_callback: İlerleme callback'i
        Returns: Backtest sonucu
        """
        try:
            start_time = datetime.utcnow()
            logger.info(f"Backtest başlatıldı: {strategy.config.name}")
            
            # Stratejiyi başlat
            strategy.start()
            
            # Veri sağlayıcıyı başlat
            await data_provider.initialize(self.config)
            
            # Ana backtest döngüsü
            total_ticks = await data_provider.get_total_ticks()
            processed_ticks = 0
            
            async for market_data in data_provider.get_market_data():
                # Zamanı güncelle
                self.current_time = market_data.timestamp
                
                # Açık işlemleri kontrol et (expiry)
                await self._check_open_trades(market_data)
                
                # Stratejiyi güncelle
                signal = await strategy.update_market_data(market_data)
                
                # Sinyal varsa işlem aç
                if signal:
                    await self._process_signal(signal, market_data)
                
                # Balance history güncelle
                self._update_balance_history()
                
                # Progress callback
                processed_ticks += 1
                if progress_callback and processed_ticks % 1000 == 0:
                    progress = processed_ticks / total_ticks if total_ticks > 0 else 0
                    await progress_callback(progress, processed_ticks, total_ticks)
            
            # Kalan açık işlemleri kapat
            await self._close_all_open_trades()
            
            # Sonuçları hesapla
            end_time = datetime.utcnow()
            result = self._calculate_results(start_time, end_time)
            
            logger.info(f"Backtest tamamlandı: {len(self.trades)} işlem, "
                       f"Final Balance: {self.balance:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Backtest hatası: {e}")
            raise
    
    async def _process_signal(self, signal: TradeSignal, market_data: MarketData) -> None:
        """Sinyali işle ve işlem aç"""
        try:
            # Risk kontrolü
            if self.risk_manager:
                validation = await self.risk_manager.validate_trade(signal, self.balance)
                if not validation['approved']:
                    logger.debug(f"İşlem reddedildi: {validation['reason']}")
                    return
                
                # Pozisyon boyutunu güncelle
                signal.amount = validation['suggested_amount']
            
            # İşlem aç
            trade = BacktestTrade(
                signal=signal,
                entry_time=self.current_time,
                entry_price=market_data.last,
                commission=signal.amount * self.config.commission,
                slippage=signal.amount * self.config.slippage
            )
            
            # Trade ID oluştur
            trade_id = f"{signal.symbol}_{signal.timestamp.strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Açık işlemler listesine ekle
            self.open_trades[trade_id] = trade
            
            # Bakiyeden düş (commission + slippage)
            self.balance -= (trade.commission + trade.slippage)
            
            logger.debug(f"İşlem açıldı: {signal.symbol} {signal.direction} "
                        f"{signal.amount} @ {market_data.last}")
            
        except Exception as e:
            logger.error(f"Sinyal işleme hatası: {e}")
    
    async def _check_open_trades(self, market_data: MarketData) -> None:
        """Açık işlemleri kontrol et (expiry)"""
        try:
            expired_trades = []
            
            for trade_id, trade in self.open_trades.items():
                if trade.signal.symbol != market_data.symbol:
                    continue
                
                # Expiry kontrolü
                expiry_time = trade.entry_time + timedelta(seconds=trade.signal.expiry_time)
                
                if self.current_time >= expiry_time:
                    # İşlemi kapat
                    await self._close_trade(trade_id, trade, market_data)
                    expired_trades.append(trade_id)
            
            # Kapatılan işlemleri kaldır
            for trade_id in expired_trades:
                del self.open_trades[trade_id]
                
        except Exception as e:
            logger.error(f"Açık işlem kontrolü hatası: {e}")
    
    async def _close_trade(self, trade_id: str, trade: BacktestTrade, market_data: MarketData) -> None:
        """İşlemi kapat"""
        try:
            trade.exit_time = self.current_time
            trade.exit_price = market_data.last
            trade.status = "closed"
            
            # P&L hesapla (binary options için)
            if self._is_trade_successful(trade, market_data):
                # Başarılı - payout al (genelde %80-90)
                payout_rate = 0.85  # %85 payout
                trade.profit_loss = trade.signal.amount * payout_rate
            else:
                # Başarısız - tutar kaybedilir
                trade.profit_loss = -trade.signal.amount
            
            # Bakiyeyi güncelle
            self.balance += trade.signal.amount + trade.profit_loss  # Amount + profit/loss
            
            # İşlemi geçmişe ekle
            self.trades.append(trade)
            
            # Risk manager'a bildir
            if self.risk_manager:
                result = {
                    'success': trade.profit_loss > 0,
                    'profit': max(0, trade.profit_loss),
                    'loss': max(0, -trade.profit_loss),
                    'trade_id': trade_id
                }
                await self.risk_manager.close_trade(trade_id, result)
            
            logger.debug(f"İşlem kapatıldı: {trade.signal.symbol} {trade.signal.direction} "
                        f"P&L: {trade.profit_loss:.2f}")
            
        except Exception as e:
            logger.error(f"İşlem kapatma hatası: {e}")
    
    def _is_trade_successful(self, trade: BacktestTrade, market_data: MarketData) -> bool:
        """İşlem başarılı mı? (Binary options mantığı)"""
        try:
            entry_price = trade.entry_price
            exit_price = market_data.last
            
            if trade.signal.direction == "CALL":
                return exit_price > entry_price
            elif trade.signal.direction == "PUT":
                return exit_price < entry_price
            else:
                return False
                
        except Exception as e:
            logger.error(f"İşlem başarı kontrolü hatası: {e}")
            return False
    
    async def _close_all_open_trades(self) -> None:
        """Tüm açık işlemleri kapat"""
        try:
            for trade_id, trade in list(self.open_trades.items()):
                # Son fiyatla kapat
                fake_market_data = MarketData(
                    symbol=trade.signal.symbol,
                    timestamp=self.current_time,
                    bid=trade.entry_price,
                    ask=trade.entry_price,
                    last=trade.entry_price,
                    volume=0.0
                )
                
                await self._close_trade(trade_id, trade, fake_market_data)
            
            self.open_trades.clear()
            
        except Exception as e:
            logger.error(f"Açık işlemleri kapatma hatası: {e}")
    
    def _update_balance_history(self) -> None:
        """Balance geçmişini güncelle"""
        try:
            self.balance_history.append((self.current_time, self.balance))
            
            # Peak balance güncelle
            if self.balance > self.peak_balance:
                self.peak_balance = self.balance
            
            # Drawdown hesapla
            drawdown = self.peak_balance - self.balance
            drawdown_percentage = (drawdown / self.peak_balance) * 100 if self.peak_balance > 0 else 0
            
            self.drawdown_history.append((self.current_time, drawdown_percentage))
            
        except Exception as e:
            logger.error(f"Balance history güncelleme hatası: {e}")
    
    def _calculate_results(self, start_time: datetime, end_time: datetime) -> BacktestResult:
        """Backtest sonuçlarını hesapla"""
        try:
            # Temel metrikler
            total_return = self.balance - self.initial_balance
            total_return_percentage = (total_return / self.initial_balance) * 100
            
            # İşlem istatistikleri
            total_trades = len(self.trades)
            winning_trades = sum(1 for trade in self.trades if trade.is_profitable)
            losing_trades = total_trades - winning_trades
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Ortalama kazanç/kayıp
            wins = [trade.profit_loss for trade in self.trades if trade.is_profitable]
            losses = [abs(trade.profit_loss) for trade in self.trades if not trade.is_profitable]
            
            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            # Profit factor
            total_wins = sum(wins)
            total_losses = sum(losses)
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            # Drawdown
            max_drawdown_percentage = max([dd[1] for dd in self.drawdown_history]) if self.drawdown_history else 0
            max_drawdown = max_drawdown_percentage * self.peak_balance / 100
            
            # Sharpe ratio (basitleştirilmiş)
            if len(self.balance_history) > 1:
                returns = []
                for i in range(1, len(self.balance_history)):
                    prev_balance = self.balance_history[i-1][1]
                    curr_balance = self.balance_history[i][1]
                    daily_return = (curr_balance - prev_balance) / prev_balance if prev_balance > 0 else 0
                    returns.append(daily_return)
                
                if returns:
                    avg_return = sum(returns) / len(returns)
                    return_std = (sum([(r - avg_return) ** 2 for r in returns]) / len(returns)) ** 0.5
                    sharpe_ratio = avg_return / return_std if return_std > 0 else 0
                else:
                    sharpe_ratio = 0
            else:
                sharpe_ratio = 0
            
            # Consecutive wins/losses
            max_consecutive_wins = 0
            max_consecutive_losses = 0
            current_wins = 0
            current_losses = 0
            
            for trade in self.trades:
                if trade.is_profitable:
                    current_wins += 1
                    current_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, current_wins)
                else:
                    current_losses += 1
                    current_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, current_losses)
            
            # Duration
            duration_days = (self.config.end_date - self.config.start_date).days
            
            return BacktestResult(
                config=self.config,
                trades=self.trades,
                final_balance=self.balance,
                total_return=total_return,
                total_return_percentage=total_return_percentage,
                max_drawdown=max_drawdown,
                max_drawdown_percentage=max_drawdown_percentage,
                sharpe_ratio=sharpe_ratio,
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                avg_win=avg_win,
                avg_loss=avg_loss,
                max_consecutive_wins=max_consecutive_wins,
                max_consecutive_losses=max_consecutive_losses,
                start_time=start_time,
                end_time=end_time,
                duration_days=duration_days
            )
            
        except Exception as e:
            logger.error(f"Sonuç hesaplama hatası: {e}")
            raise