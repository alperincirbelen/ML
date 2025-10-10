# 8. Ensemble & Confidence Katmanı

## 8.1 Kavramlar

- **Signal Provider**: (context) → {vote∈{-1,0,1}, score∈R, meta}. Vote yön, score büyüklük/güven
- **Ensemble**: Sağlayıcı çıktılarından tek skor S∈[-1,1] ve confidence c∈[0,1] üretir
- **p-hat (tahmini kazanma olasılığı)**: Kalibre edilmiş confidence; risk ve expectancy hesaplarına girer
- **Meta-öğrenme**: Ağırlıklar ve/veya üst model, sonuçlardan (win/lose) online güncellenir

## 8.2 Ensemble Stratejileri

### 8.2.1 Ağırlıklı Toplam (varsayılan)
```
S = tanh( sum_i ( w_i * v_i * s_i ) )
```
- v_i ∈ {-1,0,1}, s_i normalize skor
- Confidence: c = |S|
- Yön: sign(S)
- 0 eşiği yakınında işlem açmamak için ek eşik c_min kullanılır

### 8.2.2 Majority Vote + Güç
- Basit oy çoğunluğu; eşitlikte sum |s_i| ile kır
- Trend-rejim filtreli varyant (ör. ADX/EMA rejimi aktifken)

### 8.2.3 Stacking (L1→L2)
- **L1**: Sağlayıcı skorları/oyları, rejim sinyalleri, payout vb.
- **L2**: Lojistik regresyon (veya hafif GBM) ile p-hat üretir
- Eğitim offline (günlük) + online küçük adım (ops.)

### 8.2.4 Gating / Mixture-of-Experts
- Rejim özelliklerine (volatilite, trend gücü, RVOL) göre uzman seçici
- Her kümeye farklı ağırlık vektörü w^(k)

### 8.2.5 Bandit (UCB/Thompson, ops.)
- Kısa vadede hangi sağlayıcı/alt-strateji daha iyi?
- Çok kollu bandit ile keşif-kullanım dengesi

**Başlangıç sürümünde Ağırlıklı Toplam + Lojistik Kalibrasyon uygulanır. Stacking/gating ileriki fazda açılabilir.**

## 8.3 Skor Normalizasyonu

Her sağlayıcı için skor s_i standartlaştırılır:
```
s'_i = clip( (s_i - mu_i) / sigma_i , -3 , 3 )
```
- Kayan pencere N=500
- UI'dan katkı sınırı: |w_i * s'_i| ≤ s_cap

## 8.4 Kalibrasyon (confidence → p-hat)

### 8.4.1 Platt Scaling (lojistik)
```
p-hat = sigmoid( a*S + b )
```
- Parametreler (a,b) günlük olarak geçmiş (S, outcome) çiftlerinden fit edilir (L2 reg.)

### 8.4.2 Alternatif: İzotonik Regresyon
- Daha esnek, az veri ile aşırı uyum riski

### 8.4.3 Değerlendirme
- Brier Loss, LogLoss, ECE (Expected Calibration Error)
- Politika: ECE kötüleşirse yeniden kalibrasyon tetikle

## 8.5 Ağırlık Güncelleme (Online)

### 8.5.1 Kayan Pencere Performansı
- Her sağlayıcı için son N=200 işlemde win_rate_i, Sharpe_i, latency_penalty_i ölç

### 8.5.2 Ağırlık Kuralı (örnek)
```
w_i ← (1-α)w_i + α*softmax( k * score_i )
```
- score_i = win_rate_i − lambda * latency_penalty_i
- Sınırlar: w_i ≥ 0, toplam w_i = 1, w_i ≤ w_max

### 8.5.3 Sıfırlama
- Rejim değişimi tespitinde w ← uniform

## 8.6 Rejim Tespiti & Drift

- **Trend gücü** (ADX, 20 üstü/altı), **volatilite** (ATR z-skoru), **hacim** (RVOL), **payout rejimi** (permit orta noktası) → rejim vektörü
- **Drift testleri**: Page-Hinkley, ADWIN (opsiyonel, veri akışı)
- **Tetikte**: Ağırlıkları resetle, kalibrasyonu yenile, gereksiz sağlayıcıları devre dışı bırak (UI uyarısı)

## 8.7 Çoklu-TF / Çoklu-Ürün Birleşimi

- **Anahtar düzeyi**: Ensemble her (acc, product, timeframe) için ayrı çalışır
- **Çapraz teyit (ops.)**: TF=1 sinyali TF=5 ile uyumluysa bonus (gamma katsayısı) → S = S + gamma * sign(S5) * min(|S|, |S5|)

