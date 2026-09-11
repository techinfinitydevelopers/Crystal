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
        if (!map || typeof map !== "object") return finish(null);
        finish({ products: map, hidden: Array.isArray(body.hidden) ? body.hidden : [] });
      })
      .catch(function () { finish(null); });
  });

  /* The same photo reaches us written two ways — the catalogue stores
     "product-photos/CC-850/g2.jpg", the dashboard publishes it absolute — so
     compare on the path alone. */
  function photoKey(url) {
    return String(url || "").replace(/^https?:\/\/[^/]+/, "").replace(/^\/+/, "");
  }

  /* Photos are merged; everything else the dashboard publishes simply wins. */
  function applyPhotos(entry, override) {
    /* Promote the chosen photo, keep every other one.

       The dashboard only holds the photos it knows about — for an imported
       product that is often just the uploaded file and the old hero, while the
       catalogue carries the full strip. Assigning override.gallery straight
       over entry.gallery therefore used to drop the rest: CC-850 went from
       eight thumbnails to one. So the gallery is rebuilt as the union instead,
       catalogue order first, and the photo being promoted is the only one
       taken out of it. */
    var seen = {}, gallery = [];
    var keep = [entry.hero].concat(
      Array.isArray(entry.gallery) ? entry.gallery : [],
      Array.isArray(override.gallery) ? override.gallery : []
    );
    var heroKey = photoKey(override.hero);
    for (var j = 0; j < keep.length; j++) {
      var url = keep[j];
      if (!url) continue;
      var key = photoKey(url);
      if (key === heroKey || seen[key]) continue;
      seen[key] = true;
      gallery.push(url);
    }
    entry.hero = override.hero;
    entry.gallery = gallery;
  }

  /* Returns true if anything was actually replaced — no point rebuilding the
     response for a catalogue that came out identical. */
  function applyOverrides(data, map, hidden) {
    var list = data && data.products;
    if (!Array.isArray(list)) return false;
    var touched = false;

    /* Products removed in the dashboard. The catalogue file still lists them —
       it is in git and the dashboard cannot edit it — so dropping them here is
       what actually takes them off the site. Done first, so nothing below
       bothers patching an entry that is about to go. */
    if (hidden && hidden.length) {
      var drop = {};
      for (var h = 0; h < hidden.length; h++) drop[hidden[h]] = true;
      var kept = [];
      for (var k = 0; k < list.length; k++) {
        if (list[k] && drop[list[k].sku]) touched = true;
        else kept.push(list[k]);
      }
      if (touched) data.products = list = kept;
    }

    for (var i = 0; i < list.length; i++) {
      var entry = list[i];
      var override = entry && map[entry.sku];
      if (!override) continue;
      for (var key in override) {
        if (!Object.prototype.hasOwnProperty.call(override, key)) continue;
        if (key === "gallery") continue;          // handled with the hero
        if (key === "hero") {
          if (!override.hero) continue;
          applyPhotos(entry, override);
        } else {
          entry[key] = override[key];
        }
        touched = true;
      }
      /* A gallery edit that did not move the hero still has to land. */
      if (!override.hero && Array.isArray(override.gallery)) {
        entry.gallery = override.gallery;
        touched = true;
      }
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
        return overrides.then(function (feed) {
          if (!feed) return res;
          if (!applyOverrides(data, feed.products || {}, feed.hidden || [])) return res;
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
