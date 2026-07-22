import { afterNextRender, ChangeDetectionStrategy, Component, ElementRef, HostListener, input, output, viewChild } from '@angular/core';
import { Icon } from '../../../ui/icon/icon';

// P38 Phase 7 — gemeinsame Hülle für Interview- und Web-Suche-Wizard (`phase-7-wizards.md`
// Aufgabe 1). Rahmen/Kopf/Fußleiste exakt nach `design/styles.css` Zeile 1462 (`.kw-wiz`).
// `backLabel`/`hideFooter` sind Erweiterungen über die Plan-Basisliste hinaus (Aufgabe 2
// braucht am Summary-Schritt "Antworten anpassen" statt "Zurück", die Synthese-Wartephase
// zeigt gar keine Fußleiste) — siehe Report-Back.
@Component({
  selector: 'pf-wizard-shell',
  imports: [Icon],
  templateUrl: './wizard-shell.html',
  styleUrl: './wizard-shell.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WizardShell {
  readonly title = input.required<string>();
  readonly icon = input<string>('sparkle');
  readonly canGoBack = input<boolean>(false);
  readonly backLabel = input<string>('Zurück');
  readonly primaryLabel = input<string | null>(null);
  readonly primaryDisabled = input<boolean>(false);
  readonly hideFooter = input<boolean>(false);

  readonly close = output<void>();
  readonly back = output<void>();
  readonly primary = output<void>();

  private readonly bodyRef = viewChild<ElementRef<HTMLElement>>('body');

  constructor() {
    // Fokus aufs erste Eingabefeld beim Öffnen (Aufgabe 1). Läuft einmalig nach dem ersten
    // Rendern — die projizierten Inhalte (ng-content) stehen zu dem Zeitpunkt bereits.
    afterNextRender(() => {
      const focusable = this.bodyRef()?.nativeElement.querySelector<HTMLElement>(
        'input, textarea, select, button:not([disabled])',
      );
      focusable?.focus();
    });
  }

  @HostListener('document:keydown.escape')
  protected onEscape(): void {
    this.close.emit();
  }

  protected onBackdrop(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('wiz-scrim')) {
      this.close.emit();
    }
  }
}
