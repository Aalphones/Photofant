# Phase 5 — Face-Selection: eigener NgRx-State-Slice

**Komplexität:** standard (reines Muster-Kopieren des bestehenden Asset-Selection-States, keine neue Architektur).

**Voraussetzung:** keine (unabhängig von Phase 1-4).

## Kontext (lesen vor dem Start)

- [frontend/src/app/store/gallery/gallery.actions.ts](../../../frontend/src/app/store/gallery/gallery.actions.ts) —
  komplette Datei (45 Zeilen), insbesondere Zeile 35-42 „Selection"-Aktionen — **exaktes Vorbild**
  für die neuen Face-Aktionen.
- [frontend/src/app/store/gallery/gallery.reducer.ts:8-27](../../../frontend/src/app/store/gallery/gallery.reducer.ts#L8) —
  `GalleryState`, `selectionMode: boolean` ist **bewusst geteilt** zwischen Foto- und
  Gesichter-Tab (ein globaler Auswahlmodus-Schalter) — nur die ID-Listen sind getrennt.
- [frontend/src/app/store/gallery/gallery.reducer.ts:137-159](../../../frontend/src/app/store/gallery/gallery.reducer.ts#L137) —
  bestehende Selection-Reducer (`enableSelectionMode`, `disableSelectionMode`, `toggleSelected`,
  `selectAll`, `selectRange`, `clearSelection`) — 1:1-Vorlage für die Face-Pendants.
- [frontend/src/app/store/gallery/gallery.selectors.ts](../../../frontend/src/app/store/gallery/gallery.selectors.ts) —
  komplette Datei, insbesondere die Destructuring-Liste (Zeile 7-24) und der finale
  `gallerySelectors`-Export (Zeile 140-160).
- README „Bewusst außerhalb": keine — diese Phase hat keinen Scope-Schnitt, sie ist reines
  Zustands-Gerüst ohne UI-Anbindung (die kommt in Phase 6).

## Aufgabe 1 — Neue Actions

`frontend/src/app/store/gallery/gallery.actions.ts:35-42`, direkt nach den bestehenden
Selection-Events ergänzen:

```typescript
    // Selection
    'Enable Selection Mode':     emptyProps(),
    'Disable Selection Mode':    emptyProps(),
    'Toggle Selected':           props<{ id: number }>(),
    'Select All':                props<{ ids: number[] }>(),
    'Select Range':              props<{ ids: number[] }>(),
    'Clear Selection':           emptyProps(),
    'Remove Face Item':          props<{ id: number }>(),
    // Face-Selection — eigene ID-Liste, teilt sich `selectionMode`/Enable/Disable/Clear mit den
    // Asset-Aktionen oben (ein Schalter für beide Tabs, siehe GalleryState-Kommentar)
    'Toggle Face Selected':      props<{ id: number }>(),
    'Select All Faces':          props<{ ids: number[] }>(),
    'Select Face Range':         props<{ ids: number[] }>(),
```

## Aufgabe 2 — State + Reducer

`frontend/src/app/store/gallery/gallery.reducer.ts:8-27`, `GalleryState` erweitern:

```typescript
export interface GalleryState extends EntityState<AssetDto> {
  // ... bestehende Felder unverändert ...
  selectionMode: boolean;
  selectedIds: number[];
  anchorId: number | null;
  // Face-Selection — eigene ID-Liste (Face-IDs ≠ Asset-IDs), `selectionMode` bleibt der
  // gemeinsame Schalter für beide Tabs (siehe Aufgabe 1)
  selectedFaceIds: number[];
  faceAnchorId: number | null;
  faceItems: FaceGalleryItemDto[];
  faceTotal: number;
}
```

`initialState` (Zeile 36-54) entsprechend um `selectedFaceIds: []` und `faceAnchorId: null`
ergänzen.

Reducer (Zeile 137-159) — bestehende drei Zeilen anpassen, drei neue ergänzen:

```typescript
    on(galleryActions.enableSelectionMode, (state: GalleryState) => ({
      ...state, selectionMode: true, anchorId: null, faceAnchorId: null,
    })),
    on(galleryActions.disableSelectionMode, (state: GalleryState) => ({
      ...state, selectionMode: false, selectedIds: [], anchorId: null,
      selectedFaceIds: [], faceAnchorId: null,
    })),
    on(galleryActions.toggleSelected, (state: GalleryState, { id }) => {
      const isSelected = state.selectedIds.includes(id);
      const selectedIds = isSelected
        ? state.selectedIds.filter((existingId: number) => existingId !== id)
        : [...state.selectedIds, id];
      return { ...state, selectedIds, anchorId: id };
    }),
    on(galleryActions.selectAll, (state: GalleryState, { ids }) => {
      const merged = Array.from(new Set([...state.selectedIds, ...ids]));
      return { ...state, selectedIds: merged };
    }),
    on(galleryActions.selectRange, (state: GalleryState, { ids }) => ({
      ...state, selectedIds: ids,
    })),
    on(galleryActions.clearSelection, (state: GalleryState) => ({
      ...state, selectedIds: [], selectionMode: false, anchorId: null,
      selectedFaceIds: [], faceAnchorId: null,
    })),
    on(galleryActions.toggleFaceSelected, (state: GalleryState, { id }) => {
      const isSelected = state.selectedFaceIds.includes(id);
      const selectedFaceIds = isSelected
        ? state.selectedFaceIds.filter((existingId: number) => existingId !== id)
        : [...state.selectedFaceIds, id];
      return { ...state, selectedFaceIds, faceAnchorId: id };
    }),
    on(galleryActions.selectAllFaces, (state: GalleryState, { ids }) => {
      const merged = Array.from(new Set([...state.selectedFaceIds, ...ids]));
      return { ...state, selectedFaceIds: merged };
    }),
    on(galleryActions.selectFaceRange, (state: GalleryState, { ids }) => ({
      ...state, selectedFaceIds: ids,
    })),
```

**Warum `disableSelectionMode`/`clearSelection` beide ID-Listen zurücksetzen:** `selectionMode`
ist ein einziger, geteilter Schalter (kein Tab-lokaler Zustand) — würde nur eine Liste beim
Ausschalten geleert, bliebe im jeweils anderen Tab eine unsichtbare Karteileiche liegen, die beim
nächsten Aktivieren überraschend wieder auftaucht.

## Aufgabe 3 — Selectors

`frontend/src/app/store/gallery/gallery.selectors.ts:7-24`, Destructuring-Liste ergänzen:

```typescript
const {
  // ... bestehende Einträge unverändert ...
  selectSelectionMode,
  selectSelectedIds,
  selectAnchorId,
  selectSelectedFaceIds,
  selectFaceAnchorId,
  selectFaceItems,
  selectFaceTotal,
} = galleryFeature;
```

`gallerySelectors`-Export (Zeile 140-160) ergänzen:

```typescript
export const gallerySelectors = {
  // ... bestehende Einträge unverändert ...
  selectSelectionMode,
  selectSelectedIds,
  selectAnchorId,
  selectSelectedFaceIds,
  selectFaceAnchorId,
  selectFaceItems,
  selectFaceTotal,
  selectFaceHasMore,
  selectHashMap,
};
```

## AK dieser Phase

- [x] `gallerySelectors.selectSelectedFaceIds` und `selectFaceAnchorId` existieren und sind über
      den Store abfragbar (kurzer Konsolen-Check reicht, keine UI in dieser Phase).
- [x] `galleryActions.toggleFaceSelected({id})` fügt/entfernt die ID in `selectedFaceIds`, ohne
      `selectedIds` (Asset-Liste) zu berühren.
- [x] `galleryActions.disableSelectionMode()` und `clearSelection()` leeren **beide** ID-Listen
      (`selectedIds` und `selectedFaceIds`) plus beide Anker.
- [x] `tsc`/Build läuft fehlerfrei (neue Felder korrekt typisiert, keine bestehenden
      Selection-Aufrufer kaputt — `galerie.ts` nutzt `selectedIds`/`selectionMode` unverändert
      weiter für den Foto-Tab).

## Doc-Updates

Keine — reiner Zustands-Code, `code-map.md`-Eintrag „Personen & Faces" wird erst in Phase 6/8
mit der UI-Anbindung relevant.

## Report-Back

Plan 1:1 umgesetzt, keine Abweichung. Drei Dateien geändert (`gallery.actions.ts`,
`gallery.reducer.ts`, `gallery.selectors.ts`), `npx tsc --noEmit -p tsconfig.app.json` grün.
