#!/usr/bin/env python3
import argparse
from io import StringIO
from datetime import datetime
import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

def human_money(x, _pos):
    ax = abs(x)
    if ax >= 1_000_000_000: return f"{x/1_000_000_000:.2f}B"
    if ax >= 1_000_000:     return f"{x/1_000_000:.2f}M"
    if ax >= 1_000:         return f"{x/1_000:.2f}K"
    return f"{x:.0f}"

def fetch_dataset_csv(slug: str) -> pd.DataFrame:
    # Public CSV that includes TVL, borrowed, and per-chain columns where available.
    url = f"https://api.llama.fi/dataset/{slug}.csv"
    r = requests.get(url, timeout=40)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text))
    # Expect a 'date' column in unix seconds
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], unit="s", utc=True).dt.tz_convert("UTC")
    elif "timestamp" in df.columns:
        df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.tz_convert("UTC")
    else:
        raise SystemExit("No date/timestamp column found in dataset.")
    df = df.sort_values("date").reset_index(drop=True)
    return df

def make_charts(df: pd.DataFrame, chains: list[str], out_png: str, plot_net_change: bool):
    if "borrowed" not in df.columns:
        raise SystemExit("This dataset has no 'borrowed' column. Are you sure this is a lending protocol slug?")

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(df["date"], df["borrowed"], linewidth=2, label="Borrowed (Total)")
    # Plot per-chain borrowed if present
    for ch in chains:
        col = f"{ch}-borrowed"
        if col in df.columns:
            ax.plot(df["date"], df[col], linewidth=1.2, label=f"{ch} Borrowed")

    ax.set_title("Borrowed (Outstanding) Over Time")
    ax.set_xlabel("Date (UTC)")
    ax.set_ylabel("USD")
    ax.yaxis.set_major_formatter(FuncFormatter(human_money))
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_png, dpi=160)
    print(f"Saved chart -> {out_png}")

    if plot_net_change:
        # Net Δ borrowed (day over day) — this is NOT true “volume”, just a rough proxy
        # (borrows - repays + price effects in USD terms).
        df2 = df[["date", "borrowed"]].copy()
        df2["net_change"] = df2["borrowed"].diff()
        fig2, ax2 = plt.subplots(figsize=(11, 6))
        ax2.plot(df2["date"], df2["net_change"], linewidth=1.5)
        ax2.set_title("Net Change in Borrowed (Δ Borrowed) — proxy for lending flow (caveat: includes price effects)")
        ax2.set_xlabel("Date (UTC)")
        ax2.set_ylabel("Δ USD")
        ax2.yaxis.set_major_formatter(FuncFormatter(human_money))
        ax2.grid(True, alpha=0.25)
        fig2.tight_layout()
        out2 = out_png.replace(".png", "_net_change.png")
        fig2.savefig(out2, dpi=160)
        print(f"Saved chart -> {out2}")

def main():
    p = argparse.ArgumentParser(description="Plot Borrowed (outstanding) from DeFiLlama dataset CSV.")
    p.add_argument("--slug", default="meridian", help="DeFiLlama protocol slug (e.g., meridian, aave-v3)")
    p.add_argument("--chains", default="Telos,Taiko,Fuse", help="Comma-separated chains to try plotting per-chain borrowed")
    p.add_argument("--out-png", default="borrowed_timeseries.png", help="Output PNG filename")
    p.add_argument("--net-change", action="store_true", help="Also plot Δ Borrowed as a rough volume proxy")
    args = p.parse_args()

    chains = [c.strip() for c in args.chains.split(",") if c.strip()]
    df = fetch_dataset_csv(args.slug)
    make_charts(df, chains, args.out_png, args.net_change)

if __name__ == "__main__":
    main()
