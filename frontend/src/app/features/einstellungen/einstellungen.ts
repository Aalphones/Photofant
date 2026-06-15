import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'pf-einstellungen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="placeholder-view">
      <h3>Einstellungen</h3>
      <p>Noch nicht implementiert — kommt in P8</p>
    </div>
  `,
  styles: [':host { display: block; height: 100%; }'],
})
export class Einstellungen {}
