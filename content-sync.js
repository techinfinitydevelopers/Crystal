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
    "cta-title": document.getElementById("ctaTitle"),
    "cta-sub": document.getElementById("ctaSub"),

    // About.html's two stat rows.
    "stat-years-num": document.getElementById("statYearsNum"),
    "stat-years-lbl": document.getElementById("statYearsLbl"),
    "stat-people-num": document.getElementById("statPeopleNum"),
    "stat-people-lbl": document.getElementById("statPeopleLbl"),
    "stat-skus-num": document.getElementById("statSkusNum"),
    "stat-skus-lbl": document.getElementById("statSkusLbl"),
    "stat-customers-num": document.getElementById("statCustomersNum"),
    "stat-customers-lbl": document.getElementById("statCustomersLbl"),
    "stat-offices-num": document.getElementById("statOfficesNum"),
    "stat-offices-lbl": document.getElementById("statOfficesLbl"),
    "stat-units-num": document.getElementById("statUnitsNum"),
    "stat-units-lbl": document.getElementById("statUnitsLbl"),
    "stat-warehouses-num": document.getElementById("statWarehousesNum"),
    "stat-warehouses-lbl": document.getElementById("statWarehousesLbl"),
    "stat-outlets-num": document.getElementById("statOutletsNum"),
    "stat-outlets-lbl": document.getElementById("statOutletsLbl"),
    "stat-factory-num": document.getElementById("statFactoryNum"),
    "stat-factory-lbl": document.getElementById("statFactoryLbl"),

    // Home (index.html / index-v2.html): CTA's second line, and its three
    // stat rows (Who We Are, Infrastructure, Our Brands).
    "cta-title-2": document.getElementById("ctaTitle2"),
    "about-stat-years-num": document.getElementById("aboutStatYearsNum"),
    "about-stat-years-lbl": document.getElementById("aboutStatYearsLbl"),
    "about-stat-employees-num": document.getElementById("aboutStatEmployeesNum"),
    "about-stat-employees-lbl": document.getElementById("aboutStatEmployeesLbl"),
    "about-stat-products-num": document.getElementById("aboutStatProductsNum"),
    "about-stat-products-lbl": document.getElementById("aboutStatProductsLbl"),
    "about-stat-customers-num": document.getElementById("aboutStatCustomersNum"),
    "about-stat-customers-lbl": document.getElementById("aboutStatCustomersLbl"),
    "infra-offices-num": document.getElementById("infraOfficesNum"),
    "infra-offices-lbl": document.getElementById("infraOfficesLbl"),
    "infra-units-num": document.getElementById("infraUnitsNum"),
    "infra-units-lbl": document.getElementById("infraUnitsLbl"),
    "infra-warehouses-num": document.getElementById("infraWarehousesNum"),
    "infra-warehouses-lbl": document.getElementById("infraWarehousesLbl"),
    "infra-outlets-num": document.getElementById("infraOutletsNum"),
    "infra-outlets-lbl": document.getElementById("infraOutletsLbl"),
    "infra-factory-num": document.getElementById("infraFactoryNum"),
    "infra-factory-lbl": document.getElementById("infraFactoryLbl"),
    "brand-stat-years-num": document.getElementById("brandStatYearsNum"),
    "brand-stat-years-lbl": document.getElementById("brandStatYearsLbl"),
    "brand-stat-outlets-num": document.getElementById("brandStatOutletsNum"),
    "brand-stat-outlets-lbl": document.getElementById("brandStatOutletsLbl"),
    "brand-stat-skus-num": document.getElementById("brandStatSkusNum"),
    "brand-stat-skus-lbl": document.getElementById("brandStatSkusLbl"),
    "brand-stat-people-num": document.getElementById("brandStatPeopleNum"),
    "brand-stat-people-lbl": document.getElementById("brandStatPeopleLbl"),
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
          // A stat's counted number: update the attribute the count-up
          // animation reads too, so a value set before the animation fires
          // still lands on the right number, not the shipped default. Two
          // different count-up scripts exist on this site, reading
          // data-count and data-target respectively.
          if (el.hasAttribute("data-count")) el.setAttribute("data-count", s.text);
          if (el.hasAttribute("data-target")) el.setAttribute("data-target", s.text);
        }
      });
    })
    .catch(function () { /* the shipped copy stands */ });
})();
