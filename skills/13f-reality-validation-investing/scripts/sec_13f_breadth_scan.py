#!/usr/bin/env python3
"""
Scan SEC Form 13F structured data sets for multi-quarter institutional breadth changes.

Usage:
  python scripts/sec_13f_breadth_scan.py \
    --quarters 2025Q2=/files/structureddata/data/form-13f-data-sets/01jun2025-31aug2025_form13f.zip=30-JUN-2025 \
               2025Q3=/files/structureddata/data/form-13f-data-sets/01sep2025-30nov2025_form13f.zip=30-SEP-2025 \
               2025Q4=/files/structureddata/data/form-13f-data-sets/01dec2025-28feb2026_form13f.zip=31-DEC-2025 \
               2026Q1=/files/structureddata/data/form-13f-data-sets/01mar2026-31may2026_form13f.zip=31-MAR-2026 \
    --cache /opt/data/output/13f_scan_cache \
    --out /opt/data/output/13f_scan_candidates.json

Quarter argument format:
  LABEL=SEC_ZIP_PATH_OR_URL=REPORTCALENDARORQUARTER

Notes:
- SEC VALUE is in thousands of dollars.
- Output is keyed by CUSIP/name, not clean ticker.
- This is a research screen, not an investment recommendation.
"""

import argparse
import collections
import csv
import io
import json
import os
import re
import urllib.request
import zipfile

SEC_BASE = "https://www.sec.gov"
UA = "HermesAgent 13F research contact@example.com"

EXCLUDE_RE = re.compile(
    r"ETF|ETN|TRUST|ISHARES|SPDR|VANGUARD|INVESCO|DIREXION|PROSHARES|"
    r"SELECT SECTOR|INDEX|FUND|ARK ",
    re.I,
)


def zip_member(zf, suffix):
    return next(n for n in zf.namelist() if n.endswith(suffix))


def fetch_zip(path_or_url, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    url = path_or_url if path_or_url.startswith("http") else SEC_BASE + path_or_url
    fn = os.path.join(cache_dir, os.path.basename(path_or_url))
    if not os.path.exists(fn):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=180) as r:
            data = r.read()
        with open(fn, "wb") as f:
            f.write(data)
    return fn


def load_quarter(label, path_or_url, target_period, cache_dir):
    fn = fetch_zip(path_or_url, cache_dir)
    zf = zipfile.ZipFile(fn)

    acc_cik = {}
    with zf.open(zip_member(zf, "SUBMISSION.tsv")) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"), delimiter="\t")
        for r in reader:
            acc_cik[r["ACCESSION_NUMBER"]] = r.get("CIK") or r["ACCESSION_NUMBER"]

    accessions = set()
    with zf.open(zip_member(zf, "COVERPAGE.tsv")) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"), delimiter="\t")
        for r in reader:
            if r.get("REPORTCALENDARORQUARTER") == target_period and r.get("REPORTTYPE", "").startswith("13F"):
                accessions.add(r["ACCESSION_NUMBER"])

    pos = {}
    names = {}
    classes = {}
    values = collections.defaultdict(float)

    with zf.open(zip_member(zf, "INFOTABLE.tsv")) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"), delimiter="\t")
        for r in reader:
            acc = r["ACCESSION_NUMBER"]
            if acc not in accessions:
                continue
            if r.get("PUTCALL"):
                continue
            if r.get("SSHPRNAMTTYPE") not in ("SH", ""):
                continue
            cusip = (r.get("CUSIP") or "").strip()
            if not cusip:
                continue
            try:
                shares = float(r.get("SSHPRNAMT") or 0)
                value = float(r.get("VALUE") or 0)
            except ValueError:
                continue
            if shares <= 0:
                continue
            manager = acc_cik.get(acc, acc)
            pos[(manager, cusip)] = pos.get((manager, cusip), 0.0) + shares
            names[cusip] = r.get("NAMEOFISSUER", "").strip()
            classes[cusip] = r.get("TITLEOFCLASS", "").strip()
            values[cusip] += value

    by_cusip = collections.defaultdict(dict)
    for (manager, cusip), shares in pos.items():
        by_cusip[cusip][manager] = shares

    return {
        "label": label,
        "target_period": target_period,
        "accessions": len(accessions),
        "positions": len(pos),
        "cusips": len(by_cusip),
        "by_cusip": by_cusip,
        "names": names,
        "classes": classes,
        "values": values,
    }


