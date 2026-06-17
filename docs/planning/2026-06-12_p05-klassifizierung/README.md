# P5 — Klassifizierung (Stage 2b)

> Status: geparkt · Quelle: [Konzept](../../Konzept-Photofant.md) §6, §12.5, §12.6 · Abhängigkeiten: P2, P4

Die ML-Pipeline: ONNX-Inferenz-Layer, WD14-Tags, Florence-2-Captions, CLIP/SigLIP-Embeddings, Heuristiken — integriert in den Import-Fluss und nachträglich auf den Bestand anwendbar. Enthält den laut Konzept (§19.6) **aufwändigsten ML-Teil** (Florence-2-Generierungs-Loop auf onnxruntime).

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Inferenz-Layer](phase-1-inferenz-layer.md) | heikel | complete |
| 2 | [WD14-Tagging](phase-2-wd14-tagging.md) | standard | pending |
| 3 | [Florence-2-Captioning](phase-3-florence-captioning.md) | heikel | pending |
| 4 | [CLIP-Embeddings & Vektor-Index](phase-4-clip-vektorindex.md) | heikel | pending |
| 5 | [Heuristiken & Pipeline-Integration](phase-5-heuristiken-pipeline.md) | standard | pending |
| 6 | [Captioner-Settings & Presets](phase-6-captioner-presets.md) | standard | pending |

## Kontrakt (Backend ↔ Frontend)

- **`AssetDto`-Erweiterung (additiv):** `tags: [{ id, name, kind }]`, `caption`, `captioner`, `tagger`, `quality_score`, `framing` (nullable bis P7).
- **`POST /api/classify/rerun`** — `{ asset_ids: number[] | "all", steps: ("tags"|"caption"|"embedding"|"heuristics")[], caption_preset_id?: number }` → Queue-Jobs (Ledger-Flags werden für die gewählten Steps zurückgesetzt).
- **`GET/POST/PATCH/DELETE /api/caption-presets`** — CRUD nach Konzept §5/§12.6; `config` ist modus-spezifisches JSON, validiert gegen den `caption_mode` des Modells.
- **Capabilities-Descriptor:** `model_registry.capabilities` (JSON) beschreibt deklarativ die Settings-Steuerelemente des Captioners (§12.6) — das Frontend rendert daraus, erfindet nichts.
- **Job-Kinds neu:** `tagging`, `captioning`, `embedding`, `heuristics`.
- **Interner Kontrakt Inferenz-Layer:** `Protocol`-Interfaces pro Rolle (`Tagger.tag(image) -> list[TagScore]`, `Captioner.caption(image, preset) -> str`, `Embedder.embed(image) -> ndarray`) — Pipeline kennt nur die Interfaces, nie konkrete Modelle (P9 hängt sich hier ein).

## Finale Akzeptanzkriterien

1. Import eines neuen Bildes mit aktivierten Core-Modellen erzeugt automatisch Tags, Caption und Embedding (Ledger-gesteuert, genau einmal).
2. Bestand nachklassifizierbar über Rerun (UI-Aktion auf Auswahl oder alles), Fortschritt im Job-Dock; Abbruch jederzeit, Wiederaufnahme setzt fort statt neu zu rechnen.
3. WD14-Tags erscheinen mit Konfidenz-Schwelle (konfigurierbar) als `kind = auto`; Detail-Panel zeigt Tags + Caption.
4. Florence-2 erzeugt mit Task-Token-Preset reproduzierbare Captions; Preset-Provenienz landet in `asset.caption_preset_id`.
5. Embeddings liegen im Vektor-Index; „mehr wie dieses" liefert auf einem Testbestand sichtbar ähnliche Bilder (Such-UI selbst kommt in P6 — hier reicht ein API-Test).
6. Modelle deaktiviert → Pipeline überspringt die Steps sauber (kein Crash, Ledger-Flags bleiben offen).

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Neues Bild importieren → nach Job-Ende: Tags + Caption im Detail-Panel
- [ ] Rerun „Caption" auf ein Bild mit anderem Preset → Caption ändert sich, Preset-Provenienz sichtbar
- [ ] Tagger deaktivieren, Bild importieren → kein Fehler, Tags fehlen, Hinweis sichtbar
- [ ] `POST /api/search/semantic` (per UI ab P6, bis dahin API) mit „red dress" → plausible Treffer

## Summary

## Files touched

## Commits

## Deviations from plan

## Follow-ups
