import json
import sys
import argparse
from datetime import date
from pathlib import Path

PORTFOLIO_FILE = Path(__file__).parent.parent / "portfolio.json"


def load_portfolio():
    with open(PORTFOLIO_FILE) as f:
        return json.load(f)


def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2)


def process_buy(portfolio, ticker, shares, price, note=""):
    ticker = ticker.upper()
    total_cost = round(shares * price, 2)

    if total_cost > portfolio["cash"]:
        print(f"ERROR: Nicht genug Cash. Verfügbar: {portfolio['cash']:.2f}€, Benötigt: {total_cost:.2f}€")
        sys.exit(1)

    existing = next((p for p in portfolio["positions"] if p["ticker"] == ticker), None)
    if existing:
        total_shares = existing["shares"] + shares
        avg_price = (existing["shares"] * existing["avg_buy_price"] + shares * price) / total_shares
        existing["shares"] = round(total_shares, 6)
        existing["avg_buy_price"] = round(avg_price, 4)
    else:
        portfolio["positions"].append({
            "ticker": ticker,
            "shares": shares,
            "avg_buy_price": price,
            "first_buy_date": str(date.today()),
            "momentum_rank_at_buy": None
        })

    portfolio["cash"] = round(portfolio["cash"] - total_cost, 2)
    portfolio["trades"].append({
        "date": str(date.today()),
        "action": "BUY",
        "ticker": ticker,
        "shares": shares,
        "price": price,
        "note": note
    })


def process_sell(portfolio, ticker, shares, price, note=""):
    ticker = ticker.upper()

    existing = next((p for p in portfolio["positions"] if p["ticker"] == ticker), None)
    if not existing:
        print(f"ERROR: Keine Position in {ticker}")
        sys.exit(1)

    if shares > existing["shares"]:
        print(f"ERROR: Nur {existing['shares']} Aktien von {ticker} im Portfolio")
        sys.exit(1)

    existing["shares"] = round(existing["shares"] - shares, 6)
    if existing["shares"] == 0:
        portfolio["positions"].remove(existing)

    portfolio["cash"] = round(portfolio["cash"] + shares * price, 2)
    portfolio["trades"].append({
        "date": str(date.today()),
        "action": "SELL",
        "ticker": ticker,
        "shares": shares,
        "price": price,
        "note": note
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["buy", "sell"])
    parser.add_argument("ticker")
    parser.add_argument("shares", type=float)
    parser.add_argument("price", type=float)
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    portfolio = load_portfolio()

    if args.action == "buy":
        process_buy(portfolio, args.ticker, args.shares, args.price, args.note)
    else:
        process_sell(portfolio, args.ticker, args.shares, args.price, args.note)

    save_portfolio(portfolio)

    pos = next((p for p in portfolio["positions"] if p["ticker"] == args.ticker.upper()), None)
    print(f"✓ {args.action.upper()} {args.shares} {args.ticker.upper()} @ {args.price}€")
    if pos:
        print(f"  Position: {pos['shares']} Stück @ Ø{pos['avg_buy_price']:.2f}€")
    print(f"  Cash verbleibend: {portfolio['cash']:.2f}€")
    print(f"  Positionen gesamt: {len(portfolio['positions'])}")


if __name__ == "__main__":
    main()
