"""
Berechnet tägliche Marktdaten für den Trading Bot:
- S&P500 Momentum-Ranking (12-1 Monats-Formel)
- Regime-Indikatoren (S&P500 200MA, VIX, Marktbreite)

Schreibt Ergebnis nach market_data.json.
Wird nightly via GitHub Action ausgeführt.
"""

from __future__ import annotations

import json
from datetime import datetime, date, timedelta
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

MARKET_DATA_FILE = Path(__file__).parent.parent / "market_data.json"

TRADING_DAYS_1M = 21
TRADING_DAYS_12M = 252


def fetch_sp500_constituents() -> pd.DataFrame:
    """S&P500 Constituents von Wikipedia (Symbol + GICS Sector)."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0 (TradeBot Market Data Fetcher)"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    df = pd.read_html(resp.text)[0]
    df["Symbol"] = df["Symbol"].str.replace(".", "-", regex=False)
    return df[["Symbol", "GICS Sector"]].rename(
        columns={"Symbol": "ticker", "GICS Sector": "sector"}
    )


def fetch_price_history(tickers: list[str], period: str = "14mo") -> pd.DataFrame:
    """Batch-Download der Schlusskurse (adjustiert) für alle Ticker."""
    data = yf.download(
        tickers,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    return data["Close"] if "Close" in data else data


def compute_momentum_12_1(prices: pd.DataFrame) -> pd.Series:
    """
    12-1 Momentum: Rendite von t-12 Monaten bis t-1 Monat (letzten Monat ausgelassen).
    Klassische Definition nach Jegadeesh & Titman (1993).

    Filtert Ausreißer > 500% raus — in der Regel Datenartefakte (Spin-offs, IPOs).
    """
    if len(prices) < TRADING_DAYS_12M:
        return pd.Series(dtype=float)

    price_1mo_ago = prices.iloc[-TRADING_DAYS_1M]
    price_12mo_ago = prices.iloc[-TRADING_DAYS_12M]

    # Require non-zero, non-NaN prices at both anchor points
    valid = price_12mo_ago.notna() & price_1mo_ago.notna() & (price_12mo_ago > 0)
    price_12mo_ago = price_12mo_ago[valid]
    price_1mo_ago = price_1mo_ago[valid]

    momentum = (price_1mo_ago / price_12mo_ago) - 1
    # Filter Datenartefakte: unrealistische Momentum-Werte
    momentum = momentum[(momentum > -0.95) & (momentum < 5.0)]
    return momentum.dropna()


def compute_breadth(prices: pd.DataFrame) -> float | None:
    """Anteil der Aktien aktuell über ihrer eigenen 200-Tage-MA (in %)."""
    if len(prices) < 200:
        return None
    ma200 = prices.rolling(window=200).mean().iloc[-1]
    current = prices.iloc[-1]
    mask = current.notna() & ma200.notna()
    if mask.sum() == 0:
        return None
    above = (current[mask] > ma200[mask]).sum()
    return float(above / mask.sum() * 100)


def determine_regime(above_ma200: bool, vix: float, breadth: float | None) -> str:
    """Ampel: GREEN / YELLOW / RED."""
    if not above_ma200 or vix > 35:
        return "RED"
    if vix > 25 or (breadth is not None and breadth < 50):
        return "YELLOW"
    return "GREEN"


def next_rebalancing_date(today: date) -> date:
    """Erster Werktag des nächsten Monats."""
    if today.month == 12:
        candidate = date(today.year + 1, 1, 1)
    else:
        candidate = date(today.year, today.month + 1, 1)
    while candidate.weekday() >= 5:  # Sat=5, Sun=6
        candidate += timedelta(days=1)
    return candidate


def main():
    print("📊 Lade S&P500 Constituents von Wikipedia...")
    constituents = fetch_sp500_constituents()
    tickers = constituents["ticker"].tolist()
    print(f"   {len(tickers)} Tickers")

    print("📈 Lade Stock-Kursdaten (14 Monate)...")
    stock_prices = fetch_price_history(tickers)
    # Jede Spalte auf letzten bekannten Kurs forward-fillen (Halbtage, Feiertage)
    stock_prices = stock_prices.ffill()
    print(f"   {len(stock_prices)} Handelstage, {stock_prices.shape[1]} Stocks")

    print("📊 Lade Benchmark-Daten (S&P500, VIX)...")
    benchmarks = fetch_price_history(["^GSPC", "^VIX"]).ffill()
    sp500_prices = benchmarks["^GSPC"].dropna()
    vix_prices = benchmarks["^VIX"].dropna()

    print("🏆 Berechne Momentum-Ranking (12-1)...")
    momentum = compute_momentum_12_1(stock_prices)
    momentum_sorted = momentum.sort_values(ascending=False)
    sector_map = constituents.set_index("ticker")["sector"].to_dict()
    ranking = [
        {
            "rank": rank,
            "ticker": ticker,
            "momentum_12_1": round(float(mom), 4),
            "sector": sector_map.get(ticker, "Unknown"),
        }
        for rank, (ticker, mom) in enumerate(momentum_sorted.items(), 1)
    ]
    top5 = [f"{r['ticker']} ({r['momentum_12_1']*100:+.1f}%)" for r in ranking[:5]]
    print(f"   Top 5: {', '.join(top5)}")

    print("🚦 Berechne Regime-Indikatoren...")
    sp500_current = float(sp500_prices.iloc[-1])
    sp500_ma200 = float(sp500_prices.rolling(window=200).mean().iloc[-1])
    above_ma200 = sp500_current > sp500_ma200
    vix_current = float(vix_prices.iloc[-1])
    breadth = compute_breadth(stock_prices)
    status = determine_regime(above_ma200, vix_current, breadth)
    breadth_str = f"{breadth:.1f}%" if breadth is not None else "N/A"
    print(
        f"   Status: {status}  |  S&P500 {sp500_current:.0f} (MA200 {sp500_ma200:.0f})  "
        f"|  VIX {vix_current:.1f}  |  Breadth {breadth_str}"
    )

    market_data = {
        "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "regime": {
            "sp500_price": round(sp500_current, 2),
            "sp500_ma200": round(sp500_ma200, 2),
            "above_ma200": bool(above_ma200),
            "vix": round(vix_current, 2),
            "breadth_pct": round(breadth, 1) if breadth is not None else None,
            "status": status,
        },
        "momentum_ranking": ranking,
        "next_rebalancing": str(next_rebalancing_date(date.today())),
        "sp500_constituents_count": len(tickers),
        "analyzed_count": len(ranking),
    }

    with open(MARKET_DATA_FILE, "w") as f:
        json.dump(market_data, f, indent=2)
    print(f"✅ {MARKET_DATA_FILE.name} aktualisiert ({len(ranking)} Aktien gerankt)")


if __name__ == "__main__":
    main()
