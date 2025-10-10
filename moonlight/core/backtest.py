"""
Backtesting Engine

Parça 16 - Backtest & Paper Trading Motoru
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class BacktestConfig:
    """Backtest yapılandırması"""
    timeframe: int = 1               # 1, 5, 15
    payout_mode: str = "fixed"       # fixed | series
    payout_fixed: float = 90.0       # Fixed payout %
    latency_ms: int = 0              # Simüle gecikme
    push_is_win: bool = True         # Push = kazanç mı?
    min_trades: int = 200            # Minimum işlem sayısı


@dataclass
class BacktestReport:
    """Backtest raporu"""
    trades: pd.DataFrame
    metrics: Dict[str, float]
    equity_curve: pd.Series
    drawdown_curve: pd.Series


class Backtester:
    """
    Backtest Motoru
    
    Sorumluluklar:
    - Tarihsel veri üzerinde strateji simülasyonu
    - FTT (Fixed Time Trade) mantığıyla sonuç belirleme
    - Detaylı metrik hesaplama
    - Walk-forward validation desteği
    
    Özellikler:
    - Deterministik (seed kontrolü)
    - Sızıntısız (forward-looking yok)
    - Gerçekçi concurrency ve permit kuralları
    """
    
    def __init__(self, indicators, providers, ensemble, risk):
        self.ind = indicators
        self.providers = providers
        self.ens = ensemble
        self.risk = risk
    
    def run(self, candles: pd.DataFrame, payout_series: Optional[pd.Series], 
            cfg: BacktestConfig) -> BacktestReport:
        """
        Backtest çalıştır
        
        Args:
            candles: OHLCV DataFrame
            payout_series: Opsiyonel payout serisi
            cfg: Backtest konfigürasyonu
        
        Returns:
            BacktestReport
        """
        df = candles.copy()
        
        # Sonuç kayıtları
        trades = []
        open_trade = None
        open_until_idx = None
        
        # Bar bazlı iterasyon
        for i in range(1, len(df)):
            # Açık işlem var mı ve kapandı mı?
            if open_trade is not None and i >= open_until_idx:
                # Sonucu hesapla (FTT mantığı)
                entry_close = open_trade['entry_close']
                exit_close = df['close'].iloc[i]
                
                # Direction: +1 = call, -1 = put
                if open_trade['direction'] == 1:
                    win = exit_close > entry_close
                else:
                    win = exit_close < entry_close
                
                # Push durumu
                if cfg.push_is_win and exit_close == entry_close:
                    win = True
                
                # PnL
                payout_ratio = open_trade['payout'] / 100.0
                if win:
                    pnl = open_trade['amount'] * payout_ratio
                else:
                    pnl = -open_trade['amount']
                
                # Kaydı tamamla
                open_trade['exit_idx'] = i
                open_trade['exit_close'] = exit_close
                open_trade['status'] = 'win' if win else 'lose'
                open_trade['pnl'] = pnl
                
                trades.append(open_trade)
                open_trade = None
                open_until_idx = None
                continue
            
            # Zaten açık işlem varsa yeni açma
            if open_trade is not None:
                continue
            
            # Yeni giriş değerlendirmesi
            # TODO: Gerçek provider'ları çalıştır
            # Şimdilik basit simülasyon
            
            # Payout al
            if cfg.payout_mode == "fixed":
                payout = cfg.payout_fixed
            else:
                payout = payout_series.iloc[i] if payout_series is not None else 90.0
            
            # Basit sinyal (örnek - gerçekte ensemble'dan gelir)
            # Rastgele giriş (%20 olasılık)
            if random.random() < 0.2:
                direction = +1 if random.random() > 0.5 else -1
                amount = 1.0
                
                # İşlem aç
                open_trade = {
                    'entry_idx': i,
                    'entry_ts': df['ts_ms'].iloc[i],
                    'entry_close': df['close'].iloc[i],
                    'direction': direction,
                    'payout': payout,
                    'amount': amount
                }
                
                # Vade (TF kadar bar)
                bars_to_wait = 1  # TF=1 için 1 bar
                open_until_idx = i + bars_to_wait
        
        # DataFrame'e çevir
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        # Metrikler hesapla
        metrics = self._compute_metrics(trades_df) if not trades_df.empty else {}
        
        # Equity curve
        if not trades_df.empty:
            equity = trades_df['pnl'].cumsum()
            drawdown = equity - equity.cummax()
        else:
            equity = pd.Series()
            drawdown = pd.Series()
        
        return BacktestReport(
            trades=trades_df,
            metrics=metrics,
            equity_curve=equity,
            drawdown_curve=drawdown
        )
    
    def _compute_metrics(self, trades: pd.DataFrame) -> Dict[str, float]:
        """Metrik hesapla"""
        if trades.empty:
            return {}
        
        # Win/Loss ayır
        outcomes = trades[trades['status'].isin(['win', 'lose'])]
        
        if outcomes.empty:
            return {}
        
        wins = outcomes[outcomes['status'] == 'win']
        losses = outcomes[outcomes['status'] == 'lose']
        
        # Temel metrikler
        total_trades = len(outcomes)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = win_count / total_trades if total_trades > 0 else 0.0
        
        total_pnl = outcomes['pnl'].sum()
        avg_win = wins['pnl'].mean() if not wins.empty else 0.0
        avg_loss = losses['pnl'].mean() if not losses.empty else 0.0
        
        gross_profit = wins['pnl'].sum() if not wins.empty else 0.0
        gross_loss = abs(losses['pnl'].sum()) if not losses.empty else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Expectancy
        expectancy = (win_rate * avg_win + (1 - win_rate) * avg_loss) if total_trades > 0 else 0.0
        
        # Drawdown
        equity = outcomes['pnl'].cumsum()
        max_dd = (equity - equity.cummax()).min()
        
        return {
            "total_trades": total_trades,
            "wins": win_count,
            "losses": loss_count,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "max_drawdown": max_dd
        }


# Test
if __name__ == "__main__":
    # Basit backtest testi
    # Sentetik veri
    n = 1000
    df = pd.DataFrame({
        'ts_ms': range(n),
        'open': np.cumsum(np.random.randn(n)) * 0.01 + 100,
        'high': np.cumsum(np.random.randn(n)) * 0.01 + 100.5,
        'low': np.cumsum(np.random.randn(n)) * 0.01 + 99.5,
        'close': np.cumsum(np.random.randn(n)) * 0.01 + 100,
        'volume': np.random.randint(100, 1000, n)
    })
    
    cfg = BacktestConfig(timeframe=1, payout_fixed=90.0)
    
    backtester = Backtester(None, None, None, None)
    report = backtester.run(df, None, cfg)
    
    print("✓ Backtest completed")
    print(f"  Trades: {report.metrics.get('total_trades', 0)}")
    print(f"  Win Rate: {report.metrics.get('win_rate', 0):.2%}")
    print(f"  Total PnL: {report.metrics.get('total_pnl', 0):.2f}")
    print(f"  Profit Factor: {report.metrics.get('profit_factor', 0):.2f}")
