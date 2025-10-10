"""
Token Manager
JWT token yönetimi ve güvenlik
"""

import jwt
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import secrets
import hashlib

logger = logging.getLogger(__name__)


class TokenManager:
    """
    JWT Token Yöneticisi
    Token oluşturma, doğrulama ve yönetimi
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.secret_key = config.get('jwt_secret_key', 'default-secret')
        self.algorithm = config.get('jwt_algorithm', 'HS256')
        self.access_token_expire = config.get('access_token_expire', 3600)  # 1 saat
        self.refresh_token_expire = config.get('refresh_token_expire', 86400 * 7)  # 7 gün
        
        # Token blacklist (iptal edilmiş tokenlar)
        self.blacklisted_tokens: set = set()
        
        # Refresh token store
        self.refresh_tokens: Dict[str, Dict[str, Any]] = {}
        
        logger.info("TokenManager başlatıldı")
    
    def generate_access_token(self, user_data: Dict[str, Any]) -> str:
        """
        Access token oluştur
        Args:
            user_data: Kullanıcı bilgileri
        Returns: JWT access token
        """
        try:
            now = datetime.utcnow()
            payload = {
                'user_id': user_data.get('user_id'),
                'email': user_data.get('email'),
                'broker': user_data.get('broker'),
                'demo_account': user_data.get('demo_account', True),
                'token_type': 'access',
                'iat': int(now.timestamp()),
                'exp': int((now + timedelta(seconds=self.access_token_expire)).timestamp()),
                'jti': secrets.token_urlsafe(16)  # JWT ID
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Access token oluşturuldu: {user_data.get('email')}")
            return token
            
        except Exception as e:
            logger.error(f"Access token oluşturma hatası: {e}")
            raise
    
    def generate_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """
        Refresh token oluştur
        Args:
            user_data: Kullanıcı bilgileri
        Returns: JWT refresh token
        """
        try:
            now = datetime.utcnow()
            jti = secrets.token_urlsafe(32)
            
            payload = {
                'user_id': user_data.get('user_id'),
                'email': user_data.get('email'),
                'token_type': 'refresh',
                'iat': int(now.timestamp()),
                'exp': int((now + timedelta(seconds=self.refresh_token_expire)).timestamp()),
                'jti': jti
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # Refresh token'ı sakla
            self.refresh_tokens[jti] = {
                'user_id': user_data.get('user_id'),
                'email': user_data.get('email'),
                'created_at': now,
                'expires_at': now + timedelta(seconds=self.refresh_token_expire),
                'used': False
            }
            
            logger.info(f"Refresh token oluşturuldu: {user_data.get('email')}")
            return token
            
        except Exception as e:
            logger.error(f"Refresh token oluşturma hatası: {e}")
            raise
    
    def generate_token_pair(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Access ve refresh token çifti oluştur
        Args:
            user_data: Kullanıcı bilgileri
        Returns: Token çifti
        """
        try:
            access_token = self.generate_access_token(user_data)
            refresh_token = self.generate_refresh_token(user_data)
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': self.access_token_expire
            }
            
        except Exception as e:
            logger.error(f"Token çifti oluşturma hatası: {e}")
            raise
    
    def validate_token(self, token: str, token_type: str = 'access') -> Optional[Dict[str, Any]]:
        """
        Token doğrulama
        Args:
            token: JWT token
            token_type: Token türü ('access' veya 'refresh')
        Returns: Token payload'ı veya None
        """
        try:
            # Blacklist kontrolü
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            if token_hash in self.blacklisted_tokens:
                logger.warning("Blacklist'te token kullanılmaya çalışıldı")
                return None
            
            # Token decode
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Token türü kontrolü
            if payload.get('token_type') != token_type:
                logger.warning(f"Yanlış token türü: {payload.get('token_type')} != {token_type}")
                return None
            
            # Refresh token için ek kontroller
            if token_type == 'refresh':
                jti = payload.get('jti')
                if jti not in self.refresh_tokens:
                    logger.warning("Refresh token bulunamadı")
                    return None
                
                refresh_data = self.refresh_tokens[jti]
                if refresh_data['used']:
                    logger.warning("Kullanılmış refresh token")
                    return None
                
                if datetime.utcnow() > refresh_data['expires_at']:
                    logger.warning("Süresi dolmuş refresh token")
                    return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token süresi dolmuş")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Geçersiz token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token doğrulama hatası: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Access token yenileme
        Args:
            refresh_token: Refresh token
        Returns: Yeni token çifti veya None
        """
        try:
            # Refresh token'ı doğrula
            payload = self.validate_token(refresh_token, 'refresh')
            if not payload:
                return None
            
            jti = payload.get('jti')
            
            # Refresh token'ı kullanıldı olarak işaretle
            if jti in self.refresh_tokens:
                self.refresh_tokens[jti]['used'] = True
            
            # Yeni token çifti oluştur
            user_data = {
                'user_id': payload.get('user_id'),
                'email': payload.get('email'),
                'broker': payload.get('broker'),
                'demo_account': payload.get('demo_account')
            }
            
            new_tokens = self.generate_token_pair(user_data)
            logger.info(f"Token yenilendi: {user_data['email']}")
            
            return new_tokens
            
        except Exception as e:
            logger.error(f"Token yenileme hatası: {e}")
            return None
    
    def revoke_token(self, token: str) -> bool:
        """
        Token iptal etme (blacklist'e ekleme)
        Args:
            token: İptal edilecek token
        Returns: İptal başarılı ise True
        """
        try:
            # Token'ı decode et (doğrulama için)
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Token hash'ini blacklist'e ekle
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            self.blacklisted_tokens.add(token_hash)
            
            # Refresh token ise store'dan kaldır
            if payload.get('token_type') == 'refresh':
                jti = payload.get('jti')
                if jti in self.refresh_tokens:
                    del self.refresh_tokens[jti]
            
            logger.info(f"Token iptal edildi: {payload.get('email')}")
            return True
            
        except Exception as e:
            logger.error(f"Token iptal etme hatası: {e}")
            return False
    
    def revoke_all_user_tokens(self, user_id: str) -> int:
        """
        Kullanıcının tüm tokenlarını iptal et
        Args:
            user_id: Kullanıcı ID'si
        Returns: İptal edilen token sayısı
        """
        try:
            revoked_count = 0
            
            # Refresh tokenları kontrol et ve iptal et
            to_remove = []
            for jti, refresh_data in self.refresh_tokens.items():
                if refresh_data['user_id'] == user_id:
                    to_remove.append(jti)
                    revoked_count += 1
            
            for jti in to_remove:
                del self.refresh_tokens[jti]
            
            logger.info(f"Kullanıcının {revoked_count} token'ı iptal edildi: {user_id}")
            return revoked_count
            
        except Exception as e:
            logger.error(f"Kullanıcı tokenları iptal etme hatası: {e}")
            return 0
    
    def cleanup_expired_tokens(self) -> int:
        """
        Süresi dolmuş tokenları temizle
        Returns: Temizlenen token sayısı
        """
        try:
            now = datetime.utcnow()
            expired_count = 0
            
            # Süresi dolmuş refresh tokenları kaldır
            to_remove = []
            for jti, refresh_data in self.refresh_tokens.items():
                if now > refresh_data['expires_at']:
                    to_remove.append(jti)
                    expired_count += 1
            
            for jti in to_remove:
                del self.refresh_tokens[jti]
            
            if expired_count > 0:
                logger.info(f"{expired_count} süresi dolmuş token temizlendi")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Token temizleme hatası: {e}")
            return 0
    
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Token bilgilerini al
        Args:
            token: JWT token
        Returns: Token bilgileri
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            return {
                'user_id': payload.get('user_id'),
                'email': payload.get('email'),
                'broker': payload.get('broker'),
                'demo_account': payload.get('demo_account'),
                'token_type': payload.get('token_type'),
                'issued_at': datetime.fromtimestamp(payload.get('iat')),
                'expires_at': datetime.fromtimestamp(payload.get('exp')),
                'jti': payload.get('jti'),
                'is_expired': datetime.utcnow() > datetime.fromtimestamp(payload.get('exp'))
            }
            
        except Exception as e:
            logger.error(f"Token bilgi alma hatası: {e}")
            return None
    
    def generate_api_token(self, user_data: Dict[str, Any], scopes: List[str] = None) -> str:
        """
        API token oluştur (uzun süreli)
        Args:
            user_data: Kullanıcı bilgileri
            scopes: API yetkileri
        Returns: API token
        """
        try:
            if scopes is None:
                scopes = ['read', 'trade']
            
            now = datetime.utcnow()
            payload = {
                'user_id': user_data.get('user_id'),
                'email': user_data.get('email'),
                'broker': user_data.get('broker'),
                'token_type': 'api',
                'scopes': scopes,
                'iat': int(now.timestamp()),
                'exp': int((now + timedelta(days=365)).timestamp()),  # 1 yıl
                'jti': secrets.token_urlsafe(32)
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.info(f"API token oluşturuldu: {user_data.get('email')}")
            return token
            
        except Exception as e:
            logger.error(f"API token oluşturma hatası: {e}")
            raise
    
    def validate_api_token(self, token: str, required_scope: str = None) -> Optional[Dict[str, Any]]:
        """
        API token doğrulama
        Args:
            token: API token
            required_scope: Gerekli yetki
        Returns: Token payload'ı veya None
        """
        try:
            payload = self.validate_token(token, 'api')
            if not payload:
                return None
            
            # Scope kontrolü
            if required_scope:
                scopes = payload.get('scopes', [])
                if required_scope not in scopes and 'admin' not in scopes:
                    logger.warning(f"Yetersiz yetki: {required_scope} not in {scopes}")
                    return None
            
            return payload
            
        except Exception as e:
            logger.error(f"API token doğrulama hatası: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Token istatistikleri"""
        try:
            now = datetime.utcnow()
            
            # Aktif refresh tokenlar
            active_refresh = sum(1 for data in self.refresh_tokens.values() 
                               if not data['used'] and now <= data['expires_at'])
            
            # Süresi dolmuş refresh tokenlar
            expired_refresh = sum(1 for data in self.refresh_tokens.values() 
                                if now > data['expires_at'])
            
            return {
                'total_refresh_tokens': len(self.refresh_tokens),
                'active_refresh_tokens': active_refresh,
                'expired_refresh_tokens': expired_refresh,
                'blacklisted_tokens': len(self.blacklisted_tokens),
                'access_token_expire_seconds': self.access_token_expire,
                'refresh_token_expire_seconds': self.refresh_token_expire,
                'algorithm': self.algorithm
            }
            
        except Exception as e:
            logger.error(f"Token istatistikleri hatası: {e}")
            return {}