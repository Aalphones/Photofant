import { ChangeDetectionStrategy, Component, effect, ElementRef, input, output, signal, viewChild } from '@angular/core';
import type { ExplainabilityPayload } from '@photofant/models';
import { Icon } from '../icon/icon';

// Geteiltes „Warum?"/„Warum nicht?"-Popover (P26 Phase 3) — dieselbe Anzeige für Empfehlungs-
// Begründungen UND die P25-Korrektur-Historie (Lore-Panel), kein zweites Implementat (AK).
// Bewusst „dumm": kein eigener HTTP-Call — der Aufrufer entscheidet, ob das Payload schon
// lokal vorliegt (Empfehlungs-Reasons) oder erst nachgeladen werden muss (Warum-nicht?/
// Changelog), und steuert `payload`/`loading`. Open/Close bleibt beim Aufrufer (`open`-Input),
// damit z.B. eine Rail nur ein aktives Popover gleichzeitig zulässt.
//
// Panel ist `position: fixed`, Koordinaten aus der Trigger-BoundingRect berechnet — nicht
// `position: absolute` relativ zur Karte: die Empfehlungs-Rail steht in einem
// `overflow-x: auto`-Streifen, der jeden absolut positionierten Overflow abschneiden würde
// (CSS-Spezialfall: `overflow-x: auto` erzwingt `overflow-y: auto`, auch ohne es zu setzen).
@Component({
  selector: 'pf-explainability-popover',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './explainability-popover.html',
  styleUrl: './explainability-popover.scss',
})
export class ExplainabilityPopover {
  readonly label = input('Warum?');
  readonly open = input(false);
  readonly payload = input<ExplainabilityPayload | null>(null);
  readonly loading = input(false);

  readonly triggerClicked = output<void>();
  readonly closeRequested = output<void>();

  private readonly trigger = viewChild<ElementRef<HTMLElement>>('trigger');

  protected readonly position = signal({ top: 0, left: 0 });

  constructor() {
    effect((): void => {
      if (this.open()) {
        this.updatePosition();
      }
    });
  }

  protected close(): void {
    this.closeRequested.emit();
  }

  private updatePosition(): void {
    const element = this.trigger()?.nativeElement;
    if (element == null) { return; }
    const rect = element.getBoundingClientRect();
    const panelWidth = 260;
    const left = Math.min(rect.left, window.innerWidth - panelWidth - 8);
    this.position.set({ top: rect.bottom + 4, left: Math.max(8, left) });
  }
}
