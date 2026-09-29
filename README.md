# Value / Growth Stock Analysis Automation

Enter a stock ticker and get back:

1. **A verdict**: *Value*, *Growth*, *Both*, or *Neither*, with a confidence score.
2. **A ratio scorecard** showing each ratio, its threshold, the stock's actual value, and whether it passed.
3. **Company info**: name, sector, industry, market cap, price, dividend, and a business description.
4. **Qualitative reasoning**: plain-language explanations of *why* the stock does or doesn't fit the value or growth profile.

The methodology automates the framework from the UWaterloo **COMM 101 Stock Picking Assignment** (Prof. Peter Blake, Nov 2025). That assignment did this analysis by hand for **Chicago Atlantic (LIEN)** as a value pick and **Astera Labs (ALAB)** as a growth pick.

---

## Quick Start

Requires Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev,web]"
```

**Web view.** Start a local server, which opens http://127.0.0.1:8000 in your browser:

```bash
analyze-web
```

Type a ticker to see the verdict, score meters, both checklists, the EPS test, and the qualitative factors. You can also enter EPS-test overrides and download the Markdown report. Options: `--port 8080`, `--no-browser`, and `--offline-dir tests/fixtures` (serves saved data only). Stop the server with Ctrl+C.

**Command line:**

```bash
analyze ALAB                      # full report in the terminal
analyze LIEN --export md          # also save reports/LIEN_<date>.md
analyze LIEN --eps-10y-ago 1.23 --min-pe 5.65   # supply 10-year EPS test inputs by hand
analyze ALAB --offline tests/fixtures/ALAB.json # run on saved data, no network
```

| Option | What it does |
|---|---|
| `--export md` | Write a Markdown copy of the report (to `--output-dir`, default `reports/`) |
| `--eps-10y-ago`, `--min-pe` | Override the EPS test's starting EPS and lowest 10-year P/E |
| `--offline FILE` | Analyze a saved JSON snapshot instead of fetching live data |
| `--save-fixture FILE` | Save the fetched data as a JSON snapshot |
| `--config FILE` | Use a custom thresholds file (default: [`src/stock_analyzer/criteria.yaml`](src/stock_analyzer/criteria.yaml)) |

**10+ years of EPS history (optional).** By default the EPS test uses Yahoo Finance's ~4 years of annual EPS. To pull 10+ years from SEC EDGAR filings (US companies), set a User-Agent with your name and email. The SEC requires this and rejects anonymous requests:

```bash
set SEC_USER_AGENT=Your Name you@example.com      # PowerShell: $env:SEC_USER_AGENT="Your Name you@example.com"
```

Run the tests with `pytest`.

### Deploying to Vercel (free Hobby plan)

The repo is set up to deploy on Vercel. [`app.py`](app.py) exposes the Flask app, and [`vercel.json`](vercel.json) allows up to 60 seconds per request.

1. Sign in at [vercel.com](https://vercel.com) with GitHub, then click **Add New → Project** and import this repository.
2. Keep the defaults (Framework: Flask or Other, no build command) and click **Deploy**.
3. *Optional:* under **Settings → Environment Variables**, add `SEC_USER_AGENT` (e.g. `Your Name you@example.com`) to enable 10+ years of SEC EPS history.

Every push to `main` redeploys automatically. Pushes to other branches get preview URLs.

**Limitations:** Yahoo Finance sometimes rate-limits requests from cloud servers. If the deployed site shows fetch errors that don't happen locally, that's the cause. The cache lives in memory per server instance, so a cold start fetches fresh data.

---

## 1. Goals & Non-Goals

### Goals
- Take one ticker as input and produce a full analysis report with no manual data gathering.
- Use the same ratios, thresholds, and tests as the COMM 101 assignment so results can be checked against the hand-done work.
- Make every pass/fail decision traceable: show the formula, the inputs, and the source.
- Generate qualitative commentary that uses the assignment's qualitative factors and is backed by real data about the company.

### Non-Goals (v1)
- **Not investment advice.** This is an educational and analytical tool. Every report includes a disclaimer.
- No portfolio management, trading, or brokerage integration.
- No real-time or intraday data. Daily or most-recent-filing data is enough.
- No stock *screening* across the whole market (Part 1 of the assignment). v1 analyzes **one ticker at a time**. Screening is a possible later extension (see §9).

---

## 2. Methodology (from the COMM 101 assignment)

### 2.1 Value Stock Checklist (Quantitative)

| Ratio | Threshold | Why it matters to a value investor |
|---|---|---|
| Price / Earnings Growth (PEG) | **< 1** | Price is low relative to earnings growth |
| Price / Earnings (P/E) | **< 15** | 15 is the historical market average; below it means cheap relative to earnings |
| Price / Book (P/B) | **< 1** | Market prices the company below the value of its assets |
| Return on Equity (ROE) | **> 15%** | Strong returns on shareholder capital back up the low price |
| Return on Assets (ROA) | **> 4%** | Uses its asset base efficiently |
| Debt / Equity (D/E) | **< 1** | Low financial risk. D/E ≤ 1 is roughly the bar for an investment-grade rating |

### 2.2 10-Year EPS Test (Value confirmation)

| Input | Example (LIEN) |
|---|---|
| EPS 10 years ago | $1.23 |
| Current EPS | $2.11 |
| Lowest P/E in last 10 years | 5.65 |
| Current share price | $10.83 |
| Current annual dividend per share | $1.88 |

Calculation steps:
1. **EPS growth rate** `g = (Current EPS / EPS 10y ago)^(1/10) − 1`, giving ≈ 5.55%
2. **Projected EPS in 10y** `= Current EPS × (1 + g)^10`, giving ≈ $3.62
3. **Projected trading price** `= Lowest 10y P/E × Projected EPS`, giving ≈ $20.45
4. **Projected total value** `= Projected price + 10 × current dividend` (dividends held flat, conservative), giving ≈ $39.25
5. **Annual compound return** `= (Projected total value / Current price)^(1/10) − 1`, giving ≈ **13.74%**

**Pass condition:** annual compound return **≥ 12%**, the modern hurdle rate for taking on equity risk.

### 2.3 Growth Stock Checklist (Quantitative)

| Ratio | Threshold | Why it matters to a growth investor |
|---|---|---|
| Gross Profit Margin | **> 40%** | Products have real pricing power |
| Operating Profit Margin | **10% – 25%** | Profitable while still spending heavily on R&D and expansion |
| Net Profit Margin | **> 10%** | Turns revenue into profit efficiently |
| Return on Equity (ROE) | **> 15%** | Uses capital effectively |
| Current Ratio | **> 2** | Can cover short-term obligations |
| Quick Ratio | **> 1.5** | Can cover short-term obligations without selling inventory |
| Accounts Receivable Turnover | **> 7.3** | Customers pay quickly |
| Inventory Turnover | **> 7.3** | Inventory moves quickly (see sector caveat below) |
| Healthy Working Capital | **Current Assets > Current Liabilities** | Basic solvency |

### 2.4 Qualitative Factors

**Value factors:**
| Factor | What to look for |
|---|---|
| Small is Beautiful | Smaller market cap, overlooked by large institutional investors |
| Annuity Business | Recurring, predictable revenue (interest, subscriptions, contracts) |
| Durable Competitive Advantage | Niche focus, moat, pricing power |
| Revenues & Commodity | Revenue *not* tied to volatile commodity prices |
| Need for Capital | Self-funding business, low debt, low capex needs |
| Insider Buying | Executives buying shares, a sign they believe the stock is undervalued |

**Growth factors:**
| Factor | What to look for |
|---|---|
| Market Potential | Operates in a fast-growing industry (e.g., AI, semiconductors, cloud) |
| New Goods/Services & Customer Orientation | Steady pipeline of new products that respond to customer needs |
| Research & Development | Meaningful R&D spend, fast path from R&D to product |
| Profit Margins | Margins well above the industry average |
| Market Share | Established enough to be credible, with room to expand |

### 2.5 Context & Caveats (baked into the reasoning)
The assignment shows that thresholds should be read **relative to the sector**, not in isolation:
- **ROE and ROA vary widely by sector.** Financials hold large asset bases (for example, CIBC's ROA was ~0.76%), while tech firms are asset-light.
- **Inventory turnover** is low across semiconductors (for example, NVDA ~3.24, AMD ~2.28), so a failed check there is less important for chip companies.
- **Current ratio** above ~3 can signal idle assets (bloated receivables or inventory), not only strength.
- **D/E** is naturally higher for financial firms, so a low D/E in a lender stands out even more.

The tool should report **sector/peer comparisons** where data allows and say when a failed check is "expected for this industry."

---

## 3. Classification Logic

1. Compute the **Value Score** = weighted % of value checks passed (2.1 + the 2.2 EPS test), and the **Growth Score** = weighted % of growth checks passed (2.3).
2. The growth score also includes two **growth signals** that aren't in the assignment tables but separate growth from value in practice: revenue CAGR > 10% and expected next-year EPS growth > 10%. They're marked with `*` in the report.
3. Map the scores to a verdict (a profile needs a score ≥ **60%**):
   - Value qualifies, Growth doesn't → **Value**
   - Growth qualifies, Value doesn't → **Growth**
   - Both qualify → **Both (GARP / blend)**. The report names the stronger lean.
   - Neither qualifies → **Neither**, with the closer fit.
4. Two guards stop misleading verdicts:
   - **Price gate:** a value stock must pass at least 2 of the 3 price checks (PEG, P/E, P/B). Strong ROE/ROA/D/E alone describe a *quality* company, not a *cheap* one (e.g., NVDA).
   - **Minimum coverage:** a profile only qualifies if at least half its checks could be evaluated (e.g., banks, where the liquidity ratios don't apply).
5. Checks with **missing data** or that are **not meaningful for the sector** are shown as `N/A` and left out of the denominator. Missing data lowers the confidence score.
6. A fail that is normal for the sector (see §2.5) is shown as "Fail (sector-typical)" and gets half credit.

All thresholds, weights and guards live in [`criteria.yaml`](src/stock_analyzer/criteria.yaml).

**PEG:** Yahoo Finance often doesn't report PEG, so it's computed as P/E ÷ expected EPS growth (%). Growth comes from analyst long-term estimates, then the next-year estimate, then historical EPS CAGR. The report notes which one was used.

---

## 4. Output Report (per ticker)

```
================================================================
 ALAB: Astera Labs Inc.            Verdict: GROWTH  (Conf: 89%)
