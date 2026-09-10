/* Lets the dashboard change a product's photos without a rebuild.

   Same inversion as banner-sync and content-sync already on these pages: the
   site is static files in git and the dashboard is a separate service with its
   own database, so the dashboard cannot write into product-data/products.json.
   Instead it publishes only the products whose main image was actually chosen
   there, and this script folds them into the catalogue as it is loaded.

   It works by wrapping fetch rather than by touching any page's code: every
   page — the product page, all 46 listing pages, the search overlay — reads
   the same products.json and maps `hero` / `gallery` off each entry, so
   patching the parsed file at that one point covers all of them and leaves
   their rendering exactly as it was.

   Nothing here can hold a page up: the override request is fired at once and
   given a short deadline, and on a timeout, an error, a bad payload or a
   dashboard that is simply down, the shipped catalogue is returned untouched.

   Load it BEFORE the page's own scripts — it has to be in place before the
   first products.json request goes out. */
(function () {
  "use strict";

  var API = "https://crystal-production-eb2e.up.railway.app/api/products/image-overrides.json/";
  var DEADLINE_MS = 2500;

  if (typeof window.fetch !== "function" || typeof window.Response !== "function") return;

  var nativeFetch = window.fetch.bind(window);

  // Kicked off immediately, resolved once, and shared by every products.json
  // request on the page (Product.html makes two: the catalogue and the search
  // overlay). Resolves to null whenever the overrides cannot be trusted.
  var overrides = new Promise(function (resolve) {
    var settled = false;
    function finish(value) { if (!settled) { settled = true; resolve(value); } }
    setTimeout(function () { finish(null); }, DEADLINE_MS);
    nativeFetch(API, { cache: "no-cache" })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (body) {
        var map = body && body.products;
        finish(map && typeof map === "object" ? map : null);
      })
      .catch(function () { finish(null); });
  });

  /* Returns true if anything was actually replaced — no point rebuilding the
     response for a catalogue that came out identical. */
  function applyOverrides(data, map) {
    var list = data && data.products;
    if (!Array.isArray(list)) return false;
    var touched = false;
    for (var i = 0; i < list.length; i++) {
      var entry = list[i];
      var override = entry && map[entry.sku];
      if (!override) continue;
      if (override.hero) { entry.hero = override.hero; touched = true; }
      if (Array.isArray(override.gallery)) { entry.gallery = override.gallery; touched = true; }
    }
    return touched;
  }

  window.fetch = function (input, init) {
    var url = typeof input === "string" ? input : (input && input.url) || "";
    var request = nativeFetch(input, init);
    if (!/product-data\/products\.json/.test(url)) return request;

    return request.then(function (res) {
      if (!res.ok) return res;
      // Read the clone, so the original response is still intact and can be
      // handed back untouched down every failure path below.
      return res.clone().json().then(function (data) {
        return overrides.then(function (map) {
          if (!map || !applyOverrides(data, map)) return res;
          return new Response(JSON.stringify(data), {
            status: res.status,
            statusText: res.statusText,
            headers: { "Content-Type": "application/json" }
          });
        });
      }).catch(function () { return res; });
    });
  };
})();
