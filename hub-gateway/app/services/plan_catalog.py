import json
from functools import lru_cache
from pathlib import Path

from app.config import settings


@lru_cache(maxsize=1)
def load_plan_catalog() -> dict:
    path = Path(settings.plan_catalog_path)
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("plans", {})


def get_plan(plan_code: str) -> dict:
    plans = load_plan_catalog()
    return plans.get(plan_code) or plans.get("free", {})
