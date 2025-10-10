# 10. Order Executor & Idempotency (Durum Makinesi, Retry, Latency)

## 10.1 Tasarım Hedefleri

- **At most once finansal yan etki**: Aynı işlem için çift emir yok
- **İdempotensi**: client_request_id ile gateway/connector düzeyinde tekrarların yutulması
- **Belirsizlikte güvenlik**: Timeout/bağlantı kesilmesinde önce sorgula, emin değilse abort + reconcile
- **Gözlemlenebilirlik**: Segment bazlı latency ölçümü, durum makinesi olayları, structured log

## 10.2 Durum Makinesi

```
IDLE
└─prepare(ctx)──────────────────────────▶ PREPARE
PREPARE
├─ preflight_ok? ──no──▶ ABORT (reason=preflight)
└─ yes
   └─ place() ─ack→ PLACED
      └─ timeout/5xx → PLACE_RETRY (bounded)
PLACED
├─ confirm() → SETTLED(win/lose/abort)
├─ early_close() (ops.) → CANCELED
└─ timeout → CONFIRM_RETRY (bounded)
SETTLED | CANCELED | ABORT → IDLE
```

**Preflight**: Son anda payout permit penceresi, confidence ≥ win_threshold, concurrency lock, cool down, latency guard yeniden kontrol edilir.

## 10.3 İdempotency Tasarımı

### 10.3.1 Client Request ID
```
client_request_id = f"{account_id}:{product}:{tf}:{entry_slot}:{uuid8}"
```
- entry_slot: TF hizalı zaman damgası (örn. 2025 10 06T12:30:00Z@tf=1)
- Aynı işlemi tekrar denerken aynı client_request_id kullanılır

### 10.3.2 Storage
- orders.client_req_id UNIQUE (Parça 5)

### 10.3.3 Retry Sonrası Eşleşme
- confirm_by_client_req_id() uç noktası varsa kullan
- Yoksa reconcile() periodyk görevi client_req_id ile tamamlar

## 10.4 Retry Matrisi (Özet)

| Aşama | Hata | Politika |
|-------|------|----------|
| place() | 401/403 | Abort (yeniden login + sonraki işlemler için) |
| place() | 429/5xx/timeout | Retry n≤3, backoff=0.25·2^n + jitter; aynı client_req_id |
| confirm() | timeout/5xx | Retry n≤6, aralık 1–5s artan |
| confirm() | 404 (bulunamadı) | Önce client_req_id ile sorgula; hala yoksa Abort+reconcile |

**Not**: Finansal at most once için place() yalnızca belirsizlikte tekrar eder; zaten "fail" yanıtı geldiyse tekrar etmez.

## 10.5 Latency Ölçümü (Segmentler)

- **t_prepare**: Preflight süresi
- **t_place_http**: Connector çağrısı round trip
- **t_confirm_wait**: Kapanışa kadar geçen süre (poll/WS)
- **latency_ms (sonuç)**: t_place_http
- **Metrikler**: metrics(scope='acc:<id>', key='latency_ms', ...) ve hatalarda error_rate

## 10.6 Concurrency Lock & Cut off

- **Lock anahtarı**: (account_id, product, timeframe) → asyncio.Lock
- **Kural**: 1/5/15 kendi içinde tek açık işlem; farklı TF'lerde paralel mümkündür
- **Giriş cut off (opsiyonel)**: TF=1'de son X sn içinde yeni giriş yok (ayar: entry_cutoff_s, default 5s)

## 10.7 Preflight Kontrolleri (son saniye)

1. payout ∈ [permit_min, permit_max]
2. confidence ≥ win_threshold
3. Concurrency lock boş
4. Cool down kapalı
5. risk.enter_allowed(ctx) == True
6. latency_estimate ≤ abort_ms

## 10.8 Python İskeleti

