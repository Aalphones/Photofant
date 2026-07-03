# ADR-010 — Bildklassifizierung: CLIP+WD14-Fusion über gespeicherte Signale

**Status:** Angenommen
**Datum:** 2026-07-03
**Betrifft:** Plan `2026-06-30_p18-bildklassifizierung`

---

## Kontext

Bilder sollen gegen frei definierbare Kategorien (Medium, Stil, Franchise, Charakter …)
klassifiziert werden. Zwei Signale liegen für jedes Bild bereits in der DB: das CLIP-Bild-
Embedding (`asset.clip_embedding`, ADR-001) und die WD14-Tag-Scores (`asset_tag.score`).
Ein dritter, unabhängiger Klassifikator (eigenes Modell, eigener Inferenz-Lauf über den
gesamten Bestand) hätte einen teuren Retro-Lauf über tausende Bilder erzwungen und ein
weiteres ONNX-Modell in Verwaltung/VRAM-Budget aufgenommen.

## Entscheidung

Klassifizierung fusioniert die zwei vorhandenen Signale, statt ein drittes Modell
einzuführen:

- **CLIP:** Label-Texte werden zu Prompts (`clip_prompts` oder Fallback-Template) und
  per Cosine gegen das gespeicherte Bild-Embedding bewertet, Softmax je Kategorie.
- **WD14:** gespeicherte Tag-Scores füttern Labels, die per `wd14_tags` darauf zeigen
  (Max-Score, falls mehrere Tags konfiguriert sind).
- **Fusion:** gewichteter Schnitt beider Signale (`classification.clip_weight`/`wd14_weight`);
  fehlt eines (z.B. Tag unter Tagging-Schwelle), fällt die Fusion still auf das andere zurück.
- **Modus pro Kategorie:** `single` wählt die beste Klasse über `min_confidence`
  (Kategorie-Override oder globaler Default), `multi` alle Klassen über
  `multi_min_confidence`.
- **Ledger-Reuse:** kein neues Feld — `ProcessingLedger.classified` (seit Migration 0009
  ungenutzt) markiert, ob die Kategorien für den Content-Hash berechnet sind; der Rerun-Step
  `categories` setzt es zurück.

## Konsequenzen

- Der Retro-Lauf über den Bestand ist billig: reine DB-Reads + Fusionsmathematik, kein
  Bild-I/O, kein Modell-Neulauf.
- Klassifizierung hängt von Tagging + Embedding ab — läuft automatisch erst, wenn beide
  fertig sind (`classification_pipeline.py`), sonst fehlt ihr die Datengrundlage.
- Kategorien/Labels sind rein datengetrieben (keine Modell-Retrain nötig) — neue Klassen
  anlegen heißt nur neue DB-Zeilen + CLIP-Prompts/WD14-Tags zuordnen.
- Qualität ist an die Qualität der zwei Basissignale gekoppelt: ein Label ohne guten
  CLIP-Prompt und ohne passenden WD14-Tag bleibt schwach erkennbar.
