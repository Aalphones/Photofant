# Phase 4 — Frontend-UI: Cleanup-Dialog + Verdrahtung

**Rating:** standard (freihändiges UI ohne Mockup, aber vollständig spezifiziert — siehe README „Design-Treue").

**Voraussetzung:** Phase 3 abgeschlossen.

## Kontext (lesen vor dem Bauen)

- `frontend/src/app/features/personen/split-dialog/` (alle 3 Dateien) — das direkte Vorbild für
  Struktur/Interaktion (Grid aus Face-Kacheln, Klick-Toggle-Auswahl, Footer mit Zähler).
- `frontend/src/app/features/personen/delete-person-dialog/` — Vorbild für den Confirm-Strip
  (destruktive Aktion, Erklärtext was mit den Daten passiert).
- `frontend/src/app/features/personen/personen.ts` + `personen.html` — Wiring-Muster:
  `splitPerson`-Signal (Zeile 105), `onSplitClick`/`onSplit` (Zeile 280-287), zwei
  `(splitClick)="onSplitClick(person)"`-Bindings in `personen.html` (Zeilen 115, 142) für die
  zwei Card-Varianten (Grid/Face-Ansicht).
- `frontend/src/app/features/personen/person-card/person-card.ts` (Outputs Zeile 43-55,
  `onDupeCheckClick` Zeile 201-205) + `person-card.html` (Menü-Buttons Zeile 108-150) — Vorbild
  für den neuen Menüpunkt.
- `frontend/src/app/ui/icon/icon.ts` — verfügbare Icon-Namen; `trash` (Zeile 11) für den
  Menüpunkt, `check` (Zeile 28) für die Auswahl-Markierung.
- Farb-Token `var(--danger)` (siehe `features/galerie/lightbox/lightbox.scss:475/862`) für die
  destruktive Bestätigung + rote Score-Badges.

## Aufgabe

### 1. Neue Komponente `frontend/src/app/features/personen/cleanup-dialog/cleanup-dialog.ts`

```ts
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  OnInit,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DecimalPipe } from '@angular/common';
import type { PersonDto, PersonFace } from '@photofant/models';
import { PersonService } from '@photofant/services';
import { Icon } from '@photofant/ui';

const REASON_LABELS: Record<string, string> = {
  identity_mismatch: 'Wirkt anders als die übrigen Gesichter dieser Person',
  low_resolution: 'Niedrige Auflösung',
  low_detection_score: 'Unsichere Gesichtserkennung',
  upscaled: 'Hochskaliert',
};

@Component({
  selector: 'pf-cleanup-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, DecimalPipe],
  templateUrl: './cleanup-dialog.html',
  styleUrl: './cleanup-dialog.scss',
})
export class CleanupDialog implements OnInit {
  private readonly personService = inject(PersonService);
  private readonly destroyRef = inject(DestroyRef);

  readonly person = input.required<PersonDto>();
  readonly close = output<void>();
  // Notification only (no payload the parent needs beyond "refresh counts") —
  // the dialog itself owns its face list and stays open after deleting.
  readonly deleted = output<void>();

  protected readonly faces = signal<PersonFace[]>([]);
  protected readonly loading = signal(true);
  protected readonly deleting = signal(false);
  protected readonly selectedIds = signal<Set<number>>(new Set());
  protected readonly confirming = signal(false);

  protected readonly sortedFaces = computed((): PersonFace[] =>
    [...this.faces()].sort((a, b) => b.cleanup_score - a.cleanup_score),
  );

  protected readonly selectedCount = computed((): number => this.selectedIds().size);
  // Mirrors split-dialog's canSplit guard: never let this dialog empty a person out
  // completely — that's the separate, explicit "Person auflösen" flow.
  protected readonly canDelete = computed((): boolean =>
    this.selectedCount() > 0 && this.selectedCount() < this.faces().length,
  );

  ngOnInit(): void {
    this.loadFaces();
  }

  private loadFaces(): void {
    this.loading.set(true);
    this.personService.getPersonFaces(this.person().id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (faces: PersonFace[]) => {
          this.faces.set(faces);
          this.loading.set(false);
        },
        error: () => { this.loading.set(false); },
      });
  }

  protected toggleFace(faceId: number): void {
    this.selectedIds.update((current: Set<number>) => {
      const next = new Set(current);
      if (next.has(faceId)) {
        next.delete(faceId);
      } else {
        next.add(faceId);
      }
      return next;
    });
  }

  protected isSelected(faceId: number): boolean {
    return this.selectedIds().has(faceId);
  }

  protected reasonsTooltip(face: PersonFace): string {
    if (face.cleanup_reasons.length === 0) { return 'Kein Problem erkannt'; }
    return face.cleanup_reasons.map((reason: string) => REASON_LABELS[reason] ?? reason).join(' · ');
  }

  protected scoreSeverity(face: PersonFace): 'high' | 'medium' | 'none' {
    if (face.cleanup_score >= 0.66) { return 'high'; }
    if (face.cleanup_score >= 0.33) { return 'medium'; }
    return 'none';
  }

  protected onDeleteClick(): void {
    this.confirming.set(true);
  }

  protected onCancelConfirm(): void {
    this.confirming.set(false);
  }

  protected onConfirmDelete(): void {
    const faceIds = Array.from(this.selectedIds());
    this.deleting.set(true);
    this.personService.bulkDeleteFaces(faceIds)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.faces.update((current: PersonFace[]) =>
            current.filter((face: PersonFace) => !faceIds.includes(face.id)),
          );
          this.selectedIds.set(new Set());
          this.deleting.set(false);
          this.confirming.set(false);
          this.deleted.emit();
        },
        error: () => {
          this.deleting.set(false);
          this.confirming.set(false);
        },
      });
  }

  protected onBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('cleanup-dialog__backdrop')) {
      this.close.emit();
    }
  }
}
```

### 2. Template `cleanup-dialog.html`

```html
<div class="cleanup-dialog__backdrop" (click)="onBackdrop($event)">
  <div class="cleanup-dialog__card">
    <div class="cleanup-dialog__header">
      <h3 class="cleanup-dialog__title">Gesichter bereinigen</h3>
      <button class="cleanup-dialog__close" (click)="close.emit()">
        <pf-icon name="x" [size]="18" />
      </button>
    </div>

    <div class="cleanup-dialog__body">
      <p class="cleanup-dialog__hint">
        Gesichter, die nicht zu <strong>{{ person().name ?? 'Person #' + person().id }}</strong>
        passen oder schlecht erkannt wurden, stehen oben. Auswählen und löschen — die zugehörigen
        Fotos bleiben erhalten (sie wandern zu „Unbekannt", falls sie sonst keiner Person mehr
        zugeordnet sind).
      </p>

      @if (loading()) {
        <div class="cleanup-dialog__loading">Lade Gesichter…</div>
      } @else if (faces().length === 0) {
        <div class="cleanup-dialog__loading">Keine Gesichter vorhanden.</div>
      } @else {
        <div class="cleanup-dialog__grid">
          @for (face of sortedFaces(); track face.id) {
            <button
              class="cleanup-dialog__face"
              [class.cleanup-dialog__face--selected]="isSelected(face.id)"
              [title]="reasonsTooltip(face)"
              (click)="toggleFace(face.id)"
            >
              <img
                class="cleanup-dialog__face-img"
                [src]="'/api' + face.crop_url"
                [alt]="'Gesicht #' + face.id"
              />
              @if (isSelected(face.id)) {
                <div class="cleanup-dialog__check">
                  <pf-icon name="check" [size]="14" />
                </div>
              }
              @if (face.cleanup_score > 0) {
                <span
                  class="cleanup-dialog__score"
                  [class.cleanup-dialog__score--high]="scoreSeverity(face) === 'high'"
                  [class.cleanup-dialog__score--medium]="scoreSeverity(face) === 'medium'"
                >{{ (face.cleanup_score * 100) | number:'1.0-0' }}%</span>
              }
            </button>
          }
        </div>

        @if (confirming()) {
          <div class="cleanup-dialog__confirm">
            <span class="cleanup-dialog__confirm-text">
              {{ selectedCount() }} Gesicht(er) wirklich löschen? Das kann nicht rückgängig
              gemacht werden.
            </span>
            <div class="cleanup-dialog__actions">
              <button class="cleanup-dialog__btn cleanup-dialog__btn--cancel" (click)="onCancelConfirm()">
                Abbrechen
              </button>
              <button
                class="cleanup-dialog__btn cleanup-dialog__btn--danger"
                [disabled]="deleting()"
                (click)="onConfirmDelete()"
              >
                <pf-icon name="trash" [size]="14" />
                Ja, löschen
              </button>
            </div>
          </div>
        } @else {
          <div class="cleanup-dialog__footer">
            <span class="cleanup-dialog__count">{{ selectedCount() }} ausgewählt</span>
            <div class="cleanup-dialog__actions">
              <button class="cleanup-dialog__btn cleanup-dialog__btn--cancel" (click)="close.emit()">
                Schließen
              </button>
              <button
                class="cleanup-dialog__btn cleanup-dialog__btn--danger"
                [disabled]="!canDelete()"
                (click)="onDeleteClick()"
              >
                <pf-icon name="trash" [size]="14" />
                Ausgewählte löschen
              </button>
            </div>
          </div>
        }
      }
    </div>
  </div>
</div>
```

### 3. Styles `cleanup-dialog.scss`

Kopiere `split-dialog.scss` 1:1 als Basis (Klassen-Präfix `split-dialog__` → `cleanup-dialog__` per
Suchen/Ersetzen), dann ergänzen:

```scss
.cleanup-dialog__score {
  // Basis-Optik wie .split-dialog__score (schwarz/halbtransparent) —
  // Farb-Modifikatoren kommen on top:

  &--medium {
    background: oklch(0.7 0.15 70 / 0.85); // amber
  }

  &--high {
    background: var(--danger, oklch(0.55 0.2 25));
  }
}

.cleanup-dialog__confirm {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--line);
}

.cleanup-dialog__confirm-text {
  font-size: 12px;
  color: var(--text-2);
  line-height: 1.4;
}

.cleanup-dialog__btn--danger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background: var(--danger, oklch(0.55 0.2 25));
  color: #fff;

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  &:hover:not(:disabled) {
    opacity: 0.85;
  }
}
```

(`.cleanup-dialog__btn--cancel` bleibt identisch zu `.split-dialog__btn--cancel`, nur umbenannt.)

### 4. Menüpunkt in `person-card`

`person-card.ts` — neuer Output + Handler, neben den bestehenden (Zeile ~48):

```ts
readonly cleanupClick = output<void>();
```

Neuer Handler neben `onDupeCheckClick` (Zeile ~201):

```ts
protected onCleanupClick(event: MouseEvent): void {
  event.stopPropagation();
  this.menuOpen.set(false);
  this.cleanupClick.emit();
}
```

`person-card.html` — neuer Menü-Button, eingefügt nach „Duplikate suchen" (nach Zeile 123, vor
„Bilder importieren"):

```html
<button class="person-card__menu-item" (click)="onCleanupClick($event)">
  <pf-icon name="trash" [size]="13" />
  <span>Gesichter bereinigen…</span>
</button>
```

### 5. Verdrahtung in `personen.ts` / `personen.html`

`personen.ts` — Import + Signal + Handler (analog `splitPerson`):

```ts
import { CleanupDialog } from './cleanup-dialog/cleanup-dialog';
// ... im @Component-imports-Array ergänzen: CleanupDialog

protected readonly cleanupPerson = signal<PersonDto | null>(null);

protected onCleanupClick(person: PersonDto): void {
  this.cleanupPerson.set(person);
}

protected onCleanupDialogClose(): void {
  this.cleanupPerson.set(null);
}

protected onFacesDeleted(): void {
  // Fotoanzahl/Portrait der Person haben sich geändert — Grid neu laden.
  this.store.dispatch(personsActions.loadPersons());
}
```

`personen.html` — `(cleanupClick)="onCleanupClick(person)"` an **beiden** bestehenden
`<pf-person-card>`-Stellen ergänzen (dieselben zwei Zeilen, an denen aktuell
`(splitClick)="onSplitClick(person)"` steht, Zeilen 115 und 142), sowie der Dialog selbst,
eingefügt neben den anderen Dialogen (z.B. nach dem `SplitDialog`-Block):

```html
@if (cleanupPerson(); as person) {
  <pf-cleanup-dialog
    [person]="person"
    (close)="onCleanupDialogClose()"
    (deleted)="onFacesDeleted()"
  />
}
```

### 6. Doku — `docs/code-map.md`

In der Tabellenzeile „Personen & Faces" (Suche nach `**Personen & Faces**`) den neuen Dialog +
das neue Scoring-Modul ergänzen — Frontend-Spalte: `..., cleanup-dialog/, ...` neben `merge/split/dupe-check/delete-person-dialog`; Backend-Spalte: `..., clustering/cleanup.py, ...` neben `clustering/engine.py`.

## Akzeptanzkriterien (siehe auch README „Finale Abnahmekriterien")

- Menüpunkt „Gesichter bereinigen…" öffnet den Dialog für die geklickte Person.
- Faces sind nach `cleanup_score` absteigend sortiert; Score-Badge nur sichtbar wenn `cleanup_score > 0`, Farbe grün→amber→rot nach Schwelle.
- Hover auf eine Kachel zeigt die Gründe als Tooltip (native `title`), oder „Kein Problem erkannt".
- Löschen fragt einmal nach, entfernt die Faces dann aus der lokalen Liste (Dialog bleibt offen), Elternkomponente lädt die Personenliste neu.
- Es lässt sich nie die komplette verbleibende Auswahl der Person leeren (`canDelete()`-Guard identisch zu `split-dialog`s `canSplit()`).

## Checkliste

- [x] `cleanup-dialog.ts` / `.html` / `.scss` neu
- [x] `person-card.ts` / `.html`: neuer Output + Menüpunkt
- [x] `personen.ts` / `.html`: Signal, Handler, zwei `cleanupClick`-Bindings, Dialog eingebunden
- [x] `docs/code-map.md`: Zeile „Personen & Faces" um neuen Dialog + neues Modul ergänzt
- [ ] Manueller Check im Browser: Dialog öffnen, Sortierung/Badges/Tooltip sichtbar, löschen funktioniert, Person-Karte aktualisiert Fotoanzahl (**User**, siehe Smoke-Checkliste)

## Report-Back

Umsetzung 1:1 nach Plan-Vorlage (Komponente, Template, Styles, Verdrahtung — keine Abweichung).
`tsc --noEmit` und `ng build` laufen grün, keine neuen Warnungen (die zwei Bundle-Budget-Warnungen
sind unverändert vorbestehend, gehören zu `lightbox.scss`/Initial-Bundle, nicht zu dieser Phase).
Offen: der manuelle Browser-Check — kein Mockup vorhanden (freihändig nach `split-dialog`-Muster,
README „Design-Treue"), daher lohnt ein visueller Blick vor dem Abhaken.
