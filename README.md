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

Set Actions secret `SEC_USER_AGENT` to `WhaleEdge your-contact-email@example.com` with a real contact email. Without it, SEC tracking is explicitly unavailable. No paid subscriptions required; Yahoo's unofficial chart endpoint can rate-limit or change. Use a licensed provider before relying on the service operationally.

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
- Whale feed is SEC filing metadata and document links for three managers. It does not parse holdings deltas or infer trades. 13F can lag quarter-end by 45 days; no real-time whale orders or manager win rates are claimed.

## Sources

- https://finance.yahoo.com/ — daily chart bars, adjusted OHLC.
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces — submission metadata.
- https://www.investor.gov/introduction-investing/investing-basics/glossary/form-13f-reports-filed-institutional-investment — filing limitations.

## Maintenance

Run engine tests before changes. Add a frozen rule version before changing strategy logic, preserve prior observations, and compare changes on new forward data. Do not optimize repeatedly on the displayed test interval. Never interpret a source failure or missing symbol as a profitable result.
