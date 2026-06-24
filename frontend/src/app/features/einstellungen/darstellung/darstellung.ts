import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { Store } from '@ngrx/store';
import type { Density } from '@photofant/models';
import type { DateFormat, GalleryPageSize, Locale } from '@photofant/services';
import { SettingsService } from '@photofant/services';
import { filtersActions, galleryActions } from '@photofant/store';

@Component({
  selector: 'pf-einstellungen-darstellung',
  imports: [],
  templateUrl: './darstellung.html',
  styleUrl: './darstellung.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Darstellung {
  private readonly store = inject(Store);
  private readonly settings = inject(SettingsService);

  readonly displaySettings = this.settings.snapshot;

  setDensity(value: Density): void {
    this.store.dispatch(filtersActions.setDensity({ density: value }));
  }

  setShowMeta(value: boolean): void {
    this.settings.setShowMeta(value);
  }

  setReducedMotion(value: boolean): void {
    this.settings.setReducedMotion(value);
  }

  setLocale(value: Locale): void {
    this.settings.setLocale(value);
  }

  setDateFormat(value: DateFormat): void {
    this.settings.setDateFormat(value);
  }

  setGalleryPageSize(value: number): void {
    this.store.dispatch(galleryActions.setPageSize({ pageSize: value as GalleryPageSize }));
  }
}
