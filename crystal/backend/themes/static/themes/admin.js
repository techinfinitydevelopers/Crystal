/* Festival themes list: the On column behaves like a set of radio switches.
   Switching one on switches the others off on screen and saves at once, so
   the list never asks the server to put two themes on. Without this script
   the server rule still holds (see OneThemeOnFormSet). */
(function () {
  "use strict";
  function init() {
    var form = document.getElementById("changelist-form");
    if (!form) return;
    var boxes = Array.prototype.slice.call(
      form.querySelectorAll('#result_list td.field-is_active input[type="checkbox"]'));
    if (!boxes.length) return;
    boxes.forEach(function (box) {
      box.setAttribute("role", "switch");
      box.addEventListener("change", function () {
        if (box.checked) {
          boxes.forEach(function (other) { if (other !== box) other.checked = false; });
        }
        var row = box.closest("tr");
        if (row) row.classList.add("ft-saving");
        var save = form.querySelector('[name="_save"]');
        if (save && form.requestSubmit) form.requestSubmit(save);
        else if (save) save.click();
      });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
