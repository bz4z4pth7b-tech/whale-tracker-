# Whale Edge

Source-backed penny-stock screening, institutional SEC disclosure tracking and daily-bar strategy research. No brokerage integration or order execution. Original `whale tracker` prototype is preserved; `dist/index.html` is the replacement app and does not use its hard-coded performance claims.

## Run

Python 3.12+, no third-party dependencies:

```sh
python -m unittest discover -s tests -v
python research/refresh.py
python -m http.server 8000 --directory dist
```

Open http://localhost:8000. The hosted app checks the public GitHub snapshot every five minutes and falls back to its saved snapshot if unavailable. No keys in frontend code. Source snapshots and observations in this public repository are public.

## Unattended updates

`.github/workflows/research.yml` runs tests and refreshes every four hours on weekdays, on research-code pushes, and manually from Actions. GitHub scheduling may be delayed, and inactive public repositories may have schedules disabled. Review Actions for failures. Prices are completed daily bars, not intraday quotes. Refresh failure preserves prior data with original timestamps and explicit source errors. Partial runs identify missing symbols; coverage changes affect research comparability.

SEC requests identify WhaleEdgeResearch with the public repository contact URL by default. Set optional Actions secret `SEC_USER_AGENT` to an application name and contact email to override this identity. Failed SEC access is surfaced and a 403/429 stops further requests to that host for the run. No paid subscriptions required; Yahoo's unofficial chart endpoint can rate-limit or change. Use a licensed provider before relying on the service operationally.

## Research contract

- Watchlist: 30 configured symbols, not the full market; edit `research/config.json`.
- Screen: adjusted close $0.25 to under $5; trailing 20-session dollar volume at least $1M.
- Relative-volume ranking is a descriptive screen, not a return forecast.
- Breakout: above previous 20 highs, relative volume >=1.5. Momentum: 5-session gain >8%, relative volume >=1.5. Pullback: above previous 20-close average, down day, relative volume <1.2.
- Next-open entry, five-session hold, no overlapping positions per symbol, cash-funded equal sleeves. Return is average sleeve return, not a sum of stock returns.
- 50 basis points cost per side; 150bps stress scenario; daily mark-to-market drawdown.
- First 60% of calendar dates selects highest training return; final 40% is evaluation. Trades cannot cross the training boundary. All three strategy results remain visible.
- No automatic strategy promotion or orders. Fewer than 30 trades is insufficient evidence. Repeatedly inspected holdouts become exploratory.
- Present-day universe and adjusted price thresholds introduce selection/survivorship bias. No full point-in-time/delisted universe, halt model, live spreads, capacity model, taxes, or borrow costs. These results cannot establish attainable returns.
- Daily immutable observations begin at installation in `data/observations/`. They are signal archives, not completed forward-paper trades. Forward performance is not claimed.
- Whale directory covers seven configured institutions: Berkshire, Pershing Square, Scion, Renaissance, Citadel Advisors, Bridgewater and Point72. Follow/unfollow and follow-all operate on this covered universe, not all market participants. Follow preferences and alert thresholds persist locally in the browser.
- SEC 13F information tables are parsed across the latest two distinct reporting periods. Stock-share rows are grouped by CUSIP and class; options and principal amounts are excluded. Positive differences are *reported share increases*, not confirmed purchases. Splits and transfers can alter shares. No dollar purchase amounts or ticker mappings are inferred. Amended periods suppress comparisons. Only consecutive quarter-end periods are compared. Top 30 holdings by share count and top 200 increases per manager are displayed.
- The purchase feed samples the latest 100 SEC Form 4 entries and parses at most 40 original filings per refresh. Only non-derivative P-coded acquisitions qualify. Awards, exercises, derivatives and amended filings are excluded. Transactions aggregate only within the same accession/date/security/ownership type. Joint filers are counted once, with all reporting owners retained. Original reports may later be corrected; this is not a fully reconciled insider database.
- Default alert: strictly more than 100,000 shares. Optional dollar threshold is ANDed, unknown dollars cannot pass. Quarterly increases are opt-in and never meet a positive purchase-dollar filter.
- Browser alerts use stable event IDs, establish a silent baseline on first data load, and notify only for newly seen matching filings dated today or yesterday. Desktop notifications require explicit browser permission and an open page. No service worker, closed-tab push, SMS, email or auto-trading is implemented.
- What's Hot ranks the configured 30-symbol daily watchlist by relative volume, daily gain, or daily dollar turnover; it is not all-market net buying. Most disclosed buying aggregates sampled Form 4 events filed in the last seven calendar days.
- Filing and SEC cache history stays in `data/sec-cache/`; events persist in the snapshot with a 5,000-event retention cap. 13F data can lag quarter end by 45 days; no real-time whale orders or manager win rates are claimed.

## Sources

- https://finance.yahoo.com/ — daily chart bars, adjusted OHLC.
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces — submission metadata.
- https://www.investor.gov/introduction-investing/investing-basics/glossary/form-13f-reports-filed-institutional-investment — filing limitations.

## Maintenance

Run engine tests before changes. Add a frozen rule version before changing strategy logic, preserve prior observations, and compare changes on new forward data. Do not optimize repeatedly on the displayed test interval. Never interpret a source failure or missing symbol as a profitable result.

## Additional verification

Run `node tests/test_signals.cjs` for threshold, follow, sorting and notification-deduplication tests. `tests/test_whales.py` covers SEC XML parsing and filing distinctions. Browser QA covers navigation, threshold persistence and portfolio filtering.
