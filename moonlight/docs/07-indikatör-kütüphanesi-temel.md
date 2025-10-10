# 7. İndikatör Kütüphanesi (Temel Set)

## 7.1 Veri Sözleşmesi ve Giriş/Çıkış

- **Girdi DataFrame şeması**: sütunlar ts_ms, open, high, low, close, volume. Zaman artan sıralı ve tekil
- **Uyum**: UTC ms; UI'da Europe/Istanbul gösterilir
- **Çıkış**: pd.Series (veya tuple of Series) — girdiyle aynı uzunluk ve endeks; ısınma (warm up) döneminde NaN
- **Performans**: pandas/numpy vektörizasyonu, rolling().mean()/std(); gereksiz apply yok
- **Hafıza**: Kısa pencere hesaplarında kopyasız işlemler; uzun seriler için float32 opsiyonu (parametre ile)

## 7.2 Kapsam (Temel Göstergeler)

- **Hareketli Ortalamalar**: sma, ema, wma, hma
- **Momentum/Osilatör**: rsi, stochastic (%K/%D)
- **Trend/Momentum**: macd (12/26/9) + histogram
- **Volatilite/Bantlar**: bollinger_bands (20, 2σ) + bollinger_width
- **Volatilite**: true_range, atr (Wilder, 14)
- **Hacim Tabanlı**: obv, mfi (14)
- **VWAP (basit)**: vwap (gün/oturum reset destekli temel sürüm)

## 7.3 Modül ve API (Python)

```python
# core/indicators/basic.py
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Tuple, Optional

# === Hareketli Ortalamalar ===
def sma(s: pd.Series, length: int = 20) -> pd.Series:
    return s.rolling(length, min_periods=length).mean()

def ema(s: pd.Series, length: int = 20) -> pd.Series:
    return s.ewm(span=length, adjust=False, min_periods=length).mean()

def wma(s: pd.Series, length: int = 20) -> pd.Series:
    w = np.arange(1, length + 1)
    return s.rolling(length).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)

def hma(s: pd.Series, length: int = 20) -> pd.Series:
    # Hull MA: WMA( 2*WMA(n/2) − WMA(n), sqrt(n) )
    n1 = int(length)
    n2 = max(1, int(length/2))
    n3 = max(1, int(np.sqrt(length)))
    wma_n = wma(s, n1)
    wma_n2 = wma(s, n2)
    hull = 2*wma_n2 - wma_n
    return wma(hull, n3)

# === Momentum / Osilatör ===
def rsi(s: pd.Series, length: int = 14) -> pd.Series:
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1/length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out

def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
               k: int = 14, k_smooth: int = 3, d: int = 3) -> Tuple[pd.Series, pd.Series]:
    ll = low.rolling(k, min_periods=k).min()
    hh = high.rolling(k, min_periods=k).max()
    k_raw = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    k_line = k_raw.rolling(k_smooth, min_periods=k_smooth).mean()
    d_line = k_line.rolling(d, min_periods=d).mean()
    return k_line, d_line

# === MACD ===
def macd(s: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = ema(s, fast)
    ema_slow = ema(s, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

# === Bollinger ===
def bollinger_bands(s: pd.Series, length: int = 20, mult: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    mid = sma(s, length)
    std = s.rolling(length, min_periods=length).std(ddof=0)
    upper = mid + mult * std
    lower = mid - mult * std
    return upper, mid, lower

def bollinger_width(s: pd.Series, length: int = 20, mult: float = 2.0) -> pd.Series:
    u, m, l = bollinger_bands(s, length, mult)
    return (u - l) / m

# === ATR / True Range ===
def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1/length, adjust=False, min_periods=length).mean()

# === Hacim Tabanlı ===
def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()

def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, length: int = 14) -> pd.Series:
    tp = (high + low + close) / 3.0
    raw = tp * volume
    pos = np.where(tp.diff() > 0, raw, 0.0)
    neg = np.where(tp.diff() < 0, raw, 0.0)
    pos_mf = pd.Series(pos, index=tp.index).rolling(length, min_periods=length).sum()
    neg_mf = pd.Series(neg, index=tp.index).rolling(length, min_periods=length).sum()
    mr = pos_mf / neg_mf.replace(0, np.nan)
    return 100 - (100 / (1 + mr))

# === VWAP (basit) ===
def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, 
         session: Optional[pd.Series] = None) -> pd.Series:
    tp = (high + low + close) / 3.0
    if session is None:
        cum_pv = (tp * volume).cumsum()
        cum_v = volume.cumsum().replace(0, np.nan)
        return cum_pv / cum_v
    
    # session değişiminde sıfırlama
    pv = tp * volume
    groups = session.ne(session.shift()).cumsum()
    vwap_series = pv.groupby(groups).cumsum() / volume.groupby(groups).cumsum().replace(0, np.nan)
    vwap_series.index = tp.index
    return vwap_series
```

