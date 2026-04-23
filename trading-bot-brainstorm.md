# Trading Bot – Brainstorming-Zusammenfassung

## Ausgangslage

- **Ziel:** Den S&P500 schlagen
- **Broker:** Scalable Capital (kein öffentliches API → manuelle Orderausführung)
- **Ansatz:** Bot gibt tägliche Empfehlungen, Ausführung erfolgt manuell, Bot trackt Portfolio intern

---

## Portfolio-Struktur

| Anteil | Inhalt |
|--------|--------|
| 90% | S&P500-ETF (Core, passiv, z.B. SXR8/VUSA) |
| 10% | Bot-verwaltetes Satellite-Portfolio (aktiv) |

**Rationale:** Klassisches Core-Satellite-Prinzip. Minimales Risiko, saubere Performancemessung. Nach 2 Jahren Trackrecord ggf. Gewichtung erhöhen. Das 10%-Budget kann konzentrierter und aggressiver agieren.

---

## Strategie

### Grundprinzip: Momentum-Investing
Kaufe Stärke, verkaufe Schwäche. Wissenschaftlich eines der robustesten Anomalien am Aktienmarkt – funktioniert, weil Menschen zu langsam auf neue Informationen reagieren.

### Drei recherchierte Kandidaten

**1. Top-25 Momentum (Einzelaktien)**
- Jeden Monat alle S&P500-Aktien nach 12-1-Monats-Performance ranken
- Top 25 kaufen, gleichgewichtet, monatlich rebalancen
- Historische CAGR: ~14,8% vs. ~8,9% S&P500
- Nachteil: höhere Volatilität, kein Drawdown-Schutz

**2. Dual Momentum GEM (Gary Antonacci)**
- Monatliche Entscheidung: S&P500 vs. Weltindex vs. T-Bills
- Sehr wenige Transaktionen (2–3 pro Jahr)
- Historische CAGR: ~17,4%, maximaler Drawdown nur ~22,7%
- Nachteil: reagiert zu langsam auf schnelle Marktveränderungen

**3. "Stocks on the Move" (Andreas Clenow)**
- Momentum via 90-Tage-Regressionssteigung + Marktregime-Filter (200-Tage-MA)
- Positionsgrößen via ATR berechnet
- Ausgefeilteste Variante, aber noch manuell handhabbar

### Favorisierter Ansatz
**Top-25 Momentum + Marktregime-Filter:**
- Kern: Monatliches Rebalancing auf Top-Momentum-Aktien (12-1 Monat)
- Schutz: Wenn S&P500 unter 200-Tage-MA → Cash-Position
- Für das 10%-Satellite: 5–8 konzentrierte Positionen realistisch

---

## Bot-Architektur

### Kernidee
Nicht nur stures Regelwerk, sondern **Claude als Reasoning-Layer** – der Bot erklärt seine Entscheidungen statt nur Regeln abzufeuern.

### Interface: Telegram
- Bot schreibt täglich proaktiv um 8 Uhr ein Briefing
- Jederzeit per Chat abfragbar: *"Wie läuft Nvidia?"*
- Ausführungsrückmeldung per Nachricht: *"Habe 15 Apple gekauft zu 187€"* → Bot updated Portfolio intern

### Beispiel Daily Briefing
```
📊 Daily Briefing – 23. April 2026

🟡 Marktregime: NEUTRAL
   S&P500 über 200MA ✓  |  VIX: 22 ⚠️  |  Breadth: 61%

💼 Satellite-Portfolio: +4,2% seit Start
   vs. S&P500: +2,8% → Alpha: +1,4%

⚡ Heute zu tun:
   VERKAUFEN: Intel (aus Top-25 rausgefallen)
   KAUFEN: Meta (neu in Top-25, Momentum #7)

💤 Keine Aktion: Nvidia, Microsoft, Apple, Broadcom

📌 Nächstes Rebalancing: in 8 Tagen
```

### Hosting: Hybrid-Ansatz (Variante B) ✨

Claude Pro erlaubt 5 Routine-Runs pro Tag. Um diese knappen Runs zu schonen, trennen wir **Analyse** (braucht Claude) und **State-Updates** (braucht nur Code):

