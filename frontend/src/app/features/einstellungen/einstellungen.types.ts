export interface ShortcutRow {
  action: string;
  label: string;
  group: string;
}

export interface Section {
  id: string;
  icon: string;
  label: string;
}

export const SHORTCUT_ROWS: ShortcutRow[] = [
  { action: 'lightbox.close',  label: 'Lightbox schließen',    group: 'Lightbox' },
  { action: 'lightbox.prev',   label: 'Vorheriges Bild',       group: 'Lightbox' },
  { action: 'lightbox.next',   label: 'Nächstes Bild',         group: 'Lightbox' },
  { action: 'asset.favourite', label: 'Favorit umschalten',    group: 'Lightbox' },
  { action: 'asset.delete',    label: 'In Papierkorb legen',   group: 'Lightbox' },
];

export const SECTIONS: Section[] = [
  { id: 'bibliothek',   icon: 'folder',   label: 'Bibliothek' },
  { id: 'verarbeitung', icon: 'refresh',  label: 'Verarbeitung' },
  { id: 'darstellung',  icon: 'gallery',  label: 'Darstellung' },
  { id: 'bearbeitung',  icon: 'pencil',   label: 'Bearbeitung' },
  { id: 'tags',         icon: 'tag',      label: 'Tags' },
  { id: 'klassifizierung', icon: 'layers', label: 'Klassifizierung' },
  { id: 'comfyui',      icon: 'sparkle',  label: 'ComfyUI' },
  { id: 'mcp',          icon: 'link',     label: 'MCP-Schnittstelle' },
  { id: 'shortcuts',    icon: 'keyboard', label: 'Tastaturkürzel' },
  { id: 'backup',       icon: 'shield',   label: 'Backup & Wartung' },
  { id: 'info',         icon: 'info',     label: 'Info' },
];
