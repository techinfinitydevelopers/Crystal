/* ==========================================================================
   Crystal — size cards (ProductVariant inline)
   --------------------------------------------------------------------------
   Progressive enhancement only. The card template is fully usable with this
   file absent: the collapsible body is a native <details>, every field is a
   plain form control, and "Add another size" is Django's own inlines.js.

   What this adds:
     1. "Add photos to this size" — jumps to the Gallery Images inline, claims
        a blank row (or asks inlines.js for a new one) and preselects the size.
     2. A card added by inlines.js opens its <details> so the fields are visible
        straight away, and drops any thumbnails/chips carried over in the clone.
     3. "Default" behaves like a radio: ticking one size unticks the others.
   No jQuery, no build step, no dependency on jazzmin internals.
   ========================================================================== */
(function () {
  'use strict';

  var SIZES_GROUP = '.cz-sizes';

  /* Which inline holds ProductImage rows? Identify it by the only thing that is
     structurally certain: it is a formset whose rows carry a `-variant` select.
     Never hard-code the "images" prefix — the related_name is not ours to own. */
  function imagesGroup() {
    var groups = document.querySelectorAll('.js-inline-admin-formset');
    for (var i = 0; i < groups.length; i++) {
      if (groups[i].matches(SIZES_GROUP)) continue;
      if (groups[i].querySelector('select[name$="-variant"]')) return groups[i];
    }
    return null;
  }

  function rowOf(el) {
    return el.closest('tr, .inline-related, .form-row, .dynamic-form') || el.parentElement;
  }

  /* A row counts as free when nobody has picked a file for it and it is not an
     already-saved image (saved rows render a link or an <img> preview). */
  function isBlankImageRow(row) {
    if (!row) return false;
    if (row.classList.contains('empty-form')) return false;
    if (row.querySelector('img')) return false;
    var file = row.querySelector('input[type="file"]');
    if (!file) return false;
    if (file.value) return false;
    var initial = row.querySelector('a[href]');
    return !initial;
  }

  function flash(row) {
    if (!row) return;
    row.classList.remove('cz-flash');
    void row.offsetWidth;              /* restart the animation */
    row.classList.add('cz-flash');
  }

  function selectVariant(row, variantId) {
    var select = row && row.querySelector('select[name$="-variant"]');
    if (!select) return false;
    var wanted = String(variantId);
    for (var i = 0; i < select.options.length; i++) {
      if (select.options[i].value === wanted) {
        select.value = wanted;
        select.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
      }
    }
    return false;   /* variant not in the dropdown yet — page predates this save */
  }

  /* ── Photos, added on the card itself ───────────────────────────────────
     The old button scrolled you down to the gallery grid and left you to find
     your way back. The card now takes the files directly: the grid still does
     the work (window.crystalMedia), but nothing moves under you and the strip
     updates on the spot so it is obvious the photo landed on THIS size. */

  function stripOf(card) {
    return card && card.querySelector('.cz-strip-thumbs');
  }

  function showThumb(card, file) {
    var strip = stripOf(card);
    if (!strip) {
      var empty = card.querySelector('.cz-strip-empty');
      if (!empty) return;
      strip = document.createElement('div');
      strip.className = 'cz-strip-thumbs';
      empty.parentNode.replaceChild(strip, empty);
    }
    var span = document.createElement('span');
    span.className = 'cz-sthumb cz-sthumb--pending';
    span.title = 'Added — uploads when you save';
    var img = document.createElement('img');
    var url = URL.createObjectURL(file);
    img.addEventListener('load', function () { URL.revokeObjectURL(url); }, { once: true });
    img.src = url;
    img.alt = '';
    span.appendChild(img);
    strip.appendChild(span);
  }

  function addFilesToCard(card, files) {
    var holder = card.querySelector('.cz-addphotos');
    var variantId = holder && holder.getAttribute('data-variant-id');
    if (!variantId) return;
    if (!window.crystalMedia || !window.crystalMedia.grid()) {
      window.alert('The Gallery Images section is not on this page, so photos cannot be added here.');
      return;
    }
    var images = Array.prototype.filter.call(files, function (f) { return /^image\//.test(f.type); });
    if (!images.length) return;
    var added = window.crystalMedia.addFilesTo(variantId, images);
    if (!added) return;
    images.slice(0, added).forEach(function (f) { showThumb(card, f); });
    flashCard(card);
  }

  function flashCard(card) {
    card.classList.add('cz-card--flash');
    setTimeout(function () { card.classList.remove('cz-card--flash'); }, 900);
  }

  /* "Upload a video for this size" just opens the details and focuses the
     field that is already there — no second control to keep in step. */
  function jumpToVideo(card) {
    var body = card.querySelector('details.cz-body');
    if (body) body.open = true;
    var input = card.querySelector('input[type="file"][name$="-video"]');
    if (!input) return;
    var field = input.closest('.cz-field') || input;
    field.scrollIntoView({ block: 'center', behavior: 'smooth' });
    try { input.focus({ preventScroll: true }); } catch (e) { input.focus(); }
    field.classList.add('cz-field--flash');
    setTimeout(function () { field.classList.remove('cz-field--flash'); }, 900);
  }

  function addPhotosTo(variantId, variantName) {
    var group = imagesGroup();
    if (!group) {
      window.alert(
        'Could not find the Gallery Images section on this page. Scroll down to it ' +
        'and pick "' + (variantName || 'this size') + '" in the "Applies to size" column.'
      );
      return;
    }

    /* Prefer a blank row that is already on the page (the inline ships extras). */
    var selects = group.querySelectorAll('select[name$="-variant"]');
    var target = null;
    for (var i = 0; i < selects.length; i++) {
      var row = rowOf(selects[i]);
      if (isBlankImageRow(row)) { target = row; break; }
    }

    /* Otherwise let Django's inlines.js mint one, then take the last row. */
    if (!target) {
      var addLink = group.querySelector('.add-row a, a.add-row, .add-row button');
      if (addLink) {
        addLink.click();
        var after = group.querySelectorAll('select[name$="-variant"]');
        if (after.length) target = rowOf(after[after.length - 1]);
      }
    }

    if (!target) {
      window.alert('No empty photo row is available. Save the product, then try again.');
      return;
    }

    selectVariant(target, variantId);
    target.scrollIntoView({ block: 'center', behavior: 'smooth' });
    flash(target);
    var file = target.querySelector('input[type="file"]');
    if (file) { try { file.focus({ preventScroll: true }); } catch (e) { file.focus(); } }
  }

  /* ── A card just cloned out of #<prefix>-empty ──────────────────────────── */

  function dressNewCard(card) {
    if (!card || !card.classList.contains('cz-card')) return;

    /* inlines.js strips .empty-form from the clone but not our own markers, so
       a new card would keep the dashed "this is the blank template" look. */
    card.classList.remove('cz-card--template', 'last-related');

    /* Nothing about the blank template's chips or strip describes the new row. */
    var stale = card.querySelectorAll('.cz-sthumb, .cz-addphotos');
    for (var i = 0; i < stale.length; i++) stale[i].remove();

    var body = card.querySelector('details.cz-body');
    if (body) body.open = true;        /* a brand-new size has everything to fill in */

    var nameInput = card.querySelector('.cz-namewrap input');
    if (nameInput) {
      try { nameInput.focus({ preventScroll: true }); } catch (e) { /* non-fatal */ }
    }
  }

  /* ── "Default" is really a radio ─────────────────────────────────────────── */

  function enforceSingleDefault(changed) {
    if (!changed.checked) return;
    var group = changed.closest(SIZES_GROUP);
    if (!group) return;
    var boxes = group.querySelectorAll('input[type="checkbox"][name$="-is_default"]');
    for (var i = 0; i < boxes.length; i++) {
      if (boxes[i] === changed) continue;
      if (boxes[i].closest('.empty-form')) continue;
      if (boxes[i].checked) {
        boxes[i].checked = false;
        var card = boxes[i].closest('.cz-card');
        var chip = card && card.querySelector('.cz-chip--red');
        if (chip && chip.textContent.trim() === 'Default') chip.remove();
      }
    }
  }

  /* ── Wiring ─────────────────────────────────────────────────────────────── */

  function init() {
    if (!document.querySelector(SIZES_GROUP)) return;

    document.addEventListener('click', function (ev) {
      var addSize = ev.target.closest && ev.target.closest('[data-cz-addsize]');
      if (addSize) {
        ev.preventDefault();
        var group = document.querySelector(SIZES_GROUP);
        var link = group && group.querySelector('.add-row a, a.add-row');
        if (!link) {
          window.alert('No more sizes can be added to this product.');
          return;
        }
        link.click();
        var cards = group.querySelectorAll('.cz-card:not(.cz-card--template)');
        var made = cards[cards.length - 1];
        if (made) made.scrollIntoView({ block: 'center', behavior: 'smooth' });
        return;
      }
      var jump = ev.target.closest && ev.target.closest('[data-cz-videojump]');
      if (jump) {
        ev.preventDefault();
        var card = jump.closest('.cz-card');
        if (card) jumpToVideo(card);
        return;
      }
      /* The picker is a <label> wrapping a file input now; let the browser
         open it. Only the old button shape still needs the jump behaviour. */
      var btn = ev.target.closest && ev.target.closest('button.cz-addphotos');
      if (!btn) return;
      ev.preventDefault();
      addPhotosTo(btn.getAttribute('data-variant-id'), btn.getAttribute('data-variant-name'));
    });

    document.addEventListener('change', function (ev) {
      var picker = ev.target;
      if (!picker.matches || !picker.matches('[data-cz-sizepicker]')) return;
      var card = picker.closest('.cz-card');
      if (card && picker.files && picker.files.length) addFilesToCard(card, picker.files);
      picker.value = '';
    });

    /* Dropping files anywhere on a card is the same thing as using its picker. */
    document.addEventListener('dragover', function (ev) {
      var card = ev.target.closest && ev.target.closest('.cz-card');
      if (!card || !card.querySelector('.cz-addphotos')) return;
      if (!ev.dataTransfer || (ev.dataTransfer.types || []).indexOf('Files') === -1) return;
      ev.preventDefault();
      ev.dataTransfer.dropEffect = 'copy';
      card.classList.add('cz-card--filedrag');
    });

    document.addEventListener('dragleave', function (ev) {
      var card = ev.target.closest && ev.target.closest('.cz-card');
      if (card && !card.contains(ev.relatedTarget)) card.classList.remove('cz-card--filedrag');
    });

    document.addEventListener('drop', function (ev) {
      var card = ev.target.closest && ev.target.closest('.cz-card');
      if (!card || !card.querySelector('.cz-addphotos')) return;
      if (!ev.dataTransfer || !ev.dataTransfer.files || !ev.dataTransfer.files.length) return;
      ev.preventDefault();
      card.classList.remove('cz-card--filedrag');
      addFilesToCard(card, ev.dataTransfer.files);
    });

    document.addEventListener('change', function (ev) {
      var el = ev.target;
      if (el && el.type === 'checkbox' && /-is_default$/.test(el.name || '')) {
        enforceSingleDefault(el);
      }
    });

    /* Django >= 4.1 fires this on the document after inlines.js inserts a row. */
    document.addEventListener('formset:added', function (ev) {
      var row = ev.target;
      if (row && row.closest && row.closest(SIZES_GROUP)) dressNewCard(row);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
