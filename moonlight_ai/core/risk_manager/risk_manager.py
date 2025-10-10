"""
Risk Manager
Risk yönetimi ve pozisyon kontrolü
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from ..market_connector.base_connector import TradeSignal

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk seviyeleri"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskLimits:
    """Risk limitleri"""
    max_daily_loss: float = 100.0  # USD
    max_position_size: float = 10.0  # USD
    max_concurrent_trades: int = 3
    max_daily_trades: int = 50
    stop_loss_percentage: float = 5.0
    take_profit_percentage: float = 10.0
    max_drawdown_percentage: float = 20.0
    risk_per_trade_percentage: float = 2.0
    
    def validate(self) -> bool:
        """Limit değerlerini doğrula"""
        try:
            assert self.max_daily_loss > 0, "Günlük maksimum kayıp pozitif olmalı"
            assert self.max_position_size > 0, "Maksimum pozisyon boyutu pozitif olmalı"
            assert self.max_concurrent_trades > 0, "Maksimum eşzamanlı işlem sayısı pozitif olmalı"
            assert self.max_daily_trades > 0, "Günlük maksimum işlem sayısı pozitif olmalı"
            assert 0 < self.stop_loss_percentage < 100, "Stop loss yüzdesi 0-100 arasında olmalı"
            assert 0 < self.take_profit_percentage < 100, "Take profit yüzdesi 0-100 arasında olmalı"
            assert 0 < self.max_drawdown_percentage < 100, "Maksimum drawdown yüzdesi 0-100 arasında olmalı"
            assert 0 < self.risk_per_trade_percentage < 100, "İşlem başına risk yüzdesi 0-100 arasında olmalı"
            return True
        except AssertionError as e:
            logger.error(f"Risk limiti doğrulama hatası: {e}")
            return False


@dataclass
class TradeRecord:
    """İşlem kaydı"""
    signal: TradeSignal
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    profit_loss: float = 0.0
    status: str = "active"  # active, completed, cancelled
    
    @property
    def is_active(self) -> bool:
        """İşlem aktif mi?"""
        return self.status == "active"
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """İşlem süresi (saniye)"""
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds())
        return None


@dataclass
class RiskMetrics:
    """Risk metrikleri"""
    current_balance: float = 0.0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    active_trades: int = 0
    daily_trades: int = 0
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    risk_level: RiskLevel = RiskLevel.LOW
    
    def update_risk_level(self) -> None:
        """Risk seviyesini güncelle"""
        if self.current_drawdown > 15.0:
            self.risk_level = RiskLevel.CRITICAL
        elif self.current_drawdown > 10.0 or abs(self.daily_pnl) > 50.0:
            self.risk_level = RiskLevel.HIGH
        elif self.current_drawdown > 5.0 or abs(self.daily_pnl) > 25.0:
            self.risk_level = RiskLevel.MEDIUM
        else:
            self.risk_level = RiskLevel.LOW


class RiskManager:
    """
    Risk yöneticisi
    İşlem risklerini kontrol eder ve pozisyon boyutlarını yönetir
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.limits = RiskLimits(**config.get('risk_management', {}))
        
        if not self.limits.validate():
            raise ValueError("Geçersiz risk limitleri")
        
        self.metrics = RiskMetrics()
        self.active_trades: Dict[str, TradeRecord] = {}
        self.trade_history: List[TradeRecord] = []
        self.daily_reset_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        logger.info("RiskManager başlatıldı")
    
    async def validate_trade(self, signal: TradeSignal, current_balance: float) -> Dict[str, Any]:
        """
        İşlem doğrulama ve risk kontrolü
        Args:
            signal: İşlem sinyali
            current_balance: Güncel bakiye
        Returns: Doğrulama sonucu
        """
        try:
            # Güncel metrikleri güncelle
            self.metrics.current_balance = current_balance
            self._update_daily_metrics()
            
            validation_result = {
                'approved': False,
                'reason': '',
                'suggested_amount': 0.0,
                'risk_level': self.metrics.risk_level.value,
                'warnings': []
            }
            
            # Temel kontroller
            if not self._basic_validation(signal, validation_result):
                return validation_result
            
            # Risk limiti kontrolleri
            if not self._risk_limit_checks(signal, validation_result):
                return validation_result
            
            # Pozisyon boyutu hesaplama
            suggested_amount = self._calculate_position_size(signal, current_balance)
            validation_result['suggested_amount'] = suggested_amount
            
            # Son onay
            if suggested_amount > 0:
                validation_result['approved'] = True
                validation_result['reason'] = 'İşlem onaylandı'
                
                # Uyarılar ekle
                self._add_warnings(validation_result)
                
                logger.info(f"İşlem onaylandı: {signal.symbol} {signal.direction} "
                           f"(Tutar: {suggested_amount:.2f})")
            else:
                validation_result['reason'] = 'Pozisyon boyutu hesaplanamadı'
            
            return validation_result
            
        except Exception as e:
            logger.error(f"İşlem doğrulama hatası: {e}")
            return {
                'approved': False,
                'reason': f'Doğrulama hatası: {str(e)}',
                'suggested_amount': 0.0,
                'risk_level': RiskLevel.CRITICAL.value,
                'warnings': []
            }
    
    async def register_trade(self, signal: TradeSignal) -> str:
        """
        İşlem kaydı oluştur
        Args:
            signal: İşlem sinyali
        Returns: İşlem ID'si
        """
        try:
            trade_id = f"{signal.symbol}_{signal.timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            trade_record = TradeRecord(
                signal=signal,
                start_time=datetime.utcnow(),
                status="active"
            )
            
            self.active_trades[trade_id] = trade_record
            self.metrics.active_trades = len(self.active_trades)
            self.metrics.daily_trades += 1
            self.metrics.total_trades += 1
            
            logger.info(f"İşlem kaydedildi: {trade_id}")
            return trade_id
            
        except Exception as e:
            logger.error(f"İşlem kaydetme hatası: {e}")
            raise
    
    async def close_trade(self, trade_id: str, result: Dict[str, Any]) -> None:
        """
        İşlem kapatma
        Args:
            trade_id: İşlem ID'si
            result: İşlem sonucu
        """
        try:
            if trade_id not in self.active_trades:
                logger.warning(f"Bilinmeyen işlem ID: {trade_id}")
                return
            
            trade_record = self.active_trades[trade_id]
            trade_record.end_time = datetime.utcnow()
            trade_record.result = result
            trade_record.status = "completed"
            
            # Kar/zarar hesapla
            profit_loss = result.get('profit', 0.0) - result.get('loss', 0.0)
            trade_record.profit_loss = profit_loss
            
            # Metrikleri güncelle
            self.metrics.daily_pnl += profit_loss
            self.metrics.total_pnl += profit_loss
            
            if profit_loss > 0:
                self.metrics.winning_trades += 1
            
            # Win rate hesapla
            if self.metrics.total_trades > 0:
                self.metrics.win_rate = (self.metrics.winning_trades / self.metrics.total_trades) * 100
            
            # Drawdown hesapla
            self._update_drawdown()
            
            # İşlemi geçmişe taşı
            self.trade_history.append(trade_record)
            del self.active_trades[trade_id]
            
            self.metrics.active_trades = len(self.active_trades)
            self.metrics.update_risk_level()
            
            logger.info(f"İşlem kapatıldı: {trade_id} (P&L: {profit_loss:.2f})")
            
        except Exception as e:
            logger.error(f"İşlem kapatma hatası: {e}")
    
    def _basic_validation(self, signal: TradeSignal, result: Dict[str, Any]) -> bool:
        """Temel doğrulama kontrolleri"""
        if not signal.symbol:
            result['reason'] = 'Geçersiz sembol'
            return False
        
        if signal.direction not in ['CALL', 'PUT']:
            result['reason'] = 'Geçersiz yön'
            return False
        
        if signal.amount <= 0:
            result['reason'] = 'Geçersiz tutar'
            return False
        
        if signal.expiry_time <= 0:
            result['reason'] = 'Geçersiz vade süresi'
            return False
        
        return True
    
    def _risk_limit_checks(self, signal: TradeSignal, result: Dict[str, Any]) -> bool:
        """Risk limiti kontrolleri"""
        # Günlük kayıp kontrolü
        if abs(self.metrics.daily_pnl) >= self.limits.max_daily_loss:
            result['reason'] = f'Günlük kayıp limiti aşıldı ({self.limits.max_daily_loss})'
            return False
        
        # Eşzamanlı işlem kontrolü
        if self.metrics.active_trades >= self.limits.max_concurrent_trades:
            result['reason'] = f'Maksimum eşzamanlı işlem sayısı aşıldı ({self.limits.max_concurrent_trades})'
            return False
        
        # Günlük işlem kontrolü
        if self.metrics.daily_trades >= self.limits.max_daily_trades:
            result['reason'] = f'Günlük işlem limiti aşıldı ({self.limits.max_daily_trades})'
            return False
        
        # Pozisyon boyutu kontrolü
        if signal.amount > self.limits.max_position_size:
            result['reason'] = f'Maksimum pozisyon boyutu aşıldı ({self.limits.max_position_size})'
            return False
        
        # Drawdown kontrolü
        if self.metrics.current_drawdown >= self.limits.max_drawdown_percentage:
            result['reason'] = f'Maksimum drawdown aşıldı ({self.limits.max_drawdown_percentage}%)'
            return False
        
        return True
    
    def _calculate_position_size(self, signal: TradeSignal, current_balance: float) -> float:
        """
        Pozisyon boyutu hesaplama
        Args:
            signal: İşlem sinyali
            current_balance: Güncel bakiye
        Returns: Önerilen pozisyon boyutu
        """
        try:
            # Risk yüzdesine göre hesaplama
            risk_amount = current_balance * (self.limits.risk_per_trade_percentage / 100)
            
            # Maksimum pozisyon boyutu kontrolü
            max_amount = min(risk_amount, self.limits.max_position_size)
            
            # Sinyal tutarı ile karşılaştır
            suggested_amount = min(signal.amount, max_amount)
            
            # Minimum tutar kontrolü (1 USD)
            if suggested_amount < 1.0:
                return 0.0
            
            return round(suggested_amount, 2)
            
        except Exception as e:
            logger.error(f"Pozisyon boyutu hesaplama hatası: {e}")
            return 0.0
    
    def _add_warnings(self, result: Dict[str, Any]) -> None:
        """Uyarı mesajları ekle"""
        warnings = []
        
        # Risk seviyesi uyarıları
        if self.metrics.risk_level == RiskLevel.HIGH:
            warnings.append("Yüksek risk seviyesi tespit edildi")
        elif self.metrics.risk_level == RiskLevel.CRITICAL:
            warnings.append("Kritik risk seviyesi - dikkatli olun")
        
        # Drawdown uyarıları
        if self.metrics.current_drawdown > 10.0:
            warnings.append(f"Yüksek drawdown: {self.metrics.current_drawdown:.1f}%")
        
        # Günlük kayıp uyarıları
        if abs(self.metrics.daily_pnl) > self.limits.max_daily_loss * 0.8:
            warnings.append("Günlük kayıp limitine yaklaşılıyor")
        
        result['warnings'] = warnings
    
    def _update_daily_metrics(self) -> None:
        """Günlük metrikleri güncelle"""
        now = datetime.utcnow()
        current_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Yeni gün başladı mı?
        if current_day > self.daily_reset_time:
            self.metrics.daily_pnl = 0.0
            self.metrics.daily_trades = 0
            self.daily_reset_time = current_day
            logger.info("Günlük metrikler sıfırlandı")
    
    def _update_drawdown(self) -> None:
        """Drawdown hesaplama"""
        try:
            if not self.trade_history:
                return
            
            # Kümülatif P&L hesapla
            cumulative_pnl = []
            running_total = 0.0
            
            for trade in self.trade_history:
                running_total += trade.profit_loss
                cumulative_pnl.append(running_total)
            
            if not cumulative_pnl:
                return
            
            # Peak ve drawdown hesapla
            peak = cumulative_pnl[0]
            max_drawdown = 0.0
            current_drawdown = 0.0
            
            for pnl in cumulative_pnl:
                if pnl > peak:
                    peak = pnl
                
                drawdown = ((peak - pnl) / abs(peak)) * 100 if peak != 0 else 0.0
                
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                
                current_drawdown = drawdown
            
            self.metrics.max_drawdown = max_drawdown
            self.metrics.current_drawdown = current_drawdown
            
        except Exception as e:
            logger.error(f"Drawdown hesaplama hatası: {e}")
    
    def get_risk_report(self) -> Dict[str, Any]:
        """Risk raporu"""
        return {
            'metrics': {
                'current_balance': self.metrics.current_balance,
                'daily_pnl': self.metrics.daily_pnl,
                'total_pnl': self.metrics.total_pnl,
                'active_trades': self.metrics.active_trades,
                'daily_trades': self.metrics.daily_trades,
                'total_trades': self.metrics.total_trades,
                'winning_trades': self.metrics.winning_trades,
                'win_rate': self.metrics.win_rate,
                'max_drawdown': self.metrics.max_drawdown,
                'current_drawdown': self.metrics.current_drawdown,
                'risk_level': self.metrics.risk_level.value
            },
            'limits': {
                'max_daily_loss': self.limits.max_daily_loss,
                'max_position_size': self.limits.max_position_size,
                'max_concurrent_trades': self.limits.max_concurrent_trades,
                'max_daily_trades': self.limits.max_daily_trades,
                'max_drawdown_percentage': self.limits.max_drawdown_percentage,
                'risk_per_trade_percentage': self.limits.risk_per_trade_percentage
            },
            'active_trades': len(self.active_trades),
            'trade_history_count': len(self.trade_history)
        }