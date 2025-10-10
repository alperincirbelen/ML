# 12. Strateji Kataloğu (Plugin Sistemi) & Sinyal Sağlayıcıları

## 12.1 Mimarinin İlkeleri

- **Gevşek Bağlılık**: Stratejiler core/strategies/providers/*.py altında bağımsız modüllerdir
- **Sözleşme**: Tüm stratejiler tek bir Provider arayüzünü uygular; registry üzerinden keşfedilir
- **Konfigüre Edilebilirlik**: Varsayılan parametreler → config/UI ile ürün/TF bazında override
- **İzlenebilirlik**: Her evaluate çağrısı meta sözlüğünde katkı gerekçesini taşır (örn. {"ema20":..., "rsi14":...})
- **Isınma/Warm up**: Gerekli bar sayısı strateji tarafından bildirilecek; yetersizse vote=0 döner

## 12.2 Dizin Yapısı

```
core/strategies/
├── base.py              # Provider arayüzü & yardımcılar
├── registry.py          # Keşif & kayıt
└── providers/
    ├── ema_rsi.py       # (ID: 5/6/7/8/9/10 varyantları)
    ├── vwap_rvol.py     # (ID: 15..20 varyantları)
    ├── st_adx.py        # (ID: 25..30 varyantları)
    ├── keltner_break.py # (ID: 35..40 varyantları)
    ├── bb_walk.py       # (ID: 45..50 varyantları)
    ├── ema_cross.py     # (ID: 14, 9/21 EMA)
    └── triple_ma.py     # (ID: 34)
    # ileride: ichimoku_trend, gmmaz, pivot_reversal vb.
```

## 12.3 Provider Arayüzü

```python
# core/strategies/base.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import pandas as pd
from core.ensemble import ProviderVote

@dataclass
class ProviderContext:
    product: str
    timeframe: int
    payout: float

@dataclass
class ProviderConfig:
    id: int
    name: str
    group: str
    params: Dict[str, Any] = field(default_factory=dict)

class StrategyProvider:
    cfg: ProviderConfig
    
    def warmup_bars(self) -> int:
        """Dönmesi gereken minimum bar sayısı."""
        raise NotImplementedError
    
    def evaluate(self, df: pd.DataFrame, feats: Dict[str, Any], ctx: ProviderContext) -> Optional[ProviderVote]:
        """
        df: ts_ms, open, high, low, close, volume
        feats: Parça 7-8'den hesaplanmış Series'ler veya tekil değerler
        return ProviderVote(pid=self.cfg.id, vote=-1|0|1, score=float)
        """
        raise NotImplementedError
```

## 12.4 Registry (Keşif/Kayıt)

```python
# core/strategies/registry.py
from typing import Dict, Type, List
import importlib, pkgutil

_REG: Dict[int, Type[StrategyProvider]] = {}

def register(pid: int):
    def deco(cls: Type[StrategyProvider]):
        _REG[pid] = cls
        return cls
    return deco

def load_all():
    import core.strategies.providers as pkg
    for m in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        importlib.import_module(m.name)

def build(pid: int, **kw) -> StrategyProvider:
    cls = _REG[pid]
    return cls(**kw)

def all_metadata() -> List[dict]:
    return [getattr(v, 'META', {"id": k}) | {"id": k} for k,v in _REG.items()]
```

## 12.5 Örnek Sağlayıcılar (Mantık + Parametreler)

### 12.5.1 EMA Trend + RSI (ID 5/6/7/8/9/10 varyantları)

**Mantık**: EMA(20) > EMA(50) ve RSI14 > 55 → long oyu (vote=+1). Tersi EMA20 < EMA50 & RSI14 < 45 → short (vote=-1). Aksi 0.

**Skor**: score = w1·slope(EMA20) + w2·(RSI14−50)/50 (normalize); tavan ±s_cap.

**Parametreler**: ema_fast=20, ema_slow=50, rsi_len=14, rsi_up=55, rsi_dn=45, w1=1.0, w2=0.7.

**Warm up**: max(ema_slow, rsi_len)+5.

**Not**: Kullanıcının tablodaki SL/TP referansları FTT'de oturum risk politikasıyla karşılanır (Parça 10).

```python
# core/strategies/providers/ema_rsi.py
from .base import StrategyProvider, ProviderConfig, ProviderContext
from core.ensemble import ProviderVote
from core.indicators.basic import ema, rsi
import pandas as pd

class EMA_RSI(StrategyProvider):
    META = {"name":"EMA Trend + RSI", "group":"trend+osc"}
    
    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg
        p = self.cfg.params
        self.ema_fast = p.get('ema_fast', 20)
        self.ema_slow = p.get('ema_slow', 50)
        self.rsi_len = p.get('rsi_len', 14)
        self.rsi_up = p.get('rsi_up', 55)
        self.rsi_dn = p.get('rsi_dn', 45)
        self.w1 = p.get('w1', 1.0)
        self.w2 = p.get('w2', 0.7)
    
    def warmup_bars(self) -> int:
        return max(self.ema_slow, self.rsi_len) + 5
    
    def evaluate(self, df: pd.DataFrame, feats, ctx: ProviderContext):
        close = df['close']
        e20 = ema(close, self.ema_fast)
        e50 = ema(close, self.ema_slow)
        r = rsi(close, self.rsi_len)
        
        if len(close) < self.warmup_bars():
            return None
        
        trend_up = e20.iloc[-1] > e50.iloc[-1]
        trend_dn = e20.iloc[-1] < e50.iloc[-1]
        vote = 0
        
        if trend_up and r.iloc[-1] > self.rsi_up:
            vote = 1
        elif trend_dn and r.iloc[-1] < self.rsi_dn:
            vote = -1
        
        if vote == 0:
            return ProviderVote(pid=self.cfg.id, vote=0, score=0.0)
        
        slope = (e20.iloc[-1] - e20.iloc[-3]) / max(1e-6, e20.iloc[-3])
        score = self.w1 * slope + self.w2 * ((r.iloc[-1] - 50.0)/50.0)
        
        return ProviderVote(pid=self.cfg.id, vote=vote, score=float(score))
```

### 12.5.2 VWAP Reclaim + RVOL (ID 15..20)

**Mantık**: Fiyat VWAP altından üstüne reclaim ve RVOL>thr → long; tersi için short.

**Skor**: score = α·reclaim_strength + β·(rvol−1); reclaim_strength = (close−vwap)/vwap sonrası >0.

**Parametreler**: rvol_thr ∈ {1.1, 1.15, 1.2, 1.3, 1.5}, α=1.0, β=0.5.

**Warm up**: max(20, rvol_lb).

### 12.5.3 Supertrend + ADX (ID 25..30)

**Mantık**: supertrend_state == 'bullish' ve adx14 > thr → long; bearish & adx>thr → short.

**Parametreler**: atr_len=10, mult=3.0, adx_thr ∈ {18,20,22,24,26}.

**Skor**: score = (adx14−thr)/30 + γ·dist_to_st, dist_to_st = (close−st_line)/close işaretli.

### 12.5.4 Keltner Break (ID 35..40)

**Mantık**: Mum kapanışı KC_upper üstünde (veya short için KC_lower altında). ADX ile opsiyonel doğrulama.

**Parametreler**: ema_len=20, atr_len=10, mult ∈ {1.5..1.8}, adx_min=0|20.

**Skor**: score = (close−KC_upper)/KC_mid + δ·(adx14/50).

### 12.5.5 Bollinger Walk (ID 45..50)

**Mantık**: Ardışık ≥2 kapanış üst banda; mid altına inmedikçe long yürüyüşü sürer (short için alt bant).

**Parametreler**: bands∈[2.0,2.2], min_bars_on_band∈{2,3}.

**Skor**: score = (close−bb_upper)/bb_mid + ζ·bandwidth.

### 12.5.6 9/21 EMA Crossover (ID 14)

**Mantık**: EMA9 üstüne keserse long; altına keserse short. Whipsaw azaltmak için confirm_len=1..3 (bar sayısı) ve adx_min filtresi.

**Skor**: score = slope(EMA9−EMA21).

### 12.5.7 Triple MA 5/20/50 (ID 34)

**Mantık**: 5>20>50 long, 5<20<50 short; aksi 0.

**Skor**: score = min( d(5,20), d(20,50) ) (normalize farkların min'i), trend gücü ölçümü.

## 12.6 Parametre Varyantları ve ID Eşleme

- Kullanıcının verdiği tabloya göre aynı mantığın farklı eşiğe sahip varyantları ayrı ID olarak kayıtlıdır (örn. VWAP+RVOL 1.10,1.15,1.2…)
- UI'da tek strateji altında ön tanım presetleri listelenir; kullanıcı isterse serbest değer girer ve bu özel varyant custom ID ile tutulur

## 12.7 Skor ve Vote Politikaları

- **Vote yalnızca ana koşullar sağlandığında ±1**: Aksi 0
- **Score sürekli bir güven ölçüsü**: Eşik mesafeleri, eğimler, bant dışı mesafeler, hacim teyitleri gibi bileşenlerin lineer kombinasyonu, z score veya tanh ile yumuşatma; s_cap ile katkı tavanı (Parça 9)
- **Normalize**: Ensemble katmanı her sağlayıcı için kayan pencere ort/sigma ile standardize eder

## 12.8 UI / Konfig Entegrasyonu

- **Strateji Kataloğu ekranı**: ID, ad, grup, warm up, varsayılan paramlar, açıklama, notlar
- **Ürün/TF sayfasında**: Aktif/pasif anahtarı, preset seçimi veya özel param girişi
- **Her sağlayıcı için**: Son N işlem win%, ort. katkı, ort. latency ve w_i ağırlığı gösterilir (Parça 9 telemetrisi)
- **Profil Kaydet/Yükle**: Ürün/TF parametre setleri profil olarak kaydedilip çağrılabilir

## 12.9 Test Planı

- **Birim**: Her sağlayıcı için sınır koşulları (ör. reclaim tespiti, ardışık kapanış sayacı, MA kesişim tespiti)
- **Regresyon**: Param değişimlerinin beklenmeyen davranış üretmediği (ör. mult 1.5→1.6 değişimi)
- **Performans**: 100+ provider kombinasyonunda değerlendirme süresi TF=1 için < 50ms hedef
- **Uyumluluk**: Warm up yetersizse vote=0; NaN yayılımı testi

## 12.10 Kabul Kriterleri

- Plugin mimarisi, base arayüz, registry ve örnek stratejiler tanımlandı
- Kullanıcı tablosundaki strateji aileleri ID eşleşmeleriyle kataloğa dahil edildi
- UI/konfig override, telemetry ve test planı net
- Vote/score üretim politikaları ve warm up kuralları belirlendi
