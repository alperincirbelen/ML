"""
FastAPI Server - REST and WebSocket endpoints
Parça 15 - API sunucusu
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
import asyncio


def create_app(
    config,
    storage,
    scheduler,
    guardrails,
    metrics,
    connector_manager
) -> FastAPI:
    """
    FastAPI uygulaması oluştur
    """
    app = FastAPI(
        title="MoonLight Core API",
        version="1.0.0",
        description="Fixed-Time Trading AI - Core Engine"
    )
    
    # CORS (yalnız localhost)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:*", "http://localhost:*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # WebSocket bağlantıları
    active_ws_connections: list[WebSocket] = []
    
    @app.get("/status")
    async def get_status():
        """
        Sistem durumu
        """
        import time
        
        return {
            "api_version": "1.0",
            "service": {
                "state": "running",
                "uptime_s": int(time.time()),  # Başlangıçtan beri geçen süre (basitleştirilmiş)
                "tz": "UTC"
            },
            "core": {
                "workers": scheduler.worker_count(),
                "mode": "paper" if config.features.paper_mode else "live",
                "trade_enabled": config.features.trade_enabled
            },
            "accounts": [
                {
                    "id": acc.id,
                    "state": "connected"  # Basitleştirilmiş
                }
                for acc in config.accounts
            ],
            "killswitch": guardrails.is_kill_switch_on()
        }
    
    @app.get("/accounts")
    async def get_accounts():
        """Hesaplar listesi"""
        return [
            {
                "id": acc.id,
                "username_mask": _mask_email(acc.username),
                "profile_store": acc.profile_store,
                "state": "connected"
            }
            for acc in config.accounts
        ]
    
    @app.get("/workers")
    async def get_workers():
        """Aktif worker'lar"""
        active = scheduler.get_active_workers()
        
        return [
            {
                "account": acc,
                "product": prod,
                "tf": tf,
                "state": "RUNNING"
            }
            for acc, prod, tf in active
        ]
    
    @app.post("/start")
    async def start_workers(scope: Optional[str] = None):
        """Worker'ları başlat"""
        # Basitleştirilmiş - tüm aktif ürün/TF için başlat
        started = []
        
        for product_cfg in config.products:
            if not product_cfg.enabled:
                continue
            
            for tf_cfg in product_cfg.timeframes:
                if not tf_cfg.enabled:
                    continue
                
                for account in config.accounts:
                    # Worker başlat (factory gerekli - şimdilik placeholder)
                    # await scheduler.start_worker(account.id, product_cfg.product, tf_cfg.tf)
                    started.append({
                        "account": account.id,
                        "product": product_cfg.product,
                        "tf": tf_cfg.tf
                    })
        
        return {"ok": True, "started": started}
    
    @app.post("/stop")
    async def stop_workers():
        """Tüm worker'ları durdur"""
        await scheduler.stop_all()
        return {"ok": True}
    
    @app.post("/killswitch")
    async def toggle_killswitch(enabled: bool):
        """Kill-Switch aç/kapat"""
        guardrails.toggle_kill_switch(enabled)
        
        return {
            "ok": True,
            "killswitch": enabled,
            "ts": int(time.time() * 1000)
        }
    
    @app.get("/orders")
    async def get_orders(limit: int = 20):
        """Son işlemler"""
        trades = await storage.get_recent_trades(limit)
        return trades
    
    @app.get("/metrics")
    async def get_metrics():
        """Metrik özeti"""
        return metrics.snapshot()
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """
        WebSocket endpoint
        Real-time metrics, logs, trade updates
        """
        await websocket.accept()
        active_ws_connections.append(websocket)
        
        try:
            while True:
                # Heartbeat
                data = await websocket.receive_text()
                
                if data == '{"type":"ping"}':
                    await websocket.send_text('{"type":"pong"}')
                
                # Periyodik metrik gönderimi
                await asyncio.sleep(2)
                snapshot = metrics.snapshot()
                await websocket.send_json({
                    "topic": "metrics",
                    "data": snapshot
                })
        
        except WebSocketDisconnect:
            active_ws_connections.remove(websocket)
    
    return app


def _mask_email(email: str) -> str:
    """E-posta maskele"""
    if '@' in email:
        parts = email.split('@')
        if len(parts[0]) > 2:
            return f"{parts[0][0]}***@{parts[1]}"
    return "***"
