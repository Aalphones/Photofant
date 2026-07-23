# Gesichter-Galerie: Mehrfachauswahl (Löschen, Upscale, Trainingsset)

> Der „Auswählen"-Button im Gesichter-Tab der Galerie ist reiner UI-Blindgänger — er schaltet
> global `selectionMode` im Store um, aber `pf-face-grid` bekommt weder `selectionMode` noch
> `selectedIds` als Input, und `pf-face-cell` kennt gar keinen Auswahl-Zustand. Klick auf ein
> Gesicht öffnet immer die Lightbox, egal was der Button sagt. Dieser Plan macht die Taste
> nutzbar und hängt drei Aktionen dran: Löschen (Backend existiert bereits), Hochskalieren
> (Face-Crop selbst, nicht das ganze Foto — neu) und Zu-Trainingsset-hinzufügen (Face-Crop als
> eigenes Trainingsset-Item, nicht das ganze Foto — neu, braucht Schema-Erweiterung).
> *(private, aber Vollplan — Cross-Modul: Frontend-Selection-State + zwei Backend-Erweiterungen,
> eine davon mit DB-Migration.)*

## Phasen

| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | `collection_item` Schema-Erweiterung für Face-Items (Migration 0042, ADR-035) | heikel | ✅ complete |
| 2 | Collections-API: Face-Items hinzufügen/entfernen/auflisten | standard | ✅ complete |
| 3 | Trainingsset-Stats + Export mit Face-Items | standard | pending |
| 4 | Face-Upscale: ComfyUI-Auto-Import auf Face-Ziele erweitern (ADR-036) | heikel | pending |
| 5 | Face-Selection: eigener NgRx-State-Slice | standard | pending |
| 6 | Face-Grid/-Cell: Checkbox-Overlay + Klick-Verdrahtung | standard | pending |
| 7 | Face-Bulk-Bar: Löschen / Hochskalieren / Zu Trainingsset | standard | pending |
| 8 | Doku (code-map, models, routes) | mechanisch | pending |

## Ziel

Im Gesichter-Tab der Galerie kann man mehrere Gesichter auswählen (Checkbox-Overlay, wie bei
Fotos schon vorhanden) und darauf drei Aktionen anwenden: **Löschen**, **Hochskalieren**
(verbessert den Crop selbst — nicht das Foto, aus dem er stammt) und **Zu Trainingsset
hinzufügen** (der Crop wird Trainingsset-Mitglied — nicht das ganze Foto).

## Vorgeschichte — was der User entschieden hat

Zwei echte Architektur-Weichen wurden vor diesem Plan explizit gestellt (AskUserQuestion),
weil beide sonst am bestehenden Datenmodell vorbeigebaut worden wären:

1. **Face-Upscale ist ein echtes Face-Upscale, kein Foto-Upscale-Proxy.** Der Crop selbst wird
   hochskaliert, als neue face-gebundene `Version` gespeichert, `Face.is_upscaled` wird `True`
   gesetzt — das passt zum bestehenden Datenmodell (`Face.is_upscaled` fließt schon heute in den
   Cleanup-Score ein, ADR-033, wird aber aktuell **nirgends** auf `True` gesetzt — dieser Plan
   baut das erste und einzige Feature, das es tut). Die Alternative (bestehenden
   Asset-Bulk-Upscale auf die Quell-Fotos der Gesichter umleiten) wäre günstiger gewesen, hätte
   aber `is_upscaled` am Gesicht nie berührt und wäre bei manuell importierten Gesichtern ohne
   Quell-Foto (`Face.asset_id IS NULL`) komplett leer gelaufen.
2. **Trainingsset-Mitgliedschaft ist face-crop-basiert, kein Foto-Proxy.** `CollectionItem`
   bekommt eine neue, mit `asset_id` gleichberechtigte Spalte `face_id` (XOR, analog zum
   bestehenden `Version`-Modell) statt einfach das Quell-Foto des Gesichts hinzuzufügen. Größerer
   Scope (Schema-Migration, Export-Pipeline, Stats), aber konsistent mit der Absicht: ein
   Trainingsset aus Gesichter-Crops soll auch wirklich Crops enthalten, nicht ganze Fotos.

## Wichtige Funde vor dem Planen

