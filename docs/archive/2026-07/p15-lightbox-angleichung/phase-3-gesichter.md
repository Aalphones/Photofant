# Phase 3 — Gesichter-Redesign + PersonPicker-Modal

**Tier:** standard
**Status:** complete

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/galerie/lightbox/lightbox.html` — Gesichter-Block ab Zeile ~257
- `frontend/src/app/features/galerie/lightbox/lightbox.ts` — `toggleFaceMatches()`, `assignFaceToPerson()`
- `docs/design/js/detail.jsx` — `Section "Gesichter"` + `PersonPicker`-Komponente (ab Zeile ~141)
- `docs/design/styles.css` — `.face-item`, `.face-thumb`, `.face-name-ed`, `.quick-assign`, `.op-scrim`, `.op-modal`, `.pp-modal`

---

## Abnahme-Kriterien

- [x] Gesichter-Sektion liegt nach Caption + Tags, VOR Versionen
- [x] Jede Gesicht-Zeile: Crop-Thumbnail + Personenname + Pencil-Icon + Score/Alter
- [x] Manuelle Zuordnungen bekommen grünen Rahmen (automatisch: Akzent-Rahmen)
- [x] Quick-Assign-Grid: bis zu 5 Top-Matches als Thumbnail-Buttons mit Vorname + Score
- [x] „Weitere Personen…"-Button öffnet PersonPicker-Modal
- [x] PersonPicker-Modal: Scrim + Modal mit Suchfeld + Quick-Top5 + vollständige scrollbare Liste
- [x] PersonPicker-Modal liegt **über** der Lightbox (z-index korrekt, Mockup-Bug behoben)
- [x] Gesicht löschen: Trash-Button in jeder Gesicht-Zeile (direkt, kein extra Panel)
- [x] **„Neue Person anlegen" vollständig im PersonPicker-Modal enthalten** — Button immer sichtbar,
  klappt zu Inline-Input (Name eingeben → Bestätigen / Abbrechen), legt Person an und weist
  Gesicht direkt zu. Bestehende Logik aus `lightbox.ts` bleibt 1:1 erhalten, nur Renderort wechselt.

---

## Checkliste

### Gesicht-Zeilen-Layout (Mockup: `face-item ed-row`)

- [x] Template-Umbau: statt `face-thumb`-Buttons neues `.face-item`-Layout:
  ```html
  <div class="face-item" @for face>
    <div class="face-crop">
      <img [src]="'/api/faces/' + face.id + '/thumbnail'" />
      <div class="face-crop__border" [class.manual]="isFaceManual(face)"></div>
      <button class="face-del" (click)="deleteFaceFromAsset(face)">×</button>
    </div>
    <div class="face-info" (click)="openPersonPicker(face)">
      <span class="face-name">{{ faceLabel(face) }}</span>
      <pf-icon name="pencil" [size]="11" />
    </div>
    <div class="face-score">{{ faceScore(face) }} · {{ faceAge(face) }}</div>
  </div>
  ```
- [x] `isFaceManual(face)` computed/helper — origin === 'manual' o.ä. (prüfen was Backend liefert)
- [x] Sections-Reihenfolge im HTML anpassen: Gesichter nach Tags, vor Versionen

### Quick-Assign-Grid

- [x] Signal `quickMatches = signal<FaceMatch[]>([])` — Top-5 der `faceMatches()`, auto-geladen
  wenn `selectedFace()` gesetzt
- [x] Grid-Template (5 Spalten):
  ```html
  <div class="quick-assign">
    @for (match of quickMatches().slice(0, 5); track match.person_id) {
      <button class="quick-match" (click)="assignFaceToPerson(selectedFace()!.id, match.person_id)">
        <img [src]="'/api/faces/' + match.best_face_id + '/thumbnail'" />
        <div class="qm-name">{{ firstName(match.person_name) }}</div>
        <div class="qm-score">{{ matchScorePercent(match.score) }}%</div>
      </button>
    }
  </div>
  ```
- [x] `firstName(name)`: gibt erstes Wort zurück (`name?.split(' ')[0] ?? '?'`)

### PersonPicker-Modal

- [x] `showPersonPicker = signal(false)` — separates Signal von `selectedFace`
- [x] `openPersonPicker(face)` setzt `selectedFace` + `showPersonPicker(true)` + lädt Matches
- [x] Modal-Template als `@if (showPersonPicker())` **außerhalb** von `.lb` (Scrim auf root-Ebene)
  ```html
  <!-- Außerhalb <div class="lb"> im Template -->
  @if (showPersonPicker()) {
    <div class="pp-scrim" (click)="closePersonPicker()">
      <div class="pp-modal" (click)="$event.stopPropagation()">
        <!-- Kopf, Suche, Top5, Liste, Neue Person -->
      </div>
    </div>
  }
  ```
- [x] SCSS: `.pp-scrim` z-index > `.lb` z-index (Lightbox ist z.B. 100, Modal muss > 100 sein)
  🟡 Aktuellen z-index der Lightbox prüfen — Modal-Scrim auf `z-index: 200` oder darüber
- [x] Such-Input lädt aus `personSearchResults()` (bereits vorhanden in lightbox.ts)
- [x] Top-5 Quick-Section im Modal: `faceMatches().slice(0, 5)` als Avatar-Chips
- [x] **„Neue Person anlegen" bleibt vollständig erhalten** — die Funktion ist im aktuellen Code
  (`startCreatePerson` / `confirmCreatePerson` / `cancelCreatePerson` / `onNewPersonKeyDown`)
  implementiert und muss 1:1 ins neue Modal übernommen werden. Sie ist der einzige Weg, eine
  noch nicht bekannte Person anzulegen — darf unter keinen Umständen beim Umbau verloren gehen.
  - Anzeige: `@if (creatingNewPerson())` zeigt Inline-Input + Bestätigen + Abbrechen
  - `@else`: „Neue Person anlegen"-Button ist immer im Modal sichtbar (unterhalb der Ergebnisliste)
  - Verhalten nach Bestätigung: Person anlegen → sofort als Gesicht zuweisen → Modal schließen
  - Alle vier Handler bleiben in `lightbox.ts` unverändert; nur der Rendering-Ort wechselt
    (von inline-expanded-Panel → ins PersonPicker-Modal)
- [x] `closePersonPicker()`: `showPersonPicker(false)`, `selectedFace(null)`, `faceMatches([])`,
  `creatingNewPerson(false)`, `newPersonName('')`

---

## Report-Back

**Abweichungen von der Checkliste (bewusst, mit Begründung):**

- **Quick-Assign-Grid entkoppelt von `selectedFace`:** Die Checkliste wollte `quickMatches`
  aus `faceMatches()` ableiten, geladen "wenn `selectedFace()` gesetzt". Das kollidiert aber
  mit dem Modal: `openPersonPicker(face)` setzt `selectedFace` für JEDES angeklickte Gesicht,
  nicht nur für Gesicht 1 — dann würde das Panel-Grid plötzlich Matches für Gesicht 3 zeigen,
  während der Nutzer eigentlich das Modal für Gesicht 3 vor sich hat. Stattdessen: eigenes Signal
  `quickAssignMatches`, per Effect an `firstFace()` gekoppelt (lädt automatisch neu, sobald sich
  das erste erkannte Gesicht ändert — Navigation oder erfolgreiche Zuweisung). Verhält sich wie im
  Mockup (`topMatches` zielt dort ebenfalls hart auf Gesicht 0), ist aber sauber von der
  Modal-Auswahl getrennt. `selectedFace` + `faceMatches` gehören jetzt ausschließlich dem
  PersonPicker-Modal.
- **PersonPicker-Liste zeigt volles Personenverzeichnis, nicht nur Suchtreffer:** Die
  Checkliste nannte nur `personSearchResults()`; die Abnahme-Kriterien in der README verlangen
  aber explizit eine „vollständige scrollbare Liste". Neues Computed `personDirectory` (alle
  bekannten Personen ohne „unbekannt") wird gezeigt, solange keine Sucheingabe steht;
  `personSearchResults()` übernimmt nur bei aktiver Eingabe.
- **Kein „Unbekannt"-Eintrag im Modal:** Das Mockup hat einen Sentinel-Wert (`personId === -1`)
  für unzugeordnete Gesichter — im echten Datenmodell gibt es kein Äquivalent und die
  Phase-3-AK verlangt ihn nicht. Weggelassen.

**Sonst 1:1 nach Checkliste umgesetzt:** Alte inline-expandierende Matches-Liste komplett entfernt,
`toggleFaceMatches()` durch `openPersonPicker()`/`closePersonPicker()` ersetzt (kein anderer
Aufrufer betroffen — geprüft, `face-lightbox` hat eigene, unabhängige Implementierung).
`ng build` lokal grün, `tsc --noEmit` sauber.
