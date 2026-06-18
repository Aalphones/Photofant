import { inject, Injectable, PLATFORM_ID, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import type { Density } from '@photofant/models';

export type Locale = 'de' | 'en';
export type DateFormat = 'dmy' | 'ymd' | 'mdy';

interface DisplaySettings {
  showMeta: boolean;
  reducedMotion: boolean;
  locale: Locale;
  dateFormat: DateFormat;
  density: Density;
}

const STORAGE_KEY = 'pf-display-settings';

const DEFAULTS: DisplaySettings = {
  showMeta: true,
  reducedMotion: false,
  locale: 'de',
  dateFormat: 'dmy',
  density: 'md',
};

@Injectable({ providedIn: 'root' })
export class SettingsService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  private readonly state = signal<DisplaySettings>(this.load());

  readonly showMeta = () => this.state().showMeta;
  readonly reducedMotion = () => this.state().reducedMotion;
  readonly locale = () => this.state().locale;
  readonly dateFormat = () => this.state().dateFormat;
  readonly density = () => this.state().density;

  readonly snapshot = this.state.asReadonly();

  setShowMeta(value: boolean): void {
    this.patch({ showMeta: value });
  }

  setReducedMotion(value: boolean): void {
    this.patch({ reducedMotion: value });
  }

  setLocale(value: Locale): void {
    this.patch({ locale: value });
  }

  setDateFormat(value: DateFormat): void {
    this.patch({ dateFormat: value });
  }

  setDensity(value: Density): void {
    this.patch({ density: value });
  }

  private patch(partial: Partial<DisplaySettings>): void {
    this.state.update((current: DisplaySettings) => {
      const next = { ...current, ...partial };
      this.persist(next);
      return next;
    });
  }

  private load(): DisplaySettings {
    if (!this.isBrowser) {
      return { ...DEFAULTS };
    }
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw == null) {
        return { ...DEFAULTS };
      }
      return { ...DEFAULTS, ...JSON.parse(raw) as Partial<DisplaySettings> };
    } catch {
      return { ...DEFAULTS };
    }
  }

  private persist(settings: DisplaySettings): void {
    if (!this.isBrowser) {
      return;
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch {
      // quota exceeded — ignore silently
    }
  }
}
