# Value / Growth Stock Analyzer

Look up a stock and see whether it fits a **value** or **growth** profile, and why.

Enter a ticker to get:

- **A verdict**: Value, Growth, Both, or Neither, with a confidence score
- **A ratio scorecard**: each ratio, its threshold, the stock's actual value, and pass/fail, with sector context
- **A 10-year EPS test**: projects earnings and share value forward and compares the expected return to a 12% hurdle
- **Charts**: price history, revenue and net income, EPS, and profit margins
- **Plain-language reasons**: qualitative factors like insider buying, R&D spend, market potential, and recurring revenue

> ⚠️ For educational purposes only. Not financial or investment advice.

---

## Quick Start

Requires Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

**Web view.** Start a local server, which opens http://127.0.0.1:8000 in your browser:

```bash
analyze-web
```

Options: `--port 8080`, `--no-browser`, and `--offline-dir tests/fixtures` (serves saved data only). Stop the server with Ctrl+C.

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

[`app.py`](app.py) exposes the Flask app, and [`vercel.json`](vercel.json) allows up to 60 seconds per request.

1. Sign in at [vercel.com](https://vercel.com) with GitHub, then click **Add New → Project** and import this repository.
2. Keep the defaults (Framework: Flask or Other, no build command) and click **Deploy**.
3. *Optional:* under **Settings → Environment Variables**, add `SEC_USER_AGENT` (e.g. `Your Name you@example.com`) to enable 10+ years of SEC EPS history.

Every push to `main` redeploys automatically. Pushes to other branches get preview URLs.

**Limitations:** Yahoo Finance sometimes rate-limits requests from cloud servers. If the deployed site shows fetch errors that don't happen locally, that's the cause. The cache lives in memory per server instance, so a cold start fetches fresh data.

---

## How It Works

### Value checklist

| Ratio | Threshold | Why it matters |
|---|---|---|
| Price / Earnings Growth (PEG) | **< 1** | Price is low relative to earnings growth |
| Price / Earnings (P/E) | **< 15** | 15 is the long-run market average; below it is cheap relative to earnings |
| Price / Book (P/B) | **< 1** | The market prices the company below the value of its assets |
| Return on Equity (ROE) | **> 15%** | Strong returns on shareholder capital back up the low price |
| Return on Assets (ROA) | **> 4%** | Uses its asset base efficiently |
| Debt / Equity (D/E) | **< 1** | Low financial risk. D/E ≤ 1 is roughly the bar for an investment-grade rating |

### 10-year EPS test

Projects earnings and share value 10 years out, then asks whether buying today would return at least **12% a year**, the usual hurdle for taking on equity risk. Example:

| Input | Example |
|---|---|
| EPS 10 years ago | $2.00 |
| Current EPS | $3.00 |
| Lowest P/E in the last 10 years | 12 |
| Current share price | $18.00 |
| Annual dividend per share | $1.00 |

1. **EPS growth rate** `g = (current EPS / EPS 10y ago)^(1/10) − 1`, giving ≈ 4.14%
2. **Projected EPS in 10y** `= current EPS × (1 + g)^10`, giving $4.50
3. **Projected trading price** `= lowest 10y P/E × projected EPS`, giving $54.00
4. **Projected total value** `= projected price + 10 × current dividend` (dividends held flat), giving $64.00
5. **Annual compound return** `= (projected total value / current price)^(1/10) − 1`, giving ≈ **13.5%**, a pass

How the inputs are picked:
- **Current EPS** is trailing 12-month EPS.
- **Starting EPS** is the earliest profitable fiscal year in the last 10. Loss years are skipped because growth from a loss is undefined.
- **Lowest P/E** is each fiscal year's lowest share price ÷ that year's EPS, taking the minimum.
- Only a consecutive run of yearly data is used. Stub periods, like a pre-merger year, would otherwise distort growth rates.
- With less than 10 years of history, the test uses what's available and says so.

### Growth checklist

| Ratio | Threshold | Why it matters |
|---|---|---|
| Gross Profit Margin | **> 40%** | Products have real pricing power |
| Operating Profit Margin | **10% – 25%** | Profitable while still spending heavily on R&D and expansion |
| Net Profit Margin | **> 10%** | Turns revenue into profit efficiently |
| Return on Equity (ROE) | **> 15%** | Uses capital effectively |
| Current Ratio | **> 2** | Can cover short-term obligations |
| Quick Ratio | **> 1.5** | Can cover short-term obligations without selling inventory |
| Accounts Receivable Turnover | **> 7.3** | Customers pay quickly |
| Inventory Turnover | **> 7.3** | Inventory moves quickly |
| Healthy Working Capital | **Current Assets > Current Liabilities** | Basic solvency |
| Revenue Growth * | **> 10% a year** | Sales are expanding quickly |
| Expected EPS Growth * | **> 10% next year** | Analysts expect earnings to keep growing |

\* Extra growth signals on top of the core checklist.

### Qualitative factors

| Value factors | Growth factors |
|---|---|
| Small is Beautiful: smaller companies are often overlooked | Market Potential: operates in a fast-growing industry |
| Annuity Business: recurring, predictable revenue | New Goods/Services: R&D turning into new sales |
| Durable Competitive Advantage: pricing power, a moat | Research & Development: meaningful R&D spend |
| Revenues & Commodity: revenue not tied to commodity prices | Profit Margins: well above average |
| Need for Capital: self-funding, low debt | Market Share: credible position with room to expand |
| Insider Buying: executives buying their own shares | |

### Sector context

Thresholds are read relative to the sector:
- **Financial firms:** liquidity ratios and gross margin are not meaningful, so they're shown as N/A. Low ROA and higher D/E are normal.
- **Chipmakers:** low inventory turnover is normal (NVDA ~3.2, AMD ~2.3), so it's shown as "Fail (sector-typical)" and gets half credit.
- **Very high current ratios** (above ~3) can mean idle cash or bloated receivables, not just strength.

### Verdict

1. The **value score** is the weighted share of value checks passed (including the EPS test). The **growth score** is the same for the growth checks.
2. A profile needs a score of **60%** or more to qualify:
   - Only value qualifies → **Value**
   - Only growth qualifies → **Growth**
   - Both qualify → **Both** (growth at a reasonable price), with the stronger lean named
   - Neither qualifies → **Neither**, with the closer fit named
3. Two guards stop misleading verdicts:
   - **Price gate:** a value stock must pass at least 2 of the 3 price checks (PEG, P/E, P/B). Strong ROE, ROA and D/E alone describe a *quality* company, not a *cheap* one.
   - **Minimum coverage:** a profile only qualifies if at least half its checks could be evaluated.
4. Missing data is shown as N/A, left out of the score, and lowers the confidence.

All thresholds, weights and guards live in [`criteria.yaml`](src/stock_analyzer/criteria.yaml).

**PEG:** Yahoo Finance often doesn't report PEG, so it's computed as P/E ÷ expected EPS growth (%), using analyst long-term estimates, then the next-year estimate, then historical EPS growth. The report says which was used.

---

## Project Layout

```
├── app.py                     # Vercel entrypoint
├── src/stock_analyzer/
│   ├── cli.py                 # `analyze <TICKER>`
│   ├── criteria.yaml          # thresholds and classifier settings
│   ├── analysis.py            # runs the pipeline and builds the report
│   ├── data/                  # yfinance + SEC EDGAR providers, JSON fixtures
│   ├── ratios.py              # ratio calculations
│   ├── eps_test.py            # 10-year EPS test
│   ├── criteria.py            # checklist evaluation
│   ├── sector.py              # sector context rules
│   ├── classifier.py          # verdict + confidence
│   ├── qualitative.py         # qualitative factors
│   ├── history.py             # chart data
│   ├── report/                # terminal + Markdown reports
│   └── web/                   # Flask web view (`analyze-web`)
└── tests/                     # pytest suite with saved LIEN / ALAB data
```

**Data sources:** [Yahoo Finance](https://finance.yahoo.com) via [`yfinance`](https://github.com/ranaroussi/yfinance) for prices, ratios, statements and insider trades, plus optional [SEC EDGAR](https://www.sec.gov/edgar) filings for long-run EPS history.
