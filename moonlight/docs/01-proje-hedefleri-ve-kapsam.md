# 1. Proje Hedefleri ve Kapsam

## 1.1 Amaç ve Değer Önerisi

MoonLight, Windows 10/11 üzerinde çalışan bir sabit zamanlı (Fixed Time) işlem yapay zekâsıdır. Teknik analiz + ensemble + (opsiyonel) ML katmanlarıyla sinyal üretip kullanıcı tarafından tanımlanan risk kuralları dahilinde emir verir. Çoklu hesap işletimi, yüksek özelleştirilebilir UI, stabil servis, kayıt/öğrenme ve gözlemlenebilirlik ana hedeflerdir.

## 1.2 Kapsam (Fonksiyonel)

### 1.2.1 Hesap/Oturum Yönetimi
- **4 Hesap Eşzamanlı**: Tek PC'de aynı anda 4 farklı kullanıcı hesabı için izole profil (token/cookie kasası, bağımsız HTTP/WS oturumu, ayrı DB önekleri)
- **Güvenli Giriş**: Kullanıcı adı/e-posta + parola Windows DPAPI/Keyring ile saklanır. 2FA/OTP opsiyoneldir
- **Oturum Sağlığı**: Heartbeat/yeniden bağlanma, token yenileme, hatada kontrollü Retry/Abort

### 1.2.2 Veri Alma ve Zamanlama
- **Mumlar (OHLCV)** + mümkünse anlık fiyat ve payout/win rate bilgisi
- **TF Destekleri**: 1, 5, 15 dakika. Mum kapanışlarına hizalı tetikleyiciler
- **Gecikme Ölçümü**: Her çağrıda round trip latency log'lanır; eşik aşımlarında guardrail

### 1.2.3 Sinyal Üretimi (Analiz)
- **İndikatörler**: EMA/SMA/WMA/HMA, MACD/PPO, RSI/Stoch/StochRSI, Bollinger/Keltner, ATR, OBV/MFI/VWAP/CMF, ADX, Ichimoku, Supertrend, Donchian, Keltner, Pivot vb.
- **Strateji Kataloğu (Plugin)**: Her strateji bir signal provider olarak çalışır; ürün/TF bazında Aktif/Pasif ve parametre override UI'dan
- **Ensemble + Confidence**: Oy/ağırlık birleştirme → 0–1 güven skoru; eşik altında emir yok

### 1.2.4 Emir ve Risk Yönetimi
- **Concurrency Kuralı**: Aynı (hesap, ürün, TF) için tek açık işlem. 1/5/15 TF'leri birbirinden bağımsız paralel çalışır
- **Permit Penceresi**: Payout permit_min ≤ R ≤ permit_max aralığında değilse giriş yok
- **Win Rate Eşiği**: Ürün/TF bazında kullanıcı ayarlı (örn. ≥ %70)
- **Lot/Tutar Politikası**: Fixed, Balance Fraction, (ops.) Kelly lite; a_min/a_cap tavanları
- **Koruma Bariyerleri**: Günlük max kayıp, ardışık kayıp limiti, cool down, kill switch, circuit breaker
- **Idempotent Emir**: client_request_id ile çift emir engeli; PREPARE→SEND→CONFIRM→SETTLED durum makinesi

### 1.2.5 Öğrenme ve Kayıt
- **Feature Kaydı**: Her işlemde tüm indikatörler + bağlam özellikleri (payout, spread, latency) kaydedilir
- **Sonuç Kaydı**: win/lose, PnL, süre, latency
- **Win Rate İzleme**: Demo/gerçek ayrı; rolling pencereler (N=50/100)
- **Ağırlık Uyarlama**: Strateji/ensemble ağırlıkları son performansa göre adaptif
- **(Opsiyonel) ML**: sklearn baseline (logistic RF), ileride PyTorch (LSTM/Transformer) inference

