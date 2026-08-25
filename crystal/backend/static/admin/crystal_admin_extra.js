/* ==========================================================================
   Crystal Admin — live changelist search
   --------------------------------------------------------------------------
   Approach, and why this one:

   jazzmin renders the whole changelist toolbar as a single GET <form
   id="changelist-search">. That form already contains every piece of state
   the changelist carries — the list_filter <select>s, and hidden <input>s for
   everything else (ordering `o`, `_popup`, and any param not claimed by a
   filter spec). See jazzmin's templates/admin/change_list.html and the
   `admin_extra_filters` tag.

   One jazzmin detail makes this decisive. Its filter <select>s are rendered
   with NO name attribute at all — only data-name — and jazzmin/js/change_list.js
   copies the SELECTED OPTION's data-name onto the select on every change
   (so picking brand "Crystalina" turns the select into
   name="brand__id__exact" value="2", and picking the blank option removes the
   name again). Hand-assembling a query string would mean reimplementing that
   mapping; serialising the form gets it for free and stays correct even if
   jazzmin changes how it encodes a filter.

   So the safest way to keep filters, ordering and popup state intact is not
   to hand-assemble a query string — it is to serialise the form the server
   itself built, exactly as a real submit would, and re-request the same URL.
   That means:

     * nothing to keep in sync when a filter is added to ProductAdmin;
     * the server, not this file, decides what a valid changelist URL is;
     * the response is the identical HTML the plain form submit produces, so a
       live search and an Enter-key search can never disagree.

   The alternative — a bespoke JSON endpoint — would mean a second code path
   for rendering rows, duplicating list_display, the admin actions column and
   the pagination, and it would drift from the real changelist the moment
   anyone edits products/admin.py. Not worth it for a 530-row table.

   We swap only #changelist, then history.replaceState the URL. #changelist is
   exactly the right unit: it holds the actions bar, #result_list, the
   "N products" count (.dataTables_info — jazzmin never renders the
   `{% if show_result_count %}` span in its toolbar, because that variable is
   not in the change_list context, so .dataTables_info is the only result
   count on the page) and the paginator, whose links the server already builds
   with every filter param baked in. The filter <select>s stay outside the
   swap, so select2 and the user's focus survive.

   replaceState rather than
   pushState deliberately: typing a 6-character query should not push six (or
   even two) entries onto the back stack. Back therefore leaves the changelist
   entirely, which is what a user pressing Back expects.

   Progressive enhancement: everything here is additive. With JS off the form
   is an ordinary GET form and the Search button works as it always did. We
   never preventDefault a submit, so Enter and the Search button keep doing a
   full, native page load.
   ========================================================================== */

