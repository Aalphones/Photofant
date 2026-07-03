# Glossar — Photofant

> Gemeinsames Vokabular: ein Begriff = eine Bedeutung. EN-Terms wo im Code/UI verwendet,
> Erklärung auf Deutsch. Bei neuen Fachbegriffen hier ergänzen statt eine Nebenbedeutung
> einzuführen.

## Klassifizierung (P18)

**Kategorie** — ein frei definierbares Klassifizierungs-Merkmal für Bilder (z.B. „Medium",
„Stil", „Franchise"). Hat einen Modus (`single`/`multi`) und enthält mehrere Labels.
DB-Tabelle `classification_category`.

**Label** — eine wählbare Ausprägung innerhalb einer Kategorie (z.B. „Anime" in der
Kategorie „Stil"). Trägt optionale CLIP-Prompts und WD14-Tag-Namen, die es speisen.
DB-Tabelle `classification_label`.

**Klassifizierung** — das Ergebnis, das einem Bild ein oder mehrere Labels zuordnet
(je nach Kategorie-Modus `single` = genau eine Hauptklasse, `multi` = mehrere Klassen),
mit Confidence-Score. DB-Tabelle `asset_classification`. Nicht zu verwechseln mit „Tagging"
(WD14-Einzeltags, `asset_tag`) oder „Caption" (Freitext-Bildbeschreibung) — Klassifizierung
ist die dritte, kategorisierende Ebene obendrauf.

**Fusion** — die Zusammenführung von CLIP-Signal (Cosine-Ähnlichkeit Bild↔Label-Prompt) und
WD14-Signal (gespeicherter Tag-Score) zu einem gewichteten Gesamt-Score je Label
(`classification/engine.py`). Fehlt eines der beiden Signale, fällt die Fusion still auf
das verbleibende zurück. Siehe [ADR-010](decisions/010-bildklassifizierung-engine.md).
