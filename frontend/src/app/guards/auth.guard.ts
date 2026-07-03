import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map, of, switchMap } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isUnlocked()) {
    return true;
  }

  return auth.loadStatusOnce().pipe(
    switchMap((hasPassword: boolean) => {
      if (!hasPassword) {
        auth.markUnlocked();
        return of(true);
      }
      // Vor der Passwortabfrage kurz nachfragen: läuft schon eine entsperrte Tab?
      return auth.checkOtherTabs();
    }),
    map((unlocked: boolean) => (unlocked ? true : router.createUrlTree(['/entsperren']))),
  );
};
