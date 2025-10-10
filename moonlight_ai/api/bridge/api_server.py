"""
API Server
REST API sunucusu - istemci iletişimi
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from ...core.engine import get_engine, MoonLightEngine
from ...core.authentication.auth_manager import UserCredentials

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Pydantic models
class LoginRequest(BaseModel):
    email: str
    password: str
    broker: str
    demo_account: bool = True

class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: str
    session_info: Optional[Dict[str, Any]] = None

class TradeRequest(BaseModel):
    symbol: str
    direction: str  # CALL or PUT
    amount: float
    expiry_time: int

class StatusResponse(BaseModel):
    status: str
    timestamp: str
    session: Optional[Dict[str, Any]] = None
    market_connected: bool
    strategies: Dict[str, Any]
    risk_metrics: Optional[Dict[str, Any]] = None

class StrategyConfig(BaseModel):
    name: str
    enabled: bool = True
    symbols: List[str]
    parameters: Dict[str, Any] = {}


class APIServer:
    """
    REST API Sunucusu
    İstemciler ile güvenli iletişim sağlar
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 8000)
        self.ssl_enabled = config.get('ssl_enabled', False)
        
        # FastAPI uygulaması
        self.app = FastAPI(
            title="MoonLight AI API",
            description="Fixed-Time Trading AI API",
            version="0.1.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=config.get('cors_origins', ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Engine referansı
        self.engine: Optional[MoonLightEngine] = None
        
        # Route'ları kaydet
        self._register_routes()
        
        logger.info(f"API Server başlatıldı - {self.host}:{self.port}")
    
    def _register_routes(self) -> None:
        """API route'larını kaydet"""
        
        @self.app.on_event("startup")
        async def startup():
            """Sunucu başlatma"""
            self.engine = get_engine()
            if not await self.engine.initialize():
                raise Exception("Engine başlatma başarısız")
            logger.info("API Server hazır")
        
        @self.app.on_event("shutdown")
        async def shutdown():
            """Sunucu kapatma"""
            if self.engine:
                await self.engine.shutdown()
            logger.info("API Server kapatıldı")
        
        @self.app.get("/")
        async def root():
            """Ana sayfa"""
            return {
                "name": "MoonLight AI API",
                "version": "0.1.0",
                "status": "running",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        @self.app.post("/auth/login", response_model=LoginResponse)
        async def login(request: LoginRequest):
            """Kullanıcı girişi"""
            try:
                credentials = UserCredentials(
                    email=request.email,
                    password=request.password,
                    broker=request.broker,
                    demo_account=request.demo_account
                )
                
                if await self.engine.authenticate_user(credentials):
                    session = self.engine.current_session
                    return LoginResponse(
                        success=True,
                        token=session.token,
                        message="Giriş başarılı",
                        session_info={
                            "email": session.email,
                            "broker": session.broker,
                            "demo_account": session.demo_account,
                            "expires_at": session.expires_at.isoformat()
                        }
                    )
                else:
                    return LoginResponse(
                        success=False,
                        message="Giriş başarısız - kimlik bilgilerini kontrol edin"
                    )
                    
            except Exception as e:
                logger.error(f"Login hatası: {e}")
                return LoginResponse(
                    success=False,
                    message=f"Giriş hatası: {str(e)}"
                )
        
        @self.app.post("/auth/logout")
        async def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """Kullanıcı çıkışı"""
            try:
                token = credentials.credentials
                if self.engine.auth_manager:
                    success = await self.engine.auth_manager.logout(token)
                    return {"success": success, "message": "Çıkış yapıldı" if success else "Çıkış hatası"}
                return {"success": False, "message": "AuthManager mevcut değil"}
                
            except Exception as e:
                logger.error(f"Logout hatası: {e}")
                return {"success": False, "message": f"Çıkış hatası: {str(e)}"}
        
        @self.app.get("/status", response_model=StatusResponse)
        async def get_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """Sistem durumu"""
            try:
                # Token doğrulama
                await self._validate_token(credentials.credentials)
                
                status = self.engine.get_status()
                return StatusResponse(**status)
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Status hatası: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/trading/start")
        async def start_trading(
            symbols: List[str],
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            """İşlem başlatma"""
            try:
                await self._validate_token(credentials.credentials)
                
                # Market connector kontrolü
                if not self.engine.market_connector:
                    raise HTTPException(
                        status_code=400, 
                        detail="Market connector bağlı değil"
                    )
                
                success = await self.engine.start_trading(symbols)
                return {
                    "success": success,
                    "message": "İşlem başlatıldı" if success else "İşlem başlatma başarısız",
                    "symbols": symbols
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Start trading hatası: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/trading/stop")
        async def stop_trading(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """İşlem durdurma"""
            try:
                await self._validate_token(credentials.credentials)
                
                await self.engine.stop_trading()
                return {"success": True, "message": "İşlem durduruldu"}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Stop trading hatası: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/strategies")
        async def get_strategies(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """Strateji listesi"""
            try:
                await self._validate_token(credentials.credentials)
                
                strategies = {}
                for name, strategy in self.engine.strategies.items():
                    strategies[name] = strategy.status
                
                return {"strategies": strategies}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Get strategies hatası: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/strategies/{strategy_name}/start")
        async def start_strategy(
            strategy_name: str,
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            """Strateji başlatma"""
            try:
                await self._validate_token(credentials.credentials)
                
                if strategy_name not in self.engine.strategies:
                    raise HTTPException(status_code=404, detail="Strateji bulunamadı")
                
                strategy = self.engine.strategies[strategy_name]
                strategy.start()
                
                return {
                    "success": True,
                    "message": f"Strateji başlatıldı: {strategy_name}",
                    "status": strategy.status
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Start strategy hatası: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/strategies/{strategy_name}/stop")
        async def stop_strategy(
            strategy_name: str,
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            """Strateji durdurma"""
            try:
                await self._validate_token(credentials.credentials)
                
                if strategy_name not in self.engine.strategies:
                    raise HTTPException(status_code=404, detail="Strateji bulunamadı")
                
                strategy = self.engine.strategies[strategy_name]
                strategy.stop()
                
                return {
                    "success": True,
                    "message": f"Strateji durduruldu: {strategy_name}",
                    "status": strategy.status
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Stop strategy hatası: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/risk/report")
        async def get_risk_report(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """Risk raporu"""
            try:
                await self._validate_token(credentials.credentials)
                
                if not self.engine.risk_manager:
                    raise HTTPException(status_code=400, detail="Risk manager mevcut değil")
                
                report = self.engine.risk_manager.get_risk_report()
                return {"risk_report": report}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Risk report hatası: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/trades/history")
        async def get_trade_history(
            limit: int = 100,
            symbol: Optional[str] = None,
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            """İşlem geçmişi"""
            try:
                await self._validate_token(credentials.credentials)
                
                if not self.engine.data_manager:
                    raise HTTPException(status_code=400, detail="Data manager mevcut değil")
                
                history = await self.engine.data_manager.get_trade_history(limit, symbol)
                return {"trade_history": history, "count": len(history)}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Trade history hatası: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/market/data/{symbol}")
        async def get_market_data(
            symbol: str,
            hours: int = 24,
            credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            """Piyasa verisi geçmişi"""
            try:
                await self._validate_token(credentials.credentials)
                
                if not self.engine.data_manager:
                    raise HTTPException(status_code=400, detail="Data manager mevcut değil")
                
                data = await self.engine.data_manager.get_market_data_history(symbol, hours)
                return {"symbol": symbol, "data": data, "count": len(data)}
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Market data hatası: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health")
        async def health_check():
            """Sağlık kontrolü"""
            try:
                health_status = {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "engine_state": self.engine.state if self.engine else "not_initialized",
                    "components": {
                        "auth_manager": self.engine.auth_manager is not None if self.engine else False,
                        "market_connector": self.engine.market_connector is not None if self.engine else False,
                        "risk_manager": self.engine.risk_manager is not None if self.engine else False,
                        "data_manager": self.engine.data_manager is not None if self.engine else False
                    }
                }
                
                return health_status
                
            except Exception as e:
                logger.error(f"Health check hatası: {e}")
                return {
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e)
                }
    
    async def _validate_token(self, token: str) -> None:
        """Token doğrulama"""
        if not self.engine or not self.engine.auth_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Sistem henüz hazır değil"
            )
        
        session = await self.engine.auth_manager.validate_token(token)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz veya süresi dolmuş token"
            )
    
    async def start(self) -> None:
        """API sunucusunu başlat"""
        try:
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=True
            )
            
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"API sunucu başlatma hatası: {e}")
            raise
    
    def run_sync(self) -> None:
        """Senkron çalıştırma (test amaçlı)"""
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )