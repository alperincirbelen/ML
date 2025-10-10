"""
Smoke Test - Temel sistemin çalıştığını doğrula
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from moonlight.core.config import ConfigLoader
from moonlight.core.storage import init_database, Storage
from moonlight.core.connector import MockConnector
from moonlight.core.telemetry import setup_logger


async def main():
    print("🌙 MoonLight Smoke Test")
    print("=" * 60)
    
    # 1. Config
    print("\n✅ Test 1: Konfigürasyon yükleme...")
    try:
        config = ConfigLoader.load_yaml("configs/config.example.yaml")
        print(f"   ✓ Config version: {config.config_version}")
        print(f"   ✓ Accounts: {len(config.accounts)}")
        print(f"   ✓ Products: {len(config.products)}")
    except Exception as e:
        print(f"   ✗ HATA: {e}")
        return False
    
    # 2. Database
    print("\n✅ Test 2: Veritabanı başlatma...")
    try:
        db_path = "data/db/test_smoke.db"
        await init_database(db_path)
        storage = Storage(db_path)
        print(f"   ✓ Database: {db_path}")
    except Exception as e:
        print(f"   ✗ HATA: {e}")
        return False
    
    # 3. Connector
    print("\n✅ Test 3: Mock Connector...")
    try:
        connector = MockConnector("acc1", seed=42)
        await connector.login("test@example.com", "password")
        
        instruments = await connector.get_instruments()
        print(f"   ✓ Instruments: {len(instruments)}")
        
        candles = await connector.get_candles("EURUSD", 1, 50)
        print(f"   ✓ Candles: {len(candles)} bars")
        
        payout = await connector.get_current_win_rate("EURUSD")
        print(f"   ✓ Payout: {payout:.2f}%")
    except Exception as e:
        print(f"   ✗ HATA: {e}")
        return False
    
    # 4. Indicators
    print("\n✅ Test 4: Teknik göstergeler...")
    try:
        import pandas as pd
        from moonlight.core.indicators.basic import ema, rsi, macd
        
        df = pd.DataFrame(candles)
        
        ema_9 = ema(df['close'], 9)
        rsi_14 = rsi(df['close'], 14)
        macd_line, signal, hist = macd(df['close'])
        
        print(f"   ✓ EMA(9): {ema_9.iloc[-1]:.4f}")
        print(f"   ✓ RSI(14): {rsi_14.iloc[-1]:.2f}")
        print(f"   ✓ MACD Hist: {hist.iloc[-1]:.6f}")
    except Exception as e:
        print(f"   ✗ HATA: {e}")
        return False
    
    # 5. Storage
    print("\n✅ Test 5: Veritabanı işlemleri...")
    try:
        from moonlight.core.storage.models import Order, Result
        
        order = Order(
            id="smoke_test_1",
            ts_open_ms=int(time.time() * 1000),
            account_id="acc1",
            product="EURUSD",
            timeframe=1,
            direction="call",
            amount=10.0,
            client_req_id="smoke_req_1"
        )
        
        await storage.save_order(order)
        print("   ✓ Order saved")
        
        result = Result(
            order_id="smoke_test_1",
            ts_close_ms=int(time.time() * 1000) + 60000,
            status="win",
            pnl=9.0,
            latency_ms=120
        )
        
        await storage.save_result(result)
        print("   ✓ Result saved")
        
        trades = await storage.get_recent_trades(1)
        print(f"   ✓ Recent trades: {len(trades)}")
    except Exception as e:
        print(f"   ✗ HATA: {e}")
        return False
    
    # 6. Risk Engine
    print("\n✅ Test 6: Risk Engine...")
    try:
        from moonlight.core.risk import RiskEngine, RiskLimits, AmountPolicy, TradeContext
        
        limits = RiskLimits(max_daily_loss=5.0, max_consec_losses=5)
        policy = AmountPolicy(mode="fixed", fixed_a=1.0)
        risk = RiskEngine(limits, policy)
        
        ctx = TradeContext(
            account="acc1",
            product="EURUSD",
            timeframe=1,
            direction="call",
            payout=90.0,
            confidence=0.75,
            prob_win=0.72,
            win_threshold=0.70,
            permit_min=89.0,
            permit_max=93.0,
            balance=1000.0
        )
        
        allowed = risk.enter_allowed(ctx)
        amount = risk.compute_amount(ctx)
        
        print(f"   ✓ Entry allowed: {allowed}")
        print(f"   ✓ Amount: {amount}")
    except Exception as e:
        print(f"   ✗ HATA: {e}")
        return False
    
    # 7. Ensemble
    print("\n✅ Test 7: Ensemble...")
    try:
        from moonlight.core.ensemble import Ensemble, EnsembleState, ProviderVote
        
        state = EnsembleState()
        ensemble = Ensemble(state)
        
        votes = [
            ProviderVote(pid=1, vote=1, score=0.8),
            ProviderVote(pid=2, vote=1, score=0.6),
            ProviderVote(pid=3, vote=-1, score=0.3),
        ]
        
        result = ensemble.combine(votes)
        
        print(f"   ✓ Ensemble S: {result.S:.3f}")
        print(f"   ✓ Confidence: {result.confidence:.3f}")
        print(f"   ✓ p̂: {result.p_hat:.3f}")
        print(f"   ✓ Direction: {result.direction}")
    except Exception as e:
        print(f"   ✗ HATA: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ TÜM TESTLER BAŞARILI!")
    print("🌙 MoonLight temel bileşenleri çalışıyor.\n")
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    
    return True


if __name__ == "__main__":
    import time
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
