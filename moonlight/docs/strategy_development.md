# Strateji Geliştirme Kılavuzu

## 🎯 Strateji Anatomisi

Bir MoonLight stratejisi:
- ✅ `StrategyProvider` protokolünü uygular
- ✅ `warmup_bars()` ile minimum bar ihtiyacını bildirir
- ✅ `evaluate()` ile sinyal üretir
- ✅ Deterministik davranır (yan etkisiz)
- ✅ Süre bütçesine uyar (p90 < 3ms / 200 bar)

## 📝 Temel Şablon

```python
# moonlight/core/strategies/providers/my_strategy.py

from ..base import StrategyProvider, ProviderConfig, ProviderContext, ProviderVote
from ..registry import register
from ...indicators.basic import ema, rsi

@register(pid=101, metadata={
    "name": "My Custom Strategy",
    "group": "trend",
    "description": "Açıklama buraya"
})
class MyCustomStrategy(StrategyProvider):
    """Strateji açıklaması"""
    
    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg
        p = cfg.params
        
        # Parametreleri al (varsayılanlarla)
        self.ema_len = p.get('ema_len', 20)
        self.rsi_len = p.get('rsi_len', 14)
        self.threshold = p.get('threshold', 55)
    
    def warmup_bars(self) -> int:
        """Minimum bar sayısı"""
        return max(self.ema_len, self.rsi_len) + 5
    
    def evaluate(self, df, feats, ctx):
        """Ana mantık"""
        # 1. Warm-up kontrolü
        if len(df) < self.warmup_bars():
            return None
        
        # 2. Göstergeleri hesapla
        close = df['close']
        ema_val = ema(close, self.ema_len)
        rsi_val = rsi(close, self.rsi_len)
        
        # 3. Son değerler
        ema_now = ema_val.iloc[-1]
        rsi_now = rsi_val.iloc[-1]
        
        # 4. NaN kontrolü
        if pd.isna(ema_now) or pd.isna(rsi_now):
            return None
        
        # 5. Sinyal mantığı
        vote = 0
        if rsi_now > self.threshold:
            vote = +1  # CALL
        elif rsi_now < (100 - self.threshold):
            vote = -1  # PUT
        
        # 6. Sinyal yoksa
        if vote == 0:
            return ProviderVote(
                pid=self.cfg.id,
                vote=0,
                score=0.0,
                meta={"rsi": rsi_now}
            )
        
        # 7. Skor hesapla
        score = abs(rsi_now - 50) / 50.0  # 0-1 arası
        
        # 8. Sonuç dön
        return ProviderVote(
            pid=self.cfg.id,
            vote=vote,
            score=float(score),
            meta={
                "ema": ema_now,
                "rsi": rsi_now,
                "threshold": self.threshold
            }
        )
```

## 🧪 Test Etme

```python
# Test dosyası oluştur
# tests/strategies/test_my_strategy.py

import pandas as pd
import numpy as np
from moonlight.core.strategies.registry import build

def test_my_strategy():
    # Sentetik veri
    df = pd.DataFrame({
        'close': np.cumsum(np.random.randn(100)) * 0.01 + 100,
        # ... diğer kolonlar
    })
    
    # Strateji oluştur
    strategy = build(101, params={'threshold': 60})
    
    # Değerlendir
    from moonlight.core.strategies.base import ProviderContext
    ctx = ProviderContext("EURUSD", 1, 90.0)
    
    vote = strategy.evaluate(df, {}, ctx)
    
    # Assertions
    assert vote is None or vote.vote in (-1, 0, 1)
    if vote:
        assert -1 <= vote.score <= 1

# pytest ile çalıştır
# pytest tests/strategies/test_my_strategy.py
```

## 📊 Mevcut Stratejiler

### ID: 5 - EMA Trend + RSI

**Parametreler:**
- `ema_fast`: 9 (varsayılan)
- `ema_slow`: 21
- `rsi_len`: 7
- `rsi_up`: 55
- `rsi_dn`: 45

**Mantık:**
- EMA9 > EMA21 ve RSI7 > 55 → CALL
- EMA9 < EMA21 ve RSI7 < 45 → PUT

### ID: 14 - EMA 9/21 Crossover

**Parametreler:**
- `fast_len`: 9
- `slow_len`: 21
- `confirm_bars`: 1
- `use_adx`: true
- `adx_min`: 20

