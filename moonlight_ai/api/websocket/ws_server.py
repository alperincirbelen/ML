"""
WebSocket Server
Gerçek zamanlı veri akışı için WebSocket sunucusu
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime

import websockets
from websockets.server import WebSocketServerProtocol

from ...core.engine import get_engine, MoonLightEngine

logger = logging.getLogger(__name__)


class WebSocketServer:
    """
    WebSocket Sunucusu
    İstemciler ile gerçek zamanlı iletişim sağlar
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 8001)
        self.max_connections = config.get('max_connections', 100)
        self.heartbeat_interval = config.get('heartbeat_interval', 30)
        
        # Bağlı istemciler
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.authenticated_clients: Dict[str, str] = {}  # websocket_id -> token
        
        # Abonelikler
        self.subscriptions: Dict[str, Set[str]] = {
            'market_data': set(),
            'trade_signals': set(),
            'trade_results': set(),
            'system_status': set()
        }
        
        # Engine referansı
        self.engine: Optional[MoonLightEngine] = None
        
        # Görevler
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._server = None
        
        logger.info(f"WebSocket Server başlatıldı - {self.host}:{self.port}")
    
    async def start(self) -> None:
        """WebSocket sunucusunu başlat"""
        try:
            # Engine'i al
            self.engine = get_engine()
            
            # Engine olay dinleyicilerini ekle
            self.engine.add_event_handler('market_data', self._on_market_data)
            self.engine.add_event_handler('trade_signal', self._on_trade_signal)
            self.engine.add_event_handler('trade_result', self._on_trade_result)
            self.engine.add_event_handler('state_change', self._on_state_change)
            
            # WebSocket sunucusunu başlat
            self._server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                max_size=1024*1024,  # 1MB
                max_queue=32,
                compression=None,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Heartbeat görevini başlat
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            logger.info(f"WebSocket sunucusu başlatıldı: ws://{self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"WebSocket sunucu başlatma hatası: {e}")
            raise
    
    async def stop(self) -> None:
        """WebSocket sunucusunu durdur"""
        try:
            # Heartbeat görevini iptal et
            if self._heartbeat_task and not self._heartbeat_task.done():
                self._heartbeat_task.cancel()
                try:
                    await self._heartbeat_task
                except asyncio.CancelledError:
                    pass
            
            # Tüm istemcileri kapat
            if self.clients:
                await asyncio.gather(
                    *[client.close() for client in self.clients.values()],
                    return_exceptions=True
                )
            
            # Sunucuyu kapat
            if self._server:
                self._server.close()
                await self._server.wait_closed()
            
            logger.info("WebSocket sunucusu durduruldu")
            
        except Exception as e:
            logger.error(f"WebSocket sunucu durdurma hatası: {e}")
    
    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """İstemci bağlantısı işleyici"""
        client_id = f"client_{id(websocket)}"
        client_address = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        logger.info(f"Yeni WebSocket bağlantısı: {client_id} ({client_address})")
        
        try:
            # Maksimum bağlantı kontrolü
            if len(self.clients) >= self.max_connections:
                await websocket.close(code=1013, reason="Maksimum bağlantı sayısı aşıldı")
                return
            
            # İstemciyi kaydet
            self.clients[client_id] = websocket
            
            # Hoş geldin mesajı
            await self._send_message(websocket, {
                'type': 'welcome',
                'client_id': client_id,
                'timestamp': datetime.utcnow().isoformat(),
                'server_info': {
                    'name': 'MoonLight AI WebSocket',
                    'version': '0.1.0'
                }
            })
            
            # Mesaj döngüsü
            async for message in websocket:
                try:
                    await self._process_message(client_id, websocket, message)
                except Exception as e:
                    logger.error(f"Mesaj işleme hatası ({client_id}): {e}")
                    await self._send_error(websocket, f"Mesaj işleme hatası: {str(e)}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket bağlantısı kapatıldı: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket istemci hatası ({client_id}): {e}")
        finally:
            # Temizlik
            await self._cleanup_client(client_id)
    
    async def _process_message(self, client_id: str, websocket: WebSocketServerProtocol, message: str) -> None:
        """İstemci mesajını işle"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'auth':
                await self._handle_auth(client_id, websocket, data)
            elif msg_type == 'subscribe':
                await self._handle_subscribe(client_id, websocket, data)
            elif msg_type == 'unsubscribe':
                await self._handle_unsubscribe(client_id, websocket, data)
            elif msg_type == 'ping':
                await self._handle_ping(client_id, websocket, data)
            else:
                await self._send_error(websocket, f"Bilinmeyen mesaj türü: {msg_type}")
        
        except json.JSONDecodeError:
            await self._send_error(websocket, "Geçersiz JSON formatı")
        except Exception as e:
            logger.error(f"Mesaj işleme hatası: {e}")
            await self._send_error(websocket, f"Mesaj işleme hatası: {str(e)}")
    
    async def _handle_auth(self, client_id: str, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Kimlik doğrulama işle"""
        try:
            token = data.get('token')
            if not token:
                await self._send_error(websocket, "Token gerekli")
                return
            
            # Token doğrulama
            if self.engine and self.engine.auth_manager:
                session = await self.engine.auth_manager.validate_token(token)
                if session:
                    self.authenticated_clients[client_id] = token
                    await self._send_message(websocket, {
                        'type': 'auth_success',
                        'message': 'Kimlik doğrulama başarılı',
                        'session_info': {
                            'email': session.email,
                            'broker': session.broker,
                            'demo_account': session.demo_account,
                            'expires_at': session.expires_at.isoformat()
                        }
                    })
                    logger.info(f"WebSocket kimlik doğrulama başarılı: {client_id} ({session.email})")
                else:
                    await self._send_error(websocket, "Geçersiz token")
            else:
                await self._send_error(websocket, "Kimlik doğrulama servisi mevcut değil")
        
        except Exception as e:
            logger.error(f"Kimlik doğrulama hatası: {e}")
            await self._send_error(websocket, f"Kimlik doğrulama hatası: {str(e)}")
    
    async def _handle_subscribe(self, client_id: str, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Abonelik işle"""
        try:
            # Kimlik doğrulama kontrolü
            if client_id not in self.authenticated_clients:
                await self._send_error(websocket, "Kimlik doğrulama gerekli")
                return
            
            channels = data.get('channels', [])
            if not isinstance(channels, list):
                await self._send_error(websocket, "Kanallar liste olmalı")
                return
            
            subscribed_channels = []
            for channel in channels:
                if channel in self.subscriptions:
                    self.subscriptions[channel].add(client_id)
                    subscribed_channels.append(channel)
                else:
                    logger.warning(f"Bilinmeyen kanal: {channel}")
            
            await self._send_message(websocket, {
                'type': 'subscribe_success',
                'channels': subscribed_channels,
                'message': f'{len(subscribed_channels)} kanala abone olundu'
            })
            
            logger.info(f"WebSocket abonelik: {client_id} -> {subscribed_channels}")
        
        except Exception as e:
            logger.error(f"Abonelik hatası: {e}")
            await self._send_error(websocket, f"Abonelik hatası: {str(e)}")
    
    async def _handle_unsubscribe(self, client_id: str, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Abonelik iptali işle"""
        try:
            channels = data.get('channels', [])
            if not isinstance(channels, list):
                await self._send_error(websocket, "Kanallar liste olmalı")
                return
            
            unsubscribed_channels = []
            for channel in channels:
                if channel in self.subscriptions and client_id in self.subscriptions[channel]:
                    self.subscriptions[channel].remove(client_id)
                    unsubscribed_channels.append(channel)
            
            await self._send_message(websocket, {
                'type': 'unsubscribe_success',
                'channels': unsubscribed_channels,
                'message': f'{len(unsubscribed_channels)} kanal aboneliği iptal edildi'
            })
            
            logger.info(f"WebSocket abonelik iptali: {client_id} -> {unsubscribed_channels}")
        
        except Exception as e:
            logger.error(f"Abonelik iptali hatası: {e}")
            await self._send_error(websocket, f"Abonelik iptali hatası: {str(e)}")
    
    async def _handle_ping(self, client_id: str, websocket: WebSocketServerProtocol, data: Dict[str, Any]) -> None:
        """Ping işle"""
        await self._send_message(websocket, {
            'type': 'pong',
            'timestamp': datetime.utcnow().isoformat(),
            'client_id': client_id
        })
    
    async def _cleanup_client(self, client_id: str) -> None:
        """İstemci temizliği"""
        try:
            # İstemciyi kaldır
            if client_id in self.clients:
                del self.clients[client_id]
            
            # Kimlik doğrulama kaydını kaldır
            if client_id in self.authenticated_clients:
                del self.authenticated_clients[client_id]
            
            # Aboneliklerden kaldır
            for channel_clients in self.subscriptions.values():
                channel_clients.discard(client_id)
            
            logger.info(f"WebSocket istemci temizlendi: {client_id}")
        
        except Exception as e:
            logger.error(f"İstemci temizlik hatası: {e}")
    
    async def _send_message(self, websocket: WebSocketServerProtocol, message: Dict[str, Any]) -> None:
        """Mesaj gönder"""
        try:
            await websocket.send(json.dumps(message, default=str))
        except Exception as e:
            logger.error(f"Mesaj gönderme hatası: {e}")
    
    async def _send_error(self, websocket: WebSocketServerProtocol, error_message: str) -> None:
        """Hata mesajı gönder"""
        await self._send_message(websocket, {
            'type': 'error',
            'message': error_message,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    async def _broadcast_to_channel(self, channel: str, message: Dict[str, Any]) -> None:
        """Kanala mesaj yayınla"""
        try:
            if channel not in self.subscriptions:
                return
            
            subscribers = self.subscriptions[channel].copy()
            if not subscribers:
                return
            
            # Mesajı hazırla
            message['channel'] = channel
            message['timestamp'] = datetime.utcnow().isoformat()
            message_json = json.dumps(message, default=str)
            
            # Tüm abonelere gönder
            tasks = []
            for client_id in subscribers:
                if client_id in self.clients:
                    websocket = self.clients[client_id]
                    tasks.append(websocket.send(message_json))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        except Exception as e:
            logger.error(f"Kanal yayını hatası ({channel}): {e}")
    
    async def _heartbeat_loop(self) -> None:
        """Heartbeat döngüsü"""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Tüm istemcilere heartbeat gönder
                if self.clients:
                    heartbeat_message = {
                        'type': 'heartbeat',
                        'timestamp': datetime.utcnow().isoformat(),
                        'connected_clients': len(self.clients)
                    }
                    
                    tasks = []
                    for websocket in self.clients.values():
                        tasks.append(self._send_message(websocket, heartbeat_message))
                    
                    await asyncio.gather(*tasks, return_exceptions=True)
        
        except asyncio.CancelledError:
            logger.info("Heartbeat görevi iptal edildi")
        except Exception as e:
            logger.error(f"Heartbeat döngüsü hatası: {e}")
    
    # Engine olay işleyicileri
    async def _on_market_data(self, market_data) -> None:
        """Piyasa verisi olayı"""
        try:
            message = {
                'type': 'market_data',
                'data': {
                    'symbol': market_data.symbol,
                    'bid': market_data.bid,
                    'ask': market_data.ask,
                    'last': market_data.last,
                    'volume': market_data.volume,
                    'spread': market_data.spread,
                    'timestamp': market_data.timestamp.isoformat()
                }
            }
            await self._broadcast_to_channel('market_data', message)
        except Exception as e:
            logger.error(f"Market data yayını hatası: {e}")
    
    async def _on_trade_signal(self, signal_data: Dict[str, Any]) -> None:
        """İşlem sinyali olayı"""
        try:
            signal = signal_data['signal']
            validation = signal_data['validation']
            
            message = {
                'type': 'trade_signal',
                'data': {
                    'symbol': signal.symbol,
                    'direction': signal.direction,
                    'amount': signal.amount,
                    'confidence': signal.confidence,
                    'strategy_name': signal.strategy_name,
                    'expiry_time': signal.expiry_time,
                    'validation': validation
                }
            }
            await self._broadcast_to_channel('trade_signals', message)
        except Exception as e:
            logger.error(f"Trade signal yayını hatası: {e}")
    
    async def _on_trade_result(self, result: Dict[str, Any]) -> None:
        """İşlem sonucu olayı"""
        try:
            message = {
                'type': 'trade_result',
                'data': result
            }
            await self._broadcast_to_channel('trade_results', message)
        except Exception as e:
            logger.error(f"Trade result yayını hatası: {e}")
    
    async def _on_state_change(self, state_data: Dict[str, Any]) -> None:
        """Durum değişikliği olayı"""
        try:
            message = {
                'type': 'system_status',
                'data': state_data
            }
            await self._broadcast_to_channel('system_status', message)
        except Exception as e:
            logger.error(f"State change yayını hatası: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Sunucu istatistikleri"""
        return {
            'connected_clients': len(self.clients),
            'authenticated_clients': len(self.authenticated_clients),
            'subscriptions': {
                channel: len(clients) 
                for channel, clients in self.subscriptions.items()
            },
            'server_info': {
                'host': self.host,
                'port': self.port,
                'max_connections': self.max_connections,
                'heartbeat_interval': self.heartbeat_interval
            }
        }