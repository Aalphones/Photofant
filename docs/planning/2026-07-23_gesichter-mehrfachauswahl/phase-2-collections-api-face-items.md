# Phase 2 — Collections-API: Face-Items hinzufügen/entfernen/auflisten

**Komplexität:** standard (Muster ist durch Phase 1 vorgegeben, keine neue Architektur-Entscheidung).

**Voraussetzung:** Phase 1 abgeschlossen (Migration `0042` gelaufen, `CollectionItem.face_id` existiert).

## Kontext (lesen vor dem Start)

- [backend/photofant/api/collections.py:1-46](../../../backend/photofant/api/collections.py#L1) —
  Imports, `_VALID_KINDS`, Router-Setup.
- [backend/photofant/api/collections.py:104-166](../../../backend/photofant/api/collections.py#L104) —
  `ReorderItemsRequest`, `TrainingSetItemDto`, `AddItemsRequest` (Zeile 161-162, heute nur
  `asset_ids: list[int]`).
- [backend/photofant/api/collections.py:475-491](../../../backend/photofant/api/collections.py#L475) —
  `add_items`, heutiger Asset-only-Zustand.
- [backend/photofant/api/collections.py:518-528](../../../backend/photofant/api/collections.py#L518) —
  `remove_item(collection_id, asset_id)`.
- [backend/photofant/api/collections.py:531-566](../../../backend/photofant/api/collections.py#L531) —
  `list_training_set_items` — Asset-only Query + DTO-Bau.
- [backend/photofant/api/collections.py:569-583](../../../backend/photofant/api/collections.py#L569) —
  `update_item_caption(collection_id, asset_id, ...)`.
- [backend/photofant/db/models.py:198-215](../../../backend/photofant/db/models.py#L198) — `Face`,
  insbesondere `bbox` (`{x1,y1,x2,y2}`, keine eigene `width`/`height`-Spalte).
- README „Kontrakt" — `AddItemsRequest`-Zielform ist dort bindend vorgegeben.
- [frontend/src/app/services/collection.service.ts:54-56](../../../frontend/src/app/services/collection.service.ts#L54) —
  `addItems(collectionId, assetIds)`, wird zur Ziel-Signatur aus README „Kontrakt" umgebaut.
- [frontend/src/app/store/collections/collections.actions.ts:46-48](../../../frontend/src/app/store/collections/collections.actions.ts#L46) —
  `'Add Items': props<{ collectionId: number; assetIds: number[] }>()`.
- [frontend/src/app/store/collections/collections.effects.ts:143-155](../../../frontend/src/app/store/collections/collections.effects.ts#L143) —
  `addItems$`-Effect, ruft den Service auf.

⚠️ **FastAPI-Routing-Falle, vor dem Schreiben verstehen:** `remove_item` (Zeile 518) hat die
Signatur `remove_item(collection_id: int, asset_id: int, ...)` auf dem Pfad
`/{collection_id}/items/{asset_id}`. Starlette matcht Pfad-Segmente **als String**, bevor FastAPI
den Typ validiert — eine neue Route `/{collection_id}/items/faces/{face_id}` würde von der
bestehenden Route **verdeckt**, wenn diese zuerst im Router registriert ist (Starlette probiert
Routen in Registrierungsreihenfolge; `{asset_id}` matcht auch das literale Segment `"faces"`,
FastAPI würde dann versuchen `"faces"` als `int` zu parsen und mit 422 abbrechen, **ohne** die
speziellere Route je zu versuchen). Jede neue face-spezifische Route mit demselben Pfad-Präfix
**muss vor** der bestehenden `asset_id`-Route im Modul stehen (nicht danach).

## Aufgabe 1 — `AddItemsRequest` erweitern + `add_items`

`collections.py:161-162`:

```python
class AddItemsRequest(BaseModel):
    asset_ids: list[int] = []
    face_ids: list[int] = []
```

`add_items` (Zeile 475-491) — Face-Zweig danach ergänzen, analog zum bestehenden Asset-Zweig:

```python
@router.post("/{collection_id}/items", status_code=204)
async def add_items(collection_id: int, body: AddItemsRequest, session: DbSession) -> Response:
    """Add hand-picked members (Bulk-Bar „Zu Album"/"Zu Trainingsset"). Manual rows win over smart ones."""
    _get_collection_or_404(session, collection_id)
    for asset_id in body.asset_ids:
        item = session.query(CollectionItem).filter_by(collection_id=collection_id, asset_id=asset_id).first()
        if item is None:
            session.add(CollectionItem(collection_id=collection_id, asset_id=asset_id, source="manual"))
        else:
            item.source = "manual"
    for face_id in body.face_ids:
        item = session.query(CollectionItem).filter_by(collection_id=collection_id, face_id=face_id).first()
        if item is None:
            session.add(CollectionItem(collection_id=collection_id, face_id=face_id, source="manual"))
        else:
            item.source = "manual"
    session.commit()
    log.info(
        "Added %d asset item(s) + %d face item(s) to collection %d",
        len(body.asset_ids), len(body.face_ids), collection_id,
    )
    return Response(status_code=204)
```

## Aufgabe 2 — Face-Item entfernen (neue Route, **vor** `remove_item` einfügen)

Direkt **oberhalb** von `remove_item` (Zeile 518), damit die Registrierungsreihenfolge stimmt
(siehe Warnung oben):

```python
@router.delete("/{collection_id}/items/faces/{face_id}", status_code=204)
async def remove_face_item(collection_id: int, face_id: int, session: DbSession) -> Response:
    item = (
        session.query(CollectionItem)
        .filter_by(collection_id=collection_id, face_id=face_id)
        .first()
    )
    if item is not None:
        session.delete(item)
        session.commit()
    return Response(status_code=204)
```

## Aufgabe 3 — `TrainingSetItemDto` erweitern + `list_training_set_items`

`Face` zu den Imports aus `photofant.db.models` hinzufügen (Zeile 23-32).

`TrainingSetItemDto` (Zeile 108-118) — neue Felder ergänzen, bestehende bleiben unverändert
(Rückwärtskompatibilität für Asset-Items):

```python
class TrainingSetItemDto(BaseModel):
    kind: Literal["asset", "face"] = "asset"
    id: int  # asset.id bei kind="asset", face.id bei kind="face"
    face_id: int | None = None  # gespiegelt für face-Items, erleichtert Frontend-Discriminated-Union
    thumbnail_url: str | None = None  # nur bei kind="face" gesetzt — Frontend baut Asset-URLs weiter selbst
    content_hash: str | None
    width: int | None
    height: int | None
    framing: str | None
    quality: float | None
    caption: str | None
    caption_override: str | None
    effective_caption: str | None
    tags: list[TagDto]
```

`list_training_set_items` (Zeile 531-566) — Asset-Query unverändert lassen, danach einen
Face-Zweig anhängen:

```python
@router.get("/{collection_id}/items", response_model=list[TrainingSetItemDto])
async def list_training_set_items(collection_id: int, session: DbSession) -> list[TrainingSetItemDto]:
    """Full item detail for the training-set editor. Face-Items (P-Gesichter-Mehrfachauswahl,
    ADR-035) haben keine Tags/Framing/Quality/Caption — die Felder bleiben None/[] statt Fantasiewerte
    zu erfinden."""
    _get_collection_or_404(session, collection_id)
    items: list[TrainingSetItemDto] = []

    asset_rows = (
        session.query(Asset, CollectionItem.caption_override)
        .join(CollectionItem, CollectionItem.asset_id == Asset.id)
        .join(AssetInstance, AssetInstance.asset_id == Asset.id)
        .filter(CollectionItem.collection_id == collection_id, AssetInstance.deleted_at.is_(None))
        .distinct()
        .all()
    )
    for asset, caption_override in asset_rows:
        tag_rows = (
            session.query(Tag.id, Tag.name, AssetTag.kind, AssetTag.score)
            .join(AssetTag, AssetTag.tag_id == Tag.id)
            .filter(AssetTag.asset_id == asset.id, AssetTag.manually_removed.is_(False))
            .all()
        )
        items.append(TrainingSetItemDto(
            kind="asset", id=asset.id, content_hash=asset.content_hash,
            width=asset.width, height=asset.height, framing=asset.framing, quality=asset.quality_score,
            caption=asset.caption, caption_override=caption_override,
            effective_caption=caption_override or asset.caption,
            tags=[TagDto(id=row.id, name=row.name, kind=row.kind, score=row.score) for row in tag_rows],
        ))

    face_rows = (
        session.query(Face, CollectionItem.caption_override)
        .join(CollectionItem, CollectionItem.face_id == Face.id)
        .filter(CollectionItem.collection_id == collection_id)
        .distinct()
        .all()
    )
    for face, caption_override in face_rows:
        bbox = face.bbox or {}
        width = int(bbox["x2"] - bbox["x1"]) if bbox else None
        height = int(bbox["y2"] - bbox["y1"]) if bbox else None
        items.append(TrainingSetItemDto(
            kind="face", id=face.id, face_id=face.id, thumbnail_url=f"/api/faces/{face.id}/thumbnail",
            content_hash=None, width=width, height=height, framing=None, quality=None,
            caption=None, caption_override=caption_override, effective_caption=caption_override,
            tags=[],
        ))
    return items
```

## Aufgabe 4 — Face-Caption-Override-Route (neue Route, **vor** `update_item_caption` einfügen)

Gleiche Registrierungsreihenfolge-Regel wie Aufgabe 2. Direkt oberhalb von
`update_item_caption` (Zeile 569):

```python
@router.patch("/{collection_id}/items/faces/{face_id}", status_code=204)
async def update_face_item_caption(
    collection_id: int, face_id: int, body: UpdateItemCaptionRequest, session: DbSession
) -> Response:
    """Face-Items haben keine Original-Caption (anders als Assets) — caption_override ist hier
    die einzige Caption-Quelle, nicht nur ein Override."""
    item = session.query(CollectionItem).filter_by(collection_id=collection_id, face_id=face_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found in collection")
    item.caption_override = (body.caption_override or "").strip() or None
    session.commit()
    return Response(status_code=204)
```

## Aufgabe 5 — Frontend: `CollectionService.addItems`

`frontend/src/app/services/collection.service.ts:54-56`, Signatur ändern:

```typescript
addItems(collectionId: number, params: { assetIds?: number[]; faceIds?: number[] }): Observable<void> {
  return this.http.post<void>(`/api/collections/${collectionId}/items`, {
    asset_ids: params.assetIds ?? [],
    face_ids: params.faceIds ?? [],
  });
}
```

## Aufgabe 6 — Frontend: NgRx-Action + Effect anpassen

`frontend/src/app/store/collections/collections.actions.ts:46`:

```typescript
'Add Items': props<{ collectionId: number; assetIds?: number[]; faceIds?: number[] }>(),
```

`frontend/src/app/store/collections/collections.effects.ts:143-155`, Aufruf anpassen:

```typescript
readonly addItems$ = createEffect(() =>
  this.actions$.pipe(
    ofType(collectionsActions.addItems),
    mergeMap(({ collectionId, assetIds, faceIds }) =>
      this.collectionService.addItems(collectionId, { assetIds, faceIds }).pipe(
        map(() => collectionsActions.addItemsSuccess()),
        catchError((error: HttpErrorResponse) =>
          of(collectionsActions.addItemsFailure({ error: error.message }))
        ),
      )
    ),
  )
);
```

**Bestehende Aufrufer nicht kaputt machen:** [galerie.ts:276](../../../frontend/src/app/features/galerie/galerie.ts#L276)
und [galerie.ts:283](../../../frontend/src/app/features/galerie/galerie.ts#L283) dispatchen
`collectionsActions.addItems({ collectionId, assetIds: ids })` ohne `faceIds` — bleibt durch das
optionale Feld unverändert lauffähig, nichts an diesen zwei Stellen ändern.

## Bewusst außerhalb dieser Phase (Scope-Grenze, nicht vergessen)

Die **Trainingsset-Editor-UI** (`features/trainingssets/training-set-item` und Geschwister-
Komponenten) wird in diesem Plan **nicht** angefasst. Face-Items erscheinen ab dieser Phase
korrekt in der API-Antwort (`kind: "face"`, Thumbnail-URL, keine Tags/Framing/Caption) — wie sie
in der bestehenden Editor-Grid-Komponente **visuell** dargestellt werden (evtl. leere
Tag-Chips, kein Framing-Filter greifbar), ist unverändert das Verhalten der Komponente auf
unbekannte Werte (`null`/`[]`), kein Absturz, aber auch keine gezielte Aufwertung. Falls das nach
diesem Plan unschön aussieht: eigener Folge-Plan für die Editor-Anpassung.

## AK dieser Phase

- [ ] `POST /collections/{id}/items` mit `face_ids` legt `CollectionItem`-Zeilen mit gesetztem
      `face_id` an (asset_ids weiterhin wie bisher).
- [ ] `DELETE /collections/{id}/items/faces/{face_id}` entfernt genau das Face-Item, lässt
      Asset-Items derselben Collection unberührt.
- [ ] `GET /collections/{id}/items` liefert Face-Items mit `kind="face"`, korrektem
      `thumbnail_url`, `width`/`height` aus `bbox`, leeren `tags`.
- [ ] `PATCH /collections/{id}/items/faces/{face_id}` setzt `caption_override` am Face-Item.
- [ ] Bestehende Asset-Item-Routen (`add_items`, `remove_item`, `update_item_caption`,
      `list_training_set_items` für Asset-Items) verhalten sich exakt wie vor dieser Phase —
      Regressionscheck: ein bestehendes Trainingsset mit nur Foto-Mitgliedern zeigt identische
      Werte wie vor der Migration.
- [ ] Routing-Reihenfolge verifiziert: `curl -X DELETE /collections/1/items/faces/5` trifft
      `remove_face_item`, nicht `remove_item` mit einem 422 wegen `"faces"` als ungültigem `int`.

## Doc-Updates

- [ ] `docs/routes.md` — neue Routen `DELETE .../items/faces/{face_id}`,
      `PATCH .../items/faces/{face_id}`, geänderte `AddItemsRequest`-Form bei `POST .../items`.

## Report-Back

_(nach Umsetzung ausfüllen: ob die Routing-Reihenfolge-Falle real aufgetreten wäre ohne die
Warnung, jegliche Abweichung vom DTO-Feldsatz)_
