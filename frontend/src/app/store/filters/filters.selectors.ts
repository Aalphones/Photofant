import { filtersFeature } from './filters.reducer';

const {
  selectSort,
  selectOrder,
  selectGroup,
  selectDensity,
  selectFavourite,
  selectSources,
  selectQualityMin,
  selectTagIds,
  selectCollectionId,
  selectPersonId,
  selectFramings,
} = filtersFeature;

export const filtersSelectors = {
  sort:         selectSort,
  order:        selectOrder,
  group:        selectGroup,
  density:      selectDensity,
  favourite:    selectFavourite,
  sources:      selectSources,
  qualityMin:   selectQualityMin,
  tagIds:       selectTagIds,
  collectionId: selectCollectionId,
  personId:     selectPersonId,
  framings:     selectFramings,
};
