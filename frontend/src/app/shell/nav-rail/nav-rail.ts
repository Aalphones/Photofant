import { ChangeDetectionStrategy, Component, computed, effect, inject, output } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { Store } from '@ngrx/store';
import { gallerySelectors, maintenanceActions, maintenanceSelectors, reviewSelectors } from '@photofant/store';
import { Icon } from '../../ui/icon/icon';

interface NavItem {
  readonly id: string;
  readonly icon: string;
  readonly label: string;
  readonly count?: number;
}

@Component({
  selector: 'pf-nav-rail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive, Icon],
  templateUrl: './nav-rail.html',
  styleUrl: './nav-rail.scss',
})
export class NavRail {
  readonly close = output<void>();
  readonly importClick = output<void>();

  private readonly store = inject(Store);

  private readonly galerieCount = this.store.selectSignal(gallerySelectors.selectServerTotal);
  // selectTotal ist die geladene Seite (max DUPE_PAGE_SIZE) — das Badge braucht die
  // echte Backend-Zahl offener Paare, siehe P31 Phase 3.
  private readonly reviewCount = this.store.selectSignal(reviewSelectors.selectServerTotal);
  private readonly storageStatus = this.store.selectSignal(maintenanceSelectors.selectStatus);

  protected readonly diskFreeLabel = computed<string>(() => {
    const status = this.storageStatus();
    if (!status || status.disk_total === 0) {
      return '—';
    }
    return this.formatBytes(status.disk_total - status.disk_used) + ' frei';
  });

  protected readonly diskUsedPercent = computed<number>(() => {
    const status = this.storageStatus();
    if (!status || status.disk_total === 0) {
      return 0;
    }
    return Math.round((status.disk_used / status.disk_total) * 100);
  });

  protected readonly libraryLabel = computed<string>(() => {
    const status = this.storageStatus();
    if (!status) {
      return 'Bibliothek —';
    }
    const libraryBytes = status.db_size + status.cache_size;
    if (libraryBytes === 0) {
      return 'Bibliothek leer';
    }
    return 'Bibliothek ' + this.formatBytes(libraryBytes);
  });

  constructor() {
    effect(() => {
      this.store.dispatch(maintenanceActions.loadStatus());
    });
  }

  private formatBytes(bytes: number): string {
    if (bytes < 1024) {
      return `${bytes} B`;
    }
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    if (bytes < 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  }

  // Personen/Alben/Favoriten/Trainingssets have no backend yet (P7/P10) — no count chip until they do.
  protected readonly mainItems = computed<readonly NavItem[]>(() => [
    { id: 'galerie',      icon: 'gallery',  label: 'Galerie', count: this.galerieCount() },
    { id: 'personen',     icon: 'people',   label: 'Personen'      },
    { id: 'favoriten',    icon: 'star',     label: 'Favoriten'     },
    { id: 'alben',        icon: 'album',    label: 'Alben'         },
    { id: 'wissen',       icon: 'text',     label: 'Wissen'        },
    { id: 'trainingssets',icon: 'training', label: 'Trainingssets' },
  ]);

  protected readonly toolItems = computed<readonly NavItem[]>(() => {
    const dupeCount = this.reviewCount();
    return [
      { id: 'review',        icon: 'face',     label: 'Review-Queue', ...(dupeCount > 0 ? { count: dupeCount } : {}) },
      { id: 'modelle',       icon: 'model',    label: 'Modelle'      },
      { id: 'papierkorb',    icon: 'trash',    label: 'Papierkorb'   },
      { id: 'wartung',       icon: 'wrench',   label: 'Wartung'      },
      { id: 'einstellungen', icon: 'settings', label: 'Einstellungen'},
    ];
  });
}
