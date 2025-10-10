# 6. Connector Tasarımı (async) & Mock (Windows 10/11, 4 Hesap)

## 6.1 Kapsam ve Hedefler

- **Per Account Connector**: Her hesap için bağımsız Connector örneği (oturum/cookie/token izole)
- **HTTP + WS**: Uygunsa WebSocket ile akış (quotes/olaylar); aksi durumda periyodik poll
- **İşlevler**: login, refresh_token, get_candles, get_quote, get_current_win_rate (payout), place_order, confirm_order, heartbeat
- **İdempotensi**: client_request_id ile at most once emir davranışı
- **Rate limit**: Throttling + exponential backoff + jitter
- **Hata sınıfları**: Auth/Throttle/Maintenance/Network/Format ayrımı

## 6.2 API Sözleşmesi (Protocol)

```python
# core/connector/interface.py
from typing import List, Dict, Any, Protocol, Optional

class Connector(Protocol):
    account_id: str
    
    async def login(self, username: str, password: str, otp: Optional[str] = None) -> None: ...
    async def refresh_token(self) -> None: ...
    async def get_candles(self, product: str, timeframe: int, n: int = 200, 
                         until_ms: Optional[int] = None) -> List[Dict[str, Any]]: ...
    async def get_current_win_rate(self, product: str) -> float: ...  # payout in [0,100]
    async def get_quote(self, product: str) -> Dict[str, Any]: ...  # {ts, bid, ask, mid}
    async def place_order(self, *, product: str, amount: float, direction: str, 
                         timeframe: int, client_req_id: str) -> Dict[str, Any]: ...
    async def confirm_order(self, order_id: str) -> Dict[str, Any]: ...  # {status, pnl, ts_close_ms}
    async def cancel_order(self, order_id: str) -> Dict[str, Any]: ...  # if platform supports early close
    async def heartbeat(self) -> None: ...
    async def close(self) -> None: ...
```

## 6.3 Veri Sözleşmeleri (pydantic)

```python
# core/connector/models.py
from pydantic import BaseModel, Field
from typing import Optional

class Candle(BaseModel):
    ts_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

class Quote(BaseModel):
    ts_ms: int
    bid: float
    ask: float
    
    @property
    def mid(self):
        return (self.bid + self.ask) / 2

class OrderAck(BaseModel):
    order_id: str
    client_req_id: str
    ts_open_ms: int

class OrderResult(BaseModel):
    order_id: str
    status: str  # win | lose | abort | canceled
    pnl: float
    ts_close_ms: int
    latency_ms: int
```

## 6.4 Olymp Connector İskeleti (gerçek uçsuz)

