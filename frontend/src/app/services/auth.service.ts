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

type AuthBroadcastMessage = { type: 'ping' } | { type: 'pong' } | { type: 'unlocked' };

const CHANNEL_NAME = 'pf-auth';
// Wie lange eine frische Tab auf Antwort von bereits offenen, entsperrten Tabs wartet,
// bevor sie die Passwortabfrage zeigt. Nur diese Handshake-Runde entscheidet — es wird
// nichts persistiert, daher fragt jede neue Tab nach, sobald wirklich keine andere mehr lebt.
const PING_TIMEOUT_MS = 200;

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  private readonly channel = this.createChannel();

  readonly isUnlocked = signal(false);
  private readonly hasPasswordState = signal<boolean | null>(null);

  constructor() {
    this.channel?.addEventListener('message', (event: MessageEvent<AuthBroadcastMessage>) => {
      if (event.data.type === 'ping' && this.isUnlocked()) {
        this.channel?.postMessage({ type: 'pong' } satisfies AuthBroadcastMessage);
      }
      if (event.data.type === 'unlocked') {
        this.isUnlocked.set(true);
      }
    });
  }

  private createChannel(): BroadcastChannel | null {
    if (!this.isBrowser || typeof BroadcastChannel === 'undefined') {
      return null;
    }
    return new BroadcastChannel(CHANNEL_NAME);
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

  /**
   * Fragt per Broadcast andere offene Tabs, ob sie schon entsperrt sind, und übernimmt
   * deren Status. Antwortet niemand rechtzeitig (z.B. weil es keine andere Tab gibt),
   * bleibt die Sperre bestehen.
   */
  checkOtherTabs(): Observable<boolean> {
    const channel = this.channel;
    if (!channel) {
      return of(false);
    }
    return new Observable<boolean>((subscriber) => {
      const onMessage = (event: MessageEvent<AuthBroadcastMessage>): void => {
        if (event.data.type === 'pong') {
          finish(true);
        }
      };
      const timer = setTimeout(() => finish(false), PING_TIMEOUT_MS);
      const finish = (result: boolean): void => {
        clearTimeout(timer);
        channel.removeEventListener('message', onMessage);
        if (result) { this.isUnlocked.set(true); }
        subscriber.next(result);
        subscriber.complete();
      };
      channel.addEventListener('message', onMessage);
      channel.postMessage({ type: 'ping' } satisfies AuthBroadcastMessage);
      return () => {
        clearTimeout(timer);
        channel.removeEventListener('message', onMessage);
      };
    });
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
    this.isUnlocked.set(true);
    this.channel?.postMessage({ type: 'unlocked' } satisfies AuthBroadcastMessage);
  }
}
