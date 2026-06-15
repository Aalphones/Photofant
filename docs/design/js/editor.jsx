/* Photofant — Editor (main component)
   Editor, TopBar, CanvasArea (crop overlay + inpaint canvas), HistoryPanel, SaveModal
   → window.Editor */
(function () {
  const { Icon } = window;
  const { Img, Avatar } = window.UI;
  const { BasisPanel, UpscalePanel, Flux2Panel, InpaintPanel } = window.EditorTools;
  const { useState, useEffect, useRef, useCallback } = React;

  const TOOLS = [
    { id: "basis",   icon: "crop",     label: "Basis" },
    { id: "upscale", icon: "expand2",  label: "Upscale" },
    { id: "flux2",   icon: "pencil",   label: "Flux2" },
    { id: "inpaint", icon: "brush",    label: "Inpaint" },
  ];

  const ZOOM_LEVELS = [0.25, 0.33, 0.5, 0.67, 0.75, 1, 1.25, 1.5, 2, 3];

  /* ---- step badge colours ---- */
  const BADGE_CLS = { orig: "orig", basis: "basis", upscale: "upscale", flux: "flux", inpaint: "inpaint" };

  /* ============================================================
     CROP OVERLAY
     ============================================================ */
  function CropOverlay({ crop, onCropChange }) {
    const dragging = useRef(null);
    const containerRef = useRef(null);

    const ptPct = (e, rect) => ({
      x: Math.max(0, Math.min(100, (e.clientX - rect.left) / rect.width * 100)),
      y: Math.max(0, Math.min(100, (e.clientY - rect.top) / rect.height * 100)),
    });

    const onPD = useCallback((e, handle) => {
      e.preventDefault(); e.stopPropagation();
      const rect = containerRef.current.getBoundingClientRect();
      dragging.current = { handle, startX: e.clientX, startY: e.clientY, startCrop: { ...crop }, rect };
      const onPM = (me) => {
        if (!dragging.current) return;
        const { handle, startX, startY, startCrop, rect } = dragging.current;
        const dx = (me.clientX - startX) / rect.width * 100;
        const dy = (me.clientY - startY) / rect.height * 100;
        let { x, y, w, h } = startCrop;
        if (handle === "body") { x += dx; y += dy; }
        else if (handle === "nw") { x += dx; y += dy; w -= dx; h -= dy; }
        else if (handle === "ne") { y += dy; w += dx; h -= dy; }
        else if (handle === "sw") { x += dx; w -= dx; h += dy; }
        else if (handle === "se") { w += dx; h += dy; }
        else if (handle === "n") { y += dy; h -= dy; }
        else if (handle === "s") { h += dy; }
        else if (handle === "w") { x += dx; w -= dx; }
        else if (handle === "e") { w += dx; }
        w = Math.max(8, w); h = Math.max(8, h);
        x = Math.max(0, Math.min(x, 100 - w)); y = Math.max(0, Math.min(y, 100 - h));
        w = Math.min(w, 100 - x); h = Math.min(h, 100 - y);
        onCropChange({ x, y, w, h });
      };
      const onPU = () => { dragging.current = null; window.removeEventListener("pointermove", onPM); window.removeEventListener("pointerup", onPU); };
      window.addEventListener("pointermove", onPM);
      window.addEventListener("pointerup", onPU);
    }, [crop, onCropChange]);

    const { x, y, w, h } = crop;
    const handles = [
      { id: "nw", style: { left: x + "%", top: y + "%", transform: "translate(-50%, -50%)", cursor: "nwse-resize" } },
      { id: "ne", style: { left: (x + w) + "%", top: y + "%", transform: "translate(-50%, -50%)", cursor: "nesw-resize" } },
      { id: "sw", style: { left: x + "%", top: (y + h) + "%", transform: "translate(-50%, -50%)", cursor: "nesw-resize" } },
      { id: "se", style: { left: (x + w) + "%", top: (y + h) + "%", transform: "translate(-50%, -50%)", cursor: "nwse-resize" } },
      { id: "n",  style: { left: (x + w / 2) + "%", top: y + "%", transform: "translate(-50%, -50%)", cursor: "ns-resize" } },
      { id: "s",  style: { left: (x + w / 2) + "%", top: (y + h) + "%", transform: "translate(-50%, -50%)", cursor: "ns-resize" } },
      { id: "w",  style: { left: x + "%", top: (y + h / 2) + "%", transform: "translate(-50%, -50%)", cursor: "ew-resize" } },
      { id: "e",  style: { left: (x + w) + "%", top: (y + h / 2) + "%", transform: "translate(-50%, -50%)", cursor: "ew-resize" } },
    ];

    return React.createElement("div", { ref: containerRef, className: "ed-crop-overlay",
      onPointerDown: (e) => { e.preventDefault(); },
    },
      // shades: top, bottom, left, right
      React.createElement("div", { className: "ed-crop-shade", style: { top: 0, left: 0, right: 0, height: y + "%" }, onPointerDown: (e) => onPD(e, "body") }),
      React.createElement("div", { className: "ed-crop-shade", style: { bottom: 0, left: 0, right: 0, height: (100 - y - h) + "%" }, onPointerDown: (e) => onPD(e, "body") }),
      React.createElement("div", { className: "ed-crop-shade", style: { top: y + "%", height: h + "%", left: 0, width: x + "%" }, onPointerDown: (e) => onPD(e, "body") }),
      React.createElement("div", { className: "ed-crop-shade", style: { top: y + "%", height: h + "%", right: 0, width: (100 - x - w) + "%" }, onPointerDown: (e) => onPD(e, "body") }),
      // crop box (move body)
      React.createElement("div", { className: "ed-crop-box", style: { left: x + "%", top: y + "%", width: w + "%", height: h + "%", cursor: "move" }, onPointerDown: (e) => onPD(e, "body") },
        React.createElement("div", { className: "ed-crop-border" }),
        React.createElement("div", { className: "ed-crop-thirds" })),
      // handles
      handles.map((hd) =>
        React.createElement("div", { key: hd.id, className: "ed-crop-handle", style: { ...hd.style, position: "absolute" }, onPointerDown: (e) => onPD(e, hd.id) })));
  }

  /* ============================================================
     INPAINT MASK CANVAS
     ============================================================ */
  function InpaintCanvas({ brushSize, erasing, onMaskChange, clearTrigger }) {
    const canvasRef = useRef(null);
    const isDrawing = useRef(false);
    const lastPos = useRef(null);
    const brushRingRef = useRef(null);

    useEffect(() => {
      if (canvasRef.current) {
        const ctx = canvasRef.current.getContext("2d");
        ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
        onMaskChange(false);
      }
    }, [clearTrigger]);

    const resize = () => {
      if (!canvasRef.current) return;
      const parent = canvasRef.current.parentElement;
      const { width, height } = parent.getBoundingClientRect();
      // preserve existing drawing
      const tmp = document.createElement("canvas");
      tmp.width = canvasRef.current.width; tmp.height = canvasRef.current.height;
      tmp.getContext("2d").drawImage(canvasRef.current, 0, 0);
      canvasRef.current.width = width * window.devicePixelRatio;
      canvasRef.current.height = height * window.devicePixelRatio;
      canvasRef.current.getContext("2d").drawImage(tmp, 0, 0, canvasRef.current.width, canvasRef.current.height);
    };
    useEffect(() => { resize(); window.addEventListener("resize", resize); return () => window.removeEventListener("resize", resize); }, []);

    const getPos = (e) => {
      const rect = canvasRef.current.getBoundingClientRect();
      const src = e.touches ? e.touches[0] : e;
      return {
        x: (src.clientX - rect.left) * (canvasRef.current.width / rect.width),
        y: (src.clientY - rect.top) * (canvasRef.current.height / rect.height),
        cx: src.clientX, cy: src.clientY,
      };
    };

    const paintAt = (x, y, from) => {
      const ctx = canvasRef.current.getContext("2d");
      const r = brushSize / 2 * window.devicePixelRatio;
      ctx.globalCompositeOperation = erasing ? "destination-out" : "source-over";
      ctx.fillStyle = "rgba(239, 68, 68, 0.55)";
      ctx.beginPath();
      if (from) { ctx.moveTo(from.x, from.y); }
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    };

    const startDraw = (e) => {
      e.preventDefault();
      isDrawing.current = true;
      const pos = getPos(e);
      lastPos.current = pos;
      paintAt(pos.x, pos.y, null);
      onMaskChange(true);
    };
    const draw = (e) => {
      e.preventDefault();
      if (!isDrawing.current) return;
      const pos = getPos(e);
      paintAt(pos.x, pos.y, lastPos.current);
      lastPos.current = pos;
      if (brushRingRef.current) { brushRingRef.current.style.left = pos.cx + "px"; brushRingRef.current.style.top = pos.cy + "px"; }
    };
    const stopDraw = () => { isDrawing.current = false; lastPos.current = null; };
    const moveCursor = (e) => {
      if (!brushRingRef.current) return;
      brushRingRef.current.style.display = "block";
      brushRingRef.current.style.left = e.clientX + "px";
      brushRingRef.current.style.top = e.clientY + "px";
      brushRingRef.current.style.width = brushSize + "px";
      brushRingRef.current.style.height = brushSize + "px";
    };

    return React.createElement(React.Fragment, null,
      React.createElement("canvas", { ref: canvasRef, className: "ed-mask-canvas",
        onMouseDown: startDraw, onMouseMove: (e) => { draw(e); moveCursor(e); },
        onMouseUp: stopDraw, onMouseLeave: (e) => { stopDraw(); if (brushRingRef.current) brushRingRef.current.style.display = "none"; },
        onMouseEnter: moveCursor,
        onTouchStart: startDraw, onTouchMove: draw, onTouchEnd: stopDraw,
      }),
      React.createElement("div", { ref: brushRingRef, className: "ed-brush-ring", style: { display: "none", width: brushSize, height: brushSize } }));
  }

  /* ============================================================
     CANVAS AREA
     ============================================================ */
  function CanvasArea({ asset, tool, zoom, crop, onCropChange, brushSize, erasing, clearMaskTrigger, onMaskChange, generating, genInfo }) {
    const maxH = "calc(100vh - 52px - 64px)";
    const imgStyle = { maxHeight: maxH, maxWidth: "100%", transform: "scale(" + zoom + ")", transformOrigin: "center center", display: "block" };

    return React.createElement("div", { className: "ed-canvas-wrap" },
      React.createElement("div", { className: "ed-canvas-container" },
        React.createElement("img", { className: "ed-canvas-img", src: asset.photo, alt: "", style: imgStyle,
          onError: (e) => { e.target.style.background = asset.bg || "var(--surface)"; } }),
        tool === "basis" && React.createElement(CropOverlay, { crop, onCropChange }),
        (tool === "inpaint") && React.createElement(InpaintCanvas, { brushSize, erasing, onMaskChange, clearTrigger: clearMaskTrigger }),
        generating && React.createElement("div", { className: "ed-generating" },
          React.createElement("div", { className: "ed-gen-ring" }),
          React.createElement("div", { className: "ed-gen-label" }, genInfo.label),
          React.createElement("div", { className: "ed-gen-sub" }, genInfo.sub),
          React.createElement("div", { className: "ed-gen-prog" },
            React.createElement("div", { className: "gp-bar" }, React.createElement("i", { style: { width: genInfo.pct + "%" } })),
            React.createElement("div", { className: "gp-pct" }, Math.round(genInfo.pct) + " %")))),
      React.createElement("div", { className: "ed-canvas-info" },
        asset.w + " × " + asset.h + " px", " · ",
        Math.round(zoom * 100) + " %", " · ",
        asset.format || "JPEG"));
  }

  /* ============================================================
     HISTORY PANEL
     ============================================================ */
  function HistoryPanel({ steps, current, onRollback, open, isMobile }) {
    return React.createElement("div", { className: "ed-right" + (open ? (isMobile ? " mobile-open" : "") : " closed") },
      React.createElement("div", { className: "ed-hist-head" },
        React.createElement("h4", null, "Verlauf"),
        React.createElement("div", { className: "ed-hist-actions" },
          React.createElement("button", { className: "iconbtn", style: { width: 28, height: 28 }, title: "Alle Steps", onClick: () => {} }, React.createElement(Icon, { name: "layers", size: 15 }))),
      React.createElement("div", { className: "ed-steps" },
        [...steps].reverse().map((step, ri) => {
          const idx = steps.length - 1 - ri;
          const isCurrent = idx === current;
          return React.createElement("div", { key: step.id, className: "ed-step" + (isCurrent ? " on" : ""), onClick: () => onRollback(idx) },
            React.createElement("div", { className: "ed-step-thumb" }, React.createElement(Img, { src: step.photo, bg: step.bg })),
            React.createElement("div", { style: { flex: 1, minWidth: 0 } },
              React.createElement("div", { className: "ed-step-op" }, step.label),
              React.createElement("div", { className: "ed-step-meta" }, "Step " + (idx + 1) + "/" + steps.length),
              React.createElement("div", null, React.createElement("span", { className: "ed-step-badge " + (step.badge || "orig") }, step.badge || "original"))),
            !isCurrent && React.createElement("button", { className: "ed-rollback", onClick: (e) => { e.stopPropagation(); onRollback(idx); } }, "Rollback"));
        }))));
  }

  /* ============================================================
     SAVE MODAL
     ============================================================ */
  function SaveModal({ onClose, onSave, steps, current }) {
    const [saveMode, setSaveMode] = useState("overwrite");
    return React.createElement("div", { className: "ed-save-scrim", onClick: onClose },
      React.createElement("div", { className: "ed-save-modal", onClick: (e) => e.stopPropagation() },
        React.createElement("div", { className: "ed-save-head" },
          React.createElement("div", { className: "sh-ico" }, React.createElement(Icon, { name: "download", size: 18 })),
          React.createElement("div", null,
            React.createElement("h3", null, "Bearbeitung speichern"),
            React.createElement("p", null, steps.length - 1 + " Step" + (steps.length - 1 === 1 ? "" : "s") + " \u00b7 " + (steps[current] || steps[steps.length-1]).label))),
        React.createElement("div", { className: "ed-save-opts" },
          React.createElement("div", { className: "ed-save-opt" + (saveMode === "overwrite" ? " on" : ""), onClick: () => setSaveMode("overwrite") },
            React.createElement("span", { className: "ed-save-radio" }),
            React.createElement("div", null,
              React.createElement("div", { className: "ed-save-opt-t" }, "\u00dcberschreiben"),
              React.createElement("div", { className: "ed-save-opt-s" }, "Ersetzt den aktuellen Edit in personX/edits/. Der Vorschritt bleibt in der History der Cache-DB erhalten."))),
          React.createElement("div", { className: "ed-save-opt" + (saveMode === "copy" ? " on" : ""), onClick: () => setSaveMode("copy") },
            React.createElement("span", { className: "ed-save-radio" }),
            React.createElement("div", null,
              React.createElement("div", { className: "ed-save-opt-t" }, "Als neue Kopie"),
              React.createElement("div", { className: "ed-save-opt-s" }, "Legt eine neue Version in personX/edits/ an \u2014 der bestehende Edit bleibt unber\u00fchrt.")))),
        React.createElement("div", { className: "ed-save-foot" },
          React.createElement("button", { className: "ed-save-cancel", onClick: onClose }, "Abbrechen"),
          React.createElement("button", { className: "ed-save-ok", onClick: () => { onSave(saveMode); onClose(); } },
            React.createElement(Icon, { name: "download", size: 15 }), saveMode === "overwrite" ? "\u00dcberschreiben" : "Als Kopie speichern"))));
  }

  /* ============================================================
     MAIN EDITOR
     ============================================================ */
  function Editor({ asset, onBack, pushJobs }) {
    const [tool, setTool] = useState("basis");
    const [histOpen, setHistOpen] = useState(true);
    const [mobilePanel, setMobilePanel] = useState(null); // "tools" | "history" | null
    const [zoomIdx, setZoomIdx] = useState(5); // 1.0
    const [crop, setCrop] = useState({ x: 10, y: 10, w: 80, h: 80 });
    const [steps, setSteps] = useState([{ id: 0, label: "Original", badge: "orig", photo: asset.photo, bg: asset.bg }]);
    const [current, setCurrent] = useState(0);
    const [generating, setGenerating] = useState(false);
    const [genInfo, setGenInfo] = useState({ label: "", sub: "", pct: 0 });
    const [saveModal, setSaveModal] = useState(false);
    const [brushSize, setBrushSize] = useState(40);
    const [erasing, setErasing] = useState(false);
    const [clearMaskTrigger, setClearMaskTrigger] = useState(0);
    const [hasMask, setHasMask] = useState(false);
    const [inpaintPrompt, setInpaintPrompt] = useState("");
    const genTimerRef = useRef(null);
    const isMobile = window.innerWidth <= 860;

    const zoom = ZOOM_LEVELS[zoomIdx];

    // apply a synchronous (non-generative) operation
    const applyOp = (op) => {
      const newStep = { id: steps.length, ...op, photo: asset.photo, bg: asset.bg };
      setSteps((prev) => [...prev.slice(0, current + 1), newStep]);
      setCurrent(current + 1);
    };

    // start a generative operation (shows progress overlay)
    const startGenerate = (op) => {
      setGenerating(true);
      let pct = 0;
      setGenInfo({ label: op.genLabel, sub: op.genSub, pct: 0 });
      genTimerRef.current = setInterval(() => {
        pct += Math.random() * 7 + 3;
        if (pct >= 100) {
          pct = 100;
          clearInterval(genTimerRef.current);
          setGenerating(false);
          const newStep = { id: steps.length, ...op, photo: asset.photo, bg: asset.bg };
          setSteps((prev) => [...prev.slice(0, current + 1), newStep]);
          setCurrent((c) => c + 1);
          if (op.op === "inpaint") { setClearMaskTrigger((t) => t + 1); setHasMask(false); }
        }
        setGenInfo((g) => ({ ...g, pct: Math.min(Math.round(pct), 100) }));
      }, 180);
    };

    const rollback = (idx) => { setCurrent(idx); };

    const handleSave = (mode) => {
      if (pushJobs) pushJobs([{ kind: "tag", name: mode === "overwrite" ? "Edit speichern (überschreiben)" : "Edit speichern (neue Kopie)", sub: steps[current].label, pct: 0, done: false }]);
    };

    const zoomIn = () => setZoomIdx((i) => Math.min(ZOOM_LEVELS.length - 1, i + 1));
    const zoomOut = () => setZoomIdx((i) => Math.max(0, i - 1));
    const zoomFit = () => setZoomIdx(5);

    // keyboard shortcuts
    useEffect(() => {
      const h = (e) => {
        if (e.key === "Escape") { if (saveModal) setSaveModal(false); else onBack(); }
        if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); setSaveModal(true); }
        if ((e.metaKey || e.ctrlKey) && e.key === "z") { e.preventDefault(); rollback(Math.max(0, current - 1)); }
      };
      window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h);
    }, [saveModal, current]);

    const personName = asset.personId >= 0 ? (window.PF ? window.PF.personName(asset.personId) : "") : "";

    return React.createElement("div", { className: "ed-page" },

      // top bar
      React.createElement("div", { className: "ed-topbar" },
        React.createElement("button", { className: "ed-back", onClick: onBack },
          React.createElement(Icon, { name: "chevronDown", size: 16, style: { transform: "rotate(90deg)" } }), "Galerie"),
        React.createElement("div", { className: "ed-info" },
          React.createElement("span", { className: "ed-img-name" }, "#" + asset.id),
          personName && React.createElement("div", { className: "ctx-chip", style: { padding: "0 10px 0 4px" } },
            React.createElement("div", { className: "cc-thumb" },
              window.UI && React.createElement(window.UI.Avatar, { personId: asset.personId, size: 22, ring: false })),
            personName)),
        React.createElement("div", { className: "ed-topbar-right" },
          React.createElement("div", { className: "ed-zoom-ctrl" },
            React.createElement("button", { className: "zb", title: "Verkleinern", onClick: zoomOut }, React.createElement(Icon, { name: "zoomOut", size: 16 })),
            React.createElement("span", { className: "zv", title: "Fit (1:1)", onClick: zoomFit }, Math.round(zoom * 100) + " %"),
            React.createElement("button", { className: "zb", title: "Vergr\u00f6\u00dfern", onClick: zoomIn }, React.createElement(Icon, { name: "zoomIn", size: 16 }))),
          React.createElement("div", { className: "ed-top-sep" }),
          React.createElement("button", { className: "ed-hist-toggle" + (histOpen ? " on" : ""), onClick: () => setHistOpen((o) => !o) },
            React.createElement(Icon, { name: "layers", size: 15 }),
            React.createElement("span", null, "Verlauf"),
            steps.length > 1 && React.createElement("span", { className: "ed-hist-count" }, steps.length - 1)),
          React.createElement("button", { className: "ed-save-btn", onClick: () => setSaveModal(true) },
            React.createElement(Icon, { name: "download", size: 16 }), "Speichern"))),

      // body
      React.createElement("div", { className: "ed-body" },

        // left tool panel
        React.createElement("div", { className: "ed-left" + (isMobile ? (mobilePanel === "tools" ? " mobile-open" : "") : "") },
          React.createElement("div", { className: "ed-tool-tabs" },
            TOOLS.map((t) => React.createElement("div", { key: t.id, className: "ed-tool-tab" + (tool === t.id ? " on" : ""), onClick: () => { setTool(t.id); if (isMobile) setMobilePanel("tools"); } },
              React.createElement(Icon, { name: t.icon, size: 18 }), t.label))),
          tool === "basis" && React.createElement(BasisPanel, { asset, onApply: applyOp }),
          tool === "upscale" && React.createElement(UpscalePanel, { asset, generating, onGenerate: startGenerate }),
          tool === "flux2" && React.createElement(Flux2Panel, { asset: { ...asset, personName }, generating, onGenerate: startGenerate }),
          tool === "inpaint" && React.createElement(InpaintPanel, { brushSize, setBrushSize, erasing, setErasing, onClearMask: () => { setClearMaskTrigger((t) => t + 1); setHasMask(false); }, generating, hasMask, onGenerate: startGenerate, prompt: inpaintPrompt, setPrompt: setInpaintPrompt })),

        // canvas
        React.createElement(CanvasArea, { asset, tool, zoom, crop, onCropChange: setCrop, brushSize, erasing, clearMaskTrigger, onMaskChange: setHasMask, generating, genInfo }),

        // right history
        React.createElement(HistoryPanel, { steps, current, onRollback: rollback, open: histOpen, isMobile: isMobile && mobilePanel === "history" }),

        // mobile bottom bar
        React.createElement("div", { className: "ed-mobile-bar" },
          React.createElement("button", { className: "mb-tool" + (mobilePanel === "tools" ? " on" : ""), onClick: () => setMobilePanel((p) => p === "tools" ? null : "tools") },
            React.createElement(Icon, { name: TOOLS.find((t) => t.id === tool)?.icon || "crop", size: 20 }),
            TOOLS.find((t) => t.id === tool)?.label || "Werkzeug"),
          React.createElement("div", { className: "mb-sep" }),
          React.createElement("button", { className: "mb-tool" + (mobilePanel === "history" ? " on" : ""), onClick: () => setMobilePanel((p) => p === "history" ? null : "history") },
            React.createElement(Icon, { name: "layers", size: 20 }),
            "Verlauf"),
          React.createElement("div", { className: "mb-sep" }),
          React.createElement("button", { className: "mb-tool", style: { color: "var(--accent)", flex: "none", width: 80 }, onClick: () => setSaveModal(true) },
            React.createElement(Icon, { name: "download", size: 20 }),
            "Speichern"))),

      // scrim for mobile panels
      mobilePanel && isMobile && React.createElement("div", { onClick: () => setMobilePanel(null), style: { position: "absolute", inset: 0, zIndex: 70, background: "oklch(0.08 0.005 256 / .5)" } }),

      // save modal
      saveModal && React.createElement(SaveModal, { onClose: () => setSaveModal(false), onSave: handleSave, steps, current }));
  }

  window.Editor = Editor;
})();
