# FINDINGS — P26 Recommendation Engine

> Format: `- [ ] → Phase N: <Erkenntnis>`. Mechanik: `mode-implementing`.

- [x] → Phase 2: Die API-Karte heißt `{ asset_id, thumbnail_url, score, reasons[] }` — die generische
  `related-rail/` erwartet `{ assetId, score, reasons }`. Mapping `asset_id`→`assetId` beim Andocken nötig;
  `thumbnail_url` ist fertig geliefert (`/api/assets/{id}/thumbnail`).
- [x] → Phase 2: `GET /api/recommendations?asset_id=` liefert `status: "ready"|"computing"|"disabled"`. Bei
  `computing` ist die Liste leer und der Job läuft schon — die UI muss über den bestehenden SSE-Job-Stream
  (`JobsService.streamJobs()`, `JobKind.recommendation`) auf Fertigstellung warten und dann neu laden
  (gleiches Warte-Muster wie P25 Phase 3 Korrektur-Flow). **`'recommendation'` fehlt noch in `JOB_KINDS`
  (`models/job.model.ts`)** — dort ergänzen (wie schon `knowledge_patch`).
- [x] → Phase 2: Eine Empfehlungs-Karte kann **mehrere** Signal-Häkchen tragen (same_person + same_role +
  same_film + clip gleichzeitig) — die Reason-Checkliste (Dok 050 §6) rendert alle vorhandenen `reasons`,
  nicht nur eins.
- [ ] → Phase 3: „Warum nicht?" ist backendseitig fertig
  (`GET /api/recommendations/{source}/{target}/why-not` → `{ score, threshold, recommended, reasons[], missing[] }`).
  Phase 3 ist damit v.a. UI (Popover) + „Warum?" auf die vorhandene Reason-Chain der Karte.
- [ ] → Phase 3: Reason-Chain-Struktur `{signal, detail, weight}` ist die geteilte Explainability-Payload
  (auch P25-Changelog). Der Plan-Kontrakt nennt `{ model?, capability?, reasons[], confidence, job }` —
  für P26 sind `model`/`capability` leer, `confidence` = `score`, `job` = die berechnende Job-Id (falls die
  UI sie braucht, aus dem Cache nachreichbar; Phase 1 liefert sie noch nicht mit der Karte).
