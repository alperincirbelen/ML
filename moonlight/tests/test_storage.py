"""
Storage Layer Tests
"""

import pytest
import asyncio
from datetime import datetime
from moonlight.core.storage import Storage, OrderRecord, ResultRecord


@pytest.fixture
async def storage():
    """Test storage instance"""
    db = Storage(":memory:")  # In-memory database
    await db.init()
    yield db
    await db.close()


@pytest.mark.asyncio
async def test_save_order(storage):
    """Emir kaydedilmeli"""
    order = OrderRecord(
        id="test_001",
        ts_open_ms=int(datetime.now().timestamp() * 1000),
        account_id="acc1",
        product="EURUSD",
        timeframe=1,
        direction=1,
        amount=10.0,
        payout_pct=90.0,
        client_req_id="req_001"
    )
    
    await storage.save_order(order)
    
    # Kontrol
    orders = await storage.open_orders("acc1")
    assert len(orders) == 1
    assert orders[0]['id'] == "test_001"


@pytest.mark.asyncio
async def test_idempotent_order(storage):
    """Aynı client_req_id ile tekrar deneme güvenli olmalı"""
    order = OrderRecord(
        id="test_002",
        ts_open_ms=int(datetime.now().timestamp() * 1000),
        account_id="acc1",
        product="EURUSD",
        timeframe=1,
        direction=1,
        amount=10.0,
        payout_pct=90.0,
        client_req_id="req_002_unique"
    )
    
    # İlk kayıt
    await storage.save_order(order)
    
    # Tekrar kayıt (aynı client_req_id)
    await storage.save_order(order)
    
    # Sadece bir kayıt olmalı
    orders = await storage.open_orders("acc1")
    matching = [o for o in orders if o['client_req_id'] == "req_002_unique"]
    assert len(matching) == 1


@pytest.mark.asyncio
async def test_rolling_winrate(storage):
    """Rolling win rate hesaplanmalı"""
    # Emirler kaydet
    for i in range(10):
        order = OrderRecord(
            id=f"order_{i}",
            ts_open_ms=int(datetime.now().timestamp() * 1000) + i * 1000,
            account_id="acc1",
            product="EURUSD",
            timeframe=1,
            direction=1,
            amount=1.0,
            payout_pct=90.0,
            client_req_id=f"req_{i}"
        )
        await storage.save_order(order)
        
        # Sonuç kaydet (7 win, 3 loss)
        status = "win" if i < 7 else "lose"
        pnl = 0.9 if status == "win" else -1.0
        
        result = ResultRecord(
            order_id=f"order_{i}",
            ts_close_ms=int(datetime.now().timestamp() * 1000) + i * 1000 + 60000,
            status=status,
            pnl=pnl
        )
        await storage.save_result(result)
    
    # Win rate hesapla
    wr = await storage.rolling_winrate("acc1", "EURUSD", 1, last_n=100)
    
    assert wr is not None
    assert 0.65 < wr < 0.75  # ~%70 olmalı


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
