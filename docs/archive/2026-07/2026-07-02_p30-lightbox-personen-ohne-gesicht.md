# P30 — Lightbox: Person zuordnen ohne extrahiertes Gesicht

**Ziel:** Bilder, bei denen kein Gesicht extrahiert wurde (z.B. Hinterkopf, Gruppe zu weit weg, gescheiterte Extraktion), sind in der Lightbox aktuell eine Sackgasse — die ganze Gesichter-Sektion verschwindet kommentarlos, keine Person zuordenbar. Neu: bei `faces().length === 0` zwei Buttons —
„Extrahieren nochmal probieren" (Face-Klassifizierung für dieses eine Bild neu anstoßen) und
„Manuell Person zuordnen" (bestehender Personen-Picker, aber ohne Top-Treffer-Spalte, mit Suche/Zuweisen/Neuanlegen).

**Zusätzlich (Nachtrag):** Ein bereits einer Person zugeordnetes Gesicht lässt sich aktuell nicht zurück auf „Unbekannt" setzen — bei einer Falschzuordnung bleibt nur Löschen. Neuer, eigenständiger Button im bestehenden Picker (nur im Face-Kontext sichtbar): „Als unbekannt markieren".

**Kein Mockup vorhanden** für diesen Empty-State (`docs/design/js/detail.jsx` kennt nur den Fall mit Faces) — freihändig nach der Spezifikation des Users gebaut (exakter Wortlaut der beiden Buttons + ihr Verhalten kam von ihm), keine Rückfrage nötig.

| Phase | Inhalt | Tier | Status |
|---|---|---|---|
| 1 | Backend: Endpoint „Person direkt einem Asset zuordnen" | standard | complete |
| 2 | Frontend: Lightbox-Empty-State + Picker-Wiederverwendung + Unbekannt-Korrektur | standard | complete |

## Kontrakt (Backend ↔ Frontend)

```
PATCH /api/assets/{asset_id}/assign-person
Body:     { "person_id": number }
Response: { "asset_id": number, "person_id": number, "instance_id": number }
404 — Asset oder Person nicht gefunden
500 — physische Zuordnung fehlgeschlagen (Datei fehlt/IO-Fehler, siehe materialize_assignment)
```

Frontend ruft das über eine neue Methode `assignPersonToAsset(assetId, personId)` in `person.service.ts` auf.

## Chesterton's Fence — was wiederverwendet wird

