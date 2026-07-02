# Phase 2 — Person-bewusster Upload (face_job + Shell/ImportDialog)

**Tier:** heikel
**Status:** complete

Zwei unabhängige Teilprobleme in einer Phase:
1. **Backend:** `face_job` soll bei `fixed_person=True`-Assets das beste Gesicht direkt der Person zuweisen.
2. **Frontend:** Shell leitet den Upload-Dialog bei aktivem Personen-Filter an den Person-Import-Pfad weiter.

---

## Kontext (vorher lesen)

- `backend/photofant/jobs/face_job.py` — `_run_face_job()`, Schleife ab Zeile ~157
- `backend/photofant/db/models.py` — `AssetInstance` (Felder: `fixed_person`, `person_id`, `asset_id`)
- `frontend/src/app/shell/shell.ts` — `openImport()`, `isImportOpen`
- `frontend/src/app/shell/shell.html`
- `frontend/src/app/ui/import-dialog/import-dialog.ts` — bestehende Inputs/Submit-Logik
- `frontend/src/app/ui/import-dialog/import-dialog.html`
- `frontend/src/app/services/person.service.ts` — `importToPersonFolder()` bereits vorhanden ✅
- `frontend/src/app/store/filters/filters.selectors.ts` — `personId`-Selector

---

## Abnahme-Kriterien

- [x] Asset importiert in Person-Ordner (via Upload-Button oder Drag&Drop) → `fixed_person=True` ✅ (bereits)
- [x] Face-Job läuft nach Import → 1 Gesicht erkannt → direkt der Person zugewiesen (nicht `_unknown`)
- [x] Face-Job → 2+ Gesichter erkannt → bestes zur Person, Rest bleibt `_unknown` (incremental match normal)
- [x] Galerie mit Personen-Filter aktiv → Upload-Button öffnet ImportDialog mit Person-Banner
- [x] ImportDialog mit Person-Banner → lädt über `POST /api/persons/{id}/import`
- [x] Galerie ohne Personen-Filter → normaler Upload-Pfad (unverändert)

**Smoke-Test steht noch aus** (User führt am Plan-Ende durch, siehe finale AK in der README).

---

## Checkliste

### Backend: face_job.py

🟡 **Abweichung:** kein separates `_get_fixed_person_id()` + Post-hoc-Update auf
`Face` nach dem Insert — stattdessen wird `fixed_person_id` einmal vor der
Schleife geholt und direkt beim `Face(...)`-Insert als `person_id` gesetzt
(spart eine zusätzliche Session-Runde pro Asset, gleiches Ergebnis). Ein
Ad-hoc-Fix von vor der Phase (`544c95a`) deckte nur den Single-Face-Fall ab —
siehe FINDINGS.md.

- [x] Hilfsfunktion `_get_fixed_person_id(asset_id: int) -> int | None` ergänzen:
  ```python
  def _get_fixed_person_id(asset_id: int) -> int | None:
    from photofant.db.models import AssetInstance
    with SessionLocal() as session:
        instance = session.scalar(
            select(AssetInstance).where(
                AssetInstance.asset_id == asset_id,
                AssetInstance.fixed_person.is_(True),
                AssetInstance.deleted_at.is_(None),
            )
        )
        return int(instance.person_id) if instance is not None else None
  ```

- [x] In `_run_face_job()` — nach der Gesichts-Schleife (alle `face_id`s bekannt):

  Vor dem ersten `for face_index, face_dict in enumerate(faces):` Block wird
  `fixed_person_id = _get_fixed_person_id(asset_id)` einmalig geholt.

  In der Schleife: nach `session.add(face_row); session.flush(); face_id = face_row.id; session.commit()`:
  ```python
  # Fixierte Person: bestes Gesicht direkt zuweisen
  if fixed_person_id is not None and face_index == 0:
      # face_index 0 = höchste Score (faces ist nach score desc sortiert)
      with SessionLocal() as session:
          face = session.get(Face, face_id)
          if face is not None:
              face.person_id = fixed_person_id
              session.commit()
      log.info(
          "Fixed-person override: face %d → person %d (asset %d)",
          face_id, fixed_person_id, asset_id,
      )
  ```

  🟡 **Reihenfolge sicherstellen:** `faces`-Liste muss vor der Schleife nach `score`
  absteigend sortiert sein:
  ```python
  faces = sorted(faces, key=lambda f: f.get("score") or 0.0, reverse=True)
  ```
  Einfügen direkt nach `faces = engine.detect(image)` und dem `if not faces:` Guard.

