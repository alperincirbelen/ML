"""
Configuration Management Module

Parça 3 - Konfig & Profil Yönetimi
Tek doğruluk kaynağı: app.yaml
"""

from __future__ import annotations
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ModeEnum(str, Enum):
    """Çalışma modu"""
    PAPER = "paper"
    LIVE = "live"


class ConnectorEnum(str, Enum):
    """Bağlayıcı tipi"""
    MOCK = "mock"
    OLYMP = "olymp"


class PermitModeEnum(str, Enum):
    """Permit penceresi modu"""
    CONFIG_ONLY = "config_only"
    PREFER_CACHE = "prefer_cache"
    CACHE_ONLY = "cache_only"


class SessionConfig(BaseModel):
    """Oturum ayarları"""
    http_user_agent: str = "MoonLight/1.0"
    ws_heartbeat_s: int = 20


class AccountConfig(BaseModel):
    """Hesap yapılandırması"""
    id: str
    username: str
    profile_store: str
    keyring_service: str = "moonlight-olymp"
    session: SessionConfig = Field(default_factory=SessionConfig)


class RiskConfig(BaseModel):
    """Risk parametreleri"""
    lot: Optional[float] = None
    tp_R: Optional[float] = None
    sl_ATR_mult: Optional[float] = None


class TimeframeConfig(BaseModel):
    """Zaman dilimi ayarları"""
    tf: int = Field(..., ge=1, le=15)
    enabled: bool = True
    win_threshold: float = Field(0.70, ge=0.5, le=0.99)
    permit_min: float = Field(0.0, ge=0.0, le=100.0)
    permit_max: float = Field(100.0, ge=0.0, le=100.0)
    risk: Optional[RiskConfig] = None

    @field_validator('permit_max')
    @classmethod
    def validate_permit_range(cls, v, info):
        if 'permit_min' in info.data and v < info.data['permit_min']:
            raise ValueError('permit_max must be >= permit_min')
        return v


class ProductConfig(BaseModel):
    """Ürün yapılandırması"""
    product: str
    enabled: bool = True
    strategies: List[int] = Field(default_factory=list)
    timeframes: List[TimeframeConfig] = Field(default_factory=list)


class LimitsConfig(BaseModel):
    """Limit ve koruma ayarları"""
    max_parallel_global: Optional[int] = Field(None, ge=1)
    max_parallel_per_account: Optional[int] = Field(None, ge=1)
    max_daily_loss: Optional[float] = Field(None, gt=0)
    max_consecutive_losses: Optional[int] = Field(None, ge=1)
    rate_limit_per_min: int = Field(60, ge=1, le=300)


class RiskDefaults(BaseModel):
    """Risk varsayılanları"""
    default_lot: float = Field(1.0, gt=0)
    default_tp_R: Optional[float] = Field(1.5, gt=0)
    default_sl_ATR_mult: Optional[float] = Field(1.2, gt=0)


class EngineConfig(BaseModel):
    """Motor ayarları"""
    queue_maxsize: int = Field(2000, ge=100)
    latency_warn_ms: int = Field(800, ge=100)
    latency_abort_ms: int = Field(2500, ge=500)
    tick_interval_ms: int = Field(250, ge=100, le=5000)


class StorageConfig(BaseModel):
    """Depolama ayarları"""
    sqlite_path: str = "data/trades.db"
    dataset_csv: str = "data/ml_dataset.csv"
    wal_mode: bool = True


class LoggingConfig(BaseModel):
    """Loglama ayarları"""
    level: str = Field("INFO", pattern="^(DEBUG|INFO|WARN|ERROR)$")
    file: str = "logs/moonlight.log"
    rotate_mb: int = Field(10, ge=1, le=100)
    keep_files: int = Field(7, ge=1, le=30)
    format: str = Field("json", pattern="^(json|text)$")


