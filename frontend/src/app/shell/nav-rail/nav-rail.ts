import { ChangeDetectionStrategy, Component, computed, inject, output } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { Store } from '@ngrx/store';
import { gallerySelectors } from '@photofant/store';
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

  private readonly store = inject(Store);

  private readonly galerieCount = this.store.selectSignal(gallerySelectors.selectServerTotal);

  // Personen/Alben/Trainingssets have no backend yet (P6/P7) — no count chip until they do.
  protected readonly mainItems = computed<readonly NavItem[]>(() => [
    { id: 'galerie',      icon: 'gallery',  label: 'Galerie', count: this.galerieCount() },
    { id: 'personen',     icon: 'people',   label: 'Personen'      },
    { id: 'alben',        icon: 'album',    label: 'Alben'         },
    { id: 'trainingssets',icon: 'training', label: 'Trainingssets' },
  ]);

  protected readonly toolItems: readonly NavItem[] = [
    { id: 'modelle',       icon: 'model',    label: 'Modelle'      },
    { id: 'papierkorb',    icon: 'trash',    label: 'Papierkorb'   },
    { id: 'einstellungen', icon: 'settings', label: 'Einstellungen'},
  ];
}
