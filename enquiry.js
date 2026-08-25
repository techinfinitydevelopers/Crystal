/* Crystal Cook — Enquiry cart + Buy-Now (client-side, no backend).
   Public API: window.CrystalEnquiry { add, remove, setQty, items, count, clear, buy, renderBadge, autoSku }
   Wiring via event delegation:
     <button class="enq-add" data-id data-name data-brand data-cat [data-sku] [data-img] [data-qty-from="#sel"]>
     <button class="enq-buy" data-name [data-mk='[{"name","url","logo"}]']>
*/
(function () {
  "use strict";
  var KEY = "crystalEnquiry";
  var BRANDCODE = { crystal: "CRY", crystalina: "CRL", sparkmate: "SPK", valmate: "VAL" };

  function read() { try { return JSON.parse(localStorage.getItem(KEY)) || { items: [] }; } catch (e) { return { items: [] }; } }
  function write(d) { localStorage.setItem(KEY, JSON.stringify(d)); renderBadge(); }
  function items() { return read().items; }
  function count() { return items().reduce(function (s, i) { return s + (i.qty || 1); }, 0); }

  function hash(s) { var h = 0, i; s = String(s); for (i = 0; i < s.length; i++) { h = (h * 31 + s.charCodeAt(i)) >>> 0; } return h.toString(36).toUpperCase().slice(0, 4); }
  function autoSku(p) { var bc = BRANDCODE[String(p.brand || "").toLowerCase()] || "CC"; return bc + "-" + hash(p.id || p.name || "x"); }

  function add(p) {
    if (!p || !p.id) return;
    var d = read(), idx = d.items.findIndex(function (i) { return i.id === p.id; });
    var qty = Math.max(1, parseInt(p.qty, 10) || 1);
    if (idx >= 0) { d.items[idx].qty += qty; }
    else { d.items.push({ id: p.id, name: p.name || "", brand: p.brand || "", category: p.category || "", sku: p.sku || autoSku(p), img: p.img || "", qty: qty }); }
    write(d); toast("Added to enquiry");
  }
  function remove(id) { var d = read(); d.items = d.items.filter(function (i) { return i.id !== id; }); write(d); }
  function setQty(id, q) { var d = read(), idx = d.items.findIndex(function (i) { return i.id === id; }); if (idx >= 0) { d.items[idx].qty = Math.max(1, parseInt(q, 10) || 1); write(d); } }
  function clear() { write({ items: [] }); }

  function renderBadge() {
    var n = count();
    document.querySelectorAll(".enq-count").forEach(function (el) { el.textContent = n; el.classList.toggle("has", n > 0); });
  }

  /* ---------- toast ---------- */
  var toastTimer;
  function toast(msg) {
    var t = document.getElementById("enqToast");
    if (!t) { t = document.createElement("div"); t.id = "enqToast"; t.className = "enq-toast"; t.setAttribute("role", "status"); t.setAttribute("aria-live", "polite"); document.body.appendChild(t); }
    t.textContent = msg; t.classList.add("show");
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { t.classList.remove("show"); }, 2500);
  }

  /* ---------- marketplace modal ---------- */
  function defaultMarkets(name) {
    var q = encodeURIComponent(name || "Crystal Cook");
    // Amazon only. With a single entry buy() opens it directly instead of
    // showing a chooser, which is the whole point of there being one.
    return [
      { name: "Amazon", url: "https://www.amazon.in/s?k=" + q, logo: "brand-logos/amazon.svg" }
    ];
  }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }

  function buy(name, markets) {
    var list = (markets && markets.length) ? markets : defaultMarkets(name);
    if (list.length === 1) { window.open(list[0].url, "_blank", "noopener"); return; }
    openModal(name, list);
  }
  function escKey(e) { if (e.key === "Escape") closeModal(); }
  function openModal(name, list) {
    closeModal();
    var ov = document.createElement("div"); ov.className = "enq-modal-overlay"; ov.id = "enqModal";
    var rows = list.map(function (m) {
      return '<a class="mk-row" href="' + esc(m.url) + '" target="_blank" rel="noopener nofollow sponsored">' +
        (m.logo ? '<img src="' + esc(m.logo) + '" alt="">' : '') +
        '<span>' + esc(m.name) + '</span><span class="mk-arr">↗</span></a>';
    }).join("");
    ov.innerHTML = '<div class="enq-modal" role="dialog" aria-modal="true" aria-label="Choose marketplace">' +
      '<button class="enq-modal-x" aria-label="Close">&times;</button>' +
      '<h4>Buy “' + esc(name) + '”</h4><p>Choose where to purchase:</p>' +
      '<div class="mk-list">' + rows + '</div>' +
      '<span class="mk-note">Prices &amp; availability are set by the marketplace.</span></div>';
    document.body.appendChild(ov);
    requestAnimationFrame(function () { ov.classList.add("show"); });
    ov.addEventListener("click", function (e) { if (e.target === ov || e.target.closest(".enq-modal-x")) closeModal(); });
    document.addEventListener("keydown", escKey);
    var first = ov.querySelector(".mk-row"); if (first) first.focus();
  }
  function closeModal() {
    var ov = document.getElementById("enqModal");
    if (ov) { ov.classList.remove("show"); document.removeEventListener("keydown", escKey); setTimeout(function () { if (ov.parentNode) ov.parentNode.removeChild(ov); }, 220); }
  }

  /* ---------- click delegation ---------- */
  document.addEventListener("click", function (e) {
    var acc = e.target.closest(".mm-acc-tog");
    if (acc) { var li = acc.closest(".mm-acc"); if (li) { var open = li.classList.toggle("open"); acc.setAttribute("aria-expanded", open ? "true" : "false"); } return; }
    var a = e.target.closest(".enq-add");
    if (a) {
      e.preventDefault();
      var qty = 1, sel = a.getAttribute("data-qty-from");
      if (sel) { var qin = document.querySelector(sel); if (qin) qty = parseInt(qin.value, 10) || 1; }
      add({ id: a.dataset.id, name: a.dataset.name, brand: a.dataset.brand, category: a.dataset.cat, sku: a.dataset.sku, img: a.dataset.img, qty: qty });
      var lbl = a.querySelector(".enq-lbl");
      if (lbl && !a.dataset.busy) { a.dataset.busy = "1"; var old = lbl.textContent; a.classList.add("added"); lbl.textContent = "Added ✓"; setTimeout(function () { lbl.textContent = old; a.classList.remove("added"); delete a.dataset.busy; }, 1400); }
      return;
    }
    var b = e.target.closest(".enq-buy");
    if (b) {
      e.preventDefault();
      var mk = null; try { mk = b.dataset.mk ? JSON.parse(b.dataset.mk) : null; } catch (_) { mk = null; }
      buy(b.dataset.name, mk);
      return;
    }
  });

  /* ---------- injected styles (use site CSS variables) ---------- */
  var css =
    ".enq-link{display:inline-flex;align-items:center;gap:6px;position:relative;color:inherit;}" +
    ".enq-link svg{width:22px;height:22px;}" +
    ".enq-count{display:inline-grid;place-items:center;min-width:18px;height:18px;padding:0 5px;border-radius:100px;background:rgba(0,0,0,.18);color:#fff;font:700 11px var(--body,sans-serif);line-height:1;}" +
    ".enq-count.has{background:var(--red,#ED3338);}" +
    ".enq-toast{position:fixed;left:50%;top:18px;transform:translateX(-50%) translateY(-22px);background:var(--ink,#1A1A1A);color:#fff;padding:12px 22px;border-radius:100px;font:600 14px var(--body,sans-serif);box-shadow:0 16px 40px -16px rgba(0,0,0,.5);opacity:0;pointer-events:none;z-index:3000;transition:opacity .25s,transform .25s;}" +
    ".enq-toast.show{opacity:1;transform:translateX(-50%) translateY(0);}" +
    ".enq-modal-overlay{position:fixed;inset:0;background:rgba(10,10,10,.5);-webkit-backdrop-filter:blur(4px);backdrop-filter:blur(4px);display:grid;place-items:center;opacity:0;z-index:3000;padding:20px;transition:opacity .2s;}" +
    ".enq-modal-overlay.show{opacity:1;}" +
    ".enq-modal{background:#fff;border-radius:20px;padding:26px;width:min(420px,100%);box-shadow:0 30px 70px -30px rgba(0,0,0,.55);position:relative;transform:translateY(12px);transition:transform .2s;}" +
    ".enq-modal-overlay.show .enq-modal{transform:none;}" +
    ".enq-modal h4{font-family:var(--head);font-weight:700;font-size:20px;margin:0 0 4px;letter-spacing:-.01em;}" +
    ".enq-modal p{color:var(--muted,#666);font:600 13px var(--body);margin:0 0 16px;}" +
    ".enq-modal-x{position:absolute;top:12px;right:15px;background:none;border:none;font-size:26px;line-height:1;cursor:pointer;color:var(--muted,#888);}" +
    ".mk-list{display:grid;gap:8px;}" +
    ".mk-row{display:flex;align-items:center;gap:12px;padding:14px 16px;border:1.5px solid var(--line,#e7e7e7);border-radius:12px;font:700 15px var(--head);color:var(--ink,#1A1A1A);text-decoration:none;transition:background .2s,border-color .2s,color .2s;}" +
    ".mk-row:hover,.mk-row:focus-visible{background:var(--ink,#1A1A1A);color:#fff;border-color:var(--ink,#1A1A1A);outline:none;}" +
    ".mk-row img{height:20px;width:auto;max-width:96px;object-fit:contain;background:#fff;border-radius:4px;padding:2px 5px;}" +
    ".mk-row .mk-arr{margin-left:auto;}" +
    ".mk-note{display:block;margin-top:14px;font:600 11.5px var(--body);color:var(--muted,#888);}" +
    "@media (max-width:560px){.enq-modal-overlay{align-items:flex-end;}.enq-modal{width:100%;border-radius:20px 20px 0 0;}.mk-row{padding:16px;}}" +
    "@media (prefers-reduced-motion:reduce){.enq-toast,.enq-modal,.enq-modal-overlay{transition:none;}}";
  var st = document.createElement("style"); st.textContent = css; (document.head || document.documentElement).appendChild(st);

  if (document.readyState !== "loading") renderBadge();
  else document.addEventListener("DOMContentLoaded", renderBadge);

  window.CrystalEnquiry = { add: add, remove: remove, setQty: setQty, items: items, count: count, clear: clear, buy: buy, renderBadge: renderBadge, autoSku: autoSku };
})();
