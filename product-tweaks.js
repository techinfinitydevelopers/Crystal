(function () {
  const DEF = /*EDITMODE-BEGIN*/{
    "mood": "light",
    "type": "editorial",
    "accent": "red",
    "secOverview": true,
    "secFeatures": true,
    "secSpecs": true,
    "secGallery": false,
    "secWhy": false,
    "secRelated": true,
    "secBrandStory": false,
    "secMarquee": true,
    "secCTA": false,
    "showCategoryNav": false,
    "showCollections": false,
    "showMarquee": true,
    "showBrandValue": false,
    "showCTA": false,
    "gridCols": "4",
    "showTags": true,
    "radius": 20
  }/*EDITMODE-END*/;
  const LSK = "crystal-pdp-tweaks";
  let vals = Object.assign({}, DEF);
  try { Object.assign(vals, JSON.parse(localStorage.getItem(LSK) || "{}")); } catch (e) {}

  const ACCENTS = {
    red:     { solid: "#ED3338", g: "linear-gradient(135deg,#ED3338 0%,#c0282c 100%)" },
    saffron: { solid: "#E5A817", g: "linear-gradient(135deg,#F0B92E 0%,#c8860b 100%)" },
    maroon:  { solid: "#c0282c", g: "linear-gradient(135deg,#c0282c 0%,#8f1d20 100%)" },
    ink:     { solid: "#1A1A1A", g: "linear-gradient(135deg,#2c2c2c 0%,#0f0f0f 100%)" },
  };
  const root = document.documentElement, body = document.body;
  const SECMAP = { secOverview:"#overview", secFeatures:"#features", secSpecs:"#specs", secGallery:"#gallery", secWhy:"#why", secRelated:"#related", secBrandStory:"#brandstory", secMarquee:"#marquee", secCTA:"#cta" };
  function reveal(el) {
    if (!window.gsap || !el) return;
    gsap.set(el.querySelectorAll('[data-fade], [data-split] .word, .feat-card, .why-card, .rcard, .spec-row, .lg-item'), { clearProps: "opacity,transform,x,y,xPercent,yPercent,scale,clipPath" });
  }
  let rT;
  const refresh = () => { clearTimeout(rT); rT = setTimeout(() => { if (window.ScrollTrigger) ScrollTrigger.refresh(); }, 140); };

  function apply(initial) {
    body.classList.remove("t-warm", "t-noir");
    if (vals.mood === "warm") body.classList.add("t-warm");
    else if (vals.mood === "noir") body.classList.add("t-noir");
    body.classList.remove("tv-editorial", "tv-bold");
    if (vals.type === "editorial") body.classList.add("tv-editorial");
    else if (vals.type === "bold") body.classList.add("tv-bold");
    const a = ACCENTS[vals.accent] || ACCENTS.red;
    root.style.setProperty("--red", a.solid);
    root.style.setProperty("--grad-red", a.g);
    Object.keys(SECMAP).forEach(k => {
      const el = document.querySelector(SECMAP[k]);
      if (!el) return;
      const on = !!vals[k];
      el.style.display = on ? "" : "none";
      if (on && !initial) reveal(el);
    });
    refresh();
  }

  function syncUI() {
    document.querySelectorAll("#twkMood button").forEach(b => b.classList.toggle("on", b.dataset.mood === vals.mood));
    document.querySelectorAll("#twkType button").forEach(b => b.classList.toggle("on", b.dataset.type === vals.type));
    document.querySelectorAll("#twkAccent button").forEach(b => b.classList.toggle("on", b.dataset.acc === vals.accent));
    document.querySelectorAll('.twk-tg input[data-sec]').forEach(inp => { inp.checked = !!vals[inp.dataset.sec]; });
  }
  function save() {
    try { localStorage.setItem(LSK, JSON.stringify(vals)); } catch (e) {}
    try { window.parent.postMessage({ type: "__edit_mode_set_keys", edits: vals }, "*"); } catch (e) {}
  }
  function set(k, v) { vals[k] = v; save(); apply(false); syncUI(); }

  document.getElementById("twkAccent").innerHTML = Object.keys(ACCENTS).map(k => `<button data-acc="${k}" title="${k}" style="background:${ACCENTS[k].solid}"></button>`).join("");
  document.getElementById("twkMood").addEventListener("click", e => { const b = e.target.closest("button"); if (b) set("mood", b.dataset.mood); });
  document.getElementById("twkType").addEventListener("click", e => { const b = e.target.closest("button"); if (b) set("type", b.dataset.type); });
  document.getElementById("twkAccent").addEventListener("click", e => { const b = e.target.closest("button"); if (b) set("accent", b.dataset.acc); });
  document.querySelectorAll('.twk-tg input[data-sec]').forEach(inp => inp.addEventListener("change", () => set(inp.dataset.sec, inp.checked)));

  const panel = document.getElementById("twkPanel");
  addEventListener("message", e => { const t = e && e.data && e.data.type; if (t === "__activate_edit_mode") panel.classList.add("open"); else if (t === "__deactivate_edit_mode") panel.classList.remove("open"); });
  document.getElementById("twkClose").addEventListener("click", () => { panel.classList.remove("open"); try { window.parent.postMessage({ type: "__edit_mode_dismissed" }, "*"); } catch (e) {} });
  try { window.parent.postMessage({ type: "__edit_mode_available" }, "*"); } catch (e) {}

  apply(true);
  syncUI();
})();
