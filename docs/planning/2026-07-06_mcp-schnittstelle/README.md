# MCP-Schnittstelle — Photofant per Agent verwalten

> Eine lokale MCP-Schnittstelle, über die ein Agent (z. B. Claude Desktop, ein lokaler
> LLM-Client) den kompletten Foto-Bestand durchsuchen, ansehen und organisieren kann —
> praktisch alles, was die UI kann, außer Editor/Generativ. Eingebettet ins FastAPI-Backend,
> ohne Auth/Zertifikat, nur auf `127.0.0.1`, standardmäßig **aus**. *(private, lean.)*

## Leitplanken (vom User gesetzt)

- **Eingebettet** in den bestehenden FastAPI-Prozess (geteilte DB/Jobs/Modelle, keine Doppel-Logik).
- **Keine Auth, kein Zertifikat** — reine Localhost-Nutzung, minimale Reibung. Einziger Schutz:
  der Settings-Toggle (Default aus) + Bind nur auf Loopback + `Host`/`Origin`-Prüfung gegen DNS-Rebinding.
- **Bilder als echter Bild-Content** (`view_photo`), abschaltbar per Setting.
- **Soft-Only + Confirmation-Gate**: reversible Aktionen (Papierkorb) laufen direkt; harte
  (endgültig löschen, mergen, Reparatur) verlangen `confirm: true`.
- **Editor/Generativ und Config-Schreiben** bleiben in v1 **draußen**.

## Phasen-Übersicht

| Phase | Thema | Komplexität | Status |
|---|---|---|---|
| 1 | MCP-Infrastruktur + Settings-Toggle + Warnhinweis-UI | heikel | complete |
| 2 | Finden & Ansehen (Read-Tools inkl. Bild-Content, Job-Status) | standard | complete |
| 3 | Metadaten & Tag-Vokabular (Write, non-destruktiv) | standard | pending |
| 4 | Personen & Faces | standard | pending |
| 5 | Import, Organisieren, Duplikate | standard | pending |
| 6 | Wartung + Confirmation-Gate scharfstellen | standard | pending |

Phase 1 ist der heikle Kern (neue Library, ASGI-Mount, Lifespan, Security). 2–6 sind gleichförmige
Tool-Arbeit auf einem in Phase 1 fertig etablierten Muster.

## Kontrakt (gilt für alle Phasen — Drift-Anker)

**Wo der Code wohnt** (Parallel-Namensschema, neue `code-map.md`-Zeile):
```
backend/photofant/mcp/
  server.py            # FastMCP-Instanz, Mount-Helper, Flag-Guard-Middleware, Host-Check
  adapter.py           # run_endpoint(): öffnet DB-Session, ruft bestehende api/*.py-Funktion
  gate.py              # confirmation_required()-Helper für destruktive Tools
  tools/
    library.py         # Phase 2: search/get/view/facets/similar/lineage/capabilities/jobs
    metadata.py        # Phase 3: tags, caption, source/framing, classification
    persons.py         # Phase 4: personen + faces
    organize.py        # Phase 5: import/scan/processing, alben, trainingssets, trash, duplikate
    maintenance.py     # Phase 6: rebuild/reconcile/repair/backup
frontend/src/app/features/einstellungen/mcp/   # Settings-Sektion (analog comfyui/)
```

**Tool → Backend-Aufruf (verbindlich, keine Doppel-Logik):**
MCP-Tools rufen **die vorhandenen `api/*.py`-Endpoint-Funktionen direkt als async-Funktionen auf** —
kein interner HTTP-Loopback. Der Adapter `mcp/adapter.py:run_endpoint()` öffnet eine DB-Session über
die bestehende Session-Factory (Muster wie der `Depends`-Provider in `api/assets.py`) und übergibt sie
plus die konstruierten Pydantic-Request-Objekte an die Endpoint-Coroutine. Für Endpoints, die
`UploadFile`/`Request` brauchen (Upload), ruft das Tool stattdessen die darunterliegende Job-/Service-
Funktion (z. B. `jobs/import_job.py`), nicht den Endpoint. Damit bleibt jede Validierung/Logik an genau
einer Stelle.

**Rückgabe-Format:** Tools geben knappes, agent-lesbares JSON zurück (IDs, Namen, Scores, Pfade) —
**keine** rohen DTO-Dumps mit Base64-Blobs im Text. Bilder kommen ausschließlich über `view_photo`
als MCP-`ImageContent`. Jede Liste ist auf `mcp.max_search_results` gedeckelt und nennt `total`, damit
der Agent paginieren kann.

**Confirmation-Gate (in Phase 1 als `gate.py` gebaut, ab Phase 4/5/6 genutzt):**
Destruktive Tools nehmen `confirm: bool = false`. Ohne `confirm=true` **führen sie nichts aus**, sondern
geben eine Klartext-Warnung zurück, was passieren würde und dass ein erneuter Aufruf mit `confirm=true`
nötig ist. Gilt für: `empty_trash`, `delete_person`, `merge_persons`, `delete_face`,
`resolve_duplicate` (nur bei `delete_*`), `repair` (nur bei `trash`/`mark_missing`). Reversible Aktionen
(`trash_photo` → Papierkorb, `favourite`, `assign_person`) laufen **ohne** Gate. Global abschaltbar
per `mcp.require_confirm` (Default true).

