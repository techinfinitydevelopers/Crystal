/* Crystal admin — tag chip input.
 *
 * Vanilla, no dependency. Every listener is delegated off `document`, so a
 * widget that gets cloned into a new inline-formset row works with no extra
 * wiring — there is nothing bound to the individual nodes.
 *
 * The hidden input ([data-tags-value]) is the only thing that posts; this file
 * keeps it in sync with the chips on screen.
 */
(function () {
  'use strict';

  var ROOT = '[data-crystal-tags]';

  function root(el) {
    return el ? el.closest(ROOT) : null;
  }

  /* Current tags, read back off the chips in the DOM. */
  function readTags(box) {
    var tags = [];
    box.querySelectorAll('[data-tags-chip]').forEach(function (chip) {
      tags.push(chip.getAttribute('data-tag'));
    });
    return tags;
  }

  function syncHidden(box) {
    var hidden = box.querySelector('[data-tags-value]');
    if (hidden) hidden.value = JSON.stringify(readTags(box));
  }

  function hasTag(box, tag) {
    var wanted = tag.toLowerCase();
    return readTags(box).some(function (existing) {
      return existing.toLowerCase() === wanted;
    });
  }

  function makeChip(tag) {
    var chip = document.createElement('span');
    chip.className = 'crystal-tags__chip';
    chip.setAttribute('data-tags-chip', '');
    chip.setAttribute('data-tag', tag);

    var text = document.createElement('span');
    text.className = 'crystal-tags__chip-text';
    text.textContent = tag;

    var remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'crystal-tags__remove';
    remove.setAttribute('data-tags-remove', '');
    remove.setAttribute('aria-label', 'Remove tag ' + tag);
    remove.title = 'Remove';
    remove.textContent = '×';

    chip.appendChild(text);
    chip.appendChild(remove);
    return chip;
  }

  /* Add one or many tags. Blanks and case-insensitive duplicates are dropped,
   * which mirrors what TagListField.clean() does on the server. */
  function addTags(box, raw) {
    var chips = box.querySelector('[data-tags-chips]');
    if (!chips) return;
    String(raw).split(/[,\n\r]+/).forEach(function (part) {
      var tag = part.trim();
      if (!tag || hasTag(box, tag)) return;
      chips.appendChild(makeChip(tag));
    });
    syncHidden(box);
  }

  function removeLast(box) {
    var all = box.querySelectorAll('[data-tags-chip]');
    if (!all.length) return;
    all[all.length - 1].remove();
    syncHidden(box);
  }

  /* Enter / comma commit the typed tag; Backspace on an empty box eats the
   * last chip; Escape clears whatever is half-typed. */
  document.addEventListener('keydown', function (e) {
    var input = e.target;
    if (!input || !input.matches || !input.matches('[data-tags-input]')) return;
    var box = root(input);
    if (!box) return;

    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();          // Enter must not submit the whole form
      addTags(box, input.value);
      input.value = '';
    } else if (e.key === 'Backspace' && input.value === '') {
      e.preventDefault();
      removeLast(box);
    } else if (e.key === 'Escape' && input.value !== '') {
      e.preventDefault();
      input.value = '';
    }
  });

  /* Leaving the box commits what is sitting in it, so a typed-but-not-entered
   * tag is not silently lost on save. */
  document.addEventListener('focusout', function (e) {
    var input = e.target;
    if (!input || !input.matches || !input.matches('[data-tags-input]')) return;
    var box = root(input);
    if (!box || !input.value.trim()) return;
    addTags(box, input.value);
    input.value = '';
  });

  document.addEventListener('paste', function (e) {
    var input = e.target;
    if (!input || !input.matches || !input.matches('[data-tags-input]')) return;
    var text = (e.clipboardData || window.clipboardData).getData('text');
    if (!text || !/[,\n\r]/.test(text)) return;   // a plain word: let it type
    e.preventDefault();
    var box = root(input);
    if (box) addTags(box, text);
  });

  document.addEventListener('click', function (e) {
    var target = e.target;
    if (!target || !target.closest) return;

    var remove = target.closest('[data-tags-remove]');
    if (remove) {
      e.preventDefault();
      var box = root(remove);
      var chip = remove.closest('[data-tags-chip]');
      if (chip) chip.remove();
      if (box) syncHidden(box);
      return;
    }

    // clicking the empty space of the box focuses the text input
    var boxEl = target.closest('[data-tags-box]');
    if (boxEl && !target.closest('[data-tags-chip]')) {
      var field = boxEl.querySelector('[data-tags-input]');
      if (field) field.focus();
    }
  });

  /* A cloned formset row arrives carrying the original row's hidden value;
   * re-sync every widget once the DOM is ready so the two always agree. */
  function syncAll() {
    document.querySelectorAll(ROOT).forEach(syncHidden);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', syncAll);
  } else {
    syncAll();
  }
}());
