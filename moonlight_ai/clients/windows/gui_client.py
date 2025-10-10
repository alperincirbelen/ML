"""
GUI Client
Grafik arayüz istemcisi (Tkinter tabanlı)
"""

import asyncio
import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, Optional, Any
from datetime import datetime
import threading

import aiohttp
import websockets

logger = logging.getLogger(__name__)


class GUIClient:
    """
    Grafik Arayüz İstemcisi
    Tkinter tabanlı GUI ile MoonLight AI sistemi kontrolü
    """
    
    def __init__(self, api_server: str, ws_server: str):
        self.api_server = api_server.rstrip('/')
        self.ws_server = ws_server
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket = None
        self.auth_token: Optional[str] = None
        self.running = False
        
        # GUI bileşenleri
        self.root = None
        self.notebook = None
        self.status_var = None
        self.log_text = None
        
        # Async loop
        self.loop = None
        
        logger.info("GUI Client başlatıldı")
    
    async def run(self) -> None:
        """GUI istemcisini çalıştır"""
        try:
            self.session = aiohttp.ClientSession()
            self.running = True
            
            # Async loop'u al
            self.loop = asyncio.get_event_loop()
            
            # GUI'yi ayrı thread'de çalıştır
            gui_thread = threading.Thread(target=self._run_gui, daemon=True)
            gui_thread.start()
            
            # Ana thread'de async görevleri çalıştır
            while self.running:
                await asyncio.sleep(0.1)
        
        finally:
            await self.cleanup()
    
    def _run_gui(self) -> None:
        """GUI'yi çalıştır"""
        try:
            self.root = tk.Tk()
            self.root.title("🌙 MoonLight AI - Windows Client")
            self.root.geometry("1000x700")
            self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
            
            self._create_gui()
            self.root.mainloop()
        
        except Exception as e:
            logger.error(f"GUI hatası: {e}")
    
    def _create_gui(self) -> None:
        """GUI bileşenlerini oluştur"""
        # Ana frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Başlık
        title_label = ttk.Label(main_frame, text="🌙 MoonLight AI", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Durum çubuğu
        self.status_var = tk.StringVar(value="🔴 Bağlı Değil")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Arial", 10))
        status_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        # Notebook (sekmeler)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Sekmeler
        self._create_login_tab()
        self._create_trading_tab()
        self._create_strategies_tab()
        self._create_risk_tab()
        self._create_history_tab()
        self._create_logs_tab()
        
        # Grid yapılandırması
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
    
    def _create_login_tab(self) -> None:
        """Giriş sekmesi"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="🔐 Giriş")
        
        # Giriş formu
        ttk.Label(frame, text="E-posta:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.email_entry = ttk.Entry(frame, width=30)
        self.email_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        ttk.Label(frame, text="Şifre:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.password_entry = ttk.Entry(frame, width=30, show="*")
        self.password_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        ttk.Label(frame, text="Broker:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.broker_entry = ttk.Entry(frame, width=30)
        self.broker_entry.insert(0, "demo")
        self.broker_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        self.demo_var = tk.BooleanVar(value=True)
        demo_check = ttk.Checkbutton(frame, text="Demo Hesap", variable=self.demo_var)
        demo_check.grid(row=3, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        # Butonlar
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        login_btn = ttk.Button(button_frame, text="Giriş Yap", command=self._login)
        login_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        logout_btn = ttk.Button(button_frame, text="Çıkış Yap", command=self._logout)
        logout_btn.pack(side=tk.LEFT, padx=5)
        
        # Oturum bilgisi
        self.session_text = scrolledtext.ScrolledText(frame, height=8, width=60)
        self.session_text.grid(row=5, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)
    
    def _create_trading_tab(self) -> None:
        """İşlem sekmesi"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="🚀 İşlem")
        
        # Sembol seçimi
        ttk.Label(frame, text="Semboller:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.symbols_entry = ttk.Entry(frame, width=40)
        self.symbols_entry.insert(0, "EURUSD,GBPUSD,USDJPY")
        self.symbols_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=(10, 0))
        
        # Butonlar
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        start_btn = ttk.Button(button_frame, text="İşlem Başlat", command=self._start_trading)
        start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        stop_btn = ttk.Button(button_frame, text="İşlem Durdur", command=self._stop_trading)
        stop_btn.pack(side=tk.LEFT, padx=5)
        
        status_btn = ttk.Button(button_frame, text="Durum Güncelle", command=self._update_status)
        status_btn.pack(side=tk.LEFT, padx=5)
        
        # WebSocket
        ws_frame = ttk.LabelFrame(frame, text="WebSocket", padding="5")
        ws_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        connect_ws_btn = ttk.Button(ws_frame, text="Bağlan", command=self._connect_ws)
        connect_ws_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        disconnect_ws_btn = ttk.Button(ws_frame, text="Bağlantıyı Kes", command=self._disconnect_ws)
        disconnect_ws_btn.pack(side=tk.LEFT, padx=5)
        
        subscribe_btn = ttk.Button(ws_frame, text="Abone Ol", command=self._subscribe)
        subscribe_btn.pack(side=tk.LEFT, padx=5)
        
        # Durum bilgisi
        self.trading_text = scrolledtext.ScrolledText(frame, height=15, width=80)
        self.trading_text.grid(row=3, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(3, weight=1)
    
    def _create_strategies_tab(self) -> None:
        """Strateji sekmesi"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="🧠 Stratejiler")
        
        # Butonlar
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=0, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        
        refresh_btn = ttk.Button(button_frame, text="Yenile", command=self._refresh_strategies)
        refresh_btn.pack(side=tk.LEFT)
        
        # Strateji listesi
        self.strategies_tree = ttk.Treeview(frame, columns=('status', 'signals', 'success_rate'), show='tree headings')
        self.strategies_tree.heading('#0', text='Strateji')
        self.strategies_tree.heading('status', text='Durum')
        self.strategies_tree.heading('signals', text='Sinyal')
        self.strategies_tree.heading('success_rate', text='Başarı %')
        
        self.strategies_tree.column('#0', width=200)
        self.strategies_tree.column('status', width=100)
        self.strategies_tree.column('signals', width=100)
        self.strategies_tree.column('success_rate', width=100)
        
        self.strategies_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar
        strategies_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.strategies_tree.yview)
        strategies_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.strategies_tree.configure(yscrollcommand=strategies_scroll.set)
        
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
    
    def _create_risk_tab(self) -> None:
        """Risk sekmesi"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="⚠️ Risk")
        
        # Buton
        refresh_risk_btn = ttk.Button(frame, text="Risk Raporu Yenile", command=self._refresh_risk)
        refresh_risk_btn.grid(row=0, column=0, pady=(0, 10))
        
        # Risk bilgisi
        self.risk_text = scrolledtext.ScrolledText(frame, height=20, width=80)
        self.risk_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
    
    def _create_history_tab(self) -> None:
        """Geçmiş sekmesi"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="📈 Geçmiş")
        
        # Kontroller
        control_frame = ttk.Frame(frame)
        control_frame.grid(row=0, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        
        ttk.Label(control_frame, text="Limit:").pack(side=tk.LEFT)
        self.history_limit_var = tk.StringVar(value="20")
        limit_entry = ttk.Entry(control_frame, textvariable=self.history_limit_var, width=10)
        limit_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        refresh_history_btn = ttk.Button(control_frame, text="Yenile", command=self._refresh_history)
        refresh_history_btn.pack(side=tk.LEFT)
        
        # İşlem geçmişi
        self.history_tree = ttk.Treeview(frame, columns=('symbol', 'direction', 'amount', 'profit', 'loss', 'time'), show='headings')
        self.history_tree.heading('symbol', text='Sembol')
        self.history_tree.heading('direction', text='Yön')
        self.history_tree.heading('amount', text='Tutar')
        self.history_tree.heading('profit', text='Kar')
        self.history_tree.heading('loss', text='Zarar')
        self.history_tree.heading('time', text='Zaman')
        
        for col in ('symbol', 'direction', 'amount', 'profit', 'loss'):
            self.history_tree.column(col, width=80)
        self.history_tree.column('time', width=150)
        
        self.history_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar
        history_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        history_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.history_tree.configure(yscrollcommand=history_scroll.set)
        
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
    
    def _create_logs_tab(self) -> None:
        """Log sekmesi"""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="📝 Loglar")
        
        # Temizle butonu
        clear_btn = ttk.Button(frame, text="Temizle", command=self._clear_logs)
        clear_btn.grid(row=0, column=0, pady=(0, 10))
        
        # Log alanı
        self.log_text = scrolledtext.ScrolledText(frame, height=25, width=100)
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
    
    def _log(self, message: str) -> None:
        """Log mesajı ekle"""
        if self.log_text:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
    
    def _clear_logs(self) -> None:
        """Logları temizle"""
        if self.log_text:
            self.log_text.delete(1.0, tk.END)
    
    # API işlemleri
    def _login(self) -> None:
        """Giriş yap"""
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()
        broker = self.broker_entry.get().strip() or "demo"
        demo_account = self.demo_var.get()
        
        if not email or not password:
            messagebox.showerror("Hata", "E-posta ve şifre gerekli")
            return
        
        # Async işlemi çalıştır
        asyncio.run_coroutine_threadsafe(
            self._async_login(email, password, broker, demo_account),
            self.loop
        )
    
    async def _async_login(self, email: str, password: str, broker: str, demo_account: bool) -> None:
        """Async giriş işlemi"""
        try:
            data = {
                "email": email,
                "password": password,
                "broker": broker,
                "demo_account": demo_account
            }
            
            response = await self.api_request('POST', '/auth/login', data)
            
            if response.get('success'):
                self.auth_token = response.get('token')
                session_info = response.get('session_info', {})
                
                self._log("✅ Giriş başarılı!")
                self.status_var.set("🟢 Bağlı")
                
                # Oturum bilgisini göster
                info_text = f"""✅ Giriş Başarılı!

📧 E-posta: {session_info.get('email')}
🏢 Broker: {session_info.get('broker')}
🎯 Demo Hesap: {'Evet' if session_info.get('demo_account') else 'Hayır'}
⏰ Süre: {session_info.get('expires_at')}
🔑 Token: {self.auth_token[:20]}...
"""
                self.session_text.delete(1.0, tk.END)
                self.session_text.insert(1.0, info_text)
            else:
                self._log(f"❌ Giriş başarısız: {response.get('message')}")
                messagebox.showerror("Giriş Hatası", response.get('message'))
        
        except Exception as e:
            self._log(f"❌ Giriş hatası: {e}")
            messagebox.showerror("Hata", f"Giriş hatası: {e}")
    
    def _logout(self) -> None:
        """Çıkış yap"""
        if not self.auth_token:
            messagebox.showwarning("Uyarı", "Zaten giriş yapmamışsınız")
            return
        
        asyncio.run_coroutine_threadsafe(self._async_logout(), self.loop)
    
    async def _async_logout(self) -> None:
        """Async çıkış işlemi"""
        try:
            response = await self.api_request('POST', '/auth/logout')
            
            if response.get('success'):
                self._log("✅ Çıkış yapıldı")
                self.auth_token = None
                self.status_var.set("🔴 Bağlı Değil")
                self.session_text.delete(1.0, tk.END)
                self.session_text.insert(1.0, "Oturum kapatıldı")
            else:
                self._log(f"❌ Çıkış hatası: {response.get('message')}")
        
        except Exception as e:
            self._log(f"❌ Çıkış hatası: {e}")
    
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
    
    # Diğer işlemler için placeholder metodlar
    def _start_trading(self) -> None:
        """İşlem başlat"""
        symbols = self.symbols_entry.get().strip()
        if not symbols:
            messagebox.showerror("Hata", "Sembol belirtmelisiniz")
            return
        
        symbols_list = [s.strip().upper() for s in symbols.split(',')]
        asyncio.run_coroutine_threadsafe(self._async_start_trading(symbols_list), self.loop)
    
    async def _async_start_trading(self, symbols: list) -> None:
        """Async işlem başlatma"""
        try:
            response = await self.api_request('POST', '/trading/start', symbols)
            if response.get('success'):
                self._log(f"✅ İşlem başlatıldı: {', '.join(symbols)}")
                self._update_trading_display("🚀 İşlem Aktif")
            else:
                self._log(f"❌ İşlem başlatılamadı: {response.get('message')}")
        except Exception as e:
            self._log(f"❌ İşlem başlatma hatası: {e}")
    
    def _stop_trading(self) -> None:
        """İşlem durdur"""
        asyncio.run_coroutine_threadsafe(self._async_stop_trading(), self.loop)
    
    async def _async_stop_trading(self) -> None:
        """Async işlem durdurma"""
        try:
            response = await self.api_request('POST', '/trading/stop')
            if response.get('success'):
                self._log("✅ İşlem durduruldu")
                self._update_trading_display("🛑 İşlem Durduruldu")
            else:
                self._log(f"❌ İşlem durdurulamadı: {response.get('message')}")
        except Exception as e:
            self._log(f"❌ İşlem durdurma hatası: {e}")
    
    def _update_status(self) -> None:
        """Durum güncelle"""
        asyncio.run_coroutine_threadsafe(self._async_update_status(), self.loop)
    
    async def _async_update_status(self) -> None:
        """Async durum güncelleme"""
        try:
            response = await self.api_request('GET', '/status')
            if 'error' not in response:
                status_text = f"""📊 Sistem Durumu:
🔄 Durum: {response.get('state', 'Bilinmiyor')}
🔌 Market: {'✅ Bağlı' if response.get('market_connected') else '❌ Bağlı Değil'}
⏰ Zaman: {response.get('timestamp')}

👤 Oturum:
📧 E-posta: {response.get('session', {}).get('email', 'Yok')}
🏢 Broker: {response.get('session', {}).get('broker', 'Yok')}
"""
                self._update_trading_display(status_text)
                self._log("✅ Durum güncellendi")
            else:
                self._log(f"❌ Durum alınamadı: {response['error']}")
        except Exception as e:
            self._log(f"❌ Durum güncelleme hatası: {e}")
    
    def _update_trading_display(self, text: str) -> None:
        """İşlem ekranını güncelle"""
        if self.trading_text:
            self.trading_text.delete(1.0, tk.END)
            self.trading_text.insert(1.0, text)
    
    # WebSocket işlemleri
    def _connect_ws(self) -> None:
        """WebSocket bağlantısı"""
        if not self.auth_token:
            messagebox.showwarning("Uyarı", "Önce giriş yapın")
            return
        
        asyncio.run_coroutine_threadsafe(self._async_connect_ws(), self.loop)
    
    async def _async_connect_ws(self) -> None:
        """Async WebSocket bağlantısı"""
        try:
            self.websocket = await websockets.connect(self.ws_server)
            
            # Kimlik doğrulama
            auth_message = {
                'type': 'auth',
                'token': self.auth_token
            }
            await self.websocket.send(json.dumps(auth_message))
            
            self._log("✅ WebSocket bağlantısı kuruldu")
            
            # Mesaj dinleme görevi başlat
            asyncio.create_task(self._ws_message_handler())
        
        except Exception as e:
            self._log(f"❌ WebSocket bağlantı hatası: {e}")
    
    def _disconnect_ws(self) -> None:
        """WebSocket bağlantısını kes"""
        asyncio.run_coroutine_threadsafe(self._async_disconnect_ws(), self.loop)
    
    async def _async_disconnect_ws(self) -> None:
        """Async WebSocket bağlantı kesme"""
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
                self._log("✅ WebSocket bağlantısı kesildi")
        except Exception as e:
            self._log(f"❌ WebSocket bağlantı kesme hatası: {e}")
    
    def _subscribe(self) -> None:
        """Kanallara abone ol"""
        if not self.websocket:
            messagebox.showwarning("Uyarı", "Önce WebSocket bağlantısı kurun")
            return
        
        channels = ['market_data', 'trade_signals', 'trade_results', 'system_status']
        asyncio.run_coroutine_threadsafe(self._async_subscribe(channels), self.loop)
    
    async def _async_subscribe(self, channels: list) -> None:
        """Async abonelik"""
        try:
            subscribe_message = {
                'type': 'subscribe',
                'channels': channels
            }
            await self.websocket.send(json.dumps(subscribe_message))
            self._log(f"📡 Kanallara abone olundu: {', '.join(channels)}")
        except Exception as e:
            self._log(f"❌ Abonelik hatası: {e}")
    
    async def _ws_message_handler(self) -> None:
        """WebSocket mesaj işleyici"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    
                    if msg_type == 'market_data':
                        market_data = data.get('data', {})
                        self._log(f"📊 {market_data.get('symbol')}: {market_data.get('last'):.5f}")
                    elif msg_type == 'trade_signal':
                        signal_data = data.get('data', {})
                        direction_icon = "📈" if signal_data.get('direction') == 'CALL' else "📉"
                        self._log(f"{direction_icon} SİNYAL: {signal_data.get('symbol')} {signal_data.get('direction')}")
                    elif msg_type == 'trade_result':
                        result_data = data.get('data', {})
                        success_icon = "✅" if result_data.get('success') else "❌"
                        self._log(f"{success_icon} SONUÇ: {result_data.get('symbol')} P&L: {result_data.get('profit', 0) - result_data.get('loss', 0):+.2f}")
                    elif msg_type == 'auth_success':
                        self._log("✅ WebSocket kimlik doğrulama başarılı")
                    elif msg_type == 'subscribe_success':
                        self._log("📡 Abonelik başarılı")
                    elif msg_type == 'error':
                        self._log(f"❌ WebSocket hatası: {data.get('message')}")
                
                except json.JSONDecodeError:
                    self._log("❌ Geçersiz WebSocket mesajı")
                except Exception as e:
                    self._log(f"❌ WebSocket mesaj işleme hatası: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            self._log("🔌 WebSocket bağlantısı kesildi")
            self.websocket = None
        except Exception as e:
            self._log(f"❌ WebSocket dinleme hatası: {e}")
            self.websocket = None
    
    # Diğer tab işlemleri
    def _refresh_strategies(self) -> None:
        """Stratejileri yenile"""
        asyncio.run_coroutine_threadsafe(self._async_refresh_strategies(), self.loop)
    
    async def _async_refresh_strategies(self) -> None:
        """Async strateji yenileme"""
        try:
            response = await self.api_request('GET', '/strategies')
            if 'error' not in response:
                strategies = response.get('strategies', {})
                
                # Tabloyu temizle
                for item in self.strategies_tree.get_children():
                    self.strategies_tree.delete(item)
                
                # Stratejileri ekle
                for name, strategy in strategies.items():
                    status = "🟢 Aktif" if strategy.get('active') else "🔴 Pasif"
                    signals = strategy.get('total_signals', 0)
                    success_rate = f"{strategy.get('win_rate_percentage', 0):.1f}%"
                    
                    self.strategies_tree.insert('', 'end', text=name, 
                                              values=(status, signals, success_rate))
                
                self._log(f"✅ {len(strategies)} strateji yüklendi")
            else:
                self._log(f"❌ Stratejiler alınamadı: {response['error']}")
        except Exception as e:
            self._log(f"❌ Strateji yenileme hatası: {e}")
    
    def _refresh_risk(self) -> None:
        """Risk raporunu yenile"""
        asyncio.run_coroutine_threadsafe(self._async_refresh_risk(), self.loop)
    
    async def _async_refresh_risk(self) -> None:
        """Async risk raporu yenileme"""
        try:
            response = await self.api_request('GET', '/risk/report')
            if 'error' not in response:
                risk_report = response.get('risk_report', {})
                metrics = risk_report.get('metrics', {})
                limits = risk_report.get('limits', {})
                
                risk_text = f"""⚠️ Risk Raporu

📊 Mevcut Durum:
💰 Güncel Bakiye: {metrics.get('current_balance', 0):.2f}
📈 Günlük P&L: {metrics.get('daily_pnl', 0):.2f}
💎 Toplam P&L: {metrics.get('total_pnl', 0):.2f}
🔄 Aktif İşlem: {metrics.get('active_trades', 0)}
📊 Günlük İşlem: {metrics.get('daily_trades', 0)}
🎯 Kazanma Oranı: %{metrics.get('win_rate', 0):.1f}
📉 Maks Drawdown: %{metrics.get('max_drawdown', 0):.1f}
📊 Güncel Drawdown: %{metrics.get('current_drawdown', 0):.1f}
⚠️ Risk Seviyesi: {metrics.get('risk_level', 'Bilinmiyor').upper()}

🚫 Risk Limitleri:
💸 Maks Günlük Kayıp: {limits.get('max_daily_loss', 0):.2f}
💰 Maks Pozisyon: {limits.get('max_position_size', 0):.2f}
🔄 Maks Eşzamanlı: {limits.get('max_concurrent_trades', 0)}
📊 Maks Günlük İşlem: {limits.get('max_daily_trades', 0)}
📉 Maks Drawdown: %{limits.get('max_drawdown_percentage', 0):.1f}
"""
                
                self.risk_text.delete(1.0, tk.END)
                self.risk_text.insert(1.0, risk_text)
                self._log("✅ Risk raporu güncellendi")
            else:
                self._log(f"❌ Risk raporu alınamadı: {response['error']}")
        except Exception as e:
            self._log(f"❌ Risk raporu hatası: {e}")
    
    def _refresh_history(self) -> None:
        """İşlem geçmişini yenile"""
        limit = int(self.history_limit_var.get() or 20)
        asyncio.run_coroutine_threadsafe(self._async_refresh_history(limit), self.loop)
    
    async def _async_refresh_history(self, limit: int) -> None:
        """Async geçmiş yenileme"""
        try:
            response = await self.api_request('GET', f'/trades/history?limit={limit}')
            if 'error' not in response:
                history = response.get('trade_history', [])
                
                # Tabloyu temizle
                for item in self.history_tree.get_children():
                    self.history_tree.delete(item)
                
                # İşlemleri ekle
                for trade in history:
                    symbol = trade.get('symbol', '')
                    direction = trade.get('direction', '')
                    amount = f"{trade.get('amount', 0):.2f}"
                    profit = f"{trade.get('profit', 0):.2f}"
                    loss = f"{trade.get('loss', 0):.2f}"
                    time = trade.get('start_time', '')[:19]  # Sadece tarih/saat
                    
                    self.history_tree.insert('', 'end', 
                                           values=(symbol, direction, amount, profit, loss, time))
                
                self._log(f"✅ {len(history)} işlem geçmişi yüklendi")
            else:
                self._log(f"❌ İşlem geçmişi alınamadı: {response['error']}")
        except Exception as e:
            self._log(f"❌ İşlem geçmişi hatası: {e}")
    
    def _on_closing(self) -> None:
        """Pencere kapatma"""
        self.running = False
        if self.root:
            self.root.quit()
            self.root.destroy()
    
    async def cleanup(self) -> None:
        """Temizlik işlemleri"""
        try:
            if self.websocket:
                await self.websocket.close()
            if self.session:
                await self.session.close()
            logger.info("GUI Client temizlendi")
        except Exception as e:
            logger.error(f"Temizlik hatası: {e}")