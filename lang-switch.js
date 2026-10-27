/* Site-wide language switcher, backed by Google's website translator.

   Picking a language sets Google's own "googtrans" cookie and reloads; Google's
   script, loaded on every page, then translates the whole page in the browser --
   text the page renders later from products.json or the dashboard included, since
   it watches the DOM. The cookie lives on the root path, so the choice follows
   the visitor from page to page until they pick English again.

   Google's own widget and banner are hidden; this file draws the picker: a globe
   button in the desktop header, and the same list inside the phone menu (the
   phone header has no room left beside the logo, search and menu buttons). */
(function () {
  "use strict";

  var LANGS = [
    ["en", "English", "🇬🇧"],
    ["ar", "العربية", "🇦🇪"],
    ["fr", "Français", "🇫🇷"],
    ["es", "Español", "🇪🇸"],
    ["de", "Deutsch", "🇩🇪"],
    ["pt", "Português", "🇧🇷"],
    ["it", "Italiano", "🇮🇹"],
    ["ru", "Русский", "🇷🇺"],
    ["tr", "Türkçe", "🇹🇷"],
    ["id", "Bahasa Indonesia", "🇮🇩"],
    ["ms", "Bahasa Melayu", "🇲🇾"],
    ["ja", "日本語", "🇯🇵"],
    ["ko", "한국어", "🇰🇷"],
    ["zh-CN", "简体中文", "🇨🇳"],
    ["nl", "Nederlands", "🇳🇱"],
    ["th", "ไทย", "🇹🇭"]
  ];

  function current() {
    var m = document.cookie.match(/(?:^|;\s*)googtrans=\/[^/;]+\/([^;]+)/);
    var code = m ? decodeURIComponent(m[1]) : "en";
    for (var i = 0; i < LANGS.length; i++) if (LANGS[i][0] === code) return code;
    return "en";
  }

  function setCookie(value) {
    var host = location.hostname;
    var parts = host.split(".");
    var apex = parts.length > 1 ? "." + parts.slice(-2).join(".") : "";
    var expire = value ? "" : "; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    var v = value ? "/en/" + value : "";
    // Google reads it from the host and the parent domain; set (or clear) both.
    document.cookie = "googtrans=" + v + "; path=/" + expire;
    if (apex && host !== "localhost") document.cookie = "googtrans=" + v + "; path=/; domain=" + apex + expire;
  }

  function choose(code) {
    if (code === current()) return;
    setCookie(code === "en" ? "" : code);
    location.reload();
  }

  /* ---------- styles ---------- */
  var css = [
    /* Google's own chrome: the top banner, its spacer, hover balloons, highlights */
    "body { top: 0 !important; }",
    ".skiptranslate > iframe, iframe.skiptranslate, .goog-te-banner-frame, #goog-gt-tt, .goog-te-balloon-frame,",
    ".VIpgJd-ZVi9od-ORHb-OEVmcd, .VIpgJd-ZVi9od-aZ2wEe-wOHMyf, .VIpgJd-yAWNEb-L7lbkb { display: none !important; }",
    ".goog-text-highlight, font[style] { background: none !important; box-shadow: none !important; }",
    "#google_translate_element { position: absolute !important; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }",
    /* the picker: right-hand end of the red support bar, which is fixed at the
       top of every page -- in the header it took room the menu needed
       ("Knowledge Centre" broke onto two lines) */
    ".lang-sw { position: fixed; top: 0; right: 16px; height: 34px; z-index: 103; display: flex; align-items: center; }",
    ".lang-sw-btn { display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px; border-radius: 999px; background: transparent; border: 0; cursor: pointer; color: #fff; font: inherit; font-size: 13px; font-weight: 600; line-height: 1; }",
    ".lang-sw-btn:hover, .lang-sw.open .lang-sw-btn { background: rgba(255,255,255,0.18); }",
    ".lang-sw-btn svg { width: 16px; height: 16px; flex: 0 0 auto; }",
    "@media (max-width: 560px) { .lang-sw { right: 8px; } .lang-sw-btn span { display: none; } .lang-sw-btn { padding: 6px; } }",
    ".lang-sw-menu { position: absolute; top: calc(100% + 4px); right: 0; z-index: 1000; min-width: 220px; max-height: min(70vh, 460px); overflow-y: auto; margin: 0; padding: 6px; list-style: none; background: #fff; border: 1px solid rgba(15,15,15,0.08); border-radius: 14px; box-shadow: 0 24px 50px -20px rgba(15,15,15,0.35); display: none; }",
    ".lang-sw.open .lang-sw-menu { display: block; }",
    ".lang-sw-menu button { width: 100%; display: flex; align-items: center; gap: 10px; padding: 9px 12px; border: 0; border-radius: 10px; background: none; cursor: pointer; font: inherit; font-size: 14px; color: #1a1a1a; text-align: left; }",
    ".lang-sw-menu button:hover { background: rgba(237,51,56,0.07); }",
    ".lang-sw-menu button[aria-current='true'] { background: rgba(237,51,56,0.1); color: #ED3338; font-weight: 600; }",
    ".lang-sw-flag { font-size: 18px; line-height: 1; }",
    /* translated, the menu stays on one line (and keeps its ▾ beside the word) */
    "html.translated-ltr #hdr .nav > ul > li > a, html.translated-rtl #hdr .nav > ul > li > a { white-space: nowrap; line-height: 1.2; }",
    /* phone menu list */
    ".mm-lang { margin: 18px 0 6px; }",
    ".mm-lang-h { display: block; font-size: 12px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; opacity: 0.7; margin-bottom: 10px; }",
    ".mm-lang-grid { display: flex; flex-wrap: wrap; gap: 8px; }",
    ".mm-lang-grid button { display: inline-flex; align-items: center; gap: 6px; padding: 8px 12px; border-radius: 999px; border: 1px solid rgba(255,255,255,0.25); background: transparent; color: inherit; font: inherit; font-size: 14px; cursor: pointer; }",
    ".mm-lang-grid button[aria-current='true'] { background: #ED3338; border-color: #ED3338; color: #fff; }"
  ].join("\n");
  var style = document.createElement("style");
  style.id = "lang-switch-css";
  style.textContent = css;
  document.head.appendChild(style);

  var GLOBE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>';

  function optionButtons(withNames) {
    var cur = current();
    return LANGS.map(function (l) {
      return '<button type="button" data-lang="' + l[0] + '" lang="' + l[0] + '"' +
        (l[0] === cur ? ' aria-current="true"' : "") + '>' +
        '<span class="lang-sw-flag">' + l[2] + '</span>' + (withNames ? '<span>' + l[1] + '</span>' : l[1]) +
        '</button>';
    }).join("");
  }

  function wire(root) {
    root.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-lang]");
      if (b) choose(b.getAttribute("data-lang"));
    });
  }

  function build() {
    var cur = current();
    var label = cur === "en" ? "EN" : cur.toUpperCase().replace("ZH-CN", "中文");

    if (!document.querySelector(".lang-sw")) {
      var wrap = document.createElement("div");
      wrap.className = "lang-sw notranslate";
      wrap.setAttribute("translate", "no");
      wrap.innerHTML =
        '<button type="button" class="lang-sw-btn" aria-haspopup="true" aria-expanded="false" aria-label="Choose language" title="Language">' +
        GLOBE + '<span>' + label + '</span></button>' +
        '<ul class="lang-sw-menu" role="menu"><li>' + optionButtons(true).split("</button>").join("</button></li><li>").replace(/<li>$/, "") + '</ul>';
      document.body.appendChild(wrap);
      var btn = wrap.querySelector(".lang-sw-btn");
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var open = wrap.classList.toggle("open");
        btn.setAttribute("aria-expanded", open ? "true" : "false");
      });
      document.addEventListener("click", function (e) {
        if (!wrap.contains(e.target)) { wrap.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); }
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") { wrap.classList.remove("open"); btn.setAttribute("aria-expanded", "false"); }
      });
      wire(wrap.querySelector(".lang-sw-menu"));
    }

    var mm = document.getElementById("mobileMenu");
    if (mm && !mm.querySelector(".mm-lang")) {
      var box = document.createElement("div");
      box.className = "mm-lang notranslate";
      box.setAttribute("translate", "no");
      box.innerHTML = '<span class="mm-lang-h">' + GLOBE.replace('aria-hidden="true"', 'aria-hidden="true" width="14" height="14" style="vertical-align:-2px;margin-right:6px"') +
        'Language</span><div class="mm-lang-grid">' + optionButtons(true) + '</div>';
      var list = mm.querySelector("ul");
      if (list && list.nextSibling) mm.insertBefore(box, list.nextSibling); else mm.appendChild(box);
      wire(box);
    }
  }

  /* ---------- whole sentences back for the translator ----------
     The pages' heading animations wrap every word in its own span, and Google
     translates each span on its own -- "Crafting Everyday Essentials with Care"
     came out as five unrelated dictionary words. With a translation on, the
     words are joined back into plain text first (a highlighted run such as
     "Crystal Catalogue" stays one span), so whole sentences are translated.
     Those headings then simply show instead of animating word by word. */
  function unsplit() {
    var roots = document.querySelectorAll("[data-split], [data-lines], .anim-text");
    Array.prototype.forEach.call(roots, function (el) {
      var marks = el.querySelectorAll(".w-mask, .word");
      if (!marks.length) return;
      Array.prototype.forEach.call(el.querySelectorAll(".w-mask"), function (m) {
        var w = m.querySelector(".word") || m;
        var extra = Array.prototype.filter.call(w.classList, function (c) { return c !== "word" && c !== "about-word"; });
        var node;
        if (extra.length) { node = document.createElement("span"); node.className = extra.join(" "); node.textContent = m.textContent; }
        else node = document.createTextNode(m.textContent);
        m.parentNode.replaceChild(node, m);
      });
      Array.prototype.forEach.call(el.querySelectorAll(".word"), function (w) {
        var extra = Array.prototype.filter.call(w.classList, function (c) { return c !== "word" && c !== "about-word"; });
        if (extra.length) { w.className = extra.join(" "); w.removeAttribute("style"); }
        else w.parentNode.replaceChild(document.createTextNode(w.textContent), w);
      });
      // a highlighted phrase was split into one span per word; join neighbours
      var kids = Array.prototype.slice.call(el.childNodes);
      for (var i = 0; i < kids.length; i++) {
        var a = kids[i];
        if (a.nodeType !== 1 || a.tagName !== "SPAN" || !a.className) continue;
        var j = i + 1;
        while (j + 1 < kids.length && kids[j].nodeType === 3 && !kids[j].nodeValue.trim() &&
               kids[j + 1].nodeType === 1 && kids[j + 1].tagName === "SPAN" && kids[j + 1].className === a.className) {
          a.textContent += " " + kids[j + 1].textContent;
          el.removeChild(kids[j]); el.removeChild(kids[j + 1]);
          j += 2;
        }
        i = j - 1;
      }
      el.normalize();
      el.style.opacity = ""; el.style.transform = "";
    });
  }

  /* ---------- brand names stay as they are ----------
     "Crystal" came back as Cristal / Kristall. Every brand name in the page's
     text -- including product cards the page draws later -- is wrapped in a
     notranslate span before Google gets to it. */
  /* The spaces either side go inside the span too: Google trims the text next
     to an untranslated span, which glued "Crystal" to the next word. */
  var BRAND = /\s?\b(?:Crystalina|Crystal|SparkMate|Sparkmate|ValMate|Valmate)\b\s?/gi;
  var SKIP = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, INPUT: 1, SELECT: 1, OPTION: 1, NOSCRIPT: 1, SVG: 1 };

  function protect(root) {
    if (!root || (root.nodeType !== 1 && root.nodeType !== 3)) return;
    var nodes = [];
    if (root.nodeType === 3) nodes.push(root);
    else {
      if (SKIP[root.tagName] || (root.closest && root.closest(".notranslate"))) return;
      var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
        acceptNode: function (n) {
          var p = n.parentNode;
          if (!p || SKIP[p.tagName] || (p.closest && p.closest(".notranslate"))) return NodeFilter.FILTER_REJECT;
          BRAND.lastIndex = 0;
          return BRAND.test(n.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
        }
      });
      var n;
      while ((n = walker.nextNode())) nodes.push(n);
    }
    nodes.forEach(function (t) {
      var p = t.parentNode;
      if (!p || (p.closest && p.closest(".notranslate"))) return;
      var text = t.nodeValue, frag = document.createDocumentFragment(), last = 0, m;
      BRAND.lastIndex = 0;
      while ((m = BRAND.exec(text))) {
        if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        var s = document.createElement("span");
        s.className = "notranslate";
        s.setAttribute("translate", "no");
        s.textContent = m[0];
        frag.appendChild(s);
        last = m.index + m[0].length;
      }
      if (!last) return;
      if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
      p.replaceChild(frag, t);
    });
  }

  function watchBrands() {
    protect(document.body);
    new MutationObserver(function (records) {
      for (var i = 0; i < records.length; i++) {
        var added = records[i].addedNodes;
        for (var j = 0; j < added.length; j++) protect(added[j]);
      }
    }).observe(document.body, { childList: true, subtree: true });
  }

  /* ---------- the menu, worded by hand ----------
     Google gets one- or two-word menu labels wrong without context ("Products"
     became Italian "Libri", books; "About" a bare preposition in Arabic, Russian
     and Korean), and long renderings broke the header onto two lines. The top
     menu, the phone menu and the Contact button use these instead. */
  var MENU = {
    "About":            { ar: "من نحن", fr: "À propos", es: "Nosotros", de: "Über uns", pt: "Sobre nós", it: "Chi siamo", ru: "О нас", tr: "Hakkımızda", id: "Tentang Kami", ms: "Tentang Kami", ja: "会社概要", ko: "회사 소개", "zh-CN": "关于我们", nl: "Over ons", th: "เกี่ยวกับเรา" },
    "Products":         { ar: "المنتجات", fr: "Produits", es: "Productos", de: "Produkte", pt: "Produtos", it: "Prodotti", ru: "Продукция", tr: "Ürünler", id: "Produk", ms: "Produk", ja: "製品", ko: "제품", "zh-CN": "产品", nl: "Producten", th: "สินค้า" },
    "Brands":           { ar: "العلامات", fr: "Marques", es: "Marcas", de: "Marken", pt: "Marcas", it: "Marchi", ru: "Бренды", tr: "Markalar", id: "Merek", ms: "Jenama", ja: "ブランド", ko: "브랜드", "zh-CN": "品牌", nl: "Merken", th: "แบรนด์" },
    "Catalogue":        { ar: "الكتالوج", fr: "Catalogue", es: "Catálogo", de: "Katalog", pt: "Catálogo", it: "Catalogo", ru: "Каталог", tr: "Katalog", id: "Katalog", ms: "Katalog", ja: "カタログ", ko: "카탈로그", "zh-CN": "产品目录", nl: "Catalogus", th: "แคตตาล็อก" },
    "Knowledge Centre": { ar: "مركز المعرفة", fr: "Conseils", es: "Consejos", de: "Wissen", pt: "Dicas", it: "Consigli", ru: "Полезное", tr: "Bilgi Merkezi", id: "Pusat Info", ms: "Pusat Info", ja: "お役立ち情報", ko: "지식 센터", "zh-CN": "知识中心", nl: "Kennisbank", th: "ศูนย์ความรู้" },
    "Contact Us":       { ar: "اتصل بنا", fr: "Contact", es: "Contacto", de: "Kontakt", pt: "Contato", it: "Contatti", ru: "Контакты", tr: "İletişim", id: "Kontak", ms: "Hubungi Kami", ja: "お問い合わせ", ko: "문의하기", "zh-CN": "联系我们", nl: "Contact", th: "ติดต่อเรา" }
  };

  function relabel(code) {
    var targets = document.querySelectorAll(
      "#hdr .nav > ul > li > a, #hdr .nav-right .btn-outline, #mobileMenu > ul > li > a.mm-link, #mobileMenu > ul > li > button.mm-link");
    Array.prototype.forEach.call(targets, function (el) {
      for (var n = el.firstChild; n; n = n.nextSibling) {
        if (n.nodeType !== 3 || !n.nodeValue.trim()) continue;
        var key = n.nodeValue.trim();
        var word = MENU[key] && MENU[key][code];
        if (word) {
          n.nodeValue = n.nodeValue.replace(key, word);
          el.classList.add("notranslate");
          el.setAttribute("translate", "no");
        }
        break;
      }
    });
  }

  /* ---------- Google's translator, only when a language other than English is on ---------- */
  function loadGoogle() {
    if (current() === "en" || document.getElementById("google_translate_element")) return;
    relabel(current());
    unsplit();
    window.addEventListener("load", unsplit);
    watchBrands();
    var holder = document.createElement("div");
    holder.id = "google_translate_element";
    document.body.appendChild(holder);
    window.googleTranslateElementInit = function () {
      /* global google */
      new google.translate.TranslateElement({
        pageLanguage: "en",
        includedLanguages: LANGS.slice(1).map(function (l) { return l[0]; }).join(","),
        autoDisplay: false
      }, "google_translate_element");
    };
    var s = document.createElement("script");
    s.src = "https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit";
    s.async = true;
    document.body.appendChild(s);
  }

  function start() { build(); loadGoogle(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
