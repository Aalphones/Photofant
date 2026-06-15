/* Photofant — Modell-Dialoge
   · DownloadDialog  — Variante, Lizenz, Begleitdateien, Zielordner
   · BindDialog      — In-Place einbinden (Einzeldatei / Ordner / Komponenten), Validierung
   · CaptionerDialog — Presets + modusabhängige Parameter (task_token / instruct / instruct_guided)
   → window.DownloadDialog, window.BindDialog, window.CaptionerDialog */
(function () {
  const { Icon } = window;
  const { useState, useEffect, useRef } = React;

  /* ---- shared ---- */
  function ScrimModal({ children, onClose, wide }) {
    useEffect(() => {
      const h = (e) => { if (e.key === "Escape") onClose(); };
      window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h);
    }, []);
    return React.createElement("div", { className: "big-scrim", style: { zIndex: 135 }, onClick: onClose },
      React.createElement("div", { className: "md-modal" + (wide ? " wide" : ""), onClick: (e) => e.stopPropagation() },
        children));
  }
  function ModalHead({ model, title, sub, onClose }) {
    return React.createElement("div", { className: "md-m-head" },
      React.createElement("div", { className: "md-ico role-" + model.role },
        React.createElement(Icon, { name: { face: "face", tagger: "tag", captioner: "text", search: "search", bg: "layers", upscale: "refresh", edit: "pencil" }[model.role] || "refresh", size: 19 })),
      React.createElement("div", { style: { flex: 1, minWidth: 0 } },
        React.createElement("div", { className: "md-m-title" }, title),
        React.createElement("div", { className: "md-m-sub" }, sub || model.name)),
      React.createElement("button", { className: "iconbtn", style: { width: 32, height: 32 }, onClick: onClose },
        React.createElement(Icon, { name: "x", size: 17 })));
  }
  function ModalFoot({ info, onCancel, onConfirm, confirmLabel, confirmDisabled, confirmWarn }) {
    return React.createElement("div", { className: "md-m-foot" },
      info && React.createElement("div", { className: "md-m-foot .md-foot-info", style: { fontSize: 11, color: "var(--text-3)", display: "flex", alignItems: "center", gap: 7 } },
        React.createElement(Icon, { name: "info", size: 13 }), info),
      React.createElement("div", { className: "md-foot-actions" },
        React.createElement("button", { className: "md-btn ghost", onClick: onCancel }, "Abbrechen"),
        React.createElement("button", { className: "md-btn " + (confirmWarn ? "warn" : "primary"), disabled: confirmDisabled, onClick: onConfirm },
          confirmLabel || "Bestätigen")));
  }

  /* ============================================================
     DOWNLOAD DIALOG
     ============================================================ */
  function DownloadDialog({ model, initialVariant, onConfirm, onClose }) {
    const [selVariant, setSelVariant] = useState(initialVariant || (model.variants ? model.variants[0].id : null));
    const [licAgreed, setLicAgreed] = useState(!model.licenseNC);
    const variant = model.variants ? model.variants.find((v) => v.id === selVariant) : null;
    const destDir = "~/photofant/models";
    const COMPANIONS = model.id === "flux2_klein"
      ? [{ name: "qwen3-text-encoder.safetensors", size: "~4.8 GB" }, { name: "ae.safetensors (VAE)", size: "168 MB" }]
      : model.id.startsWith("seedvr2") ? [{ name: "vae.safetensors", size: "500 MB" }] : [];

    const disabled = !licAgreed;

    return React.createElement(ScrimModal, { onClose, wide: model.variants != null },
      React.createElement(ModalHead, { model, title: "Herunterladen", sub: model.name, onClose }),
      React.createElement("div", { className: "md-m-body" },

        // variant chooser
        model.variants && React.createElement("div", { className: "md-fld" },
          React.createElement("div", { className: "md-fld-lbl" }, "Variante"),
          React.createElement("div", { className: "md-var" },
            model.variants.map((v) =>
              React.createElement("div", { key: v.id, className: "md-var-row" + (selVariant === v.id ? " on" : ""), onClick: () => setSelVariant(v.id) },
                React.createElement("span", { className: "md-var-radio" }),
                React.createElement("div", { style: { flex: 1, minWidth: 0 } },
                  React.createElement("div", { className: "md-var-name" }, v.label, v.community && React.createElement("span", { style: { fontSize: 10, color: "var(--text-3)", fontFamily: "var(--font)", marginLeft: 5 } }, "(Community)")),
                  React.createElement("div", { className: "md-var-meta" }, v.size + " · " + v.vram + " VRAM")),
                v.rec ? React.createElement("span", { className: "md-var-rec" }, "Empfohlen") :
                v.warn ? React.createElement("span", { className: "md-var-warn" }, React.createElement(Icon, { name: "alertTriangle", size: 12 }), " " + v.warn) : null)))),

        // companion files
        COMPANIONS.length > 0 && React.createElement("div", { className: "md-fld" },
          React.createElement("div", { className: "md-fld-lbl" }, "Begleitdateien — werden mitgeladen"),
          React.createElement("div", { className: "md-companions" },
            COMPANIONS.map((c, i) =>
              React.createElement("div", { key: i, className: "md-companion" },
                React.createElement(Icon, { name: "download", size: 14 }),
                React.createElement("span", null, c.name),
                React.createElement("span", { className: "cmp-sz" }, c.size))))),

        // target folder
        React.createElement("div", { className: "md-fld" },
          React.createElement("div", { className: "md-fld-lbl" }, "Zielordner"),
          React.createElement("div", { className: "md-target" },
            React.createElement(Icon, { name: "folder", size: 15 }),
            React.createElement("span", { className: "tgt-path" }, destDir + "/" + model.id + (selVariant ? "_" + selVariant : "")),
            React.createElement("button", { className: "md-btn ghost sm", style: { flex: "none" } }, React.createElement(Icon, { name: "pencil", size: 13 }), "Ändern"))),

        // license
        React.createElement("div", { className: "md-fld" },
          React.createElement("div", { className: "md-fld-lbl" }, "Lizenz"),
          React.createElement("div", { className: "md-license" + (model.licenseNC ? " nc" : "") + (licAgreed ? " on" : ""), onClick: () => setLicAgreed((l) => !l) },
            React.createElement("div", { className: "md-chk" }, licAgreed && React.createElement(Icon, { name: "check", size: 13 })),
            React.createElement("div", null,
              React.createElement("div", { className: "md-license-t" }, model.license),
              React.createElement("div", { className: "md-license-s" },
                model.licenseNC
                  ? React.createElement(React.Fragment, null, React.createElement("b", null, "Nur für nicht-kommerzielle Nutzung."), " Ich bestätige, dieses Modell ausschließlich privat zu verwenden.")
                  : "Ich habe die Lizenzbedingungen gelesen und akzeptiere sie.")))),

        model.licenseNC && !licAgreed && React.createElement("div", { className: "md-val warn" },
          React.createElement(Icon, { name: "shield", size: 14 }),
          "Bitte die Lizenzbedingungen bestätigen, bevor der Download gestartet werden kann.")),

      React.createElement(ModalFoot, {
        info: variant ? "~" + variant.size + " Download · Queue wird geöffnet" : null,
        onCancel: onClose, confirmDisabled: disabled, confirmWarn: false,
        onConfirm: () => { onConfirm(model, selVariant); onClose(); },
        confirmLabel: React.createElement(React.Fragment, null, React.createElement(Icon, { name: "download", size: 15 }), " Download starten"),
      }));
  }

  /* ============================================================
     BIND DIALOG  (In-Place einbinden)
     ============================================================ */
  const BIND_MODES = [
    { id: "file", label: "Einzeldatei", sub: "z.B. .safetensors, .gguf, .onnx", icon: "download" },
    { id: "folder", label: "Ordner", sub: "Diffusers-Layout, buffalo_l, WD14+CSV", icon: "folder" },
    { id: "components", label: "Komponenten", sub: "Flux: Diffusion + Text-Encoder + VAE einzeln", icon: "layers" },
  ];

  const VAL_SCENARIOS = {
    ok:         { type: "ok",   icon: "check",         msg: "Datei erkannt und validiert." },
    wrongFormat:{ type: "err",  icon: "x",             msg: "Falsches Format — erwartet: .safetensors (VAE). Gefunden: .ckpt. Bitte eine safetensors-VAE wählen.", detail: "Sha256: n/a · Magic-Bytes: 0x50 4B (ZIP/CKPT)" },
    wrongRole:  { type: "err",  icon: "x",             msg: "Diese Datei sieht aus wie ein Text-Encoder, gewählt wurde aber der VAE-Slot. Slot oder Datei korrigieren.", detail: "Rolle erkannt: text_encoder" },
    loading:    { type: "loading", icon: "refresh",    msg: "Validierung läuft …" },
    none:       null,
  };

  function PathRow({ label, format, required, path, valState, onPick, onClear }) {
    const vs = valState ? VAL_SCENARIOS[valState] : null;
    return React.createElement("div", { className: "md-bind-row" + (vs ? (" " + (vs.type === "err" ? "err" : vs.type === "ok" ? "ok" : "")) : "") },
      React.createElement("div", { className: "md-bind-top" },
        React.createElement("div", { style: { flex: 1, minWidth: 0 } },
          React.createElement("div", { className: "md-bind-slotname" }, label,
            required && React.createElement("span", { className: "md-bind-req" }, "Pflicht")),
          React.createElement("div", { className: "md-bind-fmt" }, "Format: " + format)),
        React.createElement("div", { className: "md-bind-pick" },
          React.createElement("button", { className: "md-btn ghost sm", onClick: onPick },
            React.createElement(Icon, { name: path ? "pencil" : "folder", size: 14 }), path ? "Ändern" : "Wählen"))),
      path && React.createElement("div", { className: "md-bind-path" },
        React.createElement(Icon, { name: "folder", size: 13 }),
        React.createElement("span", { style: { flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, path),
        React.createElement("button", { className: "bp-x", title: "Entfernen", onClick: onClear }, React.createElement(Icon, { name: "x", size: 13 }))),
      vs && React.createElement("div", { className: "md-val " + vs.type },
        vs.type === "loading"
          ? React.createElement("div", { className: "md-spin" })
          : React.createElement(Icon, { name: vs.icon, size: 14 }),
        React.createElement("div", null,
          React.createElement("div", null, vs.msg),
          vs.detail && React.createElement("div", { className: "md-val-detail" }, React.createElement("span", { style: { fontSize: 10 } }, "▶ " + vs.detail)))));
  }

  function BindDialog({ model, initialSlot, onConfirm, onClose }) {
    const hasComponents = !!model.components;
    const availModes = hasComponents
      ? BIND_MODES
      : model.format.toLowerCase().includes("ordner") || model.format.toLowerCase().includes("bundle")
        ? BIND_MODES.filter((m) => m.id !== "file")
        : BIND_MODES.filter((m) => m.id !== "folder" && m.id !== "components");
    const defaultMode = hasComponents ? "components" : model.format.toLowerCase().includes("bundle") ? "folder" : "file";
    const [mode, setMode] = useState(defaultMode);

    // file/folder single path
    const [singlePath, setSinglePath] = useState("");
    const [singleVal, setSingleVal] = useState("none");

    // component paths
    const initComp = () => {
      if (!model.components) return {};
      return Object.fromEntries(Object.entries(model.components).map(([k, c]) => [k, { path: c.path || "", val: c.ok ? "ok" : "none" }]));
    };
    const [compPaths, setCompPaths] = useState(initComp);

    const simulatePick = (key) => {
      const fakeFiles = {
        vae: "/mnt/models/flux2/ae.safetensors",
        diffusion: "/mnt/models/flux2/flux2-dev.safetensors",
        text_encoder: "/opt/comfyui/models/clip/qwen3.safetensors",
        single: "~/comfyui/models/unet/model.safetensors",
      };
      const p = fakeFiles[key] || fakeFiles.single;
      if (key === "single") { setSinglePath(p); setSingleVal("loading"); setTimeout(() => setSingleVal("ok"), 1400); }
      else setCompPaths((prev) => ({ ...prev, [key]: { path: p, val: "loading" } }));
      if (key !== "single") setTimeout(() => {
        setCompPaths((prev) => ({ ...prev, [key]: { ...prev[key], val: key === "vae" ? "ok" : "ok" } }));
      }, 1200 + Math.random() * 600);
    };

    const componentsDone = hasComponents && Object.entries(model.components)
      .filter(([, c]) => c.required)
      .every(([k]) => compPaths[k] && compPaths[k].val === "ok");
    const singleDone = !hasComponents && (mode !== "components") && singleVal === "ok";
    const canConfirm = componentsDone || singleDone;

    return React.createElement(ScrimModal, { onClose },
      React.createElement(ModalHead, { model, title: "Vorhandene Datei einbinden", sub: model.name, onClose }),
      React.createElement("div", { className: "md-m-body" },

        // mode selector
        React.createElement("div", { className: "md-fld" },
          React.createElement("div", { className: "md-fld-lbl" }, "Methode"),
          React.createElement("div", { className: "md-bind-modeseg" },
            availModes.map((m) =>
              React.createElement("button", { key: m.id, className: m.id === mode ? "on" : "", onClick: () => setMode(m.id) },
                React.createElement(Icon, { name: m.icon, size: 18 }),
                React.createElement("span", { className: "bm-t" }, m.label),
                React.createElement("span", { className: "bm-s" }, m.sub))))),

        // single file / folder
        (mode === "file" || mode === "folder") && React.createElement(PathRow, {
          label: mode === "folder" ? "Ordner wählen" : "Datei wählen",
          format: model.format, required: true,
          path: singlePath, valState: singlePath ? singleVal : null,
          onPick: () => simulatePick("single"),
          onClear: () => { setSinglePath(""); setSingleVal("none"); },
        }),

        // component pickers
        mode === "components" && hasComponents && React.createElement("div", null,
          Object.entries(model.components).map(([key, c]) =>
            React.createElement(PathRow, {
              key, label: c.label, format: c.format, required: c.required,
              path: compPaths[key]?.path || "", valState: compPaths[key]?.path ? compPaths[key].val : null,
              onPick: () => simulatePick(key),
              onClear: () => setCompPaths((prev) => ({ ...prev, [key]: { path: "", val: "none" } })),
            }))),

        // completeness warning
        hasComponents && !componentsDone && React.createElement("div", { className: "md-val warn", style: { marginTop: 10 } },
          React.createElement(Icon, { name: "alertTriangle", size: 14 }),
          React.createElement("div", null,
            React.createElement("b", null, model.name + " unvollständig"),
            " — alle Pflicht-Komponenten müssen erfolgreich validiert sein. Feature bleibt deaktiviert.")),

        canConfirm && React.createElement("div", { className: "md-val ok", style: { marginTop: 10 } },
          React.createElement(Icon, { name: "check", size: 14 }),
          React.createElement("div", null, "Alle Pfade validiert. Modell kann aktiviert werden."))),

      React.createElement(ModalFoot, {
        info: "Dateien werden weder kopiert noch verändert.",
        onCancel: onClose, confirmDisabled: !canConfirm,
        onConfirm: () => { onConfirm(model); onClose(); },
        confirmLabel: React.createElement(React.Fragment, null, React.createElement(Icon, { name: "check", size: 15 }), " Einbinden & aktivieren"),
      }));
  }

  /* ============================================================
     CAPTIONER SETTINGS DIALOG
     ============================================================ */
  function CaptionerDialog({ model, onClose }) {
    const caps = model.capabilities;
    const [activePreset, setActivePreset] = useState(
      caps.presets.find((p) => p.isDefault)?.id || caps.presets[0]?.id);
    const preset = caps.presets.find((p) => p.id === activePreset);
    const [config, setConfig] = useState(preset ? { ...preset.config } : {});
    const setC = (k, v) => setConfig((c) => ({ ...c, [k]: v }));

    const TASK_TOKENS = ["<CAPTION>", "<DETAILED_CAPTION>", "<MORE_DETAILED_CAPTION>"];
    const JOY_TYPES = ["Descriptive", "Straightforward", "Stable-Diffusion-Prompt", "Booru-Tag-Liste", "Art-Critic", "Product-Listing"];
    const JOY_LENGTHS = ["any", "very short", "short", "medium", "long", "very long"];
    const JOY_EXTRAS = ["Beleuchtung nennen", "Kamerawinkel angeben", "Wasserzeichen erwähnen", "NSFW-Kontext ignorieren"];

    return React.createElement(ScrimModal, { onClose, wide: true },
      React.createElement(ModalHead, { model, title: "Caption-Einstellungen", sub: model.name + " · " + caps.mode, onClose }),
      React.createElement("div", { className: "md-m-body" },

        // presets
        React.createElement("div", { className: "md-fld" },
          React.createElement("div", { className: "md-fld-lbl" }, "Presets"),
          caps.presets.map((p) =>
            React.createElement("div", { key: p.id, className: "md-preset-row" + (activePreset === p.id ? " on" : ""), onClick: () => { setActivePreset(p.id); setConfig({ ...p.config }); } },
              React.createElement("span", { className: "md-preset-radio" }),
              React.createElement("div", { style: { flex: 1, minWidth: 0 } },
                React.createElement("div", { className: "md-preset-name" }, p.name),
                React.createElement("div", { className: "md-preset-sub" }, "caption_preset_id: " + p.id)),
              p.isDefault && React.createElement("span", { className: "md-preset-def" }, "Standard")))),

        // mode note
        React.createElement("div", { className: "md-fld" },
          React.createElement("div", { className: "md-fld-lbl" }, "Modus", React.createElement("span", { className: "md-modetag", style: { marginLeft: 6 } }, caps.mode))),

        // ---- task_token (Florence-2) ----
        caps.mode === "task_token" && React.createElement(React.Fragment, null,
          React.createElement("div", { className: "md-val ok", style: { marginBottom: 16 } },
            React.createElement(Icon, { name: "info", size: 14 }),
            React.createElement("div", null, "Florence-2 folgt keinen freien Anweisungen. Stil und Länge steuerst du ausschließlich über das Task-Token — kein System-Prompt-Feld.")),
          React.createElement("div", { className: "md-control" },
            React.createElement("div", { className: "md-control-lbl" }, "Task-Token"),
            React.createElement("div", { className: "md-control-hint" }, "Steuert Ausführlichkeit: CAPTION = ein Satz, DETAILED = mehrere Sätze, MORE_DETAILED = ausführlich."),
            React.createElement("div", { className: "md-seg" },
              TASK_TOKENS.map((t) =>
                React.createElement("button", { key: t, className: config.task_token === t ? "on" : "", onClick: () => setC("task_token", t) }, t)))),
          React.createElement("div", { className: "md-control" },
            React.createElement("div", { className: "md-control-lbl" }, "max_new_tokens"),
            React.createElement("div", { className: "md-slider-row" },
              React.createElement("input", { type: "range", min: 128, max: 4096, step: 128, value: config.max_new_tokens || 1024, onChange: (e) => setC("max_new_tokens", +e.target.value) }),
              React.createElement("span", { className: "md-slider-val" }, config.max_new_tokens || 1024))),
          React.createElement("div", { className: "md-control" },
            React.createElement("div", { className: "md-control-lbl" }, "num_beams (Beam-Search-Breite)"),
            React.createElement("div", { className: "md-slider-row" },
              React.createElement("input", { type: "range", min: 1, max: 8, step: 1, value: config.num_beams || 3, onChange: (e) => setC("num_beams", +e.target.value) }),
              React.createElement("span", { className: "md-slider-val" }, config.num_beams || 3)))),

        // ---- instruct (Qwen) ----
        caps.mode === "instruct" && React.createElement(React.Fragment, null,
          React.createElement("div", { className: "md-val ok", style: { marginBottom: 16 } },
            React.createElement(Icon, { name: "info", size: 14 }),
            React.createElement("div", null, "Qwen2.5-VL folgt dem System-Prompt — Stil und Format ergeben sich daraus. Für echte Booru-Tags ist WD14 das bessere Werkzeug.")),
          React.createElement("div", { className: "md-control" },
            React.createElement("div", { className: "md-control-lbl" }, "System-Prompt"),
            React.createElement("textarea", { className: "md-textarea", rows: 5, value: config.system_prompt || "", onChange: (e) => setC("system_prompt", e.target.value) })),
          React.createElement("div", { className: "md-control" },
            React.createElement("div", { className: "md-control-lbl" }, "User-Prompt"),
            React.createElement("input", { className: "md-textarea", style: { resize: "none" }, value: config.user_prompt || "", onChange: (e) => setC("user_prompt", e.target.value) })),
          React.createElement("div", { className: "md-control" },
            React.createElement("div", { className: "md-control-lbl" }, "temperature"),
            React.createElement("div", { className: "md-slider-row" },
              React.createElement("input", { type: "range", min: 0, max: 1.5, step: 0.05, value: config.temperature ?? 0.7, onChange: (e) => setC("temperature", +e.target.value) }),
              React.createElement("span", { className: "md-slider-val" }, (config.temperature ?? 0.7).toFixed(2)))),
          React.createElement("div", { className: "md-control" },
            React.createElement("div", { className: "md-control-lbl" }, "max_new_tokens"),
            React.createElement("div", { className: "md-slider-row" },
              React.createElement("input", { type: "range", min: 64, max: 2048, step: 64, value: config.max_new_tokens || 512, onChange: (e) => setC("max_new_tokens", +e.target.value) }),
              React.createElement("span", { className: "md-slider-val" }, config.max_new_tokens || 512)))),

        // ---- instruct_guided (JoyCaption) ----
        caps.mode === "instruct_guided" && React.createElement(React.Fragment, null,
          React.createElement("div", { className: "md-val ok", style: { marginBottom: 16 } },
            React.createElement(Icon, { name: "info", size: 14 }),
            React.createElement("div", null, "JoyCaption baut den Prompt aus Bausteinen. Ein Raw-Override ist nur im Advanced-Bereich nötig.")),
          React.createElement("div", { className: "md-control" },
            React.createElement("div", { className: "md-control-lbl" }, "Caption-Typ"),
            React.createElement("div", { className: "md-buildchips" },
              JOY_TYPES.map((t) =>
                React.createElement("button", { key: t, className: "md-buildchip" + (config.caption_type === t ? " on" : ""), onClick: () => setC("caption_type", t) },
                  config.caption_type === t && React.createElement(Icon, { name: "check", size: 12 }), t)))),
          React.createElement("div", { className: "md-control" },
            React.createElement("div", { className: "md-control-lbl" }, "Länge"),
            React.createElement("div", { className: "md-seg" },
              JOY_LENGTHS.map((l) =>
                React.createElement("button", { key: l, className: config.length === l ? "on" : "", onClick: () => setC("length", l) }, l)))),
          React.createElement("div", { className: "md-control" },
            React.createElement("div", { className: "md-control-lbl" }, "Zusätzliche Angaben"),
            React.createElement("div", { className: "md-buildchips" },
              JOY_EXTRAS.map((x) => {
                const on = (config.extras || []).includes(x);
                return React.createElement("button", { key: x, className: "md-buildchip" + (on ? " on" : ""), onClick: () => setC("extras", on ? (config.extras || []).filter((e) => e !== x) : [...(config.extras || []), x]) },
                  on && React.createElement(Icon, { name: "check", size: 12 }), x);
              }))))),

      React.createElement("div", { className: "md-m-foot" },
        React.createElement("div", { className: "md-foot-actions", style: { width: "100%" } },
          React.createElement("button", { className: "md-btn ghost", onClick: onClose }, "Schließen"),
          React.createElement("button", { className: "md-btn primary", onClick: onClose },
            React.createElement(Icon, { name: "check", size: 15 }), "Preset speichern"))));
  }

  window.DownloadDialog = DownloadDialog;
  window.BindDialog = BindDialog;
  window.CaptionerDialog = CaptionerDialog;
})();
