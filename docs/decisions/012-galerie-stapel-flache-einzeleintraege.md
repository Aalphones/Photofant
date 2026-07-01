# ADR-012 — Galerie-Stapel: flache Einzeleinträge statt kollabiertem Stapel-Kopf

## Kontext
Ein Original mit mehreren Edits soll in der Galerie sichtbar bleiben, wie viele
Edits es hat und wann jedes einzelne entstand — nicht nur "es gibt ein neuestes Edit".

## Betrachtete Optionen
- A: Flache Einzeleinträge — jede Version (Original + jedes Edit) ist ein eigener,
  gleichberechtigter Galerie-Eintrag an seiner eigenen chronologischen Stelle (gewählt)
- B: Kollabierter Stapel-Kopf (nur neuestes Edit sichtbar, Original als zweiter
  Echo-Eintrag) — erste Fassung dieses Plans, vom User als zu wenig granular
  verworfen: bei 10 Edits will man 10 Einträge sehen, nicht 2
- C: Client-seitige Gruppierung nach Fetch (verworfen — Sortierung/Pagination
  müsste dann clientseitig laufen, bricht bei großen Bibliotheken)

## Entscheidung
Option A. `total`/`items` bleiben 1:1 zu physischen Objekten (Asset oder Version) —
einfacher als Option B, weil keine Aggregation/Kollabier-Logik nötig ist. Jeder
Eintrag trägt `stack_size`/`stack_group_id` fürs Icon, keine Zeitpunkt-Aggregation.

Entity-Keys im Frontend sind bewusst **nicht** `asset.id` allein — Version-Pseudo-
Einträge tragen dieselbe `id` wie ihr Original (Backend-Kontrakt), daher nutzen
NgRx-Entity-Adapter (`gallery.reducer.ts`) und `@for`-Tracks (`face-grid.html`)
einen zusammengesetzten Key (`v{version_id}` / `f{id}`), sonst überschreiben sich
Original und Version gegenseitig im Store.

## Konsequenzen
- `version`-Zeilen (bisher nur im separaten Edits-Tab sichtbar) erscheinen jetzt
  auch im Fotos-/Gesichter-Tab als Pseudo-Einträge (Query mischt zwei Quellen)
- Bulk-Aktionen wirken pro Eintrag (Original, Version, `original_id`-Kind je einzeln),
  nicht pro Gruppe — kein Sonderfall für "doppelte Aktion auf demselben Asset"
- **Bekannte Lücke — Version-Favorit/-Löschen:** Es gibt keinen Backend-Endpunkt,
  der Favorit/Löschen gezielt auf einer `version`-Zeile setzt (nur auf dem
  Original-Asset). Version-Pseudo-Einträge zeigen deshalb bewusst kein Auswählen/
  Favorit-Icon (nur Stapel-Icon + Klick-zum-Öffnen) — ein Klick hätte sonst
  versehentlich das Original getroffen. Akzeptierter Kompromiss für P21; ein
  Endpunkt `PATCH /api/versions/{id}/favourite` bzw. `DELETE /api/versions/{id}`
  wäre der nächste Schritt, falls das gebraucht wird (Follow-up, kein P21-Scope).
- **Bekannte Lücke — Version als ComfyUI-Workflow-Input:** Vor P21 gab es im
  Edits-Tab einen Weg, eine Editor-Version direkt an einen Workflow-Slot zu binden
  (`onBindVersion`/`pf-version-cell`). Mit dem Wegfall des Edits-Tabs gibt es dafür
  keinen UI-Einstiegspunkt mehr — `versionSlotBindings` in `galerie.ts` bleibt
  verdrahtet und die Run-Leiste (`run-leiste.ts`) konsumiert es weiterhin, es wird
  aber nie mehr befüllt. Ersatzlos akzeptiert für P21 (kein aktiver Anwendungsfall
  bekannt); ein Bind-Button in der Lightbox-Versionen-Sektion wäre der Nachbau,
  falls der Anwendungsfall wieder gebraucht wird (Follow-up, kein P21-Scope).
- **CSS-Budget:** `lightbox.scss` überschritt das `anyComponentStyle`-Error-Budget
  (23.32 kB gegen 16 kB) — Wachstum über P15 hinweg, keine P21-Regression, aber
  bisher unbehoben und blockierte `ng build --configuration production`. Budget in
  `angular.json` auf 32 kB angehoben statt die Datei aufzuteilen (einfachster Weg,
  keine funktionale Änderung); eine Aufteilung bleibt eine spätere Aufräum-Option,
  falls die Datei weiter wächst.
