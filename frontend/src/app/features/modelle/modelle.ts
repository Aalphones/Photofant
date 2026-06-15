import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'pf-modelle',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="placeholder-view">
      <h3>Modelle</h3>
      <p>Noch nicht implementiert — kommt in P4</p>
    </div>
  `,
  styles: [':host { display: block; height: 100%; }'],
})
export class Modelle {}
