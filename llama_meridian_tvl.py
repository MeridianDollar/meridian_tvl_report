#!/usr/bin/env python3
import argparse
from datetime import datetime
import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

API = "https://api.llama.fi"

def money_fmt(x, _pos):
    ax = abs(x)
    if ax >= 1_000_000_000: return f"{x/1_000_000_000:.2f}B"
    if ax >= 1_000_000:     return f"{x/1_000_000:.2f}M"
    if ax >= 1_000:         return f"{x/1_000:.2f}K"
    return f"{x:.0f}"

def fetch_protocol(slug: str) -> dict:
    r = requests.get(f"{API}/protocol/{slug}", timeout=40)
    r.raise_for_status()
    return r.json()

def to_df(series):
    # series: list of {"date": unix, "totalLiquidityUSD" or "tvl": float}
    rows = []
    for p in series or []:
        v = p.get("totalLiquidityUSD", p.get("tvl", 0.0))
        rows.append({"date": datetime.utcfromtimestamp(int(p["date"])), "value": float(v or 0.0)})
    df = pd.DataFrame(rows).sort_values("date")
    return df

def plot_tvl(df_overall: pd.DataFrame, per_chain: dict[str, pd.DataFrame], out_png: str, title: str):
    if df_overall.empty:
        raise SystemExit("No TVL history returned by API.")
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(df_overall["date"], df_overall["value"], linewidth=2, label="Overall TVL (USD)")
    for ch, dfc in per_chain.items():
        if dfc.empty: 
            continue
        ax.plot(dfc["date"], dfc["value"], linewidth=1.2, label=f"{ch} TVL")
    ax.set_title(title)
    ax.set_xlabel("Date (UTC)")
    ax.set_ylabel("TVL (USD)")
    ax.yaxis.set_major_formatter(FuncFormatter(money_fmt))
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    print(f"Saved chart -> {out_png}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", default="meridian", help="Protocol slug (try 'meridian' or 'meridian-finance')")
    ap.add_argument("--chains", default="", help="Comma-separated chain filter (optional)")
    ap.add_argument("--out", default="tvl_chart.png", help="Output PNG")
    args = ap.parse_args()

    data = fetch_protocol(args.slug)
    overall_hist = data.get("tvl", []) or []
    df_overall = to_df(overall_hist)

    chain_tvls = data.get("chainTvls", {}) or {}
    if args.chains:
        wanted = {c.strip() for c in args.chains.split(",") if c.strip()}
        chain_tvls = {k: v for k, v in chain_tvls.items() if k in wanted}

    per_chain = {ch: to_df(payload.get("tvl", []) or []) for ch, payload in chain_tvls.items()}
    title = f"{data.get('name') or args.slug} — TVL Over Time"
    plot_tvl(df_overall, per_chain, args.out, title)

if __name__ == "__main__":
    main()
