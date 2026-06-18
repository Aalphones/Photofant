# Einstellungen Thumbnail-Qualität · Phase 2 — Frontend: Config-Store + Einstellungen-Verdrahtung

> Rating: **standard** · Status: pending · Voraussetzung: Phase 1 abgeschlossen

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt, Konvention
- `frontend/src/app/store/models/` — bestehender Config-Slice (`loadConfig`, `loadConfigSuccess`, `modelsDir`)
- `frontend/src/app/features/einstellungen/einstellungen.ts` — aktueller Stand Darstellung-Tab
- `frontend/src/app/services/settings.service.ts` — localStorage-Ansatz (wird für `density` durch Backend-Store abgelöst)

## Akzeptanzkriterien

- App-Start: `thumbnail_quality` wird aus `GET /api/config` geladen und im Store gehalten.
- Einstellungen-UI zeigt den aktuell im Backend konfigurierten Wert (kein localStorage-Stale).
- Änderung in der UI → `PATCH /api/config { thumbnail_quality }` → Store-Update → Einstellung bleibt nach Browser-Reload erhalten.
- `density` im Filters-Store wird beim App-Start aus `thumbnail_quality` initialisiert (einmalige Übernahme, überschreibbar per Gallery-Toolbar).
- 🟡 `SettingsService.setShowMeta/setReducedMotion/setLocale/setDateFormat` bleiben in localStorage (keine Backend-Relevanz).

## Checkliste

- [ ] **`models.actions.ts`**: neue Action-Gruppe oder neue Events — `loadThumbnailQualitySuccess({ quality })`, `updateThumbnailQuality({ quality })`, `updateThumbnailQualitySuccess({ quality })`, `updateThumbnailQualityFailure({ error })`
- [ ] **`models.reducer.ts`**: `thumbnailQuality: 'sm' | 'md' | 'lg' | null` zu `ModelsState` hinzufügen; `loadConfigSuccess` extrahiert `thumbnail_quality` aus Response; neue `on()`-Handler für die Quality-Actions
- [ ] **`models.effects.ts`**: `loadConfigSuccess` dispatcht nach erfolgreichem Laden zusätzlich `filtersActions.setDensity({ density: quality })` (Initialisierung des Session-Density); neuer Effect für `updateThumbnailQuality` → PATCH `/api/config` → Success/Failure
- [ ] **`models.selectors.ts`**: `selectThumbnailQuality` exportieren
- [ ] **`models/index.ts`** (Store-Barrel): neue Exports ergänzen
- [ ] **`model.service.ts`** (oder separater `config.service.ts`): Methode `updateThumbnailQuality(quality: string)` → `PATCH /api/config`
- [ ] **`einstellungen.ts`**: "Thumbnail-Größe"-Select liest aus `store.selectSignal(modelsSelectors.selectThumbnailQuality)` statt `filtersSelectors.density`; `(change)` dispatcht `modelsActions.updateThumbnailQuality({ quality })`; `SettingsService`-Density-Logik entfernen (war temporär)
- [ ] **`einstellungen.ts`**: Info-Hinweis wenn `thumbnailQuality` auf `lg` gesetzt wird: `"Für 1024-px-Thumbnails ist ein Rebuild empfohlen (Phase 3)"` — `Note`-Stil, kein Blocker
- [ ] Doc-Update: keine (interne Store-Änderung, routes.md schon in Phase 1 erledigt)

## Report-Back
