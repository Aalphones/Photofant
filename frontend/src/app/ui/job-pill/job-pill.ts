import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { Icon } from '../icon/icon';

@Component({
  selector: 'pf-job-pill',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './job-pill.html',
  styleUrl: './job-pill.scss',
})
export class JobPill {
  readonly activeCount = input.required<number>();
  readonly isOpen     = input<boolean>(false);
  readonly toggle     = output<void>();
}
