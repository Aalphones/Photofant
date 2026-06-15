/* ============================================================
   Photofant — mock data layer (deterministic, seeded)
   Generates assets, persons, tags, jobs + abstract photo
   "stand-in" gradients that read as real photography.
   ============================================================ */
(function () {
  // ---- seeded RNG (mulberry32) ----
  function rng(seed) {
    let t = seed >>> 0;
    return function () {
      t += 0x6D2B79F5;
      let x = Math.imul(t ^ (t >>> 15), 1 | t);
      x ^= x + Math.imul(x ^ (x >>> 7), 61 | x);
      return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
  }
  const pick = (r, arr) => arr[Math.floor(r() * arr.length)];

  // ---- real photo helpers (visualization only; app is conceptually offline) ----
  // Picsum = real photography at any size → "various sizes" justified grid.
  function picsum(seed, w, h) { return "https://picsum.photos/seed/" + seed + "/" + w + "/" + h; }
  function photoDims(ar, longSide) {
    return ar.w >= ar.h
      ? { w: longSide, h: Math.round(longSide * ar.h / ar.w) }
      : { h: longSide, w: Math.round(longSide * ar.w / ar.h) };
  }

  // grain texture (svg noise) shared via CSS var
  const grain =
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='120' height='120' filter='url(%23n)' opacity='0.55'/%3E%3C/svg%3E\")";
  document.documentElement.style.setProperty("--grain", grain);

  // ---- "scene" palettes — evoke real photography moods ----
  // each: bg gradient stops + a warm/cool subject blob
  const SCENES = [
    { name: "golden hour", bg: ["oklch(0.42 0.10 65)", "oklch(0.22 0.06 40)"], subj: "oklch(0.74 0.12 70)", hi: "oklch(0.86 0.10 80)" },
    { name: "studio teal",  bg: ["oklch(0.30 0.06 220)", "oklch(0.16 0.04 240)"], subj: "oklch(0.62 0.07 230)", hi: "oklch(0.80 0.05 220)" },
    { name: "warm portrait",bg: ["oklch(0.34 0.05 30)", "oklch(0.20 0.04 25)"], subj: "oklch(0.68 0.09 40)", hi: "oklch(0.82 0.07 50)" },
    { name: "moody green",  bg: ["oklch(0.30 0.06 155)", "oklch(0.17 0.04 165)"], subj: "oklch(0.56 0.08 150)", hi: "oklch(0.74 0.07 145)" },
    { name: "neon night",   bg: ["oklch(0.26 0.09 300)", "oklch(0.16 0.07 285)"], subj: "oklch(0.60 0.13 320)", hi: "oklch(0.72 0.15 340)" },
    { name: "soft grey",    bg: ["oklch(0.46 0.02 260)", "oklch(0.28 0.02 260)"], subj: "oklch(0.66 0.03 250)", hi: "oklch(0.84 0.02 250)" },
    { name: "beach",        bg: ["oklch(0.58 0.08 230)", "oklch(0.40 0.06 210)"], subj: "oklch(0.78 0.07 90)", hi: "oklch(0.90 0.06 95)" },
    { name: "rose",         bg: ["oklch(0.40 0.08 5)",  "oklch(0.24 0.06 350)"], subj: "oklch(0.70 0.10 10)", hi: "oklch(0.84 0.08 20)" },
    { name: "amber studio", bg: ["oklch(0.38 0.07 55)", "oklch(0.20 0.05 45)"], subj: "oklch(0.72 0.11 60)", hi: "oklch(0.88 0.09 70)" },
    { name: "cool blue",    bg: ["oklch(0.36 0.08 250)","oklch(0.19 0.05 255)"], subj: "oklch(0.60 0.10 255)", hi: "oklch(0.78 0.09 250)" },
    { name: "forest",       bg: ["oklch(0.32 0.06 140)","oklch(0.18 0.04 150)"], subj: "oklch(0.58 0.08 130)", hi: "oklch(0.76 0.08 120)" },
    { name: "monochrome",   bg: ["oklch(0.34 0.005 260)","oklch(0.14 0.005 260)"], subj: "oklch(0.60 0.006 260)", hi: "oklch(0.84 0.004 260)" },
  ];

  // build a CSS background that suggests a framed subject
  function sceneBg(sceneIdx, framing, r) {
    const s = SCENES[sceneIdx];
    // subject vertical position & size depends on framing
    let sy, ss;
    if (framing === "close_up") { sy = 42; ss = 78; }
    else if (framing === "medium") { sy = 64; ss = 64; }
    else { sy = 92; ss = 52; } // full_body
    const sx = 38 + Math.floor(r() * 26);
    const hiX = 24 + Math.floor(r() * 20), hiY = 18 + Math.floor(r() * 16);
    return [
      `radial-gradient(${ss}% ${ss + 8}% at ${sx}% ${sy}%, ${s.subj} 0%, transparent 58%)`,
      `radial-gradient(34% 26% at ${hiX}% ${hiY}%, ${s.hi} 0%, transparent 60%)`,
      `radial-gradient(120% 120% at 50% 120%, rgba(0,0,0,.35), transparent 60%)`,
      `linear-gradient(${150 + Math.floor(r() * 50)}deg, ${s.bg[0]}, ${s.bg[1]})`,
    ].join(", ");
  }

  // ---- persons ----
  // g/n → real portrait from randomuser.me (deterministic, reliable, true faces)
  const PERSON_DEFS = [
    { name: "Lena",   scene: 7,  g: "women", n: 65 },
    { name: "Jonas",  scene: 2,  g: "men",   n: 32 },
    { name: "Mara",   scene: 4,  g: "women", n: 68 },
    { name: "Felix",  scene: 9,  g: "men",   n: 75 },
    { name: "Sofia",  scene: 0,  g: "women", n: 44 },
    { name: "Noah",   scene: 10, g: "men",   n: 12 },
  ];

  // Larger known-face directory (für Zuordnung). Die 6 oben haben echte
  // Sammlungen; diese hier sind weitere bekannte Gesichter ohne (oder mit
  // wenigen) Treffern — damit die Personensuche realistisch skaliert.
  const DIR_FIRST = ["Anna", "Ben", "Clara", "David", "Emma", "Finn", "Greta", "Hannes", "Ida", "Jan",
    "Katja", "Leon", "Mia", "Nico", "Ole", "Paula", "Quirin", "Rosa", "Sven", "Tina",
    "Uwe", "Vera", "Wanja", "Xenia", "Yannik", "Zoe", "Amelie", "Bruno", "Carla", "Dennis",
    "Elif", "Fabian", "Gesa", "Henrik", "Iris", "Julius", "Karla", "Lukas", "Marlene", "Niklas",
    "Olivia", "Pascal", "Romy", "Simon", "Theresa", "Valentin", "Wiebke", "Yara", "Erik", "Nadja"];
  const DIR_LAST = ["Bauer", "Becker", "Fischer", "Hoffmann", "Keller", "Krüger", "Lehmann", "Maier",
    "Neumann", "Richter", "Schmidt", "Schulz", "Wagner", "Weber", "Werner", "Zimmermann"];
  const EXTRA_PEOPLE = [];
  for (let i = 0; i < 118; i++) {
    const g = i % 2 ? "men" : "women";
    const first = DIR_FIRST[(i * 5 + 2) % DIR_FIRST.length];
    const last = DIR_LAST[(i * 3 + 1) % DIR_LAST.length];
    EXTRA_PEOPLE.push({ name: first + " " + last, scene: i % 11, g, n: (i * 7 + 3) % 100, extra: true });
  }
  const ALL_PEOPLE = PERSON_DEFS.concat(EXTRA_PEOPLE);

  // ---- tag vocabulary (German) ----
  const TAGS_AUTO = [
    "porträt", "lächeln", "brille", "outdoor", "studio", "nahaufnahme",
    "blond", "dunkles haar", "kurze haare", "lange haare", "bart", "anzug",
    "rotes kleid", "lederjacke", "strand", "sonnenuntergang", "neonlicht",
    "regen", "winter", "wald", "schwarzweiß", "ganzkörper", "profil",
    "blickkontakt", "unscharf", "gegenlicht", "fenster", "café", "stadt",
  ];
  const TAGS_MANUAL = ["staffel 2", "kampagne herbst", "favorit-shoot", "ref-pose"];

  const CAPTIONS = [
    "Eine Person mit {hair} blickt direkt in die Kamera, weiches Seitenlicht.",
    "Nahaufnahme eines lächelnden Gesichts vor unscharfem {bg} Hintergrund.",
    "Ganzkörperaufnahme im {bg} Setting, natürliche Pose, neutraler Ausdruck.",
    "Porträt im Gegenlicht, {hair}, warmer Farbton der goldenen Stunde.",
    "Medium-Shot, Person trägt {outfit}, Studio-Beleuchtung von links.",
    "Profilansicht vor {bg} Kulisse, ruhige Stimmung, geringe Schärfentiefe.",
  ];
  const HAIRS = ["blondem Haar", "dunklem Haar", "kurzem Haar", "lockigem Haar"];
  const BGS = ["urbanem", "natürlichem", "studioartigem", "abendlichem"];
  const OUTFITS = ["eine Lederjacke", "einen dunklen Anzug", "ein rotes Kleid", "einen Mantel"];

  const SOURCES = ["original", "original", "original", "sdxl", "flux"];
  const FRAMINGS = ["close_up", "close_up", "medium", "medium", "full_body"];
  const FORMATS = ["jpeg", "png", "png", "jpeg"];

  const VERSION_TYPES = [
    { type: "original", label: "Original" },
    { type: "crop", label: "Zuschnitt" },
    { type: "upscale", label: "Upscale 2×" },
    { type: "flux_edit", label: "Flux-Edit" },
  ];

  function fluxMeta(r) {
    return {
      model: pick(r, ["FLUX.2 [klein] 9B", "FLUX.2 [klein] fp8"]),
      sampler: "euler", steps: 20 + Math.floor(r() * 20),
      cfg: (3 + r() * 2).toFixed(1), seed: Math.floor(r() * 9e9),
      size: pick(r, ["1024×1024", "1024×1280", "896×1152"]),
      prompt: pick(r, [
        "cinematic portrait, soft rim light, 85mm, shallow depth of field, film grain",
        "studio headshot, neutral background, high detail skin texture, natural light",
        "golden hour outdoor portrait, bokeh, warm tones, photorealistic",
      ]),
    };
  }
  function sdxlMeta(r) {
    return {
      model: "SDXL 1.0", sampler: pick(r, ["dpmpp_2m", "euler_a"]),
      steps: 28 + Math.floor(r() * 12), cfg: (5 + r() * 3).toFixed(1),
      seed: Math.floor(r() * 9e9), size: "1024×1024",
      prompt: "portrait photography, detailed face, professional lighting, 8k",
    };
  }

  const MONTHS = ["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"];

  // ---- generate assets ----
  function buildAssets(n) {
    const r = rng(424242);
    const assets = [];
    // distribute across recent months
    const periods = [
      { y: 2026, m: 5, label: "Juni 2026" },
      { y: 2026, m: 4, label: "Mai 2026" },
      { y: 2026, m: 3, label: "April 2026" },
      { y: 2026, m: 2, label: "März 2026" },
      { y: 2026, m: 0, label: "Januar 2026" },
      { y: 2025, m: 10, label: "November 2025" },
    ];
    for (let i = 0; i < n; i++) {
      const sourceR = r();
      const source = sourceR < 0.62 ? "original" : sourceR < 0.82 ? "sdxl" : "flux";
      const framing = pick(r, FRAMINGS);
      const pIdx = Math.floor(r() * (PERSON_DEFS.length + 0.6)); // some unknown
      const personId = pIdx >= PERSON_DEFS.length ? -1 : pIdx;
      const scene = personId >= 0 ? PERSON_DEFS[personId].scene : Math.floor(r() * SCENES.length);
      // aspect ratio
      const arRoll = r();
      let w, h;
      if (framing === "full_body") { w = 3; h = 4; }
      else if (arRoll < 0.25) { w = 4; h = 5; }
      else if (arRoll < 0.45) { w = 1; h = 1; }
      else if (arRoll < 0.6) { w = 3; h = 4; }
      else { w = 4; h = 5; }
      const px = pick(r, [768, 896, 1024, 1024, 1280, 1536]);
      const dims = { w: px, h: Math.round(px * h / w) };

      // tags
      const tagCount = 4 + Math.floor(r() * 6);
      const tset = new Set();
      while (tset.size < tagCount) tset.add(pick(r, TAGS_AUTO));
      const tags = [...tset].map((name) => ({ name, kind: "auto" }));
      if (r() < 0.3) tags.push({ name: pick(r, TAGS_MANUAL), kind: "manual" });

      // caption
      let cap = pick(r, CAPTIONS)
        .replace("{hair}", pick(r, HAIRS))
        .replace("{bg}", pick(r, BGS))
        .replace("{outfit}", pick(r, OUTFITS));

      const quality = 0.45 + r() * 0.54;
      const favourite = r() < 0.16;
      const period = periods[Math.floor(r() * periods.length)];
      const day = 1 + Math.floor(r() * 27);
      const date = new Date(period.y, period.m, day, 8 + Math.floor(r() * 12), Math.floor(r() * 60));

      // versions
      const nv = source === "original" ? (r() < 0.35 ? 2 + Math.floor(r() * 2) : 1) : (r() < 0.5 ? 2 : 1);
      const versions = [];
      for (let v = 0; v < nv; v++) {
        const vt = v === 0 ? VERSION_TYPES[0] : pick(r, VERSION_TYPES.slice(1));
        versions.push({
          type: vt.type, label: vt.label,
          current: v === nv - 1,
          res: v === 0 ? `${dims.w}×${dims.h}` : (vt.type === "upscale" ? `${dims.w * 2}×${dims.h * 2}` : `${dims.w}×${dims.h}`),
          when: new Date(date.getTime() + v * 86400000 * (1 + Math.floor(r() * 5))),
          params: vt.type === "crop" ? { box: "0,40,1024,1320" } : vt.type === "upscale" ? { scale: 2, model: "SeedVR2 3B" } : vt.type === "flux_edit" ? { strength: (0.3 + r() * 0.3).toFixed(2), steps: 24 } : null,
        });
      }

      // faces (people in image)
      const faceN = framing === "full_body" && r() < 0.4 ? 2 : 1;
      const faces = [];
      const usedP = new Set();
      for (let f = 0; f < faceN; f++) {
        let fp = f === 0 ? personId : Math.floor(r() * PERSON_DEFS.length);
        if (fp < 0) fp = -1;
        if (usedP.has(fp)) continue;
        usedP.add(fp);
        const cropSeed = "crop" + (i + 1) + "_" + f;
        faces.push({ personId: fp, score: 0.86 + r() * 0.13, age: 19 + Math.floor(r() * 30), scene: fp >= 0 ? PERSON_DEFS[fp].scene : scene, cropUrl: picsum(cropSeed, 80, 80) });
      }

      assets.push({
        id: i + 1,
        personId, scene, source, framing,
        ar: { w, h }, dims, format: pick(r, FORMATS),
        photo: picsum("pf" + (i + 1), photoDims({ w, h }, 480).w, photoDims({ w, h }, 480).h),
        photoLg: picsum("pf" + (i + 1), photoDims({ w, h }, 1100).w, photoDims({ w, h }, 1100).h),
        fileSize: Math.round((dims.w * dims.h) / (source === "original" ? 8 : 6) / 1024) + Math.floor(r() * 200),
        quality, favourite,
        tags, caption: cap, captioner: "Florence-2-base", tagger: "WD14 swinv2-v3",
        versions, versionCount: nv, faces,
        date, periodLabel: period.label,
        generationMeta: source === "flux" ? fluxMeta(r) : source === "sdxl" ? sdxlMeta(r) : null,
        bg: sceneBg(scene, framing, rng(i * 977 + 13)),
      });
    }
    // sort by date desc
    assets.sort((a, b) => b.date - a.date);
    return assets;
  }

  const ASSETS = buildAssets(78);

  // person stats
  const PERSONS = PERSON_DEFS.map((p, idx) => {
    const owned = ASSETS.filter((a) => a.personId === idx);
    return {
      id: idx, name: p.name, scene: p.scene,
      count: owned.length,
      favCount: owned.filter((a) => a.favourite).length,
      portrait: "https://randomuser.me/api/portraits/" + p.g + "/" + p.n + ".jpg",
      avatarBg: sceneBg(p.scene, "close_up", rng(idx * 71 + 5)),
    };
  });
  const UNKNOWN_COUNT = ASSETS.filter((a) => a.personId === -1).length;

  // tag facet counts
  const tagCounts = {};
  ASSETS.forEach((a) => a.tags.forEach((t) => { tagCounts[t.name] = (tagCounts[t.name] || 0) + 1; }));
  const TAG_FACETS = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]).map(([name, count]) => ({ name, count }));

  // small avatar bg for a person (for face chips/tiles)
  function personBg(id) {
    if (id < 0 || !ALL_PEOPLE[id]) return "linear-gradient(135deg, oklch(0.34 0.01 260), oklch(0.22 0.01 260))";
    return sceneBg(ALL_PEOPLE[id].scene, "close_up", rng(id * 71 + 5));
  }
  function personName(id) { return id < 0 || !ALL_PEOPLE[id] ? "Unbekannt" : ALL_PEOPLE[id].name; }
  function personPhoto(id) {
    if (id < 0 || !ALL_PEOPLE[id]) return null;
    const p = ALL_PEOPLE[id];
    return "https://randomuser.me/api/portraits/" + p.g + "/" + p.n + ".jpg";
  }
  // full assignable directory (id, name, photo count in current library)
  const DIRECTORY = ALL_PEOPLE.map((p, idx) => ({
    id: idx, name: p.name, count: ASSETS.filter((a) => a.personId === idx).length,
  }));

  // ---- albums (one unified type; each can be turned "smart" via its gear → auto-fill) ----
  function evalTrigger(a, t) {
    if (t.type === "person") return a.personId === t.personId || a.faces.some((f) => f.personId === t.personId);
    if (t.type === "tag") return a.tags.some((x) => x.name === t.tagName);
    if (t.type === "caption") return (a.caption || "").toLowerCase().includes((t.phrase || "").toLowerCase());
    return false;
  }
  // recompute smart-album membership from triggers (live, like the backend re-eval)
  function matchTriggers(assets, triggers, mode) {
    const pos = triggers.filter((t) => !t.negate);
    const neg = triggers.filter((t) => t.negate);
    if (!pos.length) return [];
    return assets.filter((a) => {
      const ok = mode === "all" ? pos.every((t) => evalTrigger(a, t)) : pos.some((t) => evalTrigger(a, t));
      if (!ok) return false;
      if (neg.length && neg.some((t) => evalTrigger(a, t))) return false;
      return true;
    });
  }

  // manual member lists (curated, deterministic) — the base content of an album
  const kampagne = ASSETS.filter((a) => a.tags.some((t) => t.name === "kampagne herbst")).map((a) => a.id);
  const warm = ASSETS.filter((a) => a.scene === 0 || a.scene === 8).map((a) => a.id);
  const m1ids = [...new Set([...kampagne, ...warm])].slice(0, 15);
  const m2ids = ASSETS.filter((a) => a.favourite).map((a) => a.id).slice(0, 18);
  const m3ids = ASSETS.filter((a) => a.personId === 3).map((a) => a.id).slice(0, 12);
  const lenaPortr = ASSETS.filter((a) => evalTrigger(a, { type: "person", personId: 0 }) && evalTrigger(a, { type: "tag", tagName: "porträt" })).map((a) => a.id);

  // ONE album type. `smart.on` toggles automatic rule-based filling (set via the album's gear).
  // smart.on === true  → members come from the triggers (auto-filled, re-evaluated live)
  // smart.on === false → members are the manual memberIds (hand-picked)
  // Every album carries a smart config so it can be switched on/off at any time.
  const COLLECTIONS = [
    { id: "a1", name: "Lena · Porträts", desc: "Porträtaufnahmen mit Lena.", memberIds: lenaPortr,
      smart: { on: true, mode: "all", triggers: [{ type: "person", personId: 0 }, { type: "tag", tagName: "porträt" }] } },
    { id: "a2", name: "Strand & Sonne", desc: "Strand- und Sonnenuntergangs-Motive.", memberIds: [],
      smart: { on: true, mode: "any", triggers: [{ type: "tag", tagName: "strand" }, { type: "tag", tagName: "sonnenuntergang" }] } },
    { id: "a3", name: "Brillen-Looks", desc: "Alles mit Brille.", memberIds: [],
      smart: { on: true, mode: "any", triggers: [{ type: "tag", tagName: "brille" }] } },
    { id: "a4", name: "Studio-Sessions", desc: "Studio-Aufnahmen, ohne Outdoor.", memberIds: [],
      smart: { on: true, mode: "any", triggers: [{ type: "tag", tagName: "studio" }, { type: "tag", tagName: "outdoor", negate: true }] } },
    { id: "a5", name: "Kampagne Herbst", desc: "Manuell kuratierte Auswahl.", memberIds: m1ids,
      smart: { on: false, mode: "any", triggers: [] } },
    { id: "a6", name: "Best of 2026", desc: "Die stärksten Favoriten des Jahres.", memberIds: m2ids,
      smart: { on: false, mode: "any", triggers: [] } },
    { id: "a7", name: "Felix · Auswahl", desc: "Handverlesene Felix-Shots.", memberIds: m3ids,
      smart: { on: false, mode: "any", triggers: [{ type: "person", personId: 3 }] } },
  ];

  // ---- jobs (live queue) ----
  const JOB_SEED = [
    { id: 1, kind: "tag", name: "Auto-Tagging", sub: "WD14 · 24 Bilder", pct: 38, done: false },
    { id: 2, kind: "face", name: "Face-Extraktion", sub: "buffalo_l · personA", pct: 71, done: false },
    { id: 3, kind: "caption", name: "Caption-Lauf", sub: "Florence-2-base", pct: 12, done: false },
    { id: 4, kind: "download", name: "SeedVR2 3B · fp8", sub: "3,4 GB · Modell-Download", pct: 64, done: false, dl: true },
  ];

  window.PF = {
    ASSETS, PERSONS, UNKNOWN_COUNT, TAG_FACETS, SCENES, DIRECTORY,
    TAGS_AUTO, JOB_SEED, MONTHS, COLLECTIONS,
    personBg, personName, personPhoto, picsum, photoDims, sceneBg, rng,
    evalTrigger, matchTriggers,
    framingLabel: (f) => ({ close_up: "Close-Up", medium: "Medium", full_body: "Ganzkörper" }[f] || f),
    sourceLabel: (s) => ({ original: "Original", sdxl: "SDXL", flux: "Flux" }[s] || s),
  };
})();
