# 4. Konfigürasyon Şeması (JSON/YAML) + Örnekler

## 4.1 Tasarım İlkeleri

- **Tek doğruluk kaynağı**: config.json (alternatif config.yaml)
- **Hiyerarşi**: Global → Hesap → Ürün → Timeframe → Strateji
- **Hot reload**: Güvenli alanlar çalışma sırasında değiştirilebilir (örn. win threshold); kritik alanlar kontrollü yeniden başlatma ister
- **Sırlar dışarıda**: Parola/token DPAPI/Keyring'de; config içinde yalnız profil/anahtar adı tutulur
- **Versiyonlama**: config_version ile göç (migration) kolaylığı

## 4.2 Alanların Anlamı (özet)

- **ensemble_threshold** (0–1): Strateji birleşik güven eşiği
- **limits**: Paralellik ve guardrail sınırları (Set edilmezse paper/gözlem modu)
- **accounts[]**: Çoklu hesap profilleri; her biri ayrı oturum/kasa/dizin
- **products[]**: Ürünler; TF listesi ve strateji seçimi içerir
- **timeframes[].win_threshold** (0–1): O TF'de başarı eşiği
- **timeframes[].permit_min/permit_max** (%): Payout/win rate penceresi
- **risk**: Lot/SL/TP ve guardrail varsayılları
- **engine**: Worker periyotları, kuyruk boyutları, latency gardı
- **storage**: SQLite/CSV yol ve ayarları
- **logging**: Log seviyesi, rotasyon, dosya yolları
- **ui**: Tema/renkler/özellik bayrakları

