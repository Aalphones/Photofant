/* Photofant — DupeChecker: duplicate/similar scan (person mode OR gallery filter mode) */
(function () {
  const { Icon, PF } = window;
  const { Img } = window.UI;
  const { useState, useEffect, useMemo, useCallback } = React;

  const sr = (seed) => {
    let s = seed ^ 0x9e3779b9;
    s = Math.imul(s ^ (s >>> 16), 0x45d9f3b);
    s = Math.imul(s ^ (s >>> 16), 0x45d9f3b);
    return ((s ^ (s >>> 16)) >>> 0) / 0xffffffff;
  };

  /* ---- build duplicate pairs from a flat asset array ---- */
  function generatePairs(scanAssets) {
    const pairs = [];
    const seen  = new Set();
    const key   = (a, b) => Math.min(a.id, b.id) + "_" + Math.max(a.id, b.id);

    /* 1 – existing edit relations first */
    scanAssets.forEach(a => {
      if (a.originalId != null) {
        const orig = scanAssets.find(x => x.id === a.originalId);
        if (orig) {
          const k = key(orig, a);
          if (!seen.has(k)) {
            seen.add(k);
            pairs.push({ a: orig, b: a, score: 0.90 + sr(a.id * 31) * 0.09, relation: "edit" });
          }
        }
      }
    });

    /* 2 – similar unlinked pairs */
    for (let i = 0; i < scanAssets.length && pairs.length < 14; i++) {
      for (let j = i + 1; j < scanAssets.length && pairs.length < 14; j++) {
        const a = scanAssets[i], b = scanAssets[j];
        const k = key(a, b);
        if (seen.has(k)) continue;
        const score = 0.60 + sr(a.id * 53 + b.id * 17 + 7) * 0.36;
        if (score >= 0.72) { seen.add(k); pairs.push({ a, b, score, relation: null }); }
      }
    }

    return pairs.sort((x, y) => y.score - x.score);
  }

  /* ---- score badge ---- */
  function ScoreBadge({ score }) {
    const pct = Math.round(score * 100);
    const cls = score >= 0.90 ? "high" : score >= 0.80 ? "mid" : "low";
    return React.createElement("div", { className: "dc-score-wrap" },
      React.createElement("div", { className: "dc-bar-bg" },
        React.createElement("div", { className: "dc-bar-fill " + cls, style: { width: pct + "%" } })),
      React.createElement("span", { className: "dc-pct " + cls }, pct + "%"));
  }

  /* ---- pair compare overlay ---- */
  function PairCompare({ pair, onClose, onRemove, onSetRelation }) {
    const { a, b, score, relation } = pair;
    return React.createElement("div", { className: "dc-cmp-scrim", onClick: onClose },
      React.createElement("div", { className: "dc-cmp-modal", onClick: e => e.stopPropagation() },
        React.createElement("div", { className: "dc-cmp-head" },
          React.createElement("span", { style: { fontWeight: 600, fontSize: 13 } },
            "Vergleich · " + Math.round(score * 100) + "% ähnlich"),
          React.createElement("div", { style: { display: "flex", gap: 8, marginLeft: "auto", alignItems: "center" } },
            !relation && React.createElement("button", { className: "mini-btn", onClick: () => { onSetRelation(pair); onClose(); } },
              React.createElement(Icon, { name: "link", size: 13 }), "Als Original/Edit"),
            React.createElement("button", { className: "mini-btn warn", onClick: () => { onRemove(pair); onClose(); } },
              React.createElement(Icon, { name: "trash", size: 13 }), "Rechts löschen"),
            React.createElement("button", { className: "iconbtn", style: { width: 28, height: 28 }, onClick: onClose },
              React.createElement(Icon, { name: "x", size: 14 })))),
        React.createElement("div", { className: "dc-cmp-panels" },
          [a, b].map((asset, i) =>
            React.createElement("div", { key: i, className: "dc-cmp-panel" },
              React.createElement("div", { className: "dc-cmp-img" },
                React.createElement(Img, { src: asset.photoLg || asset.photo, bg: asset.bg, style: { position: "absolute", inset: 0 } }),
                relation && React.createElement("div", { className: "dc-cmp-badge " + (i === 0 ? "orig" : "edit") },
                  i === 0 ? "Original" : "Edit")),
              React.createElement("div", { className: "dc-cmp-foot" },
                React.createElement("span", { style: { fontWeight: 500 } }, "#" + asset.id),
                React.createElement("span", null, PF.sourceLabel(asset.source)),
                React.createElement("span", null, asset.dims.w + "×" + asset.dims.h),
                React.createElement("span", null,
                  asset.date.toLocaleDateString("de-DE", { day: "2-digit", month: "short", year: "numeric" }))))))));
  }

  /* ---- pair row ---- */
  function PairRow({ pair, onCompare, onRemove, onKeepBoth, onSetRelation }) {
    const { a, b, score, relation } = pair;
    return React.createElement("div", { className: "dc-pair" },
      React.createElement("div", { className: "dc-thumbs" },
        React.createElement("div", { className: "dc-thumb" + (relation ? " orig" : "") },
          React.createElement(Img, { src: a.photo, bg: a.bg })),
        React.createElement("div", { className: "dc-thumb" + (relation ? " edit" : "") },
          React.createElement(Img, { src: b.photo, bg: b.bg }))),
      React.createElement("div", { className: "dc-pair-info" },
        React.createElement(ScoreBadge, { score }),
        React.createElement("div", { className: "dc-pair-ids" },
          React.createElement("span", null, "#" + a.id + " · " + a.dims.w + "×" + a.dims.h),
          React.createElement("span", { className: "dc-sep" }, "·"),
          React.createElement("span", null, "#" + b.id + " · " + b.dims.w + "×" + b.dims.h),
          relation === "edit" && React.createElement("span", { className: "dc-rel-tag" },
            React.createElement(Icon, { name: "link", size: 10 }), "Original / Edit"))),
      React.createElement("div", { className: "dc-pair-acts" },
        React.createElement("button", { className: "iconbtn dc-act", title: "Vergleichen", onClick: () => onCompare(pair) },
          React.createElement(Icon, { name: "compare", size: 15 })),
        !relation && React.createElement("button", { className: "iconbtn dc-act", title: "Als Original/Edit verknüpfen", onClick: () => onSetRelation(pair) },
          React.createElement(Icon, { name: "link", size: 15 })),
        React.createElement("button", { className: "iconbtn dc-act warn", title: "Rechtes Bild entfernen", onClick: () => onRemove(pair) },
          React.createElement(Icon, { name: "trash", size: 15 })),
        React.createElement("button", { className: "iconbtn dc-act ok", title: "Beide behalten", onClick: () => onKeepBoth(pair) },
          React.createElement(Icon, { name: "check", size: 15 }))));
  }

  /* ---- main DupeChecker ----
     Props:
       scanAssets  – assets to scan (required)
       personId    – if set, show person header (optional)
       label       – fallback header label, e.g. "47 Bilder · Aktiver Filter" (optional)
       onClose, onUpdateAsset
  ---- */
  function DupeChecker({ scanAssets, personId, label, onClose, onUpdateAsset }) {
    const person = personId != null ? (PF.PERSONS.find(p => p.id === personId) || null) : null;
    const allPairs   = useMemo(() => generatePairs(scanAssets), [scanAssets]);
    const [phase, setPhase]         = useState("idle");
    const [revealed, setRevealed]   = useState(0);
    const [dismissed, setDismissed] = useState(new Set());
    const [cmpTarget, setCmpTarget] = useState(null);

    const startScan = useCallback(() => {
      setPhase("scanning"); setRevealed(0);
      let n = 0;
      const t = setInterval(() => {
        n++;
        setRevealed(n);
        if (n >= allPairs.length) { clearInterval(t); setPhase("done"); }
      }, 240);
    }, [allPairs.length]);

    const dismiss = useCallback((pair) => {
      setDismissed(s => new Set([...s, pair.a.id + "_" + pair.b.id]));
    }, []);

    const handleSetRelation = useCallback((pair) => {
      onUpdateAsset && onUpdateAsset(pair.b.id, { originalId: pair.a.id });
      dismiss(pair);
    }, [onUpdateAsset, dismiss]);

    const visiblePairs = allPairs.slice(0, revealed).filter(p => !dismissed.has(p.a.id + "_" + p.b.id));
    const pct = allPairs.length > 0 ? Math.round(revealed / allPairs.length * 100) : 100;
    const scanLabel = label || (scanAssets.length + " Bilder");

    return React.createElement(React.Fragment, null,
      cmpTarget && React.createElement(PairCompare, {
        pair: cmpTarget,
        onClose: () => setCmpTarget(null),
        onRemove: (pair) => { dismiss(pair); setCmpTarget(null); },
        onSetRelation: (pair) => { handleSetRelation(pair); setCmpTarget(null); },
      }),

      React.createElement("div", { className: "dc-overlay" + (cmpTarget ? " dc-behind" : "") },
        /* header */
        React.createElement("div", { className: "dc-head" },
          React.createElement("button", { className: "iconbtn", style: { width: 34, height: 34 }, onClick: onClose },
            React.createElement(Icon, { name: "arrowLeft", size: 18 })),
          person
            ? React.createElement(React.Fragment, null,
                React.createElement("div", { className: "dc-head-av" },
                  React.createElement(Img, { src: person.portrait, bg: person.avatarBg })),
                React.createElement("div", { style: { flex: 1, minWidth: 0 } },
                  React.createElement("div", { style: { fontWeight: 600, fontSize: 14 } }, person.name),
                  React.createElement("div", { style: { fontSize: 11.5, color: "var(--text-3)" } },
                    scanAssets.length + " Bilder · Duplikat-Analyse")))
            : React.createElement("div", { style: { flex: 1, minWidth: 0 } },
                React.createElement("div", { style: { fontWeight: 600, fontSize: 14 } }, "Duplikat-Analyse"),
                React.createElement("div", { style: { fontSize: 11.5, color: "var(--text-3)" } }, scanLabel)),
          phase === "idle" && React.createElement("button", { className: "pbtn primary", style: { gap: 7 }, onClick: startScan },
            React.createElement(Icon, { name: "refresh", size: 14 }), "Scan starten")),

        /* progress */
        phase !== "idle" && React.createElement("div", { className: "dc-progress-wrap" },
          React.createElement("div", { className: "dc-prog-track" },
            React.createElement("div", { className: "dc-prog-fill" + (phase === "done" ? " done" : ""), style: { width: pct + "%" } })),
          React.createElement("div", { className: "dc-prog-lbl" },
            phase === "done"
              ? (visiblePairs.length > 0
                  ? visiblePairs.length + " ähnliche Paare gefunden"
                  : React.createElement(React.Fragment, null,
                      React.createElement(Icon, { name: "check", size: 13, style: { color: "var(--good)" } }), " Keine Duplikate gefunden"))
              : "Analysiere … " + revealed + " / " + allPairs.length + " Paare")),

        /* list */
        React.createElement("div", { className: "dc-list" },
          phase === "idle" && React.createElement("div", { className: "dc-idle-hint" },
            React.createElement(Icon, { name: "compare", size: 40, style: { color: "var(--text-3)" } }),
            React.createElement("div", { style: { fontWeight: 600, marginTop: 14, fontSize: 15 } }, "Duplikat-Scan"),
            React.createElement("div", { style: { color: "var(--text-3)", fontSize: 13, marginTop: 6, maxWidth: 300, textAlign: "center", lineHeight: 1.5 } },
              "Findet ähnliche und doppelte Bilder in " + scanLabel + ". Bereits verknüpfte Original/Edit-Paare werden besonders markiert.")),
          visiblePairs.map(pair =>
            React.createElement(PairRow, {
              key: pair.a.id + "_" + pair.b.id, pair,
              onCompare: setCmpTarget, onKeepBoth: dismiss,
              onRemove: dismiss, onSetRelation: handleSetRelation,
            })),
          phase === "done" && visiblePairs.length === 0 && React.createElement("div", { className: "dc-idle-hint" },
            React.createElement(Icon, { name: "check", size: 40, style: { color: "var(--good)" } }),
            React.createElement("div", { style: { fontWeight: 600, marginTop: 14 } }, "Alles geprüft — keine Duplikate")))));
  }

  Object.assign(window, { DupeChecker });
})();