## 7.4 Kenar Durumlar ve Uyum Testleri

- **Sıralama**: ts_ms artan değilse sıralayıp uyarı ver
- **Eksik veri**: volume boş ise obv/mfi/vwap hesapları NaN; UI'da veri eksik uyarısı
- **Bölünme/hatalar**: 0'a bölmeyi replace(0, np.nan) ile koru; inf değerleri NaN'e çevir
- **Warm up**: min_periods=length → başlangıçta NaN; strategy bu barlarda işlem açmaz
- **dtype**: Uzun serilerde float32 seçeneği sun (hafıza için), fakat son hesap float64 kalabilir

## 7.5 Feature Adlandırma Standardı

- **MA**: ema{L}, sma{L}, hma{L}
- **MACD**: macd_{f}_{s}_{sig}, macd_hist_{f}_{s}_{sig}
- **RSI**: rsi{L}
- **Stoch**: stoch_k_{L}, stoch_d_{L}
- **BB**: bb_upper_{L}_{mult}, bb_mid_{L}, bb_lower_{L}_{mult}, bb_width_{L}_{mult}
- **ATR**: atr{L}, TR: tr
- **Hacim**: obv, mfi{L}
- **VWAP**: vwap veya vwap_session

## 7.6 Performans İpuçları

- **Tekrarlanan hesaplar için önbellekleme**: Aynı Series._values kimliği ve aynı parametre — opsiyonel zayıf referanslı cache
- **Çoklu TF hesaplamalarında tek pass**: Örn. 1 dakikalık seriden 5/15 dakikayı resample edip hesapla
- **Numba gerekmez**: Profil sonucu gerekiyorsa yalnız kritik fonksiyonlara eklenir (opsiyonel)

## 7.7 Test Planı

- **Doğruluk**: RSI, MACD, BB, ATR için bilinen referans serilerle tolerans (rtol=1e-6)
- **Stoch %K/%D sınırları**: [0,100]
- **Performans**: 1M bar üzerinde toplam çalışma süresi ölçümü; hedef donanıma bağlı olarak saniye altı/çok saniye ölçeğinde
- **Uyumluluk**: NaN yayılımı ve warm up; bölünme hatası testleri

## 7.8 UI / Strateji Entegrasyonu

- **Stratejiler basic set'i doğrudan kullanır**: Parametreleri UI'dan override edilebilir
- **Grafikte overlay**: BB bantları, MA'lar; alt pencerelerde RSI, MACD, Stoch
- **Feature çıkarımı**: Storage'a yazılan kolon adları 7.5 standardı ile eşleşir

## 7.9 Kabul Kriterleri

- Temel göstergeler (MA'lar, RSI, Stoch, MACD, Bollinger, ATR/TR, OBV, MFI, VWAP) uygulandı (API imzaları ve iskelet kod hazır)
- Warm up/NaN, sıralama, bölünme hatası ve dtype politikaları tanımlandı
- Feature adlandırma standardı & UI/strateji entegrasyonu net