- [x] `_run_incremental_match(face_id)` — nur aufrufen wenn `fixed_person_id is None or face_index != 0`:
  ```python
  if embedding is not None:
      try:
          _upsert_face_vector(face_id, embedding)
      except Exception:
          log.exception("Face vector index upsert failed for face %d", face_id)
      if fixed_person_id is None or face_index != 0:
          try:
              _run_incremental_match(face_id)
          except Exception:
              log.exception("Incremental match failed for face %d", face_id)
  ```

### Frontend: import-dialog.ts

🟡 **Abweichung:** Die Plan-Skizze ging von einem bestehenden Pfad-Tab
(`mode()`, `pathInput()`) im ImportDialog aus — den gibt es in der aktuellen
Komponente nicht (nur Drag&Drop/Datei-Upload). `submit()` und `canSubmit()`
brauchten daher keinen Tab-Zweig, nur die Person/Normal-Verzweigung.

- [x] Neue Inputs ergänzen:
  ```typescript
  readonly personId   = input<number | null>(null)
  readonly personName = input<string | null>(null)
  ```
- [x] `submit()`-Methode: Person-Pfad einschlagen wenn `personId()` gesetzt:
  ```typescript
  const personId = this.personId();
  const request$ = personId != null
    ? this.personService.importToPersonFolder(personId, this.files())
    : this.assetService.uploadFiles(this.files());
  ```
- [x] `PersonService` via `inject()` ergänzt.
- [x] `canSubmit()`: unverändert (`files().length > 0`) — es gibt keinen Pfad-Tab, der ausgeblendet werden müsste.

### Frontend: import-dialog.html

- [x] Banner oberhalb des Body einfügen (nur wenn `personId()` gesetzt; zeigt
  Namen wenn vorhanden, sonst generischen Text — Klasse `imp-person-banner`
  passend zum bestehenden `imp-*`-Naming der Komponente, nicht
  `import-dialog__*`).
- [x] Kein Pfad-Tab vorhanden → nichts auszublenden (siehe Abweichung oben).
- [x] CSS-Klasse `imp-person-banner` in `import-dialog.scss` ergänzt (Info-Chip
  mit `--accent-weak`, analog `.imp-error`).

### Frontend: shell.ts

🟡 **Vereinfachung Phase 2 (wie im Plan vorgesehen):** kein `activePersonName`
computed — würde ohnehin immer `null` liefern (persons sind in der Shell nicht
geladen). Banner zeigt ohne Namen „Bilder werden dieser Person zugeordnet".
Namensauflösung ist ein möglicher Phase-3-Follow-up.

**Zusätzliche Abweichung:** Person-Pfad gilt auch für den globalen
Drag&Drop-Handler (`registerGlobalDnD` → `onDrop`), nicht nur für den
Upload-Button — beide nutzen jetzt `resolveImportPersonId()`. Die finalen AK
verlangen ausdrücklich „via Upload-Button oder Drag&Drop".

- [x] `Store` bereits injiziert ✅. Person-Filter lesen:
  ```typescript
  private readonly activePersonId = this.store.selectSignal(filtersSelectors.personId);
  ```

- [x] `openImport()` — aktuelle Route prüfen + personId übergeben:
  ```typescript
  protected openImport(): void {
    this.droppedFiles.set([]);
    this.importPersonId.set(this.resolveImportPersonId());
    this.isImportOpen.set(true);
  }

  private resolveImportPersonId(): number | null {
    return this.router.url.startsWith('/galerie') ? this.activePersonId() : null;
  }
  ```
  Neues Signal: `importPersonId = signal<number | null>(null)`. Gleicher Aufruf
  auch im DnD-`onDrop`-Handler.

- [x] `closeImport()`:
  ```typescript
  protected closeImport(): void {
    this.isImportOpen.set(false);
    this.droppedFiles.set([]);
    this.importPersonId.set(null);
  }
  ```

### Frontend: shell.html

- [x] `pf-import-dialog` erhält die neuen Inputs:
  ```html
  <pf-import-dialog
    [initialFiles]="droppedFiles()"
    [personId]="importPersonId()"
    (close)="closeImport()"
    (imported)="onImported()"
  />
  ```

---

## Doc-Updates

- [x] Keine neuen Settings-Keys
- [x] FINDINGS.md in diesem Plan-Ordner: Ad-hoc-Fix-Fund festgehalten
