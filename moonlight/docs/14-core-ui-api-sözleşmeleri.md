# 14. Core↔UI API (REST/WS) Sözleşmeleri & Şema (Windows Loopback)

## 14.1 Tasarım İlkeleri

- **Yerel ve güvenli**: Varsayılan bağlayıcı http://127.0.0.1:8750 ve ws://127.0.0.1:8751 (opsiyonel TLS: https/wss)
- **Basit kimlik**: Loopback üzerinde auth gereksiz; istenirse X-API-Key başlığı ile tek anahtar
- **Sürümleme**: api_version (örn. 1.0), schema_version ve config_version alanları
- **İdempotent işlemler**: Emir işlemleri client_request_id ile tekrara dayanıklı
- **Sözleşme önce**: Açık OpenAPI çıktısı (ops.) + UI tarafında tip güvenli istemci
- **Zaman & Yerel ayar**: API tüm zamanları UTC ms döndürür; UI sistem saat diliminde (Europe/Istanbul) gösterir

## 14.2 REST Uçları (taslak)

### 14.2.1 GET /status
**Yanıt**:
```json
{
  "api_version": "1.0",
  "service": {"state":"running","uptime_s": 12345, "tz":"UTC"},
  "core": {"workers": 42, "cpu_pct": 18.2, "mem_mb": 512},
  "accounts": [{"id":"acc1","state":"connected"},{"id":"acc2","state":"disconnected"}],
  "ws": {"metrics":"connected","alerts":"connected"}
}
```

### 14.2.2 GET /accounts
**Liste + durum bilgisi döner**:
```json
[{"id":"acc1","username_mask":"u***@mail","profile_store":"profiles/acc1/","state":"connected","last_login_ms":1728291000000,"balance":1200.50}]
```

### 14.2.3 POST /accounts/login
**Girdi**:
```json
{ "id":"acc1", "otp":"123456" }
```
(OTP opsiyonel). Parola keyring'den çekilir.

**Çıktı**:
```json
{ "ok": true, "state": "connected" }
```

### 14.2.4 GET /workers
**Aktif (account, product, timeframe) listesi ve durumları**:
```json
[{"account":"acc1","product":"EURUSD","tf":1,"state":"RUNNING","last_close_ms":1728291600000}]
```

### 14.2.5 POST /start / POST /stop
**Girdi (örnek, kapsam bazlı)**:
```json
{"scope":"global"}
{"scope":"account","account":"acc1"}
{"scope":"worker","account":"acc1","product":"EURUSD","tf":1}
```

**Çıktı**:
```json
{ "ok": true, "affected": [ ... ] }
```

### 14.2.6 GET /products
**UI ağacı için ürün & TF yapılandırması döner** (aktif/pasif, eşikler, permit aralığı, lot modu)

### 14.2.7 PUT /config
**Hot reload alanları anında uygulanır; diğerleri kontrollü restart ister**

**Girdi**: partial (yalnız değişen alanlar) veya full (tam dosya)

**Çıktı**:
```json
{"applied":["products[EURUSD].timeframes[1].win_threshold"],"restarted":["workers:acc1:EURUSD:1"],"warnings":["win_threshold < ensemble_threshold"]}
```

### 14.2.8 GET /orders / GET /orders/{id}
**Filtreler**: from_ms,to_ms,account,product,tf,status

### 14.2.9 POST /orders/cancel
**Platform destekliyorsa erkenden kapama isteği**

**Girdi**:
```json
{ "order_id":"..." }
```
→ not: onay broker kabiliyetine bağlı

### 14.2.10 GET /logs / GET /metrics
**Son tail satırı veya since_ms'ten itibaren özet metrikler**

### 14.2.11 POST /reconcile
**Boot'taki otomatik sürece ek olarak manuel tetik**

### 14.2.12 Hata Zarfı (tüm uçlar)
```json
{
  "error": {
    "code": "CONCURRENCY_BLOCK",
    "message": "(acc,product,tf) başına tek açık işlem kuralı",
    "details": {"account":"acc1","product":"EURUSD","tf":1}
  }
}
```

**Standart kodlar**: VALIDATION, AUTH, THROTTLE, MAINTENANCE, NETWORK, BUSINESS_RULE

## 14.3 WebSocket Kanalları

