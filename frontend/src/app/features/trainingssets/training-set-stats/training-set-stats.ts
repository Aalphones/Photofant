import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import type { DistItem, TrainingSetStats } from '@photofant/models';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-training-set-stats',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './training-set-stats.html',
  styleUrl: './training-set-stats.scss',
})
export class TrainingSetStatsPanel {
  readonly stats = input.required<TrainingSetStats>();
  readonly close = output<void>();

  protected readonly maxFramingCount = computed((): number => this.maxCount(this.stats().framing));
  protected readonly maxTagCount = computed((): number =>
    Math.max(1, ...this.stats().tag_frequencies.map((item) => item.count)));
  protected readonly maxQualityCount = computed((): number =>
    Math.max(1, ...this.stats().quality_histogram.map((item) => item.count)));
  protected readonly maxBucketCount = computed((): number => this.maxCount(this.stats().ar_buckets));

  protected readonly nearDupePercent = computed((): string =>
    `${Math.round(this.stats().near_dupe_rate * 100)}%`);

  private maxCount(items: DistItem[]): number {
    return Math.max(1, ...items.map((item: DistItem) => item.count));
  }

  protected barWidth(count: number, max: number): string {
    return `${Math.round((count / max) * 100)}%`;
  }

  protected framingLabel(value: string): string {
    if (value === 'close_up') { return 'Close-Up'; }
    if (value === 'medium') { return 'Medium'; }
    if (value === 'full_body') { return 'Full Body'; }
    return value;
  }

  protected onClose(): void {
    this.close.emit();
  }
}
