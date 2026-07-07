import { ChangeDetectionStrategy, Component, inject, input, output } from '@angular/core';
import { AssetService } from '@photofant/services';
import type { RelatedRailItem } from '@photofant/models';

// Generische „Ähnliche Bilder"-Kartenliste (P36). Rendert {assetId, score, reasons} —
// P36 übergibt reasons = null, P26 (Recommendation Engine) nutzt dieselbe Komponente
// später mit befüllter Begründungskette an derselben Stelle.
@Component({
  selector: 'pf-related-rail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './related-rail.html',
  styleUrl: './related-rail.scss',
})
export class RelatedRail {
  private readonly assetService = inject(AssetService);

  readonly items = input<RelatedRailItem[]>([]);
  readonly loading = input(false);
  readonly emptyMessage = input<string | null>(null);

  readonly cardClick = output<number>();

  protected thumbnailUrl(assetId: number): string {
    return this.assetService.thumbnailUrl(assetId, 256);
  }

  protected scorePercent(item: RelatedRailItem): number {
    return Math.round(item.score * 100);
  }
}
