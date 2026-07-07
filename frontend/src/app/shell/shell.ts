import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Store } from '@ngrx/store';
import { filter, map, startWith } from 'rxjs';
import { filtersSelectors, jobsActions, jobsSelectors } from '../store';
import { NavRail } from './nav-rail/nav-rail';
import { TopBar } from './top-bar/top-bar';
import { JobDock } from '../ui/job-dock/job-dock';
import { Icon } from '../ui/icon/icon';
import { ImportDialog } from '../ui/import-dialog/import-dialog';

const ROUTE_TITLES: Record<string, string> = {
  galerie:       'Galerie',
  personen:      'Personen',
  favoriten:     'Favoriten',
  alben:         'Alben',
  trainingssets: 'Trainingssets',
  review:        'Review-Queue',
  modelle:       'Modelle',
  einstellungen: 'Einstellungen',
};

@Component({
  selector: 'pf-shell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, NavRail, TopBar, JobDock, Icon, ImportDialog],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  private readonly store      = inject(Store);
  private readonly router     = inject(Router);
  private readonly document   = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly isNavOpen       = signal(false);
  protected readonly isImportOpen    = signal(false);
  protected readonly droppedFiles    = signal<File[]>([]);
  protected readonly isDraggingFiles = signal(false);
  protected readonly importPersonId  = signal<number | null>(null);

  protected readonly isDockOpen = this.store.selectSignal(jobsSelectors.isDockOpen);
  protected readonly activeJobs = this.store.selectSignal(jobsSelectors.activeCount);
  protected readonly allJobs    = this.store.selectSignal(jobsSelectors.sortedJobs);
  private readonly activePersonId = this.store.selectSignal(filtersSelectors.personId);

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
    this.registerGlobalDnD();
  }

  private registerGlobalDnD(): void {
    let depth = 0;

    const onEnter = (event: DragEvent): void => {
      if (!event.dataTransfer?.types.includes('Files')) return;
      event.preventDefault();
      depth++;
      this.isDraggingFiles.set(true);
    };

    const onLeave = (): void => {
      depth--;
      if (depth <= 0) {
        depth = 0;
        this.isDraggingFiles.set(false);
      }
    };

    const onOver = (event: DragEvent): void => {
      event.preventDefault();
    };

    const onDrop = (event: DragEvent): void => {
      event.preventDefault();
      depth = 0;
      this.isDraggingFiles.set(false);
      // Drop auf die Suchbox ist Reverse-Image-Suche (P36) — die Suchbox handhabt ihn
      // selbst; hier nicht zusätzlich den Import-Dialog öffnen.
      const target = event.target as HTMLElement | null;
      if (target?.closest('pf-search-box') != null) { return; }
      const files = event.dataTransfer?.files;
      if (files && files.length > 0) {
        const images = Array.from(files).filter((file: File) =>
          file.type.startsWith('image/')
        );
        this.droppedFiles.set(images);
        this.importPersonId.set(this.resolveImportPersonId());
        this.isImportOpen.set(true);
      }
    };

    this.document.addEventListener('dragenter', onEnter);
    this.document.addEventListener('dragleave', onLeave);
    this.document.addEventListener('dragover', onOver);
    this.document.addEventListener('drop', onDrop);

    this.destroyRef.onDestroy(() => {
      this.document.removeEventListener('dragenter', onEnter);
      this.document.removeEventListener('dragleave', onLeave);
      this.document.removeEventListener('dragover', onOver);
      this.document.removeEventListener('drop', onDrop);
    });
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

  protected clearDoneJobs(): void {
    this.store.dispatch(jobsActions.clearDoneJobs());
  }

  protected openImport(): void {
    this.droppedFiles.set([]);
    this.importPersonId.set(this.resolveImportPersonId());
    this.isImportOpen.set(true);
  }

  protected openImportFromNav(): void {
    this.isNavOpen.set(false);
    this.openImport();
  }

  protected closeImport(): void {
    this.isImportOpen.set(false);
    this.droppedFiles.set([]);
    this.importPersonId.set(null);
  }

  // Person-Upload-Pfad nur auf /galerie mit aktivem Personen-Filter, sonst normaler Import.
  private resolveImportPersonId(): number | null {
    return this.router.url.startsWith('/galerie') ? this.activePersonId() : null;
  }

  protected onImported(): void {
    this.store.dispatch(jobsActions.toggleDock());
  }
}
