# ADR-015 — Fuzzy-Freitextsuche über rapidfuzz statt FTS5

**Status:** Akzeptiert · 2026-07-02
**Querverweise:** P28 (Suche — Redesign & Bugfixes), Phase 2.

## Kontext

Die Suchleiste soll beim Tippen breit über Tag-Name, Caption und Personen-Name filtern,
auch bei Tippfehlern (fuzzy) — exakte/semantische Filterung passiert erst bei expliziter
Dropdown-Auswahl (Person/Tag/Semantik).

## Optionen

| Option | Beschreibung |
|---|---|
| **A — rapidfuzz über In-Memory-Kandidaten** | Backend holt Kandidaten (Tag-Namen, Personen-Namen, Captions) aus der bereits gefilterten Asset-Menge, scored mit `rapidfuzz`. Keine Migration, keine neue SQLite-Extension. |
| B — SQLite FTS5 mit Trigram-Tokenizer | Echtes DB-seitiges Fuzzy/Prefix-Matching, skaliert besser, aber neue virtuelle Tabelle + Migration + Sync-Pflicht bei jeder Caption/Tag/Personen-Name-Änderung. |

## Entscheidung

**Option A.** Kandidaten werden bewusst aus der bereits gefilterten Query gezogen (nicht
der Gesamtbibliothek) — dev-DB hat aktuell 53 Assets, weit unter der 50k-Schwelle, ab der
Skalierung überhaupt relevant würde. Score-Schwelle `fuzz.WRatio >= 60`
(`backend/photofant/api/assets.py`, `_TEXT_FUZZY_THRESHOLD`).

## Konsequenzen

- Bei sehr großen Bibliotheken (> ~50k Assets in der aktuell gefilterten Menge) wird das
  Scoring pro Request spürbar — dokumentierter Ausweg ist Option B (FTS5), hier nicht
  umgesetzt, kein Auftrag dazu.
- `q_mode=semantic` bleibt für explizite CLIP-Suche unverändert; `q_mode=text` ersetzt
  `tags`/`caption` nicht, ergänzt sie als neuer Default-Modus der Suchleiste.
