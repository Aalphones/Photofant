import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Store } from '@ngrx/store';
import { filter, map, startWith } from 'rxjs';
import { jobsActions, jobsSelectors } from '../store';
import { NavRail } from './nav-rail/nav-rail';
import { TopBar } from './top-bar/top-bar';
import { JobDock } from '../ui/job-dock/job-dock';
import { Icon } from '../ui/icon/icon';

const ROUTE_TITLES: Record<string, string> = {
  galerie:       'Galerie',
  personen:      'Personen',
  alben:         'Alben',
  trainingssets: 'Trainingssets',
  modelle:       'Modelle',
  einstellungen: 'Einstellungen',
};

@Component({
  selector: 'pf-shell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, NavRail, TopBar, JobDock, Icon],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  private readonly store = inject(Store);
  private readonly router = inject(Router);

  protected readonly isNavOpen = signal(false);

  protected readonly isDockOpen = this.store.selectSignal(jobsSelectors.isDockOpen);
  protected readonly activeJobs = this.store.selectSignal(jobsSelectors.activeCount);
  protected readonly allJobs    = this.store.selectSignal(jobsSelectors.allJobs);

  protected readonly activeRoute = toSignal(
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      map((event: NavigationEnd) => event.url.split('/')[1] ?? 'galerie'),
      startWith(this.router.url.split('/')[1] ?? 'galerie'),
    ),
    { initialValue: 'galerie' },
  );

  protected readonly pageTitle = (): string =>
    ROUTE_TITLES[this.activeRoute() ?? ''] ?? 'Photofant';

  constructor() {
    this.store.dispatch(jobsActions.loadStream());
  }

  protected toggleNav(): void {
    this.isNavOpen.update((isOpen: boolean) => !isOpen);
  }

  protected toggleDock(): void {
    this.store.dispatch(jobsActions.toggleDock());
  }

  protected closeDock(): void {
    this.store.dispatch(jobsActions.closeDock());
  }
}
