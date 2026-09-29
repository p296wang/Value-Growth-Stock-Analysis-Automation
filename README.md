# Value / Growth Stock Analysis Automation

Enter a stock ticker and get back:

1. **A verdict**: *Value*, *Growth*, *Both*, or *Neither*, with a confidence score.
2. **A ratio scorecard** showing each ratio, its threshold, the stock's actual value, and whether it passed.
3. **Company info**: name, sector, industry, market cap, price, dividend, and a business description.
4. **Qualitative reasoning**: plain-language explanations of *why* the stock does or doesn't fit the value or growth profile.

The methodology automates the framework from the UWaterloo **COMM 101 Stock Picking Assignment** (Prof. Peter Blake, Nov 2025). That assignment did this analysis by hand for **Chicago Atlantic (LIEN)** as a value pick and **Astera Labs (ALAB)** as a growth pick.

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

1. Compute the **Value Score** = % of value checks passed (2.1 + 2.2), and the **Growth Score** = % of growth checks passed (2.3).
2. Supplement with **growth signals** that aren't in the assignment tables but separate growth from value in practice: revenue growth (YoY / 3y CAGR), EPS growth, forward vs. trailing P/E. These act as tie-breakers.
3. Map the scores to a verdict:
   - Value Score ≥ threshold *and* Growth Score < threshold → **Value**
   - Growth Score ≥ threshold *and* Value Score < threshold → **Growth**
   - Both ≥ threshold → **Both (GARP / blend)**. The report explains which profile fits more strongly.
   - Neither → **Neither**, with the main failing reasons.
4. Checks with **missing data** are shown as `N/A` and left out of the denominator. The report lists how many checks couldn't be evaluated.
5. Sector-adjusted soft passes (see §2.5) are flagged as "Fail (sector-typical)" and weighted less heavily.

*Exact thresholds and weights for step 3 are configurable and will be tuned using the known test cases in §7.*

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

### Proposed stack
- **Language:** Python 3.11+
- **Market data:** [`yfinance`](https://github.com/ranaroussi/yfinance) (free, no key) as the primary source. A pluggable provider interface allows adding Financial Modeling Prep / Alpha Vantage / SEC EDGAR later.
- **CLI & formatting:** `typer` + `rich`
- **Config:** thresholds in `config/criteria.yaml`, so they can be changed without code edits
- **Qualitative narrative:** rule-based templates filled with real data (v1). Optional LLM-written narrative (e.g., the Claude API) based on the fetched data (v2).
- **Testing:** `pytest`, with saved fixture data for LIEN and ALAB so tests don't depend on live APIs

### Proposed layout
```
├── README.md
├── pyproject.toml
├── config/
│   └── criteria.yaml          # all thresholds from §2
├── src/stock_analyzer/
│   ├── cli.py                 # entry point: `analyze <TICKER>`
│   ├── data/
│   │   ├── provider.py        # abstract interface
│   │   └── yfinance_provider.py
│   ├── ratios.py              # ratio + 10-yr EPS test calculations
│   ├── criteria.py            # checklist evaluation
│   ├── classifier.py          # verdict + confidence
│   ├── qualitative.py         # qualitative factor evidence + text
│   ├── sector.py              # sector benchmarks / caveats
│   └── report/
│       ├── terminal.py
│       └── markdown.py
└── tests/
    ├── fixtures/              # cached LIEN / ALAB data
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

**Fallbacks:** If 10-year data isn't available, the EPS test uses the longest history available (and labels it, e.g., "4-year EPS test"), or asks the user for the missing values with `--eps-10y-ago` / `--min-pe` CLI flags.

---

## 7. Validation / Acceptance Criteria

The tool counts as working for v1 when:
- [ ] `analyze LIEN` returns **Value**, and its ratio scorecard roughly matches the assignment's Table 3.0 (values will drift with market data over time).
- [ ] `analyze ALAB` returns **Growth**, and its scorecard roughly matches Table 6.0, including the **inventory turnover fail flagged as sector-typical**.
- [ ] The 10-year EPS test, fed the assignment's LIEN inputs, returns **~13.74%** (unit test with fixed inputs).
- [ ] Well-known reference stocks classify sensibly (e.g., a mega-cap growth name vs. a mature bank or utility).
- [ ] Invalid tickers, missing data, and negative earnings (P/E undefined) are handled without crashes and explained clearly in the report.
- [ ] Every report has a data timestamp, the sources, and a disclaimer.

---

## 8. Milestones

| # | Milestone | Deliverable |
|---|---|---|
| M1 | Project setup | `pyproject.toml`, package skeleton, `criteria.yaml` with all thresholds |
| M2 | Data layer | yfinance provider + cached fixtures for LIEN / ALAB |
| M3 | Ratios & EPS test | All ratios computed, 10-yr EPS test with unit tests |
| M4 | Criteria + classifier | Value/growth scorecards and verdict logic |
| M5 | Qualitative analyzer | Rule-based evidence for each qualitative factor |
| M6 | CLI report | Formatted terminal output end to end |
| M7 | Export | Markdown/HTML report files |
| M8 *(stretch)* | Extras | LLM narrative, web UI, 10-yr data source, sector peer comparison |

---

## 9. Future Extensions
- **Screener mode** (assignment Part 1): filter a universe of stocks by custom thresholds (e.g., P/E < 15, ROE > 15%, D/E < 1, Current Ratio > 2, ROA > 5%, by sector and region).
- **Side-by-side comparison** of two or more tickers.
- **Peer benchmarking**: compare each ratio against the industry median automatically.
- **Historical trend charts** for margins, EPS, and P/E.
- **Canadian / international tickers** (e.g., `.TO` suffixes).

---

## 10. Open Questions
1. **Interface priority:** Is a CLI enough for v1, or is a web UI (e.g., Streamlit) needed early?
2. **10-year data:** Are you OK with adding a free-API-key source (FMP / Alpha Vantage) or SEC EDGAR parsing, or should v1 use manual inputs for the EPS test?
3. **Qualitative narrative:** Rule-based only, or use an LLM (needs an API key) for richer write-ups?
4. **"Both" / "Neither" handling:** Keep four verdicts, or always force a Value vs. Growth lean?

---

> ⚠️ **Disclaimer:** This project is for educational purposes and is based on coursework methodology. It does not provide financial or investment advice.
