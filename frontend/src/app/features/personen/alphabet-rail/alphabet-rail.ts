import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import type { PersonDto } from '@photofant/models';

const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

@Component({
  selector: 'pf-alphabet-rail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './alphabet-rail.html',
  styleUrl: './alphabet-rail.scss',
})
export class AlphabetRail {
  readonly persons = input<PersonDto[]>([]);
  readonly jump = output<number>();

  protected readonly letters = ALPHABET;

  private readonly firstIdByLetter = computed((): Map<string, number> => {
    const map = new Map<string, number>();
    for (const person of this.persons()) {
      const label = person.is_unknown ? 'Unbekannt' : (person.name ?? '');
      const letter = label.charAt(0).toUpperCase();
      if (letter && !map.has(letter)) {
        map.set(letter, person.id);
      }
    }
    return map;
  });

  protected isAvailable(letter: string): boolean {
    return this.firstIdByLetter().has(letter);
  }

  protected onLetterClick(letter: string): void {
    const personId = this.firstIdByLetter().get(letter);
    if (personId != null) {
      this.jump.emit(personId);
    }
  }
}
