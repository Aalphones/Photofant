import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'pf-personen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="placeholder-view">
      <h3>Personen</h3>
      <p>Noch nicht implementiert — kommt in P7</p>
    </div>
  `,
  styles: [':host { display: block; height: 100%; }'],
})
export class Personen {}
