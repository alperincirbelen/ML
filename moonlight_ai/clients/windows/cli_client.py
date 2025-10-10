"""
CLI Client
Komut satırı arayüzü istemcisi
"""

import asyncio
import json
import logging
import sys
from typing import Dict, Optional, Any
from datetime import datetime

import aiohttp
import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


class CLIClient:
    """
    Komut Satırı İstemcisi
    MoonLight AI sistemi ile etkileşim için CLI arayüzü
    """
    
    def __init__(self, api_server: str, ws_server: str):
        self.api_server = api_server.rstrip('/')
        self.ws_server = ws_server
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.auth_token: Optional[str] = None
        self.running = False
        
        # Komutlar
        self.commands = {
            'help': self.cmd_help,
            'login': self.cmd_login,
            'logout': self.cmd_logout,
            'status': self.cmd_status,
            'start': self.cmd_start_trading,
            'stop': self.cmd_stop_trading,
            'strategies': self.cmd_strategies,
            'risk': self.cmd_risk_report,
            'history': self.cmd_trade_history,
            'market': self.cmd_market_data,
            'connect': self.cmd_connect_ws,
            'disconnect': self.cmd_disconnect_ws,
            'subscribe': self.cmd_subscribe,
            'exit': self.cmd_exit,
            'quit': self.cmd_exit
        }
        
        logger.info("CLI Client başlatıldı")
    
    async def run(self) -> None:
        """CLI istemcisini çalıştır"""
        try:
            self.session = aiohttp.ClientSession()
            self.running = True
            
            print("=" * 60)
            print("🌙 MoonLight AI - Windows CLI Client")
            print("=" * 60)
            print("Komutlar için 'help' yazın")
            print()
            
            # Ana komut döngüsü
            while self.running:
                try:
                    command_line = input("moonlight> ").strip()
                    if not command_line:
                        continue
                    
                    parts = command_line.split()
                    command = parts[0].lower()
                    args = parts[1:] if len(parts) > 1 else []
                    
                    if command in self.commands:
                        await self.commands[command](args)
                    else:
                        print(f"❌ Bilinmeyen komut: {command}")
                        print("Komutlar için 'help' yazın")
                
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\n⚠️  Çıkmak için 'exit' yazın")
                except Exception as e:
                    print(f"❌ Komut hatası: {e}")
                    logger.error(f"Komut hatası: {e}")
        
        finally:
            await self.cleanup()
    
    async def cleanup(self) -> None:
        """Temizlik işlemleri"""
        try:
            if self.websocket:
                await self.websocket.close()
            if self.session:
                await self.session.close()
            logger.info("CLI Client temizlendi")
        except Exception as e:
            logger.error(f"Temizlik hatası: {e}")
    
    async def api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """API isteği gönder"""
        try:
            url = f"{self.api_server}{endpoint}"
            headers = {}
            
            if self.auth_token:
                headers['Authorization'] = f'Bearer {self.auth_token}'
            
            if method.upper() == 'GET':
                async with self.session.get(url, headers=headers) as response:
                    return await response.json()
            elif method.upper() == 'POST':
                headers['Content-Type'] = 'application/json'
                async with self.session.post(url, headers=headers, json=data) as response:
                    return await response.json()
            else:
                raise ValueError(f"Desteklenmeyen HTTP metodu: {method}")
        
        except Exception as e:
            logger.error(f"API isteği hatası: {e}")
            return {"error": str(e)}
    
    # Komut işleyicileri
    async def cmd_help(self, args) -> None:
        """Yardım"""
        print("\n📖 Kullanılabilir Komutlar:")
        print("-" * 40)
        print("🔐 Kimlik Doğrulama:")
        print("  login                 - Sisteme giriş yap")
        print("  logout                - Sistemden çıkış yap")
        print()
        print("📊 Sistem Durumu:")
        print("  status                - Sistem durumunu göster")
        print("  risk                  - Risk raporunu göster")
        print()
        print("🚀 İşlem Yönetimi:")
        print("  start <symbols>       - İşlem başlat (örn: start EURUSD,GBPUSD)")
        print("  stop                  - İşlem durdur")
        print("  strategies            - Strateji listesi")
        print()
        print("📈 Veri:")
        print("  history [limit]       - İşlem geçmişi (varsayılan: 10)")
        print("  market <symbol>       - Piyasa verisi (örn: market EURUSD)")
        print()
        print("🔌 WebSocket:")
        print("  connect               - WebSocket bağlantısı kur")
        print("  disconnect            - WebSocket bağlantısını kes")
        print("  subscribe <channels>  - Kanallara abone ol")
        print("                         (market_data,trade_signals,trade_results)")
        print()
        print("❌ Çıkış:")
        print("  exit, quit            - Programdan çık")
        print()
    
    async def cmd_login(self, args) -> None:
        """Giriş yap"""
        try:
            print("\n🔐 Giriş Bilgileri:")
            email = input("E-posta: ").strip()
            password = input("Şifre: ").strip()
            broker = input("Broker (varsayılan: demo): ").strip() or "demo"
            demo_str = input("Demo hesap? (E/h, varsayılan: E): ").strip().lower()
            demo_account = demo_str != 'h'
            
            data = {
                "email": email,
                "password": password,
                "broker": broker,
                "demo_account": demo_account
            }
            
            print("🔄 Giriş yapılıyor...")
            response = await self.api_request('POST', '/auth/login', data)
            
            if response.get('success'):
                self.auth_token = response.get('token')
                session_info = response.get('session_info', {})
                
                print("✅ Giriş başarılı!")
                print(f"📧 E-posta: {session_info.get('email')}")
                print(f"🏢 Broker: {session_info.get('broker')}")
                print(f"🎯 Demo Hesap: {'Evet' if session_info.get('demo_account') else 'Hayır'}")
                print(f"⏰ Süre: {session_info.get('expires_at')}")
            else:
                print(f"❌ Giriş başarısız: {response.get('message')}")
        
        except Exception as e:
            print(f"❌ Giriş hatası: {e}")
    
    async def cmd_logout(self, args) -> None:
        """Çıkış yap"""
        try:
            if not self.auth_token:
                print("⚠️  Zaten giriş yapmamışsınız")
                return
            
            response = await self.api_request('POST', '/auth/logout')
            
            if response.get('success'):
                print("✅ Çıkış yapıldı")
                self.auth_token = None
            else:
                print(f"❌ Çıkış hatası: {response.get('message')}")
        
        except Exception as e:
            print(f"❌ Çıkış hatası: {e}")
    
    async def cmd_status(self, args) -> None:
        """Sistem durumu"""
        try:
            if not self.auth_token:
                print("⚠️  Önce giriş yapın")
                return
            
            response = await self.api_request('GET', '/status')
            
            if 'error' in response:
                print(f"❌ Durum alınamadı: {response['error']}")
                return
            
            print("\n📊 Sistem Durumu:")
            print("-" * 30)
            print(f"🔄 Durum: {response.get('state', 'Bilinmiyor')}")
            print(f"🔌 Market Bağlantısı: {'✅ Bağlı' if response.get('market_connected') else '❌ Bağlı Değil'}")
            print(f"⏰ Zaman: {response.get('timestamp')}")
            
            # Oturum bilgisi
            session = response.get('session')
            if session:
                print(f"\n👤 Oturum:")
                print(f"  📧 E-posta: {session.get('email')}")
                print(f"  🏢 Broker: {session.get('broker')}")
                print(f"  🎯 Demo: {'Evet' if session.get('demo_account') else 'Hayır'}")
                print(f"  ⏱️  Kalan Süre: {session.get('time_remaining')} saniye")
            
            # Stratejiler
            strategies = response.get('strategies', {})
            if strategies:
                print(f"\n🧠 Stratejiler ({len(strategies)}):")
                for name, strategy in strategies.items():
                    status = "🟢 Aktif" if strategy.get('active') else "🔴 Pasif"
                    print(f"  • {name}: {status}")
                    print(f"    Sinyal: {strategy.get('total_signals', 0)}")
                    print(f"    Başarı: %{strategy.get('win_rate_percentage', 0):.1f}")
            
            # Risk metrikleri
            risk = response.get('risk_metrics')
            if risk:
                metrics = risk.get('metrics', {})
                print(f"\n⚠️  Risk Durumu:")
                print(f"  💰 Günlük P&L: {metrics.get('daily_pnl', 0):.2f}")
                print(f"  📊 Aktif İşlem: {metrics.get('active_trades', 0)}")
                print(f"  📈 Kazanma Oranı: %{metrics.get('win_rate', 0):.1f}")
                print(f"  📉 Drawdown: %{metrics.get('current_drawdown', 0):.1f}")
        
        except Exception as e:
            print(f"❌ Durum hatası: {e}")
    
    async def cmd_start_trading(self, args) -> None:
        """İşlem başlat"""
        try:
            if not self.auth_token:
                print("⚠️  Önce giriş yapın")
                return
            
            if not args:
                symbols_input = input("Semboller (virgülle ayırın, örn: EURUSD,GBPUSD): ").strip()
                symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
            else:
                symbols = [s.upper() for s in args[0].split(',')]
            
            if not symbols:
                print("❌ En az bir sembol belirtmelisiniz")
                return
            
            print(f"🚀 İşlem başlatılıyor: {', '.join(symbols)}")
            response = await self.api_request('POST', '/trading/start', symbols)
            
            if response.get('success'):
                print("✅ İşlem başlatıldı!")
                print(f"📈 Takip edilen semboller: {', '.join(symbols)}")
            else:
                print(f"❌ İşlem başlatılamadı: {response.get('message')}")
        
        except Exception as e:
            print(f"❌ İşlem başlatma hatası: {e}")
    
    async def cmd_stop_trading(self, args) -> None:
        """İşlem durdur"""
        try:
            if not self.auth_token:
                print("⚠️  Önce giriş yapın")
                return
            
            print("🛑 İşlem durduruluyor...")
            response = await self.api_request('POST', '/trading/stop')
            
            if response.get('success'):
                print("✅ İşlem durduruldu")
            else:
                print(f"❌ İşlem durdurulamadı: {response.get('message')}")
        
        except Exception as e:
            print(f"❌ İşlem durdurma hatası: {e}")
    
    async def cmd_strategies(self, args) -> None:
        """Strateji listesi"""
        try:
            if not self.auth_token:
                print("⚠️  Önce giriş yapın")
                return
            
            response = await self.api_request('GET', '/strategies')
            
            if 'error' in response:
                print(f"❌ Stratejiler alınamadı: {response['error']}")
                return
            
            strategies = response.get('strategies', {})
            
            if not strategies:
                print("⚠️  Aktif strateji yok")
                return
            
            print(f"\n🧠 Stratejiler ({len(strategies)}):")
            print("-" * 50)
            
            for name, strategy in strategies.items():
                status = "🟢 Aktif" if strategy.get('active') else "🔴 Pasif"
                enabled = "✅ Etkin" if strategy.get('enabled') else "❌ Devre Dışı"
                
                print(f"\n📋 {name}")
                print(f"  Durum: {status} | {enabled}")
                print(f"  Semboller: {', '.join(strategy.get('symbols', []))}")
                print(f"  Toplam Sinyal: {strategy.get('total_signals', 0)}")
                print(f"  Başarı Oranı: %{strategy.get('win_rate_percentage', 0):.1f}")
                print(f"  Min Güven: {strategy.get('min_confidence', 0):.2f}")
                print(f"  Son Güncelleme: {strategy.get('last_update_time', 'Yok')}")
        
        except Exception as e:
            print(f"❌ Strateji listesi hatası: {e}")
    
    async def cmd_risk_report(self, args) -> None:
        """Risk raporu"""
        try:
            if not self.auth_token:
                print("⚠️  Önce giriş yapın")
                return
            
            response = await self.api_request('GET', '/risk/report')
            
            if 'error' in response:
                print(f"❌ Risk raporu alınamadı: {response['error']}")
                return
            
            risk_report = response.get('risk_report', {})
            metrics = risk_report.get('metrics', {})
            limits = risk_report.get('limits', {})
            
            print("\n⚠️  Risk Raporu:")
            print("-" * 40)
            
            print("📊 Mevcut Durum:")
            print(f"  💰 Güncel Bakiye: {metrics.get('current_balance', 0):.2f}")
            print(f"  📈 Günlük P&L: {metrics.get('daily_pnl', 0):.2f}")
            print(f"  💎 Toplam P&L: {metrics.get('total_pnl', 0):.2f}")
            print(f"  🔄 Aktif İşlem: {metrics.get('active_trades', 0)}")
            print(f"  📊 Günlük İşlem: {metrics.get('daily_trades', 0)}")
            print(f"  🎯 Kazanma Oranı: %{metrics.get('win_rate', 0):.1f}")
            print(f"  📉 Maks Drawdown: %{metrics.get('max_drawdown', 0):.1f}")
            print(f"  📊 Güncel Drawdown: %{metrics.get('current_drawdown', 0):.1f}")
            print(f"  ⚠️  Risk Seviyesi: {metrics.get('risk_level', 'Bilinmiyor').upper()}")
            
            print("\n🚫 Risk Limitleri:")
            print(f"  💸 Maks Günlük Kayıp: {limits.get('max_daily_loss', 0):.2f}")
            print(f"  💰 Maks Pozisyon: {limits.get('max_position_size', 0):.2f}")
            print(f"  🔄 Maks Eşzamanlı: {limits.get('max_concurrent_trades', 0)}")
            print(f"  📊 Maks Günlük İşlem: {limits.get('max_daily_trades', 0)}")
            print(f"  📉 Maks Drawdown: %{limits.get('max_drawdown_percentage', 0):.1f}")
        
        except Exception as e:
            print(f"❌ Risk raporu hatası: {e}")
    
    async def cmd_trade_history(self, args) -> None:
        """İşlem geçmişi"""
        try:
            if not self.auth_token:
                print("⚠️  Önce giriş yapın")
                return
            
            limit = 10
            if args and args[0].isdigit():
                limit = int(args[0])
            
            response = await self.api_request('GET', f'/trades/history?limit={limit}')
            
            if 'error' in response:
                print(f"❌ İşlem geçmişi alınamadı: {response['error']}")
                return
            
            history = response.get('trade_history', [])
            
            if not history:
                print("⚠️  İşlem geçmişi yok")
                return
            
            print(f"\n📈 İşlem Geçmişi (Son {len(history)}):")
            print("-" * 80)
            
            for trade in history:
                success_icon = "✅" if trade.get('success') else "❌"
                direction_icon = "📈" if trade.get('direction') == 'CALL' else "📉"
                
                print(f"{success_icon} {direction_icon} {trade.get('symbol')} | "
                      f"{trade.get('direction')} | "
                      f"Tutar: {trade.get('amount', 0):.2f} | "
                      f"Kar: {trade.get('profit', 0):.2f} | "
                      f"Zarar: {trade.get('loss', 0):.2f}")
                print(f"    Başlangıç: {trade.get('start_time')}")
                print(f"    Bitiş: {trade.get('end_time', 'Devam ediyor')}")
                print()
        
        except Exception as e:
            print(f"❌ İşlem geçmişi hatası: {e}")
    
    async def cmd_market_data(self, args) -> None:
        """Piyasa verisi"""
        try:
            if not self.auth_token:
                print("⚠️  Önce giriş yapın")
                return
            
            if not args:
                symbol = input("Sembol (örn: EURUSD): ").strip().upper()
            else:
                symbol = args[0].upper()
            
            if not symbol:
                print("❌ Sembol belirtmelisiniz")
                return
            
            hours = 1  # Son 1 saat
            response = await self.api_request('GET', f'/market/data/{symbol}?hours={hours}')
            
            if 'error' in response:
                print(f"❌ Piyasa verisi alınamadı: {response['error']}")
                return
            
            data = response.get('data', [])
            
            if not data:
                print(f"⚠️  {symbol} için veri yok")
                return
            
            print(f"\n📊 {symbol} Piyasa Verisi (Son {len(data)} kayıt):")
            print("-" * 60)
            
            # Son 5 kaydı göster
            for record in data[-5:]:
                print(f"⏰ {record.get('timestamp')}")
                print(f"   Bid: {record.get('bid'):.5f} | "
                      f"Ask: {record.get('ask'):.5f} | "
                      f"Son: {record.get('last_price'):.5f}")
                print(f"   Spread: {record.get('spread'):.5f} | "
                      f"Hacim: {record.get('volume', 0):.0f}")
                print()
        
        except Exception as e:
            print(f"❌ Piyasa verisi hatası: {e}")
    
    async def cmd_connect_ws(self, args) -> None:
        """WebSocket bağlantısı kur"""
        try:
            if self.websocket:
                print("⚠️  WebSocket zaten bağlı")
                return
            
            if not self.auth_token:
                print("⚠️  Önce giriş yapın")
                return
            
            print("🔌 WebSocket bağlantısı kuruluyor...")
            
            self.websocket = await websockets.connect(self.ws_server)
            
            # Kimlik doğrulama
            auth_message = {
                'type': 'auth',
                'token': self.auth_token
            }
            await self.websocket.send(json.dumps(auth_message))
            
            # Mesaj dinleme görevi başlat
            asyncio.create_task(self._ws_message_handler())
            
            print("✅ WebSocket bağlantısı kuruldu")
        
        except Exception as e:
            print(f"❌ WebSocket bağlantı hatası: {e}")
            self.websocket = None
    
    async def cmd_disconnect_ws(self, args) -> None:
        """WebSocket bağlantısını kes"""
        try:
            if not self.websocket:
                print("⚠️  WebSocket bağlı değil")
                return
            
            await self.websocket.close()
            self.websocket = None
            print("✅ WebSocket bağlantısı kesildi")
        
        except Exception as e:
            print(f"❌ WebSocket bağlantı kesme hatası: {e}")
    
    async def cmd_subscribe(self, args) -> None:
        """Kanallara abone ol"""
        try:
            if not self.websocket:
                print("⚠️  Önce WebSocket bağlantısı kurun")
                return
            
            if not args:
                channels_input = input("Kanallar (virgülle ayırın): ").strip()
                channels = [c.strip() for c in channels_input.split(',') if c.strip()]
            else:
                channels = args[0].split(',')
            
            if not channels:
                print("❌ En az bir kanal belirtmelisiniz")
                print("Mevcut kanallar: market_data, trade_signals, trade_results, system_status")
                return
            
            subscribe_message = {
                'type': 'subscribe',
                'channels': channels
            }
            await self.websocket.send(json.dumps(subscribe_message))
            
            print(f"📡 Kanallara abone olundu: {', '.join(channels)}")
        
        except Exception as e:
            print(f"❌ Abonelik hatası: {e}")
    
    async def _ws_message_handler(self) -> None:
        """WebSocket mesaj işleyici"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    if msg_type == 'welcome':
                        print(f"🎉 WebSocket hoş geldin: {data.get('client_id')}")
                    elif msg_type == 'auth_success':
                        print("✅ WebSocket kimlik doğrulama başarılı")
                    elif msg_type == 'subscribe_success':
                        print(f"📡 Abonelik başarılı: {', '.join(data.get('channels', []))}")
                    elif msg_type == 'market_data':
                        self._handle_market_data(data.get('data', {}))
                    elif msg_type == 'trade_signal':
                        self._handle_trade_signal(data.get('data', {}))
                    elif msg_type == 'trade_result':
                        self._handle_trade_result(data.get('data', {}))
                    elif msg_type == 'system_status':
                        self._handle_system_status(data.get('data', {}))
                    elif msg_type == 'error':
                        print(f"❌ WebSocket hatası: {data.get('message')}")
                    elif msg_type == 'heartbeat':
                        pass  # Sessiz heartbeat
                    else:
                        print(f"📨 WebSocket mesajı: {msg_type}")
                
                except json.JSONDecodeError:
                    print("❌ Geçersiz WebSocket mesajı")
                except Exception as e:
                    print(f"❌ WebSocket mesaj işleme hatası: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            print("🔌 WebSocket bağlantısı kesildi")
            self.websocket = None
        except Exception as e:
            print(f"❌ WebSocket dinleme hatası: {e}")
            self.websocket = None
    
    def _handle_market_data(self, data: Dict[str, Any]) -> None:
        """Piyasa verisi işle"""
        symbol = data.get('symbol')
        last = data.get('last')
        spread = data.get('spread')
        timestamp = data.get('timestamp', '')[:19]  # Sadece tarih/saat kısmı
        
        print(f"📊 {symbol}: {last:.5f} (Spread: {spread:.5f}) [{timestamp}]")
    
    def _handle_trade_signal(self, data: Dict[str, Any]) -> None:
        """İşlem sinyali işle"""
        symbol = data.get('symbol')
        direction = data.get('direction')
        confidence = data.get('confidence', 0)
        strategy = data.get('strategy_name')
        validation = data.get('validation', {})
        
        direction_icon = "📈" if direction == 'CALL' else "📉"
        status_icon = "✅" if validation.get('approved') else "❌"
        
        print(f"{status_icon} {direction_icon} SİNYAL: {symbol} {direction} "
              f"(Güven: {confidence:.2f}, Strateji: {strategy})")
        
        if not validation.get('approved'):
            print(f"   Ret Nedeni: {validation.get('reason')}")
    
    def _handle_trade_result(self, data: Dict[str, Any]) -> None:
        """İşlem sonucu işle"""
        symbol = data.get('symbol')
        direction = data.get('direction')
        success = data.get('success', False)
        profit = data.get('profit', 0)
        loss = data.get('loss', 0)
        
        success_icon = "✅" if success else "❌"
        direction_icon = "📈" if direction == 'CALL' else "📉"
        pnl = profit - loss
        
        print(f"{success_icon} {direction_icon} SONUÇ: {symbol} {direction} "
              f"P&L: {pnl:+.2f} (Kar: {profit:.2f}, Zarar: {loss:.2f})")
    
    def _handle_system_status(self, data: Dict[str, Any]) -> None:
        """Sistem durumu işle"""
        old_state = data.get('old_state')
        new_state = data.get('new_state')
        
        print(f"🔄 Sistem durumu değişti: {old_state} → {new_state}")
    
    async def cmd_exit(self, args) -> None:
        """Çıkış"""
        print("👋 MoonLight AI'dan çıkılıyor...")
        self.running = False