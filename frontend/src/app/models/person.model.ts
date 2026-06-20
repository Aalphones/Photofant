export interface PersonDto {
  id: number;
  name: string | null;
  is_unknown: boolean;
  count: number;
  fav_count: number;
  portrait_face_id: number | null;
}

export interface PersonFace {
  id: number;
  asset_id: number | null;
  crop_url: string;
  score: number | null;
  age: number | null;
}

export interface FaceMatch {
  person_id: number;
  person_name: string | null;
  best_face_id: number;
  score: number;
}
