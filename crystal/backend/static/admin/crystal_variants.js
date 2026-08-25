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
      var btn = ev.target.closest && ev.target.closest('.cz-addphotos');
      if (!btn) return;
      ev.preventDefault();
      addPhotosTo(btn.getAttribute('data-variant-id'), btn.getAttribute('data-variant-name'));
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
