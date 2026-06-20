import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideStore } from '@ngrx/store';
import { provideEffects } from '@ngrx/effects';
import { routes } from './app.routes';
import { jobsFeature, JobsEffects, filtersFeature, searchFeature, galleryFeature, GalleryEffects, trashFeature, TrashEffects, maintenanceFeature, MaintenanceEffects, modelsFeature, ModelsEffects, presetsFeature, PresetsEffects, tagsFeature, TagsEffects, collectionsFeature, CollectionsEffects, reviewFeature, ReviewEffects, personsFeature, PersonsEffects } from './store';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(),
    provideStore({
      [jobsFeature.name]:        jobsFeature.reducer,
      [filtersFeature.name]:     filtersFeature.reducer,
      [searchFeature.name]:      searchFeature.reducer,
      [galleryFeature.name]:     galleryFeature.reducer,
      [trashFeature.name]:       trashFeature.reducer,
      [maintenanceFeature.name]: maintenanceFeature.reducer,
      [modelsFeature.name]:      modelsFeature.reducer,
      [presetsFeature.name]:     presetsFeature.reducer,
      [tagsFeature.name]:        tagsFeature.reducer,
      [collectionsFeature.name]: collectionsFeature.reducer,
      [reviewFeature.name]:      reviewFeature.reducer,
      [personsFeature.name]:     personsFeature.reducer,
    }),
    provideEffects([JobsEffects, GalleryEffects, TrashEffects, MaintenanceEffects, ModelsEffects, PresetsEffects, TagsEffects, CollectionsEffects, ReviewEffects, PersonsEffects]),
  ],
};
