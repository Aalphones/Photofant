import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'pf-alben',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="placeholder-view">
      <h3>Alben</h3>
      <p>Noch nicht implementiert — kommt in P6</p>
    </div>
  `,
  styles: [':host { display: block; height: 100%; }'],
})
export class Alben {}