(function () {
  "use strict";

  var DEBOUNCE_MS = 350;

  /* Once the busy state is shown it is held for at least this long. Without
     it the feedback is real but imperceptible: measured on localhost, the
     spinner's class went on and off inside ~20ms, so its fade-in only ever
     reached opacity 0.11 and the table never visibly dimmed — a table that
     changes with no feedback, which is the thing we were trying to avoid. */
  var MIN_BUSY_MS = 300;

  /* The table dim is held back briefly so a fast response does not strobe the
     whole result area on every search. The spinner alone covers that case. */
  var DIM_DELAY_MS = 120;

  document.addEventListener("DOMContentLoaded", function () {
    initLiveSearch();
  });

  function initLiveSearch() {
    var form = document.getElementById("changelist-search");
    var input = document.getElementById("searchbar");
    var changelist = document.getElementById("changelist");

    // Only changelists that actually have a search box and a result area.
    if (!form || !input || !changelist) {
      return;
    }
    if (form.dataset.crxLive === "1") {
      return;
    }
    form.dataset.crxLive = "1";

    // Wrap the input so the spinner can sit inside it.
    var wrap = document.createElement("span");
    wrap.className = "crx-search-wrap";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    var spinner = document.createElement("span");
    spinner.className = "crx-spinner";
    spinner.setAttribute("aria-hidden", "true");
    wrap.appendChild(spinner);

    // Announce result counts for screen readers, which get no benefit from
    // the spinner or the dimming.
    var live = document.createElement("span");
    live.className = "crx-sr";
    live.setAttribute("aria-live", "polite");
    live.setAttribute("role", "status");
    form.appendChild(live);

    var timer = null;
    var controller = null;
    var lastUrl = window.location.pathname + window.location.search;

    input.setAttribute("autocomplete", "off");

    input.addEventListener("input", function () {
      schedule();
    });

    // A cleared field via the native "x" on type=search fires `search`.
    input.addEventListener("search", function () {
      schedule();
    });

    // Escape abandons an in-flight live search rather than leaving the table
    // dimmed behind a query the user has given up on.
    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        cancel();
      }
      // Enter is NOT intercepted — the native submit runs, which is the
      // no-JavaScript path and the thing that must never break.
    });

    // Changing a filter dropdown is a navigation, not a search; jazzmin's own
    // change_list.js already submits the form for those. Left alone.

    function schedule() {
      window.clearTimeout(timer);
      timer = window.setTimeout(run, DEBOUNCE_MS);
    }

    function cancel() {
      window.clearTimeout(timer);
      if (controller) {
        controller.abort();
        controller = null;
      }
      setBusy(false);
    }

    var busySince = 0;
    var dimTimer = null;
    var releaseTimer = null;

    function setBusy(busy) {
      if (busy) {
        window.clearTimeout(releaseTimer);
        if (!wrap.classList.contains("is-busy")) {
          busySince = Date.now();
          wrap.classList.add("is-busy");
          changelist.setAttribute("aria-busy", "true");
          window.clearTimeout(dimTimer);
          dimTimer = window.setTimeout(function () {
            changelist.classList.add("crx-loading");
          }, DIM_DELAY_MS);
        }
        return;
      }

      // Hold the busy state for the remainder of MIN_BUSY_MS so the user
      // actually sees that something happened.
      var elapsed = Date.now() - busySince;
      var wait = Math.max(0, MIN_BUSY_MS - elapsed);
      window.clearTimeout(releaseTimer);
      releaseTimer = window.setTimeout(function () {
        window.clearTimeout(dimTimer);
        wrap.classList.remove("is-busy");
        changelist.classList.remove("crx-loading");
        changelist.setAttribute("aria-busy", "false");
      }, wait);
    }

    /**
     * Build the URL a real submit of this form would produce, minus the page
     * number (a new query always belongs on page 1) and minus empty values
     * (so an empty search box gives a clean ?-less URL).
     */
    function buildUrl() {
      var data = new FormData(form);
      var params = new URLSearchParams();
      data.forEach(function (value, key) {
        if (key === "p") {
          return; // reset pagination on a new query
        }
        if (value === null || String(value).length === 0) {
          return;
        }
        params.append(key, value);
      });
      var qs = params.toString();
      return window.location.pathname + (qs ? "?" + qs : "");
    }

    function run() {
      var url = buildUrl();
      if (url === lastUrl) {
        setBusy(false);
        return;
      }

      if (controller) {
        controller.abort();
      }
      controller = new AbortController();
      var mine = controller;

      setBusy(true);

      window
        .fetch(url, {
          credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          signal: mine.signal,
        })
        .then(function (response) {
          if (!response.ok) {
            throw new Error("HTTP " + response.status);
          }
          return response.text();
        })
        .then(function (html) {
          if (mine.signal.aborted) {
            return;
          }
          apply(html, url);
          lastUrl = url;
          // Keep the address bar honest without flooding the back stack.
          window.history.replaceState(
            { crxLiveSearch: true },
            "",
            url
          );
        })
        .catch(function (error) {
          if (error && error.name === "AbortError") {
            return; // superseded by a newer keystroke
          }
          // Anything else: leave the current results in place rather than
          // blanking the table, and let the user fall back to Enter.
          if (window.console) {
            window.console.warn("Live search failed, falling back:", error);
          }
        })
        .finally(function () {
          if (controller === mine) {
            controller = null;
            setBusy(false);
          }
        });
    }

    function apply(html, url) {
      var doc = new DOMParser().parseFromString(html, "text/html");

      var fresh = doc.getElementById("changelist");
      if (!fresh) {
        // Not a changelist response (a login redirect, most likely). Hand the
        // user to the real page rather than silently doing nothing.
        window.location.assign(url);
        return;
      }

      changelist.innerHTML = fresh.innerHTML;

      // The result count (.dataTables_info, e.g. "427 products") and the
      // paginator both live inside #changelist, so the swap above already
      // updated them. Read the count back out purely to announce it.
      var count = changelist.querySelector(".dataTables_info");
      var rows = changelist.querySelectorAll("#result_list tbody tr").length;
      live.textContent = count
        ? count.textContent.replace(/\s+/g, " ").trim()
        : rows + " results";

      // The admin action checkboxes and the action <select> were bound to
      // nodes we just replaced. Re-bind both.
      reinitActions();
      reinitSelect2();
    }

    /**
     * jazzmin's change_list.js select2-ifies `.actions select` on ready. That
     * select is inside #changelist, so a swap leaves an unstyled native one.
     */
    function reinitSelect2() {
      // django.jQuery and the global jQuery are two separate instances, and
      // jazzmin registers select2 on the GLOBAL one. Picking django.jQuery
      // first silently did nothing — measured: the action <select> came back
      // unstyled after every swap. Choose whichever instance actually has the
      // plugin.
      var jq = null;
      var candidates = [
        window.jQuery,
        window.django && window.django.jQuery ? window.django.jQuery : null,
      ];
      for (var i = 0; i < candidates.length; i++) {
        if (candidates[i] && typeof candidates[i].fn.select2 === "function") {
          jq = candidates[i];
          break;
        }
      }
      if (!jq) {
        return;
      }
      try {
        jq("#changelist .actions select")
          .addClass("form-control")
          .select2({ width: "element" });
      } catch (error) {
        if (window.console) {
          window.console.warn("Could not re-bind select2:", error);
        }
      }
    }

    function reinitActions() {
      if (typeof window.Actions !== "function") {
        return;
      }
      if (!document.getElementById("result_list")) {
        return; // zero results: no table, nothing to bind
      }
      if (!document.getElementById("action-toggle")) {
        return; // actions disabled for this changelist
      }
      try {
        window.Actions(
          document.querySelectorAll("#result_list tr input.action-select")
        );
      } catch (error) {
        if (window.console) {
          window.console.warn("Could not re-bind admin actions:", error);
        }
      }
    }
  }
})();
