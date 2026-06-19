import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'pf-favoriten',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="placeholder-view">
      <h3>Favoriten</h3>
      <p>Vollständige Ansicht kommt in P7 — zeigt nur Favoriten-Bilder mit vollem Grid + Filter.</p>
    </div>
  `,
  styles: [':host { display: block; height: 100%; }'],
})
export class Favoriten {}
