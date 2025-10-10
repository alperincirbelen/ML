"""
Configuration data models - Pydantic schemas
Parça 3, 4 - Konfigürasyon şemaları
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class ConnectorType(str, Enum):
    MOCK = "mock"
    OLYMP = "olymp"


class PermitMode(str, Enum):
    CONFIG_ONLY = "config_only"
    PREFER_CACHE = "prefer_cache"
    CACHE_ONLY = "cache_only"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class SessionConfig(BaseModel):
    http_user_agent: str = "MoonLight/1.0"
    ws_heartbeat_s: int = 20


class AccountConfig(BaseModel):
    id: str
    username: str
    profile_store: str
    keyring_service: str = "moonlight-olymp"
    session: Optional[SessionConfig] = Field(default_factory=SessionConfig)


class RiskConfig(BaseModel):
    lot: Optional[float] = None
    tp_R: Optional[float] = None
    sl_ATR_mult: Optional[float] = None


class TimeframeConfig(BaseModel):
    tf: int = Field(..., description="Timeframe in minutes: 1, 5, or 15")
    enabled: bool = True
    win_threshold: float = Field(0.70, ge=0.5, le=0.99)
    permit_min: float = Field(0, ge=0, le=100)
    permit_max: float = Field(100, ge=0, le=100)
    risk: Optional[RiskConfig] = None

    @validator('permit_max')
    def validate_permit_range(cls, v, values):
        if 'permit_min' in values and v < values['permit_min']:
            raise ValueError('permit_max must be >= permit_min')
        return v

    @validator('tf')
    def validate_tf(cls, v):
        if v not in [1, 5, 15]:
            raise ValueError('tf must be 1, 5, or 15')
        return v


class ProductConfig(BaseModel):
    product: str
    enabled: bool = True
    strategies: List[int] = Field(default_factory=list)
    timeframes: List[TimeframeConfig] = Field(default_factory=list)


class LimitsConfig(BaseModel):
    max_parallel_global: Optional[int] = None
    max_parallel_per_account: Optional[int] = None
    max_daily_loss: Optional[float] = 5.0
    max_consecutive_losses: Optional[int] = 5
    rate_limit_per_min: int = 60


class GlobalRiskConfig(BaseModel):
    default_lot: float = 1.0
    default_tp_R: Optional[float] = 1.5
    default_sl_ATR_mult: Optional[float] = 1.2
    daily_loss_cap: Optional[float] = 5.0
    consec_loss_cap: Optional[int] = 5
    cooldown_sec: int = 300


class EngineConfig(BaseModel):
    queue_maxsize: int = 2000
    latency_warn_ms: int = 800
    latency_abort_ms: int = 2500
    tick_interval_ms: int = 250
    grace_ms: int = 500
    jitter_ms: int = 100
    entry_cutoff_s: int = 5
    lookback: int = 300


class StorageConfig(BaseModel):
    sqlite_path: str = "data/db/moonlight.db"
    dataset_csv: str = "data/ml_dataset.csv"
    wal_mode: bool = True


class LoggingConfig(BaseModel):
    level: LogLevel = LogLevel.INFO
    file: str = "data/logs/moonlight.log"
    rotate_mb: int = 10
    keep_files: int = 7
    format: str = "json"


class CatalogConfig(BaseModel):
    refresh_sec: int = 30
    ttl_soft_sec: int = 60
    ttl_hard_sec: int = 300
    ewma_alpha: float = Field(0.1, ge=0.01, le=0.5)
    permit_mode: PermitMode = PermitMode.PREFER_CACHE
    auto_threshold: bool = True
    margin: float = Field(0.02, ge=0.0, le=0.1)


class UIConfig(BaseModel):
    theme: str = "dark"
    colors: Dict[str, str] = Field(default_factory=dict)
    host: str = "127.0.0.1"
    port: int = 8750
    ws_port: int = 8751


class FeaturesConfig(BaseModel):
    read_only: bool = False
    trade_enabled: bool = False
    paper_mode: bool = True


class ConnectorConfig(BaseModel):
    type: ConnectorType = ConnectorType.MOCK
    base_url: str = ""
    ws_url: str = ""
    timeout_s: int = 10
    rate_limit_per_account: int = 15


class AppConfig(BaseModel):
    """
    Ana konfigürasyon modeli
    Tüm sistem davranışlarını kontrol eder
    """
    config_version: str = "1.0.0"
    ensemble_threshold: float = Field(0.70, ge=0.5, le=0.95)
    
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    accounts: List[AccountConfig] = Field(min_items=1, max_items=4)
    products: List[ProductConfig] = Field(min_items=1)
    risk: GlobalRiskConfig = Field(default_factory=GlobalRiskConfig)
    engine: EngineConfig = Field(default_factory=EngineConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    catalog: CatalogConfig = Field(default_factory=CatalogConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    connector: ConnectorConfig = Field(default_factory=ConnectorConfig)

    @validator('accounts')
    def validate_max_accounts(cls, v):
        if len(v) > 4:
            raise ValueError('Maximum 4 accounts allowed')
        return v

    class Config:
        use_enum_values = True