## 4.3 JSON Şeması (kısaltılmış)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MoonLight Config",
  "type": "object",
  "required": ["config_version", "accounts", "products"],
  "properties": {
    "config_version": {"type": "string", "pattern": "^1\\.\\d+\\.\\d+$"},
    "ensemble_threshold": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.70},
    "limits": {
      "type": "object",
      "properties": {
        "max_parallel_global": {"type": ["integer", "null"], "minimum": 1},
        "max_parallel_per_account": {"type": ["integer", "null"], "minimum": 1},
        "max_daily_loss": {"type": ["number", "null"]},
        "max_consecutive_losses": {"type": ["integer", "null"]}
      },
      "additionalProperties": false
    },
    "accounts": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "username", "profile_store"],
        "properties": {
          "id": {"type": "string"},
          "username": {"type": "string"},
          "profile_store": {"type": "string"},
          "keyring_service": {"type": "string", "default": "moonlight-olymp"},
          "session": {
            "type": "object",
            "properties": {
              "http_user_agent": {"type": "string"},
              "ws_heartbeat_s": {"type": "integer", "default": 20}
            },
            "additionalProperties": false
          }
        },
        "additionalProperties": false
      }
    },
    "products": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["product", "timeframes"],
        "properties": {
          "product": {"type": "string"},
          "enabled": {"type": "boolean", "default": true},
          "strategies": {"type": "array", "items": {"type": "integer"}},
          "timeframes": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["tf", "enabled"],
              "properties": {
                "tf": {"type": "integer", "enum": [1,5,15]},
                "enabled": {"type": "boolean"},
                "win_threshold": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.70},
                "permit_min": {"type": "number", "minimum": 0, "maximum": 100},
                "permit_max": {"type": "number", "minimum": 0, "maximum": 100},
                "risk": {
                  "type": "object",
                  "properties": {
                    "lot": {"type": "number", "minimum": 0},
                    "tp_R": {"type": ["number", "null"]},
                    "sl_ATR_mult": {"type": ["number", "null"]}
                  },
                  "additionalProperties": false
                }
              },
              "additionalProperties": false
            }
          }
        },
        "additionalProperties": false
      }
    },
    "risk": {
      "type": "object",
      "properties": {
        "default_lot": {"type": "number", "default": 1},
        "default_tp_R": {"type": ["number", "null"], "default": 1.5},
        "default_sl_ATR_mult": {"type": ["number", "null"], "default": 1.2}
      },
      "additionalProperties": false
    },
    "engine": {
      "type": "object",
      "properties": {
        "queue_maxsize": {"type": "integer", "default": 1000},
        "latency_warn_ms": {"type": "integer", "default": 800},
        "latency_abort_ms": {"type": "integer", "default": 2500},
        "tick_interval_ms": {"type": "integer", "default": 250}
      },
      "additionalProperties": false
    },
    "storage": {
      "type": "object",
      "properties": {
        "sqlite_path": {"type": "string", "default": "data/trades.db"},
        "dataset_csv": {"type": "string", "default": "data/ml_dataset.csv"}
      },
      "additionalProperties": false
    },
    "logging": {
      "type": "object",
      "properties": {
        "level": {"type": "string", "enum": ["DEBUG","INFO","WARN","ERROR"], "default": "INFO"},
        "file": {"type": "string", "default": "logs/moonlight.log"},
        "rotate_mb": {"type": "integer", "default": 10},
        "keep_files": {"type": "integer", "default": 7}
      },
      "additionalProperties": false
    },
    "ui": {
      "type": "object",
      "properties": {
        "theme": {"type": "string", "enum": ["dark","light"], "default": "dark"},
        "colors": {"type": "object"}
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

## 4.4 Örnek config.json (Windows + 4 hesap)

```json
{
  "config_version": "1.0.0",
  "ensemble_threshold": 0.72,
  "limits": {
    "max_parallel_global": null,
    "max_parallel_per_account": null,
    "max_daily_loss": 5,
    "max_consecutive_losses": 5
  },
  "accounts": [
    {"id": "acc1", "username": "user1@mail", "profile_store": "profiles/acc1/", "keyring_service": "moonlight-olymp"},
    {"id": "acc2", "username": "user2@mail", "profile_store": "profiles/acc2/"},
    {"id": "acc3", "username": "user3@mail", "profile_store": "profiles/acc3/"},
    {"id": "acc4", "username": "user4@mail", "profile_store": "profiles/acc4/"}
  ],
  "products": [
    {
      "product": "EURUSD",
      "enabled": true,
      "strategies": [5,6,14,24,25,32],
      "timeframes": [
        {"tf": 1, "enabled": true, "win_threshold": 0.72, "permit_min": 89, "permit_max": 93, "risk": {"lot": 1, "tp_R": 1.5, "sl_ATR_mult": 1.2}},
        {"tf": 5, "enabled": true, "win_threshold": 0.72, "permit_min": 90, "permit_max": 93, "risk": {"lot": 1, "tp_R": 1.8, "sl_ATR_mult": 1.2}},
        {"tf": 15, "enabled": false, "win_threshold": 0.70, "permit_min": 0, "permit_max": 100, "risk": {"lot": 1, "tp_R": null, "sl_ATR_mult": null}}
      ]
    },
    {
      "product": "BTCUSD",
      "enabled": true,
      "strategies": [14,25,35],
      "timeframes": [
        {"tf": 1, "enabled": true, "win_threshold": 0.75, "permit_min": 85, "permit_max": 95, "risk": {"lot": 1, "tp_R": 2.0, "sl_ATR_mult": 1.5}},
        {"tf": 5, "enabled": true, "win_threshold": 0.74, "permit_min": 86, "permit_max": 94, "risk": {"lot": 1, "tp_R": 1.8, "sl_ATR_mult": 1.3}}
      ]
    }
  ],
  "risk": {"default_lot": 1, "default_tp_R": 1.5, "default_sl_ATR_mult": 1.2},
  "engine": {"queue_maxsize": 2000, "latency_warn_ms": 800, "latency_abort_ms": 2500, "tick_interval_ms": 250},
  "storage": {"sqlite_path": "data/trades.db", "dataset_csv": "data/ml_dataset.csv"},
  "logging": {"level": "INFO", "file": "logs/moonlight.log", "rotate_mb": 10, "keep_files": 7},
  "ui": {"theme": "dark", "colors": {"primary": "#6D28D9", "accent": "#2563EB"}}
}
```

## 4.5 Aynı yapı YAML örneği

```yaml
config_version: "1.0.0"
ensemble_threshold: 0.72
limits:
  max_parallel_global: null
  max_parallel_per_account: null
  max_daily_loss: 5
  max_consecutive_losses: 5
accounts:
  - id: acc1
    username: user1@mail
    profile_store: profiles/acc1/
    keyring_service: moonlight-olymp
  - id: acc2
    username: user2@mail
    profile_store: profiles/acc2/
products:
  - product: EURUSD
    enabled: true
    strategies: [5,6,14,24,25,32]
    timeframes:
      - tf: 1
        enabled: true
        win_threshold: 0.72
        permit_min: 89
        permit_max: 93
        risk: { lot: 1, tp_R: 1.5, sl_ATR_mult: 1.2 }
      - tf: 5
        enabled: true
        win_threshold: 0.72
        permit_min: 90
        permit_max: 93
        risk: { lot: 1, tp_R: 1.8, sl_ATR_mult: 1.2 }
  - product: BTCUSD
    enabled: true
    strategies: [14,25,35]
    timeframes:
      - tf: 1
        enabled: true
        win_threshold: 0.75
        permit_min: 85
        permit_max: 95
        risk: { lot: 1, tp_R: 2.0, sl_ATR_mult: 1.5 }
```

## 4.6 Hot Reload Kuralları

- **Yeniden başlatma gerektirmez**: win_threshold, permit_*, strategies (aktif/pasif), risk.lot, logging.level
- **Kontrollü yeniden başlatma**: Ürün/TF ekleme çıkarma, ensemble_threshold, engine.tick_interval_ms
- **Servis yeniden başlatma**: storage.sqlite_path, accounts[] (profil yolları), büyük topoloji değişimleri

## 4.7 Geçerlilik Kuralları (validation)

- permit_min ≤ permit_max ve her ikisi de [0,100]
- win_threshold ≥ ensemble_threshold önerilir (aksi durumda uyarı)
- (ürün,TF) tek açık işlem kuralı sabittir; config ile artırılamaz
- max_daily_loss/max_consecutive_losses null ise ilgili guardrail pasif

## 4.8 Sırlar (Keyring) — Kullanım Notu

- Config'te yalnız accounts[].username ve keyring_service saklanır
- Parola kurulumda tek seferlik: `keyring.set_password("moonlight-olymp", "user1@mail", "PAROLA")`
- Core çalışırken `keyring.get_password(...)` ile çeker; disk üzerinde parola yoktur

## 4.9 Kabul Kriterleri

- JSON/YAML şeması ve örnekler eksiksiz
- Hot reload alanları ve yeniden başlatma kuralları belirgin
- 4 hesap ve TF/ürün bazlı ayarlar kapsandı
- Keyring/DPAPI modelinin uygulanma yolu net
