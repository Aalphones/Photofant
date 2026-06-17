import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Icon } from '../icon/icon';

@Component({
  selector: 'pf-gated-feature',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, RouterLink],
  templateUrl: './gated-feature.html',
  styleUrl: './gated-feature.scss',
  host: { class: 'gated-feature' },
})
export class GatedFeature {
  readonly featureName = input.required<string>();
  readonly modelHint = input<string>('');
}
