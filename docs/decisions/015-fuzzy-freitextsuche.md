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

## Nachtrag — 2026-07-02: Fuzzy entfernt, Umstieg auf Option B (FTS5)

Die 50k-Schwelle war zu optimistisch angesetzt: bereits ab 8000+ Bildern wurde das
O(Bibliothek)-Python-Scoring pro Request in `q_mode=text` spürbar (jede Anfrage lud
Tag-/Personen-/Caption-Text für alle Kandidaten der gefilterten Menge und scorte sie
einzeln mit `rapidfuzz`). Auf Entscheidung von Sascha wurde die Tippfehler-Toleranz
bewusst aufgegeben zugunsten einer echten DB-seitigen Lösung:

- **Tag-Name + Personen-Name:** weiterhin `ILIKE '%q%'` (unverändert, kein Performance-
  Problem — läuft über indizierte Joins).
- **Caption:** ersetzt durch SQLite FTS5 (`asset_caption_fts`, Migration 0028,
  `backend/photofant/db/text_index.py`) — Prefix-Matching statt Fuzzy (`"token"*` pro
  Whitespace-Token), mit ILIKE-Fallback, falls der Index auf einer Verbindung fehlt
  (z.B. Test-DBs ohne Migration).
- Entfernt: `rapidfuzz`-Dependency, `_TEXT_FUZZY_THRESHOLD`, `_text_score`, der komplette
  Kandidaten-Fetch-und-Score-Block in `list_assets`. `q_mode=text` läuft jetzt als reiner
  SQL-`OR`-Filter durch den normalen datums-sortierten Merge-Zweig statt durch eigenes
  Python-Ranking.
- Getippte Suchbegriffe mit echten Tippfehlern liefern jetzt keine Treffer mehr (bewusster
  Trade-off, kein Bug).
