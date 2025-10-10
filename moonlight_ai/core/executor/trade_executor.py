"""
Trade Executor
İşlem yürütme ve emir yönetimi
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from ..market_connector.base_connector import TradeSignal

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """İşlem yürütme durumları"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeExecutor:
    """
    İşlem yürütücü
    Sinyalleri alır ve market connector üzerinden işlemleri yürütür
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pending_trades: Dict[str, Dict[str, Any]] = {}
        self.execution_history: List[Dict[str, Any]] = []
        
        # Yürütme ayarları
        self.max_retry_attempts = config.get('max_retry_attempts', 3)
        self.retry_delay = config.get('retry_delay', 1.0)  # saniye
        self.execution_timeout = config.get('execution_timeout', 30.0)  # saniye
        
        logger.info("TradeExecutor başlatıldı")
    
    async def execute_trade(self, signal: TradeSignal) -> Dict[str, Any]:
        """
        İşlem yürütme
        Args:
            signal: İşlem sinyali
        Returns: Yürütme sonucu
        """
        execution_id = f"exec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        execution_record = {
            'id': execution_id,
            'signal': signal,
            'status': ExecutionStatus.PENDING,
            'start_time': datetime.utcnow(),
            'end_time': None,
            'attempts': 0,
            'result': None,
            'error': None
        }
        
        self.pending_trades[execution_id] = execution_record
        
        try:
            logger.info(f"İşlem yürütme başlatıldı: {execution_id} - "
                       f"{signal.symbol} {signal.direction} {signal.amount}")
            
            # Yürütme durumunu güncelle
            execution_record['status'] = ExecutionStatus.EXECUTING
            
            # Retry loop
            for attempt in range(self.max_retry_attempts):
                execution_record['attempts'] = attempt + 1
                
                try:
                    # Timeout ile yürütme
                    result = await asyncio.wait_for(
                        self._execute_with_connector(signal),
                        timeout=self.execution_timeout
                    )
                    
                    # Başarılı yürütme
                    execution_record['status'] = ExecutionStatus.COMPLETED
                    execution_record['result'] = result
                    execution_record['end_time'] = datetime.utcnow()
                    
                    logger.info(f"İşlem başarıyla yürütüldü: {execution_id}")
                    
                    # Geçmişe ekle
                    self.execution_history.append(execution_record.copy())
                    
                    return {
                        'success': True,
                        'execution_id': execution_id,
                        'result': result,
                        'attempts': execution_record['attempts'],
                        'duration': (execution_record['end_time'] - execution_record['start_time']).total_seconds()
                    }
                    
                except asyncio.TimeoutError:
                    error_msg = f"İşlem timeout (deneme {attempt + 1}/{self.max_retry_attempts})"
                    logger.warning(f"{execution_id}: {error_msg}")
                    execution_record['error'] = error_msg
                    
                    if attempt < self.max_retry_attempts - 1:
                        await asyncio.sleep(self.retry_delay)
                    
                except Exception as e:
                    error_msg = f"İşlem yürütme hatası: {str(e)} (deneme {attempt + 1}/{self.max_retry_attempts})"
                    logger.error(f"{execution_id}: {error_msg}")
                    execution_record['error'] = error_msg
                    
                    if attempt < self.max_retry_attempts - 1:
                        await asyncio.sleep(self.retry_delay)
            
            # Tüm denemeler başarısız
            execution_record['status'] = ExecutionStatus.FAILED
            execution_record['end_time'] = datetime.utcnow()
            
            logger.error(f"İşlem yürütme başarısız: {execution_id} - "
                        f"Tüm denemeler tükendi ({self.max_retry_attempts})")
            
            # Geçmişe ekle
            self.execution_history.append(execution_record.copy())
            
            return {
                'success': False,
                'execution_id': execution_id,
                'error': execution_record['error'],
                'attempts': execution_record['attempts']
            }
            
        except Exception as e:
            # Beklenmeyen hata
            execution_record['status'] = ExecutionStatus.FAILED
            execution_record['error'] = f"Kritik hata: {str(e)}"
            execution_record['end_time'] = datetime.utcnow()
            
            logger.error(f"İşlem yürütme kritik hatası: {execution_id} - {e}")
            
            # Geçmişe ekle
            self.execution_history.append(execution_record.copy())
            
            return {
                'success': False,
                'execution_id': execution_id,
                'error': execution_record['error'],
                'attempts': execution_record['attempts']
            }
            
        finally:
            # Pending listesinden kaldır
            if execution_id in self.pending_trades:
                del self.pending_trades[execution_id]
    
    async def _execute_with_connector(self, signal: TradeSignal) -> Dict[str, Any]:
        """
        Market connector ile işlem yürütme
        Args:
            signal: İşlem sinyali
        Returns: Connector'dan dönen sonuç
        """
        # Bu method gerçek uygulamada market connector'a bağlanacak
        # Şimdilik simülasyon yapıyoruz
        
        # Simülasyon gecikmesi
        await asyncio.sleep(0.1)
        
        # Simülasyon sonucu
        # Gerçek uygulamada: return await market_connector.place_trade(signal)
        
        # Demo sonuç
        success_rate = 0.7  # %70 başarı oranı
        import random
        
        is_successful = random.random() < success_rate
        
        if is_successful:
            profit = signal.amount * 0.8  # %80 kazanç
            return {
                'success': True,
                'trade_id': f"trade_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'symbol': signal.symbol,
                'direction': signal.direction,
                'amount': signal.amount,
                'profit': profit,
                'loss': 0.0,
                'payout_percentage': 80.0,
                'start_time': datetime.utcnow().isoformat(),
                'expiry_time': signal.expiry_time,
                'status': 'completed'
            }
        else:
            return {
                'success': False,
                'trade_id': f"trade_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                'symbol': signal.symbol,
                'direction': signal.direction,
                'amount': signal.amount,
                'profit': 0.0,
                'loss': signal.amount,
                'payout_percentage': 0.0,
                'start_time': datetime.utcnow().isoformat(),
                'expiry_time': signal.expiry_time,
                'status': 'completed'
            }
    
    async def cancel_trade(self, execution_id: str) -> bool:
        """
        İşlem iptal etme
        Args:
            execution_id: Yürütme ID'si
        Returns: İptal başarılı ise True
        """
        try:
            if execution_id in self.pending_trades:
                execution_record = self.pending_trades[execution_id]
                
                if execution_record['status'] == ExecutionStatus.PENDING:
                    execution_record['status'] = ExecutionStatus.CANCELLED
                    execution_record['end_time'] = datetime.utcnow()
                    execution_record['error'] = "Kullanıcı tarafından iptal edildi"
                    
                    # Geçmişe ekle
                    self.execution_history.append(execution_record.copy())
                    
                    # Pending listesinden kaldır
                    del self.pending_trades[execution_id]
                    
                    logger.info(f"İşlem iptal edildi: {execution_id}")
                    return True
                else:
                    logger.warning(f"İşlem iptal edilemez (durum: {execution_record['status']}): {execution_id}")
                    return False
            else:
                logger.warning(f"İşlem bulunamadı: {execution_id}")
                return False
                
        except Exception as e:
            logger.error(f"İşlem iptal etme hatası: {e}")
            return False
    
    def get_pending_trades(self) -> Dict[str, Dict[str, Any]]:
        """Bekleyen işlemler listesi"""
        return {
            execution_id: {
                'id': record['id'],
                'symbol': record['signal'].symbol,
                'direction': record['signal'].direction,
                'amount': record['signal'].amount,
                'status': record['status'].value,
                'start_time': record['start_time'].isoformat(),
                'attempts': record['attempts']
            }
            for execution_id, record in self.pending_trades.items()
        }
    
    def get_execution_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Yürütme geçmişi
        Args:
            limit: Maksimum kayıt sayısı
        Returns: Yürütme geçmişi listesi
        """
        history = self.execution_history.copy()
        
        # Tarihe göre sırala (en yeni önce)
        history.sort(key=lambda x: x['start_time'], reverse=True)
        
        if limit:
            history = history[:limit]
        
        # Serialize edilebilir format
        result = []
        for record in history:
            result.append({
                'id': record['id'],
                'symbol': record['signal'].symbol,
                'direction': record['signal'].direction,
                'amount': record['signal'].amount,
                'status': record['status'].value,
                'start_time': record['start_time'].isoformat(),
                'end_time': record['end_time'].isoformat() if record['end_time'] else None,
                'attempts': record['attempts'],
                'success': record['result'].get('success', False) if record['result'] else False,
                'profit': record['result'].get('profit', 0.0) if record['result'] else 0.0,
                'loss': record['result'].get('loss', 0.0) if record['result'] else 0.0,
                'error': record['error']
            })
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Yürütme istatistikleri"""
        total_executions = len(self.execution_history)
        successful_executions = sum(1 for record in self.execution_history 
                                  if record['status'] == ExecutionStatus.COMPLETED 
                                  and record['result'] 
                                  and record['result'].get('success', False))
        
        failed_executions = sum(1 for record in self.execution_history 
                              if record['status'] == ExecutionStatus.FAILED)
        
        cancelled_executions = sum(1 for record in self.execution_history 
                                 if record['status'] == ExecutionStatus.CANCELLED)
        
        # Ortalama yürütme süresi
        completed_records = [record for record in self.execution_history 
                           if record['end_time'] is not None]
        
        avg_execution_time = 0.0
        if completed_records:
            total_time = sum((record['end_time'] - record['start_time']).total_seconds() 
                           for record in completed_records)
            avg_execution_time = total_time / len(completed_records)
        
        # Toplam kar/zarar
        total_profit = sum(record['result'].get('profit', 0.0) 
                          for record in self.execution_history 
                          if record['result'])
        
        total_loss = sum(record['result'].get('loss', 0.0) 
                        for record in self.execution_history 
                        if record['result'])
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'cancelled_executions': cancelled_executions,
            'pending_executions': len(self.pending_trades),
            'success_rate': (successful_executions / total_executions * 100) if total_executions > 0 else 0.0,
            'avg_execution_time_seconds': avg_execution_time,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_pnl': total_profit - total_loss
        }