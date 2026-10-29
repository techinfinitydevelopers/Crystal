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

  /* The home page is served at "/" as well as /index.html; both are "index". */
  var file = (location.pathname.split("/").pop() || "index").replace(/\.html?$/i, "");
  var slug = decodeURIComponent(file).trim().toLowerCase().replace(/\s+/g, "-");

  var API = (location.hostname.endsWith(".up.railway.app")?"https://crystal-production-eb2e.up.railway.app":"")+"/api/sections.json";

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

  function applyList(el, lead, bullets) {
    /* Build exactly what the 31 pages that ship this layout already contain:
       a lead paragraph followed by a sibling <ul class="hero-points">, not a
       <ul> nested inside the paragraph. Same DOM means the same CSS applies
       with nothing new to style, and it stays valid markup. */
    el.textContent = lead || "";
    el.classList.add("hero-lead");

    var list = el.nextElementSibling;
    if (!list || !list.hasAttribute("data-cms-list")) {
      list = document.createElement("ul");
      list.setAttribute("data-cms-list", "");
      el.parentNode.insertBefore(list, el.nextSibling);
    }
    list.className = "hero-points";
    /* Rebuilt rather than appended to: the feed can be applied more than once
       on a page, and appending would grow the list each time. */
    list.textContent = "";
    for (var i = 0; i < bullets.length; i++) {
      var li = document.createElement("li");
      li.textContent = bullets[i];
      list.appendChild(li);
    }
  }

  function applyText(el, text, asHtml) {
    var attr = el.getAttribute("data-cms-attr");
    if (attr) { el.setAttribute(attr, text); return; }
    if (asHtml || el.hasAttribute("data-cms-rich")) {
      /* The element ships with markup inside it — a <br> splitting a heading
         over two lines, a <span class="grad"> holding the red half of a
         headline, a <b>, a mailto link. textContent would flatten all of it on
         the first edit, so these 277 elements take the value as HTML.
         The value comes from a signed-in staff user through the dashboard, the
         same trust level as the page's own source.

         `asHtml` is the dashboard saying the same thing about a value the page
         never tagged. data-cms-rich is baked into this file, so without it a
         <br> typed into an ordinary paragraph reached visitors as the literal
         characters "<br>" and only the dashboard could tell otherwise. */
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

  function applyVideo(el, url) {
    /* A dashboard video replaces the file the page ships. load() restarts it
       on the new source; an autoplaying, muted loop is allowed to play again. */
    if (el.getAttribute("src") === url) return;
    var sources = el.querySelectorAll("source");
    for (var i = 0; i < sources.length; i++) sources[i].remove();
    el.src = url;
    try { el.load(); } catch (e) {}
    if (el.autoplay || el.hasAttribute("autoplay")) {
      var p = el.play && el.play();
      if (p && p.catch) p.catch(function () {});
    }
  }

  /* ── Section order ──────────────────────────────────────────────────────
     Bands that may be moved carry data-block="key" and are siblings. The
     dashboard sends the order it wants (and which bands are hidden) only for
     pages where someone changed it. The last answer is remembered, so the next
     visit lays the page out before the feed has even been asked. */
  var ORDER_KEY = "cms-blocks:" + slug;

  function moveTarget(el) {
    /* GSAP wraps a pinned band in a .pin-spacer; that wrapper is what sits
       among the siblings, so it is what has to move. */
    var p = el.parentNode;
    return p && p.classList && p.classList.contains("pin-spacer") ? p : el;
  }

  function applyBlocks(list) {
    if (!list || !list.length) return false;
    var els = {};
    var all = document.querySelectorAll("[data-block]");
    for (var i = 0; i < all.length; i++) els[all[i].getAttribute("data-block")] = all[i];
    var placed = [];
    list.forEach(function (b) { if (els[b.key]) placed.push({ el: els[b.key], show: b.show !== false }); });
    if (placed.length < 2) return false;

    var changed = false;
    placed.forEach(function (p) {
      var hidden = !p.show;
      if (hidden !== p.el.hasAttribute("data-block-hidden")) {
        changed = true;
        if (hidden) { p.el.setAttribute("data-block-hidden", ""); p.el.style.display = "none"; }
        else { p.el.removeAttribute("data-block-hidden"); p.el.style.display = ""; }
      }
    });
    /* Re-insert in the wanted order, anchored where the first band sits now,
       so anything that is not a band (a script, a stray wrapper) stays put. */
    var nodes = placed.map(function (p) { return moveTarget(p.el); });
    var parent = nodes[0].parentNode;
    var current = Array.prototype.filter.call(parent.children, function (n) { return nodes.indexOf(n) !== -1; });
    var same = current.length === nodes.length && current.every(function (n, i) { return n === nodes[i]; });
    if (!same) {
      var marker = document.createComment("blocks");
      parent.insertBefore(marker, current[0]);
      nodes.slice().reverse().forEach(function (n) {
        if (n.parentNode === parent) parent.insertBefore(n, marker.nextSibling);
      });
      parent.removeChild(marker);
      changed = true;
    }
    if (changed && window.ScrollTrigger) {
      try { window.ScrollTrigger.sort && window.ScrollTrigger.sort(); window.ScrollTrigger.refresh(); } catch (e) {}
    }
    return changed;
  }

  try {
    var cached = JSON.parse(localStorage.getItem(ORDER_KEY) || "null");
    if (cached) applyBlocks(cached);
  } catch (e) { /* no storage: wait for the feed */ }

  fetch(API, { mode: "cors", credentials: "omit" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      var pages = data && data.pages;
      if (!pages) return;

      var wanted = data.blocks && data.blocks[slug];
      try {
        if (wanted) localStorage.setItem(ORDER_KEY, JSON.stringify(wanted));
        else localStorage.removeItem(ORDER_KEY);
      } catch (e) {}
      if (wanted) applyBlocks(wanted);
      else if (document.querySelector("[data-block-hidden]")) {
        /* The order was put back in the dashboard: undo what the cached copy hid. */
        var hiddenEls = document.querySelectorAll("[data-block-hidden]");
        for (var h = 0; h < hiddenEls.length; h++) { hiddenEls[h].removeAttribute("data-block-hidden"); hiddenEls[h].style.display = ""; }
      }

      /* The header and footer are the same on every page, so their keys live
         under one pseudo-page rather than being repeated 64 times. Applied
         first, so a page that ever wants its own version of a shared key can
         override it by carrying that key itself. */
      [pages["_site"], pages[slug]].forEach(function (sections) {
        if (!sections) return;
        Object.keys(sections).forEach(function (key) {
          var section = sections[key];
          if (!section) return;
          if (section.kind === "video") {
            if (!section.url) return;
            var vids = document.querySelectorAll('[data-cms-video="' + key.replace(/"/g, '\\"') + '"]');
            for (var v = 0; v < vids.length; v++) applyVideo(vids[v], section.url);
            return;
          }
          var targets = elementsFor(key);
          if (!targets.length) return;
          for (var i = 0; i < targets.length; i++) {
            if (section.kind === "image" && section.url) {
              /* A phone crop, when one was uploaded, on the same breakpoint the
                 pages use for their phone layout. */
              var phone = section.url_mobile && window.matchMedia && window.matchMedia("(max-width: 767px)").matches;
              applyImage(targets[i], phone ? section.url_mobile : section.url);
            }
            else if (section.kind === "text" && section.format === "list" && section.bullets)
              applyList(targets[i], section.lead, section.bullets);
            else if (section.kind === "text" && section.text)
              applyText(targets[i], section.text, section.format === "html");
          }
        });
      });
    })
    .catch(function () { /* the shipped copy stands */ });
})();