## 8.8 API (Python İskelet)

```python
# core/ensemble.py
from dataclasses import dataclass, field
from typing import Dict, List
import math

@dataclass
class ProviderVote:
    pid: int
    vote: int  # -1,0,1
    score: float  # ham skor

@dataclass
class EnsembleState:
    mu: Dict[int, float] = field(default_factory=dict)
    sigma: Dict[int, float] = field(default_factory=dict)
    w: Dict[int, float] = field(default_factory=dict)
    a: float = 1.0  # Platt a
    b: float = 0.0  # Platt b

class Ensemble:
    def __init__(self, state: EnsembleState, s_cap: float = 2.0):
        self.st = state
        self.s_cap = s_cap

    def _norm(self, pid: int, x: float) -> float:
        m = self.st.mu.get(pid, 0.0)
        s = max(1e-6, self.st.sigma.get(pid, 1.0))
        z = max(-3.0, min(3.0, (x - m)/s))
        return z

    def combine(self, votes: List[ProviderVote]) -> Dict:
        # ağırlıklı toplam
        acc = 0.0
        for v in votes:
            wi = self.st.w.get(v.pid, 1.0/len(votes))
            zi = self._norm(v.pid, v.score)
            contrib = wi * v.vote * zi
            
            # katkı tavanı
            if contrib > self.s_cap:
                contrib = self.s_cap
            if contrib < -self.s_cap:
                contrib = -self.s_cap
            acc += contrib
        
        S = math.tanh(acc)
        c = abs(S)
        
        # Platt → p-hat
        p_hat = 1.0/(1.0 + math.exp(-(self.st.a*S + self.st.b)))
        
        return {"S": S, "confidence": c, "p_hat": p_hat, 
                "dir": (1 if S>0 else (-1 if S<0 else 0))}

    def update_calibration(self, S_list: List[float], y_list: List[int]):
        # küçük bir lojistik fit (basit SGD/türevli), burada iskelet
        pass

    def update_weights(self, provider_scores: Dict[int, float], 
                      alpha: float = 0.1, w_max: float = 0.4):
        # softmax temelli güncelleme
        import math
        keys = list(provider_scores.keys())
        vals = [provider_scores[k] for k in keys]
        mx = max(vals)
        exps = [math.exp(v - mx) for v in vals]
        s = sum(exps)
        new = {k: min(w_max, exps[i]/s) for i,k in enumerate(keys)}
        
        # karışım güncellemesi
        for k in keys:
            self.st.w[k] = (1-alpha)*self.st.w.get(k, 1.0/len(keys)) + alpha*new[k]
        
        # normalize
        tot = sum(self.st.w.values())
        for k in self.st.w:
            self.st.w[k] /= max(tot, 1e-9)
```

## 8.9 Telemetry & Depolama

- **metrics tablosuna**: brier, logloss, ece, auc (ops.), calib_a/b, w_entropy, drift_score yazılır
- **strategy_perf tablosu**: Sağlayıcı bazlı kazanım/kayıp sayıları, son güncelleme

## 8.10 UI Eşlemesi

- **Ensemble Ayarları**: ensemble_mode (weighted/stacking), c_min, s_cap, alpha (weight_lr), w_max
- **Kalibrasyon**: Durum (iyi/orta/kötü), son ECE, yeniden kalibre et butonu
- **Sağlayıcı Tablosu**: w_i, win%, latency, kapalı/açık anahtarı
- **Rejim Paneli**: ADX, ATR z-skoru, RVOL, payout rejimi; drift uyarıları

## 8.11 Test Planı

- **Birim**: combine() normalizasyon, sınır durumları (w=0, sigma→0), yön/|S| doğrulaması
- **Kalibrasyon**: Sentetik veriyle Platt fit → Brier/ECE iyileşmesi
- **Ağırlık Uyarlama**: Yapay performans profilleri ile w'lerin beklenen yöne kayması
- **Rejim/Drift**: ADX/ATR/RVOL değişim senaryolarında reset ve uyarı

## 8.12 Kabul Kriterleri

- Weighted ensemble + Platt kalibrasyon uygulandı (tasarım + iskelet)
- Ağırlık güncelleme, rejim/drift tepkisi ve çoklu-TF politikaları tanımlandı
- Telemetry alanları ve UI ayarları belirlendi
- Birim ve kalibrasyon testleri için net ölçütler kondu
