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
    // versionId: P21-Stapel — initiale Stage-Auswahl (welche Version zuerst gezeigt wird),
    // ändert nicht `is_current` in der DB
    'Open Lightbox':             props<{ id: number; versionId?: number | null }>(),
    // Opens an asset that may not be preloaded yet (fetches it first, then injects + opens)
    'Open Asset Lightbox':       props<{ assetId: number }>(),
    // Opens the Lightbox in Gesichter-Modus on a face's own image/versions
    'Open Face Lightbox':        props<{ faceId: number; assetId: number | null; versionId?: number | null }>(),
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
    'Remove Face Item':          props<{ id: number }>(),
    // Face-Selection — eigene ID-Liste, teilt sich `selectionMode`/Enable/Disable/Clear mit den
    // Asset-Aktionen oben (ein Schalter für beide Tabs, siehe GalleryState-Kommentar)
    'Toggle Face Selected':      props<{ id: number }>(),
    'Select All Faces':          props<{ ids: number[] }>(),
    'Select Face Range':         props<{ ids: number[] }>(),
  },
});
