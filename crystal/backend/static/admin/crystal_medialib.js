/* ==========================================================================
   Crystal Media library — "Choose from Media library" on every upload box
   --------------------------------------------------------------------------
   Loaded on every admin screen from templates/admin/base_site.html.

   For each <input type="file" name="…"> it adds a button and a hidden
   <input name="<same name>__media">. Picking a file in the modal puts the
   file's stored name in that hidden input and empties the real file input;
   the server (medialib/picking.py) reads it and points the model at the file
   that is already stored — nothing is uploaded again, nothing is copied.

   How it finds the boxes:
     * every file input on the page at load;
     * any added later — "Add another" rows, the gallery's new tiles — through a
       MutationObserver. Django's inlines.js clones the hidden empty-form row,
       so the button and hidden input come along in the clone and inlines.js
       renames the hidden input with the rest of the row ("images-__prefix__-
       image__media" -> "images-3-image__media"). That is why every click here
       is delegated from document: jQuery's clone does not carry listeners
       added with addEventListener.

   Skipped: inputs with no name (nothing to post), `multiple` inputs (a
   ModelForm file field takes one file), anything inside [data-ml-skip], and
   the library's own add form. The gallery's two multi-photo "Add photos"
   pickers get a separate "From library" button that adds one tile per pick —
   see window.crystalMedia.addLibraryItemsTo in crystal_media.js.

   Plain JS, no libraries. No <dialog>: its close event is not reliable across
   the browsers this dashboard is used in, and closing has to clean up.
   ========================================================================== */
