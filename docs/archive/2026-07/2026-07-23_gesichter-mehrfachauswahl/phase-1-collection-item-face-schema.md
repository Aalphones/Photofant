# Phase 1 — `collection_item` Schema-Erweiterung für Face-Items, ADR-035

**Komplexität:** heikel (SQLite-Primärschlüssel-Umbau, Architektur-ADR, betrifft jede spätere Phase).

## Kontext (lesen vor dem Start)

- [backend/photofant/db/models.py:161-195](../../../backend/photofant/db/models.py#L161) —
  `Collection` und `CollectionItem`, heutiger Zustand: zusammengesetzter PK `(collection_id,
  asset_id)`, `asset_id NOT NULL`.
- [backend/photofant/db/models.py:198-215](../../../backend/photofant/db/models.py#L198) — `Face`,
  insbesondere `id`, `bbox` (dict mit `x1,y1,x2,y2`).
- [backend/photofant/db/models.py:218-235](../../../backend/photofant/db/models.py#L218) —
  `Version`: Vorbild für das XOR-Pattern selbst (CheckConstraint, kein Unique-Zwang nötig, da
  Mehrfachzuordnung erlaubt ist — bei `CollectionItem` ist das anders, siehe unten).
- [backend/alembic/versions/0018_version_table.py](../../../backend/alembic/versions/0018_version_table.py) —
  wie das XOR-`CheckConstraint` in einer neuen Tabelle geschrieben wird.
- [backend/alembic/versions/0027_review_item_face_suggestion_uniqueness.py](../../../backend/alembic/versions/0027_review_item_face_suggestion_uniqueness.py) —
  **die** Vorlage für Partial-Unique-Indizes mit `sqlite_where` bei nullable XOR-Spalten. Dieselbe
  Situation wie hier: ein normaler Multi-Spalten-Unique-Constraint greift bei NULL-Werten laut
  SQL-Standard nicht (zwei Zeilen mit gleichem `asset_id` aber unterschiedlichem/NULL `face_id`
  gelten nicht als Duplikat) — deshalb zwei partielle Indizes statt eines Constraints.
- [backend/alembic/versions/0012_collections.py](../../../backend/alembic/versions/0012_collections.py) —
  die ursprüngliche `collection_item`-Migration (PK, `source`, `caption_override`).
- [backend/alembic/versions/0024_collection_polish.py](../../../backend/alembic/versions/0024_collection_polish.py) —
  fügte `position` hinzu, letzte Änderung an dieser Tabelle vor diesem Plan.
- **Migrationsnummer verifizieren:** `ls backend/alembic/versions/*.py | sort -V | tail -3` vor dem
  Schreiben laufen lassen — Stand bei Planung war `0041_asset_sort_date_index.py` (down_revision
  `0040`), diese Phase nutzt also Revision `0042` mit `down_revision = "0041"`. Falls seither eine
  weitere Migration entstanden ist, entsprechend hochzählen — nicht blind `0042` annehmen.
- **ADR-Nummer verifizieren:** `ls docs/decisions | tail -3` **und**
  `grep -rn "ADR-0[3-9][0-9]" docs/planning/` — Stand bei Planung war `034` auf Platte, kein
  jüngerer geparkter Plan reserviert `035` oder höher (verifiziert). Diese Phase nutzt `035`.

## Aufgabe 1 — Migration `0042_collection_item_face_support.py`

Neue Datei `backend/alembic/versions/0042_collection_item_face_support.py`:

```python
"""0042 — collection_item: face_id als Alternative zu asset_id (XOR)

Trainingssets sollen Face-Crops als eigenständige Mitglieder aufnehmen können, nicht nur ganze
Fotos (P-Gesichter-Mehrfachauswahl, ADR-035). asset_id wird nullable, eine neue face_id-Spalte
kommt dazu (FK auf face.id), CheckConstraint erzwingt XOR wie beim Version-Modell (0018).

Der bisherige zusammengesetzte PK (collection_id, asset_id) kann nicht bestehen bleiben, sobald
asset_id nullable wird (mehrere Face-Items mit asset_id=NULL in derselben Collection wären sonst
nicht mehr über den PK unterscheidbar) — Umstieg auf einen surrogaten Integer-PK `id`, Uniqueness
pro Achse über zwei partielle Unique-Indizes (Muster aus 0027: ein normaler Multi-Spalten-Unique-
Constraint greift bei NULL-Werten laut SQL-Standard nicht).

Revision ID: 0042
Revises: 0041
Create Date: 2026-07-23
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Schritt 1: face_id-Spalte + id-Spalte ergänzen, asset_id nullable machen, alten PK droppen.
    # recreate="always" ist bei SQLite nötig, weil eine PK-Änderung nicht per einfachem ALTER geht
    # — Alembic baut die Tabelle komplett neu (Kopie mit neuem Schema, Daten übernehmen, Rename).
    with op.batch_alter_table("collection_item", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("face_id", sa.Integer(), sa.ForeignKey("face.id"), nullable=True))
        batch_op.alter_column("asset_id", existing_type=sa.Integer(), nullable=True)
        batch_op.drop_constraint("pk_collection_item", type_="primary")

    # Schritt 2: bestehende Zeilen bekommen eine fortlaufende id (SQLite füllt eine nachträglich
    # als PRIMARY KEY deklarierte Integer-Spalte nicht rückwirkend über rowid).
    op.execute("UPDATE collection_item SET id = rowid WHERE id IS NULL")

    # Schritt 3: id zum echten (autoincrement) Primary Key machen — zweiter batch-Durchlauf, weil
    # Alembic/SQLite eine frisch hinzugefügte Spalte nicht im selben batch-Block zum PK umwidmen kann.
    with op.batch_alter_table("collection_item", recreate="always") as batch_op:
        batch_op.alter_column("id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_primary_key("pk_collection_item", ["id"])

    op.create_check_constraint(
        "ck_collection_item_xor",
        "collection_item",
        "(asset_id IS NOT NULL AND face_id IS NULL) OR (asset_id IS NULL AND face_id IS NOT NULL)",
    )
    op.create_index(
        "uq_collection_item_asset", "collection_item", ["collection_id", "asset_id"],
        unique=True, sqlite_where=sa.text("asset_id IS NOT NULL"),
    )
    op.create_index(
        "uq_collection_item_face", "collection_item", ["collection_id", "face_id"],
        unique=True, sqlite_where=sa.text("face_id IS NOT NULL"),
    )
    op.create_index("ix_collection_item_face_id", "collection_item", ["face_id"])
    op.create_index("ix_collection_item_collection_id", "collection_item", ["collection_id"])


def downgrade() -> None:
    op.drop_index("ix_collection_item_collection_id", table_name="collection_item")
    op.drop_index("ix_collection_item_face_id", table_name="collection_item")
    op.drop_index("uq_collection_item_face", table_name="collection_item")
    op.drop_index("uq_collection_item_asset", table_name="collection_item")

    # Face-Items können nicht zurück in ein asset_id-only-Schema — sie müssen vor dem Downgrade
    # gelöscht sein, sonst verletzt der alte NOT-NULL-Constraint auf asset_id die Restdaten.
    op.execute("DELETE FROM collection_item WHERE face_id IS NOT NULL")

    with op.batch_alter_table("collection_item", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_collection_item_xor", type_="check")
        batch_op.drop_column("face_id")
        batch_op.drop_column("id")
        batch_op.alter_column("asset_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_primary_key("pk_collection_item", ["collection_id", "asset_id"])
```

⚠️ **Vor dem Ausführen gegen die echte Dev-DB:** erst gegen eine **Kopie** testen (siehe
Konfidenz-Ausweis README Punkt 1). Falls `batch_op.create_primary_key` in einem separaten
zweiten `batch_alter_table`-Block nicht wie erwartet funktioniert (Alembic-Version-abhängig),
alternativ beide Schritte (Spalte hinzufügen + PK setzen) in einem einzigen
`recreate="always"`-Block versuchen und beobachten, ob die `UPDATE ... SET id = rowid`-Zeile
noch reinpasst (sie muss zwischen „Spalte existiert" und „PK gesetzt" laufen, weil eine bereits
als PK deklarierte Spalte keine NULL-Werte annimmt, die die `UPDATE`-Zeile befüllen könnte).

## Aufgabe 2 — Model-Update

`backend/photofant/db/models.py:188-195`, `CollectionItem` ersetzen durch:

```python
class CollectionItem(Base):
    __tablename__ = "collection_item"
    __table_args__ = (
        CheckConstraint(
            "(asset_id IS NOT NULL AND face_id IS NULL) OR (asset_id IS NULL AND face_id IS NOT NULL)",
            name="ck_collection_item_xor",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collection.id"), nullable=False, index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("asset.id"), nullable=True, index=True)
    face_id: Mapped[int | None] = mapped_column(ForeignKey("face.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="manual")
    caption_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

`CheckConstraint` ist an dieser Stelle bereits importiert (wird schon von `Version`, Zeile
220-224, genutzt) — kein neuer Import nötig.

## Aufgabe 3 — ADR-035

Neue Datei `docs/decisions/035-collection-item-face-support.md`:

```markdown
# ADR-035 — CollectionItem trägt Face-Crops als eigenständige Mitglieder

**Status:** Akzeptiert — 2026-07-23
**Querverweise:** [018](018-...) falls vorhanden, sonst Verweis auf `Version`-XOR-Pattern in
`models.py:218-235`; [033](033-face-cleanup-score-on-demand.md) (Face.is_upscaled)

## Kontext
Die Gesichter-Galerie soll Mehrfachauswahl mit „Zu Trainingsset hinzufügen" bekommen. Trainingssets
(`Collection.kind == "training_set"`) waren bislang ausschließlich foto-basiert — `CollectionItem`
kennt nur `asset_id`. Ein Face kann aber auch ganz ohne Quell-Foto existieren (`asset_id IS NULL`,
`origin="manual_original"`, direkter Crop-Import) — ein Foto-Proxy („füge das Foto hinzu, zu dem
das Gesicht gehört") würde für diese Faces ins Leere laufen und würde außerdem das ganze Foto statt
nur des Crops zum Trainingsdatensatz machen, was der Absicht hinter einem Face-Trainingsset
widerspricht.

## Entscheidung
`collection_item` bekommt eine neue nullable `face_id`-Spalte (FK auf `face.id`), XOR mit
`asset_id` (analog zum bestehenden `Version`-Modell). Primärschlüssel wechselt von
`(collection_id, asset_id)` auf einen surrogaten `id`, Uniqueness pro Achse über zwei partielle
Unique-Indizes (Muster aus Migration `0027`). Export, Stats und Trainingsset-Editor lernen, beide
Item-Typen zu lesen; Reorder und Near-Dupe-Review bleiben für v1 asset-only (kein Embedding pro
Face-Crop vorhanden, nicht angefragt).

## Betrachtete Optionen
- **Foto-Proxy** (Face-Auswahl fügt das zugrundeliegende Asset hinzu) — kein Schema-Change,
  aber funktioniert nicht für Faces ohne Quell-Foto und würde ganze Fotos statt Crops in ein
  Face-Trainingsset einspeisen. Verworfen — widerspricht der Absicht hinter einem
  Crop-Trainingsset.
- **Separate `face_collection_item`-Tabelle** statt Erweiterung der bestehenden Tabelle — hätte
  Export/Stats/Editor gezwungen, zwei komplett getrennte Datenquellen zu unionen statt eine
  gemeinsame Query mit Typ-Diskriminator zu fahren. Verworfen — mehr Code-Verdopplung für
  denselben fachlichen Zweck (,,ein Trainingsset-Mitglied").

## Konsequenzen
- Jede Stelle, die bisher `CollectionItem.asset_id` als garantiert `NOT NULL` annahm, muss auf
  den XOR-Fall geprüft werden (Phase 2/3 dieses Plans deckt: add/remove/list/stats/export).
- Reorder und Near-Dupe-Review bleiben absichtlich asset-only in v1 — dokumentierte Lücke, kein
  Versehen (siehe Plan-README „Bewusst draußen").
```

## AK dieser Phase

- [x] Migration `0042` läuft gegen eine Kopie der Dev-DB fehlerfrei (`alembic upgrade head`).
- [x] `sqlite3 <db> ".schema collection_item"` zeigt: `id` als PK, `face_id`-Spalte, XOR-Check.
- [x] Zeilenzahl `collection_item` vor/nach Migration identisch (keine Zeile verloren) — im
      Test mit 3 Seed-Items verifiziert (Dev-DB selbst hat 0 collection_item-Zeilen).
- [x] Bestehende Alben/Trainingssets zeigen nach der Migration unverändert ihre alten Mitglieder
      — Seed-Asset-Items überlebten Upgrade und Downgrade/Re-Upgrade.
- [x] `downgrade()` funktioniert (einmal testweise durchlaufen, dann wieder hoch).
- [x] ADR-035 liegt unter `docs/decisions/035-collection-item-face-support.md`.

## Doc-Updates

- [x] `docs/models.md` — `collection_item`-Tabellenbeschreibung: `id`-PK, neue `face_id`-Spalte,
      XOR-Hinweis.

## Report-Back

- **Migrationsnummer:** `0042` wie geplant (`down_revision = "0041"`, verifiziert — Kopf auf Platte
  war `0041_asset_sort_date_index`). ADR-Nummer `035` frei (letzte auf Platte `034`).
- **Abweichung von der Plan-Mechanik (contract-neutral, gleiches Zielschema):** Nicht der
  `batch_alter_table(recreate="always")`-Zwei-Pass mit `drop_constraint(type_="primary")` +
  `create_primary_key`, sondern ein **manueller Tabellen-Neuaufbau** (create `collection_item_new`
  → `INSERT SELECT` → `drop_table` → `rename_table`). Grund: SQLite speichert den PK-Constraint-
  Namen nicht, der reflektierte PK heißt nicht `pk_collection_item` → Drop per Name unzuverlässig.
  Keine Fremdtabelle referenziert `collection_item` per FK (geprüft) → drop+rename gefahrlos.
  Idempotent über Spalten-Guard (`face_id` da → return), wie python.md verlangt.
- **Dev-DB-Kopie-Test (Alembic 1.18.4, `PHOTOFANT_SETTINGS_PATH` → Kopie):** Upgrade→Schema exakt
  (id-PK, asset/face nullable, XOR-Check, 5 Indizes, 3 FKs). XOR weist „beide gesetzt" und „keins
  gesetzt" ab; partielle Unique-Indizes weisen doppeltes Face bzw. Asset pro Collection ab.
  Downgrade löscht Face-Zeile, stellt zusammengesetzten PK wieder her (Daten der Asset-Zeilen
  erhalten), Re-Upgrade zurück auf 0042 mit intakten Daten.
- **Lint/Typen:** `ruff` grün auf Migration + models.py; `mypy --strict` sauber auf der Migration.
  models.py hat 4-6 vorbestehende „unused type: ignore" auf JSON-Spalten (nicht meine Zeilen —
  gegen HEAD verifiziert, meine Änderung fügt **null** neue Fehler hinzu).
