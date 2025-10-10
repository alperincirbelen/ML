"""
Strategy Registry - Plugin Discovery and Management

Strateji kayıt ve keşif mekanizması
"""

from typing import Dict, Type, List, Any
from .base import StrategyProvider, ProviderConfig
import importlib
import pkgutil


# Global registry
_REGISTRY: Dict[int, Type[StrategyProvider]] = {}
_METADATA: Dict[int, Dict[str, Any]] = {}


def register(pid: int, metadata: Dict[str, Any] = None):
    """
    Strateji kayıt dekoratörü
    
    Kullanım:
        @register(pid=5, metadata={"name": "EMA+RSI", "group": "trend"})
        class MyStrategy:
            ...
    """
    def decorator(cls: Type[StrategyProvider]):
        _REGISTRY[pid] = cls
        if metadata:
            _METADATA[pid] = metadata
        return cls
    return decorator


def load_all():
    """
    Tüm provider modüllerini yükle (auto-discovery)
    
    providers/ klasöründeki tüm Python modüllerini import eder
    """
    try:
        import moonlight.core.strategies.providers as pkg
        for module_info in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
            try:
                importlib.import_module(module_info.name)
            except Exception as e:
                print(f"Warning: Failed to load {module_info.name}: {e}")
    except ImportError:
        # providers paketi henüz yok, sessizce geç
        pass


def build(pid: int, **kwargs) -> StrategyProvider:
    """
    Strateji örneği oluştur
    
    Args:
        pid: Provider ID
        **kwargs: ProviderConfig override'ları
    
    Returns:
        StrategyProvider instance
        
    Raises:
        KeyError: ID bilinmiyor
    """
    if pid not in _REGISTRY:
        raise KeyError(f"Strategy ID {pid} not registered")
    
    cls = _REGISTRY[pid]
    meta = _METADATA.get(pid, {})
    
    # Config oluştur
    config = ProviderConfig(
        id=pid,
        name=meta.get('name', f'Strategy_{pid}'),
        group=meta.get('group', 'unknown'),
        params=kwargs.get('params', {})
    )
    
    return cls(config)


def all_metadata() -> List[Dict[str, Any]]:
    """Kayıtlı tüm stratejilerin meta bilgisi"""
    result = []
    for pid in sorted(_REGISTRY.keys()):
        meta = _METADATA.get(pid, {})
        result.append({
            "id": pid,
            "name": meta.get('name', f'Strategy_{pid}'),
            "group": meta.get('group', 'unknown'),
            **meta
        })
    return result


def list_strategies() -> List[int]:
    """Kayıtlı strateji ID'leri"""
    return sorted(_REGISTRY.keys())


# Test
if __name__ == "__main__":
    print("Strategy Registry")
    print(f"Loaded strategies: {list_strategies()}")
    print(f"Metadata: {all_metadata()}")
