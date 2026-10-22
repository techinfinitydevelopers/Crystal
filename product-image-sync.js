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

  var API = (location.hostname.endsWith(".up.railway.app")?"https://crystal-production-eb2e.up.railway.app":"")+"/api/products/image-overrides.json/";
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
        finish({
          products: map,
          added: Array.isArray(body.added) ? body.added : [],
          hidden: Array.isArray(body.hidden) ? body.hidden : [],
          brands: (body.brands && typeof body.brands === "object") ? body.brands : {},
          categories: (body.categories && typeof body.categories === "object") ? body.categories : {}
        });
      })
      .catch(function () { finish(null); });
  });

  /* The line shown under a product's title (its highlight) arrives in whatever
     case it was typed — ALL CAPS, sentence case, or a mix. Every page reads
     products.json through this wrapper, so it is made uniform here, once, for
     the listing cards, the search overlay and the product page alike: each word
     starts with a capital and the rest is lower case. Words holding a digit
     (14CM, 250MM) and the acronyms below keep their capitals. */
  var KEEP_CAPS = { "SS": 1, "S.S": 1, "OTG": 1, "JMG": 1, "LED": 1, "BBQ": 1, "PS": 1, "ABS": 1, "RO": 1, "UV": 1, "USB": 1, "GST": 1 };

  function capWords(text) {
    return String(text == null ? "" : text).replace(/[A-Za-z0-9][A-Za-z0-9.'/&\-]*/g, function (w) {
      var bare = w.replace(/[.,;:!?]+$/, "");
      if (KEEP_CAPS[bare.toUpperCase()]) return bare.toUpperCase() + w.slice(bare.length);
      if (/\d/.test(bare)) return w;
      return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
    });
  }

  /* Returns true if any highlight actually changed. */
  function tidyHighlights(data) {
    var list = data && data.products;
    if (!Array.isArray(list)) return false;
    var changed = false;
    for (var i = 0; i < list.length; i++) {
      var p = list[i];
      if (!p || typeof p.highlight !== "string" || !p.highlight) continue;
      var tidy = capWords(p.highlight);
      if (tidy !== p.highlight) { p.highlight = tidy; changed = true; }
    }
    return changed;
  }

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
  function applyOverrides(data, map, hidden, added) {
    var list = data && data.products;
    if (!Array.isArray(list)) return false;
    var touched = false;

    /* Products created in the dashboard that the catalogue file has never
       listed. Added whole, unless the file already carries that code (the
       file then wins, and the patches below still apply to it). They go to
       the FRONT, newest first as the feed sends them: every listing page's
       default "Featured" order is simply catalogue order, so this is what puts
       a new product at the top of its category page. */
    if (added && added.length) {
      var have = {}, fresh = [];
      for (var a = 0; a < list.length; a++) if (list[a] && list[a].sku) have[list[a].sku] = true;
      for (var n = 0; n < added.length; n++) {
        var item = added[n];
        if (!item || !item.sku || have[item.sku]) continue;
        have[item.sku] = true;
        fresh.push(item);
      }
      if (fresh.length) {
        data.products = list = fresh.concat(list);
        touched = true;
      }
    }

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
        if (key === "removed_photos") continue;   // applied after the merge
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
      /* Photos deleted or replaced in the dashboard. The merge above keeps
         every photo the catalogue file ships, so without this an old photo
         stayed on the site next to its replacement. */
      if (Array.isArray(override.removed_photos) && override.removed_photos.length) {
        var gone = {};
        for (var r = 0; r < override.removed_photos.length; r++) gone[photoKey(override.removed_photos[r])] = true;
        var left = (Array.isArray(entry.gallery) ? entry.gallery : []).filter(function (u) { return !gone[photoKey(u)]; });
        if (entry.hero && gone[photoKey(entry.hero)]) entry.hero = left.shift() || null;
        entry.gallery = left;
        touched = true;
      }
    }
    return touched;
  }

  /* ── Brand and category wording ──────────────────────────────────────────
     Each listing page builds its own BRANDS and CATEGORIES arrays at parse
     time, as consts this script cannot reach. So the pages hand them over
     instead, and the objects inside are patched in place once the feed lands —
     which is before anything renders, because the catalogue request below
     waits on the same promise.

     Only fields somebody edited in the dashboard are in the feed, so a page
     whose wording differs from the database on purpose ("Wooden Range" here,
     "Wood Range" there) is left exactly as it shipped. */
  function patchBySlug(target, map, slugKey) {
    if (!target || !map) return;
    var items = asList(target, slugKey);
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      if (!item || typeof item !== "object") continue;
      var patch = map[item[slugKey]];
      if (!patch) continue;
      for (var key in patch) {
        if (Object.prototype.hasOwnProperty.call(patch, key)) item[key] = patch[key];
      }
    }
  }

  /* Some of this wording is already on the page by the time the feed arrives —
     the brand dropdown and the category chips are built while the page parses,
     long before any fetch resolves. Patching the arrays alone therefore only
     fixes what renders later, so the text already written out is swapped too.

     Deliberately narrow: only an exact, whole-value match of the wording the
     page itself just handed us is replaced, so this can never touch a product
     name or a sentence that merely contains the word. */
  var SWAP_ATTRS = ["data-cat", "data-brand", "title", "alt", "aria-label"];
  var swaps = {};
  var swapKeys = 0;
  var observer = null;

  function swapIn(root) {
    if (!swapKeys || !root) return;
    if (root.nodeType === 3) {
      var t = root.nodeValue;
      var hit = t && swaps[t.trim()];
      if (hit) root.nodeValue = t.replace(t.trim(), hit);
      return;
    }
    if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) return;

    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var node, hits = [];
    while ((node = walker.nextNode())) {
      var value = node.nodeValue;
      if (value && swaps[value.trim()]) hits.push(node);
    }
    for (var i = 0; i < hits.length; i++) {
      var v = hits[i].nodeValue;
      hits[i].nodeValue = v.replace(v.trim(), swaps[v.trim()]);
    }

    var els = root.querySelectorAll ? root.querySelectorAll("*") : [];
    for (var e = 0; e < els.length; e++) {
      for (var a = 0; a < SWAP_ATTRS.length; a++) {
        var av = els[e].getAttribute(SWAP_ATTRS[a]);
        if (av && swaps[av.trim()]) els[e].setAttribute(SWAP_ATTRS[a], swaps[av.trim()]);
      }
    }
  }

  function registerSwap(before, after) {
    if (!before || !after || before === after || swaps[before]) return;
    swaps[before] = after;
    swapKeys++;
  }

  function runSwaps() {
    if (!swapKeys) return;
    swapIn(document.body);
    if (observer || typeof MutationObserver !== "function") return;
    /* The catalogue renders after this, and listing pages re-render on every
       filter click, so new nodes keep arriving. Only the added subtrees are
       walked — re-scanning a 465-card grid on each mutation would not be. */
    observer = new MutationObserver(function (records) {
      for (var i = 0; i < records.length; i++) {
        var added = records[i].addedNodes;
        for (var j = 0; j < added.length; j++) swapIn(added[j]);
      }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  /* The wording as the page shipped it, kept so the swap knows what to look for. */
  function asList(target, slugKey) {
    if (!target) return [];
    if (Array.isArray(target)) return target;
    return Object.keys(target).map(function (k) {
      var v = target[k];
      if (v && typeof v === "object" && v[slugKey] === undefined) v[slugKey] = k;
      return v;
    });
  }

  function snapshot(target, slugKey) {
    var out = {};
    asList(target, slugKey).forEach(function (item) {
      if (item && typeof item === "object") out[item[slugKey]] = JSON.parse(JSON.stringify(item));
    });
    return out;
  }

  function collectSwaps(before, target, slugKey, fields) {
    asList(target, slugKey).forEach(function (item) {
      var was = item && before[item[slugKey]];
      if (!was) return;
      fields.forEach(function (f) {
        if (typeof was[f] === "string" && typeof item[f] === "string") registerSwap(was[f], item[f]);
      });
    });
  }

  window.crystalSync = {
    /* BRANDS is an array of {slug,...} on the listing pages and an object keyed
       by slug on three others; both hold the same objects BRAND_BY reuses, so
       patching in place updates every view of them. */
    brands: function (brands) {
      var before = snapshot(brands, "slug");
      overrides.then(function (feed) {
        if (!feed) return;
        patchBySlug(brands, feed.brands, "slug");
        collectSwaps(before, brands, "slug", ["name", "tagline", "blurb"]);
        runSwaps();
      });
    },
    /* CAT_LABEL is derived from CATEGORIES synchronously at parse time, so it
       has already been built by the time the feed lands and has to be patched
       alongside it. */
    categories: function (categories, labelMap) {
      var before = snapshot(categories, "id");
      overrides.then(function (feed) {
        if (!feed) return;
        patchBySlug(categories, feed.categories, "id");
        collectSwaps(before, categories, "id", ["label", "name"]);
        for (var slug in feed.categories) {
          if (!Object.prototype.hasOwnProperty.call(feed.categories, slug)) continue;
          var label = feed.categories[slug].label;
          if (!label) continue;
          if (labelMap && labelMap[slug] !== undefined) {
            registerSwap(labelMap[slug], label);
            labelMap[slug] = label;
          }
        }
        runSwaps();
      });
    }
  };

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
          var touched = feed ? applyOverrides(data, feed.products || {}, feed.hidden || [], feed.added || []) : false;
          // After the overrides, so products the dashboard adds are tidied too.
          if (tidyHighlights(data)) touched = true;
          if (!touched) return res;
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