**`CollectionItem` ist im Bestand strikt asset-basiert** (`backend/photofant/db/models.py:188-195`)
— Primärschlüssel ist heute `(collection_id, asset_id)`, `asset_id` ist `NOT NULL`. Jede
Erweiterung um Face-Items braucht zwingend eine Schema-Migration (Phase 1), nicht nur neue
API-Felder.

**Der XOR-Pattern für nullable Doppel-Spalten existiert im Projekt bereits zweimal, an zwei
verschiedenen Stellen — beide sind die Vorlage für Phase 1:**
- `Version` (`models.py:218-235`, Migration `0018_version_table.py`): `CheckConstraint`
  `(instance_id IS NOT NULL AND face_id IS NULL) OR (instance_id IS NULL AND face_id IS NOT NULL)`.
  Kein Unique-Zwang nötig (mehrere Versionen pro Achse erlaubt) — reine Zugehörigkeit.
- `review_item` (Migration `0027_review_item_face_suggestion_uniqueness.py`): **Partial Unique
  Index** (`sqlite_where=...`) statt eines normalen Unique-Constraints, weil ein normaler
  Multi-Spalten-Unique-Constraint bei NULL-Werten laut SQL-Standard nicht greift (zwei Zeilen mit
  gleichem `asset_id` aber `face_id IS NULL` gelten nicht als Duplikat). **Das ist exakt das
  Muster, das `collection_item` braucht** — hier zusätzlich mit Umstieg von zusammengesetztem PK
  auf einen surrogaten `id`-PK (siehe Phase 1), weil eine Spalte im heutigen PK nullable werden muss.

**ComfyUI-Bulk-Upscale kennt heute nur Asset-Ziele.** `run_default_workflow`
(`backend/photofant/api/comfyui.py:502-681`) importiert Ergebnisse über
`import_comfyui_output` (`backend/photofant/comfyui/importer.py:125-208`) als **komplett neues
Asset** (ADR-013) — kein `Version`-Objekt beteiligt. Der Pfad, den Face-Upscale tatsächlich
braucht (Ergebnis als face-gebundene `Version`, `is_current=True`, Thumbnail-Erzeugung,
`is_upscaled=True` am Face), existiert schon — aber nur im **Editor-Speicherpfad**
(`backend/photofant/api/edit_sessions.py:657-756`, `save_session`). Phase 4 baut einen neuen,
zweiten Auto-Import-Zweig, der dieses Editor-Muster nachbaut statt `import_comfyui_output`
wiederzuverwenden.

**Face-Bilder werden schon heute an ComfyUI übergeben** — `face_inputs` existiert bereits im
manuellen Workflow-Run (`comfyui.py:348-499`, `RunLeiste`/`onBindFace` im Frontend). Nur der
**Bulk-Ein-Klick-Pfad** (`run_default_workflow`, `target_asset_ids`-only) kennt keine Face-Ziele.
Phase 4 erweitert genau diesen Pfad, nicht den manuellen.

**Faces ohne Quell-Foto existieren real** (`Face.asset_id` ist nullable — `origin=manual_original`,
direkter Crop-Import über `POST /faces/import`). Für diese Faces ist „zum Foto zurückgehen" nie
möglich — genau der Fall, den die face-crop-basierte Trainingsset-Lösung (statt Foto-Proxy)
sauber abdeckt: sie funktioniert für **jedes** Face, mit oder ohne Quell-Foto.

**Scope-Schnitt in Phase 2/3 (bewusst, nicht versehentlich):** Face-Items in einem Trainingsset
bekommen in diesem Plan **Hinzufügen, Auflisten, Entfernen, Export, Stats-Zählung** — **nicht**
manuelle Reihenfolge (`position`/Reorder), **nicht** Near-Dupe-Review, und AR-Bucket-Stats laufen
über die `bbox`-Maße (`x2-x1`, `y2-y1` aus `Face.bbox`, bereits vorhanden — kein Datei-Zugriff
nötig), nicht über echte Pixel-Maße nach Padding. Diese drei Features existieren für Asset-Items
und blieben für Face-Items in v1 unangetastet — siehe „Bewusst draußen".

## Kontrakt (Schema + API, bindend für alle Phasen)

**`collection_item` — neue Spalten-Form (Migration 0042, Phase 1):**

