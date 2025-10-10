# 📝 Changelog

Tüm önemli değişiklikler bu dosyada belgelenir.

Format [Keep a Changelog](https://keepachangelog.com/) standardını takip eder.
Versiyonlama [Semantic Versioning](https://semver.org/) kullanır.

## [Unreleased]

### Planlanmış
- UI (Flutter Desktop)
- Daha fazla strateji (10+ plugin)
- Catalog/Payout service
- Backtest engine
- Windows Service packaging

## [1.0.0-alpha] - 2025-10-10

### Added - İlk MVP sürümü

#### Core Modüller
- **Config**: Pydantic şema, YAML/JSON loader, validation
- **Storage**: SQLite + WAL, Orders/Results/Features/Metrics tabloları
- **Connector**: Interface, MockConnector, ConnectorManager
- **Indicators**: 30+ teknik gösterge (Basic + Advanced)
- **Strategies**: Plugin sistemi, Registry, örnek EMA+RSI stratejisi
- **Ensemble**: Ağırlıklı oylama, Platt kalibrasyon, confidence
- **Risk**: Position sizing (Fixed/Fraction/Kelly), Guardrails
- **Executor**: Order FSM (PREPARE→SEND→CONFIRM→SETTLED)
- **Worker**: TF-aligned döngü, bar kapanış tetikleme
- **Scheduler**: Worker lifecycle, start/stop
- **Telemetry**: JSON logging (PII maskeli), Metrics collection
- **API**: FastAPI REST + WebSocket, localhost only

#### Güvenlik
- PII masking (e-posta, telefon)
- Idempotent orders (client_req_id)
- Fail-closed defaults
- Localhost-only binding

#### Dokümantasyon
- README.md: Genel bakış ve hızlı başlangıç
- INSTALL.md: Detaylı kurulum
- ARCHITECTURE.md: Sistem mimarisi
- STRATEGIES.md: Strateji geliştirme kılavuzu
- OPERATIONS.md: Günlük işletim ve sorun giderme

#### Test
- test_config.py: Konfigürasyon testleri
- test_indicators.py: İndikatör doğruluk testleri
- test_storage.py: Veritabanı testleri
- smoke_test.py: Uçtan uca temel test

#### Konfigürasyon
- config.example.yaml: Tam özellikli örnek
- 4 hesap desteği
- Çoklu ürün/TF ayarları
- Strateji seçimi ve parametre

### Technical Details

**Teknolojiler:**
- Python 3.10+
- FastAPI + Uvicorn
- SQLite + aiosqlite
- Pandas + NumPy
- Pydantic

**Mimari Prensipler:**
- Async-first (asyncio)
- Plugin pattern (strategies)
- Fail-closed (güvenlik)
- Single responsibility (modüller)
- Idempotency (FSM)

**Performans Hedefleri:**
- Indicator: p90 < 10 ms / 200 bar
- API /status: p90 < 300 ms
- Order latency: p90 < 2000 ms

## Katkıda Bulunanlar

- **Core Engine**: MoonLight Team
- **Proje Planı**: 30+ parçalık kapsamlı belge (ML.docx)
- **Mimari**: Modüler, güvenli, ölçeklenebilir

## Notlar

### [1.0.0-alpha] Hakkında

Bu ilk alfa sürümüdür ve **sadece test/geliştirme** amaçlıdır:

- ✅ Paper mode tam destekli
- ⚠️ Live mode için gerçek connector gerekli
- ⚠️ UI henüz yok (API hazır)
- ⚠️ Production packaging yok

**Uyarı**: Finansal işlemlerde kullanmadan önce kapsamlı testler zorunludur.

---

**Son Güncelleme**: 2025-10-10