- **Endpoint**: ws://127.0.0.1:8751/ws (sorgu: ?topic=metrics|trade_updates|alerts|logs)
- **Kalp atışı**: { "type":"ping" } ↔ { "type":"pong" } her 20sn
- **Yeniden bağlanma**: UI exponential backoff (250ms→4s), durum LED'i güncellenir

### 14.3.1 metrics örnekleri
```json
{"topic":"metrics","ts_ms":1728291660000,"scope":"acc:acc1","key":"win_rate_1m","value":0.73}
{"topic":"metrics","ts_ms":1728291660000,"scope":"prod:EURUSD","key":"latency_p50_ms","value":140}
{"topic":"metrics","ts_ms":1728291660000,"scope":"global","key":"pnl_day","value":2.4}
```

### 14.3.2 trade_updates
```json
{"topic":"trade_updates","event":"NEW","order_id":"SIM-1728291600123","account":"acc1","product":"EURUSD","tf":1,"amount":10.0,"payout":0.93,"p_hat":0.76}
{"topic":"trade_updates","event":"SETTLED","order_id":"SIM-1728291600123","status":"win","pnl":0.9,"latency_ms":120,"ts_close_ms":1728291660000}
```

### 14.3.3 alerts
```json
{"topic":"alerts","level":"WARN","code":"DAILY_LOSS_NEAR","message":"Günlük kayıp limitine yaklaşıldı","account":"acc1","pnl_day":-4.2}
{"topic":"alerts","level":"ERROR","code":"CIRCUIT_BREAKER_TRIP","message":"Ardışık kayıp limiti aşıldı"}
```

### 14.3.4 logs
```json
{"topic":"logs","chan":"trade","level":"INFO","msg":"PLACE_OK","order_id":"SIM-...","masked":"u***@mail"}
```

## 14.4 Güvenlik & Ağ Politikaları

- **Loopback zorunlu**: Varsayılan olarak yalnız 127.0.0.1 dinlenir. İstenirse UI'dan yalnızca yerel bayrağı kaldırılıp IP allow list ile sınırlanır
- **TLS (ops.)**: Self signed sertifika desteklenir; UI'da güven düğümü. Windows Firewall'da özel kural önerilir
- **CORS**: Kapalı; UI native istemci olduğu için gerekmez
- **Rate limit**: REST 30 RPS, WS 1 kanal başına 10 msg/sn (UI yeterlidir)
- **PII maskesi**: Kullanıcı adı/e-posta/OTP log ve ws'de maskeleme (u***@mail)

## 14.5 Versiyonlama ve Uyumluluk

- **GET /status** → { "api_version": "1.0", "schema_version": "2025-10-01", "config_version": "1.0.0" }
- **Kırıcı değişikliklerde**: Ana sürüm artar; UI sürüm kontrolü uyarı verir ve uyum moduna geçer (salt okunur)

## 14.6 OpenAPI & İstemci (opsiyonel)

- **Core servis başlatıldığında**: GET /openapi.json üretir
- **UI tarafında**: openapi-generator ile Dart istemci kodu üretilebilir (isteğe bağlı). Elle yazılmış hafif istemci de yeterli

## 14.7 Örnek Sunucu İskeleti (FastAPI)

```python
# core/api/server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import JSONResponse

app = FastAPI(title="MoonLight Core API", version="1.0")
API_KEY = None  # opsiyonel

@app.get("/status")
async def status(x_api_key: str | None = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        return JSONResponse(status_code=401, content={"error":{"code":"AUTH","message":"bad key"}})
    return {"api_version":"1.0","service":{"state":"running","uptime_s":0,"tz":"UTC"}}

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_text()
            if msg == '{"type":"ping"}':
                await ws.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
```

## 14.8 Test Planı (API)

- **Birlikte çalışabilirlik**: UI tüm uçları çağırır; 200/4xx/5xx durumları doğru ele alınır
- **Yük**: GET /status 50 RPS, metrics WS 10 msg/sn; UI kare hızında gecikme yok
- **Hata zarfı**: Tüm hata senaryoları standardize dönüyor (JSON)
- **Güvenlik**: Loopback dışında bağlanma başarısız; API anahtarı açıkken yanlış anahtar → 401

## 14.9 Kabul Kriterleri

- REST ve WS sözleşmeleri tanımlandı ve örnek payload'lar verildi
- Hata zarfı, sürümleme, güvenlik ve oran sınırlama net
- UI için gereken tüm endpoint ve kanallar mevcut; idempotency ve loopback ilkeleri korunuyor
