import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import type { PersonDto } from '@photofant/models';

@Injectable({ providedIn: 'root' })
export class PersonService {
  private readonly http = inject(HttpClient);

  getPersons(): Observable<PersonDto[]> {
    return this.http.get<PersonDto[]>('/api/persons');
  }

  renamePerson(id: number, name: string): Observable<PersonDto> {
    return this.http.patch<PersonDto>(`/api/persons/${id}`, { name });
  }

  portraitUrl(faceId: number): string {
    return `/api/faces/${faceId}/thumbnail`;
  }
}
