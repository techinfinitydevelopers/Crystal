/* Lets the dashboard edit this page's text and images without a rebuild.

   Same inversion as the banner-sync script already on this page: the site is
   static files in git and the dashboard is a separate service with its own
   database, so the dashboard cannot write into the site. The page ships its
   own copy and asks the dashboard, on load, whether a newer value has been
   set for each of its section keys; if so it swaps it in. If the dashboard is
   down or has nothing for this page, the shipped copy stands. Nothing here is
   awaited before paint.

   ── How an element becomes editable ──────────────────────────────────────
   Put `data-cms="some-key"` on it. That is the whole contract: this script
   finds every [data-cms] on the page and matches it against the keys the
   dashboard holds for this page. Adding a new editable section is an HTML
   attribute and nothing else — no list to keep in step here, which is what
   the old hard-coded TARGETS map turned into as pages were added.

   An element may also carry `data-cms-attr="alt"` to say that the value
   belongs in that attribute rather than in the element's text.

   ── The legacy ids ───────────────────────────────────────────────────────
   Before data-cms, 54 keys were wired by element id. Those ids are still on
   the pages and still work: LEGACY_IDS maps them, and it is consulted only
   for keys no [data-cms] claims. It can be deleted once every page carries
   the attributes. */
(function () {
  "use strict";

  var file = (location.pathname.split("/").pop() || "").replace(/\.html?$/i, "");
  if (!file) return;
  var slug = decodeURIComponent(file).trim().toLowerCase().replace(/\s+/g, "-");

  var API = "https://crystal-production-eb2e.up.railway.app/api/sections.json";

  // key -> element id, for pages that predate data-cms. Only used as a
  // fallback; an element carrying the key as data-cms always wins.
  var LEGACY_IDS = {
    "hero-pretext": "heroPreTxt",
    "hero-title": "heroTitle",
    "hero-title-2": "heroTitle2",
    "hero-sub": "heroSub",
    "about-title": "aboutTitle",
    "about-text": "aboutText",
    "about-image": "aboutImg",
    "cta-title": "ctaTitle",
    "cta-title-2": "ctaTitle2",
    "cta-sub": "ctaSub",

    // About.html's stat rows.
    "stat-years-num": "statYearsNum",
    "stat-years-lbl": "statYearsLbl",
    "stat-people-num": "statPeopleNum",
    "stat-people-lbl": "statPeopleLbl",
    "stat-skus-num": "statSkusNum",
    "stat-skus-lbl": "statSkusLbl",
    "stat-customers-num": "statCustomersNum",
    "stat-customers-lbl": "statCustomersLbl",
    "stat-offices-num": "statOfficesNum",
    "stat-offices-lbl": "statOfficesLbl",
    "stat-units-num": "statUnitsNum",
    "stat-units-lbl": "statUnitsLbl",
    "stat-warehouses-num": "statWarehousesNum",
    "stat-warehouses-lbl": "statWarehousesLbl",
    "stat-outlets-num": "statOutletsNum",
    "stat-outlets-lbl": "statOutletsLbl",
    "stat-factory-num": "statFactoryNum",
    "stat-factory-lbl": "statFactoryLbl",

    // Home's three stat rows.
    "about-stat-years-num": "aboutStatYearsNum",
    "about-stat-years-lbl": "aboutStatYearsLbl",
    "about-stat-employees-num": "aboutStatEmployeesNum",
    "about-stat-employees-lbl": "aboutStatEmployeesLbl",
    "about-stat-products-num": "aboutStatProductsNum",
    "about-stat-products-lbl": "aboutStatProductsLbl",
    "about-stat-customers-num": "aboutStatCustomersNum",
    "about-stat-customers-lbl": "aboutStatCustomersLbl",
    "infra-offices-num": "infraOfficesNum",
    "infra-offices-lbl": "infraOfficesLbl",
    "infra-units-num": "infraUnitsNum",
    "infra-units-lbl": "infraUnitsLbl",
    "infra-warehouses-num": "infraWarehousesNum",
    "infra-warehouses-lbl": "infraWarehousesLbl",
    "infra-outlets-num": "infraOutletsNum",
    "infra-outlets-lbl": "infraOutletsLbl",
    "infra-factory-num": "infraFactoryNum",
    "infra-factory-lbl": "infraFactoryLbl",
    "brand-stat-years-num": "brandStatYearsNum",
    "brand-stat-years-lbl": "brandStatYearsLbl",
    "brand-stat-outlets-num": "brandStatOutletsNum",
    "brand-stat-outlets-lbl": "brandStatOutletsLbl",
    "brand-stat-skus-num": "brandStatSkusNum",
    "brand-stat-skus-lbl": "brandStatSkusLbl",
    "brand-stat-people-num": "brandStatPeopleNum",
    "brand-stat-people-lbl": "brandStatPeopleLbl"
  };

  function elementsFor(key) {
    /* Every element claiming this key. A key may legitimately appear more
       than once — the same heading is repeated in a mobile and a desktop
       copy on several pages — so all of them are updated, not just one. */
    var found = [];
    try {
      var nodes = document.querySelectorAll('[data-cms="' + key.replace(/"/g, '\\"') + '"]');
      for (var i = 0; i < nodes.length; i++) found.push(nodes[i]);
    } catch (e) { /* a key with odd characters: fall through to the id */ }
    if (found.length) return found;
    var legacy = LEGACY_IDS[key] && document.getElementById(LEGACY_IDS[key]);
    return legacy ? [legacy] : [];
  }

  function applyText(el, text) {
    var attr = el.getAttribute("data-cms-attr");
    if (attr) { el.setAttribute(attr, text); return; }
    if (el.hasAttribute("data-cms-rich")) {
      /* The element ships with markup inside it — a <br> splitting a heading
         over two lines, a <span class="grad"> holding the red half of a
         headline, a <b>, a mailto link. textContent would flatten all of it on
         the first edit, so these 277 elements take the value as HTML.
         The value comes from a signed-in staff user through the dashboard, the
         same trust level as the page's own source. */
      el.innerHTML = text;
      return;
    }
    el.textContent = text;
    /* A stat's counted number: update the attribute the count-up animation
       reads too, so a value set before the animation fires still lands on the
       right number, not the shipped default. Two different count-up scripts
       exist on this site, reading data-count and data-target respectively. */
    if (el.hasAttribute("data-count")) el.setAttribute("data-count", text);
    if (el.hasAttribute("data-target")) el.setAttribute("data-target", text);
  }

  function applyImage(el, url) {
    var attr = el.getAttribute("data-cms-attr");
    if (attr) { el.setAttribute(attr, url); return; }
    if (el.tagName === "IMG") {
      /* A <picture> puts a <source> in front of the <img>; left in place it
         wins and the swap is invisible. Same rule the banner sync follows. */
      var picture = el.parentNode;
      if (picture && picture.tagName === "PICTURE") {
        var sources = picture.querySelectorAll("source");
        for (var i = 0; i < sources.length; i++) sources[i].remove();
      }
      el.removeAttribute("srcset");
      el.src = url;
      return;
    }
    el.style.backgroundImage = "url(" + url + ")";
  }

  fetch(API, { mode: "cors", credentials: "omit" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      var pages = data && data.pages;
      if (!pages) return;

      /* The header and footer are the same on every page, so their keys live
         under one pseudo-page rather than being repeated 64 times. Applied
         first, so a page that ever wants its own version of a shared key can
         override it by carrying that key itself. */
      [pages["_site"], pages[slug]].forEach(function (sections) {
        if (!sections) return;
        Object.keys(sections).forEach(function (key) {
          var section = sections[key];
          if (!section) return;
          var targets = elementsFor(key);
          if (!targets.length) return;
          for (var i = 0; i < targets.length; i++) {
            if (section.kind === "image" && section.url) applyImage(targets[i], section.url);
            else if (section.kind === "text" && section.text) applyText(targets[i], section.text);
          }
        });
      });
    })
    .catch(function () { /* the shipped copy stands */ });
})();
