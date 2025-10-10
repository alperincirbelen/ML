"""
Rate Limiter
İstek sınırlama ve DDoS koruması
"""

import asyncio
import time
import logging
from typing import Dict, Optional, Any, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RateLimit:
    """Rate limit konfigürasyonu"""
    requests: int  # İzin verilen istek sayısı
    window: int    # Zaman penceresi (saniye)
    burst: int     # Burst limiti (opsiyonel)


@dataclass
class ClientInfo:
    """İstemci bilgileri"""
    ip_address: str
    user_id: Optional[str] = None
    user_agent: Optional[str] = None
    last_request: Optional[datetime] = None
    total_requests: int = 0
    blocked_until: Optional[datetime] = None


class RateLimiter:
    """
    Rate Limiter
    İstek sınırlama, DDoS koruması ve kötüye kullanım önleme
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Rate limit kuralları
        self.limits = {
            'default': RateLimit(100, 60, 10),  # 100 req/min, burst 10
            'login': RateLimit(5, 60, 2),       # 5 login/min, burst 2
            'api': RateLimit(1000, 60, 50),     # 1000 API req/min, burst 50
            'websocket': RateLimit(500, 60, 25) # 500 WS msg/min, burst 25
        }
        
        # Özel limitler (config'den)
        custom_limits = config.get('rate_limits', {})
        for name, limit_config in custom_limits.items():
            self.limits[name] = RateLimit(**limit_config)
        
        # İstemci takibi
        self.clients: Dict[str, ClientInfo] = {}
        
        # İstek geçmişi (sliding window için)
        self.request_history: Dict[str, deque] = defaultdict(deque)
        
        # Engellenen IP'ler
        self.blocked_ips: Dict[str, datetime] = {}
        
        # Whitelist ve blacklist
        self.whitelist: set = set(config.get('whitelist', []))
        self.blacklist: set = set(config.get('blacklist', []))
        
        # Temizlik görevi
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
        
        logger.info("RateLimiter başlatıldı")
    
    def _start_cleanup_task(self) -> None:
        """Temizlik görevini başlat"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # 5 dakikada bir
                    await self._cleanup_old_data()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Cleanup görevi hatası: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def _cleanup_old_data(self) -> None:
        """Eski verileri temizle"""
        try:
            now = datetime.utcnow()
            cleanup_count = 0
            
            # Eski istek geçmişlerini temizle
            for client_id, history in list(self.request_history.items()):
                # 1 saatten eski kayıtları kaldır
                cutoff = now - timedelta(hours=1)
                while history and history[0] < cutoff.timestamp():
                    history.popleft()
                
                if not history:
                    del self.request_history[client_id]
                    cleanup_count += 1
            
            # Süresi dolmuş blokları kaldır
            expired_blocks = []
            for ip, block_until in self.blocked_ips.items():
                if now > block_until:
                    expired_blocks.append(ip)
            
            for ip in expired_blocks:
                del self.blocked_ips[ip]
                cleanup_count += len(expired_blocks)
            
            if cleanup_count > 0:
                logger.info(f"Rate limiter temizlik: {cleanup_count} kayıt silindi")
                
        except Exception as e:
            logger.error(f"Rate limiter temizlik hatası: {e}")
    
    async def check_rate_limit(self, 
                             client_id: str, 
                             limit_type: str = 'default',
                             ip_address: Optional[str] = None,
                             user_id: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Rate limit kontrolü
        Args:
            client_id: İstemci kimliği
            limit_type: Limit türü
            ip_address: IP adresi
            user_id: Kullanıcı ID'si
        Returns: (izin_verildi, bilgi)
        """
        try:
            now = datetime.utcnow()
            
            # IP blacklist kontrolü
            if ip_address and ip_address in self.blacklist:
                logger.warning(f"Blacklist IP erişim denemesi: {ip_address}")
                return False, {
                    'error': 'IP blacklisted',
                    'retry_after': None,
                    'blocked': True
                }
            
            # IP whitelist kontrolü
            if ip_address and ip_address in self.whitelist:
                return True, {
                    'allowed': True,
                    'whitelist': True,
                    'remaining': float('inf')
                }
            
            # Geçici blok kontrolü
            if ip_address and ip_address in self.blocked_ips:
                block_until = self.blocked_ips[ip_address]
                if now < block_until:
                    retry_after = int((block_until - now).total_seconds())
                    return False, {
                        'error': 'Temporarily blocked',
                        'retry_after': retry_after,
                        'blocked_until': block_until.isoformat()
                    }
                else:
                    # Blok süresi dolmuş
                    del self.blocked_ips[ip_address]
            
            # Rate limit kuralını al
            if limit_type not in self.limits:
                limit_type = 'default'
            
            rate_limit = self.limits[limit_type]
            
            # İstemci bilgilerini güncelle
            if client_id not in self.clients:
                self.clients[client_id] = ClientInfo(
                    ip_address=ip_address or 'unknown',
                    user_id=user_id
                )
            
            client = self.clients[client_id]
            client.last_request = now
            client.total_requests += 1
            
            # İstek geçmişini güncelle
            history = self.request_history[client_id]
            current_time = now.timestamp()
            history.append(current_time)
            
            # Zaman penceresini temizle
            window_start = current_time - rate_limit.window
            while history and history[0] < window_start:
                history.popleft()
            
            # Rate limit kontrolü
            request_count = len(history)
            
            if request_count > rate_limit.requests:
                # Limit aşıldı
                logger.warning(f"Rate limit aşıldı: {client_id} ({limit_type}) - "
                             f"{request_count}/{rate_limit.requests}")
                
                # Geçici blok uygula (IP varsa)
                if ip_address:
                    block_duration = self._calculate_block_duration(ip_address, limit_type)
                    self.blocked_ips[ip_address] = now + timedelta(seconds=block_duration)
                    
                    logger.warning(f"IP geçici olarak bloklandı: {ip_address} "
                                 f"({block_duration} saniye)")
                
                return False, {
                    'error': 'Rate limit exceeded',
                    'limit': rate_limit.requests,
                    'window': rate_limit.window,
                    'current': request_count,
                    'retry_after': rate_limit.window,
                    'reset_time': (now + timedelta(seconds=rate_limit.window)).isoformat()
                }
            
            # İzin verildi
            remaining = rate_limit.requests - request_count
            reset_time = now + timedelta(seconds=rate_limit.window)
            
            return True, {
                'allowed': True,
                'limit': rate_limit.requests,
                'remaining': remaining,
                'window': rate_limit.window,
                'reset_time': reset_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Rate limit kontrolü hatası: {e}")
            # Hata durumunda izin ver (fail-open)
            return True, {'error': f'Rate limiter error: {str(e)}'}
    
    def _calculate_block_duration(self, ip_address: str, limit_type: str) -> int:
        """
        Blok süresini hesapla (progressive blocking)
        Args:
            ip_address: IP adresi
            limit_type: Limit türü
        Returns: Blok süresi (saniye)
        """
        try:
            # Temel blok süreleri
            base_durations = {
                'login': 300,    # 5 dakika
                'api': 60,       # 1 dakika
                'default': 120   # 2 dakika
            }
            
            base_duration = base_durations.get(limit_type, 120)
            
            # Progressive blocking - önceki blokları say
            block_count = 0
            for blocked_ip, _ in self.blocked_ips.items():
                if blocked_ip == ip_address:
                    block_count += 1
            
            # Her blokta süreyi artır
            multiplier = min(2 ** block_count, 16)  # Maksimum 16x
            
            return base_duration * multiplier
            
        except Exception as e:
            logger.error(f"Blok süresi hesaplama hatası: {e}")
            return 300  # Varsayılan 5 dakika
    
    async def add_to_whitelist(self, ip_address: str) -> None:
        """IP'yi whitelist'e ekle"""
        try:
            self.whitelist.add(ip_address)
            # Eğer blacklist'te varsa kaldır
            self.blacklist.discard(ip_address)
            # Eğer bloklu ise kaldır
            self.blocked_ips.pop(ip_address, None)
            
            logger.info(f"IP whitelist'e eklendi: {ip_address}")
            
        except Exception as e:
            logger.error(f"Whitelist ekleme hatası: {e}")
    
    async def add_to_blacklist(self, ip_address: str) -> None:
        """IP'yi blacklist'e ekle"""
        try:
            self.blacklist.add(ip_address)
            # Eğer whitelist'te varsa kaldır
            self.whitelist.discard(ip_address)
            
            logger.info(f"IP blacklist'e eklendi: {ip_address}")
            
        except Exception as e:
            logger.error(f"Blacklist ekleme hatası: {e}")
    
    async def unblock_ip(self, ip_address: str) -> bool:
        """IP bloğunu kaldır"""
        try:
            if ip_address in self.blocked_ips:
                del self.blocked_ips[ip_address]
                logger.info(f"IP bloğu kaldırıldı: {ip_address}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"IP blok kaldırma hatası: {e}")
            return False
    
    def get_client_stats(self, client_id: str) -> Optional[Dict[str, Any]]:
        """İstemci istatistikleri"""
        try:
            if client_id not in self.clients:
                return None
            
            client = self.clients[client_id]
            history = self.request_history.get(client_id, deque())
            
            now = datetime.utcnow()
            
            # Son 1 saatteki istekler
            hour_ago = (now - timedelta(hours=1)).timestamp()
            recent_requests = sum(1 for req_time in history if req_time > hour_ago)
            
            return {
                'client_id': client_id,
                'ip_address': client.ip_address,
                'user_id': client.user_id,
                'total_requests': client.total_requests,
                'recent_requests_1h': recent_requests,
                'last_request': client.last_request.isoformat() if client.last_request else None,
                'is_blocked': client.ip_address in self.blocked_ips,
                'is_whitelisted': client.ip_address in self.whitelist,
                'is_blacklisted': client.ip_address in self.blacklist
            }
            
        except Exception as e:
            logger.error(f"İstemci istatistikleri hatası: {e}")
            return None
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Sistem istatistikleri"""
        try:
            now = datetime.utcnow()
            
            # Aktif istemciler (son 1 saatte istek yapan)
            hour_ago = now - timedelta(hours=1)
            active_clients = sum(1 for client in self.clients.values() 
                               if client.last_request and client.last_request > hour_ago)
            
            # Toplam istekler (son 1 saat)
            total_requests_1h = sum(
                sum(1 for req_time in history 
                    if req_time > (now - timedelta(hours=1)).timestamp())
                for history in self.request_history.values()
            )
            
            return {
                'total_clients': len(self.clients),
                'active_clients_1h': active_clients,
                'total_requests_1h': total_requests_1h,
                'blocked_ips': len(self.blocked_ips),
                'whitelisted_ips': len(self.whitelist),
                'blacklisted_ips': len(self.blacklist),
                'rate_limits': {
                    name: {
                        'requests': limit.requests,
                        'window': limit.window,
                        'burst': limit.burst
                    }
                    for name, limit in self.limits.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Sistem istatistikleri hatası: {e}")
            return {}
    
    async def shutdown(self) -> None:
        """Rate limiter'ı kapat"""
        try:
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("RateLimiter kapatıldı")
            
        except Exception as e:
            logger.error(f"RateLimiter kapatma hatası: {e}")