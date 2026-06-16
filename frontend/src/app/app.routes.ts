import { Routes } from '@angular/router';
import { Shell } from './shell/shell';

export const routes: Routes = [
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
