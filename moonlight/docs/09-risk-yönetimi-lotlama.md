# 9. Risk Yönetimi & Lotlama

## 9.1 Terimler ve Beklenti

- **Payout (R_win)**: Kazanç oranı (ör. %90 → 0.90)
- **p̂ (tahmini başarı olasılığı)**: Ensemble/kalibrasyon çıktısı
- **Beklenen değer (tutar (a) için)**: E[a] = a*(p̂*R_win - (1-p̂))
- **Kâr eşiği**: p̂ > 1/(1+R_win). Örn. R=0.90 → eşik ≈ %52.63
- **UI politikası**: Kullanıcı win_threshold'u bu teorik eşiğin üstünde (örn. %70+) ayarlar

## 9.2 Giriş (Enter) Politikaları

### 9.2.1 Permit Payout
- permit_min ≤ payout ≤ permit_max değilse giriş yok

### 9.2.2 Confidence Eşiği
- confidence ≥ win_threshold_tf

### 9.2.3 Concurrency
- (hesap, ürün, TF) başına tek açık işlem; 1/5/15 birbirinden bağımsız

### 9.2.4 Saat Filtresi (ops.)
- Düşük likidite saatleri hariç; UI'dan tanımlanır

### 9.2.5 Cool down
- Kayıptan sonra t_cooldown_s bekle; ardışık kayıpta süre artan (30s→60s→120s, tavan 5dk)

### 9.2.6 Vol/Haber Filtresi (ops.)
- ATR z skoru veya RVOL aşımında bekle

### 9.2.7 Latency Guard
- Emir turu tahmini gecikme > abort_ms ise giriş engellenir

## 9.3 Lot (Tutar) Boyutlandırması

### 9.3.1 Modlar ve Sınırlar
- **Fixed (varsayılan)**: Her işlemde aynı a0
- **Balance Fraction**: a = clamp(a_min, frac·balance, a_cap); frac=1–3% tipik
- **Kelly lite (ops.)**: f^* = (p̂(R+1)−1)/R; gerçek tutar = balance·max(0,f^*)·kelly_scale (0.1–0.3)
- **ATR Normalize (deneysel)**: Volatiliteye göre göreli ayarlama; FTT'de sınırlı faydalı
- **Sert sınırlar**: a_min ve tavan a_cap her modda uygulanır
- **Martingale/anti martingale**: Varsayılan kapalı; UI'da ayrı "riskli" bayrak + sıkı tavanlar ile opsiyonel

## 9.4 Guardrails (Bariyerler)

### 9.4.1 Günlük Kayıp
- realized_pnl_day ≤ −max_daily_loss → hemen durdur

### 9.4.2 Ardışık Kayıp
- consec_losses ≥ Lmax → durdur + cool down artır

### 9.4.3 Günlük Kâr Hedefi (ops.)
- Hedefe ulaşıldığında sadece gözlem moduna geç

### 9.4.4 Payout/Win rate Bozulması
- Permit dışına çıkıldığında yeni işlem açma

### 9.4.5 Circuit breaker
- Hata fırtınasında (auth/429/timeout) otomatik pause + uyarı

## 9.5 Çıkış (Exit) ve Erken Kapatma

- **FTT'de işlem içi SL/TP yoktur**: Platform erken kapama destekliyorsa opsiyonel: min_profit_lock, max_loss_lock politikaları
- **Aksi halde TP/SL kavramları**: Oturum düzeyi hedeflerine (günlük TP/SL) taşınır

## 9.6 Dinamik Eşik & Tutar Uyarlaması

### 9.6.1 Volatiliteye Göre Eşik
- win_threshold_dyn = base + κ·z_vol; κ UI'dan 0–0.15

### 9.6.2 Performansa Göre Lot
- Son N işlem pozitif → a ← a·(1+δ); negatif → a ← a·(1−δ)
- δ küçük (0.05–0.10), a_cap ile sınırlı

### 9.6.3 Payout'a Göre Lot
- Düşük payout'ta tutarı azalt; yüksek payout'ta artırma sınırlı