def score_rows(qdata, min_latest_holders):
    labels = list(qdata.keys())
    latest = labels[-1]
    previous = labels[-2]
    all_cusips = set().union(*(set(qdata[q]["by_cusip"]) for q in labels))

    rows = []
    for cusip in all_cusips:
        name = qdata[latest]["names"].get(cusip) or next(
            (qdata[q]["names"].get(cusip) for q in labels if cusip in qdata[q]["names"]),
            "",
        )
        cls = qdata[latest]["classes"].get(cusip) or ""
        if EXCLUDE_RE.search(name) or EXCLUDE_RE.search(cls):
            continue

        holders = []
        shares = []
        values = []
        for q in labels:
            m = qdata[q]["by_cusip"].get(cusip, {})
            holders.append(len(m))
            shares.append(sum(m.values()))
            values.append(qdata[q]["values"].get(cusip, 0.0))

        if holders[-1] < min_latest_holders:
            continue

        prev_map = qdata[previous]["by_cusip"].get(cusip, {})
        now_map = qdata[latest]["by_cusip"].get(cusip, {})
        new = len(set(now_map) - set(prev_map))
        sold = len(set(prev_map) - set(now_map))
        inc = dec = 0
        for manager in set(now_map) & set(prev_map):
            if now_map[manager] > prev_map[manager] * 1.001:
                inc += 1
            elif now_map[manager] < prev_map[manager] * 0.999:
                dec += 1

        holder_gaps = [holders[i + 1] - holders[i] for i in range(len(holders) - 1)]
        inc_quarters = sum(1 for gap in holder_gaps if gap > 0)
        score = 0
        score += min(5, max(0, (holders[-1] - holders[0]) / max(20, holders[0] or 20) * 10))
        score += 2 if inc_quarters >= 2 else 0
        score += 2 if new > sold else 0
        score += 2 if inc > dec else 0
        score += 2 if shares[-1] > shares[0] else 0

        rows.append({
            "cusip": cusip,
            "name": name,
            "class": cls,
            "holders": holders,
            "shares": shares,
            "value_k": values,
            "holder_delta_full_period": holders[-1] - holders[0],
            "holder_delta_qoq": holders[-1] - holders[-2],
            "inc_quarters": inc_quarters,
            "new": new,
            "sold": sold,
            "increased": inc,
            "decreased": dec,
            "share_delta_pct": (shares[-1] / shares[0] - 1) * 100 if shares[0] else None,
            "score": score,
        })

    return sorted(
        rows,
        key=lambda r: (r["score"], r["holder_delta_full_period"], r["new"] - r["sold"], r["holder_delta_qoq"]),
        reverse=True,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quarters", nargs="+", required=True, help="LABEL=ZIP_PATH_OR_URL=REPORT_PERIOD")
    ap.add_argument("--cache", default="/opt/data/output/13f_scan_cache")
    ap.add_argument("--out", default="/opt/data/output/13f_scan_candidates.json")
    ap.add_argument("--min-latest-holders", type=int, default=50)
    args = ap.parse_args()

    qdata = collections.OrderedDict()
    meta = []
    for spec in args.quarters:
        label, path_or_url, target = spec.split("=", 2)
        q = load_quarter(label, path_or_url, target, args.cache)
        qdata[label] = q
        meta.append({k: q[k] for k in ["label", "target_period", "accessions", "positions", "cusips"]})

    rows = score_rows(qdata, args.min_latest_holders)
    out = {"quarters": meta, "candidates": rows}
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"quarters": meta, "candidate_count": len(rows), "out": args.out}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
