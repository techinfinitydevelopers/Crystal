/* Festival themes (Diwali, Holi, Christmas...) switched on from the dashboard.

   Same inversion as content-sync.js: the site is static files and the
   dashboard a separate service. Every page loads this file; it asks
   /api/theme.json which theme is live (at most one) and dresses the page:

     - data-festival="<slug>" on <html>, and festival-theme.css injected
     - a slim greeting ribbon between the red support bar and the header
       (the header moves down by the ribbon's height while it shows, and the
       ribbon tucks away once the visitor scrolls)
     - a decorative garland hanging under the ribbon, a festive band on top
       of the footer, festival colours on button hovers
     - light falling particles if the theme has effects on
     - on the Home page, a greeting badge in the hero (+ a card if the theme
       has a banner picture)

   The answer is kept in localStorage so the next page paints the theme with
   no wait, then refreshed. Dashboard down or no answer = the normal site.

   ?theme=<slug> previews a theme for this visitor only (kept for the tab's
   session as they click around); ?theme=off stops previewing. Nothing about
   a preview reaches the dashboard. */
(function () {
  "use strict";

  if (window.__crystalFestival) return;
  window.__crystalFestival = true;

  var ONRAILWAY = location.hostname.endsWith(".up.railway.app");
  var API = (ONRAILWAY ? "https://crystal-production-eb2e.up.railway.app" : "") + "/api/theme.json";
  var KEY = "crystal-festival";
  var PKEY = "crystal-festival-preview";
  var DKEY = "crystal-festival-hidden";
  var MAX_STALE = 3 * 24 * 3600 * 1000;   // a cached theme with no refresh for 3 days is dropped

  var me = document.currentScript;
  var CSS_URL = (function () {
    var src = me && me.src ? me.src : "festival-theme.js";
    return src.replace(/festival-theme\.js(\?[^#]*)?/, function (_, q) { return "festival-theme.css" + (q || ""); });
  })();

  function store(kind) { try { return window[kind]; } catch (e) { return null; } }
  function get(kind, k) { try { var s = store(kind); return s ? s.getItem(k) : null; } catch (e) { return null; } }
  function put(kind, k, v) { try { var s = store(kind); if (s) { if (v == null) s.removeItem(k); else s.setItem(k, v); } } catch (e) {} }

  /* ── Built-in looks. The dashboard sends the words; the look lives here. ─ */
  var P = {
    "diwali": { icon: "diya", garland: "lights", fx: "spark", accent: "#E9A23B",
      fxColors: ["#FFD36E", "#FFB938", "#FF8A3D", "#FFF1C1"],
      greeting: "Happy Diwali from Crystal!", sub: "May your home glow with light, warmth and good food." },
    "holi": { icon: "splash", garland: "splash", fx: "powder", accent: "#E3367A",
      fxColors: ["#E3367A", "#F08A24", "#F5C518", "#2FB36B", "#2F7BE3", "#9C36B5"],
      greeting: "Happy Holi from Crystal!", sub: "Wishing you a season full of colour, laughter and sweets." },
    "navratri": { icon: "dandiya", garland: "toran", fx: "petal", accent: "#E8590C",
      fxColors: ["#F08C00", "#FFB703", "#E8590C", "#D6336C"],
      greeting: "Happy Navratri & Dussehra from Crystal!", sub: "Nine nights of devotion, dandiya and festive feasts." },
    "ganesh-chaturthi": { icon: "marigold", garland: "toran", fx: "petal", accent: "#F28C1B",
      fxColors: ["#F08C00", "#FFB703", "#E03131"],
      greeting: "Happy Ganesh Chaturthi from Crystal!", sub: "Ganpati Bappa Morya! Wishing your home wisdom and prosperity." },
    "raksha-bandhan": { icon: "rakhi", garland: "rakhi", fx: "petal", accent: "#D6336C",
      fxColors: ["#F783AC", "#E64980", "#FCC419", "#FFD8E4"],
      greeting: "Happy Raksha Bandhan from Crystal!", sub: "Celebrating the bond that holds a family together." },
    "janmashtami": { icon: "feather", garland: "peacock", fx: "feather", accent: "#1C7ED6",
      fxColors: ["#2E9E6E", "#1C7ED6", "#E9B949"],
      greeting: "Happy Janmashtami from Crystal!", sub: "May Kanha fill your home with joy and makhan-mishri." },
    "independence-day": { icon: "flag", garland: "bunting", fx: "petal", accent: "#FF9933",
      fxColors: ["#FF9933", "#FFFFFF", "#138808"],
      greeting: "Happy Independence Day from Crystal!", sub: "Celebrating the spirit of a free India." },
    "republic-day": { icon: "flag", garland: "bunting", fx: "petal", accent: "#FF9933",
      fxColors: ["#FF9933", "#FFFFFF", "#138808"],
      greeting: "Happy Republic Day from Crystal!", sub: "Saluting the spirit of our Constitution." },
    "sankranti": { icon: "kite", garland: "kites", fx: "kite", accent: "#1098AD",
      fxColors: ["#F03E3E", "#FAB005", "#1C7ED6", "#37B24D", "#AE3EC9"],
      greeting: "Happy Sankranti, Pongal & Lohri!", sub: "May the harvest season fill every kitchen with abundance." },
    "onam": { icon: "flower", garland: "pookalam", fx: "petal", accent: "#E0A100",
      fxColors: ["#F59F00", "#E8590C", "#FFFFFF", "#7B2CBF"],
      greeting: "Happy Onam from Crystal!", sub: "Wishing you a sadya-full season of joy and togetherness." },
    "eid": { icon: "crescent", garland: "lanterns", fx: "twinkle", accent: "#0E8A66",
      fxColors: ["#F5D98B", "#E9C46A", "#FFF3C4"],
      greeting: "Eid Mubarak from Crystal!", sub: "Wishing you peace, joy and feasts shared with loved ones." },
    "christmas": { icon: "tree", garland: "holly", fx: "snow", accent: "#C92A2A",
      fxColors: ["#FFFFFF"],
      greeting: "Merry Christmas from Crystal!", sub: "Warm wishes for a season of togetherness and good food." },
    "new-year": { icon: "sparkle", garland: "confetti", fx: "confetti", accent: "#D4AF37",
      fxColors: ["#D4AF37", "#F1D27A", "#C0C6CC", "#ED3338"],
      greeting: "Happy New Year from Crystal!", sub: "Here is to a year of great meals and greater company." }
  };
  var GENERIC = { icon: "sparkle", garland: "confetti", fx: "confetti", accent: "#D4AF37",
    fxColors: ["#D4AF37", "#F1D27A", "#ED3338"], greeting: "Season's greetings from Crystal!", sub: "" };

  /* ── Drawings: inline SVG only, no images. ─────────────────────────────── */
  var ICONS = {
    diya: '<path d="M2.5 13.5h19c-.8 4.2-4.6 7-9.5 7s-8.7-2.8-9.5-7z" fill="currentColor"/><path d="M12 2.5c2.2 3 3.2 5 3.2 6.9a3.2 3.2 0 0 1-6.4 0c0-1.9 1-3.9 3.2-6.9z" fill="#FFB938"/><path d="M12 6.5c.9 1.3 1.3 2.2 1.3 3a1.3 1.3 0 0 1-2.6 0c0-.8.4-1.7 1.3-3z" fill="#FFF1C1"/>',
    splash: '<circle cx="8" cy="9" r="5" fill="#E3367A"/><circle cx="15.5" cy="8" r="4.2" fill="#F5C518"/><circle cx="12.5" cy="15.5" r="5" fill="#2F7BE3" fill-opacity=".9"/><circle cx="18" cy="15" r="2.6" fill="#2FB36B"/><circle cx="5" cy="17" r="1.8" fill="#F08A24"/>',
    dandiya: '<path d="M5 20 18 4M19 20 6 4" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" fill="none"/><path d="M15.4 7.2l2 1.6M8.6 7.2l-2 1.6" stroke="#FFB703" stroke-width="2.4" stroke-linecap="round"/>',
    marigold: '<circle cx="12" cy="12" r="9" fill="#F08C00"/><circle cx="12" cy="12" r="9" fill="none" stroke="#C85D00" stroke-width="1.4" stroke-dasharray="1.6 1.6"/><circle cx="12" cy="12" r="5.5" fill="#FFB703"/><circle cx="12" cy="12" r="2.2" fill="#C85D00"/>',
    rakhi: '<path d="M1 12h22" stroke="#E64980" stroke-width="2"/><g fill="#FCC419"><circle cx="12" cy="6.5" r="3"/><circle cx="12" cy="17.5" r="3"/><circle cx="6.5" cy="12" r="3"/><circle cx="17.5" cy="12" r="3"/></g><circle cx="12" cy="12" r="4" fill="#E64980"/><circle cx="12" cy="12" r="1.7" fill="#FFF3BF"/>',
    feather: '<path d="M12 23V12" stroke="currentColor" stroke-width="1.4"/><ellipse cx="12" cy="9" rx="6" ry="8" fill="#2E9E6E"/><ellipse cx="12" cy="9.6" rx="3.9" ry="5.4" fill="#1C7ED6"/><ellipse cx="12" cy="10" rx="2" ry="2.8" fill="#0B2E59"/><ellipse cx="12" cy="9.6" rx="3.9" ry="5.4" fill="none" stroke="#E9B949" stroke-width=".9"/>',
    flag: '<path d="M4 2v20" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><rect x="5" y="4" width="16" height="4" fill="#FF9933"/><rect x="5" y="8" width="16" height="4" fill="#fff"/><rect x="5" y="12" width="16" height="4" fill="#138808"/><circle cx="13" cy="10" r="1.5" fill="none" stroke="#0B3D91" stroke-width=".8"/>',
    kite: '<path d="M12 2l7 9-7 10-7-10z" fill="#F03E3E"/><path d="M12 2l7 9H5z" fill="#FAB005"/><path d="M12 2v19M5 11h14" stroke="#7a2a00" stroke-width=".8"/><path d="M12 21c-1 1.2 1 1.6 0 2.6" stroke="currentColor" stroke-width="1" fill="none"/>',
    flower: '<circle cx="12" cy="12" r="10" fill="#F59F00"/><circle cx="12" cy="12" r="7.4" fill="#E8590C"/><circle cx="12" cy="12" r="5" fill="#fff"/><circle cx="12" cy="12" r="2.8" fill="#7B2CBF"/>',
    crescent: '<path d="M14.5 3.2A9 9 0 1 0 20.8 16 7.2 7.2 0 1 1 14.5 3.2z" fill="currentColor"/><path d="M18.5 5.5l.8 1.8 1.9.2-1.4 1.3.4 1.9-1.7-1-1.7 1 .4-1.9-1.4-1.3 1.9-.2z" fill="currentColor"/>',
    tree: '<path d="M12 3l6 8h-3l4.5 6h-15L9 11H6z" fill="#2B8A3E"/><rect x="10.8" y="17" width="2.4" height="4" fill="#8B5A2B"/><path d="M12 .8l.9 1.9 2 .2-1.5 1.4.4 2-1.8-1-1.8 1 .4-2-1.5-1.4 2-.2z" fill="#FCC419"/><circle cx="10" cy="13" r="1" fill="#E03131"/><circle cx="14.5" cy="15" r="1" fill="#FCC419"/>',
    sparkle: '<path d="M12 1.5l2.3 7.2 7.2 2.3-7.2 2.3L12 20.5l-2.3-7.2L2.5 11l7.2-2.3z" fill="currentColor"/><circle cx="19.5" cy="19" r="1.6" fill="currentColor"/>'
  };
  function icon(name, cls) {
    return '<svg class="' + (cls || "fest-ico") + '" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' + (ICONS[name] || ICONS.sparkle) + "</svg>";
  }

  // Garland tiles that repeat along the bottom of the ribbon (and the footer top).
  var G = {
    lights: [108, 26, "<defs><radialGradient id='g'><stop offset='0' stop-color='#FFE9A8' stop-opacity='.95'/><stop offset='1' stop-color='#FFB938' stop-opacity='0'/></radialGradient></defs><path d='M0 2 Q18 12 36 2 Q54 12 72 2 Q90 12 108 2' fill='none' stroke='#4a2e14' stroke-opacity='.6'/>" +
      "<circle cx='18' cy='14' r='9' fill='url(#g)'/><rect x='16.6' y='6' width='2.8' height='3' rx='.6' fill='#6b4a1f'/><ellipse cx='18' cy='13' rx='3' ry='4.4' fill='#FFC94D'/>" +
      "<circle cx='54' cy='14' r='9' fill='url(#g)'/><rect x='52.6' y='6' width='2.8' height='3' rx='.6' fill='#6b4a1f'/><ellipse cx='54' cy='13' rx='3' ry='4.4' fill='#FF8A3D'/>" +
      "<circle cx='90' cy='14' r='9' fill='url(#g)'/><rect x='88.6' y='6' width='2.8' height='3' rx='.6' fill='#6b4a1f'/><ellipse cx='90' cy='13' rx='3' ry='4.4' fill='#FFE7A3'/>"],
    toran: [60, 26, "<path d='M0 1.5H60' stroke='#8a5a12' stroke-width='1.4'/>" +
      "<g stroke='#B35500' stroke-width='.8' stroke-dasharray='1.1 1.1'><circle cx='15' cy='6.5' r='3.6' fill='#F08C00'/><circle cx='15' cy='13.4' r='3.6' fill='#FFB703'/><circle cx='15' cy='20.3' r='3.6' fill='#F08C00'/></g>" +
      "<path d='M45 1.5C51 6 50.5 13 45 19 39.5 13 39 6 45 1.5Z' fill='#2F7D32'/><path d='M45 3v14' stroke='#A9D18E' stroke-width='.7'/>"],
    splash: [150, 18, "<g fill-opacity='.85'><circle cx='10' cy='3' r='5' fill='#E3367A'/><circle cx='22' cy='8' r='2.2' fill='#E3367A'/><circle cx='40' cy='2' r='6' fill='#F5C518'/><circle cx='52' cy='10' r='2.5' fill='#F08A24'/><circle cx='70' cy='4' r='5' fill='#2FB36B'/><circle cx='80' cy='12' r='1.6' fill='#2FB36B'/><circle cx='98' cy='3' r='6.5' fill='#2F7BE3'/><circle cx='110' cy='11' r='2' fill='#9C36B5'/><circle cx='126' cy='2' r='5' fill='#F08A24'/><circle cx='140' cy='9' r='2.4' fill='#E3367A'/><circle cx='32' cy='13' r='1.2' fill='#2F7BE3'/><circle cx='88' cy='15' r='1.1' fill='#F5C518'/></g>"],
    bunting: [60, 20, "<path d='M0 1.5 Q30 5 60 1.5' fill='none' stroke='#555' stroke-opacity='.55'/><path d='M4 2.3H16L10 16Z' fill='#FF9933'/><path d='M24 3.3H36L30 17Z' fill='#fff' stroke='#c8c8c8' stroke-width='.6'/><circle cx='30' cy='7.5' r='2' fill='none' stroke='#0B3D91' stroke-width='.7'/><path d='M44 2.3H56L50 16Z' fill='#138808'/>"],
    rakhi: [140, 22, "<path d='M0 5 Q17.5 1 35 5 T70 5 T105 5 T140 5' fill='none' stroke='#E64980' stroke-width='1.6'/><path d='M0 5 Q17.5 9 35 5 T70 5 T105 5 T140 5' fill='none' stroke='#FCC419' stroke-width='1.1'/>" +
      "<path d='M66 8v9M74 8v9' stroke='#E64980' stroke-width='.9'/><circle cx='66' cy='18' r='1.6' fill='#FCC419'/><circle cx='74' cy='18' r='1.6' fill='#FCC419'/>" +
      "<g fill='#FCC419'><circle cx='70' cy='1.6' r='2.6'/><circle cx='70' cy='10.4' r='2.6'/><circle cx='65.6' cy='6' r='2.6'/><circle cx='74.4' cy='6' r='2.6'/></g><circle cx='70' cy='6' r='3.2' fill='#E64980'/><circle cx='70' cy='6' r='1.3' fill='#FFF3BF'/>"],
    peacock: [72, 28, "<path d='M0 1.5H72' stroke='#0B2E59' stroke-opacity='.5'/><path d='M18 1.5v6' stroke='#2E9E6E'/><ellipse cx='18' cy='15' rx='5.2' ry='7.6' fill='#2E9E6E'/><ellipse cx='18' cy='15.6' rx='3.4' ry='5' fill='#1C7ED6'/><ellipse cx='18' cy='16' rx='1.7' ry='2.5' fill='#0B2E59'/><ellipse cx='18' cy='15.6' rx='3.4' ry='5' fill='none' stroke='#E9B949' stroke-width='.8'/>" +
      "<path d='M51 1.5 49 9M57 1.5 59 9' stroke='#8A4B14' stroke-width='.7'/><ellipse cx='54' cy='16' rx='6.5' ry='5.6' fill='#B5651D'/><rect x='49.5' y='9' width='9' height='3' rx='1' fill='#8A4B14'/><ellipse cx='54' cy='9.4' rx='3.6' ry='1.5' fill='#FFF8E1'/><path d='M48.5 16h11' stroke='#E9B949' stroke-width='.9'/>"],
    kites: [84, 26, "<path d='M0 2 Q42 8 84 2' fill='none' stroke='#555' stroke-opacity='.5' stroke-width='.7'/>" +
      "<path d='M21 4l6 7-6 9-6-9z' fill='#F03E3E'/><path d='M21 4l6 7H15z' fill='#FAB005'/><path d='M21 20c-1.5 1.4 1.5 2.4 0 4' fill='none' stroke='#F03E3E' stroke-width='.8'/>" +
      "<path d='M63 5l6 7-6 9-6-9z' fill='#1C7ED6'/><path d='M63 5v16' stroke='#fff' stroke-width='.8'/><path d='M63 21c-1.5 1.4 1.5 2.4 0 4' fill='none' stroke='#1C7ED6' stroke-width='.8'/>"],
    pookalam: [44, 20, "<path d='M0 1H44' stroke='#C9A227' stroke-width='1.2'/><circle cx='22' cy='10' r='7.6' fill='#F59F00'/><circle cx='22' cy='10' r='5.6' fill='#E8590C'/><circle cx='22' cy='10' r='3.7' fill='#fff'/><circle cx='22' cy='10' r='2' fill='#7B2CBF'/><path d='M6 8c3-3 6-1 6 2-3 1-5 0-6-2zM38 8c-3-3-6-1-6 2 3 1 5 0 6-2z' fill='#2F9E44'/>"],
    lanterns: [96, 32, "<path d='M0 1.5H96' stroke='#C9A227' stroke-opacity='.7'/><path d='M24 1.5v7M72 1.5v4' stroke='#C9A227' stroke-width='.7'/>" +
      "<path d='M20 8.5h8l-1 2h-6z' fill='#C9A227'/><path d='M20.5 10.5h7l2 4-2 9h-7l-2-9z' fill='#FFD36E' fill-opacity='.9' stroke='#B8860B' stroke-width='.8'/><path d='M24 10.5v13M18.5 14.5h11' stroke='#B8860B' stroke-width='.5'/><path d='M21 23.5h6l-3 3z' fill='#C9A227'/>" +
      "<path d='M73 6a6 6 0 1 0 5.4 8.6 4.7 4.7 0 1 1-5.4-8.6z' fill='#E9C46A'/><path d='M80.5 6.5l.6 1.4 1.5.1-1.1 1 .3 1.5-1.3-.8-1.3.8.3-1.5-1.1-1 1.5-.1z' fill='#E9C46A'/>"],
    holly: [64, 22, "<path d='M0 3 Q16 9 32 3 T64 3' fill='none' stroke='#1B5E33' stroke-width='1.6'/>" +
      "<path d='M16 7c-4-1-7 1-9 4 3 0 4 1 4 3 2-2 4-3 5-7z' fill='#2B8A3E'/><path d='M16 7c4-1 7 1 9 4-3 0-4 1-4 3-2-2-4-3-5-7z' fill='#237032'/><circle cx='15' cy='8.5' r='2' fill='#E03131'/><circle cx='18' cy='9' r='1.8' fill='#C92A2A'/><circle cx='16.5' cy='11.2' r='1.8' fill='#E03131'/>" +
      "<circle cx='48' cy='9' r='2.2' fill='#FCC419'/><circle cx='48' cy='9' r='4.5' fill='#FCC419' fill-opacity='.18'/><rect x='47' y='4.6' width='2' height='2.4' fill='#555'/>"],
    confetti: [120, 18, "<g><rect x='6' y='2' width='3' height='6' rx='.6' fill='#D4AF37' transform='rotate(20 7.5 5)'/><circle cx='22' cy='9' r='1.6' fill='#ED3338'/><rect x='34' y='3' width='3' height='6' rx='.6' fill='#C0C6CC' transform='rotate(-30 35.5 6)'/><path d='M50 4l1 2.4 2.4 1-2.4 1-1 2.4-1-2.4-2.4-1 2.4-1z' fill='#D4AF37'/><rect x='64' y='8' width='3' height='6' rx='.6' fill='#ED3338' transform='rotate(45 65.5 11)'/><circle cx='78' cy='4' r='1.4' fill='#D4AF37'/><rect x='90' y='2' width='3' height='6' rx='.6' fill='#F1D27A' transform='rotate(-15 91.5 5)'/><circle cx='104' cy='11' r='1.5' fill='#C0C6CC'/><path d='M114 6l.8 1.8 1.8.8-1.8.8-.8 1.8-.8-1.8-1.8-.8 1.8-.8z' fill='#ED3338'/></g>"]
  };
  function garlandCss(name) {
    var g = G[name] || G.confetti;
    var svg = "<svg xmlns='http://www.w3.org/2000/svg' width='" + g[0] + "' height='" + g[1] + "' viewBox='0 0 " + g[0] + " " + g[1] + "'>" + g[2] + "</svg>";
    // drawn at 80%: hangs a little way into the (transparent) header, never far
    return { image: 'url("data:image/svg+xml,' + encodeURIComponent(svg) + '")', w: Math.round(g[0] * 0.8), h: Math.round(g[1] * 0.8) };
  }

  /* ── Where are we ──────────────────────────────────────────────────────── */
  function isHome() {
    var p = location.pathname.replace(/\/+$/, "/");
    return p === "/" || /\/(index|index-v2)(\.html?)?$/i.test(p);
  }
  function today() {
    var d = new Date();
    return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  }
  function inWindow(t) {
    var d = today();
    if (t.starts_on && d < t.starts_on) return false;
    if (t.ends_on && d > t.ends_on) return false;
    return true;
  }
  var reduced = false;
  try { reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}

  /* ── Which theme ───────────────────────────────────────────────────────── */
  var qs = (function () { try { return new URLSearchParams(location.search); } catch (e) { return null; } })();
  var q = qs ? (qs.get("theme") || "").trim().toLowerCase() : "";
  if (q === "off" || q === "none" || q === "0") { put("sessionStorage", PKEY, null); q = ""; }
  else if (q && /^[a-z0-9-]{1,40}$/.test(q)) {
    put("sessionStorage", PKEY, JSON.stringify({ slug: q, t: null }));
    put("sessionStorage", DKEY, null);
  } else q = "";
  var preview = null;
  try { preview = JSON.parse(get("sessionStorage", PKEY) || "null"); } catch (e) { preview = null; }

  function fallbackFor(slug) {
    var p = P[slug] || GENERIC;
    return { slug: slug, name: slug, greeting: p.greeting, sub_text: p.sub, link_text: "", link_url: "",
      effects: true, scope: "site", accent: "", banner: null, starts_on: null, ends_on: null };
  }

  var current = null;   // the theme drawn now, as JSON, so a refresh that changes nothing does nothing

  function choose(t) {
    if (!t || !t.slug) return null;
    if (!preview && !inWindow(t)) return null;
    if (t.scope === "home" && !isHome()) return null;
    return t;
  }

  /* ── Drawing ───────────────────────────────────────────────────────────── */
  var root = document.documentElement;
  var els = [];          // everything we added, for a clean teardown
  var cleanups = [];
  var cssLink = null;

  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function safeHref(u) {
    u = String(u || "").trim();
    if (!u) return "";
    if (/^(https?:)?\/\//i.test(u) || /^[\w./#?=&%-]+$/.test(u)) return u;
    return "";
  }

  function teardown() {
    cleanups.forEach(function (f) { try { f(); } catch (e) {} });
    cleanups = [];
    els.forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
    els = [];
    root.removeAttribute("data-festival");
    root.classList.remove("fest-on", "fest-rib-on", "fest-rib-up");
    root.style.removeProperty("--fest-accent");
    root.style.removeProperty("--fest-top");
    root.style.removeProperty("--fest-rib-h");
    var h = document.querySelector(".fest-hdr");
    if (h) h.classList.remove("fest-hdr");
  }

  function loadCss(done) {
    if (cssLink && cssLink.__ready) return done(true);
    if (!cssLink) {
      cssLink = document.createElement("link");
      cssLink.rel = "stylesheet";
      cssLink.href = CSS_URL;
      cssLink.__waiters = [];
      cssLink.onload = function () { cssLink.__ready = true; cssLink.__waiters.forEach(function (f) { f(true); }); cssLink.__waiters = []; };
      cssLink.onerror = function () { cssLink.__waiters.forEach(function (f) { f(false); }); cssLink.__waiters = []; };
      document.head.appendChild(cssLink);
    }
    cssLink.__waiters.push(done);
  }

  function findHeader() {
    var h = document.getElementById("hdr");
    if (h && h.tagName === "HEADER") return h;
    var all = document.getElementsByTagName("header");
    for (var i = 0; i < all.length; i++) {
      if (getComputedStyle(all[i]).position === "fixed") return all[i];
    }
    return null;
  }

  function apply(t) {
    var key = t ? JSON.stringify(t) : "";
    if (key === current) return;
    current = key;
    teardown();
    if (!t) return;
    var preset = P[t.slug] || GENERIC;
    root.setAttribute("data-festival", P[t.slug] ? t.slug : "generic");
    root.classList.add("fest-on");
    if (t.accent && /^#[0-9a-f]{6}$/i.test(t.accent)) root.style.setProperty("--fest-accent", t.accent);

    loadCss(function (ok) {
      if (!ok || current !== key) return;
      draw(t, preset);
    });
  }

  function draw(t, preset) {
    var gl = garlandCss(preset.garland);
    var body = document.body;
    var greeting = t.greeting || preset.greeting;
    var sub = t.sub_text || "";
    var href = safeHref(t.link_url);
    var hidden = get("sessionStorage", DKEY) === t.slug;

    /* Ribbon + garland + spacer */
    var header = findHeader();
    if (!hidden) {
      var rib = el("div", "fest-rib");
      rib.setAttribute("role", "region");
      rib.setAttribute("aria-label", "Festive greeting");
      rib.setAttribute("translate", "yes");
      rib.innerHTML =
        '<div class="fest-rib-in">' + icon(preset.icon) +
        '<span class="fest-msg"><b class="fest-greet">' + esc(greeting) + "</b>" +
        (sub ? '<span class="fest-sub">' + esc(sub) + "</span>" : "") + "</span>" +
        (t.link_text && href ? '<a class="fest-cta" href="' + esc(href) + '">' + esc(t.link_text) + ' <span aria-hidden="true">&rarr;</span></a>' : "") +
        "</div>" +
        '<button type="button" class="fest-x" aria-label="Hide the greeting" translate="no">' +
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg></button>';
      var garland = el("div", "fest-garland");
      garland.setAttribute("aria-hidden", "true");
      garland.style.backgroundImage = gl.image;
      garland.style.backgroundSize = gl.w + "px " + gl.h + "px";
      garland.style.height = gl.h + "px";
      var spacer = el("div", "fest-spacer");
      spacer.setAttribute("aria-hidden", "true");

      body.insertBefore(spacer, body.firstChild);
      body.appendChild(garland);
      body.appendChild(rib);
      els.push(spacer, garland, rib);

      if (header) header.classList.add("fest-hdr");

      var place = function () {
        // Straight under the support bar; never lower than where the header starts.
        var sb = document.querySelector(".support-bar");
        var top = sb ? sb.getBoundingClientRect().height : 0;
        if (header) {
          var hTop = parseFloat(getComputedStyle(header).top);
          if (hTop >= 0 && (!sb || hTop < top)) top = hTop;
        }
        root.style.setProperty("--fest-top", top + "px");
        root.style.setProperty("--fest-rib-h", rib.offsetHeight + "px");
      };
      place();
      root.classList.add("fest-rib-on");
      // Transitions only from here on: the first paint must not slide the header.
      var animT = setTimeout(function () { root.classList.add("fest-anim"); }, 500);
      cleanups.push(function () { clearTimeout(animT); root.classList.remove("fest-anim"); });
      var onResize = function () { place(); };
      addEventListener("resize", onResize, { passive: true });
      cleanups.push(function () { removeEventListener("resize", onResize); });

      // Tuck away once the visitor scrolls, back at the top of the page.
      var up = false;
      var onScroll = function () {
        var y = window.pageYOffset || document.documentElement.scrollTop || 0;
        if (!up && y > 140) { up = true; root.classList.add("fest-rib-up"); }
        else if (up && y < 60) { up = false; root.classList.remove("fest-rib-up"); }
      };
      addEventListener("scroll", onScroll, { passive: true });
      cleanups.push(function () { removeEventListener("scroll", onScroll); });
      onScroll();

      rib.querySelector(".fest-x").addEventListener("click", function () {
        put("sessionStorage", DKEY, t.slug);
        root.classList.remove("fest-rib-on", "fest-rib-up");
        [spacer, garland, rib].forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
        if (header) header.classList.remove("fest-hdr");
        stopFx();
        refreshScroll();
      });
      refreshScroll();
    }

    /* Footer band */
    var foot = document.querySelector("footer");
    if (foot) {
      var band = el("div", "fest-foot");
      band.setAttribute("aria-hidden", "true");
      band.style.backgroundImage = gl.image;
      band.style.backgroundSize = gl.w + "px " + gl.h + "px";
      band.style.height = gl.h + "px";
      if (getComputedStyle(foot).position === "static") {
        foot.style.position = "relative";
        cleanups.push(function () { foot.style.position = ""; });
      }
      foot.insertBefore(band, foot.firstChild);
      els.push(band);
    }

    /* Home hero */
    if (isHome()) drawHero(t, preset, greeting, sub);

    /* Preview chip */
    if (preview) {
      var chip = el("div", "fest-chip");
      chip.setAttribute("translate", "no");
      var label = t.name && t.name !== t.slug ? t.name
        : t.slug.replace(/-/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); });
      chip.title = "Only you see this theme. Visitors see whatever the dashboard has switched on.";
      chip.innerHTML = "Preview: <b>" + esc(label) + "</b>" +
        '<a href="' + esc(location.pathname + "?theme=off") + '">Exit</a>';
      body.appendChild(chip);
      els.push(chip);
    }

    /* Particles */
    if (t.effects !== false && !hidden) startFx(preset.fx, preset.fxColors);
  }

  function drawHero(t, preset, greeting, sub) {
    var host = document.querySelector(".hero3-txt") || document.querySelector(".hero-v2 .wrap") || document.querySelector(".hero .wrap");
    if (!host) return;
    var banner = t.banner && /^https?:\/\//i.test(t.banner) ? t.banner : "";
    var badge = el("div", "fest-badge");
    badge.setAttribute("translate", "yes");
    badge.innerHTML = (banner ? '<img class="fest-badge-img" src="' + esc(banner) + '" alt="">' : icon(preset.icon, "fest-badge-ico")) +
      '<span class="fest-badge-txt">' + esc(greeting) + "</span>";
    host.insertBefore(badge, host.firstChild);
    els.push(badge);

    var hero = host.closest(".hero3, .hero-v2, .hero, section");
    if (!hero || !banner) return;
    var card = el("figure", "fest-card");
    card.setAttribute("translate", "yes");
    card.innerHTML = '<img src="' + esc(banner) + '" alt="" loading="lazy" decoding="async">' +
      "<figcaption><b>" + esc(greeting) + "</b>" + (sub ? "<span>" + esc(sub) + "</span>" : "") + "</figcaption>";
    var img = card.querySelector("img");
    img.onerror = function () { if (card.parentNode) card.parentNode.removeChild(card); };
    hero.appendChild(card);
    els.push(card);
  }

  function refreshScroll() {
    // Home's pinned sections measured the page before the spacer existed.
    try { if (window.ScrollTrigger && window.ScrollTrigger.refresh) window.ScrollTrigger.refresh(); } catch (e) {}
  }
  addEventListener("load", function () { if (current) refreshScroll(); });

  /* ── Particles: one canvas, capped, paused when hidden, never clickable. ─ */
  var fx = null;
  function stopFx() { if (fx) { fx.stop(); fx = null; } }

  function startFx(kind, colors) {
    stopFx();
    if (reduced || !kind) return;
    var cv = el("canvas", "fest-fx");
    cv.setAttribute("aria-hidden", "true");
    document.body.appendChild(cv);
    els.push(cv);
    var ctx = cv.getContext("2d");
    if (!ctx) return;
    var W = 0, H = 0, dpr = 1, raf = 0, last = 0, running = true, parts = [];
    var small = Math.min(innerWidth, innerHeight || innerWidth) < 600;
    var BASE = { spark: 30, powder: 22, petal: 22, snow: 46, confetti: 30, twinkle: 26, kite: 7, feather: 9 }[kind] || 20;
    var N = Math.round(BASE * (small ? 0.5 : 1));

    function rnd(a, b) { return a + Math.random() * (b - a); }
    function pick() { return colors[(Math.random() * colors.length) | 0]; }
    function size() {
      dpr = Math.min(2, window.devicePixelRatio || 1);
      W = innerWidth; H = innerHeight;
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    function make(initial) {
      var p = { x: rnd(0, W), y: initial ? rnd(0, H) : -20, c: pick(), r: rnd(0, Math.PI * 2), vr: rnd(-1.2, 1.2),
        ph: rnd(0, Math.PI * 2), a: 1 };
      switch (kind) {
        case "spark": p.y = initial ? rnd(0, H) : H + 10; p.s = rnd(1, 2.3); p.vy = -rnd(14, 34); p.vx = rnd(-6, 6); break;
        case "snow": p.s = rnd(1.4, 3.6); p.vy = rnd(18, 42); p.vx = rnd(-8, 8); break;
        case "powder": p.s = rnd(3, 9); p.vy = rnd(10, 22); p.vx = rnd(-10, 10); p.a = rnd(0.22, 0.42); break;
        case "petal": p.s = rnd(3.5, 6); p.vy = rnd(22, 46); p.vx = rnd(-12, 12); break;
        case "confetti": p.s = rnd(3, 5); p.vy = rnd(30, 60); p.vx = rnd(-14, 14); p.vr = rnd(-4, 4); break;
        case "twinkle": p.y = rnd(0, H); p.s = rnd(2, 4.5); p.vy = rnd(2, 6); p.vx = 0; break;
        case "kite": p.y = initial ? rnd(0, H) : H + 30; p.s = rnd(7, 11); p.vy = -rnd(10, 20); p.vx = rnd(6, 16); break;
        case "feather": p.s = rnd(6, 9); p.vy = rnd(14, 26); p.vx = rnd(-6, 6); p.vr = rnd(-0.6, 0.6); break;
      }
      return p;
    }
    function star(x, y, s) {
      ctx.beginPath();
      ctx.moveTo(x, y - s); ctx.lineTo(x + s * 0.28, y - s * 0.28); ctx.lineTo(x + s, y);
      ctx.lineTo(x + s * 0.28, y + s * 0.28); ctx.lineTo(x, y + s); ctx.lineTo(x - s * 0.28, y + s * 0.28);
      ctx.lineTo(x - s, y); ctx.lineTo(x - s * 0.28, y - s * 0.28); ctx.closePath(); ctx.fill();
    }
    function drawP(p, tm) {
      ctx.globalAlpha = p.a;
      ctx.fillStyle = p.c;
      switch (kind) {
        case "spark":
          var f = 0.55 + 0.45 * Math.sin(tm * 6 + p.ph);
          ctx.globalAlpha = 0.18 * f; ctx.beginPath(); ctx.arc(p.x, p.y, p.s * 3.2, 0, 7); ctx.fill();
          ctx.globalAlpha = 0.9 * f; ctx.beginPath(); ctx.arc(p.x, p.y, p.s, 0, 7); ctx.fill();
          break;
        case "snow":
          ctx.globalAlpha = 0.9; ctx.beginPath(); ctx.arc(p.x, p.y, p.s, 0, 7); ctx.fill();
          ctx.globalAlpha = 0.35; ctx.strokeStyle = "#8aa2bd"; ctx.lineWidth = 0.6; ctx.stroke();
          break;
        case "powder":
          ctx.beginPath(); ctx.arc(p.x, p.y, p.s, 0, 7); ctx.fill();
          break;
        case "petal":
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.scale(1, 0.55 + 0.45 * Math.abs(Math.sin(tm * 1.6 + p.ph)));
          ctx.globalAlpha = 0.85; ctx.beginPath(); ctx.ellipse(0, 0, p.s, p.s * 0.55, 0, 0, 7); ctx.fill();
          if (p.c.toUpperCase() === "#FFFFFF") { ctx.strokeStyle = "rgba(120,120,120,.45)"; ctx.lineWidth = 0.6; ctx.stroke(); }
          ctx.restore();
          break;
        case "confetti":
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.scale(1, Math.cos(tm * 3 + p.ph));
          ctx.globalAlpha = 0.85; ctx.fillRect(-p.s / 2, -p.s, p.s, p.s * 2); ctx.restore();
          break;
        case "twinkle":
          ctx.globalAlpha = 0.25 + 0.6 * Math.max(0, Math.sin(tm * 1.4 + p.ph)); star(p.x, p.y, p.s);
          break;
        case "kite":
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(Math.sin(tm + p.ph) * 0.25);
          ctx.globalAlpha = 0.8; ctx.beginPath(); ctx.moveTo(0, -p.s); ctx.lineTo(p.s * 0.75, 0); ctx.lineTo(0, p.s * 1.15); ctx.lineTo(-p.s * 0.75, 0); ctx.closePath(); ctx.fill();
          ctx.strokeStyle = "rgba(60,60,60,.45)"; ctx.lineWidth = 0.7; ctx.beginPath(); ctx.moveTo(0, p.s * 1.15);
          ctx.quadraticCurveTo(-4, p.s * 1.6, 2, p.s * 2.2); ctx.stroke(); ctx.restore();
          break;
        case "feather":
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r);
          ctx.globalAlpha = 0.75; ctx.strokeStyle = "#2E9E6E"; ctx.lineWidth = 0.8; ctx.beginPath(); ctx.moveTo(0, p.s * 0.9); ctx.lineTo(0, p.s * 2.2); ctx.stroke();
          ctx.fillStyle = "#2E9E6E"; ctx.beginPath(); ctx.ellipse(0, 0, p.s * 0.62, p.s, 0, 0, 7); ctx.fill();
          ctx.fillStyle = "#1C7ED6"; ctx.beginPath(); ctx.ellipse(0, p.s * 0.08, p.s * 0.4, p.s * 0.64, 0, 0, 7); ctx.fill();
          ctx.fillStyle = "#0B2E59"; ctx.beginPath(); ctx.ellipse(0, p.s * 0.12, p.s * 0.2, p.s * 0.3, 0, 0, 7); ctx.fill();
          ctx.restore();
          break;
      }
    }
    function step(now) {
      if (!running) return;
      raf = requestAnimationFrame(step);
      var dt = last ? Math.min(0.05, (now - last) / 1000) : 0.016;
      last = now;
      var tm = now / 1000;
      ctx.clearRect(0, 0, W, H);
      for (var i = 0; i < parts.length; i++) {
        var p = parts[i];
        p.x += (p.vx + Math.sin(tm * 0.9 + p.ph) * 8) * dt;
        p.y += p.vy * dt;
        p.r += p.vr * dt;
        var gone = kind === "spark" || kind === "kite" ? p.y < -40 : p.y > H + 30;
        if (gone || p.x < -60 || p.x > W + 60) parts[i] = make(false);
        drawP(parts[i], tm);
      }
      ctx.globalAlpha = 1;
    }
    function play() { if (!running) { running = true; last = 0; raf = requestAnimationFrame(step); } }
    function pause() { running = false; cancelAnimationFrame(raf); }
    function onVis() { if (document.hidden) pause(); else play(); }
    var onSize = function () { size(); };

    size();
    for (var i = 0; i < N; i++) parts.push(make(true));
    raf = requestAnimationFrame(step);
    document.addEventListener("visibilitychange", onVis);
    addEventListener("resize", onSize, { passive: true });

    fx = {
      stop: function () {
        pause();
        document.removeEventListener("visibilitychange", onVis);
        removeEventListener("resize", onSize);
        if (cv.parentNode) cv.parentNode.removeChild(cv);
      }
    };
    cleanups.push(stopFx);
  }

  /* ── Go ────────────────────────────────────────────────────────────────── */
  function fromFeed(data) {
    return data && typeof data === "object" && data.theme && typeof data.theme === "object" ? data.theme : null;
  }

  function start() {
    if (preview) {
      // Paint the preview at once from what we know, then ask the dashboard for its words.
      apply(choose(preview.t || fallbackFor(preview.slug)));
      fetch(API + "?preview=" + encodeURIComponent(preview.slug), { mode: "cors", credentials: "omit", cache: "no-store" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (data) {
          var t = fromFeed(data);
          if (!t) return;
          preview.t = t;
          put("sessionStorage", PKEY, JSON.stringify(preview));
          apply(choose(t));
        })
        .catch(function () {});
      return;
    }

    var cached = null;
    try { cached = JSON.parse(get("localStorage", KEY) || "null"); } catch (e) { cached = null; }
    if (cached && cached.at && Date.now() - cached.at < MAX_STALE) apply(choose(cached.t));

    fetch(API, { mode: "cors", credentials: "omit" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        if (!data || typeof data !== "object" || !("theme" in data)) throw new Error("shape");
        var t = fromFeed(data);
        put("localStorage", KEY, JSON.stringify({ t: t, at: Date.now() }));
        apply(choose(t));
      })
      .catch(function () { /* dashboard down: keep whatever is showing (cached or the normal site) */ });
  }

  if (document.body) start();
  else document.addEventListener("DOMContentLoaded", start);
})();
