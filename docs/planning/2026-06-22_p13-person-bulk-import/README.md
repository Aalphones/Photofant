# P13 — Person-Bulk-Import

**Status:** pending

Neuen Personen Bilder per Bulk zuordnen, ohne den Galerie-Import-Dialog manuell
zu bedienen. Drei Wege: (1) Neue Person anlegen + Galerie-Filter vorbelegen,
(2) Upload in der Galerie bei aktivem Personen-Filter landet direkt im
Personen-Ordner, (3) Ausgewählte Bilder per Bulk-Bar einer Person manuell zuweisen.

---

## Overview

| Phase | Thema | Tier | Status |
|---|---|---|---|
| 1 | Neue Person anlegen — Personen-UI + NgRx | standard | complete |
| 2 | Person-bewusster Upload — face_job + Shell/ImportDialog | heikel | complete |
| 3 | Bulk-Personenzuweisung — BulkBar + Backend-Job | standard | complete |

---

## Kontrakt (Cross-Modul-Ankerpunkt)

### Backend (Phase 2 — face_job.py)

`_run_face_job` prüft nach dem Speichern aller Gesichter, ob das Asset eine
`AssetInstance` mit `fixed_person=True` hat. Wenn ja:

- Gesichter nach `score` absteigend sortieren
- Bestes Gesicht → `person_id` auf den fixierten Person-ID setzen, `_run_incremental_match` überspringen
- Weitere Gesichter → bleiben `_unknown`, normaler incremental-match-Pfad

### Backend (Phase 3 — neuer Endpoint + Job)

```python
POST /api/persons/{person_id}/bulk-assign
Body: { asset_ids: list[int] }
→ { job_id: str }
```

Job (`bulk_assign_person_job.py`):
- Datei von `current_person/photos/` → `target_person/photos/` verschieben
- `AssetInstance.person_id = target_person_id`, `fixed_person = True`
- `AssetInstance.path` aktualisieren
- Vorhandene `Face`-Zeilen mit `person_id == _unknown` umsortieren:
  - Genau 1 Gesicht: direkt zu `target_person`
  - Mehrere: bestes (score desc) zu `target_person`, Rest bleibt `_unknown`

### Frontend — neue NgRx-Actions (Phase 1)

```typescript
// persons.actions.ts — neu
'Create Person':         props<{ name: string }>()
'Create Person Success': props<{ person: PersonDto }>()
'Create Person Failure': props<{ error: string }>()
```

### Frontend — ImportDialog-Erweiterung (Phase 2)

```typescript
// import-dialog.ts — neue Inputs
personId   = input<number | null>(null)
personName = input<string | null>(null)
```
Wenn `personId` gesetzt: `personService.importToPersonFolder()` statt
`assetService.uploadFiles()` + Banner „Bilder werden [Name] zugeordnet".

### Frontend — BulkBar-Erweiterung (Phase 3)

```typescript
// bulk-bar.ts — neu
persons            = input<PersonDto[]>([])
assignPersonAction = output<void>()
```

Neuer Service-Aufruf:
```typescript
// person.service.ts — neu
bulkAssignPerson(personId: number, assetIds: number[]): Observable<{ job_id: string }>
```

---

## Finale Abnahme-Kriterien

- [ ] „Neue Person" in Personen-Toolbar anlegen → Galerie öffnet sich mit Personen-Filter vorbelegt
- [ ] Galerie-Upload bei aktivem Personen-Filter → Bilder landen in der Person's `photos/`-Ordner mit `fixed_person=True`
- [ ] Einzelgesicht erkannt → direkt der Person zugewiesen (kein Review-Schritt)
- [ ] Mehrere Gesichter erkannt → bestes der Person, Rest in `_unknown` (incremental match läuft normal)
- [ ] BulkBar zeigt „Person zuweisen" wenn Bilder ausgewählt und Personen vorhanden
- [ ] Bulk-Zuweisung verschiebt Dateien + Gesichter korrekt, Job läuft in der Job-Queue

---

## Risiken

🟡 **face_job: `fixed_person`-Check erfordert DB-Lookup pro Asset.** Ein extra
`SELECT` auf `AssetInstance` pro Job. Bei `auto_face=True` und großem Bulk-Import
akkumuliert sich das. Vertretbar (ein Lookup pro Job ist kein Hot-Loop).

🟡 **Bulk-Assign: Dateibewegung kann scheitern.** Wenn `source_path` nicht
existiert oder `target_person`-Ordner nicht angelegt ist, muss der Job
graceful pro Asset loggen + weitermachen (nicht abbrechen).

🟡 **ImportDialog-Kontext.** Die Shell kennt den Galerie-Filter erst nach dem
Store-Read. Nur auf der `/galerie`-Route mit gesetztem `personId` soll der
Person-Upload-Pfad aktiv sein — andernfalls immer normaler Import.

---

## Archiv-Footer

**Summary:** —
**Files touched:** —
**Commits:** —
**Deviations:** —
**Follow-ups:** —