```python
# core/connector/olymp.py
import asyncio, time, aiohttp
from typing import Any, Dict, List, Optional
from .interface import Connector
from .models import Candle, Quote, OrderAck, OrderResult

class OlympConnector(Connector):
    def __init__(self, account_id: str, base_url: str, ws_url: Optional[str] = None, 
                 timeout_s: int = 10):
        self.account_id = account_id
        self.base_url = base_url.rstrip('/')
        self.ws_url = ws_url
        self._session: Optional[aiohttp.ClientSession] = None
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._rate_sem = asyncio.Semaphore(8)  # basit throttling
        self._lock = asyncio.Lock()  # kritik bölgeler için
        self._ws = None
        self._timeout = aiohttp.ClientTimeout(total=timeout_s)

    async def _http(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        async with self._rate_sem:
            if not self._session:
                self._session = aiohttp.ClientSession(timeout=self._timeout)
            
            headers = kwargs.pop('headers', {})
            if self._access_token:
                headers['Authorization'] = f'Bearer {self._access_token}'
            
            url = f"{self.base_url}{path}"
            async with self._session.request(method, url, headers=headers, **kwargs) as r:
                if r.status in (401, 403):  # token yenileme dene (tek sefer)
                    await self.refresh_token()
                    headers['Authorization'] = f'Bearer {self._access_token}' if self._access_token else ''
                    async with self._session.request(method, url, headers=headers, **kwargs) as r2:
                        r2.raise_for_status()
                        return await r2.json()
                
                r.raise_for_status()
                return await r.json()

    async def login(self, username: str, password: str, otp: Optional[str] = None) -> None:
        # PLACEHOLDER: Gerçek uçlar eklenecek (resmî/izinli ise)
        payload = {"username": username, "password": password}
        if otp:
            payload["otp"] = otp
        
        # resp = await self._http('POST', '/auth/login', json=payload)
        # self._access_token = resp['access_token']; self._refresh_token = resp.get('refresh_token')
        self._access_token = "DUMMY"

    async def refresh_token(self) -> None:
        if not self._refresh_token:
            # fallback: yeniden login gerekebilir (uygun değilse abort)
            return
        
        # resp = await self._http('POST', '/auth/refresh', json={"refresh_token": self._refresh_token})
        # self._access_token = resp['access_token']

    async def get_candles(self, product: str, timeframe: int, n: int = 200, 
                         until_ms: Optional[int] = None) -> List[Dict[str, Any]]:
        # resp = await self._http('GET', f'/market/candles?symbol={product}&tf={timeframe}&n={n}&until={until_ms or 0}')
        # return resp['candles']
        return []

    async def get_current_win_rate(self, product: str) -> float:
        # resp = await self._http('GET', f'/market/payout?symbol={product}')
        # return float(resp['payout'])
        return 90.0

    async def get_quote(self, product: str) -> Dict[str, Any]:
        # resp = await self._http('GET', f'/market/quote?symbol={product}')
        # return resp
        return {"ts": int(time.time()*1000), "bid": 1.0, "ask": 1.0}

    async def place_order(self, *, product: str, amount: float, direction: str, 
                         timeframe: int, client_req_id: str) -> Dict[str, Any]:
        # resp = await self._http('POST', '/orders', json={"symbol": product, "amount": amount, 
        #                                                  "side": direction, "tf": timeframe, 
        #                                                  "client_req_id": client_req_id})
        # return resp
        return {"order_id": f"SIM-{int(time.time()*1000)}", 
                "client_req_id": client_req_id, 
                "ts_open_ms": int(time.time()*1000)}

    async def confirm_order(self, order_id: str) -> Dict[str, Any]:
        # resp = await self._http('GET', f'/orders/{order_id}')
        # return resp
        return {"order_id": order_id, "status": "win", "pnl": 0.9, 
                "ts_close_ms": int(time.time()*1000)+60000, "latency_ms": 150}

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        # resp = await self._http('POST', f'/orders/{order_id}/cancel')
        # return resp
        return {"order_id": order_id, "status": "canceled"}

    async def heartbeat(self) -> None:
        # await self._http('GET', '/ping')
        return

    async def close(self) -> None:
        if self._session:
            await self._session.close()
        self._session = None
```

## 6.5 Çoklu Hesap Bağlantı Yöneticisi

```python
# core/connector/manager.py
from typing import Dict
from .olymp import OlympConnector

class ConnectorManager:
    def __init__(self):
        self._by_account: Dict[str, OlympConnector] = {}

    async def ensure(self, account_id: str, base_url: str, **kw) -> OlympConnector:
        c = self._by_account.get(account_id)
        if not c:
            c = OlympConnector(account_id, base_url, **kw)
            self._by_account[account_id] = c
        return c

    async def login_all(self, creds: Dict[str, Dict[str, str]]):
        # creds: {acc_id: {username, password, otp?}}
        for acc, c in self._by_account.items():
            u = creds[acc]['username']
            p = creds[acc]['password']
            otp = creds[acc].get('otp')
            await c.login(u, p, otp)

    async def close_all(self):
        for c in self._by_account.values():
            await c.close()
```

## 6.6 Rate Limit ve Retry Tasarımı

- **İstek kuyruğu**: Connector içi semaphore (_rate_sem) + asyncio.Queue ile sınırlama
- **Backoff**: 429/5xx ve TimeoutError'da base * (2^n) + jitter; n_max = 5; base = 0.25s; jitter ∈ [0, 0.1s]
- **Bakım durumu**: Belirli hata kodlarında read only moda geç; emir fonksiyonları geçici devre dışı

## 6.7 İdempotensi ve Emir Güvenliği

- Her place_order çağrısında benzersiz client_request_id; Storage'da orders.client_req_id UNIQUE
- confirm_order sonucu alınmadan tekrar place_order yapılmaz (Order FSM)
- Çift yanıt durumlarında client_req_id üzerinden eşleşme ve yutma (duplicate ignore)

## 6.8 Hata Sınıflandırması & Haritalama

