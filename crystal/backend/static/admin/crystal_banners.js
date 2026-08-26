/* Keeps the banner preview honest.
 *
 * Three things move it: the sliders, choosing a new file, and the page load.
 * The file case matters most -- an admin who cannot see the photo they just
 * picked is back to guessing, so it is read locally and shown before anything
 * is saved. */
(function () {
  'use strict';

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    var preview = document.querySelector('.cb-preview');
    if (!preview) return;

    var desktop = preview.querySelector('.cb-desktop .cb-shot');
    var mobile = preview.querySelector('.cb-mobile .cb-shot');
    var scrim = preview.querySelector('.cb-desktop .cb-scrim');

    if (scrim) {
      scrim.style.backgroundImage =
        preview.dataset.scrimH + ',' + preview.dataset.scrimV;
    }

    function bind(input) {
      var target = input.dataset.preview === 'mobile' ? mobile : desktop;
      var out = document.createElement('span');
      out.className = 'cb-focus-value';
      input.insertAdjacentElement('afterend', out);

      function sync() {
        var v = input.value;
        out.textContent = v + '%';
        if (target) target.style.backgroundPosition = v + '% center';
      }
      input.addEventListener('input', sync);
      sync();
    }
    Array.prototype.forEach.call(
      document.querySelectorAll('input.crystal-focus'), bind);

    // Show a newly chosen file straight away, before it is uploaded.
    var file = document.querySelector('input[type="file"][name="image"]');
    if (file) {
      file.addEventListener('change', function () {
        var f = file.files && file.files[0];
        if (!f) return;
        var url = URL.createObjectURL(f);
        if (desktop) desktop.style.backgroundImage = 'url(' + url + ')';
        if (mobile) mobile.style.backgroundImage = 'url(' + url + ')';

        // Warn about the one thing that cannot be fixed with a slider.
        var probe = new Image();
        probe.onload = function () {
          var note = preview.querySelector('.cb-shape-note');
          if (!note) {
            note = document.createElement('p');
            note.className = 'cb-hint cb-shape-note';
            preview.appendChild(note);
          }
          var ratio = probe.width / probe.height;
          if (probe.width < 1400) {
            note.textContent = 'This photo is only ' + probe.width + 'px across. '
              + 'The band is about 1265px wide, so it will look soft. 1980px or more is right.';
            note.style.color = '#b3261e';
          } else if (ratio < 3) {
            note.textContent = 'This photo is ' + ratio.toFixed(1) + ':1. A banner wants '
              + 'about 5:1 — anything squarer gets cropped so hard that only a sliver shows.';
            note.style.color = '#b3261e';
          } else {
            note.textContent = probe.width + '×' + probe.height + ' — '
              + ratio.toFixed(1) + ':1. Good shape for a banner.';
            note.style.color = '#1e7a3c';
          }
          URL.revokeObjectURL(probe.src);
        };
        probe.src = url;
      });
    }
  });
})();
