# Trading Bot – Architektur Daily Briefing

## Kernproblem

Claude Code Routines können keine 500 Aktienkurse per Web Search zuverlässig abrufen.
Lösung: Klare Trennung zwischen **Datenbeschaffung** (Python) und **Reasoning** (Claude).

---

## Zwei-Komponenten-System

```
┌─────────────────────────────────────────┐
│  GITHUB ACTION  (täglich 22:00 Uhr)     │
│  Python + yfinance, kein LLM            │
│                                         │
│  1. S&P500-Kurse der letzten 13 Monate  │
│  2. Momentum-Ranking berechnen (12-1)   │
│  3. Regime-Indikatoren berechnen        │
│  4. Speichert → market_data.json        │
└──────────────────┬──────────────────────┘
                   │ GitHub Raw URL
┌──────────────────▼──────────────────────┐
│  CLAUDE CODE ROUTINE  (täglich 08:00)   │
│  Liest market_data.json + portfolio.json│
│                                         │
│  1. Vergleicht Positionen vs. Ranking   │
│  2. Prüft Regime-Status                 │
│  3. Entscheidet + begründet Aktionen    │
│  4. Sendet Briefing via Telegram        │
└─────────────────────────────────────────┘
```

---

## Datendateien

### `portfolio.json` (bereits vorhanden)
Wird vom User via `/trade` befüllt. Enthält Positionen, Cash, Trade-History.

### `market_data.json` (neu, von GitHub Action geschrieben)
```json
{
  "updated_at": "2026-04-23T22:00:00",
  "regime": {
    "sp500_price": 5200.0,
    "sp500_ma200": 4980.0,
    "above_ma200": true,
    "vix": 18.5,
    "breadth_pct": 67.3,
    "status": "GREEN"
  },
  "momentum_ranking": [
    { "rank": 1, "ticker": "NVDA", "momentum_12_1": 0.847, "sector": "Technology" },
    { "rank": 2, "ticker": "META", "momentum_12_1": 0.721, "sector": "Communication" }
  ],
  "next_rebalancing": "2026-05-23",
  "sp500_constituents_count": 503
}
```

### `CLAUDE.md` (Instruktionsset für die Routine)
Enthält: Strategie-Regeln, Briefing-Format, Telegram-Credentials, Entscheidungslogik.

---

## Regime-Ampel

| Status | Bedingungen |
|--------|-------------|
| 🟢 GREEN | S&P500 > 200MA **und** VIX < 25 **und** Breadth > 50% |
| 🟡 YELLOW | S&P500 > 200MA **aber** VIX 25–35 **oder** Breadth 40–50% |
| 🔴 RED | S&P500 < 200MA **oder** VIX > 35 |

Bei RED: keine neuen Käufe, bestehende Positionen prüfen.

---

## Momentum-Berechnung

```
Momentum = (Preis heute / Preis vor 12 Monaten) - 1
           abzüglich letztem Monat (Skip-Month)

→ Ranking aller S&P500-Aktien nach diesem Wert
→ Top 5–6 = Kandidaten für das Satellite-Portfolio
```

---

## Claude Code Routine – Entscheidungslogik

```
Gegeben: portfolio.json + market_data.json

1. Regime CHECK
   → RED: Briefing mit Warnung, keine Kauf-Empfehlungen

2. Positionen CHECK
   → Welche aktuellen Positionen sind NICHT mehr in Top-25?
   → → VERKAUF-Kandidaten

3. Top-5/6 CHECK
   → Welche Top-Aktien sind noch NICHT im Portfolio?
   → → KAUF-Kandidaten

4. Stop-Loss CHECK
   → Position > 15% unter Einstandspreis?
   → → Sofort VERKAUF-Empfehlung (unabhängig vom Rebalancing)

5. Briefing generieren + via Telegram senden
```

---

## Zeitplan

| Zeit | Komponente | Aktion |
|------|-----------|--------|
| 22:00 | GitHub Action | Marktdaten + Ranking berechnen, market_data.json pushen |
| 08:00 | Claude Routine | market_data.json + portfolio.json lesen, Briefing senden |
| Jederzeit | Telegram /trade | portfolio.json updaten |

---

## Nächste Schritte (Reihenfolge)

1. **`scripts/update_market_data.py`** – Momentum-Screener + Regime-Berechnung
2. **`.github/workflows/update_market_data.yml`** – Nightly GitHub Action
3. **`CLAUDE.md`** – Instruktionsset für die Claude Routine
4. **Claude Code Routine** – Schedule einrichten, testen
