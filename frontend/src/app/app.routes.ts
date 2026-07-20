import { Routes } from '@angular/router';
import { Shell } from './shell/shell';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: 'entsperren',
    loadComponent: () =>
      import('./features/unlock/unlock').then((m) => m.Unlock),
  },
  {
    path: 'editor/:kind/:id',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/editor/editor').then((m) => m.Editor),
  },
  {
    // Kein `canActivate` mehr hier: ein Guard auf dem Leerpfad-Elternknoten läuft laut
    // Angular-Router bei bestimmten Kind-zu-Kind-Navigationen (z.B. Lightbox -> /wissen)
    // erneut mit, statt nur einmal beim Betreten des Baums — das hatte den „Wissen
    // anlegen"-Button auf den Entsperren-Screen zurückgeworfen. Der Guard sitzt deshalb
    // jetzt auf jeder Kindroute einzeln (läuft dort nur bei echter Neu-Aktivierung dieser
    // konkreten Route, nicht bei jedem Geschwister-Wechsel).
    path: '',
    component: Shell,
    children: [
      { path: '', redirectTo: 'galerie', pathMatch: 'full' },
      {
        path: 'galerie',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./features/galerie/galerie').then((m) => m.Galerie),
      },
      {
        path: 'personen',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./features/personen/personen').then((m) => m.Personen),
      },
      {
        path: 'favoriten',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./features/favoriten/favoriten').then((m) => m.Favoriten),
      },
      {
        path: 'alben',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./features/alben/alben').then((m) => m.Alben),
      },
      {
        path: 'wissen',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./features/wissen/wissen').then((m) => m.Wissen),
      },
      {
        path: 'trainingssets',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./features/trainingssets/trainingssets').then(
            (m) => m.Trainingssets
          ),
      },
      {
        path: 'review',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./features/review/review').then((m) => m.Review),
      },
      {
        path: 'modelle',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./features/modelle/modelle').then((m) => m.Modelle),
      },
      {
        path: 'papierkorb',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./features/papierkorb/papierkorb').then((m) => m.Papierkorb),
      },
      {
        path: 'wartung',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./features/wartung/wartung').then((m) => m.Wartung),
      },
      {
        path: 'einstellungen',
        canActivate: [authGuard],
        loadComponent: () =>
          import('./features/einstellungen/einstellungen').then(
            (m) => m.Einstellungen
          ),
      },
    ],
  },
  { path: '**', redirectTo: 'galerie' },
];
