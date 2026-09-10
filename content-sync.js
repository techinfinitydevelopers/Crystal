/* Lets the dashboard override this page's hero text without a rebuild.
   Same inversion as the banner-sync script already on this page: the site is
   static files in git and the dashboard is a separate service with its own
   database, so the dashboard cannot write into the site. The page ships its
   own copy and asks the dashboard, on load, whether a newer value has been
   set for each section key; if so it swaps it in. If the dashboard is down
   or has nothing for this page, the shipped copy stands. Nothing here is
   awaited before paint. */
(function () {
  "use strict";

  var file = (location.pathname.split("/").pop() || "").replace(/\.html?$/i, "");
  if (!file) return;
  var slug = decodeURIComponent(file).trim().toLowerCase().replace(/\s+/g, "-");

  var API = "https://crystal-production-eb2e.up.railway.app/api/sections.json";

  // section_key -> element. Only keys present here can be edited from the
  // dashboard; a page adds more by extending this map.
  var TARGETS = {
    "hero-pretext": document.getElementById("heroPreTxt"),
    "hero-title": document.getElementById("heroTitle"),
    "hero-title-2": document.getElementById("heroTitle2"),
    "hero-sub": document.getElementById("heroSub"),
    "about-title": document.getElementById("aboutTitle"),
    "about-text": document.getElementById("aboutText"),
    "about-image": document.getElementById("aboutImg"),
  };

  fetch(API, { mode: "cors", credentials: "omit" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      var sections = data && data.pages && data.pages[slug];
      if (!sections) return;

      Object.keys(sections).forEach(function (key) {
        var el = TARGETS[key];
        if (!el) return;
        var s = sections[key];
        if (s.kind === "image" && s.url) {
          if (el.tagName === "IMG") el.src = s.url;
          else el.style.backgroundImage = "url(" + s.url + ")";
        } else if (s.kind === "text" && s.text) {
          el.textContent = s.text;
        }
      });
    })
    .catch(function () { /* the shipped copy stands */ });
})();
