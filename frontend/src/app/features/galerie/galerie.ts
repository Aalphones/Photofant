import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'pf-galerie',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="placeholder-view">
      <h3>Galerie</h3>
      <p>Noch nicht implementiert — kommt in P2</p>
    </div>
  `,
  styles: [':host { display: block; height: 100%; }'],
})
export class Galerie {}