- **AuthError** (401/403), **ThrottleError** (429), **MaintenanceError** (503/temporarily unavailable), **NetworkError** (timeout/connection reset), **FormatError** (parse/json), **BusinessRuleError** (permit dışı, concurrency, kural ihlali)
- Her hata telemetry'de sayılır; UI'ya alert olarak aktarılır

## 6.9 Zamanlama ve Zaman Uyumlaması

- Tüm zamanlar UTC ms; UI'da Europe/Istanbul gösterimi
- TF hizalama: align_to_tf(ts, tf_min) yardımcı fonksiyonu; mum kapanışında tetikleme
- Sistem saat kayması için opsiyonel NTP drift kontrolü (uyarı üretir)

## 6.10 Güvenlik Notları

- TLS zorunlu, sertifika doğrulama açık; host allow list opsiyonel
- Token/çerezler profiles/accX/ altında şifreli; loglarda maskelenir
- Scraping/otomasyon yok; yalnızca izinli/yayımlanmış uçlar kullanılacak

## 6.11 MockConnector (Test & Paper)

```python
# core/connector/mock.py
import math, random, time
from typing import Dict, Any, List, Optional

class MockConnector:
    def __init__(self, account_id: str, seed: int = 42):
        self.account_id = account_id
        random.seed(seed)
        self._price = 1.0000

    async def login(self, username: str, password: str, otp: Optional[str] = None):
        return

    async def get_candles(self, product: str, timeframe: int, n: int = 200, 
                         until_ms: Optional[int] = None) -> List[Dict[str, Any]]:
        # Basit sinüzoidal + gürültü ile OHLCV üretimi
        now = int(time.time()*1000)
        out = []
        p = self._price
        
        for i in range(n):
            t = now - i*timeframe*60_000
            base = math.sin(i/10.0)*0.001
            noise = (random.random()-0.5)*0.0005
            close = max(0.5, p + base + noise)
            high = max(close, p) + 0.0002
            low = min(close, p) - 0.0002
            
            out.append({"ts_ms": t, "open": p, "high": high, "low": low, 
                       "close": close, "volume": random.randint(100,1000)})
            p = close
        
        self._price = p
        return list(reversed(out))

    async def get_current_win_rate(self, product: str) -> float:
        return 90.0 + (random.random()-0.5)*4  # %88–%92 çevresi

    async def get_quote(self, product: str) -> Dict[str, Any]:
        self._price += (random.random()-0.5)*0.0003
        return {"ts": int(time.time()*1000), "bid": self._price-0.0001, 
                "ask": self._price+0.0001}

    async def place_order(self, *, product: str, amount: float, direction: str, 
                         timeframe: int, client_req_id: str) -> Dict[str, Any]:
        return {"order_id": f"MOCK-{client_req_id}", 
                "client_req_id": client_req_id, 
                "ts_open_ms": int(time.time()*1000)}

    async def confirm_order(self, order_id: str) -> Dict[str, Any]:
        # Basit kural: son hareket yönüne göre win/lose simüle et
        win = random.random() > 0.45
        pnl = 0.9 if win else -1.0
        return {"order_id": order_id, "status": "win" if win else "lose", 
                "pnl": pnl, "ts_close_ms": int(time.time()*1000)+60_000, 
                "latency_ms": 120}

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return {"order_id": order_id, "status": "canceled"}

    async def heartbeat(self) -> None:
        return
```

## 6.12 Test Planı

- **Birim**: Mock ile login/get_candles/get_quote/get_current_win_rate/place/confirm çağrıları; idempotent client_req_id testi
- **Hata Enjeksiyonu**: 401/429/503/timeout simülasyonları; backoff ve mod geçişleri
- **Çoklu Hesap**: 4 hesap paralel login + data çekme + order akışı; profil izolasyon doğrulaması
- **Performans**: 100+ eşzamanlı (acc,prod,tf) örneğinde dakika başına istek sayısı ve ort. latency

## 6.13 Kabul Kriterleri

- Connector sözleşmeleri ve iskele kod hazır
- Çoklu hesap yönetimi, rate limit, backoff, idempotensi ve hata sınıflandırması tanımlı
- MockConnector ile paper/backtest için çalışır demolar yapılabilir
- Gerçek uç noktalar yalnız resmî/izinli olduğunda eklenecek; scraping/atlatma yok
