"""
Encryption Manager
Gelişmiş şifreleme ve güvenlik yönetimi
"""

import os
import hashlib
import secrets
import logging
from typing import Dict, Optional, Any, Union
from datetime import datetime, timedelta
import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import bcrypt

logger = logging.getLogger(__name__)


class EncryptionManager:
    """
    Gelişmiş şifreleme yöneticisi
    Symmetric ve asymmetric şifreleme, password hashing, secure storage
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Master key (environment variable'dan alınmalı)
        self.master_key = self._get_or_create_master_key()
        
        # Fernet instance (symmetric encryption)
        self.fernet = Fernet(self.master_key)
        
        # RSA key pair (asymmetric encryption)
        self.private_key = None
        self.public_key = None
        self._generate_rsa_keys()
        
        # Salt for password hashing
        self.password_salt = self._get_or_create_salt()
        
        logger.info("EncryptionManager başlatıldı")
    
    def _get_or_create_master_key(self) -> bytes:
        """Master key'i al veya oluştur"""
        try:
            # Environment variable'dan al
            env_key = os.environ.get('MOONLIGHT_MASTER_KEY')
            if env_key:
                return base64.urlsafe_b64decode(env_key.encode())
            
            # Config'den al
            config_key = self.config.get('master_key')
            if config_key:
                return base64.urlsafe_b64decode(config_key.encode())
            
            # Yeni key oluştur
            key = Fernet.generate_key()
            logger.warning("Yeni master key oluşturuldu - güvenli bir yerde saklayın!")
            logger.warning(f"MOONLIGHT_MASTER_KEY={key.decode()}")
            return key
            
        except Exception as e:
            logger.error(f"Master key hatası: {e}")
            # Fallback - yeni key oluştur
            return Fernet.generate_key()
    
    def _get_or_create_salt(self) -> bytes:
        """Password salt'ı al veya oluştur"""
        try:
            salt_file = "data/.salt"
            
            if os.path.exists(salt_file):
                with open(salt_file, 'rb') as f:
                    return f.read()
            else:
                # Yeni salt oluştur
                salt = os.urandom(32)
                os.makedirs("data", exist_ok=True)
                with open(salt_file, 'wb') as f:
                    f.write(salt)
                logger.info("Yeni password salt oluşturuldu")
                return salt
                
        except Exception as e:
            logger.error(f"Salt oluşturma hatası: {e}")
            return os.urandom(32)
    
    def _generate_rsa_keys(self) -> None:
        """RSA key pair oluştur"""
        try:
            # Private key oluştur
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # Public key'i al
            self.public_key = self.private_key.public_key()
            
            logger.info("RSA key pair oluşturuldu")
            
        except Exception as e:
            logger.error(f"RSA key oluşturma hatası: {e}")
    
    def encrypt_symmetric(self, data: Union[str, bytes]) -> str:
        """
        Symmetric encryption (Fernet)
        Args:
            data: Şifrelenecek veri
        Returns: Base64 encoded şifrelenmiş veri
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted = self.fernet.encrypt(data)
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Symmetric encryption hatası: {e}")
            raise
    
    def decrypt_symmetric(self, encrypted_data: str) -> str:
        """
        Symmetric decryption (Fernet)
        Args:
            encrypted_data: Base64 encoded şifrelenmiş veri
        Returns: Çözülmüş veri
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Symmetric decryption hatası: {e}")
            raise
    
    def encrypt_asymmetric(self, data: Union[str, bytes]) -> str:
        """
        Asymmetric encryption (RSA)
        Args:
            data: Şifrelenecek veri
        Returns: Base64 encoded şifrelenmiş veri
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted = self.public_key.encrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return base64.urlsafe_b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Asymmetric encryption hatası: {e}")
            raise
    
    def decrypt_asymmetric(self, encrypted_data: str) -> str:
        """
        Asymmetric decryption (RSA)
        Args:
            encrypted_data: Base64 encoded şifrelenmiş veri
        Returns: Çözülmüş veri
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            
            decrypted = self.private_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Asymmetric decryption hatası: {e}")
            raise
    
    def hash_password(self, password: str) -> str:
        """
        Password hash'leme (bcrypt)
        Args:
            password: Ham şifre
        Returns: Hash'lenmiş şifre
        """
        try:
            # bcrypt ile hash'le
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            return hashed.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Password hashing hatası: {e}")
            raise
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Password doğrulama
        Args:
            password: Ham şifre
            hashed: Hash'lenmiş şifre
        Returns: Doğrulama sonucu
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Password verification hatası: {e}")
            return False
    
    def derive_key_from_password(self, password: str, salt: Optional[bytes] = None) -> bytes:
        """
        Password'dan key türet (PBKDF2)
        Args:
            password: Şifre
            salt: Salt (opsiyonel)
        Returns: Türetilmiş key
        """
        try:
            if salt is None:
                salt = self.password_salt
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            
            return kdf.derive(password.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Key derivation hatası: {e}")
            raise
    
    def encrypt_file(self, file_path: str, output_path: Optional[str] = None) -> str:
        """
        Dosya şifreleme
        Args:
            file_path: Şifrelenecek dosya
            output_path: Çıktı dosyası (opsiyonel)
        Returns: Şifrelenmiş dosya yolu
        """
        try:
            if output_path is None:
                output_path = f"{file_path}.encrypted"
            
            # Dosyayı oku
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Şifrele
            encrypted = self.fernet.encrypt(data)
            
            # Şifrelenmiş dosyayı yaz
            with open(output_path, 'wb') as f:
                f.write(encrypted)
            
            logger.info(f"Dosya şifrelendi: {file_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Dosya şifreleme hatası: {e}")
            raise
    
    def decrypt_file(self, encrypted_file_path: str, output_path: Optional[str] = None) -> str:
        """
        Dosya şifre çözme
        Args:
            encrypted_file_path: Şifrelenmiş dosya
            output_path: Çıktı dosyası (opsiyonel)
        Returns: Çözülmüş dosya yolu
        """
        try:
            if output_path is None:
                output_path = encrypted_file_path.replace('.encrypted', '')
            
            # Şifrelenmiş dosyayı oku
            with open(encrypted_file_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Şifreyi çöz
            decrypted = self.fernet.decrypt(encrypted_data)
            
            # Çözülmüş dosyayı yaz
            with open(output_path, 'wb') as f:
                f.write(decrypted)
            
            logger.info(f"Dosya şifresi çözüldü: {encrypted_file_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Dosya şifre çözme hatası: {e}")
            raise
    
    def generate_secure_token(self, length: int = 32) -> str:
        """
        Güvenli token oluştur
        Args:
            length: Token uzunluğu
        Returns: Güvenli token
        """
        try:
            return secrets.token_urlsafe(length)
        except Exception as e:
            logger.error(f"Token oluşturma hatası: {e}")
            raise
    
    def generate_api_key(self) -> Dict[str, str]:
        """
        API key çifti oluştur
        Returns: API key ve secret
        """
        try:
            api_key = f"mk_{secrets.token_urlsafe(16)}"
            api_secret = secrets.token_urlsafe(32)
            
            return {
                'api_key': api_key,
                'api_secret': api_secret,
                'created_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"API key oluşturma hatası: {e}")
            raise
    
    def sign_data(self, data: Union[str, bytes]) -> str:
        """
        Veri imzalama (RSA)
        Args:
            data: İmzalanacak veri
        Returns: Base64 encoded imza
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            signature = self.private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return base64.urlsafe_b64encode(signature).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Veri imzalama hatası: {e}")
            raise
    
    def verify_signature(self, data: Union[str, bytes], signature: str) -> bool:
        """
        İmza doğrulama
        Args:
            data: Orijinal veri
            signature: Base64 encoded imza
        Returns: Doğrulama sonucu
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            signature_bytes = base64.urlsafe_b64decode(signature.encode('utf-8'))
            
            self.public_key.verify(
                signature_bytes,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except Exception as e:
            logger.error(f"İmza doğrulama hatası: {e}")
            return False
    
    def secure_delete(self, file_path: str, passes: int = 3) -> bool:
        """
        Güvenli dosya silme (overwrite)
        Args:
            file_path: Silinecek dosya
            passes: Üzerine yazma sayısı
        Returns: Silme başarılı ise True
        """
        try:
            if not os.path.exists(file_path):
                return True
            
            file_size = os.path.getsize(file_path)
            
            with open(file_path, 'r+b') as f:
                for _ in range(passes):
                    # Rastgele veri ile üzerine yaz
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # Dosyayı sil
            os.remove(file_path)
            logger.info(f"Dosya güvenli silindi: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Güvenli silme hatası: {e}")
            return False
    
    def get_public_key_pem(self) -> str:
        """Public key'i PEM formatında al"""
        try:
            pem = self.public_key.public_key_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            return pem.decode('utf-8')
        except Exception as e:
            logger.error(f"Public key PEM hatası: {e}")
            raise
    
    def export_keys(self, password: str) -> Dict[str, str]:
        """
        Key'leri export et (şifrelenmiş)
        Args:
            password: Export şifresi
        Returns: Şifrelenmiş key'ler
        """
        try:
            # Private key'i şifreli PEM formatında serialize et
            private_pem = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
            )
            
            # Public key'i PEM formatında serialize et
            public_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return {
                'private_key': private_pem.decode('utf-8'),
                'public_key': public_pem.decode('utf-8'),
                'master_key': base64.urlsafe_b64encode(self.master_key).decode('utf-8')
            }
            
        except Exception as e:
            logger.error(f"Key export hatası: {e}")
            raise
    
    def get_encryption_stats(self) -> Dict[str, Any]:
        """Şifreleme istatistikleri"""
        return {
            'master_key_length': len(self.master_key),
            'rsa_key_size': self.private_key.key_size if self.private_key else 0,
            'salt_length': len(self.password_salt),
            'algorithms': {
                'symmetric': 'Fernet (AES 128)',
                'asymmetric': 'RSA 2048',
                'password_hash': 'bcrypt',
                'key_derivation': 'PBKDF2-HMAC-SHA256'
            }
        }