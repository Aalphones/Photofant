import { Routes } from '@angular/router';
import { Shell } from './shell/shell';

export const routes: Routes = [
  {
    path: 'editor/:kind/:id',
    loadComponent: () =>
      import('./features/editor/editor').then((m) => m.Editor),
  },
  {
    path: '',
    component: Shell,
    children: [
      { path: '', redirectTo: 'galerie', pathMatch: 'full' },
      {
        path: 'galerie',
        loadComponent: () =>
          import('./features/galerie/galerie').then((m) => m.Galerie),
      },
      {
        path: 'personen',
        loadComponent: () =>
          import('./features/personen/personen').then((m) => m.Personen),
      },
      {
        path: 'favoriten',
        loadComponent: () =>
          import('./features/favoriten/favoriten').then((m) => m.Favoriten),
      },
      {
        path: 'alben',
        loadComponent: () =>
          import('./features/alben/alben').then((m) => m.Alben),
      },
      {
        path: 'trainingssets',
        loadComponent: () =>
          import('./features/trainingssets/trainingssets').then(
            (m) => m.Trainingssets
          ),
      },
      {
        path: 'review',
        loadComponent: () =>
          import('./features/review/review').then((m) => m.Review),
      },
      {
        path: 'modelle',
        loadComponent: () =>
          import('./features/modelle/modelle').then((m) => m.Modelle),
      },
      {
        path: 'papierkorb',
        loadComponent: () =>
          import('./features/papierkorb/papierkorb').then((m) => m.Papierkorb),
      },
      {
        path: 'wartung',
        loadComponent: () =>
          import('./features/wartung/wartung').then((m) => m.Wartung),
      },
      {
        path: 'einstellungen',
        loadComponent: () =>
          import('./features/einstellungen/einstellungen').then(
            (m) => m.Einstellungen
          ),
      },
    ],
  },
  { path: '**', redirectTo: 'galerie' },
];
