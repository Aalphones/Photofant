import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import type { PersonDto, PersonFace, FaceMatch, MergeResult, SplitResult } from '@photofant/models';

@Injectable({ providedIn: 'root' })
export class PersonService {
  private readonly http = inject(HttpClient);

  getPersons(): Observable<PersonDto[]> {
    return this.http.get<PersonDto[]>('/api/persons');
  }

  renamePerson(id: number, name: string): Observable<PersonDto> {
    return this.http.patch<PersonDto>(`/api/persons/${id}`, { name });
  }

  mergePersons(fromId: number, intoId: number): Observable<MergeResult> {
    return this.http.post<MergeResult>('/api/persons/merge', { from_id: fromId, into_id: intoId });
  }

  splitPerson(personId: number, faceIds: number[]): Observable<SplitResult> {
    return this.http.post<SplitResult>(`/api/persons/${personId}/split`, { face_ids: faceIds });
  }

  getPersonFaces(personId: number): Observable<PersonFace[]> {
    return this.http.get<PersonFace[]>(`/api/persons/${personId}/faces`);
  }

  getFaceMatches(faceId: number): Observable<FaceMatch[]> {
    return this.http.get<FaceMatch[]>(`/api/faces/${faceId}/matches`);
  }

  assignFace(faceId: number, personId: number): Observable<unknown> {
    return this.http.patch(`/api/faces/${faceId}/assign`, { person_id: personId });
  }

  portraitUrl(faceId: number): string {
    return `/api/faces/${faceId}/thumbnail`;
  }
}
