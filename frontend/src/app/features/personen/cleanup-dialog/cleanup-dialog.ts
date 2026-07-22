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
