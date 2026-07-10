import { ChangeDetectionStrategy, Component, inject, input, output } from '@angular/core';
import { AssetService } from '@photofant/services';
import type { ExplainabilityPayload, RelatedRailItem } from '@photofant/models';
import { ExplainabilityPopover } from '@photofant/ui';

// Generische „Ähnliche Bilder"-Kartenliste (P36). Rendert {assetId, score, reasons} —
// P36 übergibt reasons = null, P26 (Recommendation Engine) nutzt dieselbe Komponente
// später mit befüllter Begründungskette an derselben Stelle.
//
// Explainability (P26 Phase 3): das „Warum?"/„Warum nicht?"-Icon + Popover bleibt hier bewusst
// generisch (kein HTTP-Call, kein Domänenwissen) — der Aufrufer liefert Label + Payload/Loading
// für genau die Karte, deren Popover offen ist (`explainOpenId`), und reagiert auf die
// Open/Close-Outputs. So bleibt die Rail für andere Rail-Nutzungen unverändert nutzbar.
@Component({
  selector: 'pf-related-rail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ExplainabilityPopover],
  templateUrl: './related-rail.html',
  styleUrl: './related-rail.scss',
})
export class RelatedRail {
  private readonly assetService = inject(AssetService);

  readonly items = input<RelatedRailItem[]>([]);
  readonly loading = input(false);
  readonly loadingMessage = input('Suche läuft…');
  readonly emptyMessage = input<string | null>(null);

  // null = kein Explainability-Icon auf den Karten (Default — Rückwärtskompatibel für
  // andere Rail-Nutzungen ohne „Warum?").
  readonly explainLabel = input<string | null>(null);
  readonly explainOpenId = input<number | null>(null);
  readonly explainPayload = input<ExplainabilityPayload | null>(null);
  readonly explainLoading = input(false);

  readonly cardClick = output<number>();
  readonly explainOpen = output<number>();
  readonly explainClose = output<void>();

  protected thumbnailUrl(assetId: number): string {
    return this.assetService.thumbnailUrl(assetId, 256);
  }

  protected scorePercent(item: RelatedRailItem): number {
    return Math.round(item.score * 100);
  }

  protected onExplainClick(assetId: number): void {
    if (this.explainOpenId() === assetId) {
      this.explainClose.emit();
      return;
    }
    this.explainOpen.emit(assetId);
  }
}
