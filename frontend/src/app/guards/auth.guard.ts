import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isUnlocked()) {
    return true;
  }

  return auth.loadStatusOnce().pipe(
    map((hasPassword: boolean) => {
      if (!hasPassword) {
        auth.markUnlocked();
        return true;
      }
      return router.createUrlTree(['/entsperren']);
    }),
  );
};
