/* Photofant — VersionCompare overlay (Lightbox Vergleichen-Button) */
(function () {
  const { Icon, PF } = window;
  const { Img } = window.UI;
  const { useState, useMemo } = React;

  function buildItems(asset, allAssets) {
    const items = [];
    items.push({ id: asset.id, label: "Aktuell", tag: "current", photo: asset.photoLg || asset.photo, bg: asset.bg, source: asset.source, dims: asset.dims, date: asset.date });
    asset.versions.forEach((v, i) => {
      const vw = parseInt(v.res) || asset.dims.w;
      const vh = Math.round(vw / (asset.ar.w / asset.ar.h));
      items.push({ id: "v" + i, label: v.label, tag: "version", photo: asset.photo, bg: asset.bg, source: asset.source, dims: { w: vw, h: vh }, date: v.when });
    });
    if (asset.originalId != null) {
      const orig = allAssets.find(a => a.id === asset.originalId);
      if (orig) items.push({ id: orig.id, label: "Original #" + orig.id, tag: "original", photo: orig.photoLg || orig.photo, bg: orig.bg, source: orig.source, dims: orig.dims, date: orig.date });
    }
    allAssets.filter(a => a.originalId === asset.id).forEach(e => {
      items.push({ id: e.id, label: PF.sourceLabel(e.source) + " #" + e.id, tag: "edit", photo: e.photoLg || e.photo, bg: e.bg, source: e.source, dims: e.dims, date: e.date });
    });
    return items;
  }

  const TAG_META = {
    current:  { label: "Aktuell",  cls: "vc-tag-cur" },
    original: { label: "Original", cls: "vc-tag-orig" },
    edit:     { label: "Edit",     cls: "vc-tag-edit" },
    version:  { label: "Version",  cls: "vc-tag-ver" },
  };

  function ComparePanel({ item, items, idx, onChange }) {
    const tm = TAG_META[item.tag] || { label: item.tag, cls: "" };
    return React.createElement("div", { className: "vc-panel" },
      // selector strip
      React.createElement("div", { className: "vc-panel-sel" },
        items.map((it, i) =>
          React.createElement("button", {
            key: it.id + "-" + i,
            className: "vc-sel-btn" + (i === idx ? " on" : ""),
            onClick: () => onChange(i),
          }, it.label))),
      // image
      React.createElement("div", { className: "vc-img-wrap" },
        React.createElement(Img, { src: item.photo, bg: item.bg, style: { position: "absolute", inset: 0 } }),
        React.createElement("div", { className: "vc-tag-layer" },
          React.createElement("span", { className: "vc-tag " + tm.cls }, tm.label))),
      // footer metadata
      React.createElement("div", { className: "vc-panel-foot" },
        React.createElement("span", { style: { fontWeight: 500, color: "var(--text-2)" } }, item.dims.w + "×" + item.dims.h),
        React.createElement("span", null, PF.sourceLabel(item.source)),
        React.createElement("span", null, item.date.toLocaleDateString("de-DE", { day: "2-digit", month: "short", year: "numeric" }))));
  }

  function VersionCompare({ asset, allAssets, onClose }) {
    const items = useMemo(() => buildItems(asset, allAssets), [asset.id]);
    const [leftIdx, setLeftIdx]   = useState(0);
    const [rightIdx, setRightIdx] = useState(Math.min(1, items.length - 1));

    return React.createElement("div", { className: "vc-scrim", onClick: onClose },
      React.createElement("div", { className: "vc-modal", onClick: e => e.stopPropagation() },
        // header
        React.createElement("div", { className: "vc-head" },
          React.createElement(Icon, { name: "compare", size: 15, style: { color: "var(--text-2)" } }),
          React.createElement("span", { style: { fontWeight: 600, fontSize: 13 } },
            "Versionsvergleich · #" + asset.id),
          React.createElement("span", { style: { fontSize: 11, color: "var(--text-3)", marginLeft: 6 } },
            items.length + " Varianten"),
          React.createElement("button", {
            className: "iconbtn", style: { width: 28, height: 28, marginLeft: "auto" }, onClick: onClose,
          }, React.createElement(Icon, { name: "x", size: 14 }))),
        // two panels
        React.createElement("div", { className: "vc-panels" },
          React.createElement(ComparePanel, { item: items[leftIdx],  items, idx: leftIdx,  onChange: setLeftIdx }),
          React.createElement("div", { className: "vc-divider" }),
          React.createElement(ComparePanel, { item: items[rightIdx], items, idx: rightIdx, onChange: setRightIdx }))));
  }

  Object.assign(window, { VersionCompare });
})();