### 1.2.6 UI (Windows Masaüstü)
- **Dashboard**: Çoklu hesap üstten seçim + bütünleşik görünüm; aktif işlemler, PnL, win rate, DD, latency
- **İşlem Menüsü**: Ürün/TF seçimi, win rate eşiği, permit min max, lot, guardrails; başlat/durdur/kaldır
- **Gelişmiş Ayarlar**: Ensemble ağırlıkları, öğrenme seçenekleri, cool down, saat filtreleri
- **Grafik Paneli**: Mum + indikatör overlay; PnL/win rate trendleri
- **Tema**: Mor/Mavi/Yeşil/Kırmızı/Siyah/Beyaz; koyu/açık mod; erişilebilirlik

## 1.3 Kapsam (Fonksiyonel Olmayan)

- **Windows Servis**: Core engine arka planda servis olarak; UI ayrı süreçten REST/WS ile bağlanır
- **Performans**: 100–300+ eşzamanlı (hesap×ürün×TF) izlemeyi hedefleyen asyncio işleyişi; back pressure ve rate limit kontrolleri
- **Güvenlik**: DPAPI/keyring, TLS, PII free logging, profil izolasyonu (profiles/accX/)
- **Uyumluluk**: Platform TOS ve yerel mevzuata uyum; anti bot atlatma yok
- **Gözlemlenebilirlik**: Yapılandırılmış JSON log, metrikler, alarm kanalları; crash free ≥ 24s hedefi

## 1.4 Çalışma Topolojisi

- **Core Konumu**: Core yerel Windows Servisi olarak çalışır
- **UI**: Masaüstü uygulaması (Flutter), localhost üzerinden core'a bağlanır (REST + WebSocket)
- **Neden Bu Tasarım?**: Arka plan sürekliliği (UI kapalıyken de sürdürme), kaynak izolasyonu ve güvenlik
- **Alternatif**: Gerekirse tek paket EXE içinde gömülü servis; fakat uzun süreli çalıştırmada ayrı servis tercih edilir

## 1.5 Kullanıcı Kontrolü

"Kullanıcı nasıl isterse öyle çalışsın" ilkesi: Tüm kritik parametreler UI'dan kullanıcı tarafından ayarlanır.

- **Demo↔Gerçek**: Dilediğin anda seçilebilir; istersen demo başarı eşiği şartı kaldırılabilir/aktif edilebilir
- **Paralellik Sınırı**: Kullanıcı belirler (global ve hesap bazında). Varsayılanı boş bırakıyoruz; set edilmezse core yalnız gözlem/paper modunda kalır

## 1.6 Varsayımlar ve Bağımlılıklar

- Broker erişimi için resmî veya izinli API/kanallar kullanılabilir olmalı; rate limit ve bakım pencereleri olabilir
- Windows 10/11 üzerinde yönetici olmayan kullanıcı haklarıyla çalışabilmeli; port dinleme yalnızca loopback
- Donanım: Çoklu iş için yeterli CPU/ram; disk alanı (SQLite + loglar)

## 1.7 Kabul Kriterleri

- Windows 10/11 odak + 4 hesap desteği dokümante
- Core = Windows Servisi, UI = masaüstü istemci topolojisi net
- Kullanıcı kontrollü win rate eşiği, permit penceresi, lot ve guardrails tanımlı
- Paralellik sınırları kullanıcıya bırakıldı; set edilmezse paper mod davranışı belirli
- Güvenlik/uyumluluk ve kayıt/öğrenme gereksinimleri net

## 1.8 Başarı Ölçütleri

- Uptime ≥ %99 (iş saatleri); emir turu < 2s (bağlantıya bağlı)
- Kaydı tutarlılık: orders→results→features zincirinde at least once; boot'ta reconcile ile bütünlük
- UX: Tüm ayarlar 1–2 tıkla; panic/kill switch; anlık metrik akışı (WS)

## 1.9 Kullanım Senaryoları (Örnek)

- **S1**: 4 hesapla EURUSD 1/5/15 dakikada, permit %89–%93, win threshold %72; 1 dakikada tek açık işlem kuralı
- **S2**: BTCUSD'de yalnızca 5 dakikalık stratejiler aktif; RVOL yüksekse bekle; günlük max loss 5 birim
- **S3**: Demo'da 2 hafta paper; 100 işlem penceresinde win rate ≥ hedef görülürse gerçek hesaba geçiş
