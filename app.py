"""Vercel entrypoint: exposes the web view's Flask instance as `app`.

Run locally with `analyze-web` instead; this file only exists for deployment.
"""

import os
import sys
from pathlib import Path

# Make the src/ package importable whether or not the project was pip-installed
sys.path.insert(0, str(Path(__file__).parent / "src"))

if os.environ.get("VERCEL"):
    # Only /tmp is writable on Vercel
    os.environ.setdefault("STOCK_ANALYZER_CACHE", "/tmp/stock_analyzer")
    import yfinance as yf

    yf.set_tz_cache_location("/tmp/yfinance")

from stock_analyzer.web.app import create_app  # noqa: E402

app = create_app()
