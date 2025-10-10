"""
Connector Manager - Çoklu hesap yönetimi
Parça 6 - 4 hesaba kadar izolasyon
"""

from typing import Dict, Optional
from .mock import MockConnector
from .interface import Connector


class ConnectorManager:
    """
    Çoklu hesap için connector yöneticisi
    Her hesap için izole bağlantı
    """
    
    def __init__(self):
        self._by_account: Dict[str, Connector] = {}
    
    async def ensure(
        self, 
        account_id: str, 
        connector_type: str = "mock",
        **kwargs
    ) -> Connector:
        """
        Hesap için connector sağla (yoksa oluştur)
        """
        connector = self._by_account.get(account_id)
        
        if not connector:
            if connector_type == "mock":
                connector = MockConnector(account_id, **kwargs)
            # elif connector_type == "olymp":
            #     connector = OlympConnector(account_id, **kwargs)
            else:
                raise ValueError(f"Unknown connector type: {connector_type}")
            
            self._by_account[account_id] = connector
        
        return connector
    
    async def login_all(self, credentials: Dict[str, Dict[str, str]]) -> None:
        """
        Tüm hesapları giriş yap
        credentials: {account_id: {"username": ..., "password": ..., "otp": ...}}
        """
        for account_id, connector in self._by_account.items():
            creds = credentials.get(account_id, {})
            if creds:
                username = creds.get('username', '')
                password = creds.get('password', '')
                otp = creds.get('otp')
                
                await connector.login(username, password, otp)
    
    async def close_all(self) -> None:
        """Tüm bağlantıları kapat"""
        for connector in self._by_account.values():
            await connector.close()
        
        self._by_account.clear()
    
    def get(self, account_id: str) -> Optional[Connector]:
        """Hesap için connector getir"""
        return self._by_account.get(account_id)
    
    def all_accounts(self) -> List[str]:
        """Tüm hesap ID'lerini listele"""
        return list(self._by_account.keys())