================================================================
 Sector: Technology / Semiconductors   Mkt Cap: $XX.XB   Price: $XXX
 Business: <1–2 sentence description>

 VALUE CHECKLIST                         Score: 1/7
 ┌─────────────┬───────────┬─────────┬────────┐
 │ Ratio       │ Threshold │ Actual  │ Result │
 ...
 GROWTH CHECKLIST                        Score: 8/9
 ...
 10-YEAR EPS TEST                        Return: X.X%  (Fail < 12%)
 ...
 QUALITATIVE ANALYSIS
  ✓ Market Potential: ...
  ✓ Research & Development: R&D is XX% of revenue ...
  ...
 CAVEATS
  • Inventory turnover 2.17 fails but is typical for semiconductors (NVDA 3.24, AMD 2.28)
 DATA SOURCES & TIMESTAMP
 ⚠ Educational tool, not investment advice.
================================================================
```

Output formats (in priority order):
1. **Terminal / CLI**: formatted tables (v1)
2. **Markdown / HTML export**: shareable report file
3. **Web UI**: simple input box that shows the report (stretch goal)

---

## 5. Architecture

```
          ticker
            │
            ▼
   ┌──────────────────┐
   │   Data Fetcher   │  pulls price, financial statements, ratios,
   │  (provider layer)│  company profile, insider transactions, EPS history
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │ Ratio Calculator │  computes any ratio the provider doesn't supply
   │                  │  (e.g., AR turnover, inventory turnover, EPS test)
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │ Criteria Engine  │  evaluates value + growth checklists from a
   │ (config-driven)  │  thresholds config file; applies sector context
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │   Classifier     │  scores → verdict + confidence
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │ Qualitative      │  rule-based evidence (R&D %, insider buys,
   │ Analyzer         │  market cap, revenue stability) → narrative
   └────────┬─────────┘
            ▼
   ┌──────────────────┐
   │ Report Renderer  │  CLI / Markdown / HTML
   └──────────────────┘
