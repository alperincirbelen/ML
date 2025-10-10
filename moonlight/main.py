from __future__ import annotations
import argparse
from pathlib import Path

from .config import load_config
from .connector.mock import MockConnector
from .storage.sqlite import SQLiteStorage
from .risk import RiskLimits, RiskEngine
from .executor import OrderExecutor
from .ensemble import Ensemble
from .worker import Worker
from .strategies.providers.ema_rsi import EMA_RSI


def main() -> int:
    parser = argparse.ArgumentParser(description="MoonLight PoC runner (paper mode)")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--steps", type=int, default=10, help="How many worker iterations to perform")
    args = parser.parse_args()

    cfg = load_config(args.config)
    Path(cfg.db_path).parent.mkdir(parents=True, exist_ok=True)
    db = SQLiteStorage(cfg.db_path)

    cx = MockConnector(account_id=cfg.account_id, seed=42)
    risk = RiskEngine(RiskLimits())
    executor = OrderExecutor(cx, db, risk)
    ens = Ensemble()

    # Currently only EMA_RSI (pid=5)
    providers = {5: lambda: EMA_RSI(pid=5, params={"ema_fast": 20, "ema_slow": 50, "rsi_len": 14, "rsi_up": 55, "rsi_dn": 45})}

    # Run all configured products/TFs sequentially
    for prod in cfg.products:
        for tfc in prod.tfs:
            w = Worker(
                account_id=cfg.account_id,
                product=prod.product,
                timeframe=tfc.tf,
                connector=cx,
                providers=[providers[pid]() for pid in prod.strategies if pid in providers],
                ensemble=ens,
                executor=executor,
                permit_min=tfc.permit_min,
                permit_max=tfc.permit_max,
                win_threshold=tfc.win_threshold,
            )
            for _ in range(args.steps):
                res = w.run_once(lookback=300)
                print(f"{prod.product} tf={tfc.tf}: {res}")

    print("\nPoC run finished. SQLite DB at:", cfg.db_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
