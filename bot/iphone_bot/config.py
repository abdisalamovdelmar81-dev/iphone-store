from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def parse_admin_ids(raw: str) -> set[int]:
    admin_ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        value = part.strip()
        if not value:
            continue
        if not value.isdigit():
            raise ValueError(f"ADMIN_IDS contains a non-number value: {value}")
        admin_ids.add(int(value))
    return admin_ids


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    data_dir: Path
    db_path: Path


def load_config() -> Config:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is empty. Add it to .env or GitHub Secrets.")

    data_dir = Path(os.getenv("DATA_DIR", "./data")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    return Config(
        bot_token=bot_token,
        admin_ids=parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        data_dir=data_dir,
        db_path=data_dir / "store.sqlite3",
    )
