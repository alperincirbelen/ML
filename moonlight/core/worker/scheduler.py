"""
Scheduler - Worker lifecycle management
Parça 12, 16 - Zamanlayıcı ve worker yönetimi
"""

import asyncio
from typing import Dict, Tuple, Callable, Any, Optional


class Scheduler:
    """
    Zamanlayıcı - worker'ları başlatır ve yönetir
    """
    
    def __init__(
        self,
        worker_factory: Callable,
        tick_ms: int = 250,
        jitter_ms: int = 100
    ):
        self.worker_factory = worker_factory
        self.tick_ms = tick_ms
        self.jitter_ms = jitter_ms
        
        # Workers: (account, product, tf) -> Task
        self.workers: Dict[Tuple[str, str, int], asyncio.Task] = {}
    
    def _key(self, account: str, product: str, tf: int) -> Tuple[str, str, int]:
        """Worker anahtarı"""
        return (account, product, tf)
    
    async def start_worker(
        self, 
        account: str, 
        product: str, 
        tf: int,
        **worker_kwargs
    ) -> None:
        """Worker başlat"""
        key = self._key(account, product, tf)
        
        # Zaten çalışıyorsa atla
        if key in self.workers and not self.workers[key].done():
            return
        
        # Worker oluştur
        worker = self.worker_factory(account, product, tf, **worker_kwargs)
        
        # Task başlat
        task = asyncio.create_task(
            worker.run(),
            name=f"worker:{account}:{product}:{tf}"
        )
        
        self.workers[key] = task
    
    async def stop_worker(self, account: str, product: str, tf: int) -> None:
        """Worker durdur"""
        key = self._key(account, product, tf)
        task = self.workers.get(key)
        
        if task and not task.done():
            task.cancel()
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            del self.workers[key]
    
    async def stop_all(self) -> None:
        """Tüm worker'ları durdur"""
        keys = list(self.workers.keys())
        
        for key in keys:
            await self.stop_worker(*key)
    
    def get_active_workers(self) -> List[Tuple[str, str, int]]:
        """Aktif worker'ları listele"""
        return [
            key for key, task in self.workers.items()
            if not task.done()
        ]
    
    def worker_count(self) -> int:
        """Aktif worker sayısı"""
        return len(self.get_active_workers())
