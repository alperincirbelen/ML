"""
Telemetry & Logging Infrastructure

Parça 13/17 - Metrikler, Yapılandırılmış Log, PII Maskeleme
"""

from __future__ import annotations
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from collections import defaultdict
from dataclasses import dataclass, field


# PII maskeleme pattern'leri
EMAIL_PATTERN = re.compile(r'([a-zA-Z0-9._-]+)@([a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)')
PHONE_PATTERN = re.compile(r'\+?(\d{1,3})(\d{3,4})(\d{4,7})')


def mask_email(email: str) -> str:
    """E-posta maskeleme: a***r@d***.com"""
    match = EMAIL_PATTERN.match(email)
    if not match:
        return email
    
    user, domain = match.groups()
    if len(user) > 2:
        masked_user = user[0] + '***' + user[-1]
    else:
        masked_user = user[0] + '***'
    
    # Domain ilk harf + ***
    domain_parts = domain.split('.')
    masked_domain = domain_parts[0][0] + '***.' + '.'.join(domain_parts[1:])
    
    return f"{masked_user}@{masked_domain}"


def mask_phone(phone: str) -> str:
    """Telefon maskeleme: +90******12"""
    match = PHONE_PATTERN.search(phone)
    if not match:
        return phone
    
    country, mid, last = match.groups()
    return f"+{country}{'*' * len(mid)}{last[-2:]}"


def mask_pii(text: str) -> str:
    """Metindeki PII'ları maskele"""
    # E-posta
    text = EMAIL_PATTERN.sub(lambda m: mask_email(m.group(0)), text)
    # Telefon
    text = PHONE_PATTERN.sub(lambda m: mask_phone(m.group(0)), text)
    return text


@dataclass
class MetricSnapshot:
    """Metrik snapshot"""
    ts_ms: int
    scope: str
    key: str
    value: float
    tags: Optional[str] = None


class Metrics:
    """
    Metrik Toplama ve Yönetimi
    
    Sorumluluklar:
    - Counter, Gauge, Histogram metrikleri
    - Bellekte toplama, periyodik snapshot
    - Low-cardinality label politikası
    """
    
    def __init__(self):
        self._counters: Dict[tuple, int] = defaultdict(int)
        self._gauges: Dict[tuple, float] = {}
        self._histograms: Dict[tuple, List[float]] = defaultdict(list)
    
    def _make_key(self, name: str, labels: Dict[str, str]) -> tuple:
        """Metrik anahtarı oluştur"""
        # Label'ları sırala (deterministik)
        sorted_labels = tuple(sorted(labels.items()))
        return (name, sorted_labels)
    
    def inc_counter(self, name: str, value: int = 1, **labels) -> None:
        """Sayaç artır"""
        key = self._make_key(name, labels)
        self._counters[key] += value
    
    def set_gauge(self, name: str, value: float, **labels) -> None:
        """Gauge değer ayarla"""
        key = self._make_key(name, labels)
        self._gauges[key] = value
    
    def observe_histogram(self, name: str, value: float, **labels) -> None:
        """Histogram gözlem ekle"""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)
    
    def snapshot(self) -> List[MetricSnapshot]:
        """Mevcut metriklerin snapshot'ını al"""
        ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        snapshots = []
        
        # Counters
        for (name, labels), value in self._counters.items():
            scope = self._labels_to_scope(labels)
            snapshots.append(MetricSnapshot(
                ts_ms=ts_ms,
                scope=scope,
                key=name,
                value=float(value)
            ))
        
        # Gauges
        for (name, labels), value in self._gauges.items():
            scope = self._labels_to_scope(labels)
            snapshots.append(MetricSnapshot(
                ts_ms=ts_ms,
                scope=scope,
                key=name,
                value=value
            ))
        
        # Histograms (p50, p90, p99)
        for (name, labels), values in self._histograms.items():
            if not values:
                continue
            
            scope = self._labels_to_scope(labels)
            values_sorted = sorted(values)
            n = len(values_sorted)
            
            # Percentile'lar
            p50 = values_sorted[int(n * 0.5)]
            p90 = values_sorted[int(n * 0.9)]
            p99 = values_sorted[int(n * 0.99)] if n >= 100 else p90
            
            snapshots.append(MetricSnapshot(ts_ms, scope, f"{name}_p50", p50))
            snapshots.append(MetricSnapshot(ts_ms, scope, f"{name}_p90", p90))
            snapshots.append(MetricSnapshot(ts_ms, scope, f"{name}_p99", p99))
        
        return snapshots
    
    def _labels_to_scope(self, labels: tuple) -> str:
        """Label'ları scope string'e çevir"""
        if not labels:
            return "global"
        
        # İlk label'ı kullan (basit)
        if labels:
            key, val = labels[0]
            return f"{key}:{val}"
        return "global"
    
    def reset(self) -> None:
        """Metrikleri sıfırla"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()


class StructuredLogger:
    """
    Yapılandırılmış JSON Logger
    
    Özellikler:
    - JSON format
    - PII maskeleme
    - Seviye kontrolü
    - Rotating file handler
    """
    
    def __init__(self, name: str, level: str = "INFO", log_file: Optional[str] = None):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Console handler
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(console)
        
        # File handler (opsiyonel)
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(file_handler)
    
    def _format_log(self, level: str, event: str, msg: str, ctx: Dict[str, Any]) -> str:
        """JSON log formatla"""
        log_entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "logger": self.name,
            "event": event,
            "msg": msg,
            "ctx": ctx
        }
        
        # JSON'a çevir ve PII maskele
        json_str = json.dumps(log_entry, ensure_ascii=False)
        masked = mask_pii(json_str)
        
        return masked
    
    def info(self, event: str, msg: str, **ctx) -> None:
        """Info log"""
        self.logger.info(self._format_log("INFO", event, msg, ctx))
    
    def warn(self, event: str, msg: str, **ctx) -> None:
        """Warning log"""
        self.logger.warning(self._format_log("WARN", event, msg, ctx))
    
    def error(self, event: str, msg: str, **ctx) -> None:
        """Error log"""
        self.logger.error(self._format_log("ERROR", event, msg, ctx))
    
    def debug(self, event: str, msg: str, **ctx) -> None:
        """Debug log"""
        self.logger.debug(self._format_log("DEBUG", event, msg, ctx))


# Global metrik instance
_metrics = Metrics()


def get_metrics() -> Metrics:
    """Global metrics instance'ı al"""
    return _metrics


# Test
if __name__ == "__main__":
    # PII maskeleme testi
    test_email = "ahmet.yilmaz@example.com"
    print(f"Email: {test_email} → {mask_email(test_email)}")
    
    test_phone = "+905551234567"
    print(f"Phone: {test_phone} → {mask_phone(test_phone)}")
    
    # Metrik testi
    m = Metrics()
    m.inc_counter("orders_total", account="acc1", product="EURUSD")
    m.inc_counter("orders_total", account="acc1", product="EURUSD")
    m.set_gauge("pnl_day", 2.5, account="acc1")
    m.observe_histogram("latency_ms", 120.0, phase="send")
    m.observe_histogram("latency_ms", 150.0, phase="send")
    
    snapshot = m.snapshot()
    print(f"\n✓ Metrics snapshot: {len(snapshot)} entries")
    for s in snapshot[:3]:
        print(f"  {s.scope}:{s.key} = {s.value}")
    
    # Logger testi
    logger = StructuredLogger("test", level="INFO")
    logger.info("test.event", "Test message", account="acc1", product="EURUSD")
    print("\n✓ Structured logger test completed")