```python
class CollectionItem(Base):
    __tablename__ = "collection_item"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collection.id"), nullable=False, index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("asset.id"), nullable=True, index=True)
    face_id: Mapped[int | None] = mapped_column(ForeignKey("face.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="manual")
    caption_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # CheckConstraint ck_collection_item_xor: asset_id XOR face_id (analog Version)
    # Partial Unique Index uq_collection_item_asset: (collection_id, asset_id) WHERE asset_id IS NOT NULL
    # Partial Unique Index uq_collection_item_face:  (collection_id, face_id)  WHERE face_id IS NOT NULL
```

**Backend-API-Erweiterungen (Phase 2/4, Signaturen bindend):**

```python
class AddItemsRequest(BaseModel):
    asset_ids: list[int] = []
    face_ids: list[int] = []

class DefaultRunRequest(RunRequest):
    target_asset_ids: list[int] = []
    target_face_ids: list[int] = []
    # genau eine der beiden Listen darf nicht-leer sein — validiert in run_default_workflow
```

**Frontend-Service-Erweiterungen (Phase 2/4/7, Signaturen bindend):**

```typescript
// collection.service.ts
addItems(collectionId: number, params: { assetIds?: number[]; faceIds?: number[] }): Observable<void>

// comfyui.service.ts
runDefaultWorkflow(task: string, params: {
  target_asset_ids?: number[]; target_face_ids?: number[]; inputs: Record<string, unknown>;
}): Observable<{ jobs: { job_id: string }[] }>
```

**Neue Route:** `DELETE /collections/{collection_id}/items/faces/{face_id}` (Geschwister-Route
zur bestehenden `DELETE /collections/{collection_id}/items/{asset_id}` — nicht dieselbe Route mit
Typ-Disambiguierung überladen, das würde Pfad-Parameter-Typen vermischen).

## Finale AK (Gesamt)

- [ ] Im Gesichter-Tab macht „Auswählen" Gesichter tatsächlich anklickbar-selektierbar
      (Checkbox-Overlay, wie im Foto-Tab), unabhängig vom Foto-Tab-Auswahlzustand.
- [ ] Mehrere ausgewählte Gesichter lassen sich in einem Aufruf löschen (bestehender
      Bulk-Delete-Endpunkt, jetzt aus der UI erreichbar).
- [ ] Mehrere ausgewählte Gesichter lassen sich hochskalieren — Ergebnis ersetzt den Crop als
      neue aktuelle Version am Gesicht, `is_upscaled` wird danach `true`.
- [ ] Mehrere ausgewählte Gesichter lassen sich einem bestehenden Trainingsset als Crop-Mitglieder
      hinzufügen — auch Gesichter ohne Quell-Foto.
- [ ] Ein Trainingsset-Export mit Face-Items erzeugt pro Face-Item eine Bilddatei (aus
      `crop_path`) plus Sidecar (Caption aus `caption_override`, leer falls nicht gesetzt).
- [ ] ADR-035 und ADR-036 dokumentieren die beiden Architektur-Entscheidungen.

## Risiken

- 🟡 **SQLite-PK-Umbau in Phase 1** — von zusammengesetztem PK auf surrogaten `id`-PK, per
  Alembic `batch_alter_table(recreate="always")`. Ungewöhnlichster Einzelschritt im ganzen Plan,
  siehe Konfidenz-Ausweis.
