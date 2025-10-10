# 13. UI (Flutter) Bilgi Mimarisi & Ekran Akışları

## 13.1 Teknoloji ve Mimarî

- **Framework**: Flutter (stable channel), hedef Windows desktop
- **Durum Yönetimi**: Riverpod (StateNotifier/AsyncNotifier) — basit, test edilebilir
- **İletişim**: Core servis ile REST (http) ve WebSocket (anlık metrik/olay)
- **Modülerlik**: Özellik bazlı paketleme (feature-first): accounts, products, strategies, trading, settings, logs, charts
- **Theming**: Light/Dark; renk tokenları (mor/mavi/yeşil/kırmızı/siyah/beyaz) ve erişilebilir kontrast
- **Yerelleştirme**: tr-TR varsayılan; intl ile çok dillilik

## 13.2 Ana Gezinti (Navigation)

- **Sol Kenar Çubuk (NavigationRail)**:
  1. Dashboard
  2. Hesaplar
  3. Ürünler & TF
  4. Strateji Kataloğu
  5. İşlemler & Geçmiş
  6. Grafikler
  7. Ayarlar
  8. Loglar/Alarm

- **Üst Bar**: Aktif hesap seçici (dropdown, çoklu seçim), Kill-Switch, Play/Pause (global), tema anahtarı, durum LED'leri (Core bağlantı, WS canlı, servis durumu)

## 13.3 Ekranlar ve İçerikler

### 13.3.1 Dashboard
- **KPI Kartları**: Toplam PnL (gün/hafta/ay), win-rate (demo/gerçek ayrı), açık işlem sayısı, ort. latency, ardışık kayıp, günlük risk kullanımı
- **Canlı Akış**: Son işlemler tablosu (hesap, ürün, TF, yön, tutar, durum, payout, p̂, latency)
- **Durum Paneli**: Core servis durumu, scheduler/worker sayısı, hata sayacı, alarm bildirimleri
- **Hızlı Aksiyonlar**: Tüm ürünlerde Başlat/Durdur; Profil yükle/kaydet

