# 11. Worker & Scheduler (TF Hizalama, Zamanlayıcı, Back Pressure)

## 11.1 Tasarım İlkeleri

- **İzolasyon**: Worker anahtarı = (account_id, product, timeframe); birbirinden bağımsızdır
- **TF hizalama**: 1/5/15 dk mum kapanışlarına hizalı tetikleme (TF=1'de kısa aralıklar)
- **Akış**: fetch → features → providers → ensemble → risk/preflight → execute → record
- **Back pressure**: Kuyruklar ve zaman pencereleri ile gecikmiş tiklerin atlanması (drop old), kritik olmayan iş için debounce
- **Hata toleransı**: Veri/bağlantı hatasında skip + uyarı; ardışık hatada pause ve otomatik yeniden deneme

## 11.2 Zamanlama (Scheduling)

### 11.2.1 Tick Üretimi
- **TF=1**: tick_interval_ms=250 ile nazik poll; son kapanışın 0–1s sonrasında tetik
- **TF=5/15**: align_to_tf(ts, tf) ile hizala; kapanıştan sonra grace_ms kadar bekleyip tetik

### 11.2.2 Jitter
- Aynı anda çok worker çarpışmasını azaltmak için tetiklere ±jitter_ms (örn. 50–150ms) ekle

### 11.2.3 Cut off
- entry_cutoff_s aktifse mum kapanışına çok yakın giriş yapılmaz

## 11.3 Back Pressure & Rate Limit

### 11.3.1 Queue
- asyncio.Queue(maxsize=N) ile veri/sinyal/telemetry için ayrık kuyruklar

### 11.3.2 Drop Policy
- Worker, yeni tik geldiğinde eski iş tamamlanmadıysa → eski atanır (skip_reason='overrun')

### 11.3.3 Account Semaphore
- Hesap başına asyncio.Semaphore(R) ile connector çağrılarında RPS sınırı

### 11.3.4 Global Semaphore
- Toplam istek sınırı için opsiyonel

## 11.4 Worker Döngüsü (Aşamalar)

1. **Fetch**: get_candles(product, tf, n=lookback); ekran için son M (örn. 200) bar
2. **Feature**: Parça 7–8 indikatör hesapları; NaN/warm up kontrolü
3. **Providers**: Aktif stratejiler → ProviderVote[]
4. **Ensemble**: combine() → {S, confidence, p̂, dir}
5. **Risk/Preflight**: permit penceresi, eşik, concurrency, cool down
6. **Execute**: OrderExecutor.execute(ctx) (gerekirse)
7. **Record/Publish**: Storage'a yaz ve WS ile UI'a olay/metrik akıt

## 11.5 Hata ve Geri Kazanım

### 11.5.1 Tekil Hata
- Aşamadan bağımsız try/except; skip ve alert

### 11.5.2 Ardışık Hata Sayacı
- k≥Kmax ise worker PAUSED; cooldown_backoff = base·2^k ile tekrar dene

### 11.5.3 Reconcile Tetik
- Boot'ta ve belirli aralıklarla orphan orders kontrolü

## 11.6 Python İskelet — Scheduler

```python
# core/scheduler.py
import asyncio, time
from typing import Dict, Tuple

class Scheduler:
    def __init__(self, worker_factory, tick_ms=250, jitter_ms=100):
        self.worker_factory = worker_factory
        self.tick_ms = tick_ms
        self.jitter_ms = jitter_ms
        self.workers: Dict[Tuple[str,str,int], asyncio.Task] = {}

    def _key(self, acc, prod, tf):
        return (acc, prod, tf)

    async def start_worker(self, acc: str, prod: str, tf: int):
        key = self._key(acc, prod, tf)
        if key in self.workers and not self.workers[key].done():
            return
        
        w = self.worker_factory(acc, prod, tf)
        task = asyncio.create_task(w.run(), name=f"worker:{acc}:{prod}:{tf}")
        self.workers[key] = task

    async def stop_worker(self, acc: str, prod: str, tf: int):
        key = self._key(acc, prod, tf)
        t = self.workers.get(key)
        if t and not t.done():
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass
        del self.workers[key]

    async def stop_all(self):
        for key in list(self.workers.keys()):
            await self.stop_worker(*key)
```

## 11.7 Python İskelet — Worker

```python
# core/worker.py
import asyncio, time, math
from dataclasses import dataclass
from typing import Optional

@dataclass
class WorkerConfig:
    lookback: int = 300
    grace_ms: int = 500
    tick_ms: int = 250
    jitter_ms: int = 100
    entry_cutoff_s: int = 5
    overrun_skip: bool = True

class Worker:
    def __init__(self, account_id, product, timeframe, connector, storage, 
                 indicators, providers, ensemble, risk, executor, cfg: WorkerConfig):
        self.acc = account_id
        self.prod = product
        self.tf = timeframe
        self.cx = connector
        self.db = storage
        self.ind = indicators
        self.providers = providers
        self.ens = ensemble
        self.risk = risk
        self.exec = executor
        self.cfg = cfg
        self._running = True
        self._last_close_slot = None

    def _tf_slot(self, ts_ms: int) -> int:
        tf_ms = self.tf * 60_000
        return ts_ms - (ts_ms % tf_ms)

    async def run(self):
        try:
            while self._running:
                now = int(time.time()*1000)
                slot = self._tf_slot(now)
                
                if self._last_close_slot is None:
                    self._last_close_slot = slot
                
                # Kapanış tetiği (bir önceki slot tamamlandı mı?)
                if slot > self._last_close_slot:
                    await self._on_close(self._last_close_slot)
                    self._last_close_slot = slot
                
                # Kısa tiklerde ara işlemler (TF=1 için daha sık refresh)
                await asyncio.sleep(self.cfg.tick_ms/1000.0)
        except asyncio.CancelledError:
            self._running = False

    async def _on_close(self, close_slot_ms: int):
        # Cut off: Kapanıştan hemen önce girmeyi engelle (uygunsa)
        try:
            # 1) Fetch
            candles = await self.cx.get_candles(self.prod, self.tf, n=self.cfg.lookback)
            if not candles or len(candles) < 30:
                return
            
            # pandas DF'e dönüştür (helper varsayılıyor)
            df = to_dataframe(candles)  # ts_ms, open, high, low, close, volume
            
            # 2) Features
            feats = compute_features(df, self.ind)
            
            # 3) Providers
            votes = []
            for p in self.providers:  # p: StrategyProvider
                v = p.evaluate(df, feats)
                if v is not None:
                    votes.append(v)
            
            if not votes:
                return
            
            # 4) Ensemble
            comb = self.ens.combine(votes)
            direction = 'call' if comb['dir']>0 else ('put' if comb['dir']<0 else None)
            if not direction:
                return
            
            # 5) Risk/Preflight
            payout = await self.cx.get_current_win_rate(self.prod)
            ctx = build_trade_ctx(self.acc, self.prod, self.tf, direction, payout, comb)
            if not self.risk.enter_allowed(ctx):
                return
            
            # 6) Execute
            result = await self.exec.execute(ctx)
            
            # 7) Record/Publish (executor zaten yazar; burada ek metrik/alert üretilebilir)
        except Exception as e:
            # log + alert
            return
```

## 11.8 UI Eşlemesi

- **Ayarlar → Motor**: tick_ms, grace_ms, jitter_ms, entry_cutoff_s, lookback
- **Durum**: Worker listesi (acc, prod, tf, state=RUNNING/PAUSED), son kapanış zamanı, ardışık hata sayacı
- **Kontrol**: Worker başlat/durdur; ürün/TF bazında hızlı aktivasyon

## 11.9 Test Planı

- **Fonksiyonel**: TF hizalaması doğru; kapanış tetiklerinin kaçmaması
- **Overrun**: Uzun süren bar işleminde bir sonraki tetikte skip; sistem tıkanmıyor
- **Rate limit**: Semaforla istek sayısı sınırlanıyor; 429 testlerinde backoff çalışıyor
- **Çoklu hesap**: 4 hesapla paralel workers; izolasyon korunuyor
- **Dayanıklılık**: Ardışık hata sonrası PAUSED → backoff → RUNNING döngüsü

## 11.10 Kabul Kriterleri

- Worker/scheduler iskeleti, TF hizalama ve back pressure politikaları tanımlandı
- Rate limit semaforları ve drop old stratejisi belirlendi
- Hata sayacı, pause/backoff ve UI eşleşmesi dokümante edildi
- Çoklu hesap paralel çalışmada stabilite hedefleri net