```
┌─────────────────────────────────────────────┐
│  CLAUDE ROUTINE (verbraucht Runs)           │
│  - Daily Briefing morgens 8 Uhr   [1 Run]   │
│  - Analyse-Fragen per Telegram    [1-2 Run] │
│  - Puffer                         [2-3 Run] │
└─────────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────────┐
│  SIMPLES PYTHON-SCRIPT (ohne LLM)           │
│  - Portfolio-State im GitHub Repo updaten   │
│  - Trade-Rückmeldungen verarbeiten          │
│  - Marktdaten vorberechnen                  │
└─────────────────────────────────────────────┘
```

**Typischer Tagesablauf:**

1. **08:00** – Claude Routine (Schedule-Trigger) holt Portfolio aus GitHub, analysiert Markt, postet Briefing via Telegram
2. **Tagsüber** – Du führst Order bei Scalable aus
3. **Bestätigung** – Du schreibst in Telegram: `/trade Apple 15 187.50`
4. **Python-Script** (läuft via GitHub Action oder Cloudflare Worker, kein LLM-Call) updated Portfolio-JSON im Repo
5. **Nur bei echter Analyse-Frage** ("Wie läuft mein Portfolio?") → Routine wird getriggert

### Kosten
| Komponente | Kosten/Monat |
|------------|-------------|
| Claude Pro (bereits vorhanden) | 20$ (schon da) |
| Claude Code Routines | im Abo enthalten (5/Tag) |
| Telegram Bot | kostenlos |
| GitHub Repo + Actions | kostenlos |
| Cloudflare Worker (falls genutzt) | kostenlos |
| **Zusatzkosten** | **~0€** |

### Was der Bot täglich tut
Obwohl die Kern-Strategie monatlich ist, hat tägliches Monitoring echten Mehrwert:

- **Stop-Loss-Überwachung** – Positionen die abgestürzt sind, ohne auf Monatsende zu warten
- **Regime-Erkennung** – S&P500 bricht unter 200-Tage-MA → sofort reagieren
- **Crash-Warnung** – Ampelsystem (Grün/Gelb/Rot) basierend auf VIX, Breadth, Yield Curve
- **Portfolio-Drift** – Einzelpositionen werden durch Kursbewegungen zu groß/klein
- **Kontext** – Earnings-Termine, Makro-Events die Momentum-Signale beeinflussen

### Crash-Erkennung: Ampelsystem
| Signal | Indikator |
|--------|-----------|
| 200-Tage-MA | S&P500 darunter → Gelb/Rot |
| VIX | >25 Gelb, >35 Rot |
| Marktbreite | <50% Aktien über 200MA → Gelb |
| Yield Curve | Inversion → Gelb |

Bei Rot: keine neuen Käufe, Cash-Quote im Satellite erhöhen.

---

## Geklärte Fragen

- ✅ **Gesamtportfolio:** ~100.000€ → Satellite = ~10.000€
- ✅ **Core-Portfolio:** bereits vorhanden (90% S&P500-ETF)
- ✅ **Handelsinstrumente:** Einzelaktien aus dem S&P500
- ✅ **Hosting:** Claude Code Routines (Pro-Plan) + schlankes Python-Script
- ✅ **Interface:** Telegram
- ✅ **KI-Modell:** Claude (über vorhandenes Pro-Abo, keine API-Zusatzkosten)

## Offene Fragen

- [ ] Wie viele Positionen im Satellite: 5, 6, 7 oder 8?
- [ ] Momentum-Crash-Risiko: Wie aggressiv reagiert der Bot auf Regime-Wechsel?
- [ ] Python-Script für State-Updates: GitHub Actions oder Cloudflare Worker?
- [ ] Wie wird das Portfolio initial befüllt – alles auf einmal kaufen oder schrittweise?

---

## Wichtige Einschränkungen

- Historische Backtests sind öffentlich bekannt → Momentum-Premium heute schwächer als in alten Daten
- Kein API bei Scalable → manuelle Ausführung ist Bottleneck
- Der größte Alpha-Faktor beim Privatanleger ist oft **Verhalten im Crash**, nicht die Strategie

---

*Brainstorming-Stand: April 2026 – kein Finanzberatung, kein produktiver Code*