**Async-Jobs:** Alle Tools, die einen Job auslösen (Import, Scan, Rerun, Rebuild, Export, Dupe-Scan),
geben die `job_id` zurück. Der Agent verfolgt den Fortschritt über `get_job_status` / `list_jobs`
(Phase 2) — er pollt, statt auf den SSE-Stream zu warten.

## settings.json — vorab freigeben (Critical Rule 7)

Neuer Nested-Block `mcp` (Muster: `comfyui`-Block in `settings.py`):

- `mcp.enabled` (bool, **default false**) — Schnittstelle an/aus.
- `mcp.return_images` (bool, default true) — `view_photo` liefert Bild-Content; false = nur Metadaten.
- `mcp.max_search_results` (int, default 50) — harter Deckel je Listen-Tool (Token-Schutz).
- `mcp.thumbnail_size` (int, default 256) — Kantenlänge der von `view_photo` gelieferten Thumbnails.
- `mcp.require_confirm` (bool, default true) — Confirmation-Gate für destruktive Tools.

## Finale AK (Gesamtergebnis)

- [ ] Bei `mcp.enabled=false` ist unter `/mcp` **nichts** erreichbar (404); Toggle in den Einstellungen
      schaltet **ohne Backend-Neustart** scharf.
- [ ] Ein lokaler MCP-Client (MCP Inspector / Claude Desktop) verbindet sich ohne Auth gegen
      `http://127.0.0.1:<backend-port>/mcp` und listet alle Tools der umgesetzten Phasen.
- [ ] Der Agent kann: ein Foto per Text/Semantik/Tag/Person finden, es **als Bild sehen**, taggen,
      Caption setzen, einer Person zuordnen, ins Album/Trainingsset legen, in den Papierkorb werfen,
      Dubletten auflösen, Gesichter neu extrahieren, ein Backup auslösen — je über ein Tool.
- [ ] Destruktive Tools verweigern ohne `confirm=true` die Ausführung und erklären, was sie täten.
- [ ] Die Settings-Sektion zeigt einen unübersehbaren Hinweis: „Nur mit lokal laufenden Agenten nutzen —
      sonst landen deine Bilder und Metadaten beim Cloud-Anbieter."
- [ ] `docs/routes.md` (MCP-Abschnitt), `docs/code-map.md` (neue Zeile), ADR-019 sind aktuell.

## Risiken & offene Annahmen (kritisch gegenlesen)

- 🟡 **Lifespan des gemounteten MCP-Servers** — die Streamable-HTTP-App von FastMCP bringt einen eigenen
  Session-Manager mit, dessen Lifespan mit dem FastAPI-`_lifespan` verkettet werden muss, sonst startet
  der MCP-Teil nie sauber. Heikelster Punkt, isoliert in Phase 1 (Check unten).
- 🟡 **Laufzeit-Toggle ohne Neustart** — ASGI-Mounts entstehen zur `create_app()`-Zeit. Der Toggle wird
  daher als **Flag-Guard-Middleware vor dem Mount** gelöst (liest `mcp.enabled` live), nicht durch
  bedingtes Mounten. Fallback, falls fummelig: `reboot_required` wie bei `data_root`.
- 🟡 **Keine Auth = jeder lokale Prozess darf ran**, solange das Flag an ist — inkl. DNS-Rebinding über
  eine bösartige Webseite. Mitigation ohne Reibung: Bind nur auf `127.0.0.1`, `Host`/`Origin`-Header
  gegen Loopback prüfen, Default aus. Bewusst akzeptiert (User-Entscheidung), steht im ADR.
- 🟡 **Token-Budget bei Bild-Rückgabe** — ein 256-px-JPEG als Base64 ist ~10–30k Zeichen; mehrere pro
  Turn sprengen den Agent-Kontext. Deshalb `view_photo` = genau ein Bild pro Aufruf, Größe gedeckelt.

## Konfidenz-Ausweis — wo ich am unsichersten bin

1. **Lifespan-Verkettung des `/mcp`-Mounts** (Phase 1). Check: Minimal-Spike — FastMCP-Instanz bauen,
   `app.mount("/mcp", mcp.streamable_http_app())`, kombinierten Lifespan setzen, dann MCP Inspector gegen
   `/mcp` `initialize` fahren. Läuft der Handshake, steht das Fundament.
2. **Tool→Endpoint-Adapter** (`adapter.py`, Phase 1). Check: `run_endpoint()` gegen genau einen simplen
   Endpoint (`GET /api/assets`, also `list_assets`) mit selbst geöffneter Session aufrufen und dieselbe
   Antwort wie über HTTP bekommen. Trägt das, tragen alle Tools.
3. **Live-Flag-Guard vor dem Mount** (Phase 1). Check: Flag toggeln, `/mcp` einmal mit `enabled=false`
   (→ 404) und einmal `true` (→ Handshake) treffen, **ohne** den Prozess neu zu starten.

## ADR

- **ADR-019** — MCP-Schnittstelle: offizielles Python-`mcp`-SDK (`FastMCP`, Streamable-HTTP), eingebettet
  als ASGI-Mount unter `/mcp`; auth-frei, Loopback-only, Flag-gegated. `docs/decisions/019-mcp-schnittstelle.md`
  (in Phase 1 anlegen). Nächste freie Nummer: Platte bis 018, Gemma-Pläne reservieren 013/014 → 019.

## Bottom-Sektionen (beim Archivieren füllen)

### Summary
### Files touched
### Commits
### Deviations from plan
### Follow-ups