## 9.7 Servis Akışı (psödo)

```python
if enter_allowed(ctx):
    amount = compute_amount(ctx)
    ack = place_order(ctx, amount)
    log_order(ack)
    res = await confirm_order(ack)
    log_result(res)
    risk.on_result(ctx, pnl=res.pnl, is_win=(res.status=='win'))
```

## 9.8 Python API (İskelet)

```python
# core/risk.py
from dataclasses import dataclass

@dataclass
class RiskLimits:
    max_daily_loss: float | None = 5.0
    max_consec_losses: int | None = 5
    a_min: float = 1.0
    a_cap: float = 10.0

@dataclass
class AmountPolicy:
    mode: str = "fixed"  # fixed | fraction | kelly_lite | atr_norm
    fixed_a: float = 1.0
    frac: float = 0.02  # 2% balance
    kelly_scale: float = 0.2  # 20% of Kelly

class RiskEngine:
    def __init__(self, limits: RiskLimits, amt: AmountPolicy):
        self.limits = limits
        self.amt = amt
        self._loss_streak = {}
        self._pnl_day = {}

    def enter_allowed(self, ctx) -> bool:
        if ctx.payout < ctx.permit_min or ctx.payout > ctx.permit_max:
            return False
        if ctx.confidence < ctx.win_threshold:
            return False
        if ctx.concurrency_blocked:
            return False
        if self._loss_streak.get(ctx.account, 0) >= (self.limits.max_consec_losses or 9999):
            return False
        if self._pnl_day.get(ctx.account, 0.0) <= -(self.limits.max_daily_loss or 9e9):
            return False
        return True

    def compute_amount(self, ctx) -> float:
        if self.amt.mode == "fixed":
            a = self.amt.fixed_a
        elif self.amt.mode == "fraction":
            a = ctx.balance * self.amt.frac
        elif self.amt.mode == "kelly_lite":
            R = ctx.payout
            p = max(0.0, min(1.0, ctx.prob_win))
            f_star = (p*(R+1)-1)/max(R,1e-6)
            a = ctx.balance * max(0.0, f_star) * self.amt.kelly_scale
        else:
            a = self.amt.fixed_a
        
        a = max(self.limits.a_min, min(a, self.limits.a_cap))
        return float(a)

    def on_result(self, ctx, pnl: float, is_win: bool):
        self._pnl_day[ctx.account] = self._pnl_day.get(ctx.account, 0.0) + pnl
        self._loss_streak[ctx.account] = 0 if is_win else self._loss_streak.get(ctx.account, 0) + 1
```

## 9.9 UI Eşlemesi

- **Ayarlar → Risk**: max_daily_loss, max_consec_losses, cooldown (taban/tavan), amount_mode, fixed_a, frac, kelly_scale, a_min, a_cap
- **Ayarlar → Permit & Eşik**: Ürün/TF bazında permit_min/max, win_threshold
- **Dashboard**: Günlük PnL, kayıp serisi, aktif cool down, beklenen değer (p̂, R_win, E[a])

## 9.10 Test Planı

- **Simülasyon**: MockConnector ile payout/p̂ varyasyonunda pozitif beklenen değer koşulunun seçildiği doğrulanır
- **Guardrails**: Günlük/ardışık kayıp aşımında durdur; cool down artışı
- **Lot sınırları**: a_min ≤ a ≤ a_cap; fraction/Kelly lite tavanlara uyar
- **Concurrency**: (hesap, ürün, TF) başına tek açık işlem kuralı ihlalsiz

## 9.11 Kabul Kriterleri

- Permit, confidence ve concurrency tabanlı giriş politikaları tanımlandı
- Lot modları (fixed, fraction, Kelly lite) ve sınırları uygulandı (varsayılan: fixed)
- Günlük/ardışık kayıp limitleri, cool down ve latency guard dokümante edildi
- UI ayarları, test planı ve kabul ölçütleri tamamlandı
