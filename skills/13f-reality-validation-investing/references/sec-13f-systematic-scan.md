# SEC 13F systematic scan notes

This reference captures the practical workflow discovered while building a quarterly 13F screen for institutional breadth changes.

## Best free canonical source

Use SEC Form 13F structured quarterly data sets:

- Index page: `https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets`
- Older files use names like `2023q4_form13f.zip`.
- Recent files may use date-range filenames, e.g.:
  - `01jun2025-31aug2025_form13f.zip`
  - `01sep2025-30nov2025_form13f.zip`
  - `01dec2025-28feb2026_form13f.zip`
  - `01mar2026-31may2026_form13f.zip`

Do **not** assume `YYYYqN_form13f.zip` exists for newer quarters. Parse the index page or maintain a date-range mapping.

## ZIP structure variations

Recent ZIPs may contain files under a directory prefix, e.g.:

```text
01JUN2025-31AUG2025_form13f/COVERPAGE.tsv
01JUN2025-31AUG2025_form13f/INFOTABLE.tsv
01JUN2025-31AUG2025_form13f/SUBMISSION.tsv
```

Older ZIPs may contain files at root. Robust code should find files by `endswith('INFOTABLE.tsv')`, etc.

## Minimum files used

- `COVERPAGE.tsv`: `ACCESSION_NUMBER`, `REPORTCALENDARORQUARTER`, `REPORTTYPE`, manager identity fields.
- `SUBMISSION.tsv`: maps `ACCESSION_NUMBER` to `CIK` and period metadata.
- `INFOTABLE.tsv`: holdings rows with issuer, CUSIP, FIGI, VALUE, SSHPRNAMT, PUTCALL, etc.

## Filtering recipe

1. Select filings where `COVERPAGE.REPORTCALENDARORQUARTER` equals the quarter end target, e.g. `31-MAR-2026`.
2. Restrict to `REPORTTYPE` starting with `13F`.
3. Exclude rows where `PUTCALL` is non-empty if screening long equity shares only.
4. Prefer `SSHPRNAMTTYPE == SH` when available.
5. Aggregate by `(manager CIK, CUSIP)`; if duplicate rows exist, add shares.
6. Aggregate each CUSIP by holder count, total shares held, and total reported market value.

Remember SEC `VALUE` is in thousands of dollars.

## Multi-quarter metrics

For each CUSIP across 3–4 quarters:

- `holders[q]`: count distinct managers holding the CUSIP.
- `shares[q]`: total shares held.
- `market_value[q]`: sum of SEC `VALUE`.
- `new_positions`: managers in current quarter but not previous quarter.
- `sold_out`: managers in previous quarter but not current quarter.
- `increased_positions`: managers with current shares > previous shares, allowing tiny tolerance.
- `decreased_positions`: managers with current shares < previous shares.
- `holder_delta_4q`: latest holder count minus earliest holder count.
- `holder_delta_qoq`: latest minus previous quarter.
- `share_delta_pct`: latest total shares vs earliest total shares.

Prefer holder breadth/new positions/share count over market value, because market value can rise from price appreciation.

## Practical pitfalls

- Ticker mapping is not clean in SEC bulk data. The data is keyed by CUSIP/FIGI/name; use a ticker-to-CUSIP mapping or cross-check candidate names manually.
- Corporate actions, spin-offs, IPOs, share-class changes, and foreign issuer CUSIPs can create false acceleration.
- ETFs, CEFs, trusts, and index products can pollute screens; filter obvious names/classes but verify manually.
- New IPOs naturally show many new holders; treat them separately from true multi-quarter accumulation.
- A rising holder count with falling total shares means broad but shallow adoption, or large-holder selling offsetting new smaller holders. This can still be useful but is weaker than breadth + shares both rising.

## Cross-check sources

Use SEC as canonical, then cross-check selected tickers with:

- Nasdaq institutional-holdings endpoint/pages for latest ticker-level aggregates.
- MarketBeat / HoldingsChannel for visible holder tables.
- Company filings and industry data for reality validation.

Do not rely on free aggregator pages as the only source for a high-conviction conclusion.