- 🟡 **Caption-Lücke bei Face-Items im Export** — Faces haben keine eigene Caption-Spalte;
  Sidecar-Caption kommt ausschließlich aus `CollectionItem.caption_override`. Ohne manuell
  gesetzten Override bleibt die Sidecar-Datei bei Face-Items leer. Bewusst akzeptiert (kein
  automatischer Foto-Caption-Fallback, da inkonsistent mit „Crop, nicht Foto").
- 🟡 **AR-Bucket-Stats für Face-Items nutzen `bbox`-Maße, nicht echte Crop-Pixel-Maße** — nach
  Padding kann das Seitenverhältnis leicht abweichen. Für eine Bucket-Näherung ausreichend,
  explizit kein Blocker.
- 🟡 **Stack-Pseudo-Einträge (`kind: "version"`) teilen ihre `id` mit dem Eltern-Face**
  (`face-grid.ts:56-63`) — Auswahl eines Stapel-Mitglieds selektiert dasselbe `face.id` wie das
  Eltern-Face selbst (analog zum bestehenden Lightbox-Öffnen-Verhalten). Kein neuer Bug, nur
  bestehendes Konfliktmuster geerbt — dokumentiert in Phase 6.
- 🟡 **Trainingsset-Editor-UI bleibt unangetastet.** Face-Items sind ab Phase 2 vollständig über
  die API nutzbar (hinzufügen, auflisten, exportieren, Stats), aber die bestehende
  Editor-Grid-Komponente (`features/trainingssets/training-set-item`) wurde nicht darauf
  ausgelegt, `kind="face"`-Einträge (keine Tags/Framing/Caption) hübsch darzustellen — sie
  zeigt sie mit leeren Feldern an, stürzt aber nicht ab. Bewusster Scope-Schnitt (siehe
  Phase 2 „Bewusst außerhalb dieser Phase"), kein Versehen.

## Bewusst draußen (Feature-Radar, max. 1 Punkt — hier verbraucht)

**Manuelle Reihenfolge (Reorder) und Near-Dupe-Review für Face-Items in Trainingssets.** Beide
Features existieren heute für Asset-Items (`reorder`, Near-Dupe-Review-Query in
`api/collections.py`) und wären am selben Schema-Umbau technisch erreichbar — aber nicht
angefragt, und Near-Dupe bräuchte ein Embedding pro Face-Crop (existiert nicht). Bleibt
Backlog-Kandidat, falls Trainingssets mit Face-Items in der Praxis Kuratierung brauchen.

## Konfidenz-Ausweis

1. **Am unsichersten: die SQLite-PK-Umstellung in Phase 1.** `batch_alter_table(recreate="always")`
   mit gleichzeitigem Spalten-Hinzufügen, Nullable-Wechsel und PK-Tausch ist der komplexeste
   Migrations-Schritt im gesamten Projekt bisher (bestehende Migrationen ändern PKs nie, nur
   `0027` ändert Unique-Constraints). **Check:** Migration gegen eine **Kopie** der echten
   Dev-Datenbank laufen lassen, danach `sqlite3 <db> ".schema collection_item"` prüfen (neuer
   `id`-PK, `face_id`-Spalte vorhanden) und `SELECT count(*) FROM collection_item` vor/nach
   der Migration vergleichen (keine Zeile verloren).
2. **Zweitunsicherste Stelle: der neue Face-Auto-Import-Zweig in Phase 4** teilt sich Code mit
   `edit_sessions.py` (`_unset_current_versions`, `_generate_version_thumbnail`) — diese Helfer
   sind heute modul-privat. **Check:** vor dem Schreiben prüfen, ob eine Extraktion in ein
   gemeinsames Modul (z. B. `photofant/media/versions.py`) nötig ist oder ein Re-Export genügt,
   damit kein Kopier-Drift zwischen Editor-Pfad und Upscale-Pfad entsteht (siehe Phase 4,
   Aufgabe 2).
3. **Drittens: Windows-Migration lokal ausführen, bevor Phase 2 beginnt** — Phase 2-8 bauen alle
   auf der neuen Spalte auf; ein Fehlschlag in Phase 1 muss vor jeder Folgearbeit auffallen, nicht
   erst am Ende.

## Smoke-Checkliste (du prüfst am Plan-Ende)

1. **Migration zuerst:** `alembic upgrade head` läuft ohne Fehler, bestehende Alben/Trainingssets
   zeigen danach unverändert ihre alten Foto-Mitglieder.
2. **Auswählen im Gesichter-Tab:** Button aktivieren, mehrere Gesichter anklicken (Checkbox
   erscheint, Klick öffnet **nicht** mehr die Lightbox), Zähler in der Bulk-Leiste stimmt.
3. **Löschen:** ausgewählte Gesichter löschen, Galerie aktualisiert sich, gelöschte Gesichter sind
   weg (auch aus Cluster/Person-Zuordnung, falls zugeordnet).
4. **Hochskalieren:** ausgewählte Gesichter hochskalieren, Toast bestätigt Job-Start, nach
   Abschluss zeigt die Gesichter-Kachel den neuen (größeren/schärferen) Crop, Cleanup-Score-Ansicht
   in „Personen" zeigt das Gesicht danach nicht mehr als upscale-bedürftig.
5. **Trainingsset:** ausgewählte Gesichter (mind. eines mit, eines ohne Quell-Foto, falls
   vorhanden) einem Trainingsset hinzufügen, im Trainingsset-Editor erscheinen sie als
   Crop-Einträge, Export erzeugt Bilddateien + Sidecars für beide.

## Bottom-Sektionen

_(beim Archivieren füllen)_

### Summary
### Files touched
### Commits
### Deviations from plan
### Follow-ups
