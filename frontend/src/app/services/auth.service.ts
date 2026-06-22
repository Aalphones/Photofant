import { inject, Injectable, PLATFORM_ID, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { map, Observable, of, tap } from 'rxjs';

interface AuthStatusResponse {
  has_password: boolean;
}

interface UnlockResponse {
  success: boolean;
}

const SESSION_KEY = 'pf-unlocked';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  readonly isUnlocked = signal(this.loadFromSession());
  private readonly hasPasswordState = signal<boolean | null>(null);

  private loadFromSession(): boolean {
    if (!this.isBrowser) {
      return false;
    }
    return sessionStorage.getItem(SESSION_KEY) === 'true';
  }

  /** Fetches password status from the backend (result cached in signal). */
  loadStatusOnce(): Observable<boolean> {
    const cached = this.hasPasswordState();
    if (cached !== null) {
      return of(cached);
    }
    return this.http.get<AuthStatusResponse>('/api/auth/status').pipe(
      map((response: AuthStatusResponse) => response.has_password),
      tap((hasPassword: boolean) => this.hasPasswordState.set(hasPassword)),
    );
  }

  /** Sends the password to the backend and marks session as unlocked on success. */
  tryUnlock(password: string): Observable<boolean> {
    return this.http.post<UnlockResponse>('/api/auth/unlock', { password }).pipe(
      map((response: UnlockResponse) => response.success),
      tap((success: boolean) => {
        if (success) {
          this.markUnlocked();
        }
      }),
    );
  }

  /** Marks the session as unlocked without a password check (used when no password is configured). */
  markUnlocked(): void {
    if (this.isBrowser) {
      sessionStorage.setItem(SESSION_KEY, 'true');
    }
    this.isUnlocked.set(true);
  }
}
