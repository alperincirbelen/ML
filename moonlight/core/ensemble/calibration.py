"""
Probability Calibration
Parça 9, 28 - Olasılık kalibrasyonu
"""

import math
from typing import List, Tuple
from abc import ABC, abstractmethod


class Calibrator(ABC):
    """Kalibrasyon arayüzü"""
    
    @abstractmethod
    def predict(self, S: float) -> float:
        """S skorunu olasılığa çevir"""
        pass
    
    @abstractmethod
    def fit(self, S_list: List[float], y_list: List[int]) -> None:
        """Kalibrasyon parametrelerini öğren"""
        pass


class PlattCalibrator(Calibrator):
    """
    Platt Scaling (Lojistik Kalibrasyon)
    p̂ = sigmoid(a*S + b)
    """
    
    def __init__(self, a: float = 1.0, b: float = 0.0):
        self.a = a
        self.b = b
    
    def predict(self, S: float) -> float:
        """S → p̂"""
        z = self.a * S + self.b
        z = max(-50, min(50, z))  # Overflow koruması
        return 1.0 / (1.0 + math.exp(-z))
    
    def fit(self, S_list: List[float], y_list: List[int]) -> None:
        """
        Basit fit (SGD)
        Gerçek uygulamada sklearn LogisticRegression kullanılabilir
        """
        if len(S_list) < 10:
            return  # Yetersiz veri
        
        # Basit optimizasyon (gradient descent)
        lr = 0.01
        epochs = 100
        
        for _ in range(epochs):
            # Gradients
            grad_a = 0.0
            grad_b = 0.0
            
            for S, y in zip(S_list, y_list):
                p = self.predict(S)
                error = p - y
                
                grad_a += error * S
                grad_b += error
            
            # Update
            self.a -= lr * grad_a / len(S_list)
            self.b -= lr * grad_b / len(S_list)
    
    def brier_score(self, S_list: List[float], y_list: List[int]) -> float:
        """Brier skor - kalibrasyon kalitesi"""
        if not S_list:
            return 0.0
        
        total = 0.0
        for S, y in zip(S_list, y_list):
            p = self.predict(S)
            total += (p - y) ** 2
        
        return total / len(S_list)


def breakeven_threshold(payout_frac: float) -> float:
    """
    Başabaş kazanım oranı
    w* = 1 / (1 + r)
    Örn: r=0.9 → w* ≈ 0.5263
    """
    return 1.0 / (1.0 + payout_frac)


def suggest_threshold(
    cfg_threshold: float,
    payout_frac: float,
    margin: float = 0.02
) -> float:
    """
    Dinamik eşik önerisi
    max(config_threshold, breakeven + margin)
    """
    be = breakeven_threshold(payout_frac)
    return max(cfg_threshold, be + margin)
