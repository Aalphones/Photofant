import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import type {
  ClusterResult,
  FaceDetailDto,
  FaceImportResult,
  FaceMatch,
  FacesPage,
  MergeResult,
  PersonDto,
  PersonDupePair,
  PersonFace,
  PersonImportResponse,
  SplitResult,
} from '@photofant/models';

@Injectable({ providedIn: 'root' })
export class PersonService {
  private readonly http = inject(HttpClient);

  getPersons(): Observable<PersonDto[]> {
    return this.http.get<PersonDto[]>('/api/persons');
  }

  createPerson(name: string): Observable<PersonDto> {
    return this.http.post<PersonDto>('/api/persons', { name });
  }

  renamePerson(id: number, name: string): Observable<PersonDto> {
    return this.http.patch<PersonDto>(`/api/persons/${id}`, { name });
  }

  setPersonGroup(id: number, groupName: string | null): Observable<PersonDto> {
    return this.http.patch<PersonDto>(`/api/persons/${id}`, { group_name: groupName });
  }

  mergePersons(fromId: number, intoId: number): Observable<MergeResult> {
    return this.http.post<MergeResult>('/api/persons/merge', { from_id: fromId, into_id: intoId });
  }

  splitPerson(personId: number, faceIds: number[]): Observable<SplitResult> {
    return this.http.post<SplitResult>(`/api/persons/${personId}/split`, { face_ids: faceIds });
  }

  deletePerson(id: number): Observable<MergeResult> {
    return this.http.delete<MergeResult>(`/api/persons/${id}`);
  }

  getPersonFaces(personId: number): Observable<PersonFace[]> {
    return this.http.get<PersonFace[]>(`/api/persons/${personId}/faces`);
  }

  getFaceMatches(faceId: number): Observable<FaceMatch[]> {
    return this.http.get<FaceMatch[]>(`/api/faces/${faceId}/matches`);
  }

  getFace(faceId: number): Observable<FaceDetailDto> {
    return this.http.get<FaceDetailDto>(`/api/faces/${faceId}`);
  }

  assignFace(faceId: number, personId: number): Observable<unknown> {
    return this.http.patch(`/api/faces/${faceId}/assign`, { person_id: personId });
  }

  assignPersonToAsset(assetId: number, personId: number): Observable<unknown> {
    return this.http.patch(`/api/assets/${assetId}/assign-person`, { person_id: personId });
  }

  revealPersonFolder(personId: number): Observable<void> {
    return this.http.post<void>(`/api/persons/${personId}/reveal`, null);
  }

  bulkAssignPerson(personId: number, assetIds: number[]): Observable<PersonImportResponse> {
    return this.http.post<PersonImportResponse>(`/api/persons/${personId}/bulk-assign`, { asset_ids: assetIds });
  }

  importToPersonFolder(personId: number, files: File[]): Observable<PersonImportResponse> {
    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file, file.name);
    }
    return this.http.post<PersonImportResponse>(`/api/persons/${personId}/import`, formData);
  }

  importFacesDirect(personId: number, files: File[]): Observable<FaceImportResult[]> {
    const formData = new FormData();
    formData.append('person_id', String(personId));
    for (const file of files) {
      formData.append('files', file, file.name);
    }
    return this.http.post<FaceImportResult[]>('/api/faces/import', formData);
  }

  triggerClustering(): Observable<ClusterResult> {
    return this.http.post<ClusterResult>('/api/faces/cluster', null);
  }

  searchDuplicates(personId: number, clipThreshold = 0.15): Observable<PersonDupePair[]> {
    return this.http.post<PersonDupePair[]>('/api/duplicates/search', {
      person_id: personId,
      clip_threshold: clipThreshold,
    });
  }

  deleteFace(faceId: number): Observable<void> {
    return this.http.delete<void>(`/api/faces/${faceId}`);
  }

  listFacesGallery(params: { page: number; page_size: number; person_id?: number; asset_ids?: number[] }): Observable<FacesPage> {
    let httpParams = new HttpParams()
      .set('page', params.page)
      .set('page_size', params.page_size);
    if (params.person_id != null) {
      httpParams = httpParams.set('person_id', params.person_id);
    }
    if (params.asset_ids != null && params.asset_ids.length > 0) {
      for (const assetId of params.asset_ids) {
        httpParams = httpParams.append('asset_ids', assetId);
      }
    }
    return this.http.get<FacesPage>('/api/faces/gallery', { params: httpParams });
  }

  faceGalleryThumbnailUrl(faceId: number): string {
    return `/api/faces/${faceId}/thumbnail`;
  }

  portraitUrl(faceId: number): string {
    return `/api/faces/${faceId}/thumbnail`;
  }
}
