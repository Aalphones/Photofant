import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type { AssetDto, Facets, FaceGalleryItemDto } from '@photofant/models';

export const galleryActions = createActionGroup({
  source: 'Gallery',
  events: {
    'Set Page Size':             props<{ pageSize: number }>(),
    'Request Page':              emptyProps(),
    // Album lightbox: inject ordered context so prev/next navigates within the album
    'Set Lightbox Context':      props<{ assets: AssetDto[] }>(),
    'Request Next Page':         emptyProps(),
    'Reset':                     emptyProps(),
    'Load Page Success':         props<{ items: AssetDto[]; total: number; page: number; pageSize: number; facets: Facets }>(),
    'Load Faces Page Success':   props<{ items: FaceGalleryItemDto[]; total: number; page: number; pageSize: number }>(),
    'Load Page Failure':         props<{ error: string }>(),
    'Open Lightbox':             props<{ id: number }>(),
    // Opens the parent asset lightbox from face-gallery mode (fetches asset first)
    'Open Face Lightbox':        props<{ assetId: number }>(),
    'Inject Asset':              props<{ asset: AssetDto }>(),
    'Close Lightbox':            emptyProps(),
    'Lightbox Go To':            props<{ id: number }>(),
    'Lightbox Next':             emptyProps(),
    'Lightbox Prev':             emptyProps(),
    'Lightbox Mark Pending Next': emptyProps(),
    'Toggle Favourite':          props<{ id: number; value: boolean }>(),
    'Toggle Favourite Success':  props<{ asset: AssetDto }>(),
    'Toggle Favourite Failure':  props<{ id: number; previous: boolean }>(),
    'Delete Asset':              props<{ id: number }>(),
    'Delete Asset Success':      props<{ id: number }>(),
    'Delete Asset Failure':      props<{ error: string }>(),
    // Selection
    'Enable Selection Mode':     emptyProps(),
    'Disable Selection Mode':    emptyProps(),
    'Toggle Selected':           props<{ id: number }>(),
    'Select All':                props<{ ids: number[] }>(),
    'Select Range':              props<{ ids: number[] }>(),
    'Clear Selection':           emptyProps(),
  },
});
