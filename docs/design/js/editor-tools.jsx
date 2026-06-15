/* Photofant — Editor Tool Panels
   BasisPanel, UpscalePanel, Flux2Panel, InpaintPanel  → window.EditorTools */
(function () {
  const { Icon } = window;
  const { useState, useEffect, useRef } = React;

  /* ---- shared helpers ---- */
  function Ts({ label, children }) {
    return React.createElement("div", { className: "ed-ts" },
      label && React.createElement("div", { className: "ed-ts-lbl" }, label),
      children);
  }
  function Ctrl({ label, val, min, max, step, onChange, fmt }) {
    return React.createElement("div", { className: "ed-ctrl" },
      React.createElement("div", { className: "ed-ctrl-row" },
        React.createElement("span", { className: "ed-ctrl-lbl" }, label),
        React.createElement("span", { className: "ed-ctrl-val" }, fmt ? fmt(val) : val)),
      React.createElement("input", { type: "range", min, max, step, value: val, onChange: (e) => onChange(+e.target.value) }));
  }
  function Note({ type = "info", icon, children }) {
    return React.createElement("div", { className: "ed-note " + type },
      React.createElement(Icon, { name: icon || "info", size: 14 }),
      React.createElement("span", null, children));
  }

  /* ============================================================
     BASIS PANEL — Crop / Rotate / Mirror / Pad / Convert
     ============================================================ */
  const RATIOS = [
    { id: "free", label: "Frei" },
    { id: "1:1", label: "1:1", w: 1, h: 1 },
    { id: "4:3", label: "4:3", w: 4, h: 3 },
    { id: "3:4", label: "3:4", w: 3, h: 4 },
    { id: "16:9", label: "16:9", w: 16, h: 9 },
    { id: "3:2", label: "3:2", w: 3, h: 2 },
    { id: "2:3", label: "2:3", w: 2, h: 3 },
  ];

  function BasisPanel({ asset, onApply }) {
    const [cropRatio, setCropRatio] = useState("free");
    const [format, setFormat] = useState("keep"); // keep | png | jpeg
    const [quality, setQuality] = useState(92);
    const [padActive, setPadActive] = useState(false);

    const applyRotate = (dir) => onApply({ op: "rotate", label: dir === "cw" ? "90° im Uhrzeigersinn" : dir === "ccw" ? "90° gegen Uhrzeigersinn" : "180°", badge: "basis", params: { dir } });
    const applyMirror = (axis) => onApply({ op: "mirror", label: axis === "h" ? "Horizontal spiegeln" : "Vertikal spiegeln", badge: "basis", params: { axis } });
    const applyPad = () => onApply({ op: "pad", label: "Auf Quadrat aufgefüllt", badge: "basis", params: {} });
    const applyCrop = () => onApply({ op: "crop", label: "Zugeschnitten (" + (cropRatio === "free" ? "Frei" : cropRatio) + ")", badge: "basis", params: { ratio: cropRatio } });
    const applyConvert = () => onApply({ op: "convert", label: "Konvertiert → " + format.toUpperCase() + (format === "jpeg" ? " Q" + quality : ""), badge: "basis", params: { format, quality } });

    return React.createElement("div", { className: "ed-tool-content" },
      React.createElement(Ts, { label: "Zuschneiden" },
        React.createElement("div", { className: "ed-seg", style: { marginBottom: 10 } },
          RATIOS.map((r) => React.createElement("button", { key: r.id, className: cropRatio === r.id ? "on" : "", onClick: () => setCropRatio(r.id) }, r.label))),
        React.createElement(Note, { type: "info", icon: "info" }, "Crop-Rahmen direkt auf dem Canvas verschieben oder Verhältnis wählen."),
        React.createElement("div", { className: "ed-act-row" },
          React.createElement("button", { className: "ed-act primary", onClick: applyCrop }, React.createElement(Icon, { name: "crop", size: 15 }), "Zuschnitt anwenden"),
          React.createElement("button", { className: "ed-act ghost", title: "Smart-Crop auf Gesicht", onClick: () => onApply({ op: "smart_crop", label: "Smart-Crop (Gesicht)", badge: "basis", params: {} }) }, React.createElement(Icon, { name: "face", size: 15 })))),

      React.createElement(Ts, { label: "Drehen & Spiegeln" },
        React.createElement("div", { className: "ed-icon-seg", style: { marginBottom: 8 } },
          React.createElement("button", { onClick: () => applyRotate("ccw") },
            React.createElement(Icon, { name: "rotateCw", size: 18, style: { transform: "scaleX(-1)" } }), "−90°"),
          React.createElement("button", { onClick: () => applyRotate("cw") },
            React.createElement(Icon, { name: "rotateCw", size: 18 }), "+90°"),
          React.createElement("button", { onClick: () => applyRotate("180") },
            React.createElement(Icon, { name: "refresh", size: 18 }), "180°")),
        React.createElement("div", { className: "ed-icon-seg" },
          React.createElement("button", { onClick: () => applyMirror("h") },
            React.createElement(Icon, { name: "flipH", size: 18 }), "Horizontal"),
          React.createElement("button", { onClick: () => applyMirror("v") },
            React.createElement(Icon, { name: "flipH", size: 18, style: { transform: "rotate(90deg)" } }), "Vertikal"))),

      React.createElement(Ts, { label: "Pad to Square" },
        React.createElement(Note, { type: "info", icon: "info" }, "Füllt das Bild auf 1:1 auf — ohne Beschnitt. Nützlich für Trainingsset-Buckets."),
        React.createElement("button", { className: "ed-act ghost", onClick: applyPad }, React.createElement(Icon, { name: "expand2", size: 15 }), "Auf Quadrat aufüllen")),

      React.createElement(Ts, { label: "Format-Konvertierung" },
        React.createElement("div", { className: "ed-seg", style: { marginBottom: 12 } },
          [["keep", "Behalten"], ["png", "PNG"], ["jpeg", "JPEG"]].map(([id, l]) =>
            React.createElement("button", { key: id, className: format === id ? "on" : "", onClick: () => setFormat(id) }, l))),
        format === "jpeg" && React.createElement(Ctrl, { label: "JPEG-Qualität", val: quality, min: 60, max: 100, step: 1, onChange: setQuality }),
        format === "jpeg" && React.createElement(Note, { type: "warn", icon: "alertTriangle" }, "JPEG ist verlustbehaftet. Transparenz (Alpha) geht verloren."),
        React.createElement("button", { className: "ed-act ghost", disabled: format === "keep", onClick: applyConvert },
          React.createElement(Icon, { name: "download", size: 15 }), "Konvertieren")));
  }

  /* ============================================================
     UPSCALE PANEL — SeedVR2 direkt + Ultimate SD Upscale
     ============================================================ */
  const UPSCALE_MODELS = [
    { id: "seedvr2_3b_fp8",  label: "SeedVR2 3B fp8",    vram: "~12 GB", rec: true },
    { id: "seedvr2_3b_gguf", label: "SeedVR2 3B GGUF Q4", vram: "8 GB",  rec: false },
    { id: "seedvr2_7b_fp8",  label: "SeedVR2 7B fp8",    vram: "~16 GB", rec: false },
  ];

  function UpscalePanel({ asset, generating, onGenerate }) {
    const [mode, setMode] = useState("direct"); // "direct" | "ultimate"
    const [model, setModel] = useState(() => window.EditorStore ? window.EditorStore.get().upscale.defaultModel : "seedvr2_3b_fp8");
    const [targetSize, setTargetSize] = useState(() => window.EditorStore ? (window.EditorStore.get().upscale.targetSize || 2048) : 2048);
    const [tileOverride, setTileOverride] = useState(false);
    const [tileSize, setTileSize] = useState(1024);
    const [tilePadding, setTilePadding] = useState(32);
    const [denoisingStrength, setDenoisingStrength] = useState(0.2);
    const [refineOverride, setRefineOverride] = useState(false);
    const [refinePrompt, setRefinePrompt] = useState("");
    const [refineSteps, setRefineSteps] = useState(1);
    const [upscaleCfg, setUpscaleCfg] = useState(() => window.EditorStore ? window.EditorStore.get().upscale : {});

    useEffect(() => {
      if (!window.EditorStore) return;
      const cfg = window.EditorStore.get().upscale;
      setUpscaleCfg(cfg);
      setTileSize(cfg.tileSize || 1024);
      setTilePadding(cfg.tilePadding || 32);
      setDenoisingStrength(cfg.denoisingStrength || 0.2);
      setRefinePrompt(cfg.refinePrompt || "");
      return window.EditorStore.subscribe((c) => {
        setUpscaleCfg(c.upscale);
        if (!tileOverride) {
          setTileSize(c.upscale.tileSize || 1024);
          setTilePadding(c.upscale.tilePadding || 32);
          setDenoisingStrength(c.upscale.denoisingStrength || 0.2);
        }
        if (!refineOverride) {
          setRefinePrompt(c.upscale.refinePrompt || "");
        }
      });
    }, []);

    const selModel = UPSCALE_MODELS.find(m => m.id === model) || UPSCALE_MODELS[0];

    // Output dimensions: longest side -> targetSize
    const longest = Math.max(asset.w || 1, asset.h || 1);
    const outScale = targetSize / longest;
    const outW = Math.round((asset.w || 0) * outScale);
    const outH = Math.round((asset.h || 0) * outScale);

    const effTile = tileOverride ? tileSize : (upscaleCfg.tileSize || 1024);
    const effPadding = tileOverride ? tilePadding : (upscaleCfg.tilePadding || 32);
    const effDenoising = tileOverride ? denoisingStrength : (upscaleCfg.denoisingStrength || 0.2);
    const effRefineSteps = tileOverride ? refineSteps : 1;

    const denoisingLabel = (v) => {
      if (v <= 0.25) return v.toFixed(2) + " · Konservativ";
      if (v <= 0.40) return v.toFixed(2) + " · Empfohlen";
      return v.toFixed(2) + " · Achtung: Artefakte";
    };

    return React.createElement("div", { className: "ed-tool-content" },

      // mode picker
      React.createElement(Ts, { label: "Modus" },
        React.createElement("div", { className: "ed-icon-seg", style: { gap: 7 } },
          React.createElement("button", { className: mode === "direct" ? "on" : "", style: { flexDirection: "row", gap: 6, height: 40, fontSize: 12 }, onClick: () => setMode("direct") },
            React.createElement(Icon, { name: "expand2", size: 16 }), "SeedVR2 direkt"),
          React.createElement("button", { className: mode === "ultimate" ? "on" : "", style: { flexDirection: "row", gap: 6, height: 40, fontSize: 12 }, onClick: () => setMode("ultimate") },
            React.createElement(Icon, { name: "refresh", size: 16 }), "Ultimate SD Upscale"))),

      // SeedVR2 model (both modes)
      React.createElement(Ts, { label: "SeedVR2-Modell" },
        React.createElement("select", { className: "ed-select", value: model, onChange: (e) => setModel(e.target.value) },
          UPSCALE_MODELS.map((m) =>
            React.createElement("option", { key: m.id, value: m.id }, m.label + (m.rec ? " ★" : "") + " · " + m.vram)))),

      // Target size (both modes)
      React.createElement(Ts, { label: "Zielgröße (längste Seite)" },
        React.createElement("div", { className: "ed-seg", style: { marginBottom: 10, flexWrap: "wrap" } },
          [1024, 2048, 3072, 4096].map((s) =>
            React.createElement("button", { key: s, className: targetSize === s ? "on" : "", onClick: () => setTargetSize(s) },
              s === 1024 ? "1k" : s === 2048 ? "2k" : s === 3072 ? "3k" : "4k"))),
        React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8 } },
          React.createElement("input", { type: "number",
            style: { width: 88, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-s)", color: "var(--text)", padding: "6px 10px", fontSize: 13, outline: "none", fontFamily: "var(--mono)", textAlign: "right" },
            value: targetSize, min: 256, max: 16384, step: 64,
            onChange: (e) => setTargetSize(Math.max(256, +e.target.value)) }),
          React.createElement("span", { style: { fontSize: 12, color: "var(--text-3)", fontFamily: "var(--mono)" } },
            "px → " + outW + "×" + outH))),

      // Ultimate: Tile & Denoising settings
      mode === "ultimate" && React.createElement(Ts, { label: "Kachel-Einstellungen" },
        React.createElement(Note, { type: "accent", icon: "info" },
          "Standard aus Einstellungen → Bearbeitung. Änderungen gelten nur für diesen Run."),
        React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8, marginBottom: 6 } },
          React.createElement("span", { style: { fontSize: 12, color: "var(--text-3)", minWidth: 80 } }, "Kachelgröße"),
          React.createElement("div", { className: "ed-seg", style: { flex: 1 } },
            [512, 768, 1024].map((s) =>
              React.createElement("button", { key: s, className: effTile === s ? "on" : "",
                onClick: () => { setTileOverride(true); setTileSize(s); } }, s))),
          !tileOverride && React.createElement("span", { style: { fontSize: 10, color: "var(--accent)", fontWeight: 600, whiteSpace: "nowrap" } }, "Einst.")),
        React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8, marginBottom: 6 } },
          React.createElement("span", { style: { fontSize: 12, color: "var(--text-3)", minWidth: 80 } }, "Padding"),
          React.createElement("div", { className: "ed-seg", style: { flex: 1 } },
            [16, 32, 64, 128].map((s) =>
              React.createElement("button", { key: s, className: effPadding === s ? "on" : "",
                onClick: () => { setTileOverride(true); setTilePadding(s); } }, s)))),
        React.createElement(Ctrl, { label: "Denoising Strength",
          val: effDenoising, min: 0.05, max: 0.5, step: 0.01,
          onChange: (v) => { setTileOverride(true); setDenoisingStrength(v); },
          fmt: denoisingLabel }),
        React.createElement(Ctrl, { label: "Refine-Schritte",
          val: effRefineSteps, min: 1, max: 40, step: 1,
          onChange: (v) => { setTileOverride(true); setRefineSteps(v); } }),
        tileOverride && React.createElement("button", {
          style: { fontSize: 11, color: "var(--accent)", fontWeight: 600, marginTop: 4 },
          onClick: () => { setTileOverride(false); const c = upscaleCfg; setTileSize(c.tileSize||1024); setTilePadding(c.tilePadding||32); setDenoisingStrength(c.denoisingStrength||0.2); setRefineSteps(1); }
        }, "↩ Auf Einstellungen zurücksetzen")),

      // Ultimate: Tiled Refine (Flux2)
      mode === "ultimate" && React.createElement(Ts, { label: "Tiled Refine (Flux2)" },
        React.createElement(Note, { type: "accent", icon: "info" },
          "Standard-Einstellungen aus den Einstellungen → Bearbeitung. Änderungen hier gelten nur für diesen Run."),
        React.createElement("div", { className: "ed-ctrl" },
          React.createElement("div", { className: "ed-ctrl-row" },
            React.createElement("span", { className: "ed-ctrl-lbl" }, "Refine-Prompt"),
            !refineOverride && React.createElement("span", { style: { fontSize: 10, color: "var(--accent)", fontWeight: 600 } }, "aus Einstellungen")),
          React.createElement("textarea", {
            rows: 3, value: refineOverride ? refinePrompt : upscaleCfg.refinePrompt || "",
            style: { width: "100%", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius)", color: "var(--text)", fontSize: 12, padding: "8px 10px", outline: "none", resize: "vertical", lineHeight: 1.5, opacity: refineOverride ? 1 : 0.7, fontFamily: "inherit" },
            placeholder: "Refine-Prompt …",
            onChange: (e) => { setRefineOverride(true); setRefinePrompt(e.target.value); }
          })),
        refineOverride && React.createElement("button", {
          style: { fontSize: 11, color: "var(--accent)", fontWeight: 600, marginTop: 4 },
          onClick: () => { setRefineOverride(false); }
        }, "↩ Auf Einstellungen zurücksetzen")),

      mode === "ultimate" && React.createElement(Note, { type: "info", icon: "info" },
        "Stage 1: SeedVR2 → " + outW + "×" + outH + " px · Kacheln " + effTile + "×" + effTile + " · Padding " + effPadding + " · Denoising " + effDenoising.toFixed(2) + ". Stage 2: Flux2 Refine (" + effRefineSteps + " Steps)."),

      mode === "direct" && React.createElement(Note, { type: "info", icon: "info" },
        "SeedVR2 → " + outW + " × " + outH + " px · als neue Version gespeichert."),

      React.createElement("button", { className: "ed-act primary", style: { marginTop: 8 }, disabled: generating,
        onClick: () => onGenerate({
          op: mode === "ultimate" ? "ultimate_upscale" : "upscale",
          label: mode === "ultimate" ? "Ultimate SD Upscale → " + targetSize + " px + Refine" : "SeedVR2 Upscale → " + targetSize + " px",
          badge: "upscale",
          params: { model, targetSize, mode, tileSize: effTile, tilePadding: effPadding, denoisingStrength: effDenoising, refinePrompt: refineOverride ? refinePrompt : upscaleCfg.refinePrompt, refineSteps: effRefineSteps },
          genLabel: mode === "ultimate" ? "Ultimate SD Upscale läuft …" : "SeedVR2 läuft …",
          genSub: mode === "ultimate" ? "Stage 1: " + selModel.label + " → " + outW + "×" + outH + " · Stage 2: Flux2 Tiled Refine" : selModel.label + " · → " + outW + "×" + outH,
        }) },
        generating
          ? React.createElement(React.Fragment, null, React.createElement("div", { className: "ed-gen-ring", style: { width: 16, height: 16, borderWidth: 2 } }), "Wird berechnet …")
          : React.createElement(React.Fragment, null, React.createElement(Icon, { name: mode === "ultimate" ? "refresh" : "expand2", size: 15 }), mode === "ultimate" ? "Ultimate Upscale starten" : "SeedVR2 starten")));
  }

    /* ============================================================
     FLUX2 PANEL — Prompt + Template Library + Params
     ============================================================ */
  // Templates now loaded from EditorStore (localStorage)

  function Flux2Panel({ asset, generating, onGenerate }) {
    const [prompt, setPrompt] = useState("");
    const [strength, setStrength] = useState(0.65);
    const [steps, setSteps] = useState(20);
    const [guidance, setGuidance] = useState(7.5);
    const [seed, setSeed] = useState(-1);
    const [tmpl, setTmpl] = useState(null);
    const [templates, setTemplates] = useState(() => window.EditorStore ? window.EditorStore.get().templates : []);

    useEffect(() => {
      if (!window.EditorStore) return;
      setTemplates(window.EditorStore.get().templates);
      return window.EditorStore.subscribe((cfg) => setTemplates(cfg.templates));
    }, []);

    const applyTemplate = (t) => {
      setTmpl(t.id);
      setPrompt(t.prompt.replace("{person}", asset.personName || "person"));
      setStrength(t.strength);
      setSteps(t.steps);
      setGuidance(t.guidance);
      setSeed(t.seed);
    };

    return React.createElement("div", { className: "ed-tool-content" },
      React.createElement(Ts, { label: "Templates" },
        React.createElement("div", { className: "ed-tmpl-grid" },
          templates.length === 0
              ? React.createElement("div", { style: { gridColumn: "1/-1", fontSize: 12, color: "var(--text-3)", padding: "8px 4px" } }, "Noch keine Templates — unter Einstellungen → Bearbeitung anlegen.")
              : templates.map((t) =>
            React.createElement("button", { key: t.id, className: "ed-tmpl" + (tmpl === t.id ? " on" : ""), onClick: () => applyTemplate(t) },
              React.createElement("div", { className: "ed-tmpl-name" }, t.name),
              React.createElement("div", { className: "ed-tmpl-prompt" }, t.prompt),
              React.createElement("div", { className: "ed-tmpl-params" },
                React.createElement("span", { className: "ed-tmpl-p" }, "str " + t.strength),
                React.createElement("span", { className: "ed-tmpl-p" }, "s" + t.steps),
                React.createElement("span", { className: "ed-tmpl-p" }, "cfg" + t.guidance))))),

      React.createElement(Ts, { label: "Prompt" },
        React.createElement("div", { className: "ed-ctrl" },
          React.createElement("textarea", { rows: 4, value: prompt, placeholder: "Beschreibe den gewünschten Edit … {person} wird durch den Namen ersetzt.", onChange: (e) => setPrompt(e.target.value) }))),

      React.createElement(Ts, { label: "Parameter" },
        React.createElement(Ctrl, { label: "Stärke (strength)", val: strength, min: 0.1, max: 0.99, step: 0.01, onChange: setStrength, fmt: (v) => v.toFixed(2) }),
        React.createElement(Ctrl, { label: "Schritte (steps)", val: steps, min: 10, max: 50, step: 1, onChange: setSteps }),
        React.createElement(Ctrl, { label: "CFG-Skala (guidance)", val: guidance, min: 1, max: 15, step: 0.5, onChange: setGuidance, fmt: (v) => v.toFixed(1) }),
        React.createElement("div", { className: "ed-ctrl" },
          React.createElement("div", { className: "ed-ctrl-row" },
            React.createElement("span", { className: "ed-ctrl-lbl" }, "Seed"),
            React.createElement("span", { className: "ed-ctrl-val" }, seed === -1 ? "Zufällig" : seed)),
          React.createElement("div", { style: { display: "flex", gap: 7, marginTop: 6 } },
            React.createElement("input", { type: "number", value: seed, min: -1, style: { flex: 1, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-s)", color: "var(--text)", padding: "7px 10px", fontSize: 12, outline: "none", fontFamily: "var(--mono)" }, onChange: (e) => setSeed(+e.target.value) }),
            React.createElement("button", { className: "ed-act ghost", style: { width: 36, height: 34, padding: 0, flex: "none" }, onClick: () => setSeed(-1) }, React.createElement(Icon, { name: "refresh", size: 14 }))))),

      React.createElement("button", { className: "ed-act primary", disabled: generating || !prompt.trim(), onClick: () => onGenerate({ op: "flux_edit", label: "Flux2-Edit", badge: "flux", params: { prompt, strength, steps, guidance, seed }, genLabel: "FLUX.2 generiert", genSub: steps + " Steps · strength " + strength.toFixed(2) }) },
        generating ? React.createElement(React.Fragment, null, React.createElement("div", { className: "ed-gen-ring", style: { width: 16, height: 16, borderWidth: 2 } }), "Wird generiert …")
                   : React.createElement(React.Fragment, null, React.createElement(Icon, { name: "pencil", size: 15 }), "Edit generieren"))));
  }

  /* ============================================================
     INPAINT PANEL — Brush + Mask + Prompt
     ============================================================ */
  function InpaintPanel({ brushSize, setBrushSize, erasing, setErasing, onClearMask, generating, hasMask, onGenerate, prompt, setPrompt }) {
    return React.createElement("div", { className: "ed-tool-content" },
      React.createElement(Ts, { label: "Pinsel" },
        React.createElement("div", { className: "ed-icon-seg", style: { marginBottom: 12 } },
          React.createElement("button", { className: !erasing ? "on" : "", onClick: () => setErasing(false) },
            React.createElement(Icon, { name: "brush", size: 17 }), "Malen"),
          React.createElement("button", { className: erasing ? "on" : "", onClick: () => setErasing(true) },
            React.createElement(Icon, { name: "eraser", size: 17 }), "Löschen")),
        React.createElement(Ctrl, { label: "Pinselgröße", val: brushSize, min: 8, max: 120, step: 4, onChange: setBrushSize }),
        React.createElement("div", { className: "ed-brush-preview" },
          React.createElement("div", { className: "ed-brush-dot", style: { width: brushSize / 4, height: brushSize / 4 } }),
          React.createElement("div", { className: "ed-brush-dot", style: { width: brushSize / 2, height: brushSize / 2 } }),
          React.createElement("div", { className: "ed-brush-dot", style: { width: brushSize, height: brushSize } })),
        React.createElement("button", { className: "ed-act ghost", onClick: onClearMask }, React.createElement(Icon, { name: "trash", size: 14 }), "Maske zurücksetzen")),

      React.createElement(Note, { type: "info", icon: "info" }, "Markiere den Bereich, der entfernt oder verändert werden soll. Flux2 füllt den Bereich basierend auf dem Prompt auf."),

      React.createElement(Ts, { label: "Cleanup-Prompt (optional)" },
        React.createElement("div", { className: "ed-ctrl" },
          React.createElement("textarea", { rows: 3, value: prompt, placeholder: "Leer lassen für automatischen Hintergrund-Fill …", onChange: (e) => setPrompt(e.target.value) }))),

      React.createElement("button", { className: "ed-act primary", disabled: generating || !hasMask, onClick: () => onGenerate({ op: "inpaint", label: "Inpainting" + (prompt.trim() ? ": " + prompt.slice(0, 30) + "…" : " (Cleanup)"), badge: "inpaint", params: { prompt }, genLabel: "Inpainting läuft", genSub: "FLUX.2 · Maske wird gefüllt" }) },
        generating ? React.createElement(React.Fragment, null, React.createElement("div", { className: "ed-gen-ring", style: { width: 16, height: 16, borderWidth: 2 } }), "Wird berechnet …")
                   : React.createElement(React.Fragment, null, React.createElement(Icon, { name: "brush", size: 15 }), hasMask ? "Inpainting starten" : "Erst Bereich markieren")));
  }

  window.EditorTools = { BasisPanel, UpscalePanel, Flux2Panel, InpaintPanel };
})();
