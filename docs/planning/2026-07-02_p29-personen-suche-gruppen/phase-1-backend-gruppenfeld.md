# Phase 1 — Backend: Gruppenfeld + Erstellungsdatum

**Tier:** standard
**Status:** pending

---

## Kontext (vorher lesen)

- `backend/photofant/db/models.py` — `Person`-Klasse, Zeile ~26-31
- `backend/photofant/api/persons.py` — `PersonDto`, `_build_person_dto`, `create_person`, `rename_person`
- `backend/alembic/` — Migrations-Verzeichnis, letzte Migration als Vorlage für Stil/Naming
- Referenz für nullable `DateTime`-Spalte mit Backfill-Verzicht: `Asset.created_at` (models.py Zeile 60)

---

## Abnahme-Kriterien

- [ ] Migration läuft sauber gegen die bestehende DB (`alembic upgrade head`)
- [ ] `GET /api/persons` liefert `group_name` und `created_at` für jede Person
- [ ] `POST /api/persons` (neue Person) setzt `created_at` automatisch
- [ ] `PATCH /api/persons/{id}` akzeptiert `group_name` (optional, unabhängig von `name`)
- [ ] `group_name: ""` im PATCH-Body löscht die Gruppe (wird zu `None`)
- [ ] Weder `name` noch `group_name` gesetzt → 422

---

## Checkliste

### Migration (neu, alembic)

- [ ] `alembic revision -m "add person group_name and created_at"` im `backend/`-Verzeichnis
- [ ] Upgrade:
  ```python
  op.add_column("person", sa.Column("group_name", sa.Text(), nullable=True))
  op.add_column("person", sa.Column("created_at", sa.DateTime(), nullable=True))
  ```
- [ ] Downgrade: beide Spalten wieder droppen
- [ ] Kein Backfill für bestehende Zeilen — beide Felder bleiben `NULL`

### db/models.py

- [ ] `Person`-Klasse erweitern:
  ```python
  group_name: Mapped[str | None] = mapped_column(Text, nullable=True)
  created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
  ```
  (`Text`, `DateTime`, `datetime` sind bereits importiert — siehe Kopf der Datei)

### api/persons.py

- [ ] `PersonDto` erweitern:
  ```python
  group_name: str | None
  created_at: datetime | None
  ```
- [ ] `_build_person_dto` — beide neuen Felder durchreichen:
  ```python
  group_name=person.group_name,
  created_at=person.created_at,
  ```
- [ ] `create_person` — `created_at` setzen:
  ```python
  from datetime import UTC, datetime
  new_person = Person(name=name, is_unknown=False, created_at=datetime.now(UTC).replace(tzinfo=None))
  ```
- [ ] `RenameRequest` → umbenennen/erweitern zu `UpdatePersonRequest`:
  ```python
  class UpdatePersonRequest(BaseModel):
      name: str | None = None
      group_name: str | None = None
  ```
- [ ] `rename_person` → `update_person` umbauen:
  ```python
  @router.patch("/{person_id}", response_model=PersonDto)
  async def update_person(person_id: int, body: UpdatePersonRequest, session: DbSession) -> PersonDto:
      person = session.get(Person, person_id)
      if person is None:
          raise HTTPException(status_code=404, detail="Person not found")
      if body.name is None and body.group_name is None:
          raise HTTPException(status_code=422, detail="Nothing to update")

      if body.name is not None:
          if person.is_unknown:
              raise HTTPException(status_code=400, detail="Cannot rename the unknown person")
          new_name = body.name.strip()
          if not new_name:
              raise HTTPException(status_code=422, detail="Name must not be empty")
          # bestehende Rename-Logik (Ordner umbenennen) unverändert übernehmen
          ...
          person.name = new_name

      if body.group_name is not None:
          person.group_name = body.group_name.strip() or None

      session.commit()
      session.refresh(person)
      return _build_person_dto(session, person)
  ```
  🟡 **Wichtig:** die bestehende Ordner-Umbenennung (`rename_person_folder`) darf
  nur laufen, wenn `body.name is not None` — sonst wird bei einem reinen
  Gruppen-Update unnötig das Dateisystem angefasst.

---

## Doc-Updates

- [ ] `docs/models.md` — `Person`-Tabelle um `group_name`, `created_at` ergänzen
- [ ] `docs/routes.md` — `PATCH /api/persons/{id}` Request-Body-Doku aktualisieren
