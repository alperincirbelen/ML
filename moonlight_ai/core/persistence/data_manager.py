"""
Data Manager
Veri saklama ve veritabanı yönetimi
"""

import asyncio
import logging
import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class DataManager:
    """
    Veri yöneticisi
    SQLite veritabanı ile veri saklama ve yönetimi
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_path = config.get('path', 'data/moonlight.db')
        self.backup_enabled = config.get('backup_enabled', True)
        self.backup_interval = config.get('backup_interval', 3600)  # saniye
        
        # Veritabanı bağlantısı
        self.connection: Optional[sqlite3.Connection] = None
        
        # Backup görevleri
        self._backup_task: Optional[asyncio.Task] = None
        
        logger.info(f"DataManager başlatıldı - DB: {self.db_path}")
    
    async def initialize(self) -> None:
        """Veritabanını başlat ve tabloları oluştur"""
        try:
            # Dizin oluştur
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Veritabanı bağlantısı
            self.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            
            # WAL mode (Write-Ahead Logging) - daha iyi performans
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=NORMAL")
            self.connection.execute("PRAGMA cache_size=10000")
            self.connection.execute("PRAGMA temp_store=MEMORY")
            
            # Tabloları oluştur
            await self._create_tables()
            
            # Backup görevini başlat
            if self.backup_enabled:
                self._backup_task = asyncio.create_task(self._backup_loop())
            
            logger.info("Veritabanı başarıyla başlatıldı")
            
        except Exception as e:
            logger.error(f"Veritabanı başlatma hatası: {e}")
            raise
    
    async def _create_tables(self) -> None:
        """Veritabanı tablolarını oluştur"""
        try:
            cursor = self.connection.cursor()
            
            # Market data tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    bid REAL NOT NULL,
                    ask REAL NOT NULL,
                    last_price REAL NOT NULL,
                    volume REAL NOT NULL,
                    spread REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX(symbol, timestamp)
                )
            """)
            
            # Trade signals tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    amount REAL NOT NULL,
                    expiry_time INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    strategy_name TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX(symbol, timestamp),
                    INDEX(strategy_name)
                )
            """)
            
            # Trade results tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    execution_id TEXT,
                    symbol TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    amount REAL NOT NULL,
                    profit REAL NOT NULL,
                    loss REAL NOT NULL,
                    payout_percentage REAL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME,
                    expiry_time INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX(symbol, start_time),
                    INDEX(status),
                    INDEX(success)
                )
            """)
            
            # User sessions tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    broker TEXT NOT NULL,
                    demo_account BOOLEAN NOT NULL,
                    token_hash TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    expires_at DATETIME NOT NULL,
                    last_activity DATETIME NOT NULL,
                    INDEX(user_id),
                    INDEX(email),
                    INDEX(expires_at)
                )
            """)
            
            # System logs tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    module TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT,
                    timestamp DATETIME NOT NULL,
                    INDEX(level, timestamp),
                    INDEX(module)
                )
            """)
            
            # Strategy performance tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    total_signals INTEGER NOT NULL,
                    successful_signals INTEGER NOT NULL,
                    total_profit REAL NOT NULL,
                    total_loss REAL NOT NULL,
                    win_rate REAL NOT NULL,
                    avg_confidence REAL NOT NULL,
                    date DATE NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(strategy_name, symbol, date),
                    INDEX(strategy_name, date)
                )
            """)
            
            self.connection.commit()
            logger.info("Veritabanı tabloları oluşturuldu")
            
        except Exception as e:
            logger.error(f"Tablo oluşturma hatası: {e}")
            raise
    
    async def save_market_data(self, market_data) -> None:
        """
        Piyasa verisi kaydet
        Args:
            market_data: MarketData instance
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO market_data 
                (symbol, timestamp, bid, ask, last_price, volume, spread)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                market_data.symbol,
                market_data.timestamp,
                market_data.bid,
                market_data.ask,
                market_data.last,
                market_data.volume,
                market_data.spread
            ))
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"Piyasa verisi kaydetme hatası: {e}")
    
    async def save_trade_signal(self, signal) -> None:
        """
        İşlem sinyali kaydet
        Args:
            signal: TradeSignal instance
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO trade_signals 
                (symbol, direction, amount, expiry_time, confidence, strategy_name, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.symbol,
                signal.direction,
                signal.amount,
                signal.expiry_time,
                signal.confidence,
                signal.strategy_name,
                signal.timestamp
            ))
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"İşlem sinyali kaydetme hatası: {e}")
    
    async def save_trade_result(self, result: Dict[str, Any]) -> None:
        """
        İşlem sonucu kaydet
        Args:
            result: İşlem sonucu dictionary
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO trade_results 
                (trade_id, execution_id, symbol, direction, amount, profit, loss, 
                 payout_percentage, start_time, end_time, expiry_time, status, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.get('trade_id'),
                result.get('execution_id'),
                result.get('symbol'),
                result.get('direction'),
                result.get('amount', 0.0),
                result.get('profit', 0.0),
                result.get('loss', 0.0),
                result.get('payout_percentage', 0.0),
                result.get('start_time'),
                result.get('end_time'),
                result.get('expiry_time', 0),
                result.get('status', 'unknown'),
                result.get('success', False)
            ))
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"İşlem sonucu kaydetme hatası: {e}")
    
    async def get_market_data_history(self, symbol: str, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Piyasa verisi geçmişi
        Args:
            symbol: Sembol
            hours: Kaç saatlik geçmiş
        Returns: Piyasa verisi listesi
        """
        try:
            cursor = self.connection.cursor()
            since = datetime.utcnow() - timedelta(hours=hours)
            
            cursor.execute("""
                SELECT symbol, timestamp, bid, ask, last_price, volume, spread
                FROM market_data 
                WHERE symbol = ? AND timestamp >= ?
                ORDER BY timestamp ASC
            """, (symbol, since))
            
            rows = cursor.fetchall()
            
            return [
                {
                    'symbol': row[0],
                    'timestamp': row[1],
                    'bid': row[2],
                    'ask': row[3],
                    'last_price': row[4],
                    'volume': row[5],
                    'spread': row[6]
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Piyasa verisi geçmişi alma hatası: {e}")
            return []
    
    async def get_trade_history(self, limit: int = 100, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        İşlem geçmişi
        Args:
            limit: Maksimum kayıt sayısı
            symbol: Belirli sembol (opsiyonel)
        Returns: İşlem geçmişi listesi
        """
        try:
            cursor = self.connection.cursor()
            
            if symbol:
                cursor.execute("""
                    SELECT trade_id, symbol, direction, amount, profit, loss, 
                           start_time, end_time, status, success
                    FROM trade_results 
                    WHERE symbol = ?
                    ORDER BY start_time DESC
                    LIMIT ?
                """, (symbol, limit))
            else:
                cursor.execute("""
                    SELECT trade_id, symbol, direction, amount, profit, loss, 
                           start_time, end_time, status, success
                    FROM trade_results 
                    ORDER BY start_time DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            
            return [
                {
                    'trade_id': row[0],
                    'symbol': row[1],
                    'direction': row[2],
                    'amount': row[3],
                    'profit': row[4],
                    'loss': row[5],
                    'start_time': row[6],
                    'end_time': row[7],
                    'status': row[8],
                    'success': bool(row[9])
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"İşlem geçmişi alma hatası: {e}")
            return []
    
    async def get_strategy_performance(self, strategy_name: str, days: int = 30) -> Dict[str, Any]:
        """
        Strateji performansı
        Args:
            strategy_name: Strateji adı
            days: Kaç günlük performans
        Returns: Performans metrikleri
        """
        try:
            cursor = self.connection.cursor()
            since = datetime.utcnow() - timedelta(days=days)
            
            # Toplam istatistikler
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(profit) as total_profit,
                    SUM(loss) as total_loss,
                    AVG(amount) as avg_amount
                FROM trade_results tr
                JOIN trade_signals ts ON tr.symbol = ts.symbol 
                    AND datetime(tr.start_time) = datetime(ts.timestamp)
                WHERE ts.strategy_name = ? AND tr.start_time >= ?
            """, (strategy_name, since))
            
            stats = cursor.fetchone()
            
            if not stats or stats[0] == 0:
                return {
                    'strategy_name': strategy_name,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'win_rate': 0.0,
                    'total_profit': 0.0,
                    'total_loss': 0.0,
                    'net_pnl': 0.0,
                    'avg_amount': 0.0,
                    'roi_percentage': 0.0
                }
            
            total_trades = stats[0]
            winning_trades = stats[1]
            total_profit = stats[2] or 0.0
            total_loss = stats[3] or 0.0
            avg_amount = stats[4] or 0.0
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
            net_pnl = total_profit - total_loss
            roi_percentage = (net_pnl / (avg_amount * total_trades) * 100) if (avg_amount * total_trades) > 0 else 0.0
            
            return {
                'strategy_name': strategy_name,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'total_loss': total_loss,
                'net_pnl': net_pnl,
                'avg_amount': avg_amount,
                'roi_percentage': roi_percentage
            }
            
        except Exception as e:
            logger.error(f"Strateji performansı alma hatası: {e}")
            return {}
    
    async def log_system_event(self, level: str, module: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Sistem olayı kaydet
        Args:
            level: Log seviyesi (INFO, WARNING, ERROR, etc.)
            module: Modül adı
            message: Log mesajı
            data: Ek veri (opsiyonel)
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO system_logs (level, module, message, data, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                level,
                module,
                message,
                json.dumps(data) if data else None,
                datetime.utcnow()
            ))
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"Sistem olayı kaydetme hatası: {e}")
    
    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """
        Eski verileri temizle
        Args:
            days: Kaç günden eski veriler silinecek
        Returns: Silinen kayıt sayıları
        """
        try:
            cursor = self.connection.cursor()
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Market data temizliği
            cursor.execute("DELETE FROM market_data WHERE timestamp < ?", (cutoff_date,))
            market_data_deleted = cursor.rowcount
            
            # System logs temizliği
            cursor.execute("DELETE FROM system_logs WHERE timestamp < ?", (cutoff_date,))
            logs_deleted = cursor.rowcount
            
            # Süresi dolmuş oturumları temizle
            cursor.execute("DELETE FROM user_sessions WHERE expires_at < ?", (datetime.utcnow(),))
            sessions_deleted = cursor.rowcount
            
            self.connection.commit()
            
            result = {
                'market_data_deleted': market_data_deleted,
                'logs_deleted': logs_deleted,
                'sessions_deleted': sessions_deleted
            }
            
            logger.info(f"Veri temizliği tamamlandı: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Veri temizliği hatası: {e}")
            return {}
    
    async def maintenance(self) -> None:
        """Veritabanı bakımı"""
        try:
            cursor = self.connection.cursor()
            
            # VACUUM - veritabanı optimizasyonu
            cursor.execute("VACUUM")
            
            # ANALYZE - istatistik güncelleme
            cursor.execute("ANALYZE")
            
            # Eski verileri temizle (30 günden eski)
            await self.cleanup_old_data(30)
            
            logger.info("Veritabanı bakımı tamamlandı")
            
        except Exception as e:
            logger.error(f"Veritabanı bakım hatası: {e}")
    
    async def _backup_loop(self) -> None:
        """Backup döngüsü"""
        try:
            while True:
                await asyncio.sleep(self.backup_interval)
                await self._create_backup()
        except asyncio.CancelledError:
            logger.info("Backup görevi iptal edildi")
        except Exception as e:
            logger.error(f"Backup döngüsü hatası: {e}")
    
    async def _create_backup(self) -> None:
        """Veritabanı yedeği oluştur"""
        try:
            backup_path = f"{self.db_path}.backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            # SQLite backup
            backup_conn = sqlite3.connect(backup_path)
            self.connection.backup(backup_conn)
            backup_conn.close()
            
            logger.info(f"Veritabanı yedeği oluşturuldu: {backup_path}")
            
            # Eski yedekleri temizle (7 günden eski)
            backup_dir = Path(self.db_path).parent
            cutoff_time = datetime.utcnow() - timedelta(days=7)
            
            for backup_file in backup_dir.glob(f"{Path(self.db_path).name}.backup_*"):
                if backup_file.stat().st_mtime < cutoff_time.timestamp():
                    backup_file.unlink()
                    logger.info(f"Eski yedek silindi: {backup_file}")
            
        except Exception as e:
            logger.error(f"Backup oluşturma hatası: {e}")
    
    async def close(self) -> None:
        """Veritabanı bağlantısını kapat"""
        try:
            # Backup görevini iptal et
            if self._backup_task and not self._backup_task.done():
                self._backup_task.cancel()
                try:
                    await self._backup_task
                except asyncio.CancelledError:
                    pass
            
            # Bağlantıyı kapat
            if self.connection:
                self.connection.close()
                self.connection = None
            
            logger.info("Veritabanı bağlantısı kapatıldı")
            
        except Exception as e:
            logger.error(f"Veritabanı kapatma hatası: {e}")
    
    def get_database_info(self) -> Dict[str, Any]:
        """Veritabanı bilgileri"""
        try:
            cursor = self.connection.cursor()
            
            # Tablo boyutları
            tables_info = {}
            tables = ['market_data', 'trade_signals', 'trade_results', 'user_sessions', 'system_logs']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                tables_info[table] = count
            
            # Veritabanı boyutu
            db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
            
            return {
                'database_path': self.db_path,
                'database_size_bytes': db_size,
                'database_size_mb': round(db_size / 1024 / 1024, 2),
                'tables': tables_info,
                'backup_enabled': self.backup_enabled
            }
            
        except Exception as e:
            logger.error(f"Veritabanı bilgi alma hatası: {e}")
            return {}