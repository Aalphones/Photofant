import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'pf-trainingssets',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="placeholder-view">
      <h3>Trainingssets</h3>
      <p>Noch nicht implementiert — kommt in P10</p>
    </div>
  `,
  styles: [':host { display: block; height: 100%; }'],
})
export class Trainingssets {}
