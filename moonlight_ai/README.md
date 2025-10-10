# MoonLight AI - Fixed Time Trading System

**MoonLight**, Android (telefon/tablet) ve Windows 10/11 üzerinde çalışabilecek, arka planda işlem yapabilen, demo ve gerçek hesaplarda işlemleri otomatikleştirebilen modüler bir Fixed-Time (binary / turbo) işlem yapay zekâsı projesidir.

## 🎯 Proje Hedefleri

- Sabit zamanlı (Fixed Time) kontratlarda demo ve gerçek hesapta otomatik işlem
- Hem Android hem Windows üzerinde çalışma
- Güvenli kimlik doğrulama ve şifreli veri saklama
- Kapsamlı test ve backtest yetenekleri
- Risk yönetimi ve para yönetimi
- Uyumluluk ve etik standartlara uygun geliştirme

## 🏗️ Mimari

### Core Engine (Python)
- Asenkron WebSocket/REST veri alma ve emir verme
- Strateji işleyici ve risk yöneticisi
- Simülasyon ve backtest modülleri

### API/Bridge
- Core ile istemciler arasında güvenli WebSocket/REST arayüzü
- TLS şifrelemesi ve token tabanlı kimlik doğrulama

### İstemciler
- **Windows Client**: Masaüstü GUI veya CLI
- **Android Client**: Hafif mobil istemci (gelecek sürümlerde)

## 📁 Proje Yapısı

```
moonlight_ai/
├── core/                   # Ana motor modülleri
│   ├── market_connector/    # Piyasa bağlantısı
│   ├── authentication/     # Kimlik doğrulama
│   ├── strategy_engine/     # Strateji motoru
│   ├── risk_manager/        # Risk yönetimi
│   ├── executor/           # İşlem yürütücü
│   └── persistence/        # Veri saklama
├── api/                    # API katmanı
│   ├── bridge/             # İstemci köprüsü
│   ├── security/           # Güvenlik
│   └── websocket/          # WebSocket sunucusu
├── clients/                # İstemci uygulamaları
│   ├── windows/            # Windows masaüstü
│   └── android/            # Android mobil
├── tests/                  # Test dosyaları
├── config/                 # Konfigürasyon
├── logs/                   # Log dosyaları
└── data/                   # Veri dosyaları
```

## 🚀 Kurulum

1. Python 3.9+ gereklidir
2. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

## ⚠️ Önemli Uyarılar

- Bu sistem yalnızca eğitim ve araştırma amaçlıdır
- Gerçek para ile işlem yapmadan önce kapsamlı testler yapın
- Platform hizmet şartlarını ve yerel yasaları kontrol edin
- Risk yönetimi kurallarını mutlaka uygulayın

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🤝 Katkıda Bulunma

Lütfen katkıda bulunmadan önce proje dokümantasyonunu ve etik kuralları inceleyin.