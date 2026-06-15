/* Photofant — Modelle (Model-Management)
   Tier-gruppiete Karten + Drawer + Acquisition-Dialoge → window.Models */
(function () {
  const { Icon } = window;
  const { useState, useMemo } = React;

  /* ============================================================
     MOCK REGISTRY
     ============================================================ */
  const VRAM_GB = 16; // simulated detected VRAM

  const REGISTRY = [
    // ---- CORE ----
    { id: "buffalo_l", tier: "core", role: "face", name: "InsightFace buffalo_l",
      desc: "Face-Detection + Embedding-Extraktion. Wird für jedes Gesicht in der Sammlung benötigt.",
      format: "ONNX Bundle", size: "280 MB", license: "MIT (Code), Weights gesondert", licenseNC: false,
      managed: 1, status: "active", path: "~/photofant/models/buffalo_l", isDefault: true,
      capabilities: null,
      meta: { framework: "onnxruntime", version: "1.3.0", source: "insightface-zoo" },
    },
    { id: "wd14_swinv2", tier: "core", role: "tagger", name: "WD14 SwinV2-v3",
      desc: "Booru-Tag-Klassifikator. Schnell, speicherschonend, sehr gute Abdeckung.",
      format: "ONNX + CSV", size: "380 MB", license: "Permissiv", licenseNC: false,
      managed: 1, status: "active", path: "~/photofant/models/wd14_swinv2", isDefault: true,
      capabilities: null,
      meta: { framework: "onnxruntime", version: "v3", source: "SmilingWolf/wd-swinv2-tagger-v3" },
    },
    { id: "florence2_base", tier: "core", role: "captioner", name: "Florence-2-base",
      desc: "Schneller, MIT-lizenzierter Captioner. Deterministische Beam-Search, kein freier Prompt.",
      format: "ONNX / safetensors", size: "460 MB", license: "MIT", licenseNC: false,
      managed: 1, status: "active", path: "~/photofant/models/florence2_base", isDefault: true,
      capabilities: { mode: "task_token", presets: [
        { id: "detailed", name: "Detailliert", isDefault: true, config: { task_token: "<DETAILED_CAPTION>", max_new_tokens: 1024, num_beams: 3 } },
        { id: "short", name: "Kurz", config: { task_token: "<CAPTION>", max_new_tokens: 256, num_beams: 3 } },
        { id: "verbose", name: "Ausführlich", config: { task_token: "<MORE_DETAILED_CAPTION>", max_new_tokens: 2048, num_beams: 5 } },
      ]},
      meta: { framework: "onnxruntime", version: "base", source: "microsoft/Florence-2-base" },
    },
    { id: "clip_siglip", tier: "core", role: "search", name: "CLIP / SigLIP",
      desc: "Semantische Bild-Einbettungen für die thematische Suche.",
      format: "ONNX", size: "300 MB", license: "Permissiv", licenseNC: false,
      managed: 0, status: "inplace", path: "/opt/comfyui/models/clip/sigLIP_so400m.onnx",
      capabilities: null,
      meta: { framework: "onnxruntime", version: "so400m", source: "google/siglip-so400m-patch14-384" },
    },
    { id: "rembg", tier: "core", role: "bg", name: "rembg isnet-general-use",
      desc: "Hintergrundentfernung. Benötigt für Freisteller und saubere Gesichtsextraktion.",
      format: "ONNX", size: "178 MB", license: "MIT", licenseNC: false,
      managed: 0, status: "missing", path: null,
      capabilities: null,
      meta: { framework: "onnxruntime", version: "isnet-general-use", source: "danielgatis/rembg" },
    },
    // ---- OPTIONAL ----
    { id: "wd14_vit_large", tier: "optional", role: "tagger", name: "WD14 ViT-Large",
      desc: "Genauerer Tagger — langsamer, aber bessere Qualität bei schwierigen Bildtypen.",
      format: "ONNX", size: "1.2 GB", license: "Permissiv", licenseNC: false,
      managed: 0, status: "available", path: null,
      capabilities: null,
      meta: { framework: "onnxruntime", version: "v3", source: "SmilingWolf/wd-vit-large-tagger-v3" },
    },
    { id: "florence2_large", tier: "optional", role: "captioner", name: "Florence-2-large",
      desc: "Größere Florence-Variante — spürbar bessere Beschreibungsqualität.",
      format: "ONNX / safetensors", size: "1.5 GB", license: "MIT", licenseNC: false,
      managed: 0, status: "available", path: null,
      capabilities: { mode: "task_token", presets: [
        { id: "detailed", name: "Detailliert", isDefault: true, config: { task_token: "<DETAILED_CAPTION>", max_new_tokens: 1024, num_beams: 3 } },
      ]},
      meta: { framework: "onnxruntime", version: "large", source: "microsoft/Florence-2-large" },
    },
    { id: "joycaption", tier: "optional", role: "captioner", name: "JoyCaption Beta2",
      desc: "Geführter Captioner mit Stil-Bausteinen. Ideal für konsistente Trainingssets.",
      format: "safetensors", size: "16–17 GB", license: "Bitte prüfen", licenseNC: false,
      managed: 0, status: "missing", path: null,
      capabilities: { mode: "instruct_guided", presets: [
        { id: "descriptive", name: "Descriptive", isDefault: true, config: { caption_type: "Descriptive", length: "medium", extras: [] } },
        { id: "booru", name: "Booru-Tags", config: { caption_type: "Booru-Tag-Liste", length: "any", extras: [] } },
        { id: "sdprompt", name: "SD-Prompt", config: { caption_type: "Stable-Diffusion-Prompt", length: "medium", extras: [] } },
      ]},
      meta: { framework: "torch", version: "beta2", source: "fancyfeast/llama-joycaption-beta-two-hf-llava" },
    },
    { id: "qwen25vl", tier: "optional", role: "captioner", name: "Qwen2.5-VL 7B",
      desc: "Freier Instruction-Captioner. Flexibelster Ausgabestil über System-Prompt.",
      format: "safetensors", size: "~15 GB", license: "Apache 2.0", licenseNC: false,
      managed: 0, status: "missing", path: null,
      capabilities: { mode: "instruct", presets: [
        { id: "natural", name: "Natürliche Prosa", isDefault: true, config: {
            system_prompt: "Describe this image in natural, flowing prose. Be accurate and concise.",
            user_prompt: "Describe this image.", temperature: 0.7, top_p: 0.9, max_new_tokens: 512, repetition_penalty: 1.05,
          }},
        { id: "tags", name: "Tag-Stil", config: {
            system_prompt: "Output a comma-separated list of descriptive tags for this image. Focus on subject, style, mood, colors.",
            user_prompt: "List the tags for this image.", temperature: 0.5, top_p: 0.9, max_new_tokens: 256, repetition_penalty: 1.1,
          }},
      ]},
      meta: { framework: "torch", version: "7B-Instruct", source: "Qwen/Qwen2.5-VL-7B-Instruct" },
    },
    // ---- GENERATIV ----
    { id: "flux2_klein", tier: "generativ", role: "edit", name: "FLUX.2 [klein] 9B",
      desc: "Generatives Bearbeitungsmodell. Erfordert Diffusion, Text-Encoder (Qwen3) und VAE.",
      format: "safetensors / GGUF", size: "18 GB (bf16) / 9 GB (fp8)", license: "non-commercial", licenseNC: true,
      managed: 0, status: "incomplete", path: null,
      components: {
        diffusion: { label: "Diffusion / Transformer", required: true, path: "/mnt/models/flux2/flux2-dev.safetensors", ok: true, format: "safetensors" },
        text_encoder: { label: "Text-Encoder (Qwen3)", required: true, path: "/mnt/models/flux2/qwen3-encoder.safetensors", ok: true, format: "safetensors" },
        vae: { label: "VAE", required: true, path: null, ok: false, format: "safetensors" },
      },
      variants: [
        { id: "bf16", label: "bf16", size: "18.2 GB", vram: "~29 GB", rec: false },
        { id: "fp8", label: "fp8", size: "~9 GB", vram: "~24 GB", rec: true },
        { id: "gguf_q4", label: "GGUF Q4", size: "~4.5 GB", vram: "~12 GB", rec: false, community: true },
      ],
      capabilities: null,
      meta: { framework: "torch/diffusers", version: "dev", source: "black-forest-labs/FLUX.2-dev" },
    },
    { id: "seedvr2_3b", tier: "generativ", role: "upscale", name: "SeedVR2 3B",
      desc: "Schneller Real-World-Upscaler. Ideal für Bilder bis 4K auf mittelstarker GPU.",
      format: "safetensors / GGUF", size: "6.2 GB (fp16) / 1.9 GB (GGUF-Q4)", license: "Apache 2.0", licenseNC: false,
      managed: 0, status: "available", path: null,
      components: {
        diffusion: { label: "Diffusion", required: true, path: null, ok: false, format: "safetensors" },
        vae: { label: "VAE", required: true, path: null, ok: false, format: "safetensors" },
      },
      variants: [
        { id: "fp16", label: "fp16", size: "6.2 GB", vram: "16 GB+", rec: false },
        { id: "fp8", label: "fp8", size: "3.4 GB", vram: "~12 GB", rec: VRAM_GB >= 12 && VRAM_GB < 16 },
        { id: "gguf_q4", label: "GGUF Q4", size: "1.9 GB", vram: "8 GB", rec: VRAM_GB < 12 },
      ],
      capabilities: null,
      meta: { framework: "torch/diffusers", version: "3B", source: "ByteDance/SeedVR2-3B" },
    },
    { id: "seedvr2_7b", tier: "generativ", role: "upscale", name: "SeedVR2 7B",
      desc: "Höchste Upscaling-Qualität. Für Bilder mit viel Detail und starke GPUs.",
      format: "safetensors / GGUF", size: "14.5 GB (fp16) / 4.6 GB (GGUF-Q4)", license: "Apache 2.0", licenseNC: false,
      managed: 0, status: "available", path: null,
      components: {
        diffusion: { label: "Diffusion", required: true, path: null, ok: false, format: "safetensors" },
        vae: { label: "VAE", required: true, path: null, ok: false, format: "safetensors" },
      },
      variants: [
        { id: "fp16", label: "fp16", size: "14.5 GB", vram: "20 GB+", rec: false, warn: VRAM_GB < 20 ? "< " + VRAM_GB + " GB erkannt" : null },
        { id: "fp8", label: "fp8", size: "8.2 GB", vram: "~16 GB", rec: VRAM_GB >= 16, warn: VRAM_GB < 16 ? "< " + VRAM_GB + " GB erkannt" : null },
        { id: "gguf_q4", label: "GGUF Q4", size: "4.6 GB", vram: "~12 GB", rec: VRAM_GB < 16 },
      ],
      capabilities: null,
      meta: { framework: "torch/diffusers", version: "7B", source: "ByteDance/SeedVR2-7B" },
    },
  ];

  const TIERS = [
    { id: "core", label: "Core", desc: "Immer aktiv · ONNX Runtime · läuft auch auf CPU", badge: "core" },
    { id: "optional", label: "Optional / Heavy", desc: "Torch · nur bei Bedarf laden · empfohlen für bessere Qualität", badge: "optional" },
    { id: "generativ", label: "Generativ", desc: "Flux2, SeedVR2 · GPU + zweistellige GB VRAM + Disk", badge: "generativ" },
  ];

  const ROLE_META = {
    face:      { icon: "face",    label: "Face-Analyse" },
    tagger:    { icon: "tag",     label: "Tagger" },
    captioner: { icon: "text",    label: "Captioner" },
    search:    { icon: "search",  label: "Semantische Suche" },
    bg:        { icon: "layers",  label: "Hintergrund" },
    upscale:   { icon: "refresh", label: "Upscale" },
    edit:      { icon: "pencil",  label: "Generatives Editing" },
  };

  const STATUS_META = {
    active:     { cls: "active",     dot: true, label: "Aktiv" },
    available:  { cls: "available",  dot: true, label: "Nicht installiert" },
    loading:    { cls: "loading",    dot: false, label: "Lädt …" },
    missing:    { cls: "missing",    dot: true, label: "Nicht konfiguriert" },
    inplace:    { cls: "inplace",    dot: true, label: "In-Place" },
    incomplete: { cls: "incomplete", dot: true, label: "Unvollständig" },
  };

  /* ============================================================
     SHARED SMALL COMPONENTS
     ============================================================ */
  function StatusChip({ status }) {
    const m = STATUS_META[status] || STATUS_META.missing;
    return React.createElement("span", { className: "md-status " + m.cls },
      m.dot && React.createElement("span", { className: "dot" }),
      m.label);
  }

  function ModelIcon({ model }) {
    const rm = ROLE_META[model.role] || { icon: "refresh", label: "" };
    return React.createElement("div", { className: "md-ico role-" + model.role },
      React.createElement(Icon, { name: rm.icon, size: 20 }));
  }

  function CompChips({ components }) {
    if (!components) return null;
    return React.createElement("div", { className: "md-comp" },
      Object.entries(components).map(([key, c]) =>
        React.createElement("span", { key, className: "md-comp-chip " + (c.ok ? "ok" : "miss") },
          React.createElement(Icon, { name: c.ok ? "check" : "alertTriangle", size: 12 }), c.label)));
  }

  /* ============================================================
     MODEL CARD
     ============================================================ */
  function ModelCard({ model, onClick }) {
    const rm = ROLE_META[model.role] || { icon: "refresh", label: model.role };
    const sm = STATUS_META[model.status] || STATUS_META.missing;
    const isInc = model.status === "incomplete";
    const isLoading = model.status === "loading";

    return React.createElement("button", {
      className: "md-card is-" + model.status, onClick: () => onClick(model),
    },
      React.createElement("div", { className: "md-card-top" },
        React.createElement(ModelIcon, { model }),
        React.createElement("div", { className: "md-card-id" },
          React.createElement("div", { className: "md-name" },
            model.name,
            model.isDefault && React.createElement("span", { className: "md-default", title: "Standard" }, React.createElement(Icon, { name: "star", size: 13 }))),
          React.createElement("div", { className: "md-role" }, rm.label + " · " + model.format)),
        React.createElement(StatusChip, { status: model.status })),

      React.createElement("p", { className: "md-desc" }, model.desc),

      model.components && React.createElement(CompChips, { components: model.components }),

      isLoading && React.createElement("div", { className: "md-prog" },
        React.createElement("div", { className: "md-prog-top" }, React.createElement("span", null, "Herunterladen …"), React.createElement("span", null, "42%")),
        React.createElement("div", { className: "md-prog-bar" }, React.createElement("i", { style: { width: "42%" } }))),

      React.createElement("div", { className: "md-foot" },
        React.createElement("div", { className: "md-meta" },
          React.createElement("span", null, model.size),
          React.createElement("span", { className: "dotsep" }, "·"),
          React.createElement("span", null, model.meta.framework),
          model.licenseNC && React.createElement(React.Fragment, null,
            React.createElement("span", { className: "dotsep" }, "·"),
            React.createElement("span", { style: { color: "var(--warn)", fontWeight: 600 } }, "non-commercial"))),
        React.createElement("div", { className: "md-foot-spacer" }),
        React.createElement("span", { className: "md-linkbtn" }, "Details")));
  }

  /* ============================================================
     DETAIL DRAWER
     ============================================================ */
  function Drawer({ model, onClose, onDownload, onBind, onCaptionerSettings }) {
    const [selVariant, setSelVariant] = useState(() => {
      if (!model.variants) return null;
      const rec = model.variants.find((v) => v.rec);
      return rec ? rec.id : model.variants[0].id;
    });
    const rm = ROLE_META[model.role] || { icon: "refresh", label: model.role };
    const sm = STATUS_META[model.status] || STATUS_META.missing;
    const hasComponents = !!model.components;
    const canConfigure = model.capabilities != null;
    const isActive = model.status === "active" || model.status === "inplace";
    const isInstalled = ["active", "inplace", "incomplete"].includes(model.status);

    return React.createElement(React.Fragment, null,
      React.createElement("div", { className: "md-drawer-scrim", onClick: onClose }),
      React.createElement("div", { className: "md-drawer" },
        // head
        React.createElement("div", { className: "md-dr-head" },
          React.createElement(ModelIcon, { model }),
          React.createElement("div", { style: { flex: 1, minWidth: 0 } },
            React.createElement("div", { className: "md-dr-title" }, model.name),
            React.createElement("div", { className: "md-dr-role" }, rm.label + " · " + model.meta.framework),
            React.createElement("div", { style: { marginTop: 8 } }, React.createElement(StatusChip, { status: model.status }))),
          React.createElement("button", { className: "md-dr-close", onClick: onClose }, React.createElement(Icon, { name: "x", size: 18 }))),

        // body
        React.createElement("div", { className: "md-dr-body" },

          // gate warning if missing
          (model.status === "missing" || model.status === "available") &&
            React.createElement("div", { className: "md-sec" },
              React.createElement("div", { className: "md-gate" },
                React.createElement(Icon, { name: "alertTriangle", size: 15 }),
                React.createElement("div", null,
                  React.createElement("b", null, rm.label + " nicht verfügbar"),
                  " — dieses Feature bleibt deaktiviert, bis das Modell konfiguriert und validiert wurde."))),

          // incomplete warning
          model.status === "incomplete" && hasComponents &&
            React.createElement("div", { className: "md-sec" },
              React.createElement("div", { className: "md-gate" },
                React.createElement(Icon, { name: "alertTriangle", size: 15 }),
                React.createElement("div", null,
                  React.createElement("b", null, model.name + " unvollständig"),
                  " — alle Komponenten (Diffusion, Text-Encoder, VAE) müssen gesetzt sein."))),

          // description
          React.createElement("div", { className: "md-sec" },
            React.createElement("div", { className: "md-sec-t" }, "Über das Modell"),
            React.createElement("p", { style: { margin: 0, fontSize: 13, color: "var(--text-2)", lineHeight: 1.55, textWrap: "pretty" } }, model.desc)),

          // metadata KV
          React.createElement("div", { className: "md-sec" },
            React.createElement("div", { className: "md-sec-t" }, "Metadaten"),
            React.createElement("dl", { className: "md-kv" },
              React.createElement("dt", null, "Format"), React.createElement("dd", null, model.format),
              React.createElement("dt", null, "Größe"), React.createElement("dd", null, model.size),
              React.createElement("dt", null, "Framework"), React.createElement("dd", null, model.meta.framework),
              React.createElement("dt", null, "Version"), React.createElement("dd", null, model.meta.version),
              React.createElement("dt", null, "Quelle"), React.createElement("dd", null, model.meta.source),
              React.createElement("dt", null, "Lizenz"),
              React.createElement("dd", null, React.createElement("span", { className: "lic" + (model.licenseNC ? " nc" : "") },
                model.licenseNC && React.createElement(Icon, { name: "shield", size: 12 }), model.license)),
              isInstalled && model.status !== "incomplete" && React.createElement(React.Fragment, null,
                React.createElement("dt", null, "Pfad"),
                React.createElement("dd", null, model.path || "in-place")),
              React.createElement("dt", null, "Verwaltung"),
              React.createElement("dd", null, model.managed === 1 ? "Managed (App)" : isInstalled ? "In-Place (extern)" : "—"))),

          // variant chooser
          model.variants && React.createElement("div", { className: "md-sec" },
            React.createElement("div", { className: "md-sec-t" },
              "Variante wählen",
              React.createElement("span", { className: "md-sec-act" },
                React.createElement("span", { style: { fontSize: 11, color: "var(--text-3)" } },
                  VRAM_GB + " GB VRAM erkannt"))),
            React.createElement("div", { className: "md-var" },
              model.variants.map((v) =>
                React.createElement("div", { key: v.id, className: "md-var-row" + (selVariant === v.id ? " on" : ""), onClick: () => setSelVariant(v.id) },
                  React.createElement("span", { className: "md-var-radio" }),
                  React.createElement("div", { style: { flex: 1, minWidth: 0 } },
                    React.createElement("div", { className: "md-var-name" }, v.label, v.community && React.createElement("span", { style: { fontSize: 10, color: "var(--text-3)", fontFamily: "var(--font)", marginLeft: 4 } }, "(Community)")),
                    React.createElement("div", { className: "md-var-meta" }, v.size + " Disk · " + v.vram + " VRAM")),
                  v.rec ? React.createElement("span", { className: "md-var-rec" }, "Empfohlen") :
                  v.warn ? React.createElement("span", { className: "md-var-warn" }, React.createElement(Icon, { name: "alertTriangle", size: 12 }), " " + v.warn) : null)))),

          // component slots (in-place)
          hasComponents && React.createElement("div", { className: "md-sec" },
            React.createElement("div", { className: "md-sec-t" }, "Komponenten"),
            Object.entries(model.components).map(([key, c]) =>
              React.createElement("div", { key, className: "md-slot " + (c.ok ? "ok" : "miss") },
                React.createElement("div", { className: "md-slot-ico" },
                  React.createElement(Icon, { name: c.ok ? "check" : "alertTriangle", size: 16 })),
                React.createElement("div", { className: "md-slot-body" },
                  React.createElement("div", { className: "md-slot-name" }, c.label,
                    c.required && React.createElement("span", { style: { fontSize: 9.5, fontWeight: 700, letterSpacing: ".04em", textTransform: "uppercase", color: "var(--text-3)", marginLeft: 7 } }, "PFLICHT")),
                  React.createElement("div", { className: "md-slot-path " + (c.path ? "" : "miss") },
                    c.path || "Kein Pfad — bitte einbinden")),
                React.createElement("button", { className: "md-btn ghost sm", style: { marginLeft: "auto", flex: "none" }, onClick: () => onBind(model, key) },
                  React.createElement(Icon, { name: c.ok ? "pencil" : "folder", size: 14 }),
                  c.ok ? "Ändern" : "Wählen")))),

          // captioner settings link
          canConfigure && isActive && React.createElement("div", { className: "md-sec" },
            React.createElement("div", { className: "md-sec-t" }, "Caption-Einstellungen"),
            React.createElement("button", { className: "md-btn ghost", style: { width: "100%" }, onClick: () => onCaptionerSettings(model) },
              React.createElement(Icon, { name: "settings", size: 15 }),
              "Presets & Parameter konfigurieren …")),

        ), // end dr-body

        // footer
        React.createElement("div", { className: "md-dr-foot" },
          !isInstalled
            ? React.createElement(React.Fragment, null,
                React.createElement("button", { className: "md-btn primary", onClick: () => onDownload(model, selVariant) },
                  React.createElement(Icon, { name: "download", size: 16 }), "Herunterladen"),
                React.createElement("button", { className: "md-btn ghost", onClick: () => onBind(model, null) },
                  React.createElement(Icon, { name: "folder", size: 16 }), "Vorhandene Datei einbinden"))
            : React.createElement(React.Fragment, null,
                model.status === "incomplete"
                  ? React.createElement("button", { className: "md-btn warn", style: { flex: 1 }, onClick: () => onBind(model, null) },
                      React.createElement(Icon, { name: "folder", size: 16 }), "Fehlende Komponenten einbinden")
                  : React.createElement("button", { className: "md-btn ghost", style: { flex: 1 } },
                      React.createElement(Icon, { name: isActive ? "check" : "refresh", size: 16 }),
                      isActive ? "Aktiv" : "Laden"),
                React.createElement("button", { className: "md-btn danger md-btn icononly" },
                  React.createElement(Icon, { name: "trash", size: 16 }))))));
  }

  /* ============================================================
     MAIN PAGE
     ============================================================ */
  function Models({ onDownload, onBind, onCaptionerSettings }) {
    const [drawer, setDrawer] = useState(null);
    const [models, setModels] = useState(REGISTRY);
    const [modelsDir, setModelsDir] = useState("~/photofant/models");

    const openDrawer = (m) => setDrawer(m);
    const closeDrawer = () => setDrawer(null);

    const activeCount = models.filter((m) => ["active", "inplace"].includes(m.status)).length;
    const missingCore = models.filter((m) => m.tier === "core" && m.status === "missing").length;

    return React.createElement("div", { className: "grid-wrap" },

      // top heading
      React.createElement("div", { className: "month-head", style: { padding: "20px 22px 6px" } },
        React.createElement("h3", null, "Modelle"),
        React.createElement("span", { className: "m-count" }, models.length),
        React.createElement("div", { className: "m-line" }),
        React.createElement("span", { style: { fontSize: 12, color: "var(--text-3)" } },
          activeCount + " aktiv · " + (missingCore > 0 ? missingCore + " Core fehlen" : "Core vollständig"))),

      // system status bar
      React.createElement("div", { className: "md-sysbar" },
        React.createElement("div", { className: "md-sys" },
          React.createElement("div", { className: "md-sys-ico" }, React.createElement(Icon, { name: "cpu", size: 14 })),
          React.createElement("div", null,
            React.createElement("div", { className: "md-sys-k" }, "GPU"),
            React.createElement("div", { className: "md-sys-v" }, "NVIDIA RTX 4080 · " + VRAM_GB + " GB VRAM"))),
        React.createElement("div", { className: "md-sys" },
          React.createElement("div", { className: "md-sys-ico" }, React.createElement(Icon, { name: "folder", size: 14 })),
          React.createElement("div", null,
            React.createElement("div", { className: "md-sys-k" }, "Modell-Ordner"),
            React.createElement("div", { className: "md-sys-v path" }, modelsDir)),
          React.createElement("button", { className: "md-sys-edit", title: "Ordner ändern" }, React.createElement(Icon, { name: "pencil", size: 13 }))),
        React.createElement("div", { className: "md-sys-spacer" }),
        React.createElement("div", { className: "md-offline" }, "Offline · lokal")),

      // tier sections
      React.createElement("div", { className: "md-page" },
        TIERS.map((tier) => {
          const tierModels = models.filter((m) => m.tier === tier.id);
          return React.createElement("div", { key: tier.id, className: "md-tier" },
            React.createElement("div", { className: "md-tier-head" },
              React.createElement("h3", null, tier.label),
              React.createElement("span", { className: "md-tier-badge " + tier.badge }, tier.id),
              React.createElement("span", { className: "md-tier-desc" }, tier.desc),
              React.createElement("span", { className: "md-tier-agg" },
                tierModels.filter((m) => ["active", "inplace"].includes(m.status)).length + "/" + tierModels.length + " aktiv")),
            React.createElement("div", { className: "md-grid" },
              tierModels.map((m) => React.createElement(ModelCard, { key: m.id, model: m, onClick: openDrawer }))));
        })),

      // drawer
      drawer && React.createElement(Drawer, {
        model: drawer,
        onClose: closeDrawer,
        onDownload: (m, v) => { onDownload(m, v); closeDrawer(); },
        onBind: (m, slot) => { onBind(m, slot); },
        onCaptionerSettings: (m) => { onCaptionerSettings(m); },
      }));
  }

  window.Models = Models;
  window.MODEL_REGISTRY = REGISTRY;
})();