class CatalogConfig(BaseModel):
    """Katalog/payout cache ayarları"""
    refresh_sec: int = Field(30, ge=5, le=300)
    ttl_sec: int = Field(120, ge=10, le=600)
    ewma_alpha: float = Field(0.3, ge=0.01, le=0.99)
    permit_mode: PermitModeEnum = PermitModeEnum.PREFER_CACHE
    auto_threshold: bool = True
    margin: float = Field(0.02, ge=0.0, le=0.10)


class UIConfig(BaseModel):
    """UI tercihleri"""
    theme: str = Field("dark", pattern="^(dark|light)$")
    colors: Dict[str, str] = Field(default_factory=lambda: {
        "primary": "#6D28D9",
        "accent": "#2563EB",
        "success": "#10B981",
        "danger": "#EF4444"
    })
    locale: str = "tr-TR"
    timezone: str = "Europe/Istanbul"


class APIConfig(BaseModel):
    """API ayarları"""
    host: str = "127.0.0.1"
    http_port: int = Field(8750, ge=1024, le=65535)
    ws_port: int = Field(8751, ge=1024, le=65535)
    cors_enabled: bool = False
    api_key: Optional[str] = None


class TelemetryConfig(BaseModel):
    """Telemetri ayarları"""
    enabled: bool = True
    prometheus_port: Optional[int] = Field(None, ge=1024, le=65535)
    snapshot_interval_sec: int = Field(30, ge=10, le=300)


class SecurityConfig(BaseModel):
    """Güvenlik ayarları"""
    pii_masking: bool = True
    log_secrets: bool = False
    enforce_tls: bool = False


class AppConfig(BaseModel):
    """Ana uygulama konfigürasyonu"""
    config_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    mode: ModeEnum = ModeEnum.PAPER
    connector: ConnectorEnum = ConnectorEnum.MOCK
    ensemble_threshold: float = Field(0.70, ge=0.5, le=0.99)
    
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    accounts: List[AccountConfig] = Field(..., min_length=1, max_length=4)
    products: List[ProductConfig] = Field(..., min_length=1)
    risk: RiskDefaults = Field(default_factory=RiskDefaults)
    engine: EngineConfig = Field(default_factory=EngineConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    catalog: CatalogConfig = Field(default_factory=CatalogConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    @field_validator('accounts')
    @classmethod
    def validate_account_ids_unique(cls, v):
        ids = [acc.id for acc in v]
        if len(ids) != len(set(ids)):
            raise ValueError('Account IDs must be unique')
        return v

    @field_validator('products')
    @classmethod
    def validate_products(cls, v):
        if not v:
            raise ValueError('At least one product must be configured')
        for prod in v:
            if not prod.timeframes:
                raise ValueError(f'Product {prod.product} must have at least one timeframe')
        return v


def load_config(path: str | Path) -> AppConfig:
    """
    Konfigurasyon dosyasını yükle ve doğrula
    
    Args:
        path: YAML konfig dosya yolu
        
    Returns:
        AppConfig: Doğrulanmış konfigurasyon
        
    Raises:
        FileNotFoundError: Dosya bulunamadı
        ValueError: Şema doğrulama hatası
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    try:
        config = AppConfig(**data)
        return config
    except Exception as e:
        raise ValueError(f"Config validation failed: {e}")


def save_config(config: AppConfig, path: str | Path) -> None:
    """
    Konfigürasyonu dosyaya kaydet
    
    Args:
        config: AppConfig nesnesi
        path: Hedef dosya yolu
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    data = config.model_dump(mode='json', exclude_none=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


# Örnek kullanım ve doğrulama
if __name__ == "__main__":
    # Test: Örnek konfig yükle
    example_path = Path(__file__).parent.parent / "configs" / "app.example.yaml"
    if example_path.exists():
        try:
            cfg = load_config(example_path)
            print(f"✓ Config loaded: {cfg.config_version}")
            print(f"  Mode: {cfg.mode}")
            print(f"  Connector: {cfg.connector}")
            print(f"  Accounts: {len(cfg.accounts)}")
            print(f"  Products: {len(cfg.products)}")
        except Exception as e:
            print(f"✗ Config validation failed: {e}")
