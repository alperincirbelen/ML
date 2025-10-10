"""
FastAPI Server - REST & WebSocket Endpoints

Loopback-only, Windows masaüstü UI için
"""

from __future__ import annotations
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import asyncio

from ..config import AppConfig
from ..storage import Storage
from ..telemetry import get_metrics


def create_app(config: AppConfig, storage: Storage, scheduler: Any = None) -> FastAPI:
    """
    FastAPI uygulaması oluştur
    
    Args:
        config: Uygulama konfigürasyonu
        storage: Storage instance
        scheduler: Worker scheduler (opsiyonel)
    """
    app = FastAPI(
        title="MoonLight Core API",
        version="1.0.0",
        description="Fixed-Time Trading AI - Core Engine API"
    )
    
    # CORS (loopback için gerekli değil ama opsiyonel)
    if config.api.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:*"],
            allow_methods=["*"],
            allow_headers=["*"]
        )
    
    # Global state
    app.state.config = config
    app.state.storage = storage
    app.state.scheduler = scheduler
    app.state.kill_switch = False
    app.state.active_ws = set()
    
    # === REST Endpoints ===
    
    @app.get("/status")
    async def get_status(x_api_key: Optional[str] = Header(default=None)):
        """Sistem durumu"""
        # API key kontrolü (opsiyonel)
        if config.api.api_key and x_api_key != config.api.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        workers_list = []
        if scheduler:
            workers_list = scheduler.list_workers()
        
        return {
            "api_version": "1.0",
            "config_version": config.config_version,
            "mode": config.mode,
            "connector": config.connector,
            "kill_switch": app.state.kill_switch,
            "service": {
                "state": "running",
                "uptime_s": 0,  # TODO: Calculate
                "tz": "UTC"
            },
            "accounts": [
                {"id": acc.id, "username_mask": mask_email(acc.username)}
                for acc in config.accounts
            ],
            "workers": workers_list,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @app.get("/accounts")
    async def get_accounts():
        """Hesap listesi"""
        return [
            {
                "id": acc.id,
                "username_mask": mask_email(acc.username),
                "profile_store": acc.profile_store
            }
            for acc in config.accounts
        ]
    
    @app.get("/products")
    async def get_products():
        """Ürün listesi"""
        return [
            {
                "product": prod.product,
                "enabled": prod.enabled,
                "strategies": prod.strategies,
                "timeframes": [
                    {
                        "tf": tf.tf,
                        "enabled": tf.enabled,
                        "win_threshold": tf.win_threshold,
                        "permit_min": tf.permit_min,
                        "permit_max": tf.permit_max
                    }
                    for tf in prod.timeframes
                ]
            }
            for prod in config.products
        ]
    
    @app.get("/workers")
    async def get_workers():
        """Aktif worker listesi"""
        if not scheduler:
            return []
        return scheduler.list_workers()
    
    @app.post("/start")
    async def start_workers(scope: Dict[str, Any]):
        """
        Worker başlat
        
        Body:
          {"scope": "global"} veya
          {"scope": "account", "account": "acc1"} veya
          {"scope": "worker", "account": "acc1", "product": "EURUSD", "tf": 1}
        """
        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")
        
        # TODO: Scope'a göre worker başlatma
        return {"ok": True, "message": "Workers started"}
    
    @app.post("/stop")
    async def stop_workers(scope: Dict[str, Any]):
        """Worker durdur"""
        if not scheduler:
            raise HTTPException(status_code=503, detail="Scheduler not available")
        
        # TODO: Scope'a göre worker durdurma
        return {"ok": True, "message": "Workers stopped"}
    
    @app.get("/orders")
    async def get_orders(
        limit: int = 20,
        account: Optional[str] = None,
        product: Optional[str] = None,
        timeframe: Optional[int] = None
    ):
        """İşlem geçmişi"""
        trades = await storage.recent_trades(
            limit=limit,
            account_id=account,
            product=product,
            timeframe=timeframe
        )
        return trades
    
    @app.post("/killswitch")
    async def toggle_killswitch(state: Dict[str, bool]):
        """Kill switch aç/kapa"""
        app.state.kill_switch = state.get("open", False)
        
        return {
            "open": app.state.kill_switch,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @app.get("/metrics")
    async def get_metrics_summary():
        """Metrik özeti"""
        metrics = get_metrics()
        snapshot = metrics.snapshot()
        
        # Scope'a göre grupla
        by_scope = {}
        for s in snapshot:
            if s.scope not in by_scope:
                by_scope[s.scope] = {}
            by_scope[s.scope][s.key] = s.value
        
        return by_scope
    
    # === WebSocket Endpoint ===
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """
        WebSocket bağlantısı
        
        Kanallar: metrics, trade_updates, alerts, logs
        """
        await websocket.accept()
        app.state.active_ws.add(websocket)
        
        try:
            while True:
                # Ping/pong
                data = await websocket.receive_text()
                
                if data == '{"type":"ping"}':
                    await websocket.send_text('{"type":"pong"}')
                
                # TODO: Channel subscription yönetimi
                
        except WebSocketDisconnect:
            app.state.active_ws.discard(websocket)
    
    return app


# Helper
def mask_email(email: str) -> str:
    """E-posta quick mask"""
    if '@' in email:
        parts = email.split('@')
        if len(parts[0]) > 2:
            return f"{parts[0][0]}***@{parts[1]}"
    return email


# Standalone run (test için)
if __name__ == "__main__":
    import uvicorn
    from ..config import load_config
    
    # Örnek config yükle
    cfg = load_config("configs/app.example.yaml")
    storage = Storage(cfg.storage.sqlite_path)
    
    app_instance = create_app(cfg, storage)
    
    print(f"✓ Starting API server on {cfg.api.host}:{cfg.api.http_port}")
    print(f"  Mode: {cfg.mode}")
    print(f"  Connector: {cfg.connector}")
    print(f"\n  Docs: http://{cfg.api.host}:{cfg.api.http_port}/docs")
    
    uvicorn.run(
        app_instance,
        host=cfg.api.host,
        port=cfg.api.http_port,
        log_level="info"
    )
