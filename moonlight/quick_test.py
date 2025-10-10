#!/usr/bin/env python3
"""
MoonLight Quick Validation Test

Temel bileşenlerin çalıştığını hızlıca doğrular
"""

import asyncio
import sys
from pathlib import Path


async def run_tests():
    """Hızlı doğrulama testleri"""
    print("=" * 60)
    print("MoonLight - Quick Validation Test")
    print("=" * 60)
    print()
    
    passed = 0
    failed = 0
    
    # Test 1: Config
    print("Test 1: Configuration Loading...")
    try:
        from moonlight.core.config import load_config
        config_path = Path("configs/app.example.yaml")
        cfg = load_config(config_path)
        print(f"  ✓ Config loaded: v{cfg.config_version}")
        print(f"    Mode: {cfg.mode}, Connector: {cfg.connector}")
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1
    
    print()
    
    # Test 2: Storage
    print("Test 2: Database Initialization...")
    try:
        from moonlight.core.storage import Storage
        db = Storage(":memory:")
        await db.init()
        print("  ✓ Database schema created")
        
        # Test write
        from moonlight.core.storage import OrderRecord
        from datetime import datetime
        
        order = OrderRecord(
            id="test_001",
            ts_open_ms=int(datetime.now().timestamp() * 1000),
            account_id="acc1",
            product="TEST",
            timeframe=1,
            direction=1,
            amount=1.0,
            payout_pct=90.0,
            client_req_id="test_req_001"
        )
        await db.save_order(order)
        print("  ✓ Order write successful")
        
        orders = await db.open_orders("acc1")
        assert len(orders) == 1
        print("  ✓ Order read successful")
        
        await db.close()
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1
    
    print()
    
    # Test 3: Indicators
    print("Test 3: Technical Indicators...")
    try:
        import pandas as pd
        import numpy as np
        from moonlight.core.indicators.basic import ema, rsi, macd
        from moonlight.core.indicators.advanced import adx, supertrend
        
        # Sample data
        close = pd.Series(np.cumsum(np.random.randn(100)) * 0.01 + 100)
        high = close + 0.5
        low = close - 0.5
        
        ema20 = ema(close, 20)
        assert not ema20.dropna().empty
        print("  ✓ EMA calculation")
        
        rsi14 = rsi(close, 14)
        assert rsi14.dropna().min() >= 0
        assert rsi14.dropna().max() <= 100
        print("  ✓ RSI calculation")
        
        adx14 = adx(high, low, close, 14)
        assert not adx14.dropna().empty
        print("  ✓ ADX calculation")
        
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1
    
    print()
    
    # Test 4: Mock Connector
    print("Test 4: Mock Connector...")
    try:
        from moonlight.core.connector.mock import MockConnector
        
        conn = MockConnector("test_acc", seed=42)
        await conn.login("test@example.com", "password")
        print("  ✓ Login successful")
        
        candles = await conn.get_candles("EURUSD", 1, n=50)
        assert len(candles) == 50
        print(f"  ✓ Candles fetched: {len(candles)}")
        
        payout = await conn.get_current_win_rate("EURUSD")
        assert 0 < payout < 100
        print(f"  ✓ Payout: {payout:.2f}%")
        
        ack = await conn.place_order(
            product="EURUSD",
            amount=1.0,
            direction="call",
            timeframe=1,
            client_req_id="test_123"
        )
        print(f"  ✓ Order placed: {ack.order_id}")
        
        # Idempotency test
        ack2 = await conn.place_order(
            product="EURUSD",
            amount=1.0,
            direction="call",
            timeframe=1,
            client_req_id="test_123"
        )
        assert ack.order_id == ack2.order_id
        print("  ✓ Idempotency verified")
        
        await conn.close()
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1
    
    print()
    
    # Test 5: Strategy Registry
    print("Test 5: Strategy System...")
    try:
        from moonlight.core.strategies.registry import load_all, list_strategies, build
        
        load_all()
        strategies = list_strategies()
        print(f"  ✓ Strategies loaded: {len(strategies)}")
        print(f"    IDs: {strategies}")
        
        # Test bir strateji
        if 5 in strategies:
            strategy = build(5)
            print(f"  ✓ Strategy 5 instantiated")
        
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1
    
    print()
    
    # Test 6: Ensemble
    print("Test 6: Ensemble & Calibration...")
    try:
        from moonlight.core.ensemble import Ensemble, EnsembleState, ProviderVote
        
        state = EnsembleState()
        ens = Ensemble(state, s_cap=2.0)
        
        votes = [
            ProviderVote(pid=5, vote=+1, score=0.6),
            ProviderVote(pid=14, vote=+1, score=0.8),
            ProviderVote(pid=15, vote=0, score=0.1),
        ]
        
        result = ens.combine(votes)
        assert -1 <= result.S <= 1
        assert 0 <= result.confidence <= 1
        assert 0 <= result.p_hat <= 1
        
        print(f"  ✓ Ensemble S: {result.S:.4f}")
        print(f"  ✓ Confidence: {result.confidence:.4f}")
        print(f"  ✓ p_hat: {result.p_hat:.4f}")
        
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1
    
    print()
    
    # Test 7: Risk Engine
    print("Test 7: Risk Management...")
    try:
        from moonlight.core.risk import RiskEngine, RiskLimits, AmountPolicy, TradeContext
        
        limits = RiskLimits(max_daily_loss=5.0, max_consec_losses=3)
        policy = AmountPolicy(mode="fixed", fixed_a=1.0)
        risk = RiskEngine(limits, policy)
        
        ctx = TradeContext(
            account="acc1",
            product="EURUSD",
            timeframe=1,
            payout=0.9,
            confidence=0.75,
            prob_win=0.65,
            permit_min=85.0,
            permit_max=95.0,
            win_threshold=0.70
        )
        
        allowed = risk.enter_allowed(ctx)
        print(f"  ✓ Entry check: {allowed}")
        
        amount = risk.compute_amount(ctx)
        print(f"  ✓ Amount: {amount}")
        
        # Simulate losses
        risk.on_result(ctx, pnl=-1.0, is_win=False)
        risk.on_result(ctx, pnl=-1.0, is_win=False)
        risk.on_result(ctx, pnl=-1.0, is_win=False)
        
        allowed = risk.enter_allowed(ctx)
        print(f"  ✓ After 3 losses: {'BLOCKED' if not allowed else 'ALLOWED'}")
        
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        sys.exit(1)
