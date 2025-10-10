"""
Metrics Collection
Parça 13, 17 - Metrik toplama
"""

import time
from typing import Dict, List
from collections import defaultdict, deque


class Metrics:
    """
    Bellekiçi metrik toplama
    Sayaçlar, gauge'ler ve histogramlar
    """
    
    def __init__(self):
        # Counters
        self._counters: Dict[str, int] = defaultdict(int)
        
        # Gauges
        self._gauges: Dict[str, float] = {}
        
        # Histograms (son N değer)
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
    
    def inc(self, key: str, labels: Dict[str, str] = None, value: int = 1) -> None:
        """Counter artır"""
        metric_key = self._build_key(key, labels)
        self._counters[metric_key] += value
    
    def set(self, key: str, value: float, labels: Dict[str, str] = None) -> None:
        """Gauge ayarla"""
        metric_key = self._build_key(key, labels)
        self._gauges[metric_key] = value
    
    def observe(self, key: str, value: float, labels: Dict[str, str] = None) -> None:
        """Histogram'a değer ekle"""
        metric_key = self._build_key(key, labels)
        self._histograms[metric_key].append(value)
    
    def get_counter(self, key: str, labels: Dict[str, str] = None) -> int:
        """Counter değeri"""
        metric_key = self._build_key(key, labels)
        return self._counters.get(metric_key, 0)
    
    def get_gauge(self, key: str, labels: Dict[str, str] = None) -> float:
        """Gauge değeri"""
        metric_key = self._build_key(key, labels)
        return self._gauges.get(metric_key, 0.0)
    
    def get_histogram_stats(
        self, 
        key: str, 
        labels: Dict[str, str] = None
    ) -> Dict[str, float]:
        """
        Histogram istatistikleri
        p50, p90, p99, avg, min, max
        """
        metric_key = self._build_key(key, labels)
        values = list(self._histograms.get(metric_key, []))
        
        if not values:
            return {"count": 0}
        
        values_sorted = sorted(values)
        n = len(values_sorted)
        
        return {
            "count": n,
            "avg": sum(values) / n,
            "min": values_sorted[0],
            "max": values_sorted[-1],
            "p50": values_sorted[int(n * 0.50)] if n > 0 else 0.0,
            "p90": values_sorted[int(n * 0.90)] if n > 0 else 0.0,
            "p99": values_sorted[int(n * 0.99)] if n > 0 else 0.0,
        }
    
    def snapshot(self) -> Dict[str, Any]:
        """Tüm metriklerin anlık görüntüsü"""
        return {
            "ts_ms": int(time.time() * 1000),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: self.get_histogram_stats(k.split('{')[0])
                for k in self._histograms.keys()
            }
        }
    
    def reset(self) -> None:
        """Tüm metrikleri sıfırla"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
    
    @staticmethod
    def _build_key(key: str, labels: Optional[Dict[str, str]]) -> str:
        """Metrik anahtarı oluştur"""
        if not labels:
            return key
        
        label_str = ','.join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{key}{{{label_str}}}"
