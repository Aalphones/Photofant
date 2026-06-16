# P2 · Phase 6 — Import-UI & Shortcuts

> Rating: standard · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (import/scan)
- [docs/design/README.md](../../design/README.md) — Globales Drag & Drop, Job-Dock; `docs/design/js/import.jsx`
- [Konzept](../../Konzept-Photofant.md) §11 (Import), §13.5 (Shortcuts)

## Akzeptanzkriterien

- Import-Dialog (Dateien wählen oder global Drag & Drop aufs Fenster → Overlay-Pill → Dialog), Upload als Multipart, Fortschritt im Job-Dock.
- „Ordner scannen"-Aktion stößt den FS-Scan-Job an.
- Shortcuts global registriert: ←/→, F, Entf, Esc, `?` (Legende-Overlay); Legende zeigt Belegung (Anpassbarkeit kommt mit Settings, P-spätere).
- Erstnutzer-tauglich: leerer Zustand der Galerie zeigt „Bilder hierher ziehen oder importieren" mit Button — kein toter Bildschirm.

## Checkliste

- [x] Import-Dialog + globale DnD-Zone (Overlay nach Prototyp)
- [x] Multipart-Upload-Pfad im Backend (zusätzlich zum Pfad-Import) — `POST /api/assets/upload`, `python-multipart` als Dep
- [x] Scan-Trigger in der Top-Bar/Galerie
- [x] Shortcut-Service (zentrale Registry, Konflikt-frei, Legende-Overlay-Komponente)
- [x] Empty-State der Galerie
- [x] Doc-Update: routes.md; README Features-Stand

## Report-Back

Phase 6 abgeschlossen. Alle AK umgesetzt:

- **Import-Dialog**: zwei Modi (Pfad-Import via Textarea + Browser-Upload via Multipart). Globale DnD-Zone im Shell-Level: Drag über das Fenster → Pill-Overlay → Drop öffnet den Dialog mit den gefallenen Dateien.
- **Backend `/api/assets/upload`**: nimmt `multipart/form-data; files[]`, speichert in `tempfile.mkdtemp()`, ruft `enqueue_import` auf — identische Pipeline wie Pfad-Import.
- **Scan-Trigger**: Scan-Icon in der TopBar, ruft `POST /api/assets/scan` → Job im Dock.
- **ShortcutService**: zentrale Registry (`register(entries): deregister`), `?`-Taste aus dem Service selbst (singleton), Lightbox registriert ihre 5 Shortcuts beim Mount und deregistriert beim Unmount via `destroyRef`.
- **ShortcutLegend**: Overlay (nach `?`-Taste oder Keyboard-Button in der TopBar), gruppiert nach Context, zeigt alle registrierten Shortcuts.
- **Demo-Job-Button**: entfernt.
- **Empty-State**: Galerie zeigt bei leerer Bibliothek "Noch keine Bilder" mit Drag-Hinweis.
- **Icons**: `folder`, `plus`, `scan`, `keyboard` zu `icon.ts` hinzugefügt.

Abweichung: `/api/assets/upload` ist ein separater Endpunkt (nicht multipart auf `/api/assets/import`), weil FastAPI Form-Data und JSON-Body nicht auf derselben Route mixen kann. routes.md ist aktualisiert.
