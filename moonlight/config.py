from __future__ import annotations
import json
from dataclasses import dataclass
from typing import List


@dataclass
class TFConfig:
    tf: int
    win_threshold: float
    permit_min: float
    permit_max: float


@dataclass
class ProductConfig:
    product: str
    strategies: List[int]
    tfs: List[TFConfig]


@dataclass
class AppConfig:
    account_id: str
    db_path: str
    products: List[ProductConfig]


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    products: List[ProductConfig] = []
    for p in data["products"]:
        tfs = [TFConfig(tf=it["tf"], win_threshold=it["win_threshold"], permit_min=it["permit_min"], permit_max=it["permit_max"]) for it in p["timeframes"]]
        products.append(ProductConfig(product=p["product"], strategies=p["strategies"], tfs=tfs))
    return AppConfig(account_id=data.get("account_id", "acc1"), db_path=data.get("db_path", "data/trades.db"), products=products)
