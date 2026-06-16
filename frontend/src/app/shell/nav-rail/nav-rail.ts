import { ChangeDetectionStrategy, Component, output } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
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

  protected readonly mainItems: readonly NavItem[] = [
    { id: 'galerie',      icon: 'gallery',  label: 'Galerie',      count: 0 },
    { id: 'personen',     icon: 'people',   label: 'Personen',     count: 0 },
    { id: 'alben',        icon: 'album',    label: 'Alben',        count: 0 },
    { id: 'trainingssets',icon: 'training', label: 'Trainingssets',count: 0 },
  ];

  protected readonly toolItems: readonly NavItem[] = [
    { id: 'modelle',       icon: 'model',    label: 'Modelle'      },
    { id: 'papierkorb',    icon: 'trash',    label: 'Papierkorb'   },
    { id: 'einstellungen', icon: 'settings', label: 'Einstellungen'},
  ];
}
