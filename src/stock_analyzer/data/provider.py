"""Provider interface plus JSON fixture loading/saving for offline runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from stock_analyzer.models import CompanyData


class TickerNotFound(Exception):
    pass


class DataProvider(Protocol):
    def fetch(self, ticker: str) -> CompanyData:
        """Fetch everything needed to analyze one ticker. Missing fields are None/empty, never raised."""
        ...


class FixtureProvider:
    """Serves a previously saved CompanyData JSON file."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def fetch(self, ticker: str) -> CompanyData:
        return load_fixture(self.path)


def load_fixture(path: Path) -> CompanyData:
    return CompanyData.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def save_fixture(data: CompanyData, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data.to_dict(), indent=1), encoding="utf-8")
