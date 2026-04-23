import requests
import yfinance as yf
from datetime import datetime

PORTFOLIO_URL = "https://raw.githubusercontent.com/maximilianrichter89-gif/tradebot/main/portfolio.json"


def fetch_portfolio():
    r = requests.get(PORTFOLIO_URL)
    r.raise_for_status()
    return r.json()


def fetch_prices(tickers):
    prices = {}
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            prices[ticker] = float(hist["Close"].iloc[-1]) if not hist.empty else None
        except Exception:
            prices[ticker] = None
    return prices


def pnl_indicator(pct):
    if pct is None:
        return ""
    if pct >= 5:
        return "▲▲"
    if pct > 0:
        return "▲"
    if pct <= -5:
        return "▼▼"
    return "▼"


def fmt(value, suffix="€", decimals=2, sign=False):
    if value is None:
        return "N/A"
    fmt_str = f"{'+' if sign else ''}.{decimals}f"
    return f"{value:{fmt_str}}{suffix}"


def display(portfolio, prices):
    cash = portfolio["cash"]
    positions = portfolio["positions"]
    budget = portfolio["meta"]["satellite_budget"]
    currency = portfolio["meta"]["currency"]

    rows = []
    for pos in positions:
        ticker = pos["ticker"]
        shares = pos["shares"]
        avg_price = pos["avg_buy_price"]
        current_price = prices.get(ticker)

        cost_basis = shares * avg_price
        current_value = shares * current_price if current_price else None
        pnl = current_value - cost_basis if current_value else None
        pnl_pct = (pnl / cost_basis * 100) if pnl is not None else None
        weight = (current_value / budget * 100) if current_value else None

        rows.append({
            "ticker": ticker,
            "shares": shares,
            "avg_price": avg_price,
            "current_price": current_price,
            "cost_basis": cost_basis,
            "current_value": current_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "weight": weight,
        })

    invested_value = sum(r["current_value"] or r["cost_basis"] for r in rows)
    total_value = cash + invested_value
    total_pnl = total_value - budget
    total_pnl_pct = total_pnl / budget * 100

    W = 68
    print()
    print("=" * W)
    print(f"  SATELLITE PORTFOLIO  |  {datetime.now().strftime('%d.%m.%Y %H:%M')}  |  {currency}")
    print("=" * W)

    if not rows:
        print("\n  Keine offenen Positionen.\n")
    else:
        header = f"  {'TICKER':<8} {'STÜCK':>6} {'Ø KAUF':>8} {'KURS':>9} {'WERT':>10} {'P&L':>10} {'%':>7}  {'WEIGHT':>6}"
        print()
        print(header)
        print(f"  {'-' * (W - 2)}")
        for r in rows:
            ind = pnl_indicator(r["pnl_pct"])
            print(
                f"  {r['ticker']:<8}"
                f" {r['shares']:>6.1f}"
                f" {fmt(r['avg_price']):>8}"
                f" {fmt(r['current_price']):>9}"
                f" {fmt(r['current_value']):>10}"
                f" {fmt(r['pnl'], sign=True):>10}"
                f" {fmt(r['pnl_pct'], suffix='%', sign=True):>7}"
                f"  {ind:<2} {fmt(r['weight'], suffix='%', decimals=1):>5}"
            )

    print()
    print(f"  {'─' * (W - 2)}")
    print(f"  {'Cash':<30} {fmt(cash):>10}")
    print(f"  {'Portfoliowert':<30} {fmt(total_value):>10}")
    print(f"  {'Performance seit Start':<30} {fmt(total_pnl, sign=True):>10}  ({fmt(total_pnl_pct, suffix='%', decimals=1, sign=True)})")
    print("=" * W)
    print()

    note = "  Kurse in USD (S&P500 Aktien). Ø Kauf-Preise in EUR (Scalable)."
    print(note)
    print()


def main():
    print("Lade Portfolio von GitHub...")
    portfolio = fetch_portfolio()

    tickers = [p["ticker"] for p in portfolio["positions"]]
    if tickers:
        print(f"Hole Kurse für: {', '.join(tickers)}")
    prices = fetch_prices(tickers)

    display(portfolio, prices)


if __name__ == "__main__":
    main()
