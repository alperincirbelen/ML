"""
Strategy Registry - Plugin discovery
Parça 13, 23 - Strateji kaydı ve keşif
"""

from typing import Dict, Type, List, Any
import importlib
import pkgutil


# Global registry
_REGISTRY: Dict[int, Type] = {}


def register(pid: int):
    """
    Strateji kayıt dekoratörü
    
    Kullanım:
        @register(5)
        class MyStrategy:
            ...
    """
    def decorator(cls: Type) -> Type:
        _REGISTRY[pid] = cls
        return cls
    return decorator


class StrategyRegistry:
    """Strateji kayıt yöneticisi"""
    
    @staticmethod
    def load_all() -> None:
        """
        Tüm provider modüllerini yükle
        providers/ klasöründeki tüm .py dosyaları
        """
        try:
            import moonlight.core.strategies.providers as pkg
            
            for module_info in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
                try:
                    importlib.import_module(module_info.name)
                except Exception as e:
                    print(f"Warning: Failed to load strategy module {module_info.name}: {e}")
        except ImportError:
            # providers klasörü henüz yok
            pass
    
    @staticmethod
    def build(pid: int, **kwargs) -> Any:
        """
        ID'den strateji oluştur
        """
        if pid not in _REGISTRY:
            raise ValueError(f"Strategy {pid} not found in registry")
        
        cls = _REGISTRY[pid]
        return cls(**kwargs)
    
    @staticmethod
    def all_metadata() -> List[Dict]:
        """Tüm stratejilerin metadata'sı"""
        result = []
        
        for pid, cls in _REGISTRY.items():
            meta = getattr(cls, 'META', {})
            meta['id'] = pid
            result.append(meta)
        
        return result
    
    @staticmethod
    def list_ids() -> List[int]:
        """Kayıtlı strateji ID'leri"""
        return list(_REGISTRY.keys())
