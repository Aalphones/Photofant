# P31 — Duplikaterkennung: Schwelle fixen, Review paginieren

**Datum:** 2026-07-03
**Anlass:** Voll-Scan auf 8.440 Bildern meldete 55.654 „Duplikate" (CLIP-Default 85% ist eine
„gleiches Motiv"-Schwelle, keine „gleiche Datei"-Schwelle). Die Review-Seite lädt alle Paare
auf einmal → >111k DB-Queries pro Request, DOM-Overload, Tab-Crash.

## Überblick

| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | [Threshold-Semantik & Entkopplung](phase-1-threshold-semantik.md) | standard | complete |
| 2 | [Backend: Pagination + Query-Fix](phase-2-api-pagination.md) | standard | complete |
| 3 | [Frontend: Review-Dupes nachladen](phase-3-frontend-pagination.md) | standard | complete |

## Designentscheidungen

- **CLIP-Duplikat-Default: 0.15 → 0.03 Distanz (85% → 97% Ähnlichkeit).** Echte
  Beinahe-Duplikate liegen bei CLIP-Cosine ≥ 0.96; 0.85 matcht „gleiches Motiv/gleicher Stil".
- **Lightbox-Ähnlichkeit entkoppeln:** `GET /assets/{id}/similar` will bewusst *lose*
  Ähnlichkeit (Entdecken, nicht Deduplizieren) → eigener Settings-Key
  `similar_clip_threshold` (Default 0.15, bisheriges Verhalten bleibt).
- **pHash im Voll-Scan bleibt exakt (Distanz 0):** bewusst so — der Settings-Text verspricht
  „Kein Fehlalarm möglich". Verstanden und beibehalten (Chesterton's Fence).
- **Alt-Kandidaten-Cleanup über den Scan selbst:** Der Voll-Scan löscht zu Beginn alle
  *ungelösten* `dupe_candidate`-Zeilen (frischer Scan = frische Wahrheit; manuell gelöste
  bleiben). Kein separates Purge-Feature nötig.
- **Auto-Resolve (Papierkorb) als Bulk-UPDATE** vor dem Seiten-SELECT statt 2 COUNT-Queries
  pro Paar in Python (das war die 111k-Query-Quelle).

## Settings-Keys (Critical Rule 7)

| Key | Änderung | Default |
|---|---|---|
| `dupe_clip_threshold` | Default-Änderung + einmalige Migration (exakt 0.15 → 0.03) | 0.03 |
| `similar_clip_threshold` | **neu** — Lightbox „Ähnliche Bilder", übernimmt den alten Wert | 0.15 |

Seitengröße der Review-Liste: Frontend-Konstante `DUPE_PAGE_SIZE = 50` (reine UI-Portionierung,
kein Tuning-Charakter → kein Settings-Key).

## Kontrakt (Phase 2 → Phase 3)

```
GET /api/review/dupes?offset=<int, default 0>&limit=<int, default 50, max 200>
→ {
    "items": DupePairDto[],   // Felder unverändert wie heute
    "total": int              // ungelöste Paare nach Auto-Resolve
  }
```

Sortierung (stabil, actionable zuerst):
`ORDER BY (phash_distance IS NULL), phash_distance, clip_distance, id`
— exakte pHash-Treffer zuerst, dann CLIP nach aufsteigender Distanz.

**Breaking Change:** Response war bisher ein nacktes Array. Phase 2 stellt um,
Phase 3 zieht das Frontend nach — beide Phasen in derselben Umsetzungsrunde abschließen.

## Finale Abnahmekriterien

1. Voll-Scan mit Default-Settings auf dem 8.440er-Bestand liefert eine plausible
   Kandidatenzahl (Größenordnung ≤ wenige hundert, nicht zehntausende).
