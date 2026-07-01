# 13F Reality Validation

An AI-agent skill for finding institutional accumulation signals, then validating the thesis with real-world price, supply-demand, and financial data.

This repository publishes a reusable **13F + Reality Validation** investment research skill: use institutional 13F accumulation as a discovery signal, then validate the underlying thesis with real-world prices, supply-demand data, financial transmission, valuation, and crowding checks.

> Not financial advice. These are research workflows for evidence collection and thesis validation.

## Skills

### `13f-reality-validation-investing`

Use this when you want to discover or evaluate stocks by combining:

1. **13F institutional accumulation signals**
   - Holder-count breadth
   - New positions
   - Increased vs decreased positions
   - Total shares held
   - Quality of entering/increasing institutions

2. **Reality / industry validation**
   - Product or commodity price curves
   - Shortages, inventory, lead times, backlogs
   - Customer demand and pricing power
   - Financial statement transmission
   - Valuation and crowding

Core idea:

> Do not use 13F as an answer machine. Use 13F to find questions; then use reality and industry data to verify whether institutions are likely buying the right thesis.

## Install in Hermes Agent

Install directly from the raw `SKILL.md` URL:

```bash
hermes skills install https://raw.githubusercontent.com/xij669/13f-reality-validation/main/skills/13f-reality-validation-investing/SKILL.md
```

Then use it in a session:

```bash
hermes -s 13f-reality-validation-investing
```

Or ask Hermes naturally, for example:

```text
Use the 13F reality validation framework to evaluate MU and STX.
```

## Use with other agents

If your agent does not support Hermes skills directly, give it the raw `SKILL.md` link and ask it to follow the workflow:

```text
Read and follow this investment research workflow:
https://raw.githubusercontent.com/xij669/13f-reality-validation/main/skills/13f-reality-validation-investing/SKILL.md
```

## Repository structure

```text
skills/
└── 13f-reality-validation-investing/
    ├── SKILL.md
    ├── references/
    │   └── sec-13f-systematic-scan.md
    └── scripts/
        └── sec_13f_breadth_scan.py
```

## Data sources suggested by the skill

- SEC Form 13F structured quarterly data sets
- SEC EDGAR 13F filings
- Nasdaq institutional holdings pages/endpoints
- WhaleWisdom / Fintel / HoldingsChannel / MarketBeat, where accessible
- Company filings and earnings calls
- Industry-specific price, inventory, backlog, utilization, and demand data

## License

MIT. See [`LICENSE`](LICENSE).
