# FINDINGS — P21 Galerie-Stapel & Tab-Konsolidierung

Format: `- [ ] → Phase N: <Erkenntnis / Abweichung / Folgefund>`

<!-- Einträge werden während der Umsetzung von mode-implementing eingepflegt -->

- [x] → Phase 1: ComfyUI-Default-Import legte bisher immer eine `Version`, nie ein Asset an —
  Kontrakt-Annahme "original_id-Kinder laufen schon durch die Pipeline" war falsch.
  Korrigiert via ADR-013 (siehe README + phase-1 Update). Wird in Phase 1 selbst gebaut.
- [ ] → Phase 2/3: Galerie-Grid muss beachten, dass frisch umgestellte ComfyUI-Edits jetzt
  als vollwertige Asset-Kacheln erscheinen (nicht mehr im `edits`-Tab-Modell), inkl. eigener
  Tags/Caption/Faces sichtbar in der Detailansicht — keine Sonderbehandlung nötig, aber beim
  Testen im Blick behalten.
- [x] → Phase 2/3: `AssetDto`/`FaceGalleryItemDto` liefern jetzt `kind: "asset"|"version"|"face"`
  + `version_id`. Frontend muss die Thumbnail-URL danach wählen: `kind==="version"` →
  `/api/versions/{version_id}/thumbnail`, sonst `/api/assets/{id}/thumbnail` bzw.
  `/api/faces/{id}/thumbnail`. Stapel-Icon zeigen, wenn `stack_size > 1`.
  Eingearbeitet in Phase 2 für den Fotos-Tab.

- [x] → Phase 2 (kritisch, während Umsetzung entdeckt): `AssetDto.id` ist bei
  Version-Pseudo-Einträgen (`kind==='version'`) **identisch** mit der `id` des
  Originals — die NgRx-EntityAdapter-Map im `gallery`-Slice nutzte bisher `asset.id`
  als Key, was Original und seine Editor-Versionen gegenseitig überschrieben hätte
  (nur die zuletzt geladene Zeile hätte überlebt → Stapel-AK „N+1 Kacheln" wäre
  gebrochen). Behoben: Entity-Key ist jetzt `String(id)` für `kind==='asset'`,
  `` `v${version_id}` `` für `kind==='version'` (`gallery.reducer.ts`). **Bekannte
  Einschränkung:** `onRangeSelect`/`selectGroups` scannen weiterhin nach `.id`
  (Business-Feld, nicht Entity-Key) — wenn eine Version-Kachel und ihr Original
  gleichzeitig sichtbar sind, kann `findIndex` bei Shift-Klick-Rangeauswahl die
  falsche Grenze treffen (Edge Case, dokumentierter Kompromiss analog zum
  Backend-„single-hop"-Kompromiss aus Phase 1).

- [ ] → Phase 5 (ADR-012): Es gibt **keinen** Backend-Endpunkt, der Favorit/Löschen
  gezielt auf einer `version`-Zeile setzt (nur auf dem Original-Asset). Version-
  Pseudo-Einträge im Fotos-Grid haben deshalb in Phase 2 **kein** Auswählen/Favorit
  bekommen (Cell zeigt nur Stapel-Icon + Klick-zum-Öffnen) — sonst hätte ein Klick
  versehentlich das Original getroffen. Muss in ADR-012 als bewusste Entscheidung
  festgehalten werden: entweder Backend-Endpunkt für Version-Favorit/-Löschen
  nachziehen, oder das „jeder Eintrag ist ein eigenständiges Auswahl-Ziel"-AK aus
  dem README für `kind==='version'` explizit einschränken.

- [x] → Phase 2/3: `face-grid.html`s `@for`-Track lief auf `face.id` — Backend vergibt
  Version-Pseudo-Einträgen (Face-Edits) dieselbe `id` wie ihrem zugehörigen Face
  (`faces.py`: `id=face.id` in beiden Zweigen). Mehrere Stapel-Mitglieder hätten denselben
  Track-Key gehabt → Angular hätte DOM-Knoten falsch wiederverwendet (analog zum
  Entity-Key-Fund aus Phase 2 für `AssetDto`). Behoben in Phase 3: Track-Funktion nutzt
  `versionId != null ? 'v'+versionId : 'f'+id`.

- [x] → Phase 4 (Lightbox-Anbindung, kritisch): Widerspruch zwischen dieser Notiz (Phase 4
  soll nur das `item.id`-Matching in der *alten* separaten Gesichter-Lightbox fixen) und
  der Phase-4-Datei selbst (verlangt Umstieg auf den *neuen* Gesichter-Modus). Per
  Rückfrage an den User aufgelöst: voll auf den neuen Gesichter-Modus umgestellt, alte
  `face-lightbox/`-Komponente entfernt, fehlende Fähigkeiten (Person zuweisen, Gesicht
  löschen, Explorer-Reveal, Vor/Zurück durch alle Gesichter) dort nachgebaut. Details:
  Report-Back Phase 4.

- [ ] → Phase 5 (ADR-012): `ng build --configuration production` schlägt an einem
  CSS-Budget-Fehler in `lightbox.scss` (23.32 kB, Error-Schwelle 16 kB) fehl. Bereits vor
  Phase 4 vorhanden (Wachstum über P15 hinweg), keine Regression dieser Phase — aber bisher
  nirgends dokumentiert oder behoben. Phase 5 sollte entscheiden: Budget in `angular.json`
  anheben (einfachster Weg) oder `lightbox.scss` aufteilen.

- [ ] → Phase 5 (ADR-012, verschoben aus Phase 4 — nicht Teil der Phase-4-Checkliste,
  weiterhin offen): Die Workflow-Run-Leiste hatte bisher einen
  Weg, eine Editor-Version direkt als ComfyUI-Input zu binden (`onBindVersion` im
  jetzt entfernten Edits-Tab, `pf-version-cell` → Bind-Klick). Mit dem Wegfall des
  Edits-Tabs gibt es **keinen** UI-Einstiegspunkt mehr dafür — `versionSlotBindings`
  in `galerie.ts` bleibt verdrahtet (Run-Leiste zeigt/verarbeitet Version-Bindings
  weiterhin), wird aber nie mehr befüllt. Phase 5 sollte prüfen, ob ein Bind-Button
  in der Lightbox-Versionen-Sektion (P15 Phase 4) diese Lücke schließen soll, oder
  ob die Version-Bindung als Workflow-Input ersatzlos entfällt (Kontrakt-Entscheidung,
  gehört ins README/ADR-012).