```

### Stack
- **Language:** Python 3.11+
- **Market data:** [`yfinance`](https://github.com/ranaroussi/yfinance) (free, no key) as the primary source, plus SEC EDGAR XBRL company facts for 10+ years of annual EPS (free, needs `SEC_USER_AGENT`). Providers sit behind a small interface, so others can be added.
- **CLI & formatting:** `typer` + `rich`
- **Config:** thresholds in `src/stock_analyzer/criteria.yaml` (shipped with the package), so they can be changed without code edits
- **Qualitative narrative:** rule-based templates filled with real data (v1). Optional LLM-written narrative (e.g., the Claude API) based on the fetched data (v2).
- **Testing:** `pytest`, with saved fixture data for LIEN and ALAB so tests don't depend on live APIs

### Layout
```
├── README.md
├── pyproject.toml
├── src/stock_analyzer/
│   ├── cli.py                 # entry point: `analyze <TICKER>`
│   ├── criteria.yaml          # all thresholds from §2 and classifier settings
│   ├── analysis.py            # runs the pipeline and builds the Report
│   ├── models.py              # dataclasses passed between stages
│   ├── data/
│   │   ├── provider.py        # provider interface + JSON fixtures
│   │   ├── yfinance_provider.py
│   │   └── sec_edgar.py       # 10+ year annual EPS from SEC filings
│   ├── ratios.py              # ratio calculations
│   ├── eps_test.py            # 10-year EPS test
│   ├── criteria.py            # checklist evaluation
│   ├── sector.py              # sector context rules
│   ├── classifier.py          # verdict + confidence
│   ├── qualitative.py         # qualitative factor evidence + text
│   └── report/                # terminal + Markdown renderers
└── tests/
    ├── fixtures/              # saved LIEN / ALAB data
    └── test_*.py
