# Phase 3 — Trainingsset-Stats + Export mit Face-Items

**Komplexität:** standard (reine Erweiterung bestehender Queries, keine neue Architektur-Entscheidung).

**Voraussetzung:** Phase 1 + 2 abgeschlossen.

## Kontext (lesen vor dem Start)

- [backend/photofant/collections/stats.py](../../../backend/photofant/collections/stats.py) —
  komplette Datei ist klein (170 Zeilen), einmal ganz lesen. `compute_training_set_stats`
  (Zeile 112-169) ist die einzige zu ändernde Funktion.
- [backend/photofant/jobs/export_job.py:251-311](../../../backend/photofant/jobs/export_job.py#L251) —
  `_sidecar_content`, `_collection_item_rows`, `_copy_collection_item`. `_collection_item_rows`
  (Zeile 260-285) ist die einzige zu ändernde Funktion.
- [backend/photofant/db/models.py:198-215](../../../backend/photofant/db/models.py#L198) — `Face`,
  `crop_path`, `bbox`.
- README „Wichtige Funde" — Scope-Schnitt: Near-Dupe-Rate bleibt **asset-only** (kein Embedding
  pro Face-Crop vorhanden), AR-Buckets nutzen `bbox`-Maße für Face-Items.

## Aufgabe 1 — `compute_training_set_stats` um Face-Items erweitern

`backend/photofant/collections/stats.py:21` — Import ergänzen: `from photofant.db.models import
Asset, AssetTag, CollectionItem, Face, Tag`.

`compute_training_set_stats` (Zeile 112-169) — nach der bestehenden Asset-Query eine Face-Query
ergänzen, deren Ergebnisse in `total`, `ar_buckets` und `framing`/`quality`/`tags` einfließen wie
folgt: **Framing, Qualität und Tags bleiben rein asset-basiert** (Faces haben keine dieser
Eigenschaften) — Face-Items zählen nur in `total` und `ar_buckets` mit, **Near-Dupe-Rate bleibt
komplett asset-only** (Face-Embeddings existieren nicht).

```python
def compute_training_set_stats(session: Session, collection_id: int) -> TrainingSetStats:
    from photofant.settings import load_settings

    asset_rows = (
        session.query(
            Asset.id, Asset.framing, Asset.quality_score, Asset.width, Asset.height, Asset.dino_embedding
        )
        .join(CollectionItem, CollectionItem.asset_id == Asset.id)
        .filter(CollectionItem.collection_id == collection_id)
        .all()
    )
    face_rows = (
        session.query(Face.bbox)
        .join(CollectionItem, CollectionItem.face_id == Face.id)
        .filter(CollectionItem.collection_id == collection_id)
        .all()
    )
    total = len(asset_rows) + len(face_rows)
    if total == 0:
        return TrainingSetStats(total=0)

    framing_counts = Counter(row.framing for row in asset_rows if row.framing is not None)
    framing = [DistItem(value=value, count=count) for value, count in framing_counts.most_common()]

    quality_buckets = [0] * 5
    for row in asset_rows:
        if row.quality_score is None:
            continue
        index = min(int(row.quality_score * 5), 4)
        quality_buckets[index] += 1
    quality_histogram = [
        HistogramBucket(label=_quality_bucket_label(index), count=count)
        for index, count in enumerate(quality_buckets)
    ]

    ar_keys = [_bucket_key(row.width, row.height) for row in asset_rows]
    for (bbox,) in face_rows:
        if bbox:
            ar_keys.append(_bucket_key(int(bbox["x2"] - bbox["x1"]), int(bbox["y2"] - bbox["y1"])))
    bucket_counts = Counter(key for key in ar_keys if key is not None)
    ar_buckets = [DistItem(value=value, count=count) for value, count in bucket_counts.most_common()]

    asset_ids = [row.id for row in asset_rows]
    tag_rows = (
        session.query(Tag.name, func.count(AssetTag.id).label("cnt"))
        .join(AssetTag, AssetTag.tag_id == Tag.id)
        .filter(AssetTag.asset_id.in_(asset_ids), AssetTag.manually_removed.is_(False))
        .group_by(Tag.name)
        .order_by(func.count(AssetTag.id).desc())
        .limit(20)
        .all()
    ) if asset_ids else []
    tag_frequencies = [TagFrequency(name=row.name, count=row.cnt) for row in tag_rows]

    embeddings = [bytes(row.dino_embedding) for row in asset_rows if row.dino_embedding is not None]
    near_dupe_threshold = load_settings()["training_near_dupe_dino_threshold"]
    near_dupe_rate = _near_dupe_rate(embeddings, near_dupe_threshold)

    return TrainingSetStats(
        total=total,
        framing=framing,
        tag_frequencies=tag_frequencies,
        quality_histogram=quality_histogram,
        ar_buckets=ar_buckets,
        near_dupe_rate=round(near_dupe_rate, 4),
    )
```

Docstring-Kommentar am Funktionskopf ergänzen: „Face-Items zählen in `total`/`ar_buckets` mit
(bbox-Maße statt echter Crop-Pixel-Maße — Näherung, siehe Plan-README Risiken), bleiben aber
außen vor bei `framing`/`quality_histogram`/`tag_frequencies`/`near_dupe_rate` — diese
Eigenschaften existieren am Face-Modell nicht bzw. (Near-Dupe) fehlt das nötige Embedding."

## Aufgabe 2 — `_collection_item_rows` um Face-Items erweitern

`backend/photofant/jobs/export_job.py:21` — Import ergänzen: `from photofant.db.models import
Asset, AssetInstance, AssetTag, CollectionItem, Face, Person, Tag`.

`_collection_item_rows` (Zeile 260-285):

```python
def _collection_item_rows(collection_id: int) -> list[tuple[Path, str | None, list[str]]]:
    """Active members: (source path, effective caption, effective tag names).

    Asset-Items: effective caption = `caption_override` if set, else `Asset.caption` (Galerie-
    Original). Face-Items (P-Gesichter-Mehrfachauswahl, ADR-035) haben keine Galerie-Caption —
    `caption_override` ist hier die einzige Quelle (leer bleibt leer, kein Foto-Fallback), Tags
    bleiben immer `[]` (kein Face-Tag-Konzept)."""
    with SessionLocal() as session:
        asset_rows = (
            session.query(AssetInstance.path, Asset.id, Asset.caption, CollectionItem.caption_override)
            .join(Asset, Asset.id == AssetInstance.asset_id)
            .join(CollectionItem, CollectionItem.asset_id == Asset.id)
            .filter(CollectionItem.collection_id == collection_id, AssetInstance.deleted_at.is_(None))
            .distinct()
            .all()
        )
        items: list[tuple[Path, str | None, list[str]]] = []
        for path, asset_id, caption, caption_override in asset_rows:
            tag_rows = (
                session.query(Tag.name)
                .join(AssetTag, AssetTag.tag_id == Tag.id)
                .filter(AssetTag.asset_id == asset_id, AssetTag.manually_removed.is_(False))
                .order_by(AssetTag.score.desc())
                .all()
            )
            items.append((Path(path), caption_override or caption, [row[0] for row in tag_rows]))

        face_rows = (
            session.query(Face.crop_path, CollectionItem.caption_override)
            .join(CollectionItem, CollectionItem.face_id == Face.id)
            .filter(CollectionItem.collection_id == collection_id)
            .distinct()
            .all()
        )
        for crop_path, caption_override in face_rows:
            items.append((Path(crop_path), caption_override, []))

        return items
```

Downstream (`_copy_collection_item`, `_split_train_val`, `run_export_collection_job`) bleiben
**unverändert** — sie arbeiten bereits generisch auf `(Path, caption, tags)`-Tupeln, unabhängig
davon ob die Quelle ein Asset oder ein Face war.

## AK dieser Phase

- [x] `GET /collections/{id}/stats` für ein Trainingsset mit gemischten Asset- und Face-Items:
      `total` zählt beide, `ar_buckets` enthält Einträge aus beiden Quellen, `framing`/
      `quality_histogram`/`tag_frequencies`/`near_dupe_rate` bleiben unverändert asset-only
      (keine Exception, keine falschen Werte für Face-Anteile). Abgedeckt durch
      `test_stats_mixed_asset_and_face_items` + `test_stats_face_without_bbox_skips_ar_bucket`
      (`backend/tests/test_collection_face_items.py`).
- [x] `POST /collections/{id}/export` für dasselbe gemischte Trainingsset erzeugt Bilddateien für
      Face-Items (aus `crop_path`) und Asset-Items (wie bisher), Sidecar-Dateien mit korrektem
      Caption-Verhalten (Face-Item ohne `caption_override` → leere Sidecar-Datei, kein Absturz).
      Abgedeckt durch `test_export_rows_mixed_asset_and_face_items` (Sidecar-Bau selbst
      unverändert generisch, siehe Downstream-Hinweis in der Phasen-Datei oben).
- [x] Ein Trainingsset **ohne** Face-Items (nur Fotos) liefert exakt dieselben Stats/Export-Werte
      wie vor dieser Phase (Regressionscheck). Abgedeckt durch
      `test_stats_asset_only_collection_unchanged` + bestehender
      `test_training_near_dupe_rate_uses_dino` (`test_dupe_scan_dino.py`, weiterhin grün).

## Doc-Updates

- [x] `docs/code-map.md` — Zeile „Trainingssets & Export": Hinweis ergänzt, dass Stats/Export
      jetzt auch Face-Items lesen (`collections/stats.py`, `jobs/export_job.py`).

## Report-Back

`ar_buckets` bei gemischten Sets: Face-Crops landen im selben Bucket-Format wie Assets
(`"<Basis> · <Seitenverhältnis>"`, z. B. `"512 · 1:1"`) — ein 512×512-Face-Crop und ein
1024×1024-Asset landen in unterschiedlichen Buckets (verschiedene Basisauflösung), aber
beide sind sauber gezählt, keine Kollision oder falsche Zuordnung. Die bbox-Näherung ist für
die Bucket-Granularität (grobe AR-Stufen, nicht Pixel-genau) ausreichend — genau das Risiko,
das die README vorab benannt hat, kein neuer Fund.
