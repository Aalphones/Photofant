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

- [x] In `_resolve_media_refs` (`knowledge.py`): ist mindestens eine Person in
      `media_links.persons`, zusätzlich deren erkannte Fotos (Query über `AssetInstance`,
      analog dem `person_id`-Filter in `assets.py`) als `kind="asset"`-`MediaRefDto` anhängen,
      dedupliziert gegen `media_links.assets` — neue Helper `_combined_photo_asset_ids`
      vereinigt beide Quellen als Set, sortiert neueste zuerst
      (`func.coalesce(Asset.created_at, Asset.imported_at)`, dasselbe Muster wie die Galerie).
- [x] Obergrenze + Gesamtzahl eingebaut: `_MAX_RELATED_PHOTOS = 24` (neueste zuerst), neues
      `LoreDto.related_photos_total` trägt die ungedeckelte Gesamtzahl — Konvention `items` +
      `total` aus `AssetsPage` (`assets.py`) übernommen statt neu erfunden.
- [x] Test: Person mit 3 erkannten Fotos, 0 manuell verknüpften Assets → `related_media` enthält
      alle 3 als `kind=asset` (`test_lore_includes_recognized_photos_of_linked_person`).
- [x] Test: Person ohne ein einziges erkanntes Foto, aber mit einem manuell verknüpften Asset →
      `related_media` enthält weiterhin genau das eine
      (`test_lore_keeps_manual_asset_when_person_has_no_recognized_photos`).
- [x] Test: Person mit mehr Fotos als die Obergrenze → Liste ist gedeckelt, Zähler stimmt
      (`test_lore_caps_recognized_photos_and_reports_total`, 30 Fotos → 24 gezeigt, `total=30`,
      geprüft auch, dass es wirklich die neuesten 24 sind).

### Frontend

- [x] `relatedPhotos()` unverändert (Backend liefert schon eine fertige, gedeckelte Liste).
      Neuer Computed `relatedPhotosOverflow()` zeigt „und N weitere" unter dem Foto-Grid, wenn
      `related_photos_total` über der gezeigten Anzahl liegt. Album-Button (Phase 6) bleibt
      unverändert, liest weiterhin `relatedPhotos()`.

### Docs

- [x] `docs/routes.md`: `LoreDto`-Beschreibung um `related_photos_total` und die
      Live-Foto-Erweiterung ergänzt.

## Report-Back

Backend liest jetzt live die Fotos der verknüpften Person(en) aus `AssetInstance` und mischt
sie dedupliziert mit manuell verknüpften Assets — neueste 24 zuerst, Rest über
`related_photos_total` gezählt. Nichts davon landet in der Vault-Markdown (bewusste Ausnahme,
README-Begründung). Frontend zeigt bei Überhang „und N weitere" unter dem Foto-Grid; Album-Button
aus Phase 6 läuft unverändert weiter, weil er weiterhin nur `relatedPhotos()` liest.

**Kein Grund gefunden, der gegen "live lesen statt spiegeln" spricht** — die Query ist ein
einzelner, indizierter Join (kein Vollscan), keine FINDINGS-Eintrag nötig.

**Konfidenz:** Deckel von 24 ist wie im Plan angemerkt eine Startgröße, keine gemessene — Rest
unverändert seit dem Konfidenz-Ausweis im README.
