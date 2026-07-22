# Phase 3 — Frontend-Model + Service

**Rating:** mechanisch (reine Typ-/Methoden-Ergänzung, kein neuer Zustand, kein Store-Eingriff).

**Voraussetzung:** Phase 2 abgeschlossen (Backend liefert die neuen Felder/den neuen Endpoint).

## Kontext (lesen vor dem Bauen)

- `frontend/src/app/models/person.model.ts` — `PersonFace`-Interface (Zeile 16-22), snake_case
  Feldnamen 1:1 wie das Backend (dieses Projekt konvertiert nicht zu camelCase).
- `frontend/src/app/services/person.service.ts` — `deleteFace(faceId)` (Zeile ~116) als
  Vorbild für den neuen `bulkDeleteFaces`-Aufruf.

## Aufgabe

### 1. `frontend/src/app/models/person.model.ts`

`PersonFace` um die fünf neuen Felder erweitern:

```ts
export interface PersonFace {
  id: number;
  asset_id: number | null;
  crop_url: string;
  score: number | null;
  age: number | null;
  resolution: number | null;
  is_upscaled: boolean;
  identity_distance: number | null;
  cleanup_score: number;
  cleanup_reasons: string[];
}
```

Neues Interface für die Bulk-Delete-Antwort, direkt darunter oder bei den anderen
Result-Interfaces (z.B. neben `FaceImportResult`):

```ts
export interface BulkDeleteFacesResult {
  deleted: number;
  asset_ids: number[];
}
```

### 2. `frontend/src/app/services/person.service.ts`

Neue Methode, direkt neben `deleteFace`:

```ts
bulkDeleteFaces(faceIds: number[]): Observable<BulkDeleteFacesResult> {
  return this.http.post<BulkDeleteFacesResult>('/api/faces/bulk-delete', { face_ids: faceIds });
}
```

`BulkDeleteFacesResult` zum Type-Import am Dateikopf ergänzen (gleiche Import-Zeile wie die
anderen Modelle aus `@photofant/models`).

## Akzeptanzkriterien

- `tsc` kompiliert ohne neue Fehler.
- `getPersonFaces()` gibt (nach Phase 2) Objekte mit den neuen Feldern zurück — kein Cast/Mapping
  nötig, da das Backend bereits das exakte JSON-Shape liefert.

## Checkliste

- [x] `PersonFace`-Interface erweitert, `BulkDeleteFacesResult` neu
- [x] `PersonService.bulkDeleteFaces()` neu
- [x] `tsc --noEmit` (oder Projekt-Äquivalent) sauber

## Report-Back

Beide Interfaces + Service-Methode 1:1 nach Plan-Vorgabe ergänzt (`person.model.ts`,
`person.service.ts`), `BulkDeleteFacesResult` zusätzlich im Barrel-Export
(`models/index.ts`) ergänzt — das stand nicht explizit im Plan, war aber nötig, sonst
importiert `person.service.ts` einen Typ, der über `@photofant/models` nicht sichtbar
ist. `npx tsc --noEmit` läuft grün, keine neuen Fehler. Kein Cast/Mapping in
`getPersonFaces()` nötig — Backend liefert das Shape 1:1 (Phase 2 bereits abgeschlossen).
