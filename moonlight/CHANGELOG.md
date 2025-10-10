# Changelog

All notable changes to MoonLight will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-10

### Added
- 🎉 Initial MVP release
- ✅ Core engine with Python asyncio
- ✅ Multi-account support (up to 4 accounts)
- ✅ Mock connector for paper trading
- ✅ 50+ strategy catalog (8 implemented in MVP)
- ✅ Ensemble voting and Platt calibration
- ✅ Risk management (daily loss, consecutive loss, circuit breaker)
- ✅ SQLite storage with WAL mode
- ✅ Idempotent order execution (FSM)
- ✅ Structured JSON logging with PII masking
- ✅ Metrics and telemetry (counter, gauge, histogram)
- ✅ FastAPI server for UI communication (loopback)
- ✅ WebSocket support for real-time updates
- ✅ Flutter desktop UI foundation (Windows)
- ✅ Backtesting engine
- ✅ Configuration management (YAML)
- ✅ Kill switch and guardrails
- ✅ TOS compliance framework

### Strategies (MVP)
- ID 5-7: EMA Trend + RSI (neutral, conservative, aggressive)
- ID 14: EMA 9/21 Crossover
- ID 15-18: VWAP Reclaim + RVOL (various thresholds)
- ID 25-28: Supertrend + ADX (various ADX thresholds)

### Security
- ✅ Windows DPAPI/Keyring integration
- ✅ PII masking (email, phone, tokens)
- ✅ Loopback-only API (127.0.0.1)
- ✅ Secret-free logs and configs
- ✅ Audit trail for all decisions

### Documentation
- ✅ Architecture overview
- ✅ Getting started guide
- ✅ Strategy development guide
- ✅ Security and compliance guide
- ✅ Installation guide
- ✅ API reference (auto-generated)

### Technical Details
- **Python**: 3.10+
- **Flutter**: 3.16+
- **Database**: SQLite with WAL
- **API**: FastAPI + WebSocket
- **State**: Riverpod
- **Theme**: Material 3, Purple/Blue/Green/Red palette

## [Upcoming] - Roadmap

### [1.1.0] - Planned
- 🔄 Real Olymp Trade connector (with authorized endpoints only)
- 🔄 Hot-reload configuration
- 🔄 Advanced calibration (Isotonic regression)
- 🔄 Drift detection (ADWIN, Page-Hinkley)
- 🔄 Walk-forward validation
- 🔄 Support bundle auto-generation

### [1.2.0] - Planned
- 🔄 Machine learning models (scikit-learn baseline)
- 🔄 Feature engineering pipelines
- 🔄 A/B testing framework
- 🔄 Canary deployment
- 🔄 Prometheus exporter
- 🔄 Enhanced UI (charts, heatmaps)

### [1.3.0] - Planned
- 🔄 PyTorch models (LSTM, Transformer)
- 🔄 Multi-device sync (optional)
- 🔄 Android support
- 🔄 Advanced regime detection
- 🔄 Hierarchical RL

### [2.0.0] - Future
- 🔄 Multi-broker support
- 🔄 Cloud deployment option
- 🔄 Advanced ML pipelines
- 🔄 Distributed learning

## Security Updates

### Critical
- None

### Important
- None

## Known Issues

### v1.0.0
- [ ] Real connector not implemented (mock only)
- [ ] Hot-reload not supported (restart required)
- [ ] Limited strategy parameters in UI
- [ ] No built-in optimizer for hyperparameters

---

## Migration Guides

### 0.x → 1.0.0
Not applicable (initial release)

---

For security vulnerabilities, please contact: security@moonlight.local

**DO NOT** open public issues for security concerns.
