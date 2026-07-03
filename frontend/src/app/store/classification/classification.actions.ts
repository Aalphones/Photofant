import { createActionGroup, emptyProps, props } from '@ngrx/store';
import type {
  CategoryPatchRequest,
  ClassificationCategory,
  ClassificationLabel,
  ClassificationMode,
  LabelPatchRequest,
} from '@photofant/models';

export const classificationActions = createActionGroup({
  source: 'Classification',
  events: {
    'Load':          emptyProps(),
    'Load Success':  props<{ categories: ClassificationCategory[] }>(),
    'Load Failure':  props<{ error: string }>(),

    'Create Category':         props<{ name: string; mode: ClassificationMode }>(),
    'Create Category Success': props<{ category: ClassificationCategory }>(),
    'Create Category Failure': props<{ error: string }>(),

    'Patch Category':         props<{ id: number; patch: CategoryPatchRequest }>(),
    'Patch Category Success': props<{ category: ClassificationCategory }>(),
    'Patch Category Failure': props<{ error: string }>(),

    'Delete Category':         props<{ id: number }>(),
    'Delete Category Success': props<{ id: number }>(),
    'Delete Category Failure': props<{ error: string }>(),

    'Create Label':         props<{ categoryId: number; name: string }>(),
    'Create Label Success': props<{ label: ClassificationLabel }>(),
    'Create Label Failure': props<{ error: string }>(),

    'Patch Label':         props<{ id: number; categoryId: number; patch: LabelPatchRequest }>(),
    'Patch Label Success': props<{ label: ClassificationLabel }>(),
    'Patch Label Failure': props<{ error: string }>(),

    'Delete Label':         props<{ id: number; categoryId: number }>(),
    'Delete Label Success': props<{ id: number; categoryId: number }>(),
    'Delete Label Failure': props<{ error: string }>(),

    'Reclassify All':         emptyProps(),
    'Reclassify All Success': props<{ jobId: string }>(),
    'Reclassify All Failure': props<{ error: string }>(),
  },
});
