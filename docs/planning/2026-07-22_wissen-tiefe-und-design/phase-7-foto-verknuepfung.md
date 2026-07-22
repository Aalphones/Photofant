# Phase 7 — Fotos: echte Verknüpfung zur Person

**Rating:** standard

Gefunden beim Testen einer Person-Verknüpfung (She-Hulk/Tatiana Maslany): Ist eine Person mit
einer Wissens-Entity verknüpft, bleibt die Sektion „Verknüpfte Fotos" trotzdem leer. Grund:
`link_person_entity` schreibt die Person-ID nur in `media_links.persons` (das Feld, das den
Avatar-Chip füllt) — nie in `media_links.assets` (das Feld, das die Foto-Sektion tatsächlich
zeigt). Es gibt aktuell keinen Weg, wie Fotos dort automatisch hineinkommen; der einzige
Backend-Endpunkt dafür (`assets.py` Zeile 1218) hat keinen einzigen Frontend-Aufrufer.

**Entscheidung für diese Phase:** Fotos werden für personen-verknüpfte Entities nicht in die
Markdown-Datei geschrieben (das würde bei jedem neuen Foto der Person eine Vault-Änderung
auslösen und Hunderte IDs in eine Textdatei duplizieren, die `AssetInstance` schon kennt).
Stattdessen liest `get_lore` sie **live** nach demselben Muster, das die Personen-Galerie schon
nutzt (Fotos, auf denen die Person erkannt wurde). `media_links.assets` bleibt daneben bestehen
für Fälle ohne Person (z.B. eine reine Notiz, der man einzelne Fotos manuell zuordnet).

## Kontext — das musst du lesen

- `backend/photofant/api/knowledge.py` → `_resolve_media_refs` (Zeile 367-395), `get_lore`
  (Zeile 577).
- `backend/photofant/knowledge/service.py` → `get_lore` (Zeile 377), `Lore`-Dataclass
  (Zeile 97-113, insb. Kommentar zu `related_media`).
- `backend/photofant/api/assets.py` Zeile 616-633 — das bestehende Muster „Fotos dieser
  Person" (`AssetInstance.person_id`-Filter), das die Personen-Galerie schon verwendet.
  **Wiederverwenden, nicht neu erfinden.**
- `backend/photofant/api/persons.py` → `link_person_entity` (Zeile 352), Zeile 365
  (`link_media`-Aufruf — schreibt bewusst nur `media_links.persons`, das bleibt so).
- `backend/photofant/db/models.py` → `AssetInstance`.
- `frontend/src/app/features/wissen/knowledge-detail-dialog/knowledge-detail-dialog.ts` →
  `relatedPhotos` (Zeile 235) — bleibt die gemeinsame Quelle für Phase 6 (Album-Button), hier
  vermutlich unverändert, wenn das Backend schon eine fertige, gedeckelte Liste liefert.
- `docs/routes.md` — Beschreibung der `lore`-Route.

## AK dieser Phase

1. Eine mit einer Wissens-Entity verknüpfte Person zeigt im Detail-Dialog unter „Verknüpfte
   Fotos" die Fotos, auf denen sie erkannt wurde — ohne dass jemand sie einzeln verknüpfen muss.
2. Manuell verknüpfte Fotos (`media_links.assets`, z.B. bei einer personenlosen Notiz) bleiben
   zusätzlich möglich; das Ergebnis ist die deduplizierte Vereinigung beider Quellen.
3. Bei sehr vielen Fotos (hunderte) bläht sich der Dialog nicht auf — eine sinnvolle Obergrenze
   (z.B. die neuesten 24) plus ein Hinweis „und N weitere"; die vollständige Liste bleibt der
   Personen-Galerie vorbehalten.
4. Phase 6 Teil A (Album-Button) funktioniert mit diesen Fotos ohne eigene Anpassung —
   `relatedPhotos()` bleibt die einzige Quelle, die dort gelesen wird.
5. `cd backend && uv run ruff check .` und `cd frontend && npm run lint && npm run build`
   sind grün.

## Checkliste

### Backend

- [ ] In `get_lore`/`_resolve_media_refs` (oder einer neuen Helper-Funktion in `knowledge.py`):
      ist mindestens eine Person in `media_links.persons`, zusätzlich deren erkannte Fotos
      (Query analog `assets.py` Zeile 616-633) als `kind="asset"`-`MediaRefDto` anhängen,
      dedupliziert gegen bereits vorhandene `media_links.assets`-Einträge.
- [ ] Obergrenze + Gesamtzahl einbauen (z.B. neueste N, Rest als Zähler). **Nicht raten** — mit
      dem bestehenden Pagination-Muster in `assets.py` abgleichen, ob es dafür schon eine
      Konvention gibt, statt eine neue zu erfinden.
- [ ] Test: Person mit 3 erkannten Fotos, 0 manuell verknüpften Assets → `related_media` enthält
      alle 3 als `kind=asset`.
- [ ] Test: Person ohne ein einziges erkanntes Foto, aber mit einem manuell verknüpften Asset →
      `related_media` enthält weiterhin genau das eine.
- [ ] Test: Person mit mehr Fotos als die Obergrenze → Liste ist gedeckelt, Zähler stimmt.

### Frontend

- [ ] Prüfen, ob `relatedPhotos()` (und der Album-Button aus Phase 6) mit einer eventuellen
      „und N weitere"-Erweiterung im DTO noch klaglos läuft — eigener Code nur, falls das
      Backend nicht schon eine fertige, gedeckelte Liste liefert.

### Docs

- [ ] `docs/routes.md`: Beschreibung von `GET .../lore` ergänzen — `related_media` enthält bei
      `personId` jetzt auch die erkannten Fotos der Person, nicht nur manuell verknüpfte.

## Report-Back
