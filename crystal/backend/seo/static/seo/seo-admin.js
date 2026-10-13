/* Live length counters and a Google-style preview for the SEO screens.
 *
 * Google cuts a title off at about 60 characters and a description at about
 * 155, so those are the two numbers worth showing while someone types. The
 * preview is a rough picture of the result, not a promise -- Google decides the
 * final cut in pixels, not characters.
 */
(function () {
  "use strict";

  var LIMITS = {
    id_title: [30, 60], id_meta_title: [30, 60], id_og_title: [20, 70],
    id_description: [110, 155], id_meta_description: [110, 155],
    id_og_description: [60, 200]
  };

  function verdict(len, lo, hi) {
    if (!len) return ["empty", "#94a3b8"];
    if (len > hi) return ["too long — Google will cut it off", "#dc2626"];
    if (len < lo) return ["short — room to say more", "#d97706"];
    return ["good length", "#16a34a"];
  }

  function attach(id) {
    var input = document.getElementById(id);
    if (!input || input.dataset.seoBound) return;
    input.dataset.seoBound = "1";
    var range = LIMITS[id];
    var note = document.createElement("div");
    note.className = "seo-count";
    note.style.cssText = "font-size:12px;margin-top:4px;font-weight:600;";
    input.parentNode.appendChild(note);

    function update() {
      var n = input.value.length;
      /* An empty box does not mean an empty page: the page keeps what it says
         today. Judge that text instead of reporting "empty". */
      var fb = n ? "" : fallback(id);
      if (fb) {
        var fv = verdict(fb.length, range[0], range[1]);
        note.textContent = "empty — the page keeps its current text (" + fb.length + " characters, " + fv[0] + ")";
        note.style.color = fv[1] === "#dc2626" ? fv[1] : "#64748b";
      } else {
        var v = verdict(n, range[0], range[1]);
        note.textContent = n + " / " + range[1] + " — " + v[0];
        note.style.color = v[1];
      }
      renderPreview();
    }
    input.addEventListener("input", update);
    update();
  }

  function fallback(id) {
    var box = document.getElementById("seo-preview");
    if (!box) return "";
    /* Only the search title and description fall back to the page's own text;
       the share-card fields fall back to those, which is a different story. */
    if (id.indexOf("id_og_") === 0) return "";
    if (/title$/.test(id)) return box.dataset.fallbackTitle || "";
    if (/description$/.test(id)) return box.dataset.fallbackDescription || "";
    return "";
  }

  function val(id) {
    var el = document.getElementById(id);
    return el ? el.value : "";
  }

  function cut(text, n) {
    return text.length > n ? text.slice(0, n - 1).replace(/\s+\S*$/, "") + "…" : text;
  }

  function renderPreview() {
    var box = document.getElementById("seo-preview");
    if (!box) return;
    var title = val("id_title") || val("id_meta_title") || box.dataset.fallbackTitle || "";
    var desc = val("id_description") || val("id_meta_description") || box.dataset.fallbackDescription || "";
    box.innerHTML = "";
    var url = document.createElement("div");
    url.textContent = box.dataset.url || "";
    url.style.cssText = "font-size:13px;color:#188038;margin-bottom:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;";
    var t = document.createElement("div");
    t.textContent = cut(title, 62) || "(no title)";
    t.style.cssText = "font-size:19px;line-height:1.3;color:#1a0dab;margin-bottom:3px;";
    var d = document.createElement("div");
    d.textContent = cut(desc, 160) || "(no description — Google will pick something from the page)";
    d.style.cssText = "font-size:13px;line-height:1.5;color:#4d5156;";
    box.appendChild(url); box.appendChild(t); box.appendChild(d);
  }

  function init() {
    Object.keys(LIMITS).forEach(attach);
    renderPreview();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