```python
# core/executor.py
import asyncio, time, uuid
from dataclasses import dataclass
from typing import Optional

@dataclass
class TradeCtx:
    account: str
    product: str
    timeframe: int  # 1,5,15
    direction: str  # 'call'|'put'
    payout: float  # % (örn. 90.0)
    confidence: float
    prob_win: float
    win_threshold: float
    permit_min: float
    permit_max: float
    balance: float

class OrderExecutor:
    def __init__(self, connector, storage, risk_engine, locks, confirm_timeout_s: int = 120):
        self.cx = connector
        self.db = storage
        self.risk = risk_engine
        self.locks = locks
        self.confirm_timeout_s = confirm_timeout_s

    def _entry_slot(self, timeframe: int) -> int:
        now = int(time.time()*1000)
        tf_ms = timeframe * 60_000
        return now - (now % tf_ms)

    async def execute(self, ctx: TradeCtx):
        # Preflight
        if not (ctx.permit_min <= ctx.payout <= ctx.permit_max):
            return {"status":"skipped","reason":"permit"}
        if ctx.confidence < ctx.win_threshold:
            return {"status":"skipped","reason":"confidence"}
        
        key = (ctx.account, ctx.product, ctx.timeframe)
        lock = self.locks.setdefault(key, asyncio.Lock())
        if lock.locked():
            return {"status":"skipped","reason":"concurrency"}
        
        async with lock:
            if not self.risk.enter_allowed(ctx):
                return {"status":"skipped","reason":"risk_guard"}
            
            amount = self.risk.compute_amount(ctx)
            entry_slot = self._entry_slot(ctx.timeframe)
            client_req_id = f"{ctx.account}:{ctx.product}:{ctx.timeframe}:{entry_slot}:{uuid.uuid4().hex[:8]}"
            
            # PLACE
            t0 = time.time()
            try:
                ack = await self.cx.place_order(
                    product=ctx.product, amount=amount, direction=ctx.direction,
                    timeframe=ctx.timeframe, client_req_id=client_req_id
                )
            except Exception as e:
                # belirsizlikte tekrar: aynı client_req_id ile
                for n in range(1,4):
                    await asyncio.sleep(0.25*(2**n))
                    try:
                        ack = await self.cx.place_order(
                            product=ctx.product, amount=amount, direction=ctx.direction,
                            timeframe=ctx.timeframe, client_req_id=client_req_id
                        )
                        break
                    except Exception:
                        ack = None
                
                if ack is None:
                    return {"status":"abort","reason":"place_failed"}
            
            t1 = time.time()
            
            # Persist ORDER
            order_id = ack.get("order_id")
            await self.db.save_order({
                "id": order_id,
                "ts_open_ms": int(t0*1000),
                "account_id": ctx.account,
                "product": ctx.product,
                "timeframe": ctx.timeframe,
                "direction": ctx.direction,
                "amount": amount,
                "client_req_id": client_req_id,
                "permit_win_min": ctx.permit_min,
                "permit_win_max": ctx.permit_max,
            })
            
            # Confirm (poll)
            deadline = time.time() + self.confirm_timeout_s
            res = None
            while time.time() < deadline:
                try:
                    res = await self.cx.confirm_order(order_id)
                    if res.get("status") in ("win","lose","abort","canceled"):
                        break
                except Exception:
                    await asyncio.sleep(1.0)
                await asyncio.sleep(1.0)
            
            if res is None:
                return {"status":"abort","reason":"confirm_timeout"}
            
            # Persist RESULT
            await self.db.save_result({
                "order_id": order_id,
                "ts_close_ms": res.get("ts_close_ms"),
                "status": res.get("status"),
                "pnl": float(res.get("pnl", 0.0)),
                "duration_ms": int(res.get("ts_close_ms", 0) - int(t0*1000)),
                "latency_ms": int((t1 - t0)*1000)
            })
            
            # Risk feedback
            self.risk.on_result(ctx, pnl=float(res.get("pnl", 0.0)), 
                               is_win=(res.get("status") == "win"))
            
            return {"status": res.get("status"), "order_id": order_id}
```

## 10.9 Telemetry & Log Olayları

- **trade_events**: PREPARE, PLACE_OK, PLACE_RETRY, CONFIRM_OK, CONFIRM_TIMEOUT, SETTLED_WIN/LOSE/ABORT, ABORT_REASON
- **Latency dağılımı**: p50/p90/p99, retry sayı histogramı, concurrency skip sayısı

## 10.10 Reconcile (Boot'ta Kurtarma)

- orders içinde results olmayan kayıtları topla → connector'dan order_id / client_req_id ile durumu sor
- Bulunursa results ekle; bulunamazsa status='abort' ile kapat ve kullanıcıya uyarı

## 10.11 UI Eşlemesi

- **Ayarlar → Yürütme**: confirm_timeout_s, entry_cutoff_s, retry_max_place, retry_max_confirm
- **Dashboard**: Anlık durum (FSM state), latency, retry sayısı; son işlem özet
- **Loglar**: trade.log içinde redakte edilmiş olaylar; system.log hata/sistem olayları

## 10.12 Test Planı

- **Birim**: FSM geçişleri, concurrency lock, cut off, idempotent client_req_id
- **Entegrasyon**: MockConnector ile place/confirm retry senaryoları; belirsizlikte tek emir
- **Dayanıklılık**: Boot'ta reconcile, ağ kesintisi, 429/5xx fırtınası, bakım modu
- **Zamanlama**: TF hizalama ve entry_cutoff_s sınaması

## 10.13 Kabul Kriterleri

- İdempotent, at most once yürütme hattı tanımlandı ve iskelet kodu yazıldı
- FSM, retry matrisi, latency ölçümü, concurrency lock ve reconcile net
- UI ve telemetry eşlemeleri belirlendi
