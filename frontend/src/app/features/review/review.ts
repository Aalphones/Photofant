import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'pf-review',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="placeholder-view">
      <h3>Review-Queue</h3>
      <p>Noch nicht implementiert — kein aktiver Backlog-Plan.</p>
    </div>
  `,
  styles: [':host { display: block; height: 100%; }'],
})
export class Review {}
