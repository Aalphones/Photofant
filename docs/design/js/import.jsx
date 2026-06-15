/* Photofant — Import-Dialog (zweispaltig, Einzel + Bulk, kontextabhängig).
   Wird per Drag&Drop oder Klick aus Top-Bar / Personen-Ordner / Lightbox geöffnet
   und belegt Metadaten je nach View automatisch vor.  → window.ImportDialog */
(function () {
  const { Icon, PF } = window;
  const { Img, Avatar } = window.UI;
  const { useState, useMemo, useRef, useEffect } = React;

  const SOURCES = [
    { id: "original", label: "Original", sw: "oklch(0.55 0.02 256)" },
    { id: "sdxl", label: "SDXL", sw: "oklch(0.52 0.13 200)" },
    { id: "flux", label: "Flux", sw: "oklch(0.55 0.16 285)" },
  ];

  let _fid = 0;
  const sampleNames = ["IMG_4821", "DSC09173", "shoot_final_v3", "render_0042", "portrait_edit", "upscaled_2x", "flux_out_88", "session_07"];
  function makeSample() {
    _fid++;
    const w = [768, 896, 1024, 1024, 1280][_fid % 5];
    const h = Math.round(w * [1.25, 1, 1.33, 1.25][_fid % 4]);
    const seed = "imp" + _fid + "_" + Math.floor(Math.random() * 9999);
    const name = sampleNames[_fid % sampleNames.length] + (_fid > sampleNames.length ? "_" + _fid : "");
    return {
      id: "f" + _fid + "_" + Date.now(), name: name + ".jpg",
      sizeKB: Math.round((w * h) / 7 / 1024 * 100) / 100 * 1024 / 1000,
      w, h, photo: PF.picsum(seed, Math.round(w / 2), Math.round(h / 2)), bg: "var(--surface)",
    };
  }

  function ImportDialog({ assets, context, onClose, onSubmit }) {
    const ctx = context || { source: "top" };

    // ---- files ----
    const [files, setFiles] = useState(() => [makeSample(), makeSample(), makeSample()]);
    const [scope, setScope] = useState("all");      // "all" | fileId
    const [dragging, setDragging] = useState(false);
    const dragDepth = useRef(0);
    const inputRef = useRef(null);

    // ---- shared + per-file metadata ----
    const initRel = ctx.source === "relation" && ctx.relAssetId != null
      ? { assetId: ctx.relAssetId, dir: ctx.role === "original" ? "isOriginalOf" : "isEditOf" }
      : null;
    const initPersons = ctx.source === "person" && ctx.personId != null && ctx.personId >= 0
      ? [{ id: ctx.personId, fixed: true }] : [];
    const [shared, setShared] = useState({
      source: ctx.source === "relation" && ctx.role === "edit" ? "flux" : "original",
      persons: initPersons,
      relation: initRel,
      tags: [],
      faceOriginal: false,
      caption: "",
    });
    const [overrides, setOverrides] = useState({}); // { [fileId]: partial }

    // ---- relation browser + person popover ----
    const [relPicker, setRelPicker] = useState(false);
    const [personPicker, setPersonPicker] = useState(false);
    const [tagDraft, setTagDraft] = useState("");

    // resolve the metadata object for the active scope (read)
    const activeMeta = scope === "all" ? shared : { ...shared, ...(overrides[scope] || {}) };
    const isOverridden = (key) => scope !== "all" && overrides[scope] && key in overrides[scope];

    // write a field for current scope
    const setField = (key, val) => {
      if (scope === "all") setShared((s) => ({ ...s, [key]: val }));
      else setOverrides((o) => ({ ...o, [scope]: { ...(o[scope] || {}), [key]: val } }));
    };

    // ---- file ops ----
    const addReal = (fileList) => {
      const arr = [...fileList].filter((f) => f.type.startsWith("image/"));
      if (!arr.length) { setFiles((p) => [...p, makeSample()]); return; }
      const next = arr.map((f) => {
        const url = URL.createObjectURL(f);
        const e = { id: "f" + (++_fid) + "_" + Date.now(), name: f.name, sizeKB: f.size / 1024, w: 0, h: 0, photo: url, bg: "var(--surface)" };
        const im = new Image(); im.onload = () => { e.w = im.naturalWidth; e.h = im.naturalHeight; setFiles((p) => [...p]); }; im.src = url;
        return e;
      });
      setFiles((p) => [...p, ...next]);
    };
    const removeFile = (id) => {
      setFiles((p) => p.filter((f) => f.id !== id));
      setOverrides((o) => { const n = { ...o }; delete n[id]; return n; });
      if (scope === id) setScope("all");
    };

    // ---- drag & drop ----
    const onDragEnter = (e) => { e.preventDefault(); dragDepth.current++; setDragging(true); };
    const onDragLeave = (e) => { e.preventDefault(); dragDepth.current--; if (dragDepth.current <= 0) { setDragging(false); dragDepth.current = 0; } };
    const onDrop = (e) => {
      e.preventDefault(); setDragging(false); dragDepth.current = 0;
      if (e.dataTransfer.files && e.dataTransfer.files.length) addReal(e.dataTransfer.files);
      else setFiles((p) => [...p, makeSample()]);
    };

    useEffect(() => {
      const h = (e) => { if (e.key === "Escape" && !relPicker && !personPicker) onClose(); };
      window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h);
    }, [relPicker, personPicker]);

    // ---- person helpers (scope-aware) ----
    const persons = activeMeta.persons || [];
    const addPerson = (pid) => { if (persons.some((p) => p.id === pid)) return; setField("persons", [...persons, { id: pid, fixed: false }]); };
    const removePerson = (pid) => setField("persons", persons.filter((p) => p.id !== pid));
    const togglePin = (pid) => setField("persons", persons.map((p) => p.id === pid ? { ...p, fixed: !p.fixed } : p));

    // ---- tags ----
    const tags = activeMeta.tags || [];
    const addTag = () => { const v = tagDraft.trim().toLowerCase(); if (v && !tags.includes(v)) setField("tags", [...tags, v]); setTagDraft(""); };
    const removeTag = (t) => setField("tags", tags.filter((x) => x !== t));

    // ---- relation ----
    const relation = activeMeta.relation;
    const relAsset = relation ? assets.find((a) => a.id === relation.assetId) : null;
    const setRelation = (assetId) => setField("relation", { assetId, dir: relation ? relation.dir : "isEditOf" });
    const setDir = (dir) => setField("relation", { ...relation, dir });

    // ---- header context chip ----
    let ctxChip = null;
    if (ctx.source === "person" && ctx.personId >= 0) {
      ctxChip = React.createElement("div", { className: "ctx-chip" },
        React.createElement("div", { className: "cc-thumb" }, React.createElement(Avatar, { personId: ctx.personId, size: 24, ring: false })),
        React.createElement("span", { className: "cc-k" }, "Ordner"), PF.personName(ctx.personId));
    } else if (ctx.source === "relation" && relAsset) {
      ctxChip = React.createElement("div", { className: "ctx-chip rel" },
        React.createElement("div", { className: "cc-sq" }, React.createElement(Img, { src: relAsset.photo, bg: relAsset.bg })),
        React.createElement("span", { className: "cc-k" }, "Bezug"), "#" + relAsset.id);
    }

    // ---- submit ----
    const submit = () => {
      const n = files.length;
      const anyFaces = files.some((f) => {
        const m = { ...shared, ...(overrides[f.id] || {}) };
        return (m.persons && m.persons.length) || m.faceOriginal;
      });
      const jobs = [
        { kind: "refresh", name: "Import", sub: n + " Bild" + (n === 1 ? "" : "er") + " · Pipeline gestartet", pct: 4, done: false },
        { kind: "tag", name: "Auto-Tagging", sub: "WD14 · " + n + " Bild" + (n === 1 ? "" : "er"), pct: 0, done: false },
        { kind: "caption", name: "Caption-Lauf", sub: "Florence-2-base · " + n, pct: 0, done: false },
      ];
      if (anyFaces) jobs.splice(2, 0, { kind: "face", name: "Face-Extraktion", sub: "buffalo_l · " + n, pct: 0, done: false });
      onSubmit(jobs);
      onClose();
    };

    const scopeLabel = scope === "all"
      ? { t: "Alle Dateien · " + files.length, s: "Metadaten gelten für jeden Import" }
      : (() => { const f = files.find((x) => x.id === scope); return { t: f ? f.name : "Datei", s: "Nur für diese Datei (überschreibt „Alle“)" }; })();

    return React.createElement(React.Fragment, null,
      React.createElement("div", { className: "big-scrim", onClick: onClose },
        React.createElement("div", {
          className: "imp-modal", onClick: (e) => e.stopPropagation(),
          onDragEnter, onDragOver: (e) => e.preventDefault(), onDragLeave, onDrop,
        },
          // header
          React.createElement("div", { className: "imp-head" },
            React.createElement("div", { className: "ih-ico" }, React.createElement(Icon, { name: "upload", size: 19 })),
            React.createElement("div", { style: { minWidth: 0, flex: 1 } },
              React.createElement("div", { className: "imp-title" }, "Bilder importieren"),
              React.createElement("div", { className: "imp-sub" }, "Lokal verarbeitet · Tagging, Gesichter & Caption laufen offline")),
            ctxChip,
            React.createElement("button", { className: "iconbtn", style: { width: 34, height: 34 }, onClick: onClose }, React.createElement(Icon, { name: "x", size: 19 }))),

          // body
          React.createElement("div", { className: "imp-body" },
            // LEFT — files
            React.createElement("div", { className: "imp-left" + (dragging ? " drag" : "") },
              React.createElement("input", { ref: inputRef, type: "file", accept: "image/*", multiple: true, style: { display: "none" }, onChange: (e) => { addReal(e.target.files); e.target.value = ""; } }),
              files.length === 0
                ? React.createElement("div", { className: "imp-drop", onClick: () => inputRef.current && inputRef.current.click() },
                    React.createElement("div", { className: "dz-ico" }, React.createElement(Icon, { name: "upload", size: 26 })),
                    React.createElement("div", { className: "dz-title" }, "Dateien hierher ziehen"),
                    React.createElement("div", { className: "dz-sub" }, "JPG, PNG, WebP · einzeln oder als Stapel"),
                    React.createElement("div", { className: "dz-or" }, "oder"),
                    React.createElement("button", { className: "dz-btn", onClick: (e) => { e.stopPropagation(); inputRef.current.click(); } }, React.createElement(Icon, { name: "upload", size: 15 }), "Dateien wählen"),
                    React.createElement("div", { className: "dz-sample" }, React.createElement("b", { onClick: (e) => { e.stopPropagation(); setFiles([makeSample(), makeSample(), makeSample()]); } }, "Beispieldateien laden")))
                : React.createElement("div", { className: "imp-filewrap" },
                    React.createElement("div", { className: "imp-filebar" },
                      React.createElement("span", { className: "fb-t" }, files.length + " Datei" + (files.length === 1 ? "" : "en")),
                      React.createElement("button", { className: "imp-addmore", onClick: () => inputRef.current.click() }, React.createElement(Icon, { name: "plus", size: 14 }), "Hinzufügen")),
                    React.createElement("div", { className: "imp-files" },
                      React.createElement("div", { className: "imp-allrow" + (scope === "all" ? " sel" : ""), onClick: () => setScope("all") },
                        React.createElement("div", { className: "ar-ico" }, React.createElement(Icon, { name: "layers", size: 17 })),
                        React.createElement("div", { style: { minWidth: 0, flex: 1 } },
                          React.createElement("div", { className: "ar-t" }, "Alle Dateien"),
                          React.createElement("div", { className: "ar-s" }, "Gemeinsame Metadaten"))),
                      files.map((f) => React.createElement("div", {
                        key: f.id, className: "imp-file" + (scope === f.id ? " sel" : ""), onClick: () => setScope(f.id),
                      },
                        React.createElement("div", { className: "if-thumb" }, React.createElement(Img, { src: f.photo, bg: f.bg })),
                        React.createElement("div", { className: "if-body" },
                          React.createElement("div", { className: "if-name" }, f.name),
                          React.createElement("div", { className: "if-meta" },
                            React.createElement("span", null, f.w ? f.w + "×" + f.h : "…"),
                            React.createElement("span", null, (f.sizeKB / 1024).toFixed(1) + " MB"),
                            overrides[f.id] && Object.keys(overrides[f.id]).length > 0 && React.createElement("span", { className: "if-adj" }, "angepasst"))),
                        React.createElement("button", { className: "if-x", title: "Entfernen", onClick: (e) => { e.stopPropagation(); removeFile(f.id); } }, React.createElement(Icon, { name: "x", size: 15 }))))))),

            // RIGHT — metadata
            React.createElement("div", { className: "imp-right" },
              React.createElement("div", { className: "imp-scope" },
                scope === "all"
                  ? React.createElement("div", { className: "sc-ico" }, React.createElement(Icon, { name: "layers", size: 16 }))
                  : React.createElement("div", { className: "sc-thumb" }, (() => { const f = files.find((x) => x.id === scope); return f ? React.createElement(Img, { src: f.photo, bg: f.bg }) : null; })()),
                React.createElement("div", { style: { minWidth: 0, flex: 1 } },
                  React.createElement("div", { className: "sc-t" }, scopeLabel.t),
                  React.createElement("div", { className: "sc-s" }, scopeLabel.s)),
                scope !== "all" && overrides[scope] && Object.keys(overrides[scope]).length > 0 &&
                  React.createElement("button", { className: "rf-clear", style: { fontSize: 11.5, color: "var(--accent)", fontWeight: 600 }, onClick: () => setOverrides((o) => { const n = { ...o }; delete n[scope]; return n; }) }, "Auf „Alle“ zurücksetzen")),

              // Quelle
              React.createElement("div", { className: "fld" },
                React.createElement("div", { className: "fld-lbl" }, "Quelle", isOverridden("source") && React.createElement("span", { className: "fl-auto" }, "angepasst")),
                React.createElement("div", { className: "seg-pick" },
                  SOURCES.map((s) => React.createElement("button", { key: s.id, className: activeMeta.source === s.id ? "on" : "", onClick: () => setField("source", s.id) },
                    React.createElement("span", { className: "sw", style: { background: s.sw } }), s.label)))),

              // Personen
              React.createElement("div", { className: "fld" },
                React.createElement("div", { className: "fld-lbl" }, "Personen",
                  ctx.source === "person" && React.createElement("span", { className: "fl-auto" }, React.createElement(Icon, { name: "pin", size: 11 }), "aus Ordner")),
                React.createElement("div", { className: "psel-wrap" },
                  persons.map((p) => React.createElement("div", { key: p.id, className: "psel-chip" + (p.fixed ? " fix" : "") },
                    React.createElement(Avatar, { personId: p.id, size: 22, ring: false }),
                    React.createElement("span", { className: "pc-name" }, PF.personName(p.id)),
                    React.createElement("button", { className: "pc-pin" + (p.fixed ? " on" : ""), title: p.fixed ? "Feste Zuordnung (bestätigt)" : "Als fix markieren", onClick: () => togglePin(p.id) },
                      React.createElement(Icon, { name: p.fixed ? "lock" : "pin", size: 13 })),
                    React.createElement("button", { className: "pc-x", title: "Entfernen", onClick: () => removePerson(p.id) }, React.createElement(Icon, { name: "x", size: 13 })))),
                  React.createElement("button", { className: "psel-add", onClick: () => setPersonPicker(true) }, React.createElement(Icon, { name: "plus", size: 14 }), "Person")),
                persons.some((p) => p.fixed) && React.createElement("div", { className: "note", style: { marginTop: 10 } },
                  React.createElement(Icon, { name: "lock", size: 14 }), "Fix markierte Personen werden beim Face-Matching nicht überschrieben.")),

              // Beziehung
              React.createElement("div", { className: "fld" },
                React.createElement("div", { className: "fld-lbl" }, "Beziehung",
                  ctx.source === "relation" && React.createElement("span", { className: "fl-auto" }, React.createElement(Icon, { name: "link", size: 11 }), "vorbelegt")),
                relAsset
                  ? React.createElement("div", { className: "rel-card" },
                      React.createElement("div", { className: "rel-card-top" },
                        React.createElement("div", { className: "rel-thumb" }, React.createElement(Img, { src: relAsset.photo, bg: relAsset.bg })),
                        React.createElement("div", { style: { minWidth: 0 } },
                          React.createElement("div", { className: "rel-id" }, "#" + relAsset.id),
                          React.createElement("div", { className: "rel-cap" }, relAsset.caption)),
                        React.createElement("div", { className: "rel-acts" },
                          React.createElement("button", { className: "rel-mini", title: "Anderes Bild wählen", onClick: () => setRelPicker(true) }, React.createElement(Icon, { name: "pencil", size: 14 })),
                          React.createElement("button", { className: "rel-mini del", title: "Beziehung entfernen", onClick: () => setField("relation", null) }, React.createElement(Icon, { name: "x", size: 14 })))),
                      React.createElement("div", { className: "rel-dir-lbl" }, "Richtung"),
                      React.createElement("div", { className: "seg-pick" },
                        React.createElement("button", { className: relation.dir === "isEditOf" ? "on" : "", onClick: () => setDir("isEditOf") }, "Edit von #" + relAsset.id),
                        React.createElement("button", { className: relation.dir === "isOriginalOf" ? "on" : "", onClick: () => setDir("isOriginalOf") }, "Original von #" + relAsset.id)))
                  : React.createElement("button", { className: "rel-add", onClick: () => setRelPicker(true) }, React.createElement(Icon, { name: "link", size: 16 }), "Mit Original / Edit verknüpfen")),

              // Face-Original
              React.createElement("div", { className: "fld" },
                React.createElement("div", { className: "switch-row", onClick: () => setField("faceOriginal", !activeMeta.faceOriginal) },
                  React.createElement("div", { className: "switch" + (activeMeta.faceOriginal ? " on" : "") }, React.createElement("i", null)),
                  React.createElement("div", { className: "sr-txt" },
                    React.createElement("div", { className: "sr-title" }, "Als eigenständiges Face-Original importieren"),
                    React.createElement("div", { className: "sr-sub" }, "Wird als Referenz-Gesicht behandelt – nicht als Edit eines anderen Bildes.")))),

              // Tags
              React.createElement("div", { className: "fld" },
                React.createElement("div", { className: "fld-lbl" }, "Manuelle Tags", isOverridden("tags") && React.createElement("span", { className: "fl-auto" }, "angepasst")),
                React.createElement("div", { className: "tagwrap" },
                  tags.map((t) => React.createElement("span", { key: t, className: "tg manual" }, t,
                    React.createElement("span", { className: "tx", onClick: () => removeTag(t) }, React.createElement(Icon, { name: "x", size: 12 })))),
                  React.createElement("input", {
                    className: "tg", style: { width: 120, outline: "none", color: "var(--text)" }, value: tagDraft, placeholder: "+ Tag …",
                    onChange: (e) => setTagDraft(e.target.value),
                    onKeyDown: (e) => { if (e.key === "Enter") addTag(); }, onBlur: addTag,
                  }))),

              // Caption / Notiz
              React.createElement("div", { className: "fld", style: { marginBottom: 4 } },
                React.createElement("div", { className: "fld-lbl" }, "Caption / Notiz", isOverridden("caption") && React.createElement("span", { className: "fl-auto" }, "angepasst")),
                React.createElement("textarea", {
                  className: "txt-in", rows: 3, value: activeMeta.caption,
                  placeholder: "Optional – leer lassen, dann generiert Florence-2 automatisch eine Caption.",
                  onChange: (e) => setField("caption", e.target.value),
                })))),

          // footer
          React.createElement("div", { className: "imp-foot" },
            React.createElement("div", { className: "foot-info" },
              React.createElement(Icon, { name: "info", size: 13 }),
              files.length === 0 ? "Noch keine Dateien" : files.length + " Bild" + (files.length === 1 ? "" : "er") + " bereit · Verarbeitung startet nach Import"),
            React.createElement("div", { className: "foot-actions" },
              React.createElement("button", { className: "foot-btn ghost", onClick: onClose }, "Abbrechen"),
              React.createElement("button", { className: "foot-btn primary", disabled: files.length === 0, onClick: submit },
                React.createElement(Icon, { name: "upload", size: 16 }), files.length > 1 ? files.length + " importieren" : "Importieren"))),

          dragging && React.createElement("div", { className: "imp-dragveil" },
            React.createElement("div", { className: "dv-pill" }, React.createElement(Icon, { name: "upload", size: 18, style: { color: "var(--accent)" } }), "Loslassen zum Hinzufügen")))),

      // nested: relation browser
      relPicker && React.createElement(window.RelationBrowser, {
        assets, multi: false,
        title: "Bild verknüpfen", subtitle: "Wähle das zugehörige Original oder den Edit",
        initialSelected: relation ? [relation.assetId] : [],
        excludeIds: ctx.source === "relation" ? [] : [],
        onConfirm: (ids) => { if (ids[0] != null) setRelation(ids[0]); setRelPicker(false); },
        onClose: () => setRelPicker(false),
      }),
      // nested: person picker
      personPicker && React.createElement(window.PersonSelect, {
        excludeIds: persons.map((p) => p.id),
        onPick: addPerson, onClose: () => setPersonPicker(false),
        title: "Person zuordnen",
      }));
  }

  window.ImportDialog = ImportDialog;
})();
