/* Photofant — shared presentational components → window */
(function () {
  const { Icon } = window;

  // Photo renderer. With `src` → real <img> (object-fit cover, gradient bg while loading).
  // Without `src` → abstract gradient stand-in from the data layer (legacy / fallback).
  function Img({ bg, src, ar, radius, className = "", style = {} }) {
    if (src) {
      return React.createElement("img", {
        src, loading: "lazy", draggable: false, alt: "",
        className,
        style: {
          position: "absolute", inset: 0, width: "100%", height: "100%",
          objectFit: "cover", display: "block", borderRadius: radius || 0,
          background: bg || "var(--surface)", ...style,
        },
      });
    }
    return React.createElement("div", {
      className: "grain " + className,
      style: { position: "absolute", inset: 0, background: bg, borderRadius: radius || 0, ...style },
    });
  }

  function Avatar({ personId, size = 34, ring = true }) {
    const src = window.PF.personPhoto(personId);
    const bg = window.PF.personBg(personId);
    return React.createElement("div", {
      style: {
        width: size, height: size, borderRadius: "50%", overflow: "hidden",
        position: "relative", flex: "none",
        boxShadow: ring ? "inset 0 0 0 1px rgba(255,255,255,.12)" : "none",
      },
    }, React.createElement(Img, { src, bg }));
  }

  // generic tooltip-ish wrapper not needed; keep minimal

  function scoreClass(s) { return s >= 0.9 ? "high" : s >= 0.75 ? "mid" : ""; }

  window.UI = { Img, Avatar, scoreClass };
})();