### 13.3.2 Hesaplar
- **Hesap Listesi** (en fazla 4): id, kullanıcı adı, profil yolu, durum (bağlı/bağsız), son login, bakiye (okunabiliyorsa)
- **Güvenli Giriş**: Keyring servis adı; parola girişi ayrı modal (parola UI'da saklanmaz)
- **Oturum Testi**: Login denemesi, heartbeat, izin/payout sorgusu
- **Limitler**: Hesap bazlı max_parallel, max_daily_loss, max_consecutive_losses

### 13.3.3 Ürünler & TF
- **Ağaç Görünüm**: Ürün → TF(1/5/15)
- **Her TF için kart**: Enabled, win_threshold, permit_min/max, lot/tutar modu, concurrency=1 (sabit), cool down
- **Çoklu seç-ke uygulama**: Birden fazla TF'ye aynı ayarı uygula (ör. permit aralığını topluca değiştir)

### 13.3.4 Strateji Kataloğu
- **Kart Izgara**: (ID, ad, grup) + kısa açıklama
- **Detay Modal**: Parametreler (ör. EMA 20/50, RSI 14, RVOL thr…), warm up, son N işlemde win%
- **Presetler**: Kullanıcının sunduğu varyantlar (ör. RVOL 1.1/1.15/1.2/1.3/1.5) tek tıkla
- **Aktifleştirme**: Ürün/TF bazında stratejiyi aç/kapat ve param override

### 13.3.5 İşlemler & Geçmiş
- **Tablo**: Zaman, hesap, ürün, TF, yön, tutar, payout, p̂, sonuç (win/lose/abort), PnL, latency
- **Filtreler**: Tarih aralığı, ürün, TF, hesap, sonuç
- **Dışa Aktarım**: CSV/Parquet
- **Detay**: Bir işlem tıklandığında order/result/features özet (gizlilik kurallarıyla)

### 13.3.6 Grafikler
- **Mum Grafiği + overlay**: EMA/SMA/BB/Keltner/Supertrend/Ichimoku seçilebilir
- **Alt Paneller**: RSI, MACD, Stoch, ADX, CMF, RVOL
- **Sinyal İşaretleri**: Sağlayıcı vote'larının işaretçileri (↑/↓), giriş noktaları, sonuç renklendirmesi
- **Performans Grafikleri**: Rolling win rate, PnL eğrisi, latency histogramı

### 13.3.7 Ayarlar
- **Genel**: Dil, tema, tablo yoğunluğu, tarih/saat formatı
- **Motor (Engine)**: tick_ms, grace_ms, jitter_ms, entry_cutoff_s, lookback
- **Risk**: max_daily_loss, max_consec_losses, amount_mode, fixed_a, frac, kelly_scale, a_min, a_cap
- **Permit/Eşik**: Ürün/TF bazlı varsayılanlar
- **Ensemble**: ensemble_mode, c_min, s_cap, alpha, w_max, kalibrasyon durumu ve yeniden kalibre et
- **Bağlantı**: Core loopback adresi, WS tercihi; yalnızca yerel izin

### 13.3.8 Loglar & Alarm
- **Canlı Log (WS)**: system.log ve trade.log akışı; arama/filtreleme
- **Alarm Merkezi**: Guardrail tetikleri (günlük kayıp, ardışık kayıp, latency abort, permit dışı, connector hata)
- **Bildirim**: Windows toast (ops.) + uygulama içi badge

### 13.3.9 Onboarding
- **3 adım sihirbaz**: (1) Hesap ekle & parola kasası, (2) Ürün/TF + eşikler, (3) Strateji presetleri & risk
- **Son adımda Paper Mod ile başlat önerisi**: Kill switch öğretimi

## 13.4 Durum Mimarisi (Riverpod)

### 13.4.1 Providers
- **coreClientProvider**: REST/WS istemcisi
- **accountsProvider**: Liste + bağlantı durumu
- **productsProvider**: Ağaç yapı
- **workersProvider**: Aktif (acc,prod,tf)
- **metricsStreamProvider**: WS'den anlık metrik
- **logsStreamProvider**: Log akışı
- **ordersNotifier**: Arama/filtre/indir
- **settingsNotifier**: Config görüntüle/güncelle

### 13.4.2 Hata Durumları
- AsyncValue ile yükleniyor/başarısız; kullanıcıya aksiyon önerisi (yeniden dene, config aç)

## 13.5 Performans & UX

- **Sanal Liste**: Büyük tablolarda virtualization
- **Debounce/Throttle**: Arama/filtre alanları
- **Grafik Performansı**: İzlence penceresi (ör. 500–2000 bar) + lazily compute
- **Klavye Kısayolları**: Ctrl+K (komut paleti), Ctrl+P (Play/Pause), Ctrl+Shift+X (kill switch)
- **Erişilebilirlik**: Kontrast ≥ 4.5:1, focus ring, screen reader etiketleri

## 13.6 Tema & Renkler (Tokenlar)

### 13.6.1 Temel Renkler
- **Mor**: #6D28D9
- **Mavi**: #2563EB
- **Yeşil (pozitif)**: #10B981
- **Kırmızı (negatif/uyarı)**: #EF4444
- **Siyah**: #0B0F14 (arka plan – dark)
- **Beyaz**: #FFFFFF (arka plan – light)

### 13.6.2 Durum Renk Haritası
- **Win**: Yeşil
- **Lose**: Kırmızı
- **Paused**: Sarımsı amber #F59E0B
- **Running**: Mavi
- **Risk near**: Turuncu #F97316
- **Circuit breaker**: Koyu kırmızı + uyarı simgesi

### 13.6.3 Tipografi
- **Başlık**: TitleLarge kalın, metin: BodyMedium; sayılar tabular nums (eşit aralıklı) – okunabilirlik için

### 13.6.4 Yoğunluk & Layout
- **Desktop grid**: Sol NavigationRail (dar/geniş mod), üst AppBar (hesap anahtarı), içerik ResponsiveGrid (1–3 sütun)

## 13.7 Proje Yapısı (Flutter)

```
ui_app/
├── main.dart
├── app/
│   ├── app.dart              # MaterialApp, theme, router
│   ├── theme.dart            # renk paleti, koyu/açık şema
│   └── router.dart           # go_router rotaları
├── core/
│   ├── api_client.dart       # REST/WS istemci sarmalayıcı
│   ├── models.dart           # DTO'lar (freezed)
│   ├── store.dart            # Riverpod provider'ları (state)
│   ├── format.dart           # para, tarih, yüzde yardımcıları
│   └── charts.dart           # standart graf bileşenleri
├── features/
│   ├── dashboard/
│   ├── accounts/
│   ├── products/
│   ├── strategies/
│   ├── backtest/
│   ├── orders/
│   ├── logs/
│   ├── settings/
│   └── alerts/
├── widgets/
│   ├── cards.dart
│   ├── tables.dart
│   ├── forms.dart
│   └── badges.dart
└── pubspec.yaml
```

## 13.8 Bileşenler (Örnek)

- **AccountCard**: Durum LED, login testi, limit ayarları
- **TFCard**: Permit, win threshold, lot modu; concurrency/guardrail rozetleri
- **StrategyTile**: Ad, açıklama, preset seçici, param formu
- **MetricSparkline**: Mini win rate/PnL eğrisi
- **LogView**: Filtrelenebilir canlı log
- **OrderTable**: Sanal liste + sütun seçici + CSV indir

## 13.9 Hata/Alarm UX Politikası

- **Kritik** (kill switch tetik, günlük kayıp aşımı): Modal + Toast + Alarm sayacı
- **Orta** (retry, backoff): Banner/Toast
- **Düşük** (UI doğrulama): inline hata mesajı
- **Tekrar eden alarmlar**: Konsolide edilir; sessize al seçeneği

## 13.10 Güvenlik & Gizlilik UX

- **Parola girişleri**: Maskeli ve yalnız keyring'e gider
- **Loglarda PII yok**: Hassas alanlar ••• maskeli gösterilir
- **Dışa aktarımda**: Kullanıcıya anonimleştirme seçeneği sunulur

## 13.11 Kabul Kriterleri

- Tüm ana ekranlar ve gezinti akışı tanımlandı
- Riverpod tabanlı durum modeli ve WS/REST entegrasyonu netleşti
- Renk/tema tokenları, kontrast ve erişilebilirlik ilkeleri belirlendi
- Tablo/grafik performansı, hata/alarm UX politikaları ve bileşen listesi hazır
