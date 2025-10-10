"""
Guardrails - Safety barriers and circuit breaker
Parça 8 - Koruma bariyerleri
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional


class CircuitBreakerState(Enum):
    """Circuit breaker durumları"""
    CLOSED = "closed"  # Normal işlem
    OPEN = "open"      # Yeni işlem yok
    HALF_OPEN = "half_open"  # Tek test işlemi


@dataclass
class GuardrailsConfig:
    """Guardrails konfigürasyonu"""
    enable_kill_switch: bool = True
    enable_circuit_breaker: bool = True
    cb_consecutive_losses: int = 5
    cb_cooldown_sec: int = 600
    cb_min_trades_for_wr: int = 20


class Guardrails:
    """
    Güvenlik bariyerleri
    Kill-Switch ve Circuit Breaker
    """
    
    def __init__(self, config: GuardrailsConfig):
        self.config = config
        self._kill_switch: bool = False
        self._cb_state: Dict[str, CircuitBreakerState] = {}
        self._cb_cooldown_until: Dict[str, float] = {}
    
    def is_kill_switch_on(self) -> bool:
        """Kill-Switch durumu"""
        return self._kill_switch
    
    def toggle_kill_switch(self, enabled: bool) -> None:
        """Kill-Switch aç/kapat"""
        self._kill_switch = enabled
    
    def get_cb_state(self, scope: str) -> CircuitBreakerState:
        """
        Circuit breaker durumu
        scope: account_id veya "global"
        """
        return self._cb_state.get(scope, CircuitBreakerState.CLOSED)
    
    def trip_circuit_breaker(self, scope: str, cooldown_sec: Optional[int] = None) -> None:
        """
        Circuit breaker'ı tetikle (OPEN yap)
        """
        import time
        
        self._cb_state[scope] = CircuitBreakerState.OPEN
        
        cooldown = cooldown_sec or self.config.cb_cooldown_sec
        self._cb_cooldown_until[scope] = time.time() + cooldown
    
    def reset_circuit_breaker(self, scope: str) -> None:
        """Circuit breaker'ı sıfırla (CLOSED yap)"""
        self._cb_state[scope] = CircuitBreakerState.CLOSED
        if scope in self._cb_cooldown_until:
            del self._cb_cooldown_until[scope]
    
    def check_cooldown(self, scope: str) -> bool:
        """
        Cooldown süresi doldu mu?
        Returns: True ise cooldown bitti, HALF_OPEN'a geçilebilir
        """
        import time
        
        if scope not in self._cb_cooldown_until:
            return True
        
        return time.time() >= self._cb_cooldown_until[scope]
    
    def attempt_half_open(self, scope: str) -> bool:
        """
        HALF_OPEN geçişi dene
        Returns: True ise geçiş yapıldı
        """
        if self.get_cb_state(scope) == CircuitBreakerState.OPEN:
            if self.check_cooldown(scope):
                self._cb_state[scope] = CircuitBreakerState.HALF_OPEN
                return True
        
        return False
    
    def pre_trade_check(
        self, 
        account: str, 
        kill_switch_override: bool = False
    ) -> tuple[bool, Optional[str]]:
        """
        İşlem öncesi kontrol
        Returns: (allowed, reason)
        """
        # Kill-Switch
        if not kill_switch_override and self._kill_switch:
            return False, "killswitch_on"
        
        # Account-level CB
        account_cb = self.get_cb_state(account)
        if account_cb == CircuitBreakerState.OPEN:
            # Cooldown kontrolü
            if self.check_cooldown(account):
                self.attempt_half_open(account)
            else:
                return False, "cb_open"
        
        # Global CB
        global_cb = self.get_cb_state("global")
        if global_cb == CircuitBreakerState.OPEN:
            if not self.check_cooldown("global"):
                return False, "cb_global_open"
        
        return True, None
