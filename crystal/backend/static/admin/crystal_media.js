/* ==========================================================================
   Crystal media grid — behaviour for admin/products/product/edit_inline/gallery_grid.html
   --------------------------------------------------------------------------
   Vanilla; no jQuery, no drag library. It cooperates with Django's own
   inlines.js rather than replacing it:

     * "Add another" still belongs to inlines.js. Adding a photo here just
       clicks the .add-row link it injected, then fills the file input of the
       tile it created. Files post with the normal form on Save — there is no
       upload endpoint, no CSRF plumbing and no draft-image concept.
     * New tiles are picked up through the bubbling "formset:added" event
       inlines.js dispatches, so nothing has to be re-bound by hand.
     * Everything else is delegated off the group root, so cloned tiles work
       without any per-tile wiring at all.

   Drag-and-drop reordering uses the HTML5 API, which has no touch support and
   no keyboard story. The per-tile arrow buttons drive exactly the same move()
   and renumber() as a drop does; they are the accessible path and the phone
   path, not a consolation prize.
   ========================================================================== */
(function () {
  "use strict";

  var TILE = "[data-cz-tile]";
  var DRAG_MIME = "text/x-crystal-tile";

  /* ---------- small helpers ------------------------------------------------ */

  function all(root, sel) {
    return Array.prototype.slice.call(root.querySelectorAll(sel));
  }

  /** Real, live tiles: excludes the #<prefix>-empty clone source. */
  function tiles(root) {
    return all(root, TILE).filter(function (t) {
      return !t.classList.contains("empty-form");
    });
  }

  function fieldIn(tile, suffix) {
    // Ids are "<prefix>-<n>-<field>"; names are the same. inlines.js rewrites
    // both on clone, so matching by the id suffix stays correct afterwards.
    var els = tile.querySelectorAll("input,select,textarea");
    for (var i = 0; i < els.length; i++) {
      var n = els[i].name || els[i].id || "";
      if (n.slice(-(suffix.length + 1)) === "-" + suffix) return els[i];
    }
    return null;
  }

  var heroField = function (t) { return fieldIn(t, "is_hero"); };
  var orderField = function (t) { return fieldIn(t, "order"); };
  var variantField = function (t) { return fieldIn(t, "variant"); };
  var deleteField = function (t) { return fieldIn(t, "DELETE"); };
  var fileField = function (t) { return t.querySelector('[data-cz-file] input[type="file"]'); };

  /** The variant a tile currently belongs to — read live from its own select. */
  function groupKey(tile) {
    var v = variantField(tile);
    return v ? String(v.value || "") : "";
  }

  function isDeleted(tile) {
    var d = deleteField(tile);
    return !!(d && d.checked);
  }

  /* ---------- ordering ----------------------------------------------------- */

  /**
   * Renumber every order input in one pass, in document order.
   * Groups are contiguous in the DOM, so a single global sequence also leaves
   * each group internally ordered — and keeps the numbers unique across the
   * product, which is what the old table produced by hand.
   */
  function renumber(root) {
    var n = 0;
    tiles(root).forEach(function (t) {
      var o = orderField(t);
      if (o) o.value = n;
      n += 1;
    });
  }

  /** Move a tile one slot within its own variant group. dir is -1 or +1. */
  function nudge(root, tile, dir) {
    var key = groupKey(tile);
    var siblings = tiles(root).filter(function (t) { return groupKey(t) === key; });
    var i = siblings.indexOf(tile);
    var j = i + dir;
    if (i < 0 || j < 0 || j >= siblings.length) return;
    var other = siblings[j];
    if (dir < 0) other.parentNode.insertBefore(tile, other);
    else other.parentNode.insertBefore(tile, other.nextSibling);
    renumber(root);
    flash(tile);
    tile.querySelector('[data-cz-nudge="' + dir + '"]').focus();
  }

  function flash(tile) {
    tile.classList.remove("cz-tile--moved");
    // Force a reflow so the animation restarts on a repeated nudge.
    void tile.offsetWidth;
    tile.classList.add("cz-tile--moved");
  }

  /* ---------- hero --------------------------------------------------------- */

  /** Hero is per SIZE, not per product: only untick tiles in the same group. */
  function setHero(root, tile) {
    var h = heroField(tile);
    if (!h) return;
    var key = groupKey(tile);
    var on = !h.checked;
    tiles(root).forEach(function (t) {
      var f = heroField(t);
      if (!f) return;
      if (t === tile) f.checked = on;
      else if (groupKey(t) === key) f.checked = false;
    });
    syncHero(root);
  }

  function syncHero(root) {
    all(root, TILE).forEach(function (t) {
      var f = heroField(t);
      t.classList.toggle("cz-tile--hero", !!(f && f.checked));
    });
  }

  function syncDeleted(root) {
    all(root, TILE).forEach(function (t) {
      t.classList.toggle("cz-tile--deleted", isDeleted(t));
    });
  }

  /* ---------- previews ----------------------------------------------------- */

  function preview(tile, file) {
    var img = tile.querySelector("[data-cz-img]");
    if (!img || !file || !/^image\//.test(file.type)) return;
    var url = URL.createObjectURL(file);
    img.addEventListener("load", function () { URL.revokeObjectURL(url); }, { once: true });
    img.src = url;
    img.hidden = false;
    img.alt = file.name;
    var ph = tile.querySelector(".cz-tile-noimg");
    if (ph) ph.hidden = true;
    tile.classList.add("cz-tile--filled");
  }

  /* ---------- adding files ------------------------------------------------- */

  function addButton(root) {
    // inlines.js injects <div class="add-row"><a class="addlink">…</a></div>
    // after the last .inline-related, i.e. inside the last group's grid.
    // inlines.js hides the wrapper (not the link) once max_num is reached.
    var a = root.querySelector(".add-row a");
    if (!a || (a.parentNode && a.parentNode.style.display === "none")) return null;
    return a;
  }

  /**
   * Add one blank tile via Django's own add link and hand back the tile it
   * created. inlines.js inserts the clone synchronously and fires a bubbling
   * "formset:added" whose target is the new row, so a one-shot listener is
   * enough — no polling, no guessing at indices.
   */
  function addTile(root) {
    var link = addButton(root);
    if (!link) return null;
    var made = null;
    var grab = function (e) { made = e.target; };
    root.addEventListener("formset:added", grab, true);
    link.click();
    root.removeEventListener("formset:added", grab, true);
    return made && made.matches && made.matches(TILE) ? made : null;
  }

  function attach(tile, file, variantValue) {
    var input = fileField(tile);
    if (!input) return false;
    try {
      var dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
    } catch (err) {
      return false; // No DataTransfer constructor (very old browser): give up quietly.
    }
    input.dispatchEvent(new Event("change", { bubbles: true }));
    var v = variantField(tile);
    if (v && variantValue !== undefined && variantValue !== null) {
      // Only set it if the option really exists for this product.
      for (var i = 0; i < v.options.length; i++) {
        if (v.options[i].value === String(variantValue)) { v.value = String(variantValue); break; }
      }
    }
    preview(tile, file);
    return true;
  }

  /**
   * inlines.js always inserts a new row just before #<prefix>-empty, i.e. at
   * the end of the "All sizes" grid. If the photo was dropped on a size, move
   * the tile under that size's heading so the grouping the card promises is
   * actually what the user sees. Only the tile moves — the empty template stays
   * last, which is the bit inlines.js cares about.
   */
  function relocate(root, tile, variantValue) {
    var section = root.querySelector('[data-cz-group="' + String(variantValue).replace(/"/g, "") + '"]');
    var grid = section && section.querySelector(".cz-media-grid");
    if (grid && tile.parentNode !== grid) grid.appendChild(tile);
  }

  function addFiles(root, fileList, variantValue) {
    var files = Array.prototype.slice.call(fileList).filter(function (f) {
      return /^image\//.test(f.type);
    });
    var added = 0;
    files.forEach(function (f) {
      var tile = addTile(root);
      if (tile && attach(tile, f, variantValue)) {
        if (variantValue) relocate(root, tile, variantValue);
        added += 1;
      }
    });
    if (added) {
      renumber(root);
      announce(root, added + (added === 1 ? " photo added." : " photos added.") +
                     " Save the product to upload.");
    } else if (files.length) {
      announce(root, "Could not add those files. Use the Add photos button.");
    }
    return added;
  }

  function announce(root, msg) {
    var live = root.querySelector("[data-cz-live]");
    if (live) live.textContent = msg;
  }

  /* ---------- drag to reorder --------------------------------------------- */

  var dragging = null;

  function tileFrom(e, root) {
    var t = e.target.closest ? e.target.closest(TILE) : null;
    return t && root.contains(t) ? t : null;
  }

  function wireDrag(root) {
    root.addEventListener("dragstart", function (e) {
      var t = tileFrom(e, root);
      if (!t || t.classList.contains("empty-form")) return;
      // A drag that begins inside the file input is the browser's business.
      if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
      dragging = t;
      t.classList.add("cz-tile--dragging");
      root.classList.add("cz-media--dragging");
      e.dataTransfer.effectAllowed = "move";
      try { e.dataTransfer.setData(DRAG_MIME, t.id); } catch (err) { /* IE-ish */ }
    });

    root.addEventListener("dragend", function () {
      if (dragging) dragging.classList.remove("cz-tile--dragging");
      dragging = null;
      root.classList.remove("cz-media--dragging");
      root.classList.remove("cz-media--filedrag");
      all(root, ".cz-tile--over").forEach(function (t) { t.classList.remove("cz-tile--over"); });
    });

    root.addEventListener("dragover", function (e) {
      if (isFileDrag(e)) { fileDragOver(root, e); return; }
      if (!dragging) return;
      var over = tileFrom(e, root);
      if (!over || over === dragging || over.classList.contains("empty-form")) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      all(root, ".cz-tile--over").forEach(function (t) { t.classList.remove("cz-tile--over"); });
      over.classList.add("cz-tile--over");
    });

    root.addEventListener("drop", function (e) {
      if (isFileDrag(e)) { fileDrop(root, e); return; }
      if (!dragging) return;
      var over = tileFrom(e, root);
      if (!over || over === dragging || over.classList.contains("empty-form")) return;
      e.preventDefault();
      var box = over.getBoundingClientRect();
      var after = (e.clientX - box.left) > box.width / 2;
      over.parentNode.insertBefore(dragging, after ? over.nextSibling : over);
      // Dropping into another size's group re-points the photo at that size.
      var target = over.closest("[data-cz-group]");
      var v = variantField(dragging);
      if (target && v) {
        var want = target.getAttribute("data-cz-group") || "";
        for (var i = 0; i < v.options.length; i++) {
          if (v.options[i].value === want) { v.value = want; break; }
        }
      }
      over.classList.remove("cz-tile--over");
      renumber(root);
      syncHero(root);
      flash(dragging);
    });
  }

  /* ---------- drag files in ------------------------------------------------ */

  function isFileDrag(e) {
    var t = e.dataTransfer && e.dataTransfer.types;
    if (!t) return false;
    return Array.prototype.indexOf.call(t, "Files") !== -1;
  }

  var veilDepth = 0;

  function fileDragOver(root, e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    root.classList.add("cz-media--filedrag");
  }

  function fileDrop(root, e) {
    e.preventDefault();
    veilDepth = 0;
    root.classList.remove("cz-media--filedrag");
    var section = e.target.closest ? e.target.closest("[data-cz-group]") : null;
    var want = section ? (section.getAttribute("data-cz-group") || "") : "";
    addFiles(root, e.dataTransfer.files, want);
  }

  function wireFileDrag(root) {
    root.addEventListener("dragenter", function (e) {
      if (!isFileDrag(e)) return;
      veilDepth += 1;
      root.classList.add("cz-media--filedrag");
      e.preventDefault();
    });
    root.addEventListener("dragleave", function (e) {
      if (!isFileDrag(e)) return;
      veilDepth = Math.max(0, veilDepth - 1);
      if (!veilDepth) root.classList.remove("cz-media--filedrag");
    });
    // The page as a whole must not navigate away when a stray file misses.
    ["dragover", "drop"].forEach(function (type) {
      window.addEventListener(type, function (e) {
        if (isFileDrag(e) && !root.contains(e.target)) e.preventDefault();
      });
    });
  }

  /* ---------- wiring ------------------------------------------------------- */

  function wire(root) {
    if (root.dataset.czWired) return;
    root.dataset.czWired = "1";

    var live = document.createElement("p");
    live.className = "cz-sr";
    live.setAttribute("role", "status");
    live.setAttribute("aria-live", "polite");
    live.setAttribute("data-cz-live", "");
    root.appendChild(live);

    root.addEventListener("click", function (e) {
      var hero = e.target.closest("[data-cz-hero]");
      if (hero && root.contains(hero)) {
        var t = hero.closest(TILE);
        if (t && !t.classList.contains("empty-form")) { e.preventDefault(); setHero(root, t); }
        return;
      }
      var nb = e.target.closest("[data-cz-nudge]");
      if (nb && root.contains(nb)) {
        e.preventDefault();
        var tile = nb.closest(TILE);
        if (tile) nudge(root, tile, parseInt(nb.getAttribute("data-cz-nudge"), 10));
      }
    });

    root.addEventListener("change", function (e) {
      var t = e.target;
      if (!t.name) return;
      if (/-is_hero$/.test(t.name)) {
        // The real checkbox was used (keyboard / screen reader). Enforce the
        // one-per-size rule from here too.
        if (t.checked) {
          var tile = t.closest(TILE);
          var key = groupKey(tile);
          tiles(root).forEach(function (o) {
            if (o === tile) return;
            var f = heroField(o);
            if (f && groupKey(o) === key) f.checked = false;
          });
        }
        syncHero(root);
      } else if (/-DELETE$/.test(t.name)) {
        syncDeleted(root);
      } else if (/-variant$/.test(t.name)) {
        syncHero(root);
      } else if (t.type === "file" && t.files && t.files[0]) {
        var ft = t.closest(TILE);
        if (ft) preview(ft, t.files[0]);
      }
    });

    var picker = root.querySelector("[data-cz-picker]");
    if (picker) {
      picker.addEventListener("change", function () {
        if (this.files && this.files.length) addFiles(root, this.files, "");
        this.value = "";
      });
    }

    wireDrag(root);
    wireFileDrag(root);

    // Tiles cloned by inlines.js inherit a stale preview and a stale hero star.
    root.addEventListener("formset:added", function (e) {
      var t = e.target;
      if (!t || !t.matches || !t.matches(TILE)) return;
      var img = t.querySelector("[data-cz-img]");
      if (img) { img.removeAttribute("src"); img.hidden = true; img.alt = ""; }
      var ph = t.querySelector(".cz-tile-noimg");
      if (ph) ph.hidden = false;
      var h = heroField(t);
      if (h) h.checked = false;
      // inlines.js rewrites id/name/for but not aria-describedby, so a clone's
      // help-text pointer would still aim at the hidden template's node.
      all(t, "[aria-describedby]").forEach(function (el) {
        el.setAttribute(
          "aria-describedby",
          el.getAttribute("aria-describedby").replace("__prefix__", String(t.id).split("-").pop())
        );
      });
      t.classList.remove("cz-tile--hero", "cz-tile--filled", "cz-tile--moved", "cz-tile--dragging");
      t.classList.add("cz-tile--new");
      t.setAttribute("draggable", "true");
    });

    syncHero(root);
    syncDeleted(root);
  }

  function init() {
    all(document, ".cz-media.js-inline-admin-formset").forEach(wire);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