2. Voll-Scan ersetzt ungelöste Alt-Kandidaten vollständig (kein 55k-Restbestand).
3. `GET /api/review/dupes` antwortet auch bei 50k+ Restbestand in < 1s (eine Seite,
   konstante Query-Anzahl — kein N+1).
4. Review-Seite rendert initial max. `DUPE_PAGE_SIZE` Paar-Zeilen; „Mehr laden" hängt die
   nächste Seite an; Kopfzeile zeigt „X von Y".
5. Lightbox „Ähnliche Bilder" verhält sich wie vor der Änderung (loser Threshold greift).
6. Settings-Slider: Bereich 90–99%, Default 97%, Erklärtext entsprechend angepasst;
   Per-Person-Duplikat-Check respektiert 97% (kein stilles Clamping auf 95%).

## Smoke-Checkliste (User prüft nach Abschluss)

- [ ] Einstellungen → Verarbeitung: Slider zeigt 97%, Bereich 90–99, neuer Erklärtext
- [ ] Voll-Scan starten → Job läuft durch, Kandidatenzahl plausibel (nicht fünfstellig)
- [ ] Review → Duplikate öffnet sofort (kein Hänger, kein Crash), zeigt „50 von Y"
- [ ] „Mehr laden" klicken → nächste 50 erscheinen, Zähler aktualisiert
- [ ] Ein Paar auflösen (z.B. löschen) → Zeile verschwindet, Zähler sinkt um 1
- [ ] Lightbox eines beliebigen Bilds → „Ähnliche Bilder" liefert weiterhin Treffer
- [ ] Personen → Duplikat-Check eines Ordners → Ergebnisse konsistent mit 97%

## Bottom Sections (beim Archivieren füllen)

### Summary

CLIP-Duplikat-Schwelle von „gleiches Motiv" (85%) auf „echtes Beinahe-Duplikat" (97%)
korrigiert, Lightbox-Ähnlichkeit davon entkoppelt, und die Review-Seite paginiert statt
alle Paare + N+1-Queries auf einmal zu laden.

### Files touched

- Backend: `backend/photofant/api/review.py`, `backend/photofant/api/duplicates.py`,
  `backend/photofant/settings.py`, `backend/photofant/jobs/dupe_scan_job.py`
- Frontend: `frontend/src/app/store/review/*`, `frontend/src/app/services/review.service.ts`,
  `frontend/src/app/models/review.model.ts`, `frontend/src/app/models/index.ts`,
  `frontend/src/app/features/review/review-dupes/*`, `frontend/src/app/shell/nav-rail/nav-rail.ts`,
  `frontend/src/app/features/einstellungen/verarbeitung/*`
- Docs: `docs/routes.md`

### Commits

- `28a78bd` — Phase 1 (Threshold-Semantik & Entkopplung)
- `c193b56` — Phase 2 + 3 (Pagination + Query-Fix, zusammen wegen Breaking Change)

### Deviations from plan

- Phase 2+3 wurden wie geplant in einer Runde committet statt an der Phasengrenze zu
  clearen — der Plan verlangt das explizit wegen des Breaking Change.
- `nav-rail.ts` (Review-Badge) war nicht in der Checkliste, musste aber mitgezogen werden:
  bezog den Zähler bisher aus der (jetzt paginierten) Entity-Anzahl, das hätte den Badge auf
  `DUPE_PAGE_SIZE` gedeckelt. Siehe Report-Back Phase 3.

### Follow-ups

- Smoke-Checkliste unten ist noch nicht vom User durchlaufen (Voll-Scan auf dem 8.440er-Bestand
  manuell prüfen).
- Offset-Pagination + gleichzeitiges Auflösen von Paaren ist eine bekannte, nicht behobene
  Unschärfe: löst der User ein Paar mitten auf einer Seite auf, kann „Mehr laden" theoretisch
  ein Paar überspringen (Backend-Liste verschiebt sich um 1). Nicht Teil der Abnahmekriterien,
  aber notierenswert falls es auffällt.