- `materialize_assignment(session, asset_id, person_id, data_root, fixed=True)` (`backend/photofant/media/person_folders.py:236`) macht bereits alles Nötige: legt eine `AssetInstance` an oder verschiebt/kopiert die vorhandene Datei in den Zielordner der Person, setzt `fixed_person`. Wird heute nur aus `reassign_face()` heraus aufgerufen (nachdem eine Face-Zeile umgehängt wurde) — funktioniert aber unabhängig von Faces, weil `AssetInstance` keine Face-Referenz braucht. Für ein Asset ohne jedes Face liegt es aktuell in der `_unknown`-Person; `materialize_assignment` erkennt das (`real_instance_count == 0`, keine verbleibenden `_unknown`-Faces) und **verschiebt** die bestehende Instanz statt sie zu duplizieren — kein Sonderfall nötig.
- `classifyService.rerun({ asset_ids, steps })` (Frontend) / `POST /api/classify/rerun` (Backend, `steps` akzeptiert `"faces"`) — bereits bild-genau nutzbar, kein Backend-Task hier.
- Der Personen-Picker in der Lightbox (`showPersonPicker`, `faceMatches`, `pickerList`, `personSearchQuery`, `assignFaceToPerson()`, `startCreatePerson()`/`confirmCreatePerson()`) — die Top-Treffer-Spalte hängt bereits an `faceMatches().length > 0`; bleibt `faceMatches` leer (kein Face zum Matchen), fällt sie automatisch weg. Keine zweite Dialog-Komponente nötig.
- **„Unbekannt" ist bereits ein normaler `Person`-Datensatz** (`is_unknown = true`), und `PATCH /api/faces/{face_id}/assign` (`assign_face` → `reassign_face`) akzeptiert **jede** Ziel-Person, inklusive der Unbekannt-Person — das ist heute schon der Mechanismus, den die Review-Queue für „Ablehnen" nutzt (`api/review_queue.py` → `resolve_face_review(action="reject")` → `reassign_face(..., unknown_person.id, ...)`). Der Picker filtert `is_unknown`-Personen aber bewusst aus Suche/Directory raus (`lightbox.ts:326`, `:332` — richtig so, „Unbekannt" soll nicht durchsuchbar in der Namensliste auftauchen). **Kein Backend-Task** — reine Frontend-Ergänzung: eigener, klar abgesetzter Button statt Aufnahme in die Trefferliste (Vorbild: `review-faces.ts` `onReject()`).

## Phase 1 — Backend: Endpoint ✅

**Kontext:** `backend/photofant/api/faces.py:515` (`assign_face`, Vorbild für Struktur/Fehlerbehandlung) · `backend/photofant/media/person_folders.py:236` (`materialize_assignment`) · `backend/photofant/api/assets.py` (Ziel-Datei, hat `Asset`/`Person`/`AssetInstance`-Imports bereits).

**AK:**
- [x] `PATCH /api/assets/{asset_id}/assign-person` in `api/assets.py`, DTOs `AssignPersonRequest{person_id: int}` / `AssetPersonAssignResultDto{asset_id, person_id, instance_id}`
- [x] 404 bei unbekanntem Asset oder Person; 500 mit Klartext-Detail wenn `materialize_assignment` `None` liefert
- [x] Erfolgsfall: `session.commit()`, danach `enqueue_reevaluate_assets([asset_id])` (Smart-Alben aktualisieren, analog `assign_face`)
- [x] `person.service.ts`: neue Methode `assignPersonToAsset(assetId: number, personId: number)`
- [x] ADR-016 (`docs/decisions/016-manuelle-personen-zuordnung-ohne-gesicht.md`): Entscheidung „physische Kopie/Move wie bei Face-Zuordnung, über `materialize_assignment` wiederverwendet" statt schlankem DB-only-Tag — Kontext/Optionen/Konsequenzen, 10 Zeilen
- [x] `docs/routes.md`: neuer Endpoint-Eintrag bei den Asset-Routen
- [x] `docs/code-map.md`: Zeile „Personen & Faces" bzw. „Galerie & Lightbox" ergänzen falls die neue Route dort noch fehlt

## Phase 2 — Frontend: Lightbox-Empty-State + Picker ✅

**Kontext:** `frontend/src/app/features/galerie/lightbox/lightbox.ts` (Gesichter-Sektion, aktuell nur gerendert wenn `faces().length > 0`; `openPersonPicker(face)`, `selectedFaceId()!`, `assignFaceToPerson()`, `openRerunDialog()`/`onRerunConfirm()` als Vorbild für den Rerun-Call) · `lightbox.html` (`panel-sec` „Aktionen"-Block, Picker-Modal ab Zeile ~576) · `services/classify.service.ts`, `services/person.service.ts`.

**AK:**
- [x] `@else`-Zweig in der Gesichter-Sektion wenn `faces().length === 0`: zwei Buttons, Label exakt „Extrahieren nochmal probieren" und „Manuell Person zuordnen" (Idiotensicherheits-Gate: beide Labels sind bereits selbsterklärend, kein Tooltip nötig)
- [x] „Extrahieren nochmal probieren" → neue Methode, ruft `classifyService.rerun({ asset_ids: [assetId], steps: ['faces'] })` **direkt** auf (kein Rerun-Dialog mit Preset-Auswahl dazwischen — nur dieser eine Step, kein Nutzer-Entscheid nötig); sichtbares Feedback (Pending-State/Toast), Job läuft asynchron im Hintergrund weiter
- [x] „Manuell Person zuordnen" → öffnet den bestehenden Picker im „Asset-Modus": `selectedFace` bleibt `null`, `faceMatches` bleibt leer (→ Top-Treffer-Spalte blendet sich von selbst aus), Suche/Liste/„Neue Person anlegen" bleiben nutzbar
- [x] Zuweisungs-Pfad im Picker vereinheitlichen: ein Handler statt der drei Template-Stellen mit `assignFaceToPerson(selectedFaceId()!, ...)` — verzweigt intern auf Face-Reassign (bestehend) vs. `personService.assignPersonToAsset(assetId, personId)` (neu), je nachdem ob ein Face im Kontext ist. Nimmt dabei das bestehende `!` (Non-Null-Assertion) aus dem Template raus.
- [x] Nach erfolgreichem `assignPersonToAsset`: Picker schließen, Asset-Detail neu laden (Person-Zuordnung muss sichtbar werden, auch ohne Face)
- [x] „Neue Person anlegen" im Asset-Modus nutzt denselben bestehenden Inline-Flow der Lightbox (`startCreatePerson`/`confirmCreatePerson`) — **keine** Vereinheitlichung mit der separaten `create-person-dialog`-Komponente aus der Personen-Seite in diesem Plan (🟡 bestehende Doppelung, kein neuer Scope hier)
- [x] Neuer Computed `unknownPerson = computed(() => this.allPersons().find(p => p.is_unknown) ?? null)` (Vorbild: `review-unknown.ts:30`)
- [x] Picker zeigt **nur im Face-Kontext** (also beim Öffnen über ein bestehendes Gesicht, nicht im Asset-Modus aus Phase 2 oben) einen eigenständigen Button „Als unbekannt markieren" — getrennt von der Such-/Trefferliste, ruft den vereinheitlichten Assign-Handler mit `unknownPerson()!.id` auf; kein Vorschau-/Bestätigungsschritt nötig (eine Aktion, ein Klick, jederzeit über den Picker erneut korrigierbar)
- [x] Deckt den Use-Case „Person wurde falsch zugewiesen, zurück auf Unbekannt setzen" ab, ohne dass das Gesicht gelöscht werden muss

## Summary

Assets ohne extrahiertes Gesicht sind in der Lightbox keine Sackgasse mehr: Re-Extraktion
oder manuelle Personen-Zuordnung direkt anstoßbar. Zusätzlich lässt sich eine
Fehlzuordnung im Picker jetzt per Klick auf „Unbekannt" zurücksetzen, ohne das Gesicht
zu löschen.

## Files touched

- `backend/photofant/api/assets.py` — `PATCH /api/assets/{asset_id}/assign-person`
- `backend/photofant/media/person_folders.py` — wiederverwendet (`materialize_assignment`), unverändert
- `frontend/src/app/services/person.service.ts` — `assignPersonToAsset()`
- `frontend/src/app/features/galerie/lightbox/lightbox.ts` — Empty-State, vereinheitlichter Assign-Handler, Retry-Extraktion, Unbekannt-Korrektur
- `frontend/src/app/features/galerie/lightbox/lightbox.html` — Empty-State-Buttons, Picker-Markup
- `frontend/src/app/features/galerie/lightbox/lightbox.scss` — Styles für Empty-State + Unbekannt-Button
- `docs/decisions/016-manuelle-personen-zuordnung-ohne-gesicht.md`, `docs/routes.md`

## Commits

- `9786c89` feat(personen): Endpoint fuer manuelle Personen-Zuordnung ohne Gesicht (Phase 1)
- `800c9ee` feat(lightbox): Personenzuordnung ohne Gesicht + Unbekannt-Korrektur im Picker (Phase 2)

## Deviations from plan

Keine.

## Follow-ups

- 🟡 Bestehende Doppelung zwischen dem Inline-„Neue Person"-Flow der Lightbox und der
  separaten `create-person-dialog`-Komponente der Personen-Seite — bewusst nicht
  vereinheitlicht (kein Scope dieses Plans).
