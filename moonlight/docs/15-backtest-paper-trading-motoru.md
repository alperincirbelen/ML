# 15. Backtest & Paper Trading Motoru (Metrikler, Walk Forward)

## 15.1 Kapsam ve Varsayımlar

- **Enstrüman**: Fixed Time Trade (FTT) — giriş bar kapanışında yapılır; vade TF adımı kadardır (1/5/15 dk)
- **Payout (R)**: Zamanla değişken olabilir. Backtest'te iki mod:
  1. **Sabit**: Kullanıcı tanımlı (örn. %90)
  2. **Seri**: Zaman serisi (csv) ile her bara özel payout%
- **Gecikme/Slip**: İsteğe bağlı latency_ms ve price_offset modeli; FTT'de fiyat ofseti sınırlı etkide, giriş/kapanış bar kapanış fiyatıyla varsayılır
- **Concurrency**: Aynı (ürün, TF) için tek açık pozisyon
- **Permit**: permit_min ≤ payout ≤ permit_max değilse giriş yok

## 15.2 Veri Girişi

- **Candles**: ts_ms, open, high, low, close, volume (UTC ms, artan sıralı)
- **Payout**: ts_ms, payout (yüzde). Yoksa sabit değer kullanılır
- **Split & Align**: Candles ile payout serisi TF slotu üzerinden birleştirilir

## 15.3 Simülasyon Döngüsü (Olay Akışı)

```python
for her kapanan bar (t):
    1) Özellikleri hesapla (Parça 7–8)
    2) Aktif sağlayıcıları değerlendir → ProviderVote[]
    3) Ensemble.combine → {S, confidence, p̂, dir}
    4) Risk/Permit/Concurrency önkontrolü
    5) Giriş kararı: TRUE ise trade aç → vade = TF adımı
    6) t+TF sonunda kapanış: kazan/kaybet belirle (FTT outcome)
    7) PnL = +amount*R (win) veya −amount (lose)
    8) Kayıt/metrik güncelle → rapor
```

**FTT sonuç kuralı (örn. CALL)**: close(t+TF) > close(t) → win, eşitse push (varsayılanı lose değil; platform kuralına göre ayarlanabilir)

## 15.4 Metrikler

### 15.4.1 Temel
- İşlem sayısı, win rate, ort. payout, expectancy E = p̂·R − (1−p̂), kâr faktörü, ort. işlem kârı

### 15.4.2 Risk
- Max DD, Calmar, Sharpe, Sortino (ops.), max ardışık kayıp, günlük PnL dağılımı

### 15.4.3 Stabilite
- Ürün/TF kırılımında win rate, saat gün ısı haritası, rejimlere göre (ADX↑/↓, RVOL↑/↓) performans

### 15.4.4 Kalibrasyon
- Brier, LogLoss, reliability diagram (p̂ dilimleri vs gerçek win)

### 15.4.5 Operasyonel
- Permit skip oranı, concurrency skip, ort. latency varsayımı etkisi

## 15.5 Walk Forward & CV

### 15.5.1 Zaman Temelli Ayrım
- Genişleyen (expanding) veya kaydırmalı (rolling) pencereler

### 15.5.2 WF Protokolü
1. **Train**: [t0, t1) → ağırlık/kalibrasyon/param fit
2. **Test**: [t1, t2) → donmuş paramlarla skor
3. **Kaydır**: t0→t1, t1→t2 …

### 15.5.3 Nested CV (ops.)
- İç döngüde hiperparametre seçimi; dış döngü raporlar

### 15.5.4 Model Gov
- Aşırı uyumu engellemek için bilgi sızıntısı yok, test setine bakarak param güncellenmez

## 15.6 Hiperparametre Taraması

### 15.6.1 Grid/Random
- Strateji eşikleri (örn. rsi_up, adx_thr, keltner_mult), ensemble c_min, s_cap, risk amount_mode vb

### 15.6.2 Bayes Opt. (ops.)
- Hedef fonksiyonu Sharpe·λ + Expectancy·(1−λ) ve işlem sayısı alt eşiği

### 15.6.3 Ceza
- Çok karmaşık konfig için AIC/BIC benzeri basit ceza veya minimum işlem sayısı filtresi

## 15.7 Paper Trading

- **MockConnector** (Parça 6) + gerçek zamanlı worker/scheduler ile emir açmadan simülasyon
- **Gerçek payout akışı varsa**: Onu kullanır; yoksa sabit/parametrik
- **UI'da canlı akış + "Paper" rozeti**: PnL sanal, kayıtlar account_id='paper' ile ayrılır

## 15.8 Raporlama (UI + Dosya)

### 15.8.1 UI
- **Özet kartları**: Win rate, PnL, PF, DD, Sharpe, işlem sayısı, ort. payout
- **Grafikler**: Equity curve, Drawdown, Reliability diagram, Saat/Gün ısı haritası, TF/Ürün kırılımı