**Mantık:**
- EMA9 yukarı kesişim + ADX > 20 → CALL
- EMA9 aşağı kesişim + ADX > 20 → PUT

### ID: 15 - VWAP Reclaim + RVOL

**Parametreler:**
- `rvol_lb`: 20
- `rvol_thr`: 1.3
- `alpha`: 1.0
- `beta`: 0.5

**Mantık:**
- VWAP reclaim + RVOL > 1.3 → Yön sinyali
- Skor: Reclaim gücü + hacim fazlası

### ID: 25 - Supertrend + ADX

**Parametreler:**
- `st_len`: 10
- `st_mult`: 3.0
- `adx_len`: 14
- `adx_thr`: 22

**Mantık:**
- Supertrend bullish + ADX > 22 → CALL
- Supertrend bearish + ADX > 22 → PUT

## 🎨 Best Practices

### ✅ Yapılması Gerekenler

1. **Warm-up kontrolü**: Her zaman
2. **NaN handling**: Güvenli varsayılanlar
3. **Deterministik**: Aynı girdi → aynı çıktı
4. **Meta bilgi**: Karar gerekçesi açık
5. **Performans**: Ağır hesapları önbellekle

### ❌ Yapılmaması Gerekenler

1. **Future-looking**: İleri bakış yasak
2. **Yan etki**: Disk/ağ erişimi yok
3. **Global state**: Sınıf içi durum minimal
4. **Rastgelelik**: Seed olmadan random() kullanma
5. **Aşırı karmaşıklık**: Basit tut

## 📚 Gösterge Kullanımı

### Temel Göstergeler

```python
from moonlight.core.indicators.basic import (
    sma, ema, rsi, macd, bollinger_bands, atr
)

# DataFrame'de
close = df['close']
ema20 = ema(close, 20)
rsi14 = rsi(close, 14)
macd_line, signal, hist = macd(close)
```

### İleri Göstergeler

```python
from moonlight.core.indicators.advanced import (
    adx, supertrend, keltner_channel, rvol
)

high, low = df['high'], df['low']
adx14 = adx(high, low, close, 14)
st_line, st_dir = supertrend(high, low, close)
```

## 🔧 Parametre Optimizasyonu

### Walk-Forward Yaklaşımı

1. **Eğitim**: Son 3 ay
2. **Validation**: 1 hafta
3. **Test**: 1 hafta
4. Pencereyi kaydır, tekrarla

### Metrikler

- **Win Rate**: ≥ %55 (binary için minimum)
- **Profit Factor**: ≥ 1.2
- **Max Drawdown**: ≤ 5× tek işlem tutarı
- **Expectancy**: > 0

## 📦 Strateji Paketleme

### Manifest Oluştur

```yaml
# moonlight/core/strategies/providers/my_strategy/provider.yaml
id: 101
name: "My Custom Strategy"
version: "1.0.0"
api: 1
author: "Your Name"
entry: "provider:MyCustomStrategy"
warmup_bars: 30
params_schema:
  ema_len: {type: int, min: 5, max: 200, default: 20}
  threshold: {type: float, min: 50, max: 80, default: 55}
notes: "Açıklama ve notlar"
```

## 🧪 Backtest Örneği

```bash
# CLI
python -m moonlight.core.backtest \
  --config configs/app.yaml \
  --strategy 101 \
  --product EURUSD \
  --tf 1 \
  --from 2025-01-01 \
  --to 2025-03-31 \
  --report-dir reports/
```

## 🚀 Devreye Alma

### 1. Paper Testi
- Minimum 1000 işlem
- 2-4 hafta süre
- Win rate ≥ hedef
- Guardrail test edildi

### 2. Canary (Live)
- Tek hesap
- Tek ürün/TF
- Minimum tutar (%0.25-0.5)
- 1 hafta gözlem

### 3. Rollout
- Kademeli artış: %10 → %25 → %50 → %100
- Her adımda metrik kontrolü
- Rollback planı hazır

## 📞 Destek

Sorun yaşarsanız:
1. Destek paketi oluşturun: UI → Ops → Destek Paketi
2. Log dosyalarını inceleyin
3. Metric snapshot'ları kontrol edin

---

**Unutmayın:** Basit stratejiler çoğu zaman karmaşıklardan daha iyi çalışır!
