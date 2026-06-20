import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  OnInit,
  output,
  signal,
} from '@angular/core';
import { DestroyRef } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import type { PersonDto, PersonFace } from '@photofant/models';
import { PersonService } from '@photofant/services';
import { DecimalPipe } from '@angular/common';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-split-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, DecimalPipe],
  templateUrl: './split-dialog.html',
  styleUrl: './split-dialog.scss',
})
export class SplitDialog implements OnInit {
  private readonly personService = inject(PersonService);
  private readonly destroyRef = inject(DestroyRef);

  readonly person = input.required<PersonDto>();
  readonly close = output<void>();
  readonly split = output<{ personId: number; faceIds: number[] }>();

  protected readonly faces = signal<PersonFace[]>([]);
  protected readonly loading = signal(true);
  protected readonly selectedIds = signal<Set<number>>(new Set());

  protected readonly selectedCount = computed((): number => this.selectedIds().size);
  protected readonly canSplit = computed(
    (): boolean => this.selectedCount() > 0 && this.selectedCount() < this.faces().length,
  );

  ngOnInit(): void {
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

  protected onConfirm(): void {
    this.split.emit({
      personId: this.person().id,
      faceIds: Array.from(this.selectedIds()),
    });
  }

  protected onBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('split-dialog__backdrop')) {
      this.close.emit();
    }
  }
}
