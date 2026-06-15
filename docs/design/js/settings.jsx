/* Photofant — Einstellungen (Settings)
   6 Sektionen: Bibliothek, Verarbeitung, Darstellung, Tastaturkürzel, Backup & Wartung, Info
   → window.Settings */
(function () {
  const { Icon } = window;
  const { useState, useEffect, useRef } = React;

  /* ---- tiny shared helpers ---- */
  function Switch({ on, onClick }) {
    return React.createElement("button", { className: "st-switch" + (on ? " on" : ""), onClick, role: "switch", "aria-checked": on },
      React.createElement("i", null));
  }
  function Row({ title, sub, ctrl, top }) {
    return React.createElement("div", { className: "st-row" + (top ? " top" : "") },
      React.createElement("div", { className: "st-row-body" },
        React.createElement("div", { className: "st-row-title" }, title),
        sub && React.createElement("div", { className: "st-row-sub" }, sub)),
      ctrl && React.createElement("div", { className: "st-row-ctrl" }, ctrl));
  }
  function Group({ label, children }) {
    return React.createElement(React.Fragment, null,
      label && React.createElement("div", { className: "st-group-label" }, label),
      React.createElement("div", { className: "st-group" }, children));
  }
  function Note({ type = "info", icon, children }) {
    return React.createElement("div", { className: "st-note " + type },
      React.createElement(Icon, { name: icon || "info", size: 15 }), React.createElement("span", null, children));
  }
  function PathRow({ label, sub, value, onEdit }) {
    return React.createElement(Row, { title: label, sub, top: true,
      ctrl: React.createElement("div", { className: "st-path" },
        React.createElement(Icon, { name: "folder", size: 14 }),
        React.createElement("span", { className: "sp-val" }, value),
        React.createElement("button", { className: "sp-btn", onClick: onEdit }, "Ändern")) });
  }
  function SliderRow({ title, sub, min, max, step, value, fmt, onChange }) {
    return React.createElement(Row, { title, sub,
      ctrl: React.createElement("div", { className: "st-slider-wrap" },
        React.createElement("input", { type: "range", min, max, step, value, onChange: (e) => onChange(+e.target.value) }),
        React.createElement("span", { className: "st-slider-val" }, fmt ? fmt(value) : value)) });
  }
  function OpButton({ label, icon, variant = "ghost", running, result, onClick }) {
    return React.createElement("div", { className: "st-row btn-row" },
      React.createElement("div", { className: "st-row-body" },
        running && React.createElement("div", { className: "st-op-result running" },
          React.createElement("div", { className: "op-spin" }), label + " läuft …"),
        result && !running && React.createElement("div", { className: "st-op-result" },
          React.createElement(Icon, { name: "check", size: 14 }), result)),
      React.createElement("div", { className: "st-row-ctrl" },
        React.createElement("button", { className: "st-btn " + variant, disabled: running, onClick },
          React.createElement(Icon, { name: icon, size: 15 }), label)));
  }

  /* ============================================================
     SECTION: BIBLIOTHEK
     ============================================================ */
  function SectionBibliothek({ cfg, setCfg }) {
    const totalGB = 148.4, dbMB = 42, trashGB = 2.3;
    const usedPct = Math.round(totalGB / 500 * 100);
    return React.createElement("div", { className: "st-section" },
      React.createElement("div", { className: "st-section-head" },
        React.createElement("h2", null, "Bibliothek"),
        React.createElement("p", null, "Ordner, Speichernutzung und Aufräum-Optionen.")),

      React.createElement(Group, { label: "Speicherorte" },
        React.createElement(PathRow, { label: "Sammlungs-Ordner", sub: "Wurzelverzeichnis aller Person-Ordner und Bilddateien.", value: cfg.libraryPath, onEdit: () => {} }),
        React.createElement(PathRow, { label: "Modell-Ordner", sub: "Standard-Ziel für neue Modell-Downloads.", value: cfg.modelsPath, onEdit: () => {} })),

      React.createElement(Group, { label: "Speichernutzung" },
        React.createElement("div", { className: "st-row top" },
          React.createElement("div", { className: "st-row-body", style: { flex: 1 } },
            React.createElement("div", { className: "st-row-title" }, "Übersicht"),
            React.createElement("div", { className: "st-storage" },
              React.createElement("div", { className: "st-storage-bar" },
                React.createElement("div", { className: "sb-used", style: { width: usedPct + "%" } })),
              React.createElement("div", { className: "st-storage-legend" },
                React.createElement("span", { className: "sl-item" }, React.createElement("span", { className: "sl-dot", style: { background: "var(--accent)" } }), totalGB + " GB Bilder"),
                React.createElement("span", { className: "sl-item" }, React.createElement("span", { className: "sl-dot", style: { background: "var(--warn)" } }), trashGB + " GB Papierkorb"),
                React.createElement("span", { className: "sl-item" }, React.createElement("span", { className: "sl-dot", style: { background: "var(--surface-2)" } }), dbMB + " MB Datenbank"))))),

        React.createElement(Row, { title: "Papierkorb automatisch leeren",
          sub: "Gelöschte Bilder werden nach dieser Zeit endgültig entfernt.",
          ctrl: React.createElement("select", { className: "st-select", value: cfg.trashDays, onChange: (e) => setCfg((c) => ({ ...c, trashDays: +e.target.value })) },
            React.createElement("option", { value: 7 }, "nach 7 Tagen"),
            React.createElement("option", { value: 30 }, "nach 30 Tagen"),
            React.createElement("option", { value: 90 }, "nach 90 Tagen"),
            React.createElement("option", { value: 0 }, "Nie (manuell)")) }),

        React.createElement(Row, { title: "Papierkorb jetzt leeren",
          sub: "12 Dateien · 2,3 GB werden endgültig gelöscht.",
          ctrl: React.createElement("button", { className: "st-btn danger" }, React.createElement(Icon, { name: "trash", size: 15 }), "Jetzt leeren") })),

      React.createElement(Note, { type: "accent", icon: "info" },
        "Alle Bilddateien liegen ausschließlich im Dateisystem. Die Datenbank hält nur Metadaten — ein regelmäßiges DB-Backup schützt vor Datenverlust."));
  }

  /* ============================================================
     SECTION: VERARBEITUNG
     ============================================================ */
  function SectionVerarbeitung({ cfg, setCfg }) {
    const set = (k) => (v) => setCfg((c) => ({ ...c, [k]: v }));
    const tog = (k) => () => setCfg((c) => ({ ...c, [k]: !c[k] }));
    return React.createElement("div", { className: "st-section" },
      React.createElement("div", { className: "st-section-head" },
        React.createElement("h2", null, "Verarbeitung"),
        React.createElement("p", null, "Pipeline-Parameter für Import, Gesichtserkennung, Tagging und Caption.")),

      React.createElement(Group, { label: "Gesichtserkennung" },
        React.createElement(SliderRow, {
          title: "Erkennungs-Schwellwert", min: 0.5, max: 0.99, step: 0.01, value: cfg.faceThreshold,
          sub: "Mindestkosinus-Ähnlichkeit für automatische Personen-Zuordnung. Niedrigere Werte → mehr Treffer, mehr Fehler.",
          fmt: (v) => Math.round(v * 100) + " %", onChange: set("faceThreshold") }),
        React.createElement(SliderRow, {
          title: "Face-Padding", min: 0, max: 0.6, step: 0.05, value: cfg.facePadding,
          sub: "Rand um das erkannte Gesicht beim Extrahieren des Face-Crops.",
          fmt: (v) => Math.round(v * 100) + " %", onChange: set("facePadding") }),
        React.createElement(Row, { title: "Review-Queue",
          sub: "Unsichere Zuordnungen (Ähnlichkeit knapp über Schwellwert) in der Review-Queue zur Bestätigung sammeln.",
          ctrl: React.createElement(Switch, { on: cfg.reviewQueue, onClick: tog("reviewQueue") }) })),

      React.createElement(Group, { label: "Duplikat-Erkennung" },
        React.createElement(SliderRow, {
          title: "pHash-Schwellwert", min: 0, max: 20, step: 1, value: cfg.phashThreshold,
          sub: "Maximale Hamming-Distanz, ab der zwei Bilder als nahezu doppelt gewertet werden. 0 = exakt identisch.",
          fmt: (v) => v === 0 ? "0 (exakt)" : "≤ " + v, onChange: set("phashThreshold") }),
        React.createElement(Row, { title: "Embedding-Ähnlichkeit zusätzlich prüfen",
          sub: "Langsamer, aber trifft auch farbkalibrierte oder leicht zugeschnittene Duplikate.",
          ctrl: React.createElement(Switch, { on: cfg.dupEmbedding, onClick: tog("dupEmbedding") }) })),

      React.createElement(Group, { label: "Blur-Qualitäts-Filter" },
        React.createElement(SliderRow, {
          title: "Laplacian-Varianz (Mindestschärfe)", min: 0, max: 300, step: 10, value: cfg.blurThreshold,
          sub: "Bilder unterhalb dieses Werts werden als unscharf markiert und ggf. ausgefiltert.",
          fmt: (v) => v === 0 ? "Aus" : String(v), onChange: set("blurThreshold") })),

      React.createElement(Group, { label: "Auto-Pipeline" },
        React.createElement(Row, { title: "Auto-Tagging (WD14)",
          sub: "Tags automatisch beim Import berechnen.",
          ctrl: React.createElement(Switch, { on: cfg.autoTag, onClick: tog("autoTag") }) }),
        React.createElement(Row, { title: "Auto-Caption (Florence-2)",
          sub: "Caption automatisch beim Import erzeugen.",
          ctrl: React.createElement(Switch, { on: cfg.autoCaption, onClick: tog("autoCaption") }) }),
        React.createElement(Row, { title: "CLIP-Embedding (Semantische Suche)",
          sub: "Bild-Embeddings für thematische Freitextsuche berechnen. Kann übersprungen werden, wenn Semantische Suche nicht benötigt wird.",
          ctrl: React.createElement(Switch, { on: cfg.autoEmbed, onClick: tog("autoEmbed") }) }),
        React.createElement(Row, { title: "Hintergrundentfernung (rembg)",
          sub: "Hintergrundentfernung im Import-Fluss aktivieren. Erfordert rembg isnet-general-use.",
          ctrl: React.createElement(Switch, { on: cfg.autoRembg, onClick: tog("autoRembg") }) })),

      React.createElement(Group, { label: "Priorität" },
        React.createElement(Row, { title: "Import-Parallelität",
          sub: "Wie viele Bilder gleichzeitig in der Queue verarbeitet werden. Höhere Werte belasten GPU/CPU stärker.",
          ctrl: React.createElement("input", { type: "number", className: "st-num", min: 1, max: 8, value: cfg.parallel,
            onChange: (e) => setCfg((c) => ({ ...c, parallel: Math.max(1, Math.min(8, +e.target.value)) })) }) })));
  }

  /* ============================================================
     SECTION: DARSTELLUNG
     ============================================================ */
  function SectionDarstellung({ cfg, setCfg }) {
    const tog = (k) => () => setCfg((c) => ({ ...c, [k]: !c[k] }));
    return React.createElement("div", { className: "st-section" },
      React.createElement("div", { className: "st-section-head" },
        React.createElement("h2", null, "Darstellung"),
        React.createElement("p", null, "Galerie-Raster, Metadaten-Dichte und Sprache.")),

      React.createElement(Group, { label: "Galerie" },
        React.createElement(Row, { title: "Standardgröße Thumbnail",
          sub: "Beeinflusst die Spaltenbreite im Raster.",
          ctrl: React.createElement("select", { className: "st-select", value: cfg.thumbSize,
            onChange: (e) => setCfg((c) => ({ ...c, thumbSize: e.target.value })) },
            React.createElement("option", { value: "s" }, "Klein (200 px)"),
            React.createElement("option", { value: "m" }, "Mittel (280 px)"),
            React.createElement("option", { value: "l" }, "Groß (360 px)")) }),
        React.createElement(Row, { title: "Metadaten unter Bild anzeigen",
          sub: "Zeigt Personen-Avatar, Quelle und Tags unter jedem Bild im Raster.",
          ctrl: React.createElement(Switch, { on: cfg.showMeta, onClick: tog("showMeta") }) }),
        React.createElement(Row, { title: "Animations-Effekte reduzieren",
          sub: "Deaktiviert Überblend- und Slide-Animationen für barrierefreieres Erleben.",
          ctrl: React.createElement(Switch, { on: cfg.reducedMotion, onClick: tog("reducedMotion") }) })),

      React.createElement(Group, { label: "Sprache & Region" },
        React.createElement(Row, { title: "Sprache",
          ctrl: React.createElement("select", { className: "st-select", value: cfg.locale,
            onChange: (e) => setCfg((c) => ({ ...c, locale: e.target.value })) },
            React.createElement("option", { value: "de" }, "Deutsch"),
            React.createElement("option", { value: "en" }, "English")) }),
        React.createElement(Row, { title: "Datumsformat",
          ctrl: React.createElement("select", { className: "st-select", value: cfg.dateFormat,
            onChange: (e) => setCfg((c) => ({ ...c, dateFormat: e.target.value })) },
            React.createElement("option", { value: "dmy" }, "TT.MM.JJJJ"),
            React.createElement("option", { value: "ymd" }, "JJJJ-MM-TT"),
            React.createElement("option", { value: "mdy" }, "MM/DD/YYYY")) })));
  }

  /* ============================================================
     SECTION: BEARBEITUNG — Flux2 Templates + Upscale Settings
     ============================================================ */

  const EMPTY_TEMPLATE = { name: "", prompt: "", strength: 0.65, steps: 20, guidance: 7.5, seed: -1 };

  function TemplateEditor({ t, onSave, onCancel }) {
    const [draft, setDraft] = React.useState({ ...t });
    const set = (k) => (v) => setDraft((d) => ({ ...d, [k]: v }));
    return React.createElement("div", { style: { background: "var(--bg-2)", border: "1px solid var(--accent-line)", borderRadius: "var(--radius)", padding: "13px 14px", marginBottom: 8 } },
      React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 10 } },
        React.createElement("div", null,
          React.createElement("div", { className: "st-row-title", style: { marginBottom: 5 } }, "Name"),
          React.createElement("input", { className: "st-num", style: { width: "100%", textAlign: "left", fontFamily: "inherit", fontSize: 13, padding: "8px 11px" }, value: draft.name, placeholder: "Template-Name …", onChange: (e) => set("name")(e.target.value) })),
        React.createElement("div", null,
          React.createElement("div", { className: "st-row-title", style: { marginBottom: 5 } }, "Prompt"),
          React.createElement("textarea", { className: "md-textarea", rows: 4, value: draft.prompt, placeholder: "Prompt … {person} wird durch den Namen ersetzt.", onChange: (e) => set("prompt")(e.target.value) })),
        React.createElement(SliderRow, { title: "Stärke (strength)", min: 0.1, max: 0.99, step: 0.01, value: draft.strength, onChange: set("strength"), fmt: (v) => v.toFixed(2) }),
        React.createElement(SliderRow, { title: "Schritte (steps)", min: 10, max: 50, step: 1, value: draft.steps, onChange: set("steps") }),
        React.createElement(SliderRow, { title: "CFG-Skala (guidance)", min: 1, max: 15, step: 0.5, value: draft.guidance, onChange: set("guidance"), fmt: (v) => v.toFixed(1) }),
        React.createElement("div", { className: "st-row-title", style: { marginBottom: 4 } }, "Seed"),
        React.createElement("div", { style: { display: "flex", gap: 8 } },
          React.createElement("input", { type: "number", className: "st-num", style: { flex: 1, textAlign: "left" }, value: draft.seed, onChange: (e) => set("seed")(+e.target.value) }),
          React.createElement("button", { className: "st-btn ghost", onClick: () => set("seed")(-1) }, "↩ Zufall")),
        React.createElement("div", { style: { display: "flex", gap: 8, marginTop: 4 } },
          React.createElement("button", { className: "st-btn ghost", style: { flex: 1 }, onClick: onCancel }, "Abbrechen"),
          React.createElement("button", { className: "st-btn accent", style: { flex: 1 }, disabled: !draft.name.trim() || !draft.prompt.trim(), onClick: () => onSave(draft) },
            React.createElement(Icon, { name: "check", size: 14 }), draft.id ? "Speichern" : "Hinzufügen"))));
  }

  function SectionBearbeitung() {
    const { useState: uS, useEffect: uE } = React;
    const [templates, setTemplates] = uS(() => window.EditorStore ? window.EditorStore.get().templates : []);
    const [upscale, setUpscale] = uS(() => window.EditorStore ? window.EditorStore.get().upscale : {});
    const [editing, setEditing] = uS(null); // null | "new" | template-id
    const [draft, setDraft] = uS(null);

    uE(() => {
      if (!window.EditorStore) return;
      setTemplates(window.EditorStore.get().templates);
      setUpscale(window.EditorStore.get().upscale);
      return window.EditorStore.subscribe((cfg) => { setTemplates(cfg.templates); setUpscale(cfg.upscale); });
    }, []);

    const startNew = () => { setEditing("new"); setDraft({ ...EMPTY_TEMPLATE }); };
    const startEdit = (t) => { setEditing(t.id); setDraft({ ...t }); };
    const cancelEdit = () => { setEditing(null); setDraft(null); };
    const saveTemplate = (d) => {
      if (!window.EditorStore) return;
      if (editing === "new") window.EditorStore.addTemplate(d);
      else window.EditorStore.updateTemplate(editing, d);
      setEditing(null); setDraft(null);
    };
    const deleteTemplate = (id) => { if (window.EditorStore) window.EditorStore.deleteTemplate(id); };
    const setU = (k) => (v) => { if (window.EditorStore) window.EditorStore.setUpscale({ [k]: v }); };

    return React.createElement("div", { className: "st-section" },
      React.createElement("div", { className: "st-section-head" },
        React.createElement("h2", null, "Bearbeitung"),
        React.createElement("p", null, "Flux2-Templates verwalten und Upscale-Standardeinstellungen für den Editor festlegen.")),

      /* ---- Flux2 Templates ---- */
      React.createElement(Group, { label: "Flux2-Templates" },
        React.createElement("div", { style: { padding: "14px 16px" } },
          templates.length === 0 && editing !== "new" &&
            React.createElement(Note, { type: "info", icon: "info" }, "Noch keine Templates. „Neu“ klicken zum Anlegen."),
          templates.map((t) =>
            editing === t.id
              ? React.createElement(TemplateEditor, { key: t.id, t: draft, onSave: saveTemplate, onCancel: cancelEdit })
              : React.createElement("div", { key: t.id, style: { display: "flex", alignItems: "flex-start", gap: 12, padding: "10px 0", borderBottom: "1px solid var(--line)" } },
                  React.createElement("div", { style: { flex: 1, minWidth: 0 } },
                    React.createElement("div", { className: "st-row-title", style: { marginBottom: 3 } }, t.name),
                    React.createElement("div", { className: "st-row-sub", style: { overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, t.prompt),
                    React.createElement("div", { style: { display: "flex", gap: 6, marginTop: 6 } },
                      React.createElement("span", { className: "md-modetag" }, "str " + t.strength.toFixed(2)),
                      React.createElement("span", { className: "md-modetag" }, "s" + t.steps),
                      React.createElement("span", { className: "md-modetag" }, "cfg" + t.guidance.toFixed(1)),
                      React.createElement("span", { className: "md-modetag" }, t.seed === -1 ? "seed:rand" : "seed:" + t.seed))),
                  React.createElement("div", { style: { display: "flex", gap: 6, flexShrink: 0 } },
                    React.createElement("button", { className: "st-btn ghost", style: { height: 30, padding: "0 10px", fontSize: 12 }, onClick: () => startEdit(t) },
                      React.createElement(Icon, { name: "pencil", size: 13 }), "Bearbeiten"),
                    React.createElement("button", { className: "st-btn danger", style: { height: 30, padding: "0 10px", fontSize: 12 }, onClick: () => deleteTemplate(t.id) },
                      React.createElement(Icon, { name: "trash", size: 13 }))))),
          editing === "new" && React.createElement(TemplateEditor, { t: draft, onSave: saveTemplate, onCancel: cancelEdit }),
          editing !== "new" && React.createElement("div", { style: { paddingTop: 14 } },
            React.createElement("button", { className: "st-btn accent", onClick: startNew },
              React.createElement(Icon, { name: "plus", size: 14 }), "Neues Template")))),

      /* ---- Upscale Defaults ---- */
      React.createElement(Group, { label: "Upscale — Zielgröße & Kacheln" },
        React.createElement(Note, { type: "accent", icon: "info" }, "Standardwerte für alle Upscale-Operationen im Editor. Können pro Run überschrieben werden."),
        React.createElement(Row, { title: "Zielgröße (längste Seite)",
          sub: "Die längste Seite wird auf diesen Wert skaliert. Die andere Seite wird proportional angepasst.",
          ctrl: React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 6 } },
            React.createElement("input", { type: "number", className: "st-num",
              style: { width: 90 }, min: 256, max: 16384, step: 64,
              value: upscale.targetSize || 2048,
              onChange: (e) => setU("targetSize")(Math.max(256, +e.target.value)) }),
            React.createElement("span", { style: { fontSize: 12, color: "var(--text-3)" } }, "px")) }),
        React.createElement(Row, { title: "Kachelgröße",
          sub: "Quadratische Kacheln. 512 px für SD 1.5 · 768 oder 1024 px für SDXL.",
          ctrl: React.createElement("select", { className: "st-select",
            value: upscale.tileSize || 1024,
            onChange: (e) => setU("tileSize")(+e.target.value) },
            React.createElement("option", { value: 512 }, "512 px (SD 1.5)"),
            React.createElement("option", { value: 768 }, "768 px (SDXL)"),
            React.createElement("option", { value: 1024 }, "1024 px (SDXL)")) }),
        React.createElement(Row, { title: "Padding",
          sub: "Überlappung der Kacheln gegen sichtbare Naht-Kanten.",
          ctrl: React.createElement("select", { className: "st-select",
            value: upscale.tilePadding || 32,
            onChange: (e) => setU("tilePadding")(+e.target.value) },
            React.createElement("option", { value: 16 }, "16 px"),
            React.createElement("option", { value: 32 }, "32 px (Standard)"),
            React.createElement("option", { value: 64 }, "64 px"),
            React.createElement("option", { value: 128 }, "128 px")) }),
        React.createElement(SliderRow, { title: "Denoising Strength",
          sub: "0.15–0.25: Konservativ, nur schärfer · 0.30–0.40: Empfohlen (Hautporen, Texturen) · > 0.45: Artefakte / Kachelmuster möglich",
          min: 0.05, max: 0.5, step: 0.01,
          value: upscale.denoisingStrength || 0.2,
          fmt: (v) => v <= 0.25 ? v.toFixed(2) + " (Konservativ)" : v <= 0.40 ? v.toFixed(2) + " ★ Empfohlen" : v.toFixed(2) + " ⚠ Zu hoch",
          onChange: setU("denoisingStrength") })),

      /* ---- Tiled Refine (Flux2) ---- */
      React.createElement(Group, { label: "Ultimate SD Upscale — Tiled Refine (Flux2)" },
        React.createElement(Note, { type: "accent", icon: "info" }, "Standardwerte für den Flux2-Refine-Schritt. Im Editor können sie pro Run überschrieben werden."),
        React.createElement("div", { className: "st-row top" },
          React.createElement("div", { className: "st-row-body" },
            React.createElement("div", { className: "st-row-title" }, "Refine-Prompt"),
            React.createElement("div", { className: "st-row-sub", style: { marginBottom: 8 } }, "Beschreibt das Ziel für den Flux2-Refine-Schritt. Wird kachelweise auf das hochskalierte Bild angewendet."),
            React.createElement("textarea", { className: "md-textarea", rows: 3, value: upscale.refinePrompt || "", onChange: (e) => setU("refinePrompt")(e.target.value), placeholder: "Refine-Prompt …" }))),
        React.createElement(SliderRow, { title: "Refine-Schritte", min: 1, max: 40, step: 1, value: upscale.refineSteps || 1, onChange: setU("refineSteps") }),
        React.createElement(SliderRow, { title: "Refine CFG-Skala", min: 1, max: 15, step: 0.5, value: upscale.refineGuidance || 7.0, onChange: setU("refineGuidance"), fmt: (v) => v.toFixed(1) })));
  }

    /* ============================================================
     SECTION: TASTATURKÜRZEL
     ============================================================ */
  const SC_GROUPS = [
    { label: "Navigation", shortcuts: [
      { action: "Vorheriges Bild", keys: ["←"] },
      { action: "Nächstes Bild", keys: ["→"] },
      { action: "Lightbox schließen", keys: ["Esc"] },
      { action: "Galerie", keys: ["G"] },
      { action: "Personen", keys: ["P"] },
      { action: "Favoriten", keys: ["F"] },
    ]},
    { label: "Bild-Aktionen", shortcuts: [
      { action: "Favorit setzen / entfernen", keys: ["Space"] },
      { action: "Löschen (Papierkorb)", keys: ["Del"] },
      { action: "Tag hinzufügen", keys: ["T"] },
      { action: "Lightbox öffnen", keys: ["Enter"] },
      { action: "Mehrfachauswahl umschalten", keys: ["Shift", "Klick"] },
    ]},
    { label: "Suche & Filter", shortcuts: [
      { action: "Suche fokussieren", keys: ["/"] },
      { action: "Filter-Rail öffnen", keys: ["Shift", "F"] },
      { action: "Alle Filter zurücksetzen", keys: ["Esc"] },
    ]},
  ];

  function SectionShortcuts() {
    const [editing, setEditing] = useState(null); // "groupIdx_scIdx"
    const [sc, setSc] = useState(SC_GROUPS);
    const listenRef = useRef(null);

    useEffect(() => {
      if (!editing) return;
      const h = (e) => {
        e.preventDefault();
        const parts = [];
        if (e.metaKey || e.ctrlKey) parts.push("Ctrl");
        if (e.shiftKey) parts.push("Shift");
        if (e.altKey) parts.push("Alt");
        const k = e.key;
        if (!["Meta","Control","Shift","Alt"].includes(k)) parts.push(k === " " ? "Space" : k.length === 1 ? k.toUpperCase() : k);
        if (parts.length === 0) return;
        const [gi, si] = editing.split("_").map(Number);
        setSc((prev) => prev.map((g, gi2) => gi2 !== gi ? g : { ...g, shortcuts: g.shortcuts.map((s, si2) => si2 !== si ? s : { ...s, keys: parts }) }));
        setEditing(null);
      };
      window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h);
    }, [editing]);

    return React.createElement("div", { className: "st-section" },
      React.createElement("div", { className: "st-section-head" },
        React.createElement("h2", null, "Tastaturkürzel"),
        React.createElement("p", null, "Klicke auf einen Kürzel-Eintrag, um ihn neu zu belegen. Taste(n) drücken zum Speichern.")),
      editing && React.createElement(Note, { type: "accent", icon: "info" }, "Taste(n) drücken … Esc bricht ab."),
      React.createElement("div", { className: "st-shortcuts" },
        sc.map((grp, gi) =>
          React.createElement("div", { key: gi, className: "st-sc-group" },
            React.createElement("div", { className: "st-sc-group-lbl" }, grp.label),
            React.createElement("div", { className: "st-group" },
              grp.shortcuts.map((s, si) => {
                const key = gi + "_" + si;
                const isEditing = editing === key;
                return React.createElement("div", { key: si, className: "st-sc-row" + (isEditing ? " editing" : ""),
                  onClick: () => { if (!editing) setEditing(key); } },
                  React.createElement("div", { className: "st-sc-action" }, s.action),
                  React.createElement("div", { className: "st-sc-keys" },
                    isEditing
                      ? React.createElement("span", { className: "st-sc-listening" }, "Taste(n) drücken …")
                      : s.keys.map((k, i) => React.createElement("span", { key: i, className: "st-key" }, k))),
                  React.createElement("button", { className: "st-sc-edit", title: "Kürzel ändern", onClick: (e) => { e.stopPropagation(); setEditing(key); } },
                    React.createElement(Icon, { name: "pencil", size: 13 })));
              }))))),
      React.createElement("div", { style: { marginTop: 8, display: "flex", gap: 8 } },
        React.createElement("button", { className: "st-btn ghost", onClick: () => setSc(SC_GROUPS) },
          React.createElement(Icon, { name: "refresh", size: 14 }), "Auf Standard zurücksetzen")));
  }

  /* ============================================================
     SECTION: BACKUP & WARTUNG
     ============================================================ */
    /* ============================================================
     SECTION: INFO
     ============================================================ */
  function SectionInfo() {
    return React.createElement("div", { className: "st-section" },
      React.createElement("div", { className: "st-section-head" },
        React.createElement("h2", null, "Info"),
        React.createElement("p", null, "Version, Lizenz und Systemdetails.")),

      React.createElement(Group, { label: "Anwendung" },
        React.createElement("div", { className: "st-row" },
          React.createElement("div", { className: "st-row-body" },
            React.createElement("div", { className: "st-row-title" }, "Photofant"),
            React.createElement("div", { className: "st-row-sub" }, "Lokale, private Bildverwaltung · \u201evergisst nie\u201c")),
          React.createElement("div", { className: "st-row-ctrl" },
            React.createElement("span", { className: "st-ver" }, "v0.7.1-alpha"))),
        React.createElement("div", { className: "st-row top" },
          React.createElement("div", { className: "st-row-body" },
            React.createElement("dl", { className: "st-kv" },
              React.createElement("dt", null, "Backend"), React.createElement("dd", null, "FastAPI 0.111 · Python 3.12"),
              React.createElement("dt", null, "Datenbank"), React.createElement("dd", null, "SQLite 3.45 · 42 MB"),
              React.createElement("dt", null, "DB-Pfad"), React.createElement("dd", null, "~/Bilder/.photofant/db.sqlite"),
              React.createElement("dt", null, "Thumbnails-DB"), React.createElement("dd", null, "~/Bilder/.photofant/thumbnails.sqlite · 890 MB"),
              React.createElement("dt", null, "ONNX Runtime"), React.createElement("dd", null, "1.17.3"),
              React.createElement("dt", null, "Letzte Migration"), React.createElement("dd", null, "2026-05-22 · rev 0012"))))),

      React.createElement(Group, { label: "Laufzeitumgebung" },
        React.createElement("div", { className: "st-row top" },
          React.createElement("div", { className: "st-row-body" },
            React.createElement("dl", { className: "st-kv" },
              React.createElement("dt", null, "GPU"), React.createElement("dd", null, "NVIDIA RTX 4080 · 16 GB VRAM"),
              React.createElement("dt", null, "CUDA"), React.createElement("dd", null, "12.4"),
              React.createElement("dt", null, "HF_HUB_OFFLINE"), React.createElement("dd", null, "1 (gesetzt)"),
              React.createElement("dt", null, "TRANSFORMERS_OFFLINE"), React.createElement("dd", null, "1 (gesetzt)"))))),

      React.createElement(Note, { type: "accent", icon: "shield" },
        "Kein Netzwerkverkehr zur Laufzeit. Alle Daten bleiben lokal. Keine Authentifizierung, kein Account, keine Telemetrie."));
  }

  /* ============================================================
     MAIN SETTINGS VIEW
     ============================================================ */
  const SECTIONS = [
    { id: "bibliothek",   icon: "folder",   label: "Bibliothek" },
    { id: "verarbeitung", icon: "refresh",  label: "Verarbeitung" },
    { id: "darstellung",  icon: "gallery",  label: "Darstellung" },
    { id: "bearbeitung",  icon: "pencil",   label: "Bearbeitung" },
    { id: "shortcuts",    icon: "settings", label: "Tastaturkürzel" },
    { id: "info",         icon: "info",     label: "Info" },
  ];

  function Settings() {
    const [active, setActive] = useState("bibliothek");
    const [mobileOpen, setMobileOpen] = useState(false);
    const [cfg, setCfg] = useState({
      libraryPath: "~/Bilder",
      modelsPath: "~/photofant/models",
      backupPath: "~/.photofant/backups",
      trashDays: 30,
      faceThreshold: 0.68,
      facePadding: 0.20,
      phashThreshold: 8,
      blurThreshold: 80,
      dupEmbedding: false,
      reviewQueue: true,
      autoTag: true,
      autoCaption: true,
      autoEmbed: true,
      autoRembg: false,
      parallel: 2,
      thumbSize: "m",
      showMeta: true,
      reducedMotion: false,
      locale: "de",
      dateFormat: "dmy",
      autoBackup: true,
    });

    const goSection = (id) => { setActive(id); setMobileOpen(true); };
    const goBack = () => setMobileOpen(false);

    const sectionContent = () => {
      switch (active) {
        case "bibliothek":   return React.createElement(SectionBibliothek, { cfg, setCfg });
        case "verarbeitung": return React.createElement(SectionVerarbeitung, { cfg, setCfg });
        case "darstellung":  return React.createElement(SectionDarstellung, { cfg, setCfg });
        case "bearbeitung":  return React.createElement(SectionBearbeitung);
        case "shortcuts":    return React.createElement(SectionShortcuts);
        case "info":         return React.createElement(SectionInfo);
        default:             return null;
      }
    };

    return React.createElement("div", { className: "st-page" },
      // left nav
      React.createElement("aside", { className: "st-nav" + (mobileOpen ? " section-open" : "") },
        React.createElement("div", { className: "st-nav-title" }, "Einstellungen"),
        SECTIONS.map((s) =>
          React.createElement("button", { key: s.id, className: "st-nav-item" + (active === s.id ? " on" : ""), onClick: () => goSection(s.id) },
            React.createElement("div", { className: "st-nav-ico" }, React.createElement(Icon, { name: s.icon, size: 16 })),
            s.label,
            s.warn && React.createElement("span", { className: "st-nav-badge" }, "!")))),
      // right body
      React.createElement("div", { className: "st-body" + (mobileOpen ? "" : " section-closed") },
        React.createElement("div", { className: "st-nav-back", onClick: goBack },
          React.createElement(Icon, { name: "chevronDown", size: 16, style: { transform: "rotate(90deg)" } }), "Einstellungen"),
        sectionContent()));
  }

  window.Settings = Settings;
})();
