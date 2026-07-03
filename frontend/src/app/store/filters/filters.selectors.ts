import { filtersFeature } from './filters.reducer';

const {
  selectSort,
  selectOrder,
  selectDensity,
  selectFavourite,
  selectSources,
  selectQualityMin,
  selectTagIds,
  selectCollectionId,
  selectPersonId,
  selectFramings,
  selectHasFaces,
  selectMediaType,
  selectClassificationLabelIds,
} = filtersFeature;

export const filtersSelectors = {
  sort:         selectSort,
  order:        selectOrder,
  density:      selectDensity,
  favourite:    selectFavourite,
  sources:      selectSources,
  qualityMin:   selectQualityMin,
  tagIds:       selectTagIds,
  collectionId: selectCollectionId,
  personId:     selectPersonId,
  framings:     selectFramings,
  hasFaces:     selectHasFaces,
  mediaType:    selectMediaType,
  classificationLabelIds: selectClassificationLabelIds,
};
