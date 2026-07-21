import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

// P38 Phase 5 — Vollständigkeits-Ring (Wissen-Übersicht, -Detail, Personen-Karte).
// Reine Anzeige-Komponente: der Aufrufer projiziert Avatar/Icon in <ng-content>.
@Component({
  selector: 'pf-completeness-ring',
  templateUrl: './completeness-ring.html',
  styleUrl: './completeness-ring.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CompletenessRing {
  readonly value = input.required<number>();
  readonly size = input<number>(64);
  readonly thickness = input<number>(4);

  protected readonly percent = computed((): number => Math.round(this.value() * 100));
  protected readonly thicknessPx = computed((): string => `${this.thickness()}px`);
}
