"""
Authentication Tests
Kimlik doğrulama modülü testleri
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from core.authentication.auth_manager import AuthManager, UserCredentials, AuthSession
from core.authentication.encryption import EncryptionManager
from core.authentication.token_manager import TokenManager


class TestAuthManager:
    """AuthManager test sınıfı"""
    
    @pytest.mark.asyncio
    async def test_auth_manager_initialization(self, test_config):
        """AuthManager başlatma testi"""
        config = test_config['security']
        auth_manager = AuthManager(config)
        
        assert auth_manager.secret_key == config['jwt_secret_key']
        assert auth_manager.algorithm == config['jwt_algorithm']
        assert auth_manager.token_expiry == config['jwt_expiration']
        assert len(auth_manager.active_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_user_credentials_validation(self):
        """UserCredentials doğrulama testi"""
        # Geçerli credentials
        valid_creds = UserCredentials(
            email="test@example.com",
            password="password123",
            broker="test_broker",
            demo_account=True
        )
        assert valid_creds.email == "test@example.com"
        
        # Geçersiz email
        with pytest.raises(ValueError, match="Geçerli bir e-posta adresi gerekli"):
            UserCredentials(
                email="invalid-email",
                password="password123",
                broker="test_broker"
            )
        
        # Kısa şifre
        with pytest.raises(ValueError, match="Şifre en az 6 karakter olmalı"):
            UserCredentials(
                email="test@example.com",
                password="123",
                broker="test_broker"
            )
    
    @pytest.mark.asyncio
    async def test_successful_authentication(self, auth_manager, test_user_credentials):
        """Başarılı kimlik doğrulama testi"""
        session = await auth_manager.authenticate(test_user_credentials)
        
        assert session is not None
        assert isinstance(session, AuthSession)
        assert session.email == test_user_credentials.email
        assert session.broker == test_user_credentials.broker
        assert session.demo_account == test_user_credentials.demo_account
        assert not session.is_expired
        assert session.token in auth_manager.active_sessions
    
    @pytest.mark.asyncio
    async def test_token_validation(self, auth_manager, test_user_credentials):
        """Token doğrulama testi"""
        # Oturum oluştur
        session = await auth_manager.authenticate(test_user_credentials)
        assert session is not None
        
        # Token'ı doğrula
        validated_session = await auth_manager.validate_token(session.token)
        assert validated_session is not None
        assert validated_session.email == session.email
        assert validated_session.token == session.token
    
    @pytest.mark.asyncio
    async def test_invalid_token_validation(self, auth_manager):
        """Geçersiz token doğrulama testi"""
        # Geçersiz token
        invalid_session = await auth_manager.validate_token("invalid_token")
        assert invalid_session is None
        
        # Boş token
        empty_session = await auth_manager.validate_token("")
        assert empty_session is None
    
    @pytest.mark.asyncio
    async def test_token_refresh(self, auth_manager, test_user_credentials):
        """Token yenileme testi"""
        # Oturum oluştur
        session = await auth_manager.authenticate(test_user_credentials)
        old_token = session.token
        
        # Token'ı yenile
        new_token = await auth_manager.refresh_token(old_token)
        assert new_token is not None
        assert new_token != old_token
        
        # Yeni token geçerli olmalı
        new_session = await auth_manager.validate_token(new_token)
        assert new_session is not None
        assert new_session.email == session.email
    
    @pytest.mark.asyncio
    async def test_logout(self, auth_manager, test_user_credentials):
        """Çıkış testi"""
        # Oturum oluştur
        session = await auth_manager.authenticate(test_user_credentials)
        token = session.token
        
        # Çıkış yap
        success = await auth_manager.logout(token)
        assert success is True
        
        # Token artık geçerli olmamalı
        validated_session = await auth_manager.validate_token(token)
        assert validated_session is None
        assert token not in auth_manager.active_sessions
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, auth_manager):
        """Rate limiting testi"""
        invalid_creds = UserCredentials(
            email="test@example.com",
            password="wrong_password",
            broker="test_broker"
        )
        
        # Birden fazla başarısız deneme
        for _ in range(auth_manager.max_attempts):
            session = await auth_manager.authenticate(invalid_creds)
            assert session is None
        
        # Hesap kilitli olmalı
        assert auth_manager._is_locked_out(invalid_creds.email)
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self, auth_manager, test_user_credentials):
        """Oturum temizleme testi"""
        # Oturum oluştur
        session = await auth_manager.authenticate(test_user_credentials)
        
        # Oturumu manuel olarak süresi dolmuş yap
        session.expires_at = datetime.utcnow() - timedelta(seconds=1)
        
        # Temizlik yap
        cleaned_count = await auth_manager.cleanup_expired_sessions()
        assert cleaned_count >= 1
        assert session.token not in auth_manager.active_sessions


class TestEncryptionManager:
    """EncryptionManager test sınıfı"""
    
    def test_encryption_manager_initialization(self, test_config):
        """EncryptionManager başlatma testi"""
        config = test_config['security']
        enc_manager = EncryptionManager(config)
        
        assert enc_manager.master_key is not None
        assert enc_manager.fernet is not None
        assert enc_manager.private_key is not None
        assert enc_manager.public_key is not None
    
    def test_symmetric_encryption(self, test_config):
        """Symmetric şifreleme testi"""
        enc_manager = EncryptionManager(test_config['security'])
        
        original_data = "Bu bir test mesajıdır"
        
        # Şifrele
        encrypted = enc_manager.encrypt_symmetric(original_data)
        assert encrypted != original_data
        assert isinstance(encrypted, str)
        
        # Şifreyi çöz
        decrypted = enc_manager.decrypt_symmetric(encrypted)
        assert decrypted == original_data
    
    def test_asymmetric_encryption(self, test_config):
        """Asymmetric şifreleme testi"""
        enc_manager = EncryptionManager(test_config['security'])
        
        original_data = "Bu bir test mesajıdır"
        
        # Şifrele
        encrypted = enc_manager.encrypt_asymmetric(original_data)
        assert encrypted != original_data
        assert isinstance(encrypted, str)
        
        # Şifreyi çöz
        decrypted = enc_manager.decrypt_asymmetric(encrypted)
        assert decrypted == original_data
    
    def test_password_hashing(self, test_config):
        """Password hashing testi"""
        enc_manager = EncryptionManager(test_config['security'])
        
        password = "test_password_123"
        
        # Hash'le
        hashed = enc_manager.hash_password(password)
        assert hashed != password
        assert isinstance(hashed, str)
        
        # Doğrula
        assert enc_manager.verify_password(password, hashed) is True
        assert enc_manager.verify_password("wrong_password", hashed) is False
    
    def test_secure_token_generation(self, test_config):
        """Güvenli token oluşturma testi"""
        enc_manager = EncryptionManager(test_config['security'])
        
        token1 = enc_manager.generate_secure_token()
        token2 = enc_manager.generate_secure_token()
        
        assert token1 != token2
        assert len(token1) > 0
        assert len(token2) > 0
    
    def test_api_key_generation(self, test_config):
        """API key oluşturma testi"""
        enc_manager = EncryptionManager(test_config['security'])
        
        api_keys = enc_manager.generate_api_key()
        
        assert 'api_key' in api_keys
        assert 'api_secret' in api_keys
        assert 'created_at' in api_keys
        assert api_keys['api_key'].startswith('mk_')
    
    def test_data_signing(self, test_config):
        """Veri imzalama testi"""
        enc_manager = EncryptionManager(test_config['security'])
        
        data = "Bu imzalanacak veridir"
        
        # İmzala
        signature = enc_manager.sign_data(data)
        assert signature is not None
        assert isinstance(signature, str)
        
        # İmzayı doğrula
        assert enc_manager.verify_signature(data, signature) is True
        assert enc_manager.verify_signature("farklı veri", signature) is False


class TestTokenManager:
    """TokenManager test sınıfı"""
    
    def test_token_manager_initialization(self, test_config):
        """TokenManager başlatma testi"""
        config = test_config['security']
        token_manager = TokenManager(config)
        
        assert token_manager.secret_key == config['jwt_secret_key']
        assert token_manager.algorithm == config['jwt_algorithm']
        assert len(token_manager.blacklisted_tokens) == 0
        assert len(token_manager.refresh_tokens) == 0
    
    def test_access_token_generation(self, test_config):
        """Access token oluşturma testi"""
        token_manager = TokenManager(test_config['security'])
        
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'broker': 'test_broker',
            'demo_account': True
        }
        
        token = token_manager.generate_access_token(user_data)
        assert token is not None
        assert isinstance(token, str)
        
        # Token'ı doğrula
        payload = token_manager.validate_token(token, 'access')
        assert payload is not None
        assert payload['email'] == user_data['email']
        assert payload['token_type'] == 'access'
    
    def test_refresh_token_generation(self, test_config):
        """Refresh token oluşturma testi"""
        token_manager = TokenManager(test_config['security'])
        
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'broker': 'test_broker',
            'demo_account': True
        }
        
        token = token_manager.generate_refresh_token(user_data)
        assert token is not None
        assert isinstance(token, str)
        
        # Token'ı doğrula
        payload = token_manager.validate_token(token, 'refresh')
        assert payload is not None
        assert payload['email'] == user_data['email']
        assert payload['token_type'] == 'refresh'
    
    def test_token_pair_generation(self, test_config):
        """Token çifti oluşturma testi"""
        token_manager = TokenManager(test_config['security'])
        
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'broker': 'test_broker',
            'demo_account': True
        }
        
        tokens = token_manager.generate_token_pair(user_data)
        
        assert 'access_token' in tokens
        assert 'refresh_token' in tokens
        assert 'token_type' in tokens
        assert 'expires_in' in tokens
        
        # Her iki token da geçerli olmalı
        access_payload = token_manager.validate_token(tokens['access_token'], 'access')
        refresh_payload = token_manager.validate_token(tokens['refresh_token'], 'refresh')
        
        assert access_payload is not None
        assert refresh_payload is not None
    
    def test_token_refresh(self, test_config):
        """Token yenileme testi"""
        token_manager = TokenManager(test_config['security'])
        
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'broker': 'test_broker',
            'demo_account': True
        }
        
        # İlk token çifti
        original_tokens = token_manager.generate_token_pair(user_data)
        
        # Refresh token ile yenile
        new_tokens = token_manager.refresh_access_token(original_tokens['refresh_token'])
        
        assert new_tokens is not None
        assert 'access_token' in new_tokens
        assert 'refresh_token' in new_tokens
        assert new_tokens['access_token'] != original_tokens['access_token']
    
    def test_token_revocation(self, test_config):
        """Token iptal etme testi"""
        token_manager = TokenManager(test_config['security'])
        
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'broker': 'test_broker',
            'demo_account': True
        }
        
        token = token_manager.generate_access_token(user_data)
        
        # Token geçerli olmalı
        assert token_manager.validate_token(token, 'access') is not None
        
        # Token'ı iptal et
        success = token_manager.revoke_token(token)
        assert success is True
        
        # Token artık geçerli olmamalı
        assert token_manager.validate_token(token, 'access') is None
    
    def test_expired_token_cleanup(self, test_config):
        """Süresi dolmuş token temizleme testi"""
        # Kısa süreli token için config
        short_config = test_config['security'].copy()
        short_config['refresh_token_expire'] = 1  # 1 saniye
        
        token_manager = TokenManager(short_config)
        
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'broker': 'test_broker',
            'demo_account': True
        }
        
        # Refresh token oluştur
        refresh_token = token_manager.generate_refresh_token(user_data)
        
        # Token'ın geçerli olduğunu kontrol et
        assert token_manager.validate_token(refresh_token, 'refresh') is not None
        
        # 2 saniye bekle (token'ın süresinin dolması için)
        import time
        time.sleep(2)
        
        # Temizlik yap
        cleaned_count = token_manager.cleanup_expired_tokens()
        assert cleaned_count >= 1
        
        # Token artık geçerli olmamalı
        assert token_manager.validate_token(refresh_token, 'refresh') is None