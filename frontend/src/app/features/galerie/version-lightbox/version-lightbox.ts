import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  output,
} from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { Router } from '@angular/router';
import type { VersionGalleryItemDto } from '@photofant/models';
import { Icon } from '@photofant/ui';
import { ZoomStage } from '../lightbox/zoom-stage';

@Component({
  selector: 'pf-version-lightbox',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, ZoomStage],
  templateUrl: './version-lightbox.html',
  styleUrl: './version-lightbox.scss',
})
export class VersionLightbox {
  private readonly router  = inject(Router);
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);

  readonly version  = input.required<VersionGalleryItemDto>();
  readonly hasPrev  = input<boolean>(false);
  readonly hasNext  = input<boolean>(false);

  readonly close       = output<void>();
  readonly prev        = output<void>();
  readonly next        = output<void>();
  readonly openOriginal = output<number>();

  protected readonly imageUrl = computed((): string =>
    `/api/versions/${this.version().id}/file`
  );

  protected readonly typeLabel = computed((): string => {
    const type = this.version().type;
    if (!type) { return 'Edit'; }
    if (type === 'crop') { return 'Zuschnitt'; }
    if (type === 'resize') { return 'Skaliert'; }
    if (type === 'convert') { return 'Konvertiert'; }
    return type;
  });

  protected readonly formattedDate = computed((): string => {
    const dateStr = this.version().created_at;
    if (!dateStr) { return '—'; }
    return new Intl.DateTimeFormat('de-DE', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    }).format(new Date(dateStr));
  });

  protected readonly dimensions = computed((): string => {
    const { width, height } = this.version();
    if (width && height) { return `${width} × ${height}`; }
    return '—';
  });

  constructor() {
    const onKeyDown = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') { return; }
      if (event.key === 'Escape') { this.close.emit(); }
      else if (event.key === 'ArrowLeft' && this.hasPrev())  { this.prev.emit(); }
      else if (event.key === 'ArrowRight' && this.hasNext()) { this.next.emit(); }
    };
    this.document.addEventListener('keydown', onKeyDown);
    this.destroyRef.onDestroy(() => this.document.removeEventListener('keydown', onKeyDown));
  }

  protected openInEditor(): void {
    void this.router.navigate(['/editor', 'version', this.version().id]);
    this.close.emit();
  }

  protected onOpenOriginal(): void {
    const parentId = this.version().parent_asset_id;
    if (parentId != null) {
      this.openOriginal.emit(parentId);
    }
  }
}
