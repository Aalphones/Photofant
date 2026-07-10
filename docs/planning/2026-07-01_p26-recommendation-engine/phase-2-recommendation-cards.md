# Phase 2 — Empfehlungs-Karten-UI (unter Lore Panel)

**Komplexität:** standard · **Status:** complete

## Kontext
- README → Design-Lage + Screen-Eigentümer (P15/P25) · Konzept Dok 050 §6/§13
- Phase 1: `GET /api/recommendations` · **P25:** Lore-Panel-Struktur (Andockort)
- Bestand: `store/gallery/`, Grid-/Cell-Muster `features/galerie/`, Tokens

## AK (UI-Struktur = Kontrakt)
- [x] Unter dem Lore Panel (P25) ein Empfehlungs-Bereich mit Karten: **Vorschaubild · Score · Reason-Checkliste** (✓-Liste der Signale, Dok 050 §6).
- [x] Karten-Klick öffnet das empfohlene Bild (bestehende Navigation).
- [x] „Wird berechnet"-Status (leerer Cache) dezent, lädt nach Job-Ende nach (SSE/Poll wie andere Jobs).
- [x] Keine Empfehlungen → Bereich entfällt.
- [x] Dockt unter P25s Panel an, baut dessen Struktur nicht um.

## Umsetzung
- [x] Reco-State: **komponentenlokal in `lightbox.ts`** (Signal + `toSignal(combineLatest(...))`, gleiche Pipeline wie `detail`/`lineage`/`relatedRail`) — **nicht** `store/gallery/`/`store/knowledge/`. Begründung: weder Lore-Panel (P25) noch Related-Rail (P36) legen ihre Pro-Asset-Daten in NgRx ab; ein neues Store-Slice wäre hier der Ausreißer, nicht die konsistente Wahl.
- [x] `services/recommendation.service.ts` (`getRecommendations`)
- [x] Keine neue Komponente — die generische `related-rail/` (P36) wird mit befüllten `reasons` wiederverwendet (wie in ihrem eigenen Kopf-Kommentar vorgesehen); Reason-Checkliste = `recommendationReasonLabel()`-Mapping auf `{label}` + CSS-Anpassung (kein Bullet-Punkt mehr, nur „✓").
- [x] „Wird berechnet"-Zustand + Nachladen: `related-rail`'s `loading`-State (neues `loadingMessage`-Input) + ein `effect()` in `lightbox.ts`, das auf einen `recommendation`-Job im globalen Job-Store wartet und dann den bestehenden `reloadTrigger` bumpt.
- [x] Doc: `docs/code-map.md`, `docs/design-reconciliation.md` (freihändig markiert)

## Deviations (Phase 2)
- **Kein Job-Id-Filter beim Warten auf den Job:** Der Korrektur-Flow (P25 Phase 3) filtert `JobsService.streamJobs()` auf eine bekannte `job_id`. Der Empfehlungs-Endpoint liefert bei Cache-Miss aber **keine** Job-Id (`status:"computing"`, Job läuft bereits serverseitig) — siehe FINDINGS. Umgesetzt über den globalen `jobsSelectors.allJobs`-Store (wie beim Upscale-Flow): sobald irgendein `kind:"recommendation"`-Job auf `done`/`error` steht, während wir noch auf „computing" warten, wird neu geladen. Selbstkorrigierend, falls es der falsche Job war (nächster Reload liefert wieder „computing").
- **`related-rail` minimal erweitert statt neuer Komponente:** `loadingMessage`-Input (Default „Suche läuft…", P26 nutzt „Wird berechnet …") + CSS (`list-style: none` auf den Reasons, da die Labels jetzt selbst ein „✓" tragen). Kein Verhaltensbruch für P36.
- **`thumbnail_url` aus dem Backend ungenutzt:** `related-rail` baut die Thumbnail-URL immer selbst über `AssetService.thumbnailUrl(assetId, 256)` (gleich für P36 und P26) — das vom Backend mitgelieferte `thumbnail_url`-Feld wird nicht gebraucht, kein Mapping nötig.
