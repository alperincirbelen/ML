# MoonLight — Fixed Time İşlem AI

## Proje Özeti

MoonLight, Android (telefon/tablet) ve Windows 10/11 üzerinde çalışabilecek, arka planda işlem yapabilen, demo ve gerçek hesaplarda işlemleri otomatikleştirebilen modüler bir Fixed-Time (binary / turbo) işlem yapay zekâsı projesidir. Sistem; güvenlik, uyumluluk, geri test (backtest), paper-trading, risk yönetimi ve takip/izleme özelliklerine sahip olacaktır.

## İçindekiler

1. [Proje hedefleri ve kapsam](#1-proje-hedefleri-ve-kapsam)
2. [Hukuk, uyumluluk ve etik](#2-hukuk-uyumluluk-ve-etik)
3. [Yüksek seviyeli mimari](#3-yüksek-seviyeli-mimari)
4. [Modüller ve geliştirme rehberi](#4-modüller-ve-geliştirme-rehberi)
5. [Platforma göre dağıtım stratejisi](#5-platforma-göre-dağıtım-stratejisi)
6. [Güvenlik ve gizlilik uygulamaları](#6-güvenlik-ve-gizlilik-uygulamaları)
7. [Test, validation ve dağıtım](#7-test-validation-ve-dağıtım)
8. [MVP yol haritası](#8-mvp-yol-haritası)
9. [Dosya/klasör yapısı](#9-dosyaklasör-yapısı)
10. [Kullanılacak kütüphaneler ve araçlar](#10-kullanılacak-kütüphaneler-ve-araçlar)
11. [İzleme, loglama ve hata yönetimi](#11-izleme-loglama-ve-hata-yönetimi)
12. [Risk yönetimi ve backtesting](#12-risk-yönetimi-ve-backtesting)
13. [Etik kısıtlamalar ve yasaklar](#13-etik-kısıtlamalar-ve-yasaklar)
14. [İleri aşama ML/AI özellikleri](#14-ileri-aşama-mlai-özellikleri)
15. [Geliştirme kalitesi](#15-geliştirme-kalitesi)
16. [Sonraki adımlar](#16-sonraki-adımlar)

## Teknoloji Stack

- **Core Engine**: Python 3.10+ (asyncio, event-driven)
- **UI**: Flutter (Windows desktop), Kotlin (Android - future)
- **Database**: SQLite + CSV/Parquet
- **Communication**: REST/WebSocket (TLS)
- **Security**: Windows DPAPI/Keyring, PII redaction
- **Trading**: Fixed-Time contracts, demo/real accounts

## Proje Yapısı

```
moonlight/
├── core/                    # Python core engine
│   ├── api/                 # REST/WebSocket API
│   ├── connector/           # Broker connectors
│   ├── indicators/          # Technical indicators
│   ├── strategies/          # Strategy providers
│   ├── ensemble.py          # Signal combination
│   ├── risk.py             # Risk management
│   ├── worker.py           # Trading workers
│   ├── storage.py          # Data persistence
│   ├── telemetry.py        # Metrics & logging
│   ├── scheduler.py        # Task scheduling
│   └── main.py             # Service entry point
├── ui_app/                  # Flutter Windows UI
│   ├── lib/
│   │   ├── screens/        # UI screens
│   │   ├── widgets/        # Reusable components
│   │   ├── theme/          # UI theming
│   │   └── services/       # API clients
├── docs/                    # Documentation
├── data/                    # Data storage
└── tests/                   # Test suites
```

## Hızlı Başlangıç

1. **Kurulum**: Windows 10/11 üzerinde Python 3.10+ ve Flutter kurulumu
2. **Konfigürasyon**: `config.json` dosyasını düzenleyin
3. **Demo Mod**: Paper trading ile test edin
4. **Gerçek Hesap**: Demo başarı sonrası gerçek hesaba geçin

## Güvenlik Uyarısı

⚠️ **ÖNEMLİ**: Bu yazılım yalnızca eğitim ve araştırma amaçlıdır. Gerçek para ile işlem yapmadan önce:
- Platform hizmet şartlarını inceleyin
- Yerel mevzuatı kontrol edin
- Demo hesapta kapsamlı test yapın
- Risk yönetimi kurallarını uygulayın

## Lisans

Bu proje eğitim ve araştırma amaçlıdır. Ticari kullanım için gerekli izinleri alın.

## Katkıda Bulunma

Proje geliştirme aşamasındadır. Katkılar için lütfen önce iletişime geçin.

## İletişim

Proje hakkında sorularınız için GitHub Issues kullanın.