```

---

## 6. Data Requirements & Known Gaps

| Data point | Likely source | Risk |
|---|---|---|
| P/E, P/B, PEG, ROE, ROA, D/E, margins, current/quick ratio | yfinance `info` | Low. Definitions may differ slightly from Finviz |
| AR turnover, inventory turnover, working capital | Computed from income statement + balance sheet | Low |
| Company description, sector, industry, market cap | yfinance `info` | Low |
| R&D expense (as % of revenue) | Income statement | Low. Not reported by all companies |
| Insider transactions | yfinance `insider_transactions` | Medium. Coverage varies |
| Revenue / EPS growth (3–4 years) | Financial statements | Low |
| **EPS from 10 years ago** | yfinance only gives ~4 years of annual data | **High.** Needs another source (SEC EDGAR XBRL, FMP) or manual input |
| **Lowest P/E over 10 years** | Needs 10 years of price and EPS history | **High.** Same as above |
| Sector / peer benchmark ratios | Static table or peer lookup | Medium |

**Fallbacks:** If 10-year data isn't available, the EPS test uses the longest history available and says so in the report. You can also supply the values with the `--eps-10y-ago` / `--min-pe` CLI flags.

**How the EPS test picks its inputs:**
- **Current EPS** is trailing 12-month EPS.
- **Starting EPS** is the earliest profitable fiscal year in the last 10. Loss years are skipped because growth from a loss is undefined.
- **Lowest P/E** is each fiscal year's lowest share price ÷ that year's EPS, taking the minimum.
- Only a consecutive run of yearly data points is used. Stub periods, like a pre-merger or SPAC-era year, would otherwise distort growth rates.

---

## 7. Validation / Acceptance Criteria

The tool counts as working for v1 when:
- [x] `analyze LIEN` returns **Value**, and its ratio scorecard roughly matches the assignment's Table 3.0 (values will drift with market data over time).
- [x] `analyze ALAB` returns **Growth**, and its scorecard roughly matches Table 6.0, including the **inventory turnover fail flagged as sector-typical**.
- [x] The 10-year EPS test, fed the assignment's LIEN inputs, returns **~13.74%** (unit test with fixed inputs).
- [x] Well-known reference stocks classify sensibly (e.g., a mega-cap growth name vs. a mature bank or utility).
- [x] Invalid tickers, missing data, and negative earnings (P/E undefined) are handled without crashes and explained clearly in the report.
- [x] Every report has a data timestamp, the sources, and a disclaimer.

Live results on 2026-09-29: LIEN → Value, ALAB → Growth, NVDA → Growth (fails the value price gate), AAPL / KO / JPM → Neither.

---

## 8. Milestones

| # | Milestone | Deliverable | Status |
|---|---|---|---|
| M1 | Project setup | `pyproject.toml`, package skeleton, `criteria.yaml` with all thresholds | Done |
| M2 | Data layer | yfinance provider, SEC EDGAR EPS history, saved fixtures for LIEN / ALAB | Done |
| M3 | Ratios & EPS test | All ratios computed, 10-yr EPS test with unit tests | Done |
| M4 | Criteria + classifier | Value/growth scorecards and verdict logic | Done |
| M5 | Qualitative analyzer | Rule-based evidence for each qualitative factor | Done |
| M6 | CLI report | Formatted terminal output end to end | Done |
| M7 | Export | Markdown report files | Done |
| M8 | Web view | Local Flask web page (`analyze-web`) | Done |
| M9 *(stretch)* | Extras | LLM narrative, sector peer comparison, screener | Not started |

---

## 9. Future Extensions
- **Screener mode** (assignment Part 1): filter a universe of stocks by custom thresholds (e.g., P/E < 15, ROE > 15%, D/E < 1, Current Ratio > 2, ROA > 5%, by sector and region).
- **Side-by-side comparison** of two or more tickers.
- **Peer benchmarking**: compare each ratio against the industry median automatically.
- **Historical trend charts** for margins, EPS, and P/E.
- **Canadian / international tickers** (e.g., `.TO` suffixes).

---

## 10. Decisions
1. **Interface:** CLI with Markdown export, plus a local web view (`analyze-web`).
2. **10-year data:** SEC EDGAR XBRL (free), with manual override flags and a shorter-history fallback.
3. **Qualitative narrative:** rule-based templates now. A Claude-written narrative comes later.
4. **Verdicts:** four outcomes (Value / Growth / Both / Neither) with a confidence score.

---

> ⚠️ **Disclaimer:** This project is for educational purposes and is based on coursework methodology. It does not provide financial or investment advice.
