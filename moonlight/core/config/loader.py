"""
Configuration loader with validation
Parça 3, 4 - Konfigürasyon yükleme ve doğrulama
"""

import os
import yaml
import json
from pathlib import Path
from typing import Optional
from .models import AppConfig


class ConfigLoader:
    """
    Konfigürasyon dosyasını yükler ve doğrular
    Fail-closed: Geçersiz konfig → sistem başlamaz
    """
    
    @staticmethod
    def load_yaml(path: str) -> AppConfig:
        """YAML konfigürasyon dosyasını yükle"""
        config_path = Path(path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Pydantic validation
            config = AppConfig(**data)
            return config
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}")
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    @staticmethod
    def load_json(path: str) -> AppConfig:
        """JSON konfigürasyon dosyasını yükle"""
        config_path = Path(path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            config = AppConfig(**data)
            return config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON syntax: {e}")
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    @staticmethod
    def load_from_env() -> AppConfig:
        """
        Ortam değişkeninden konfigürasyon yükle
        MOONLIGHT_CONFIG environment variable
        """
        config_path = os.environ.get('MOONLIGHT_CONFIG')
        
        if not config_path:
            raise ValueError("MOONLIGHT_CONFIG environment variable not set")
        
        if config_path.endswith('.yaml') or config_path.endswith('.yml'):
            return ConfigLoader.load_yaml(config_path)
        elif config_path.endswith('.json'):
            return ConfigLoader.load_json(config_path)
        else:
            raise ValueError("Config file must be .yaml, .yml, or .json")
    
    @staticmethod
    def validate_config(config: AppConfig) -> tuple[bool, List[str]]:
        """
        Konfigürasyonu doğrula ve uyarıları döndür
        Returns: (is_valid, warnings_list)
        """
        warnings = []
        
        # Parallellik kontrolü
        if config.limits.max_parallel_global is None:
            warnings.append("max_parallel_global not set - system will run in observation mode only")
        
        if config.limits.max_parallel_per_account is None:
            warnings.append("max_parallel_per_account not set")
        
        # Trade enabled kontrolü
        if config.features.trade_enabled and config.features.paper_mode is False:
            warnings.append("LIVE MODE ENABLED - ensure all safety checks are in place")
        
        # Connector kontrolü
        if config.connector.type.value == "olymp" and not config.connector.base_url:
            warnings.append("olymp connector selected but base_url is empty - connector will be passive")
        
        # Strateji kontrolü
        for product in config.products:
            if product.enabled and not product.strategies:
                warnings.append(f"Product {product.product} enabled but no strategies defined")
        
        # Permit aralığı kontrolü
        for product in config.products:
            for tf in product.timeframes:
                if tf.enabled and tf.permit_min >= tf.permit_max:
                    return False, [f"Invalid permit range for {product.product} TF{tf.tf}"]
        
        return True, warnings
