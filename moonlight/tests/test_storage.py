"""
Storage tests
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
from moonlight.core.storage import Storage, init_database
from moonlight.core.storage.models import Order, Result


@pytest.fixture
async def temp_storage():
    """Geçici veritabanı"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    await init_database(db_path)
    storage = Storage(db_path)
    
    yield storage
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_save_order(temp_storage):
    """Emir kaydı testi"""
    order = Order(
        id="test_order_1",
        ts_open_ms=1000000,
        account_id="acc1",
        product="EURUSD",
        timeframe=1,
        direction="call",
        amount=10.0,
        client_req_id="test_req_1"
    )
    
    await temp_storage.save_order(order)
    
    # Aynı client_req_id ile tekrar - idempotent olmalı
    await temp_storage.save_order(order)


@pytest.mark.asyncio
async def test_save_result(temp_storage):
    """Sonuç kaydı testi"""
    # Önce order
    order = Order(
        id="test_order_2",
        ts_open_ms=1000000,
        account_id="acc1",
        product="EURUSD",
        timeframe=1,
        direction="call",
        amount=10.0,
        client_req_id="test_req_2"
    )
    await temp_storage.save_order(order)
    
    # Sonuç
    result = Result(
        order_id="test_order_2",
        ts_close_ms=1060000,
        status="win",
        pnl=9.0,
        latency_ms=120
    )
    await temp_storage.save_result(result)
    
    # Tekrar kayıt - update olmalı
    result.pnl = 9.5
    await temp_storage.save_result(result)


@pytest.mark.asyncio
async def test_rolling_winrate(temp_storage):
    """Win rate hesaplama testi"""
    # Birkaç işlem kaydet
    for i in range(10):
        order = Order(
            id=f"order_{i}",
            ts_open_ms=1000000 + i * 60000,
            account_id="acc1",
            product="EURUSD",
            timeframe=1,
            direction="call",
            amount=10.0,
            client_req_id=f"req_{i}"
        )
        await temp_storage.save_order(order)
        
        # 7 win, 3 lose
        status = "win" if i < 7 else "lose"
        result = Result(
            order_id=f"order_{i}",
            ts_close_ms=1060000 + i * 60000,
            status=status,
            pnl=9.0 if status == "win" else -10.0
        )
        await temp_storage.save_result(result)
    
    # Win rate kontrol
    wr = await temp_storage.rolling_winrate("acc1", "EURUSD", 1, 10)
    
    assert wr is not None
    assert 0.65 < wr < 0.75  # ~0.70 olmalı
