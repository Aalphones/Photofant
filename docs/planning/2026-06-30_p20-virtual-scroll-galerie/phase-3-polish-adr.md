# Phase 3 — Polish & ADR

**Komplexität:** standard

## Kontext

- `phase-2-virtual-rendering.md` Report-Back lesen (aufgetauchte Edge-Cases)
- [`frontend/src/app/features/galerie/grid/`](../../../frontend/src/app/features/galerie/grid/) — alle Grid-Files
- `README.md` — Smoke-Checkliste ausführen

## Abnahmekriterien

- ResizeObserver debounced (kein Layout-Thrashing beim Ziehen des Fensters).
- `containerWidth === 0`-Fallback: Grid zeigt Skeleton bis erste Messung, kein Crash.
- ADR-011 existiert unter `docs/decisions/011-galerie-virtual-scroll.md`.
- Alle Punkte der Smoke-Checkliste grün.

## Checkliste

### Implementierung

- [x] ResizeObserver-Callback per `requestAnimationFrame` debounced:
  ```typescript
  let rafId: number | null = null;
  const ro = new ResizeObserver(([entry]) => {
    if (rafId !== null) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(() => {
      if (entry) containerWidth.set(entry.contentRect.width);
      rafId = null;
    });
  });
  ```
  Cleanup: `cancelAnimationFrame(rafId)` im `destroyRef.onDestroy`.

- [x] `containerWidth === 0`-Guard in `rows`-Computed: `if (containerWidth() === 0) return []` — Virtualizer rendert 0 Items, zeigt nur Skeleton bis erste Messung.

- [x] Edge-Case Viewport-Resize: TanStack behält bei Count-Änderung die Scroll-Position (Offset-basiert, kein Index-Sprung) — geprüft, kein zusätzlicher `scrollToIndex`-Aufruf nötig; Smoke-Checkliste deckt den sichtbaren Fall ab (800px-Viewport-Test).

- [x] Selektions-Check: `GalerieGrid.onSelectAll()`/`selectAll`-Output waren tot (kein Template-Trigger mehr seit Wegfall der Gruppen-Header — die Erkenntnis aus FINDINGS.md). Statt Grid-intern gefixt: neuer „Alle auswählen"-Button in der Sub-Toolbar (sichtbar bei aktivem Auswahlmodus), der direkt `allAssets()` im Galerie-/Favoriten-Parent nutzt. Grid-Output entfernt (toter Pfad), beide Consumer (`galerie.html`, `favoriten.html`) umgestellt.

- [x] Skeleton-Anzeige: war schon korrekt außerhalb des Spacer-Divs (aus Phase 2) — keine Änderung nötig.

### ADR anlegen

- [x] `docs/decisions/011-galerie-virtual-scroll.md` anlegen:

```markdown
# ADR-011 — Virtual-Scroll-Strategie: @tanstack/angular-virtual, Row-level

## Kontext
Die Galerie rendert alle Assets als gescrollte Flex-Rows ohne Virtualisierung.
Bei 6000+ Assets pro Monat entstehen tausende DOM-Knoten — messbare Performance-Probleme.

## Betrachtete Optionen
1. **Angular CDK VirtualScrollViewport** — für uniforme Item-Höhen ausgelegt,
   aber Items haben uniforme Zeilenhöhe, nicht uniforme Breite. Das Justified-Grid-
   Layout (variable Breiten innerhalb einer Zeile) ist nicht abbildbar.

2. **Custom Group-level** — IntersectionObserver pro Monatsgruppe, Placeholder-Div.
   Zu grob: eine Gruppe mit 6000 Bildern rendert alles auf einmal wenn sichtbar.

3. **@tanstack/angular-virtual, Row-level** — virtualisiert auf Zeilen-Ebene.
   Braucht unsere eigene Row-Breaking-Engine (computeRows), übernimmt aber
   Scroll-Position-Tracking, Total-Height-Spacer und Overscan.

## Entscheidung
Option 3. Row-level Virtualisierung passt zur Datenform (flache Asset-Liste,
uniforme Zeilenhöhe = baseHeight). @tanstack/virtual ist stabil und battle-tested.
Die Row-Breaking-Engine ist ~40 Zeilen purer Code ohne Framework-Abhängigkeit.

## Konsequenzen
- Monatsgruppen-Header entfallen (kein `selectGroups` mehr im Grid).
- Row-Breaking-Algorithmus kann ±1 Zeile von Browser-Flexbox abweichen
  (Sub-Pixel-Rounding) — führt zu ±ROW_HEIGHT px Drift in der Scroll-Gesamthöhe.
- Scroll-Container muss ein explizites Element mit overflow-y: auto sein
  (kein Window-Scroll). Galerie-Layout entsprechend angepasst.
- `GRID_PADDING` und `GRID_GAP` in row-layout.ts sind CSS-Konstanten —
  Styling-Änderungen an grid.scss müssen dort nachgezogen werden.
```

### Docs

- [x] `docs/code-map.md` finaler Stand: war bereits aus Phase 2 aktuell (row-layout.ts, Virtualizer-Host, `#loadSentinel` entfernt) — keine Änderung nötig, Phase 3 war reine Logik ohne Struktur-Änderung.
- [x] README Bottom Sections füllen: Summary, Files touched, Commits, Deviations, Follow-ups

## Report-Back

Alle Checkliste-Punkte umgesetzt, `tsc`/`ng build` sauber. Zusätzlicher, mit dem
User abgestimmter Scope: der beim Umbau verwaiste „Gruppierung"-Button in der
Sub-Toolbar (täuschte Funktion vor, ohne noch etwas sichtbar zu bewirken) wurde
komplett samt Store-Pfad entfernt — Details in FINDINGS.md und ADR-011.
