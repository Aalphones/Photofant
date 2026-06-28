import { ChangeDetectionStrategy, Component, computed, inject, output } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { Store } from '@ngrx/store';
import { gallerySelectors, reviewSelectors } from '@photofant/store';
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
  private readonly reviewCount = this.store.selectSignal(reviewSelectors.selectTotal);

  // Personen/Alben/Favoriten/Trainingssets have no backend yet (P7/P10) — no count chip until they do.
  protected readonly mainItems = computed<readonly NavItem[]>(() => [
    { id: 'galerie',      icon: 'gallery',  label: 'Galerie', count: this.galerieCount() },
    { id: 'personen',     icon: 'people',   label: 'Personen'      },
    { id: 'favoriten',    icon: 'star',     label: 'Favoriten'     },
    { id: 'alben',        icon: 'album',    label: 'Alben'         },
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
