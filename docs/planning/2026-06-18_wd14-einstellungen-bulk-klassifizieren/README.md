# WD14-Einstellungen + Bulk-Klassifizieren

> Status: pending

## Übersicht

| # | Phase | Rating | Status |
|---|---|---|---|
| 1 | [Backend WD14-Einstellungen](phase-1-backend-einstellungen.md) | mechanisch | pending |
| 2 | [Frontend Verarbeitungs-Einstellungen](phase-2-frontend-verarbeitung.md) | standard | pending |
| 3 | [Gallery Bulk-Klassifizieren](phase-3-bulk-klassifizieren.md) | standard | pending |

## Kontext & Abgrenzung

Dieses Feature ergänzt `2026-06-18_einstellungen-fehlende-sektionen`:
- **Phase 2 dieses Plans ist ein Superset von Phase 1 der einstellungen-fehlende-sektionen-Frontend-Seite** — wer Phase 2 umsetzt, kann in jenem Plan Phase 1 als erledigt markieren. Backend-Seite dort (import_job.py Guards, heuristics blur_threshold) ist **bereits implementiert**.
- Phasen 2–4 von `einstellungen-fehlende-sektionen` (Bibliothek, Shortcuts, Info) sind orthogonal und können danach folgen.

## API-Kontrakt

### Bestehend, unverändert
- `GET /api/config` → `{ data: { models_dir, auto_tag, auto_caption, auto_embed, blur_threshold, ... } }`
- `PATCH /api/config` → `{ data: { <partial> } }` → Updated config zurück
- `POST /api/classify/rerun` → `{ asset_ids: number[] | "all", steps: ClassifyStep[], caption_preset_id?: number }` → `{ job_id: string }`

### Neu (nach Phase 1)
`GET /api/config` liefert zwei zusätzliche Felder:
```
data.min_probability: float   // Default 0.5 — ersetzt tagging_threshold
data.max_tags: int            // Default 30
```

`PATCH /api/config` akzeptiert dieselben Keys zum Patchen.

### Frontend-Store-Kontrakt (nach Phase 2)
`modelsActions.loadConfigSuccess` bekommt ein neues Pflichtprop:
```ts
processingConfig: ProcessingConfig
```
Reducer speichert es in `state.processingConfig`. Selector: `modelsSelectors.selectProcessingConfig`.

`ProcessingConfig`:
```ts
{
  autoTag: boolean;
  autoCaption: boolean;
  autoEmbed: boolean;
  minProbability: number;
  maxTags: number;
  blurThreshold: number;
}
```

## Finale Akzeptanzkriterien

1. WD14 gibt maximal `max_tags` Tags aus, sortiert nach Konfidenz absteigend, nur solche ≥ `min_probability`. Beide Werte kommen aus `settings.json` (Defaults: 0.5 / 30).
2. Einstellungen-Seite zeigt Sektion „Verarbeitung": auto_tag/auto_caption/auto_embed Toggles + min_probability + max_tags + blur_threshold — Änderungen persistieren sofort via PATCH.
3. Galerie: mehrere Bilder markierbar → Bulk-Bar zeigt „Klassifizieren" → RerunDialog → Job in Leiste.
4. Lightbox „Klassifizieren" ist **bereits fertig** — kein Code-Änderungsbedarf.

## Smoke-Checkliste (User prüft am Ende)

- [ ] Bild neu taggen → ≤ 30 Tags, alle ≥ 0.5 Konfidenz, absteigend sortiert
- [ ] `min_probability` auf 0.8 setzen → Rerun liefert spürbar weniger Tags
- [ ] `max_tags` auf 5 setzen → Rerun liefert genau 5 Tags
- [ ] Einstellungen → auto_tag Toggle deaktivieren → Import-Job enqueued keinen Tagging-Job
- [ ] Galerie: 3 Bilder markieren → Bulk-Bar → Klassifizieren → Dialog → Abschicken → Job in Leiste sichtbar

---

## Summary
<!-- beim Archivieren füllen -->

## Files Touched
<!-- beim Archivieren füllen -->

## Commits
<!-- beim Archivieren füllen -->

## Deviations from Plan
<!-- beim Archivieren füllen -->

## Follow-ups
<!-- beim Archivieren füllen -->
