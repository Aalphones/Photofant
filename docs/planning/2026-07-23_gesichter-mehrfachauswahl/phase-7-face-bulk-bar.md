# Phase 7 — Face-Bulk-Bar: Löschen / Hochskalieren / Zu Trainingsset

**Komplexität:** standard (neue, aber kleine Komponente; Verdrahtung folgt bestehenden Mustern).

**Voraussetzung:** Phase 2 (Trainingsset-API), Phase 4 (Face-Upscale-API) und Phase 6
(Auswahl-UI) abgeschlossen — diese Phase ist die Klammer, die alle drei nutzbar macht.

## Kontext (lesen vor dem Start)

- [frontend/src/app/ui/bulk-bar/bulk-bar.ts](../../../frontend/src/app/ui/bulk-bar/bulk-bar.ts) —
  komplette Datei — Vorbild für Struktur (Inputs/Outputs, Trainingsset-Inline-Dropdown-Menü
  Zeile 114-121). Die neue Komponente ist **keine Erweiterung** von `BulkBar` (die trägt
  Tag/Album/Rerun/Edit/Dupe-Scan/Person-Zuweisen — alles asset-spezifisch, nicht auf Faces
  übertragbar), sondern eine **eigene, kleine** Geschwister-Komponente mit nur 3 Aktionen.
