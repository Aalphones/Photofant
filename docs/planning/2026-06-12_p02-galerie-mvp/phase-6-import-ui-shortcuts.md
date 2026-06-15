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

- [ ] Import-Dialog + globale DnD-Zone (Overlay nach Prototyp)
- [ ] Multipart-Upload-Pfad im Backend (zusätzlich zum Pfad-Import)
- [ ] Scan-Trigger in der Top-Bar/Galerie
- [ ] Shortcut-Service (zentrale Registry, Konflikt-frei, Legende-Overlay-Komponente)
- [ ] Empty-State der Galerie
- [ ] Doc-Update: routes.md; README Features-Stand

## Report-Back
