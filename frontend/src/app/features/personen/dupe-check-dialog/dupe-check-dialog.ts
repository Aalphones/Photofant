import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  input,
  OnInit,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Store } from '@ngrx/store';
import type { PersonDto, PersonDupePair } from '@photofant/models';
import { PersonService } from '@photofant/services';
import { modelsSelectors } from '@photofant/store';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-dupe-check-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './dupe-check-dialog.html',
  styleUrl: './dupe-check-dialog.scss',
})
export class DupeCheckDialog implements OnInit {
  private readonly personService = inject(PersonService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly store = inject(Store);
  private readonly processingConfig = this.store.selectSignal(modelsSelectors.selectProcessingConfig);

  readonly person = input.required<PersonDto>();
  readonly close = output<void>();

  protected readonly phase = signal<'idle' | 'loading' | 'done'>('idle');
  protected readonly pairs = signal<PersonDupePair[]>([]);
  protected readonly error = signal<string | null>(null);
  protected readonly dismissed = signal<Set<string>>(new Set());

  protected readonly visiblePairs = computed((): PersonDupePair[] => {
    const dismissed = this.dismissed();
    return this.pairs().filter(
      (pair: PersonDupePair) => !dismissed.has(`${pair.asset_a_id}_${pair.asset_b_id}`),
    );
  });

  ngOnInit(): void {
    this.startScan();
  }

  protected startScan(): void {
    this.phase.set('loading');
    this.error.set(null);
    this.personService
      .searchDuplicates(this.person().id, this.processingConfig().dupeThreshold)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (pairs: PersonDupePair[]) => {
          this.pairs.set(pairs);
          this.phase.set('done');
        },
        error: () => {
          this.error.set('Scan fehlgeschlagen.');
          this.phase.set('idle');
        },
      });
  }

  protected dismiss(pair: PersonDupePair): void {
    this.dismissed.update((current: Set<string>) => {
      const next = new Set(current);
      next.add(`${pair.asset_a_id}_${pair.asset_b_id}`);
      return next;
    });
  }

  protected thumbnailUrl(assetId: number, contentHash: string): string {
    return `/api/assets/${assetId}/thumbnail?size=256&v=${contentHash.slice(0, 8)}`;
  }

  protected onBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('dupe-check-dialog__backdrop')) {
      this.close.emit();
    }
  }
}
