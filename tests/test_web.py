from pathlib import Path

import pytest

from stock_analyzer.web.app import create_app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client():
    return create_app(fixture_dir=FIXTURES).test_client()


def test_home_page(client):
    html = client.get("/").get_data(as_text=True)
    assert "Is it a value stock or a growth stock?" in html
    assert 'href="/?ticker=ALAB"' in html


def test_lien_report(client):
    html = client.get("/?ticker=lien").get_data(as_text=True)
    assert "Chicago Atlantic" in html
    assert 'class="verdict-badge">Value<' in html
    assert "10-Year EPS Test" in html
    assert "Same as above." in html  # repeated financial-sector notes are collapsed


def test_alab_report(client):
    html = client.get("/?ticker=ALAB").get_data(as_text=True)
    assert 'class="verdict-badge">Growth<' in html
    assert "Fail (sector-typical)" in html


def test_report_includes_charts_and_price_header(client):
    import json
    import re

    html = client.get("/?ticker=ALAB").get_data(as_text=True)
    for chart in ("price", "financials", "eps", "margins"):
        assert f'data-chart="{chart}"' in html
    assert "Show data table" in html
    assert 'class="price-figure">$' in html
    assert "52-week range" in html and "1-year return" in html
    data = json.loads(re.search(r'<script type="application/json" id="chart-data">(.*?)</script>', html, re.S).group(1))
    assert len(data["prices"]) > 100
    assert data["financials"] and data["eps"]


def test_unknown_ticker_shows_error(client):
    resp = client.get("/?ticker=NOPE")
    assert resp.status_code == 200
    assert "No saved data for &#39;NOPE&#39;" in resp.get_data(as_text=True)


def test_eps_overrides_are_applied(client):
    html = client.get("/?ticker=LIEN&eps_10y_ago=1.23&min_pe=5.65").get_data(as_text=True)
    assert "EPS 10 years ago" in html
    assert "5.65" in html


def test_markdown_download(client):
    resp = client.get("/report.md?ticker=ALAB")
    assert resp.status_code == 200
    assert resp.headers["Content-Disposition"].startswith('attachment; filename="ALAB_')
    assert "**Verdict: GROWTH**" in resp.get_data(as_text=True)