### 15.8.2 Dışa Aktarım
- backtest_report.json, trades.csv, equity.csv, metrics.json

## 15.9 Python API (İskelet)

```python
# core/backtest.py
from dataclasses import dataclass
import pandas as pd
from typing import Dict, List, Optional

@dataclass
class BacktestConfig:
    timeframe: int  # 1,5,15
    payout_mode: str = "fixed"  # fixed | series
    payout_fixed: float = 90.0
    latency_ms: int = 0
    push_is_win: bool = True
    min_trades: int = 200

@dataclass
class BacktestReport:
    trades: pd.DataFrame
    metrics: Dict[str, float]

class Backtester:
    def __init__(self, indicators, providers, ensemble, risk):
        self.ind = indicators
        self.providers = providers
        self.ens = ensemble
        self.risk = risk

    def run(self, candles: pd.DataFrame, payout_series: Optional[pd.Series], cfg: BacktestConfig) -> BacktestReport:
        df = candles.copy()
        
        # 1) features
        feats = compute_features(df, self.ind)
        
        # 2) iterate bars → sinyal & karar
        recs = []
        open_until = None
        
        for i in range(1, len(df)):  # bar kapanışı
            if open_until is not None and i >= open_until:
                # sonucu hesapla
                entry = recs[-1]
                entry_close = df['close'].iloc[i]
                win = (entry_close > entry['entry_close']) if entry['dir']==1 else (entry_close < entry['entry_close'])
                
                if cfg.push_is_win and entry_close == entry['entry_close']:
                    win = True
                
                R = entry['payout']/100.0
                pnl = entry['amount']*R if win else -entry['amount']
                
                entry.update({
                    "exit_idx": i,
                    "status": "win" if win else "lose",
                    "pnl": pnl
                })
                open_until = None
                continue
            
            if open_until is not None:
                continue  # yeni giriş değerlendirmesi
            
            votes = []
            for p in self.providers:
                v = p.evaluate(df.iloc[:i+1], feats)
                if v:
                    votes.append(v)
            
            if not votes:
                continue
            
            comb = self.ens.combine(votes)
            if comb['dir']==0:
                continue
            
            payout = float(cfg.payout_fixed if cfg.payout_mode=="fixed" else payout_series.iloc[i])
            ctx = build_backtest_ctx(df, i, comb, payout)
            
            if not self.risk.enter_allowed(ctx):
                continue
            
            amount = self.risk.compute_amount(ctx)
            recs.append({
                "entry_idx": i,
                "entry_ts": int(df['ts_ms'].iloc[i]),
                "entry_close": float(df['close'].iloc[i]),
                "dir": comb['dir'],
                "payout": payout,
                "amount": amount
            })
            open_until = i + bars_of(cfg.timeframe)
        
        trades = pd.DataFrame(recs)
        metrics = compute_metrics(trades)
        return BacktestReport(trades=trades, metrics=metrics)
```

## 15.10 Doğruluk & Kenar Durumlar

- **Warm up**: Yetersiz barlarda sinyal üretilmez
- **Tie/push**: Platform kuralına göre ayarlanabilir; varsayılan push_is_win=True
- **Payout eksikliği**: Seri varsa eksik değerler taşınmaz, bar atlanır
- **Saat dilimi**: Giriş/rapor UTC ms, UI'da Europe/Istanbul gösterimi
- **Repro**: Rastgelelik içeren kararlar seed ile sabitlenir

## 15.11 Test Planı

- **Birim**: FTT outcome doğrulaması (CALL/PUT), push davranışı, payout sabit/seri uyumu, concurrency kuralı
- **Entegrasyon**: Parça 7–13 ile uçtan uca backtest; belirli veri setinde beklenen metriklerle karşılaştırma
- **Walk Forward**: Sentetik rejim değişimi setinde kalibrasyon/weight reset etkisi
- **Performans**: 1M bar'lık veri -> süre ve bellek bütçesi; işlemsel sayaçlar

## 15.12 UI Eşlemesi

- **Backtest sihirbazı**: Veri seç (csv), TF, payout modu, tarih aralığı, strateji presetleri, risk ayarları
- **Rapor ekranı**: Özet metrik, equity/drawdown grafikleri, p̂ kalibrasyon grafiği, ısı haritaları, işlem listesi
- **Karşılaştırma**: Farklı preset/param setleri yan yana (tablo + grafikli)
- **Dışa aktarım**: Tek tıkla .json/.csv

## 15.13 Kabul Kriterleri

- FTT backtest/paper motoru tasarlandı ve iskelet kodu verildi
- Payout modeli (sabit/seri), concurrency ve permit kuralları uygulandı
- Zengin metrik seti, walk forward ve hiperparam taraması yönergeleri tanımlandı
- UI raporlama ve dışa aktarım belirlendi; test planı ve kenar durumları kapsandı