- [frontend/src/app/ui/bulk-bar/bulk-bar.html:64-82](../../../frontend/src/app/ui/bulk-bar/bulk-bar.html#L64) —
  Trainingsset-Inline-Dropdown-Markup, 1:1-Vorlage.
- [frontend/src/app/ui/bulk-bar/bulk-bar.scss](../../../frontend/src/app/ui/bulk-bar/bulk-bar.scss) —
  Container-/Divider-/Action-Button-Styles, 1:1 übernehmbar (nur Klassenpräfix `facebulkbar__`
  statt `bulkbar__`, damit keine Kollision mit dem Original entsteht, falls beide gleichzeitig im
  DOM sind — sind sie zwar nie, aber getrennte Präfixe vermeiden jede Verwechslung beim Lesen).
- [frontend/src/app/features/galerie/galerie.html:88-106](../../../frontend/src/app/features/galerie/galerie.html#L88) —
  heutiges `@if (selectedCount() > 0) { <pf-bulk-bar ... /> }` — reagiert **nur** auf die
  Asset-Auswahl, unabhängig vom aktiven Tab. Diese Phase macht daraus einen `mediaType()`-Zweig.
- [frontend/src/app/features/galerie/galerie.ts:355-378](../../../frontend/src/app/features/galerie/galerie.ts#L355) —
  `onBulkUpscale` (Asset-Pfad) — **exaktes Vorbild** für `onFaceBulkUpscale`, nur mit
  `target_face_ids`/`face_inputs` statt `target_asset_ids`/`inputs` (Phase 4 „Kontrakt").
- [frontend/src/app/features/galerie/lightbox/lightbox.ts:1283-1296](../../../frontend/src/app/features/galerie/lightbox/lightbox.ts#L1283) —
  `deleteFaceFromAsset` — zeigt das bestehende Muster nach Einzel-Face-Löschung:
  `galleryActions.removeFaceItem({id})` pro gelöschtem Face dispatchen (aktualisiert `faceItems`/
  `faceTotal` direkt im Store, kein Full-Reload nötig). `onFaceBulkDelete` wendet dasselbe Muster
  pro ID in der Bulk-Antwort an.
- [frontend/src/app/services/person.service.ts:120-122](../../../frontend/src/app/services/person.service.ts#L120) —
  `bulkDeleteFaces(faceIds)` — bereits vorhanden, wird hier zum ersten Mal aus der Galerie
  aufgerufen (bisher nur vom Cleanup-Dialog genutzt).
- README „Kontrakt" — `CollectionService.addItems`/`comfyuiService.runDefaultWorkflow`
  Ziel-Signaturen (aus Phase 2/4).

## Aufgabe 1 — Neue Komponente `FaceBulkBar`

Neue Dateien `frontend/src/app/features/galerie/face-bulk-bar/face-bulk-bar.ts`,
`face-bulk-bar.html`, `face-bulk-bar.scss`.

```typescript
// face-bulk-bar.ts
import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { Icon } from '@photofant/ui';

export interface FaceBulkTrainingSetOption {
  id: number;
  name: string;
}

@Component({
  selector: 'pf-face-bulk-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './face-bulk-bar.html',
  styleUrl: './face-bulk-bar.scss',
})
export class FaceBulkBar {
  readonly count        = input.required<number>();
  readonly trainingSets = input<FaceBulkTrainingSetOption[]>([]);
  readonly canUpscale   = input<boolean>(false);

  readonly close            = output<void>();
  readonly deleteAction     = output<void>();
  readonly upscaleAction    = output<void>();
  readonly addToTrainingSet = output<number>();

  protected readonly showTrainingSetMenu = signal(false);

  protected readonly countLabel = computed((): string => {
    const n = this.count();
    return n === 1 ? '1 Gesicht ausgewählt' : `${n} Gesichter ausgewählt`;
  });

  protected toggleTrainingSetMenu(): void {
    this.showTrainingSetMenu.update((open: boolean) => !open);
  }

  protected pickTrainingSet(collectionId: number): void {
    this.addToTrainingSet.emit(collectionId);
    this.showTrainingSetMenu.set(false);
  }

  protected triggerUpscale(): void {
    this.upscaleAction.emit();
  }

  protected triggerDelete(): void {
    // Face-Löschen ist endgültig (kein Papierkorb/Undo wie bei Assets, siehe
    // person.service.ts::bulkDeleteFaces) — deshalb eine native Sicherheitsabfrage,
    // anders als der Asset-Bulk-Bar-Trash-Button (der landet zuerst im Papierkorb).
    const label = this.count() === 1 ? 'Dieses Gesicht' : `Diese ${this.count()} Gesichter`;
    if (window.confirm(`${label} endgültig löschen? Das kann nicht rückgängig gemacht werden.`)) {
      this.deleteAction.emit();
    }
  }

  protected onClose(): void {
    this.close.emit();
  }
}
```

```html
<!-- face-bulk-bar.html -->
<div class="facebulkbar__inner">
  <span class="facebulkbar__count">{{ countLabel() }}</span>
  <div class="facebulkbar__divider"></div>

  <div class="facebulkbar__album">
    <button class="facebulkbar__action" (click)="toggleTrainingSetMenu()">
      <pf-icon name="training" [size]="15" />
      Zu Trainingsset
    </button>
    @if (showTrainingSetMenu()) {
      <div class="facebulkbar__album-menu">
        @for (trainingSet of trainingSets(); track trainingSet.id) {
          <button class="facebulkbar__album-item" (click)="pickTrainingSet(trainingSet.id)">
            <pf-icon name="training" [size]="13" />
            {{ trainingSet.name }}
          </button>
        }
        @if (trainingSets().length === 0) {
          <span class="facebulkbar__album-empty">Keine Trainingssets angelegt</span>
        }
      </div>
    }
  </div>

  @if (canUpscale()) {
    <div class="facebulkbar__divider"></div>
    <button class="facebulkbar__action" (click)="triggerUpscale()">
      <pf-icon name="refresh" [size]="15" />
      Hochskalieren
    </button>
  }

  <div class="facebulkbar__divider"></div>
  <button class="facebulkbar__action facebulkbar__action--danger" (click)="triggerDelete()">
    <pf-icon name="trash" [size]="15" />
    Löschen
  </button>

  <div class="facebulkbar__divider"></div>
  <button class="facebulkbar__close" (click)="onClose()" aria-label="Auswahl aufheben">
    <pf-icon name="x" [size]="16" />
  </button>
</div>
```

`face-bulk-bar.scss` — Inhalt 1:1 aus `bulk-bar.scss` übernehmen, alle Klassennamen
`bulkbar__` → `facebulkbar__` ersetzen (mechanisches Suchen/Ersetzen, keine Werte ändern).

## Aufgabe 2 — `Galerie`: bedingte Bulk-Leiste je Tab

`frontend/src/app/features/galerie/galerie.html:88-106` ersetzen durch:

```html
@if (mediaType() === 'faces') {
  @if (selectedFaceCount() > 0) {
    <pf-face-bulk-bar
      [count]="selectedFaceCount()"
      [trainingSets]="trainingSets()"
      [canUpscale]="canBulkUpscale()"
      (close)="onFaceBulkClose()"
      (deleteAction)="onFaceBulkDelete()"
      (upscaleAction)="onFaceBulkUpscale()"
      (addToTrainingSet)="onFaceAddToTrainingSet($event)"
    />
  }
} @else if (selectedCount() > 0) {
  <pf-bulk-bar
    [count]="selectedCount()"
    [albums]="albums()"
    [trainingSets]="trainingSets()"
    [canUpscale]="canBulkUpscale()"
    [persons]="persons()"
    (close)="onBulkClose()"
    (tagAction)="onBulkTag($event)"
    (addToAlbum)="onAddToAlbum($event)"
    (addToTrainingSet)="onAddToTrainingSet($event)"
    (rerunAction)="onBulkRerunOpen()"
    (editAction)="onBulkEditOpen()"
    (upscaleAction)="onBulkUpscale()"
    (dupeScanAction)="onBulkDupeScan()"
    (trashAction)="onBulkTrash()"
    (assignPersonAction)="onBulkAssignPersonOpen()"
  />
}
```

**`canUpscale` bleibt bewusst `canBulkUpscale()` für beide Leisten** — dieselbe
ComfyUI-Default-Upscale-Workflow-Konfiguration entscheidet für Fotos und Gesichter gleichermaßen,
ob überhaupt ein Upscale-Workflow hinterlegt ist (Bild-Quelle unterscheidet sich erst beim
tatsächlichen Aufruf über `inputs` vs. `face_inputs`, siehe Aufgabe 4). Keine zweite,
duplizierte Computed-Property anlegen.

`frontend/src/app/features/galerie/galerie.ts` — `FaceBulkBar` zu `imports` (Zeile 21)
hinzufügen: `import { FaceBulkBar } from './face-bulk-bar/face-bulk-bar';`.

## Aufgabe 3 — `Galerie`: neue Computed + Close/Delete

Bei `selectedCount` (Zeile 128) ergänzen:

```typescript
  protected readonly selectedFaceCount = computed((): number => this.selectedFaceIds().length);
```

Bei `onBulkClose` (Zeile 258-260) ergänzen:

```typescript
  protected onFaceBulkClose(): void {
    this.store.dispatch(galleryActions.clearSelection());
  }
```

(`clearSelection` leert seit Phase 5 **beide** ID-Listen und schaltet `selectionMode` aus — exakt
dasselbe Verhalten wie `onBulkClose` für den Foto-Tab.)

Neue Methode, bei `onBulkTrash` (Zeile 380-389) danach einfügen:

```typescript
  protected onFaceBulkDelete(): void {
    const ids = this.selectedFaceIds();
    if (!ids.length) { return; }
    this.personService.bulkDeleteFaces(ids)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        for (const id of ids) {
          this.store.dispatch(galleryActions.removeFaceItem({ id }));
        }
        this.store.dispatch(galleryActions.clearSelection());
      });
  }
```

## Aufgabe 4 — `Galerie`: Face-Upscale-Aufruf

Neue Methode, direkt nach `onBulkUpscale` (Zeile 355-378):

```typescript
  protected onFaceBulkUpscale(): void {
    const workflow = this.upscaleWorkflow();
    const ids = this.selectedFaceIds();
    if (workflow == null || ids.length === 0) { return; }
    const imageSlot = workflow.inputs.find((input) => input.kind === 'image');
    if (imageSlot == null) { return; }
    this.comfyuiService.runDefaultWorkflow('upscale', {
      target_face_ids: ids,
      inputs: {},
      face_inputs: { [imageSlot.key]: ids },
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: { jobs: { job_id: string }[] }) => {
          const count = response.jobs.length;
          this.showRunToast(`${count} Upscale-Job${count !== 1 ? 's' : ''} gestartet — Ergebnis wird automatisch importiert`);
        },
        error: (error: unknown) => {
          const message = error instanceof Error ? error.message : 'Fehler beim Senden an ComfyUI';
          this.showRunToast(`Fehler: ${message}`);
        },
      });
    this.store.dispatch(galleryActions.clearSelection());
  }
```

Kein sofortiges Neuladen der Gesichter-Liste nach dem Auslösen — der Job läuft asynchron im
Hintergrund (ComfyUI), der Toast informiert, das `is_upscaled`-Sparkle-Badge
(`face-cell.html:20-24`) erscheint von selbst, sobald die Kachel das nächste Mal geladen wird
(Seiten-Reload oder normales Nachladen beim Scrollen) — exakt dasselbe Verhalten wie beim
bestehenden Asset-Bulk-Upscale (kein Sofort-Refresh dort ebenfalls).

## Aufgabe 5 — `Galerie`: Zu-Trainingsset-Aufruf

Neue Methode, bei `onAddToTrainingSet` (Zeile 280-285) danach einfügen:

```typescript
  protected onFaceAddToTrainingSet(collectionId: number): void {
    const ids = this.selectedFaceIds();
    if (!ids.length) { return; }
    this.store.dispatch(collectionsActions.addItems({ collectionId, faceIds: ids }));
    this.store.dispatch(galleryActions.clearSelection());
  }
```

## AK dieser Phase

- [ ] Im Gesichter-Tab erscheint bei ≥1 ausgewähltem Gesicht die neue Bulk-Leiste (nicht die
      Foto-Bulk-Leiste), im Foto-Tab weiterhin die bestehende `pf-bulk-bar` (Regressionscheck).
- [ ] „Löschen" fragt vor dem Löschen nach Bestätigung, löscht danach alle ausgewählten
      Gesichter in einem Aufruf, die Gesichter-Liste aktualisiert sich sofort (kein Reload nötig).
- [ ] „Hochskalieren" ist nur sichtbar, wenn ein Default-Upscale-Workflow konfiguriert ist
      (`canBulkUpscale()`), löst beim Klick einen Job pro ausgewähltem Gesicht aus, Toast
      bestätigt die Anzahl.
- [ ] „Zu Trainingsset" zeigt die vorhandenen Trainingssets in einem Inline-Dropdown, Klick fügt
      alle ausgewählten Gesichter als Crop-Mitglieder hinzu (verifizierbar über
      `GET /collections/{id}/items` — Phase 2 AK).
- [ ] Schließen-Button leert die Auswahl und schaltet den Auswahl-Modus aus.

## Doc-Updates

- [ ] `docs/code-map.md` — Zeile „Personen & Faces": neue Komponente
      `features/galerie/face-bulk-bar/` ergänzen.

## Report-Back

_(nach Umsetzung ausfüllen: ob die native `window.confirm`-Bestätigung fürs Löschen genügt oder
ein eigener Dialog gewünscht war, tatsächliches Verhalten bei sehr großen Bulk-Upscale-Batches)_
