/* Features the super admin has switched off stop showing on the website too.

   In the dashboard, Super admin control hides a feature (a sidebar group or item such as
   "Gifting", "Blog", "Awards") from the admins. When that is switched off for everyone, a feature
   that nobody can edit any more must not stay on the public site either. This script asks the
   dashboard which features are off (/api/features.json) and removes them from the page:

     gifting  the Gifting menu/footer links, and the /Gifting page itself becomes "Page not found"
     blog     the Knowledge Centre links, and Blog / Article / /blog/... become "Page not found"
     awards   the Awards & Recognition strip on About

   (Festival themes and category banners are switched off at the source: their own feeds answer
   "no theme" / "no banners" when their feature is off, so there is nothing to hide here.)

   The answer is kept in localStorage so the next page applies it before anything is painted. If
   the dashboard cannot be reached the last known answer stands; with none, the page is left alone,
   so the site never depends on the dashboard being up. Hiding uses an attribute, not removal, so a
   feature switched back on comes back without a reload. */
(function () {
  "use strict";

  var KEY = "crystalFeaturesOff";
  var LOCAL = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
  var API = (location.hostname.endsWith(".up.railway.app") ? "https://crystal-production-eb2e.up.railway.app"
    : LOCAL ? "http://localhost:8000" : "") + "/api/features.json";

  // Never run inside the not-found page we put on screen ourselves.
  if (window.__featuresNotFound || document.querySelector("section.nf")) return;

  var path = decodeURIComponent(location.pathname).toLowerCase();
  var file = (path.split("/").pop() || "").replace(/\.html?$/, "");

  /* name -> which dashboard keys turn it off, where it shows up, what to hide */
  var FEATURES = {
    gifting: {
      keys: ["gifting", "gifting.giftset"],
      isPage: function () { return file === "gifting"; },
      link: function (href) { return /(^|\/)gifting(\.html)?($|[?#])/i.test(href); }
    },
    blog: {
      keys: ["blog", "blog.blog"],
      isPage: function () { return file === "blog" || file === "article" || /^\/blog\//.test(path); },
      link: function (href) { return /(^|\/)(blog|article)(\.html)?($|[?#])/i.test(href) || /(^|\/)blog\/[^/]+/i.test(href); }
    },
    awards: {
      keys: ["awards", "awards.award"],
      isPage: function () { return false; },
      link: function () { return false; },
      blocks: ['section[data-block="awards"]']
    }
  };

  var style = document.createElement("style");
  style.textContent = "[data-feature-off]{display:none !important}";
  (document.head || document.documentElement).appendChild(style);

  function readCache() {
    try { var v = JSON.parse(localStorage.getItem(KEY) || "null"); return Array.isArray(v) ? v : null; } catch (e) { return null; }
  }
  function writeCache(list) { try { localStorage.setItem(KEY, JSON.stringify(list)); } catch (e) { /* private mode */ } }

  var off = {};            // feature name -> true
  function compute(list) {
    var set = {}; (list || []).forEach(function (k) { set[k] = true; });
    off = {};
    Object.keys(FEATURES).forEach(function (name) {
      if (FEATURES[name].keys.some(function (k) { return set[k]; })) off[name] = true;
    });
  }

  function hrefOf(a) { return (a.getAttribute("href") || ""); }

  function sweep(root) {
    Object.keys(FEATURES).forEach(function (name) {
      var f = FEATURES[name], on = !off[name];
      // links: take the whole menu/footer item when the link sits in one
      (root.querySelectorAll ? root : document).querySelectorAll("a[href]").forEach(function (a) {
        if (!f.link(hrefOf(a))) return;
        var target = a.closest("li") || a;
        if (on) { target.removeAttribute("data-feature-off"); a.removeAttribute("data-feature-off"); }
        else target.setAttribute("data-feature-off", name);
      });
      (f.blocks || []).forEach(function (sel) {
        document.querySelectorAll(sel).forEach(function (el) {
          if (on) el.removeAttribute("data-feature-off"); else el.setAttribute("data-feature-off", name);
        });
      });
    });
  }

  /* The address itself belongs to a switched-off feature: show the site's "Page not found". */
  function notFound() {
    if (window.__featuresNotFound) return;
    window.__featuresNotFound = true;
    document.documentElement.style.visibility = "hidden";
    fetch("/404.html", { cache: "no-cache" }).then(function (r) { return r.ok ? r.text() : Promise.reject(); })
      .then(function (html) {
        document.open(); document.write(html); document.close();
        document.documentElement.style.visibility = "";
      })
      .catch(function () {
        document.documentElement.style.visibility = "";
        document.body.innerHTML = '<p style="padding:120px 20px;text-align:center;font:600 18px sans-serif">Page not found.</p>';
      });
  }

  function onPageOff() {
    return Object.keys(off).some(function (name) { return FEATURES[name].isPage(); });
  }

  /* The page being "off" comes either from the last visit's answer (cache) or from the dashboard just now.
     A cached "off" is held (page hidden, never replaced) until the dashboard confirms it, for at most 1.5 s,
     so a feature switched back on is not stuck behind a stale answer. */
  var confirmed = false, holdTimer = null;
  function release() { document.documentElement.style.visibility = ""; clearTimeout(holdTimer); }
  function apply() {
    if (onPageOff()) {
      if (confirmed) { release(); notFound(); return; }
      document.documentElement.style.visibility = "hidden";
      if (!holdTimer) holdTimer = setTimeout(function () { confirmed = true; apply(); }, 1500);
      return;
    }
    release();
    sweep(document);
  }

  // 1) what we knew from the last page: applied before the first paint
  var cached = readCache();
  if (cached) { compute(cached); apply(); }

  // 2) anything the page builds later (blog teasers, search results...)
  if (typeof MutationObserver === "function") {
    var timer = null;
    new MutationObserver(function () {
      if (!Object.keys(off).length) return;
      clearTimeout(timer); timer = setTimeout(function () { sweep(document); }, 120);
    }).observe(document.documentElement, { childList: true, subtree: true });
  }

  // 3) what the dashboard says now
  var ctl = typeof AbortController === "function" ? new AbortController() : null;
  var t = setTimeout(function () { if (ctl) ctl.abort(); }, 4000);
  fetch(API, { mode: "cors", credentials: "omit", cache: "no-cache", signal: ctl ? ctl.signal : undefined })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      clearTimeout(t);
      if (!data || !Array.isArray(data.off)) { confirmed = true; apply(); return; }
      writeCache(data.off);
      compute(data.off);
      confirmed = true;
      apply();
    })
    .catch(function () { clearTimeout(t); confirmed = true; apply(); /* the last known answer stands */ });
})();
