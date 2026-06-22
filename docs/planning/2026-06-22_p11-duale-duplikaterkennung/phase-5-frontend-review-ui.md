# Phase 5 — Frontend-Review-UI

**Tier:** standard  
**Status:** pending

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/review/review-dupes/dupe-pair-row/dupe-pair-row.ts` + `.html` + `.scss`
- `frontend/src/app/features/review/review-dupes/dupe-compare/dupe-compare.ts` + `.html` + `.scss`
- `frontend/src/app/features/personen/dupe-check-dialog/dupe-check-dialog.html`
- `@photofant/models` — `PersonDupePair`-Interface (wo definiert?)
- `frontend/src/app/models/` — Frontend-seitige DTOs für Review-Items prüfen
- Kontrakt-Sektion in README — `PersonDupePair` und `DupePairResponse`-Typen
- Phase 3 + 4 müssen abgeschlossen sein

---

## Abnahme-Kriterien

- [ ] `dupe-pair-row` zeigt bei einem Paar, das nur per CLIP gefunden wurde, „CLIP: 87 % ähnlich" — und kein DHash-Balken
- [ ] `dupe-pair-row` zeigt bei einem Paar, das von beiden erkannt wurde, beide Scores untereinander
- [ ] `dupe-compare` (Lightbox-Modal) zeigt in der Kopfzeile den höchsten Score und darunter eine Zeile pro Methode die getriggert hat
- [ ] `dupe-check-dialog` (Person-Duplikate) zeigt analog beide Scores pro Paar
- [ ] Labels erklären die Methode ohne Fachbegriff: „Pixel-Ähnlichkeit" statt „DHash", „Inhalts-Ähnlichkeit" statt „CLIP"
- [ ] Frontend-Typen `PersonDupePair` und das Review-DTO sind mit dem API-Kontrakt aus Phase 3 synchron
- [ ] Fehlende Scores (null) werden nicht als „0 %" dargestellt — sie werden ausgeblendet

---

## Checkliste

### Modell-Typen aktualisieren

- [ ] `PersonDupePair` (in `@photofant/models`) erweitern:
  ```typescript
  phash_distance:       number | null
  phash_similarity_pct: number | null
  clip_distance:        number | null
  clip_similarity_pct:  number | null
  triggered_by:         'phash' | 'clip' | 'both'
  ```
- [ ] Review-DTO (Frontend-seitiges Interface für `/review/dupes`) analog erweitern
- [ ] Prüfen ob `similarity_pct` an irgendeiner Stelle noch als einzige Zahl erwartet wird → anpassen

### dupe-pair-row

- [ ] Scores-Block ersetzen — statt einer Ähnlichkeits-Zeile: bedingte Blöcke:
  ```html
  @if (pair.phash_similarity_pct !== null) {
    <div class="dupe-pair-row__score">
      <span class="dupe-pair-row__score-label">Pixel-Ähnlichkeit</span>
      <span class="dupe-pair-row__score-value">{{ pair.phash_similarity_pct }} %</span>
    </div>
  }
  @if (pair.clip_similarity_pct !== null) {
    <div class="dupe-pair-row__score">
      <span class="dupe-pair-row__score-label">Inhalts-Ähnlichkeit</span>
      <span class="dupe-pair-row__score-value">{{ pair.clip_similarity_pct }} %</span>
    </div>
  }
  ```
- [ ] SCSS — `dupe-pair-row__score` und `dupe-pair-row__score-label/-value` stylen (kompakt, nicht dominant)

### dupe-compare

- [ ] Kopfzeile: Hauptzahl = `max(phash_similarity_pct, clip_similarity_pct)` (ohne null)
- [ ] Unter der Hauptzahl: je eine Label-Zeile pro aktiver Methode:
  ```
  Pixel: 94 %   ·   Inhalt: 88 %
  ```
  Oder wenn nur eine Methode: nur diese anzeigen
- [ ] `similarity()` Signal in `dupe-compare.ts` auf `max(...)` anpassen

### dupe-check-dialog

- [ ] `dupe-check-dialog.html` — Score-Block pro Paar analog `dupe-pair-row` (beide Methoden, konditionell)
- [ ] Prozentzahl-Balken (`dupe-check-dialog__score-fill`) auf höchsten Score zeigen

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