(function () {
  "use strict";

  var tag = document.currentScript || document.querySelector("script[data-picker-url]");
  if (!tag) return;
  var CFG = {
    picker: tag.getAttribute("data-picker-url"),
    upload: tag.getAttribute("data-upload-url"),
    library: tag.getAttribute("data-library-url"),
    csrf: tag.getAttribute("data-csrf") || ""
  };
  var SUFFIX = "__media";
  var KIND_LABEL = { "": "All files", image: "Images", video: "Videos", pdf: "PDFs", other: "Other files" };
  var KIND_ICON = { image: "fa-image", video: "fa-film", pdf: "fa-file-pdf", other: "fa-file" };

  function el(tagName, cls, text) {
    var e = document.createElement(tagName);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function csrf() {
    if (CFG.csrf) return CFG.csrf;
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  /** The kind filter the modal opens on, from the box's accept attribute. */
  function kindFromAccept(accept) {
    var parts = String(accept || "").toLowerCase().split(",")
      .map(function (p) { return p.trim(); }).filter(Boolean);
    if (!parts.length) return "";
    function every(test) { return parts.every(test); }
    if (every(function (p) { return /^image\//.test(p) || /^\.(jpe?g|png|gif|webp|avif|bmp|tiff?)$/.test(p); })) return "image";
    if (every(function (p) { return /^video\//.test(p) || /^\.(mp4|webm|mov|m4v|ogv)$/.test(p); })) return "video";
    if (every(function (p) { return p === ".pdf" || p === "application/pdf"; })) return "pdf";
    return "";
  }

  function skipped(input) {
    if (!input.name || input.multiple || input.type !== "file") return true;
    if (input.closest("[data-ml-skip]") || input.hasAttribute("data-ml-skip")) return true;
    // The library's own add form: picking a library file there would only
    // make a second row for the same file.
    if (document.body.classList.contains("model-mediaitem")) return true;
    return false;
  }

  /* ---------- one upload box ---------------------------------------------- */

  function wrapperOf(input) {
    var next = input.nextElementSibling;
    return next && next.classList.contains("ml-field") ? next : null;
  }

  function enhance(input) {
    if (skipped(input)) return null;
    var wrap = wrapperOf(input);
    if (wrap) {
      // Already there (or cloned along with an inline row). Keep the hidden
      // input's name tied to the file input's, whatever renamed the row.
      var hidden = wrap.querySelector("input[type=hidden]");
      if (hidden && hidden.name !== input.name + SUFFIX) hidden.name = input.name + SUFFIX;
      return wrap;
    }
    wrap = el("span", "ml-field");
    var btn = el("button", "ml-btn");
    btn.type = "button";
    btn.setAttribute("data-ml-open", "");
    btn.innerHTML = '<i class="fas fa-photo-video" aria-hidden="true"></i> ';
    btn.appendChild(document.createTextNode("Choose from Media library"));
    var hidden = el("input");
    hidden.type = "hidden";
    hidden.name = input.name + SUFFIX;
    hidden.value = "";
    var chosen = el("span", "ml-chosen");
    chosen.hidden = true;
    wrap.appendChild(btn);
    wrap.appendChild(hidden);
    wrap.appendChild(chosen);
    input.parentNode.insertBefore(wrap, input.nextSibling);
    return wrap;
  }

  function scan(root) {
    if (!root || !root.querySelectorAll) return;
    if (root.matches && root.matches("input[type=file]")) enhance(root);
    Array.prototype.forEach.call(root.querySelectorAll("input[type=file]"), enhance);
    Array.prototype.forEach.call(root.querySelectorAll("[data-cz-picker],[data-cz-sizepicker]"), multiButton);
  }

  /** Point this box at a library file. Exposed for crystal_media.js. */
  function assign(input, item) {
    var wrap = enhance(input);
    if (!wrap) return false;
    var hidden = wrap.querySelector("input[type=hidden]");
    hidden.value = item.name;
    // A real upload would win on the server; make sure there is none, and
    // that "Clear" is not ticked too (Clear + a file is refused as a contradiction).
    try { input.value = ""; } catch (e) { /* old browsers */ }
    var clear = input.form && input.form.querySelector('input[type=checkbox][name="' + input.name + '-clear"]');
    if (clear) clear.checked = false;

    var chosen = wrap.querySelector(".ml-chosen");
    chosen.textContent = "";
    if (item.kind === "image" && item.url) {
      var img = el("img");
      img.src = item.url;
      img.alt = "";
      chosen.appendChild(img);
    } else {
      var ic = el("i", "fas " + (KIND_ICON[item.kind] || "fa-file"));
      ic.setAttribute("aria-hidden", "true");
      chosen.appendChild(ic);
    }
    var label = el("span", "ml-chosen__name", item.filename || item.name);
    label.title = item.name;
    chosen.appendChild(label);
    var rm = el("button", "ml-chosen__remove", "remove");
    rm.type = "button";
    rm.setAttribute("data-ml-remove", "");
    chosen.appendChild(rm);
    chosen.hidden = false;
    wrap.classList.add("is-picked");
    input.dispatchEvent(new CustomEvent("medialib:picked", { bubbles: true, detail: item }));
    return true;
  }

  function unassign(wrap) {
    var hidden = wrap.querySelector("input[type=hidden]");
    if (hidden) hidden.value = "";
    var chosen = wrap.querySelector(".ml-chosen");
    if (chosen) { chosen.textContent = ""; chosen.hidden = true; }
    wrap.classList.remove("is-picked");
  }

  /* The gallery's multi-photo pickers: one tile per picked file. */
  function multiButton(input) {
    var label = input.closest("label") || input;
    var next = label.nextElementSibling;
    if (next && next.hasAttribute("data-ml-multi")) return;
    var btn = el("button", "ml-btn ml-btn--multi");
    btn.type = "button";
    btn.setAttribute("data-ml-multi", "");
    btn.innerHTML = '<i class="fas fa-photo-video" aria-hidden="true"></i> ';
    btn.appendChild(document.createTextNode("From Media library"));
    label.parentNode.insertBefore(btn, label.nextSibling);
  }

  /* ---------- the modal ---------------------------------------------------- */

  var modal = null;
  var state = null;

  function buildModal() {
    var m = el("div", "ml-modal");
    m.hidden = true;
    m.setAttribute("role", "dialog");
    m.setAttribute("aria-modal", "true");
    m.setAttribute("aria-labelledby", "ml-modal-title");
    m.innerHTML =
      '<div class="ml-modal__backdrop" data-ml-close></div>' +
      '<div class="ml-modal__panel">' +
      '  <div class="ml-modal__head">' +
      '    <h2 id="ml-modal-title"><i class="fas fa-photo-video" aria-hidden="true"></i> Media library</h2>' +
      '    <button type="button" class="ml-modal__x" data-ml-close aria-label="Close">&times;</button>' +
      '  </div>' +
      '  <div class="ml-modal__bar">' +
      '    <input type="search" class="ml-modal__q" placeholder="Search by name" aria-label="Search the library">' +
      '    <select class="ml-modal__kind" aria-label="Show"></select>' +
      '    <label class="ml-modal__upload"><input type="file" multiple data-ml-skip>' +
      '      <i class="fas fa-cloud-upload-alt" aria-hidden="true"></i> Upload new</label>' +
      '  </div>' +
      '  <div class="ml-modal__status" role="status" aria-live="polite"></div>' +
      '  <div class="ml-modal__body">' +
      '    <div class="ml-modal__grid" role="listbox"></div>' +
      '    <div class="ml-modal__more" hidden><button type="button" class="ml-btn">Load more</button></div>' +
      '    <div class="ml-modal__veil" aria-hidden="true"><span>Drop files to upload them to the library</span></div>' +
      '  </div>' +
      '  <div class="ml-modal__foot">' +
      '    <span class="ml-modal__sel">Nothing selected</span>' +
      '    <a class="ml-modal__lib" target="_blank" rel="noopener">Open the full library &#8599;</a>' +
      '    <button type="button" class="ml-modal__cancel" data-ml-close>Cancel</button>' +
      '    <button type="button" class="ml-modal__use" disabled>Use this file</button>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(m);

    var kindSel = m.querySelector(".ml-modal__kind");
    Object.keys(KIND_LABEL).forEach(function (k) {
      var o = el("option", null, KIND_LABEL[k]);
      o.value = k;
      kindSel.appendChild(o);
    });
    m.querySelector(".ml-modal__lib").href = CFG.library;

    var q = m.querySelector(".ml-modal__q");
    var t = null;
    q.addEventListener("input", function () {
      clearTimeout(t);
      t = setTimeout(function () { load(true); }, 250);
    });
    kindSel.addEventListener("change", function () { load(true); });
    m.querySelector(".ml-modal__more button").addEventListener("click", function () { load(false); });
    m.querySelector(".ml-modal__use").addEventListener("click", finish);
    m.querySelector(".ml-modal__upload input").addEventListener("change", function () {
      if (this.files && this.files.length) upload(this.files);
      this.value = "";
    });

    var grid = m.querySelector(".ml-modal__grid");
    grid.addEventListener("click", function (e) {
      var tile = e.target.closest(".ml-tile");
      if (tile) toggle(tile);
    });
    grid.addEventListener("dblclick", function (e) {
      var tile = e.target.closest(".ml-tile");
      if (!tile) return;
      if (!tile.classList.contains("is-selected")) toggle(tile);
      finish();
    });

    var body = m.querySelector(".ml-modal__body");
    var depth = 0;
    function isFiles(e) {
      return e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], "Files") !== -1;
    }
    body.addEventListener("dragenter", function (e) { if (!isFiles(e)) return; e.preventDefault(); depth++; body.classList.add("is-dragging"); });
    body.addEventListener("dragover", function (e) { if (isFiles(e)) e.preventDefault(); });
    body.addEventListener("dragleave", function (e) { if (!isFiles(e)) return; depth = Math.max(0, depth - 1); if (!depth) body.classList.remove("is-dragging"); });
    body.addEventListener("drop", function (e) {
      if (!isFiles(e)) return;
      e.preventDefault();
      depth = 0;
      body.classList.remove("is-dragging");
      if (e.dataTransfer.files.length) upload(e.dataTransfer.files);
    });

    m.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { e.preventDefault(); close(); }
      if (e.key === "Tab") trapFocus(e);
    });
    return m;
  }

  function trapFocus(e) {
    var f = Array.prototype.filter.call(
      modal.querySelectorAll("button, input, select, a[href]"),
      function (x) { return !x.disabled && x.offsetParent !== null; });
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  function status(msg, isError) {
    var s = modal.querySelector(".ml-modal__status");
    s.textContent = msg || "";
    s.classList.toggle("is-error", !!isError);
  }

  /**
   * opts: { kind, multiple, onPick(items), returnFocus }
   */
  function open(opts) {
    if (!modal) modal = buildModal();
    state = {
      opts: opts,
      page: 0,
      pages: 1,
      selected: {},   // id -> item
      order: [],
      items: {},
      req: 0
    };
    modal.querySelector(".ml-modal__q").value = "";
    modal.querySelector(".ml-modal__kind").value = opts.kind || "";
    var up = modal.querySelector(".ml-modal__upload input");
    up.setAttribute("accept", opts.kind === "image" ? "image/*" :
                              opts.kind === "video" ? "video/*" :
                              opts.kind === "pdf" ? ".pdf,application/pdf" : "");
    modal.querySelector(".ml-modal__grid").textContent = "";
    status("");
    syncFoot();
    modal.hidden = false;
    document.documentElement.classList.add("ml-modal-open");
    load(true);
    setTimeout(function () { modal.querySelector(".ml-modal__q").focus(); }, 30);
  }

  function close() {
    if (!modal || modal.hidden) return;
    modal.hidden = true;
    document.documentElement.classList.remove("ml-modal-open");
    var back = state && state.opts.returnFocus;
    state = null;
    if (back && back.focus) { try { back.focus(); } catch (e) { /* gone */ } }
  }

  function load(reset) {
    if (!state) return;
    if (reset) {
      state.page = 0;
      modal.querySelector(".ml-modal__grid").textContent = "";
    }
    var page = state.page + 1;
    var params = new URLSearchParams({
      kind: modal.querySelector(".ml-modal__kind").value,
      q: modal.querySelector(".ml-modal__q").value.trim(),
      page: String(page)
    });
    var mine = ++state.req;
    status("Loading…");
    fetch(CFG.picker + "?" + params.toString(), {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest", "Accept": "application/json" }
    })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        if (!state || mine !== state.req) return;
        state.page = data.page;
        state.pages = data.pages;
        var grid = modal.querySelector(".ml-modal__grid");
        data.items.forEach(function (item) { grid.appendChild(tileFor(item)); });
        modal.querySelector(".ml-modal__more").hidden = data.page >= data.pages;
        if (!data.total) {
          status(modal.querySelector(".ml-modal__q").value.trim()
            ? "Nothing matches that search."
            : "Nothing here yet — use “Upload new” to add files.");
        } else {
          status(data.total + (data.total === 1 ? " file" : " files"));
        }
      })
      .catch(function () {
        if (!state || mine !== state.req) return;
        status("Could not load the library. Check the connection and try again.", true);
      });
  }

  function tileFor(item) {
    state.items[item.id] = item;
    var b = el("button", "ml-tile");
    b.type = "button";
    b.setAttribute("role", "option");
    b.setAttribute("data-id", item.id);
    b.title = item.title + (item.source ? " — from " + item.source : "");
    var box = el("span", "ml-tile__img");
    if (item.kind === "image" && item.url) {
      var img = el("img");
      img.loading = "lazy";
      img.src = item.url;
      img.alt = item.alt || "";
      box.appendChild(img);
    } else {
      var ic = el("i", "fas " + (KIND_ICON[item.kind] || "fa-file"));
      ic.setAttribute("aria-hidden", "true");
      box.appendChild(ic);
    }
    b.appendChild(box);
    b.appendChild(el("span", "ml-tile__name", item.title));
    var meta = [];
    if (item.width && item.height) meta.push(item.width + "×" + item.height);
    if (item.size) meta.push(item.size);
    b.appendChild(el("span", "ml-tile__meta", meta.join(" · ")));
    if (state.selected[item.id]) b.classList.add("is-selected");
    b.setAttribute("aria-selected", state.selected[item.id] ? "true" : "false");
    return b;
  }

  function toggle(tile) {
    var id = tile.getAttribute("data-id");
    var item = state.items[id];
    if (!item) return;
    if (!state.opts.multiple) {
      Array.prototype.forEach.call(modal.querySelectorAll(".ml-tile.is-selected"), function (t) {
        t.classList.remove("is-selected");
        t.setAttribute("aria-selected", "false");
      });
      state.selected = {};
      state.order = [];
    }
    if (state.selected[id]) {
      delete state.selected[id];
      state.order = state.order.filter(function (x) { return x !== id; });
      tile.classList.remove("is-selected");
      tile.setAttribute("aria-selected", "false");
    } else {
      state.selected[id] = item;
      state.order.push(id);
      tile.classList.add("is-selected");
      tile.setAttribute("aria-selected", "true");
    }
    syncFoot();
  }

  function syncFoot() {
    var n = state ? state.order.length : 0;
    var use = modal.querySelector(".ml-modal__use");
    var sel = modal.querySelector(".ml-modal__sel");
    use.disabled = !n;
    if (state && state.opts.multiple) {
      use.textContent = n > 1 ? "Use these " + n + " files" : "Use this file";
    } else {
      use.textContent = "Use this file";
    }
    if (!n) sel.textContent = "Nothing selected";
    else if (n === 1) sel.textContent = state.selected[state.order[0]].filename;
    else sel.textContent = n + " files selected";
  }

  function finish() {
    if (!state || !state.order.length) return;
    var items = state.order.map(function (id) { return state.selected[id]; });
    var cb = state.opts.onPick;
    close();
    if (cb) cb(items);
  }

  function upload(fileList) {
    var fd = new FormData();
    Array.prototype.forEach.call(fileList, function (f) { fd.append("file", f); });
    status("Uploading " + fileList.length + (fileList.length === 1 ? " file…" : " files…"));
    modal.classList.add("is-busy");
    fetch(CFG.upload, {
      method: "POST",
      body: fd,
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" }
    })
      .then(function (r) {
        return r.json().catch(function () { return { items: [], errors: ["The upload failed (HTTP " + r.status + ")."] }; });
      })
      .then(function (data) {
        if (!state) return;
        var grid = modal.querySelector(".ml-modal__grid");
        var tiles = (data.items || []).map(function (item) {
          var t = tileFor(item);
          grid.insertBefore(t, grid.firstChild);
          return t;
        });
        // New uploads arrive selected — upload-then-use is the common path.
        if (!state.opts.multiple && tiles.length) toggle(tiles[0]);
        else tiles.slice().reverse().forEach(function (t) { if (!t.classList.contains("is-selected")) toggle(t); });
        var errs = data.errors || [];
        if (errs.length) status(errs.join(" "), true);
        else status(tiles.length + (tiles.length === 1 ? " file uploaded and selected." : " files uploaded and selected."));
      })
      .catch(function () {
        status("The upload failed. Check the connection and try again.", true);
      })
      .then(function () { if (modal) modal.classList.remove("is-busy"); });
  }

  /* ---------- delegated clicks -------------------------------------------- */

  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t.closest) return;

    var openBtn = t.closest("[data-ml-open]");
    if (openBtn) {
      e.preventDefault();
      var wrap = openBtn.closest(".ml-field");
      var input = wrap && wrap.previousElementSibling;
      if (!input || input.type !== "file") return;
      open({
        kind: kindFromAccept(input.getAttribute("accept")),
        multiple: false,
        returnFocus: openBtn,
        onPick: function (items) { assign(input, items[0]); }
      });
      return;
    }

    var multi = t.closest("[data-ml-multi]");
    if (multi) {
      e.preventDefault();
      var holder = multi.previousElementSibling;
      var variant = holder && holder.getAttribute("data-variant-id") || "";
      open({
        kind: "image",
        multiple: true,
        returnFocus: multi,
        onPick: function (items) {
          if (window.crystalMedia && window.crystalMedia.addLibraryItemsTo) {
            window.crystalMedia.addLibraryItemsTo(variant, items);
          }
        }
      });
      return;
    }

    var rm = t.closest("[data-ml-remove]");
    if (rm) {
      e.preventDefault();
      var w = rm.closest(".ml-field");
      if (w) {
        unassign(w);
        var inp = w.previousElementSibling;
        if (inp) inp.dispatchEvent(new CustomEvent("medialib:cleared", { bubbles: true }));
      }
      return;
    }

    if (t.closest("[data-ml-close]")) {
      e.preventDefault();
      close();
      return;
    }

    var copy = t.closest("[data-ml-copy]");
    if (copy) {
      e.preventDefault();
      e.stopPropagation();
      var url = new URL(copy.getAttribute("data-ml-copy"), window.location.href).href;
      var done = function () {
        var old = copy.innerHTML;
        copy.classList.add("is-copied");
        copy.textContent = "Copied";
        setTimeout(function () { copy.innerHTML = old; copy.classList.remove("is-copied"); }, 1400);
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(url).then(done, function () { window.prompt("Copy this address:", url); });
      } else {
        window.prompt("Copy this address:", url);
      }
    }
  });

  // Choosing a real file after a pick: the upload is what the person wants now.
  document.addEventListener("change", function (e) {
    var input = e.target;
    if (!input || input.type !== "file" || !input.files || !input.files.length) return;
    var wrap = wrapperOf(input);
    if (wrap) unassign(wrap);
  });

  /* ---------- the "Upload files" page -------------------------------------- */

  function wireUploadPage(form) {
    var input = form.querySelector('input[type=file][name="files"]');
    var drop = form.querySelector("[data-ml-drop]");
    var queue = form.querySelector("[data-ml-queue]");
    if (!input || !drop || !queue) return;

    function render() {
      queue.textContent = "";
      var files = Array.prototype.slice.call(input.files || []);
      queue.hidden = !files.length;
      files.forEach(function (f) {
        var li = el("li");
        li.appendChild(el("span", "ml-queue__name", f.name));
        li.appendChild(el("span", "ml-queue__size",
          f.size > 1048576 ? (f.size / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(f.size / 1024)) + " KB"));
        queue.appendChild(li);
      });
    }
    input.addEventListener("change", render);
    ["dragenter", "dragover"].forEach(function (type) {
      drop.addEventListener(type, function (e) { e.preventDefault(); drop.classList.add("is-over"); });
    });
    drop.addEventListener("dragleave", function () { drop.classList.remove("is-over"); });
    drop.addEventListener("drop", function (e) {
      e.preventDefault();
      drop.classList.remove("is-over");
      try {
        // Add to what is already chosen rather than replacing it.
        var dt = new DataTransfer();
        Array.prototype.forEach.call(input.files || [], function (f) { dt.items.add(f); });
        Array.prototype.forEach.call(e.dataTransfer.files, function (f) { dt.items.add(f); });
        input.files = dt.files;
      } catch (err) {
        input.files = e.dataTransfer.files;
      }
      render();
    });
  }

  /* ---------- start -------------------------------------------------------- */

  window.crystalLibrary = { open: open, assign: assign, enhance: enhance };

  function start() {
    scan(document.body);
    var page = document.querySelector("[data-ml-uploadpage]");
    if (page) wireUploadPage(page);
    if (window.MutationObserver) {
      new MutationObserver(function (records) {
        records.forEach(function (r) {
          Array.prototype.forEach.call(r.addedNodes, function (n) {
            if (n.nodeType === 1 && !(n.classList && n.classList.contains("ml-field"))) scan(n);
          });
        });
      }).observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
