# Trading Bot – Projektstatus

*Stand: April 2026*

---

## Strategie

**Ziel:** S&P500 schlagen mit einem 10%-Satellite-Portfolio (~10.000€ von ~100.000€ Gesamtportfolio). 90% bleibt passiv in S&P500-ETF (Core).

**Gewählte Strategie:** Top-Momentum + Marktregime-Filter
- Jeden Monat alle S&P500-Aktien nach **12-1-Monats-Momentum** ranken (12 Monate Performance, letzten Monat ausgelassen)
- **5–6 konzentrierte Positionen** (~1.600–2.000€ pro Position)
- **Regime-Filter:** Wenn S&P500 unter 200-Tage-MA → Cash-Position, keine neuen Käufe
- Monatliches Rebalancing, tägliches Monitoring

**Wissenschaftliche Basis:** Jegadeesh & Titman (1993), von Fama & French bestätigt. Momentum ist eine der robustesten Anomalien am Aktienmarkt.

**Regime-Ampel:**

| Status | Bedingung |
|--------|-----------|
| 🟢 GREEN | S&P500 > 200MA, VIX < 25, Breadth > 50% |
| 🟡 YELLOW | VIX 25–35 oder Breadth 40–50% |
| 🔴 RED | S&P500 < 200MA oder VIX > 35 |

---

## Architektur

**Kernprinzip:** Strikte Trennung zwischen Datenbeschaffung (Python) und Reasoning (Claude).

```
GitHub Action (22:00) → market_data.json
Claude Routine (08:00) → liest beide JSONs → Telegram Briefing
User → /trade in Telegram → Cloudflare Worker → GitHub Action → portfolio.json
```

**Zwei-Komponenten-System:**
- **Python GitHub Action** (kein LLM): Berechnet Momentum-Rankings + Regime-Indikatoren, schreibt `market_data.json`
- **Claude Code Routine** (LLM): Liest `portfolio.json` + `market_data.json`, reasont über Aktionen, sendet Briefing via Telegram

**Warum nicht alles in Claude?** Claude kann keine 500 Aktienkurse zuverlässig per Web Search abrufen. Python + yfinance ist die richtige Schicht dafür.

---

## Infrastruktur (bereits gebaut)

| Komponente | Status | Details |
|-----------|--------|---------|
| `portfolio.json` | ✅ | GitHub Repo, Single Source of Truth |
| `scripts/update_portfolio.py` | ✅ | Buy/Sell verarbeiten, Validierung, Cash-Tracking |
| GitHub Action: Trade-Processing | ✅ | `repository_dispatch`-Trigger |
| Cloudflare Worker | ✅ | Telegram Webhook → GitHub API Bridge |
| Auto-Deploy Pipeline | ✅ | Push zu main → Worker deployed automatisch |
| `viewer.py` | ✅ | Live-Kurse via yfinance, zieht JSON von GitHub |
| Telegram Bot | ✅ | `/trade buy NVDA 8 187.50` funktioniert end-to-end |

**Trade-Flow (funktioniert):**
```
/trade buy NVDA 8 187.50 (Telegram)
→ Cloudflare Worker
→ GitHub repository_dispatch
→ Python Script
→ portfolio.json commit
```

---

## Datendateien

**`portfolio.json`** — vom User befüllt via `/trade`
```json
{
  "meta": { "satellite_budget": 10000, "currency": "EUR" },
  "cash": 10000.0,
  "positions": [{ "ticker": "NVDA", "shares": 8, "avg_buy_price": 187.50 }],
  "trades": [...],
  "performance_snapshots": []
}
```

**`market_data.json`** — von Python GitHub Action geschrieben (noch zu bauen)
```json
{
  "regime": { "status": "GREEN", "sp500_ma200": true, "vix": 18.5, "breadth_pct": 67 },
  "momentum_ranking": [{ "rank": 1, "ticker": "NVDA", "momentum_12_1": 0.847 }],
  "next_rebalancing": "2026-05-23"
}
```

---

## Kosten

| Komponente | Kosten |
|-----------|--------|
| Claude Pro | bereits vorhanden |
| Claude Code Routines | im Pro-Abo (5 Runs/Tag) |
| GitHub Repo + Actions | kostenlos |
| Cloudflare Worker | kostenlos (100k Req/Tag) |
| Telegram Bot | kostenlos |
| **Gesamt Zusatzkosten** | **0€** |

---

## Key Insights aus der Recherche

- **Kein GitHub-Repo kombiniert bewiesene Momentum-Strategie mit LLM-Reasoning** — das ist genuines Neuland
- **Kalshi AI Bot** (367 Stars): Confidence-Threshold-Prinzip — Claude gibt kein Signal wenn Signale widersprüchlich sind. Wollen wir einbauen
- **Historische Backtests sind öffentlich bekannt** → Momentum-Premium heute schwächer als in alten Daten
- **Größter Alpha-Faktor beim Privatanleger:** Verhalten im Crash, nicht die Strategie

---

## Offene Baustellen (Reihenfolge)

- [ ] `scripts/update_market_data.py` — Momentum-Screener + Regime-Berechnung
- [ ] `.github/workflows/update_market_data.yml` — Nightly GitHub Action (22:00)
- [ ] `CLAUDE.md` — Instruktionsset für die Claude Routine
- [ ] Claude Code Routine — Schedule einrichten und testen
