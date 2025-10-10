"""
Authentication Manager
Kimlik doğrulama ve oturum yönetimi
"""

import asyncio
import hashlib
import logging
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

import bcrypt
import jwt
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


@dataclass
class UserCredentials:
    """Kullanıcı kimlik bilgileri"""
    email: str
    password: str
    broker: str
    demo_account: bool = True
    
    def __post_init__(self):
        """Veri doğrulama"""
        if not self.email or '@' not in self.email:
            raise ValueError("Geçerli bir e-posta adresi gerekli")
        if not self.password or len(self.password) < 6:
            raise ValueError("Şifre en az 6 karakter olmalı")
        if not self.broker:
            raise ValueError("Broker bilgisi gerekli")


@dataclass
class AuthSession:
    """Kimlik doğrulama oturumu"""
    user_id: str
    email: str
    broker: str
    demo_account: bool
    token: str
    expires_at: datetime
    created_at: datetime
    last_activity: datetime
    
    @property
    def is_expired(self) -> bool:
        """Oturum süresi dolmuş mu?"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def time_remaining(self) -> int:
        """Kalan süre (saniye)"""
        if self.is_expired:
            return 0
        return int((self.expires_at - datetime.utcnow()).total_seconds())


class AuthManager:
    """
    Kimlik doğrulama yöneticisi
    Kullanıcı oturumları, şifreleme ve token yönetimi
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.secret_key = config.get('jwt_secret_key', 'default-secret')
        self.algorithm = config.get('jwt_algorithm', 'HS256')
        self.token_expiry = config.get('jwt_expiration', 3600)  # 1 saat
        self.max_attempts = config.get('max_login_attempts', 5)
        self.lockout_duration = config.get('lockout_duration', 300)  # 5 dakika
        
        # Şifreleme anahtarı
        encryption_key = config.get('encryption_key')
        if encryption_key:
            self.cipher = Fernet(encryption_key.encode()[:44].ljust(44, b'='))
        else:
            self.cipher = Fernet(Fernet.generate_key())
        
        # Aktif oturumlar
        self.active_sessions: Dict[str, AuthSession] = {}
        
        # Başarısız giriş denemeleri
        self.failed_attempts: Dict[str, Dict[str, Any]] = {}
        
        logger.info("AuthManager başlatıldı")
    
    async def authenticate(self, credentials: UserCredentials) -> Optional[AuthSession]:
        """
        Kullanıcı kimlik doğrulama
        Args:
            credentials: Kullanıcı kimlik bilgileri
        Returns: Başarılı ise AuthSession, aksi halde None
        """
        try:
            # Rate limiting kontrolü
            if self._is_locked_out(credentials.email):
                logger.warning(f"Hesap kilitli: {credentials.email}")
                return None
            
            # Kimlik bilgilerini doğrula
            if not await self._verify_credentials(credentials):
                self._record_failed_attempt(credentials.email)
                return None
            
            # Başarılı giriş - başarısız denemeleri temizle
            self._clear_failed_attempts(credentials.email)
            
            # Yeni oturum oluştur
            session = await self._create_session(credentials)
            
            # Aktif oturumlar listesine ekle
            self.active_sessions[session.token] = session
            
            logger.info(f"Başarılı kimlik doğrulama: {credentials.email}")
            return session
            
        except Exception as e:
            logger.error(f"Kimlik doğrulama hatası: {e}")
            return None
    
    async def validate_token(self, token: str) -> Optional[AuthSession]:
        """
        Token doğrulama
        Args:
            token: JWT token
        Returns: Geçerli ise AuthSession, aksi halde None
        """
        try:
            # Aktif oturumlardan kontrol et
            if token in self.active_sessions:
                session = self.active_sessions[token]
                
                # Süre kontrolü
                if session.is_expired:
                    await self.logout(token)
                    return None
                
                # Son aktivite zamanını güncelle
                session.last_activity = datetime.utcnow()
                return session
            
            # JWT token'ı doğrula
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Token bilgilerinden oturum oluştur
            session = AuthSession(
                user_id=payload['user_id'],
                email=payload['email'],
                broker=payload['broker'],
                demo_account=payload['demo_account'],
                token=token,
                expires_at=datetime.fromtimestamp(payload['exp']),
                created_at=datetime.fromtimestamp(payload['iat']),
                last_activity=datetime.utcnow()
            )
            
            if session.is_expired:
                return None
            
            # Aktif oturumlar listesine ekle
            self.active_sessions[token] = session
            return session
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token süresi dolmuş")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Geçersiz token")
            return None
        except Exception as e:
            logger.error(f"Token doğrulama hatası: {e}")
            return None
    
    async def logout(self, token: str) -> bool:
        """
        Oturum kapatma
        Args:
            token: JWT token
        Returns: Başarılı ise True
        """
        try:
            if token in self.active_sessions:
                session = self.active_sessions[token]
                del self.active_sessions[token]
                logger.info(f"Oturum kapatıldı: {session.email}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Oturum kapatma hatası: {e}")
            return False
    
    async def refresh_token(self, token: str) -> Optional[str]:
        """
        Token yenileme
        Args:
            token: Mevcut token
        Returns: Yeni token veya None
        """
        try:
            session = await self.validate_token(token)
            if not session:
                return None
            
            # Yeni token oluştur
            new_token = self._generate_token(session.user_id, session.email, 
                                           session.broker, session.demo_account)
            
            # Eski oturumu kaldır, yenisini ekle
            del self.active_sessions[token]
            session.token = new_token
            session.expires_at = datetime.utcnow() + timedelta(seconds=self.token_expiry)
            self.active_sessions[new_token] = session
            
            logger.info(f"Token yenilendi: {session.email}")
            return new_token
            
        except Exception as e:
            logger.error(f"Token yenileme hatası: {e}")
            return None
    
    def encrypt_data(self, data: str) -> str:
        """
        Veri şifreleme
        Args:
            data: Şifrelenecek veri
        Returns: Şifrelenmiş veri (base64)
        """
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Şifreleme hatası: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Veri şifre çözme
        Args:
            encrypted_data: Şifrelenmiş veri (base64)
        Returns: Çözülmüş veri
        """
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Şifre çözme hatası: {e}")
            raise
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Aktif oturumlar listesi"""
        sessions = {}
        for token, session in self.active_sessions.items():
            sessions[token] = {
                'email': session.email,
                'broker': session.broker,
                'demo_account': session.demo_account,
                'expires_at': session.expires_at.isoformat(),
                'last_activity': session.last_activity.isoformat(),
                'time_remaining': session.time_remaining
            }
        return sessions
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Süresi dolmuş oturumları temizle
        Returns: Temizlenen oturum sayısı
        """
        expired_tokens = []
        for token, session in self.active_sessions.items():
            if session.is_expired:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            del self.active_sessions[token]
        
        if expired_tokens:
            logger.info(f"{len(expired_tokens)} süresi dolmuş oturum temizlendi")
        
        return len(expired_tokens)
    
    async def _verify_credentials(self, credentials: UserCredentials) -> bool:
        """
        Kimlik bilgilerini doğrula
        Gerçek uygulamada broker API'si ile doğrulanacak
        """
        # Demo amaçlı basit doğrulama
        # Gerçek uygulamada broker API'si kullanılacak
        
        # Temel format kontrolü
        if not credentials.email or not credentials.password:
            return False
        
        # Şimdilik tüm geçerli format bilgilerini kabul et
        # TODO: Gerçek broker API entegrasyonu
        await asyncio.sleep(0.1)  # API çağrısı simülasyonu
        return True
    
    async def _create_session(self, credentials: UserCredentials) -> AuthSession:
        """Yeni oturum oluştur"""
        user_id = hashlib.md5(credentials.email.encode()).hexdigest()
        token = self._generate_token(user_id, credentials.email, 
                                   credentials.broker, credentials.demo_account)
        
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.token_expiry)
        
        return AuthSession(
            user_id=user_id,
            email=credentials.email,
            broker=credentials.broker,
            demo_account=credentials.demo_account,
            token=token,
            expires_at=expires_at,
            created_at=now,
            last_activity=now
        )
    
    def _generate_token(self, user_id: str, email: str, broker: str, demo_account: bool) -> str:
        """JWT token oluştur"""
        now = datetime.utcnow()
        payload = {
            'user_id': user_id,
            'email': email,
            'broker': broker,
            'demo_account': demo_account,
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(seconds=self.token_expiry)).timestamp())
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def _is_locked_out(self, email: str) -> bool:
        """Hesap kilitli mi kontrol et"""
        if email not in self.failed_attempts:
            return False
        
        attempts = self.failed_attempts[email]
        if attempts['count'] >= self.max_attempts:
            # Kilitleme süresi doldu mu?
            if time.time() - attempts['last_attempt'] > self.lockout_duration:
                # Kilidi kaldır
                del self.failed_attempts[email]
                return False
            return True
        
        return False
    
    def _record_failed_attempt(self, email: str) -> None:
        """Başarısız deneme kaydet"""
        now = time.time()
        if email in self.failed_attempts:
            self.failed_attempts[email]['count'] += 1
            self.failed_attempts[email]['last_attempt'] = now
        else:
            self.failed_attempts[email] = {
                'count': 1,
                'last_attempt': now
            }
        
        logger.warning(f"Başarısız giriş denemesi: {email} "
                      f"({self.failed_attempts[email]['count']}/{self.max_attempts})")
    
    def _clear_failed_attempts(self, email: str) -> None:
        """Başarısız denemeleri temizle"""
        if email in self.failed_attempts:
            del self.failed_attempts[email]