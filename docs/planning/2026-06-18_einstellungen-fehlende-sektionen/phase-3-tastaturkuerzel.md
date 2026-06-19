# Einstellungen fehlende Sektionen · Phase 3 — Tastaturkürzel

> Rating: **standard** · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt, Keyboard-Shortcuts-Schema, Persistenz-Entscheidung
- `frontend/src/app/services/shortcut.service.ts` — registriert Shortcuts zur Laufzeit (register/unregister-Pattern); **kein Bezug zu Konfiguration** — nur Legend-Anzeige
- `backend/photofant/maintenance/store.py` — Precedent für JSON-Blob in `app_config`

## Schema-Entscheidung

Shortcuts als JSON-Blob unter `app_config`-Key `keyboard_shortcuts`. Schema:
```json
{
  "version": 1,
  "shortcuts": [
    { "action": "lightbox.prev",     "keys": ["ArrowLeft"] },
    { "action": "lightbox.next",     "keys": ["ArrowRight"] },
    { "action": "lightbox.close",    "keys": ["Escape"] },
    { "action": "nav.gallery",       "keys": ["g"] },
    { "action": "nav.persons",       "keys": ["p"] },
    { "action": "nav.favourites",    "keys": ["f"] },
    { "action": "asset.favourite",   "keys": [" "] },
    { "action": "asset.delete",      "keys": ["Delete"] },
    { "action": "asset.tag",         "keys": ["t"] },
    { "action": "asset.open",        "keys": ["Enter"] },
    { "action": "search.focus",      "keys": ["/"] },
    { "action": "filter.toggle",     "keys": ["Shift", "f"] },
    { "action": "filter.reset",      "keys": ["Escape"] }
  ]
}
```

`version`-Feld ermöglicht spätere Schema-Migration ohne Datenverlust.

## Akzeptanzkriterien

- `GET /api/config` liefert `keyboard_shortcuts` (JSON-Blob als String; Default: null → Frontend nutzt Defaults).
- `PATCH /api/config` mit `{ "keyboard_shortcuts": "{...}" }` persistiert Blob.
- Frontend `ShortcutService` liest Shortcuts beim App-Start aus dem Store (geladen von Backend); fällt auf Code-Defaults zurück wenn kein Blob gespeichert.
- Einstellungs-UI ermöglicht Kürzel-Bearbeitung (Klick → Tastendruck → Speichern) analog zum Prototyp-Verhalten.
- "Auf Standard zurücksetzen" löscht den `keyboard_shortcuts`-Blob (`PATCH /api/config` mit `null`).

## Checkliste

### Backend

- [ ] **`api/config.py` `_read_config()`**: Default `keyboard_shortcuts: None` (kein hartkodierter Default — Frontend-Defaults gelten wenn null)
- [ ] Kein weiterer Backend-Code nötig: `PATCH /api/config` mit beliebigem Key-Value funktioniert bereits

### Frontend

- [ ] **Neues Model-Interface `ShortcutConfig`** in `models/` (oder inline im Service): Action-ID → Keys-Array-Map
- [ ] **`ShortcutService`** erweitern:
  - Initialisierung: liest `keyboard_shortcuts`-Blob aus `app_config`-Store (NgRx); merged mit Code-Defaults (Code-Defaults als Fallback für fehlende Actions)
  - Neue `signal`-basierte Map `resolvedShortcuts` — kombiniert Defaults + DB-Overrides
  - Shortcut-Handler in allen Views lesen aus `resolvedShortcuts` statt hartkodierten Keys
  - Methode `saveShortcuts(shortcuts: ShortcutConfig): void` — dispatcht `modelsActions.updateConfig({ keyboard_shortcuts: JSON.stringify(...) })`
  - Methode `resetShortcuts(): void` — dispatcht mit `null`
- [ ] **`models.actions.ts` / `effects.ts`**: generischer `updateConfig`-Action falls noch nicht vorhanden (kann für alle `app_config`-Keys genutzt werden)
- [ ] **`einstellungen.ts`**: Sektion "Tastaturkürzel" — Tabelle mit Gruppen/Zeilen; Klick auf Zeile → Listening-Modus (Tastendruck speichert neue Belegung via `ShortcutService.saveShortcuts`); Reset-Button; analog zum Prototyp `settings.jsx` `SectionShortcuts`
- [ ] **Shortcut-Integration in Views**: Galerie (Prev/Next Lightbox, Filter-Toggle, Search-Focus), Lightbox (Prev/Next/Close), global (Favorit, Delete, Tag) — statt hardcodierter `key === "ArrowLeft"` Checks: `shortcutService.resolvedShortcuts()['lightbox.prev'].includes(event.key)`
- [ ] Doc-Update: kein neuer Endpoint (uses existing PATCH /api/config)

## Report-Back
