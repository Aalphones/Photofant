# Phase 2 — Person-bewusster Upload (face_job + Shell/ImportDialog)

**Tier:** heikel
**Status:** pending

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

- [ ] Asset importiert in Person-Ordner (via Upload-Button oder Drag&Drop) → `fixed_person=True` ✅ (bereits)
- [ ] Face-Job läuft nach Import → 1 Gesicht erkannt → direkt der Person zugewiesen (nicht `_unknown`)
- [ ] Face-Job → 2+ Gesichter erkannt → bestes zur Person, Rest bleibt `_unknown` (incremental match normal)
- [ ] Galerie mit Personen-Filter aktiv → Upload-Button öffnet ImportDialog mit Person-Banner
- [ ] ImportDialog mit Person-Banner → lädt über `POST /api/persons/{id}/import`
- [ ] Galerie ohne Personen-Filter → normaler Upload-Pfad (unverändert)

---

## Checkliste

### Backend: face_job.py

- [ ] Hilfsfunktion `_get_fixed_person_id(asset_id: int) -> int | None` ergänzen:
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

- [ ] In `_run_face_job()` — nach der Gesichts-Schleife (alle `face_id`s bekannt):

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

- [ ] `_run_incremental_match(face_id)` — nur aufrufen wenn `fixed_person_id is None or face_index != 0`:
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

- [ ] Neue Inputs ergänzen:
  ```typescript
  readonly personId   = input<number | null>(null)
  readonly personName = input<string | null>(null)
  ```
- [ ] `submit()`-Methode: Person-Pfad einschlagen wenn `personId()` gesetzt:
  ```typescript
  const pid = this.personId();
  const request$ = pid != null
    ? this.personService.importToPersonFolder(pid, this.files())
    : this.mode() === 'path'
      ? this.assetService.importPaths(this.parsePaths())
      : this.assetService.uploadFiles(this.files());
  ```
- [ ] `PersonService` via `inject()` ergänzen (bereits tree-shakeable, kein Modul-Import nötig).
- [ ] `canSubmit()`: wenn `personId()` gesetzt → nur Upload-Tab relevant (Pfad-Tab ausblenden):
  ```typescript
  protected canSubmit(): boolean {
    if (this.isLoading()) { return false; }
    if (this.personId() != null) { return this.files().length > 0; }
    if (this.mode() === 'path') { return this.pathInput().trim().length > 0; }
    return this.files().length > 0;
  }
  ```

### Frontend: import-dialog.html

- [ ] Banner oberhalb der Tabs einfügen (nur wenn personName() gesetzt):
  ```html
  @if (personName()) {
    <div class="import-dialog__person-banner">
      <pf-icon name="user" [size]="14" />
      Bilder werden <strong>{{ personName() }}</strong> zugeordnet
    </div>
  }
  ```
- [ ] Pfad-Tab ausblenden wenn personId() gesetzt (Upload ist der einzig sinnvolle Modus):
  ```html
  @if (!personId()) {
    <div class="import-dialog__tabs">…</div>
  }
  ```
- [ ] CSS-Klasse `import-dialog__person-banner` in `import-dialog.scss` ergänzen
  (dezenter Info-Chip, analog anderen Bannern im Projekt).

### Frontend: shell.ts

- [ ] `Store` bereits injiziert ✅. Person-Filter lesen:
  ```typescript
  private readonly activePersonId   = this.store.selectSignal(filtersSelectors.personId);
  private readonly activePersonName = computed((): string | null => {
    const personId = this.activePersonId();
    if (personId == null) { return null; }
    // persons muss für diese Auflösung im Store sein — nur auflösen wenn bereits geladen
    // Shell nutzt personsSelectors nicht direkt; Name ist optional (Banner zeigt ID-Fallback)
    return null;   // Phase 2: personId reicht, Name wird in ImportDialog nicht gezeigt wenn null
  });
  ```

  🟡 **Vereinfachung Phase 2:** Shell übergibt nur `personId`, `personName = null`.
  Der Banner zeigt dann „Bilder werden dieser Person zugeordnet" ohne Namen.
  Verbesserung (Name anzeigen) kann als Follow-up in Phase 3 mitgenommen werden,
  wenn persons im Store sowieso für den AssignPersonDialog geladen werden.

- [ ] `openImport()` — aktuelle Route prüfen + personId übergeben:
  ```typescript
  protected openImport(): void {
    this.droppedFiles.set([]);
    const onGalerie = this.router.url.startsWith('/galerie');
    this.importPersonId.set(onGalerie ? (this.activePersonId() ?? null) : null);
    this.isImportOpen.set(true);
  }
  ```
  Neues Signal: `importPersonId = signal<number | null>(null)`.

- [ ] `closeImport()`:
  ```typescript
  protected closeImport(): void {
    this.isImportOpen.set(false);
    this.droppedFiles.set([]);
    this.importPersonId.set(null);
  }
  ```

### Frontend: shell.html

- [ ] `pf-import-dialog` erhält die neuen Inputs:
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

- [ ] Keine neuen Settings-Keys
- [ ] FINDINGS.md in diesem Plan-Ordner: Beobachtungen zur `fixed_person`-Logik festhalten falls Abweichungen vom Plan auftreten
