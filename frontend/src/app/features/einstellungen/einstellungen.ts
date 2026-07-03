import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { Icon } from '@photofant/ui';
import { SECTIONS, type Section } from './einstellungen.types';
import { Bibliothek } from './bibliothek/bibliothek';
import { Verarbeitung } from './verarbeitung/verarbeitung';
import { Darstellung } from './darstellung/darstellung';
import { Bearbeitung } from './bearbeitung/bearbeitung';
import { Tastaturkuerzel } from './tastaturkuerzel/tastaturkuerzel';
import { BackupWartung } from './backup-wartung/backup-wartung';
import { Info } from './info/info';
import { Tags } from './tags/tags';
import { Klassifizierung } from './klassifizierung/klassifizierung';
import { ComfyUISection } from './comfyui/comfyui';

@Component({
  selector: 'pf-einstellungen',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, Bibliothek, Verarbeitung, Darstellung, Bearbeitung, Tastaturkuerzel, BackupWartung, Info, Tags, Klassifizierung, ComfyUISection],
  templateUrl: './einstellungen.html',
  styleUrl: './einstellungen.scss',
})
export class Einstellungen {
  readonly sections: Section[] = SECTIONS;
  readonly activeSection = signal<string>('bibliothek');
  readonly mobileOpen = signal<boolean>(false);

  goSection(id: string): void {
    this.activeSection.set(id);
    this.mobileOpen.set(true);
  }

  goBack(): void {
    this.mobileOpen.set(false);
  }
}
