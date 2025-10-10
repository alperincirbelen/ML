# 📊 Strateji Kataloğu

## Strateji Mimarisi

MoonLight plugin tabanlı strateji sistemi kullanır. Her strateji:

- **Benzersiz ID**: Kayıt için
- **Parametre Seti**: Özelleştirilebilir
- **Warmup Gereksinimi**: Minimum bar sayısı
- **Vote Üretimi**: -1 (short/put), 0 (neutral), +1 (long/call)
- **Skor**: Güven derecesi

## Kayıtlı Stratejiler

### ID: 5 - EMA Trend + RSI
- **Grup**: Trend + Oscillator
- **Mantık**: 
  - EMA(9) > EMA(21) ve RSI(7) > 55 → Long
  - EMA(9) < EMA(21) ve RSI(7) < 45 → Short
- **Parametreler**:
  - `ema_fast`: 9 (varsayılan)
  - `ema_slow`: 21 (varsayılan)
  - `rsi_len`: 7
  - `rsi_up`: 55
  - `rsi_dn`: 45
- **Warmup**: 26 bar
- **Kullanım**: Trend takibi + momentum doğrulama

### ID: 14 - EMA 9/21 Crossover
- **Grup**: Trend
- **Mantık**: EMA(9) kesişimi EMA(21) ile
- **Parametreler**:
  - `ema_fast`: 9
  - `ema_slow`: 21
  - `confirm_bars`: 1 (whipsaw azaltma)
- **Warmup**: 22 bar

### ID: 15 - VWAP Reclaim + RVOL
- **Grup**: Volume + Trend
- **Mantık**: 
  - Fiyat VWAP altından üste geçiş
  - RVOL(20) > 1.3 → Hacim teyidi
- **Parametreler**:
  - `rvol_threshold`: 1.3
  - `min_dist_vwap`: 0.001
- **Warmup**: 25 bar

### ID: 25 - Supertrend + ADX
- **Grup**: Trend + Strength
- **Mantık**:
  - Supertrend bullish ve ADX > 20 → Long
  - Supertrend bearish ve ADX > 20 → Short
- **Parametreler**:
  - `st_len`: 10
  - `st_mult`: 3.0
  - `adx_threshold`: 20
- **Warmup**: 30 bar

### ID: 35 - Keltner Breakout
- **Grup**: Volatility Breakout
- **Mantık**: Kapanış üst banda breakout
- **Parametreler**:
  - `ema_len`: 20
  - `atr_len`: 10
  - `mult`: 1.6
- **Warmup**: 25 bar

### ID: 45 - Bollinger Walk
- **Grup**: Volatility Mean-Reversion
- **Mantık**: Ardışık üst bantta kapanış (≥2 bar)
- **Parametreler**:
  - `length`: 20
  - `mult`: 2.0
  - `walk_len`: 2
- **Warmup**: 22 bar

## Yeni Strateji Ekleme

### 1. Dosya Oluştur

```python
# moonlight/core/strategies/providers/my_strategy.py

from ..base import ProviderConfig, ProviderContext
from ..registry import register
from ...ensemble.models import ProviderVote
from ...indicators.basic import ema, rsi

@register(101)  # Benzersiz ID seç
class MyStrategy:
    META = {
        "name": "My Custom Strategy",
        "group": "custom",
        "description": "Açıklama"
    }
    
    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg
        # Parametreleri al
        self.param1 = cfg.params.get('param1', default_value)
    
    def warmup_bars(self) -> int:
        """Gerekli minimum bar sayısı"""
        return 50
    
    def evaluate(self, df, feats, ctx):
        """Strateji değerlendirmesi"""
        
        # Warmup kontrolü
        if len(df) < self.warmup_bars():
            return None
        
        # İndikatörler hesapla
        ema_20 = ema(df['close'], 20)
        rsi_14 = rsi(df['close'], 14)
        
        # Son değerler
        ema_now = ema_20.iloc[-1]
        rsi_now = rsi_14.iloc[-1]
        
        # Karar mantığı
        if rsi_now > 70 and ema_now > df['close'].iloc[-2]:
            vote = 1
            score = 0.8
        elif rsi_now < 30 and ema_now < df['close'].iloc[-2]:
            vote = -1
            score = 0.8
        else:
            vote = 0
            score = 0.0
        
        return ProviderVote(
            pid=self.cfg.id,
            vote=vote,
            score=score,
            meta={"ema": ema_now, "rsi": rsi_now}
        )
```

### 2. Import Ekle

```python
# moonlight/core/strategies/providers/__init__.py
from .my_strategy import MyStrategy
```

### 3. Config'e Ekle

```yaml
products:
  - product: EURUSD
    strategies: [5, 14, 101]  # Yeni strateji ID'si
```

### 4. Test Et

```bash
python tests/smoke_test.py
```

## Strateji Geliştirme İlkeleri

### 1. Determinizm
- Aynı girdi → aynı çıktı
- Random kullanmayın (veya seed kullanın)

### 2. Warmup
- Yetersiz veride `None` döndürün
- NaN'leri kontrol edin

### 3. Performans
- p90 < 5 ms / 200 bar hedefleyin
- Gereksiz hesaplamalardan kaçının

### 4. Skor Normalizasyonu
- Score'u [-1, 1] aralığına sınırlayın
- Aşırı değerler ensemble'ı bozabilir

### 5. Meta Bilgi
- Karar gerekçelerini `meta` alanına ekleyin
- Açıklanabilirlik için önemli

## Ensemble Entegrasyonu

Stratejileriniz otomatik olarak ensemble'a dahil edilir:

1. **Oylama**: Her strateji vote verir
2. **Ağırlıklandırma**: Performansa göre ağırlık
3. **Normalizasyon**: Z-score ile standartlaştırma
4. **Birleştirme**: Weighted sum + tanh
5. **Kalibrasyon**: S → p̂ (kazanma olasılığı)

## Performans İzleme

Her strateji için otomatik izlenir:

- **Win Rate**: Son N işlemde başarı oranı
- **Contribution**: Ensemble'a katkı
- **Latency**: Hesaplama süresi
- **Weight**: Güncel ağırlık

Panel'de görüntülenebilir (geliştirilecek).

## Örnek Kullanım

```yaml
# Sadece trend stratejileri
products:
  - product: EURUSD
    strategies: [5, 14, 25]  # EMA+RSI, Crossover, Supertrend

# Sadece volatilite
products:
  - product: BTCUSD
    strategies: [35, 45]  # Keltner, Bollinger

# Karma (hybrid)
products:
  - product: XAUUSD
    strategies: [5, 15, 25, 35]  # Trend + Volume + Volatility
```

## İleri Seviye

### Parametre Optimizasyonu
- Backtest ile en iyi parametreleri bulun
- Grid search veya Bayesian optimization
- Walk-forward validation

### Ensemble Ağırlıkları
- Online learning ile otomatik güncelleme
- Performansa dayalı adaptasyon
- Rejim bazlı ayarlama

### Meta-Learning
- Stratejilerin stratejisi
- Bağlama göre strateji seçimi
- Contextual bandits

---

**İpucu**: Başlangıçta 2-3 basit strateji ile başlayın. Kompleks kombinasyonlar sonra.
