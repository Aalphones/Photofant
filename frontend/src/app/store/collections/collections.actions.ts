import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type {
  Collection,
  CollectionDetail,
  CreateCollectionRequest,
  CreateTriggerRequest,
  UpdateCollectionRequest,
} from '@photofant/models';

export const collectionsActions = createActionGroup({
  source: 'Collections',
  events: {
    'Load':                  emptyProps(),
    'Load Success':          props<{ items: Collection[] }>(),
    'Load Failure':          props<{ error: string }>(),

    'Load Detail':           props<{ id: number }>(),
    'Load Detail Success':   props<{ detail: CollectionDetail }>(),
    'Load Detail Failure':   props<{ error: string }>(),
    'Clear Detail':          emptyProps(),

    'Create':                props<{ request: CreateCollectionRequest }>(),
    'Create Success':        props<{ detail: CollectionDetail }>(),
    'Create Failure':        props<{ error: string }>(),

    'Update':                props<{ id: number; request: UpdateCollectionRequest }>(),
    'Update Success':        props<{ detail: CollectionDetail }>(),
    'Update Failure':        props<{ error: string }>(),

    'Delete':                props<{ id: number }>(),
    'Delete Success':        props<{ id: number }>(),
    'Delete Failure':        props<{ error: string }>(),

    'Add Trigger':           props<{ collectionId: number; request: CreateTriggerRequest }>(),
    'Add Trigger Success':   props<{ collectionId: number }>(),
    'Add Trigger Failure':   props<{ error: string }>(),

    'Update Trigger':        props<{ collectionId: number; triggerId: number; negate: boolean }>(),
    'Update Trigger Success': props<{ collectionId: number }>(),
    'Update Trigger Failure': props<{ error: string }>(),

    'Delete Trigger':        props<{ collectionId: number; triggerId: number }>(),
    'Delete Trigger Success': props<{ collectionId: number }>(),
    'Delete Trigger Failure': props<{ error: string }>(),

    'Add Items':             props<{ collectionId: number; assetIds: number[] }>(),
    'Add Items Success':     emptyProps(),
    'Add Items Failure':     props<{ error: string }>(),
  },
});
