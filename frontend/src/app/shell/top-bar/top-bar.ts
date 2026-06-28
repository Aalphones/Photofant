import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { Icon } from '../../ui/icon/icon';
import { JobPill } from '../../ui/job-pill/job-pill';
import { SearchBox } from '../../ui/search-box/search-box';

@Component({
  selector: 'pf-top-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, JobPill, SearchBox],
  templateUrl: './top-bar.html',
  styleUrl: './top-bar.scss',
})
export class TopBar {
  readonly title      = input<string>('Photofant');
  readonly activeJobs = input<number>(0);
  readonly isDockOpen = input<boolean>(false);

  readonly menuToggle = output<void>();
  readonly dockToggle = output<void>();
}
