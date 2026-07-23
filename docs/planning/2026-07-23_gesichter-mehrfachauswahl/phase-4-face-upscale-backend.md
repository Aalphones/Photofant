# Phase 4 — Face-Upscale: ComfyUI-Auto-Import auf Face-Ziele erweitern, ADR-036

**Komplexität:** heikel (neuer Auto-Import-Zweig, Code-Extraktion aus `edit_sessions.py`, Architektur-ADR).

**Voraussetzung:** keine Abhängigkeit von Phase 1-3 (andere Code-Ecke) — kann parallel/unabhängig
umgesetzt werden.

## Kontext (lesen vor dem Start)

- [backend/photofant/api/comfyui.py:150-163](../../../backend/photofant/api/comfyui.py#L150) —
  `RunRequest`, `DefaultRunRequest` (heute nur `target_asset_ids`).
- [backend/photofant/api/comfyui.py:502-681](../../../backend/photofant/api/comfyui.py#L502) —
  `run_default_workflow`, insbesondere Zeile 568-583 (Pflicht-Input-Validierung), 652-665
  (`expand_batch`-Aufruf), 657-679 (Ziel-Längen-Check + `enqueue_comfyui_runs`-Aufruf).
- [backend/photofant/jobs/comfyui_run_job.py:1-30](../../../backend/photofant/jobs/comfyui_run_job.py#L1) —
  Modul-Docstring + Imports.
- [backend/photofant/jobs/comfyui_run_job.py:161-216](../../../backend/photofant/jobs/comfyui_run_job.py#L161) —
  `expand_batch`, insbesondere Zeile 200-206: die Batch-Achse „faces" wird **bereits unterstützt**
  (kein Change nötig) — der fehlende Teil ist ausschließlich, was **nach** dem ComfyUI-Lauf mit
  dem Ergebnis passiert (Auto-Import), nicht die Input-Seite.
- [backend/photofant/jobs/comfyui_run_job.py:235-245](../../../backend/photofant/jobs/comfyui_run_job.py#L235) —
  `_resolve_face_paths` (bereits vorhanden, liest `Face.crop_path`).
- [backend/photofant/jobs/comfyui_run_job.py:353-425](../../../backend/photofant/jobs/comfyui_run_job.py#L353) —
  `_wait_and_import_output`, `_import_and_cleanup` (Asset-Auto-Import, ADR-013) — **Vorbild für
  Struktur**, nicht für den Ziel-Typ.
- [backend/photofant/jobs/comfyui_run_job.py:430-497](../../../backend/photofant/jobs/comfyui_run_job.py#L430) —
  `enqueue_comfyui_runs`, insbesondere Zeile 462-472 (`auto_import`-Dict-Bau).
- [backend/photofant/comfyui/importer.py:40-53](../../../backend/photofant/comfyui/importer.py#L40) —
  `ImportedComfyUIAsset`.
- [backend/photofant/comfyui/importer.py:211-256](../../../backend/photofant/comfyui/importer.py#L211) —
  `read_comfyui_output` (lädt Ergebnis-Bytes von ComfyUI — **wiederverwendbar, bereits public**),
  `delete_imported_local_output` (bereits public).
- [backend/photofant/comfyui/importer.py:268-277](../../../backend/photofant/comfyui/importer.py#L268) —
  `_write_edit_file` (aktuell modul-privat — wird in Aufgabe 1 public gemacht, `write_edit_file`).
- [backend/photofant/api/edit_sessions.py:657-756](../../../backend/photofant/api/edit_sessions.py#L657) —
  `save_session` — **die** Vorlage für die Version-Erzeugung selbst (Zeile 728-744: `_unset_current_versions`
  → `Version(...)` → Commit → `_generate_version_thumbnail`). Face-Upscale baut exakt dasselbe
  DB-Muster nach, nur mit ComfyUI-Ergebnisbytes statt gerenderten Editor-Steps.
- [backend/photofant/api/edit_sessions.py:770-787](../../../backend/photofant/api/edit_sessions.py#L770) —
  `_unset_current_versions`, `_generate_version_thumbnail` — werden in Aufgabe 2 in ein
  gemeinsames Modul extrahiert, damit Editor-Pfad und Upscale-Pfad nicht auseinanderdriften
  (siehe README Konfidenz-Ausweis Punkt 2).
- [frontend/src/app/models/comfyui-workflow.model.ts:107-120](../../../frontend/src/app/models/comfyui-workflow.model.ts#L107) —
  `DefaultRunTask`, `DefaultRunRequest` (TS-Interface).
- [frontend/src/app/services/comfyui.service.ts:174-190](../../../frontend/src/app/services/comfyui.service.ts#L174) —
  `runDefaultWorkflow` — Body-Konstruktion, `face_inputs` wird **bereits** durchgereicht.

## Aufgabe 1 — `_write_edit_file` public machen

`backend/photofant/comfyui/importer.py:268` — Funktion umbenennen: `_write_edit_file` →
`write_edit_file` (kein Verhaltensunterschied, nur der führende Unterstrich fällt weg, macht sie
für Phase 4 modulübergreifend importierbar statt gegen die Namenskonvention zu verstoßen). Den
einen bestehenden Aufruf in `import_comfyui_output` (Zeile 155) entsprechend anpassen.

## Aufgabe 2 — Version-Helfer in gemeinsames Modul extrahieren

Neue Datei `backend/photofant/media/versions.py`:

```python
"""Shared Version-row helpers — genutzt vom Crop-Editor-Speicherpfad (edit_sessions.py) UND vom
ComfyUI-Face-Upscale-Auto-Import (comfyui_run_job.py), damit beide Pfade exakt dasselbe
Version-Anlage-Muster teilen statt still auseinanderzudriften."""
from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy.orm import Session

from photofant.db.cache import get_cache_db_path, init_cache_db, store_thumbnail
from photofant.db.models import Version
from photofant.media.thumbnails import generate_thumbnail


def unset_current_versions(db: Session, instance_id: int | None, face_id: int | None) -> None:
    query = db.query(Version).filter(Version.is_current.is_(True))
    if instance_id is not None:
        query = query.filter(Version.instance_id == instance_id)
    else:
        query = query.filter(Version.face_id == face_id)
    for version in query.all():
        version.is_current = False


async def generate_version_thumbnail(version_id: int, file_path: Path) -> None:
    cache_path = get_cache_db_path()
    init_cache_db(cache_path)
    for size in (256, 512):
        thumb = await asyncio.to_thread(generate_thumbnail, file_path, size)
        await asyncio.to_thread(store_thumbnail, cache_path, version_id, size, thumb, "edit")
```

`backend/photofant/api/edit_sessions.py:770-787` — die beiden Funktionsdefinitionen **entfernen**,
stattdessen oben im Modul importieren:

```python
from photofant.media.versions import (
    generate_version_thumbnail as _generate_version_thumbnail,
    unset_current_versions as _unset_current_versions,
)
```

Alle bestehenden Aufrufstellen (`_unset_current_versions(...)`, `_generate_version_thumbnail(...)`
bei Zeile 714, 728, 744) bleiben **unverändert** — nur der Alias-Import ersetzt die lokale
Definition. `_find_current_version` (Zeile 759-767) bleibt in `edit_sessions.py`, wird nicht
gebraucht.

## Aufgabe 3 — `DefaultRunRequest` + Validierung in `comfyui.py`

`backend/photofant/api/comfyui.py:161-163`:

```python
class DefaultRunRequest(RunRequest):
    target_asset_ids: list[int] = []
    target_face_ids: list[int] = []
```

`run_default_workflow` (Zeile 502-681) — nach dem bestehenden `expand_batch`-Aufruf (Zeile
652-656) den Ziel-Längen-Check (Zeile 657-664) ersetzen durch:

```python
    if body.target_asset_ids and body.target_face_ids:
        raise HTTPException(
            status_code=422, detail="target_asset_ids und target_face_ids schließen sich aus",
        )
    targets = body.target_asset_ids or body.target_face_ids
    if not targets:
        raise HTTPException(
            status_code=422, detail="target_asset_ids oder target_face_ids erforderlich",
        )
    if len(targets) != len(expanded):
        raise HTTPException(
            status_code=422,
            detail=(
                "Ziel-Liste muss genau zur Anzahl expandierter Jobs passen "
                f"(erwartet {len(expanded)}, erhalten {len(targets)})"
            ),
        )
```

Den `enqueue_comfyui_runs`-Aufruf (Zeile 666-679) entsprechend erweitern:

```python
    statuses = await enqueue_comfyui_runs(
        workflow_template=template,
        input_bindings=input_bindings,
        param_bindings=param_bindings,
        expanded_inputs=expanded,
        params=param_values,
        workflow_name=workflow_item.name,
        mask_input_key=mask_input_key,
        mask_data_url=mask_data_url,
        auto_import_targets=body.target_asset_ids or None,
        auto_import_face_targets=body.target_face_ids or None,
        auto_import_task=task,
        auto_import_workflow_key=key,
        auto_import_output_node_id=output_node_id,
    )
```

**Kein Change an `expand_batch` selbst** — die Batch-Achse „faces" existiert bereits
(`comfyui_run_job.py:200-206`). Face-Upscale steuert seine Batch-Bilder über `body.face_inputs`
(nicht `body.inputs`) — das Frontend (Aufgabe 6) füttert den Bild-Slot des Upscale-Workflows mit
Face-IDs über genau dieses Feld, exakt wie es der manuelle Workflow-Modus (`RunLeiste`) heute
schon für Einzel-Faces tut.

## Aufgabe 4 — `enqueue_comfyui_runs`: face-Ziele im Auto-Import-Dict

`backend/photofant/jobs/comfyui_run_job.py:430-472`, Signatur + Dict-Bau:

```python
async def enqueue_comfyui_runs(
    workflow_template: dict[str, Any],
    input_bindings: list[dict[str, Any]],
    param_bindings: list[dict[str, Any]],
    expanded_inputs: list[tuple[dict[str, int], dict[str, int], dict[str, int]]],
    params: dict[str, Any],
    workflow_name: str,
    mask_input_key: str | None = None,
    mask_data_url: str | None = None,
    auto_import_targets: list[int] | None = None,
    auto_import_face_targets: list[int] | None = None,
    auto_import_task: str | None = None,
    auto_import_workflow_key: str | None = None,
    auto_import_output_node_id: str | None = None,
) -> list[JobStatus]:
    ...
    for index, (job_inputs, job_face_inputs, job_version_inputs) in enumerate(expanded_inputs):
        ...
        auto_import: dict[str, Any] | None = None
        if auto_import_targets is not None:
            auto_import = {
                "target_asset_id": auto_import_targets[index],
                "task": auto_import_task,
                "workflow_key": auto_import_workflow_key,
                "output_node_id": auto_import_output_node_id,
                "output_dir": output_dir,
                "poll_interval_seconds": poll_interval_seconds,
                "wait_timeout_seconds": wait_timeout_seconds,
            }
        elif auto_import_face_targets is not None:
            auto_import = {
                "target_face_id": auto_import_face_targets[index],
                "task": auto_import_task,
                "workflow_key": auto_import_workflow_key,
                "output_node_id": auto_import_output_node_id,
                "output_dir": output_dir,
                "poll_interval_seconds": poll_interval_seconds,
                "wait_timeout_seconds": wait_timeout_seconds,
            }
        ...  # Rest der Schleife unverändert
```

## Aufgabe 5 — Face-Auto-Import-Zweig in `_wait_and_import_output` + neue `_import_face_upscale_result`

`backend/photofant/jobs/comfyui_run_job.py:23` — Import ergänzen: `from photofant.db.models import
Asset, AssetInstance, Face, Person, Version` (nur `Person` ist neu in dieser Zeile).

Neue Funktion, direkt vor `_import_and_cleanup` (Zeile 401):

```python
def _import_face_upscale_result(
    client: ComfyUIClient, face_id: int, output: ComfyUIOutputRef, output_dir: str,
) -> tuple[int, Path]:
    """Sync-Hälfte des Face-Upscale-Imports: DB-Schreiben + lokales Output-Cleanup. Baut exakt
    dasselbe Version-Muster wie edit_sessions.py::save_session (Editor-Speicherpfad) nach, nur
    mit ComfyUI-Ergebnisbytes statt gerenderten Editor-Steps — beide Pfade teilen sich seit
    Aufgabe 2 dieselben Helfer (unset_current_versions/generate_version_thumbnail), damit sie
    nicht auseinanderdriften. Thumbnail-Erzeugung ist async (eigene to_thread-Aufrufe) und läuft
    getrennt im Aufrufer — analog zum bestehenden Split zwischen _import_and_cleanup und
    enqueue_post_import_pipeline für den Asset-Pfad."""
    from photofant.comfyui.importer import (
        delete_imported_local_output, read_comfyui_output, write_edit_file,
    )
    from photofant.media.versions import unset_current_versions

    with SessionLocal() as session:
        face = session.get(Face, face_id)
        if face is None:
            raise ValueError(f"Gesicht {face_id} nicht gefunden")
        person = session.get(Person, face.person_id or 1)
        if person is None:
            raise ValueError(f"Person fuer Gesicht {face_id} nicht gefunden")

        image_bytes, _local_source_path = read_comfyui_output(client, output, output_dir)
        destination = write_edit_file(person, output.filename, image_bytes)

        unset_current_versions(session, None, face_id)
        version = Version(
            instance_id=None,
            face_id=face_id,
            type="upscale",
            parent_id=None,
            path=str(destination.resolve()),
            is_current=True,
            params={"source": "comfyui_auto_import", "task": "upscale"},
            created_at=datetime.now(UTC),
        )
        session.add(version)
        face.is_upscaled = True
        session.commit()
        session.refresh(version)
        version_id = version.id

    delete_imported_local_output(output_dir, output)
    return version_id, destination
```

`datetime`/`UTC` importieren (`from datetime import UTC, datetime`) — noch nicht im Modul
importiert, oben bei den bestehenden Imports (Zeile 6-26) ergänzen.

`_wait_and_import_output` (Zeile 353-398) — nach dem bestehenden Progress-Update auf `0.9`
(Zeile 385) verzweigen:

```python
    job_queue.update(status, progress=0.9, state=JobState.RUNNING)

    target_face_id = auto_import.get("target_face_id")
    if target_face_id is not None:
        version_id, destination = await asyncio.to_thread(
            _import_face_upscale_result, client, int(target_face_id), output, output_dir,
        )
        from photofant.media.versions import generate_version_thumbnail
        await generate_version_thumbnail(version_id, destination)
        return

    imported = await asyncio.to_thread(
        _import_and_cleanup, client, target_asset_id, output, output_dir, task, workflow_key, prompt_id,
    )
    from photofant.jobs.import_job import enqueue_post_import_pipeline
    await enqueue_post_import_pipeline([imported.asset_id])
```

`target_asset_id = int(auto_import["target_asset_id"])` (Zeile 363) darf nicht mehr
bedingungslos am Funktionsanfang stehen, wenn `target_face_id` gesetzt ist (der Schlüssel fehlt
dann im Dict) — auf `auto_import.get("target_asset_id")` umstellen und erst im Asset-Zweig zu
`int(...)` konvertieren, analog zu `target_face_id` oben.

## Aufgabe 6 — Frontend: `DefaultRunRequest` + `runDefaultWorkflow`

`frontend/src/app/models/comfyui-workflow.model.ts:111-120`:

```typescript
export interface DefaultRunRequest {
  target_asset_ids?: number[];
  target_face_ids?: number[];
  inputs: Record<string, number | number[]>;
  face_inputs?: Record<string, number | number[]>;
  prompt?: string | null;
  negative_prompt?: string | null;
  resolution?: ResolutionRun | null;
  mask?: { asset_id: number; mask_data_url: string } | null;
  toggles?: Record<string, boolean>;
}
```

`frontend/src/app/services/comfyui.service.ts:175-190`, Body-Konstruktion ergänzen:

```typescript
runDefaultWorkflow(
  task: DefaultRunTask,
  payload: DefaultRunRequest,
): Observable<{ jobs: { job_id: string }[] }> {
  return this.http.post<{ jobs: { job_id: string }[] }>(
    `/api/comfyui/defaults/${task}/run`,
    {
      target_asset_ids: payload.target_asset_ids ?? [],
      target_face_ids: payload.target_face_ids ?? [],
      inputs: payload.inputs,
      face_inputs: payload.face_inputs ?? {},
      prompt: payload.prompt ?? null,
      negative_prompt: payload.negative_prompt ?? null,
      resolution: payload.resolution ?? null,
      mask: payload.mask ?? null,
      toggles: payload.toggles ?? {},
    },
  );
}
```

**Bestehender Aufrufer bleibt lauffähig:** [galerie.ts:362-365](../../../frontend/src/app/features/galerie/galerie.ts#L362)
(`onBulkUpscale`, Asset-Pfad) sendet `target_asset_ids` und `inputs`, kein `target_face_ids` —
läuft mit den neuen optionalen Feldern unverändert weiter. Der neue Face-Aufruf entsteht in
Phase 7 (`onFaceBulkUpscale`) und sendet spiegelbildlich `target_face_ids` + `face_inputs`
(leeres `inputs: {}`).

## Aufgabe 7 — ADR-036

Neue Datei `docs/decisions/036-face-upscale-auto-import.md`:

```markdown
# ADR-036 — Face-Upscale erzeugt eine face-gebundene Version, kein neues Asset

**Status:** Akzeptiert — 2026-07-23
**Querverweise:** [013](013-comfyui-asset-import.md) (Asset-Auto-Import, das Gegenstück für
Foto-Ziele), [033](033-face-cleanup-score-on-demand.md) (Face.is_upscaled im Cleanup-Score)

## Kontext
Der bestehende ComfyUI-Bulk-Auto-Import (`run_default_workflow`) kennt nur Asset-Ziele und legt
für jedes Ergebnis ein komplett neues `Asset` an (ADR-013) — passend für „ganzes Foto
hochskalieren", aber falsch für „Gesichts-Crop hochskalieren": es gibt kein Asset, das den
hochskalierten Crop sinnvoll repräsentiert, und `Face.is_upscaled` (fließt in den Cleanup-Score
ein) würde nie berührt.

## Entscheidung
Face-Upscale-Ergebnisse werden als neue **face-gebundene `Version`** gespeichert (dasselbe Muster
wie der Crop-Editor-Speicherpfad in `edit_sessions.py`), nicht als neues Asset. Der Editor-Pfad
und der neue Auto-Import-Pfad teilen sich seither dieselben Helfer
(`photofant/media/versions.py`), damit beide nicht auseinanderdriften. Das zugehörige `Face`
bekommt `is_upscaled = True`.

## Betrachtete Optionen
- **Asset-Auto-Import auf die Quell-Fotos der ausgewählten Gesichter umleiten** — kein neuer
  Auto-Import-Pfad nötig, aber upscaled das ganze Foto statt des Crops, berührt
  `Face.is_upscaled` nie, und funktioniert nicht für Gesichter ohne Quell-Foto
  (`Face.asset_id IS NULL`). Verworfen — vom User explizit gegen diese günstigere Variante
  entschieden (siehe Plan-README „Vorgeschichte").
- **Neues Asset auch für Face-Ergebnisse** (Wiederverwendung von `import_comfyui_output`) — hätte
  ein Asset ganz ohne zugehöriges Foto im Bestand erzeugt (keine `AssetInstance`,
  kein `original_id`-Ziel im bisherigen Sinn) — verworfen, verletzt die Asset-Invariante „ein
  Asset hat mindestens eine Instanz".

## Konsequenzen
- Face-Upscale ist der erste und einzige Ort im Bestand, der `Face.is_upscaled` auf `True` setzt.
- `edit_sessions.py` und `comfyui_run_job.py` teilen sich jetzt `photofant/media/versions.py` —
  künftige Änderungen am Version-Anlage-Muster (z. B. neue Pflichtfelder) müssen an **einer**
  Stelle gepflegt werden, nicht zwei.
```

## AK dieser Phase

- [ ] `POST /comfyui/defaults/upscale/run` mit `target_face_ids` + `face_inputs` läuft durch,
      liefert Job-IDs.
- [ ] Nach Job-Abschluss: neue `Version` mit `face_id` gesetzt, `is_current=True`, Thumbnail
      abrufbar (`/api/versions/{id}/thumbnail`), vorherige `is_current`-Version desselben Faces
      ist jetzt `False`.
- [ ] `Face.is_upscaled` ist nach dem Job `True`.
- [ ] Bestehender Asset-Upscale-Bulk-Flow (`onBulkUpscale`, Foto-Tab) funktioniert unverändert
      (Regressionscheck).
- [ ] `target_asset_ids` + `target_face_ids` gleichzeitig gesetzt → 422.
- [ ] ADR-036 liegt unter `docs/decisions/036-face-upscale-auto-import.md`.

## Doc-Updates

- [ ] `docs/routes.md` — `DefaultRunRequest`-Form bei `POST /comfyui/defaults/{task}/run`
      ergänzen (`target_face_ids`).
- [ ] `docs/code-map.md` — Zeile „Personen & Faces" oder „ComfyUI": Hinweis auf
      `photofant/media/versions.py` als gemeinsamen Helfer für Editor-Speichern + Face-Upscale.

## Report-Back

_(nach Umsetzung ausfüllen: ob die Extraktion nach `media/versions.py` reibungslos lief, echte
Laufzeit eines Face-Upscale-Jobs, jegliche Abweichung vom auto_import-Dict-Schema)_
