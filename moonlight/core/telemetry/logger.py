"""
Structured JSON Logging
Parça 13, 17 - Yapılandırılmış loglama
"""

import logging
import json
import re
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Any, Dict


def mask_pii(text: str) -> str:
    """
    PII maskele
    E-posta: a***r@***
    Telefon: +90******12
    """
    # E-posta maskeleme
    text = re.sub(
        r'\b([a-zA-Z])[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
        r'\1***@***',
        text
    )
    
    # Telefon maskeleme
    text = re.sub(
        r'\+?\d{1,3}[\s-]?\(?\d{1,4}\)?[\s-]?\d{1,4}[\s-]?\d{1,4}',
        r'+**********',
        text
    )
    
    return text


class JsonFormatter(logging.Formatter):
    """JSON log formatter"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": mask_pii(record.getMessage()),
        }
        
        # Extra context
        if hasattr(record, 'ctx'):
            log_data['ctx'] = record.ctx
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(
    name: str,
    log_file: str,
    level: str = "INFO",
    rotate_mb: int = 10,
    keep_files: int = 7
) -> logging.Logger:
    """
    Structured logger kur
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.propagate = False
    
    # Dosya oluştur
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Rotating file handler
    handler = RotatingFileHandler(
        log_file,
        maxBytes=rotate_mb * 1024 * 1024,
        backupCount=keep_files,
        encoding='utf-8'
    )
    
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    
    # Console handler (geliştirme için)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(console)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Logger getir"""
    return logging.getLogger(name)
