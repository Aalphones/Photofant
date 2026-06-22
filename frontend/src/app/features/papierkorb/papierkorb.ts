import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { Store } from '@ngrx/store';
import type { AssetDto } from '@photofant/models';
import { AssetService } from '@photofant/services';
import { trashActions, trashSelectors } from '@photofant/store';
import { Icon } from '@photofant/ui';

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  return new Intl.DateTimeFormat('de-DE', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(new Date(dateStr));
}

function formatBytes(bytes: number | null): string {
  if (bytes == null) return '—';
  if (bytes >= 1_048_576) return (bytes / 1_048_576).toFixed(1) + ' MB';
  if (bytes >= 1_024) return Math.round(bytes / 1_024) + ' KB';
  return bytes + ' B';
}

@Component({
  selector: 'pf-papierkorb',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './papierkorb.html',
  styleUrl: './papierkorb.scss',
})
export class Papierkorb {
  private readonly store = inject(Store);
  private readonly assetService = inject(AssetService);

  protected readonly items     = this.store.selectSignal(trashSelectors.selectAll);
  protected readonly total     = this.store.selectSignal(trashSelectors.selectTotal);
  protected readonly isLoading  = this.store.selectSignal(trashSelectors.selectIsLoading);

  protected readonly formatDate = formatDate;
  protected readonly formatBytes = formatBytes;

  constructor() {
    this.store.dispatch(trashActions.load());
  }

  protected thumbnailUrl(asset: AssetDto): string {
    return this.assetService.thumbnailUrl(asset.id, 256, asset.content_hash);
  }

  protected onRestore(id: number): void {
    this.store.dispatch(trashActions.restore({ id }));
  }

  protected onPurge(id: number): void {
    this.store.dispatch(trashActions.purge({ id }));
  }

  protected onEmpty(): void {
    this.store.dispatch(trashActions.empty());
  }
}
