# Phase 5 — „aktualisiert am …" end-to-end

**Rating:** standard

Das Mockup zeigt in der Kopfzeile des Detail-Dialogs „45 % vollständig · Familie · aktualisiert
03. März 2026". Im Wissens-Schema gibt es **keinen** Zeitstempel. Er wird aus der Änderungszeit
der Vault-Markdown-Datei gelesen — nicht gespeichert, damit der Vault Markdown-first bleibt und
keine Spalte dazukommt, die man pflegen müsste.

## Kontext — das musst du lesen

- README dieses Plans, **Kontrakt-Sektion 3**.
- `backend/photofant/knowledge/vault.py` — `load_entity(path)` (Zeile 73), `save_entity` (102).
- `backend/photofant/api/knowledge.py` — `EntityDto` (Zeile 66), `LoreDto` (177) und die Stelle,
  an der `EntityDto` aus einer `Entity` gebaut wird.
- `frontend/src/app/models/knowledge.model.ts` → `EntityDto`.
- `frontend/src/app/features/wissen/knowledge-detail-dialog/knowledge-detail-dialog.html`
  Zeile 66 (die Sub-Zeile) und `.ts` (`percent()`).
- `docs/conventions/python.md`, `docs/conventions/angular.md`

**Pfad-Helfer ist vorhanden — geprüft:** `Vault.entity_path(entity, domain)` (`vault.py` Zeile 69)
liefert `<root>/<type-folder>/<slug>.md`. Den benutzen, **keinen** zweiten Pfad-Bau danebenstellen.
Er braucht die geladene Domäne — die liegt an der Bau-Stelle des DTOs ohnehin vor bzw. ist über
`vault.load_domain(entity.domain)` erreichbar.

## AK dieser Phase

1. `EntityDto` trägt `updated_at: datetime | None`.
2. Der Wert entspricht der Änderungszeit der Markdown-Datei der Entity.
3. Ist die Datei nicht auflösbar, ist der Wert `null` und **kein** Fehler.
4. Die Kopfzeile des Detail-Dialogs zeigt „N % vollständig · Domäne · aktualisiert TT. Mon JJJJ"
   (deutsches Format, z.B. „03. März 2026").
5. Bei `null` endet die Kopfzeile nach der Domäne — kein „aktualisiert —", kein leerer Punkt.
6. `uv run ruff check .`, `npm run lint`, `npm run build` grün.

## Checkliste

### Backend

- [x] `Vault.entity_path(entity, domain)` verwenden (siehe oben).
- [x] Funktion, die zu einer Entity die Datei-`mtime` als `datetime` liefert; `FileNotFoundError`
      und `OSError` → `None` (AK 3).
- [x] `EntityDto.updated_at: datetime | None = None` ergänzen und an der Bau-Stelle befüllen.
- [x] Test: Entity anlegen → `updated_at` ist gesetzt und liegt nicht in der Zukunft.
- [x] Test: nicht auflösbarer Pfad → `None`, kein Fehler.

### Frontend

- [x] `EntityDto.updated_at: string | null` im Model ergänzen.
- [x] In `knowledge-detail-dialog.ts` ein `computed` `updatedLabel(): string | null` — formatiert
      mit `Intl.DateTimeFormat('de-DE', { day: '2-digit', month: 'short', year: 'numeric' })`.
      Bei `null` oder unparsebarem Wert `null` zurückgeben. **Kein** hand-gebauter Monatsname.
- [x] `knowledge-detail-dialog.html` Zeile 66: die Sub-Zeile um `@if (updatedLabel(); as label)`
      erweitern — `· aktualisiert {{ label }}`.

### Docs

- [x] `docs/models.md`: `updated_at` beim Entity-Kontrakt ergänzen, mit dem Hinweis, dass er aus
      der Dateizeit stammt und nicht persistiert wird.

## Report-Back

**Umsetzung wie geplant, keine Abweichungen.** `updated_at_for(entity, domain=None)` in
`knowledge/service.py` folgt exakt dem Muster von `completeness_for` (gleiches Domänen-Memo,
gleiche Signatur-Form) — `Vault.entity_path` + `path.stat().st_mtime`, `OSError` (deckt
`FileNotFoundError` mit ab) → `None`. Alle 7 direkten `EntityDto.from_entity`-Aufrufstellen
und beide `LoreDto.from_lore`-Aufrufstellen in `api/knowledge.py` bekamen den dritten Parameter
— keine vergessen, per Grep vor Abschluss gegengeprüft.

**Konfidenz:** hoch, keine wacklige Stelle. Backend-Tests (2 neu, `test_knowledge_service.py`)
und die volle Suite (`test_knowledge_service.py` + `test_knowledge_api.py`, 59 grün) laufen
durch, `ruff check` auf den geänderten Dateien sauber, `npm run lint`/`npm run build` grün
(Bundle-Budget-Warnungen sind Vorbelastung, unverändert von dieser Phase).

Dateien: `backend/photofant/api/knowledge.py`, `backend/photofant/knowledge/service.py`,
`backend/tests/test_knowledge_service.py`, `frontend/src/app/models/knowledge.model.ts`,
`frontend/src/app/features/wissen/knowledge-detail-dialog/knowledge-detail-dialog.ts`,
`frontend/src/app/features/wissen/knowledge-detail-dialog/knowledge-detail-dialog.html`,
`docs/models.md`.
