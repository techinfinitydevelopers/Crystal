  const RM = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const U = "https://proj.leo9studio.in/projects/crystal-wp/wp-content/uploads/";

  const BRANDS = {
    crystal:    { name: "Crystal",    tagline: "World of Kitchenware", story: "It began in 1971 with a simple gas lighter and a belief that everyday Indian homes deserved better. Today Crystal spans knives, tools, cookware and appliances — the flagship of the family.", img: U + "2026/04/Knife-2.jpg" },
    crystalina: { name: "Crystalina", tagline: "Splendid Finish",      story: "Crystalina brings a splendid mirror finish to serveware and dinnerware — premium stainless steel that makes every meal feel like an occasion.", img: "about-assets/prod-3.jpg" },
    sparkmate:  { name: "SparkMate",  tagline: "Cleaning Simplified",  story: "SparkMate makes a spotless home effortless — spin mops, wipers and brushes engineered for fast, low-effort cleaning.", img: U + "2026/04/Spin-Mops-2.jpg" },
    valmate:    { name: "ValMate",    tagline: "Value for Money",      story: "ValMate delivers dependable everyday essentials at honest prices — practical storage, flasks and home solutions built for real value.", img: U + "2026/04/10.jpg" },
  };
  window.crystalSync && window.crystalSync.brands(BRANDS);
  const CAT_LABEL = { cookware:"Cookware", kitchenware:"Kitchenware", "water-bottle":"Water Bottle", "oil-pourer":"Oil Pourer & Sprayer", "wood-range":"Wooden Range", "pressure-cooker":"Pressure Cooker", "electric-appliances":"Electric Appliances", cooktop:"Cooktop", "lunch-box":"Lunch Box", "cleaning-aid":"Cleaning Aid" };
  window.crystalSync && window.crystalSync.categories(null, CAT_LABEL);

  const ICONS = {
    heat:'<path d="M12 3c3 3.5 4.5 5.5 4.5 8a4.5 4.5 0 0 1-9 0c0-1.6.8-2.8 2.2-4 .4 1.2 1.2 1.5 1.6.7.5-.9.1-3.1.7-4.7z"/>',
    shield:'<path d="M12 3l7 3v5c0 4.5-3 7.8-7 9-4-1.2-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/>',
    induction:'<circle cx="12" cy="12" r="8.5"/><path d="M8.5 12a3.5 3.5 0 0 1 7 0 1.8 1.8 0 0 1-3.5 0"/>',
    leaf:'<path d="M5 19c0-8 6-13 14-13 0 8-5 14-13 14"/><path d="M5.5 18.5c3-5 7-8 11-9"/>',
    blade:'<path d="M4 15C11 13 17 7 20.5 3c.8 3.8-.6 9.4-7.5 13.5z"/><path d="M4 15l-1.6 4.4 4.4-1.6"/>',
    precision:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.4"/><path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3"/>',
    grip:'<path d="M8.5 11V5.6a1.5 1.5 0 0 1 3 0V10m0 0V4.6a1.5 1.5 0 0 1 3 0V10m0 .5V7a1.5 1.5 0 0 1 3 0v7a6 6 0 0 1-6 6h-.6a6 6 0 0 1-5-2.7L5.4 14.4"/>',
    spin:'<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v4h-4"/>',
    lock:'<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    stack:'<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    shine:'<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
    power:'<path d="M13 3L5 14h6l-1 7 8-11h-6z"/>',
    refill:'<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v4h-4"/>',
  };

  const CAT_TPL = {
    cookware: { features:[["heat","Even Heat Distribution","Triply, heavy-gauge base spreads heat uniformly for consistent, no-hotspot cooking."],["shield","Built to Last","Premium-grade metal and rugged construction engineered for years of daily use."],["induction","Induction & Gas Ready","Works flawlessly across induction, gas and most cooktops."],["leaf","Healthier Cooking","Low-oil, food-safe surfaces let you cook lighter without losing taste."]], specs:{Material:"Triply stainless steel",Finish:"Mirror polish",Compatibility:"Induction & gas",Handle:"Stay-cool riveted",Care:"Hand wash recommended",Warranty:"5 years"}, variants:["24 cm","26 cm","28 cm"] },
    cutlery: { features:[["blade","Surgical-Grade Steel","Forged from high-carbon surgical stainless steel that holds its edge for years."],["precision","Laser-Honed Edge","Precision-ground blade for clean, effortless cuts every time."],["grip","Ergonomic Grip","Balanced, comfortable handle designed for safe, fatigue-free use."],["shield","Rust & Stain Resistant","Stays bright and hygienic wash after wash."]], specs:{Material:"Surgical stainless steel",Edge:"Laser honed",Handle:"Ergonomic polymer",Care:"Hand wash",Warranty:"2 years"}, variants:["Single","Set of 3","Set of 5"] },
    cleaning: { features:[["spin","360° Spin Action","Effortless hands-free wringing for a faster, cleaner mop."],["grip","Comfort Handle","Lightweight, sturdy handle that's easy to manoeuvre."],["shield","Durable Build","Rust-proof materials made to last through daily cleaning."],["leaf","Microfibre Power","High-absorbency microfibre lifts dirt and dries fast."]], specs:{Material:"ABS + stainless steel","Mop Head":"Microfibre",Bucket:"Single-bucket spin",Care:"Rinse & air dry",Warranty:"1 year"}, variants:["Standard","Pro"] },
    storage: { features:[["lock","Airtight Seal","Leak-proof, airtight lids lock freshness in and spills out."],["stack","Stackable & Modular","Space-saving shapes that nest and stack neatly."],["leaf","Food-Safe & BPA-Free","Made from food-grade, BPA-free materials safe for everyday use."],["shield","Built to Last","Tough, crack-resistant build for years of kitchen duty."]], specs:{Material:"Food-grade / steel",Seal:"Airtight silicone",Compatibility:"Fridge & freezer safe",Care:"Dishwasher safe",Warranty:"1 year"}, variants:["Small","Medium","Large","Set"] },
    flasks: { features:[["heat","24-Hour Insulation","Double-wall vacuum keeps drinks hot or cold for up to 24 hours."],["lock","Leak-Proof Lid","Secure, spill-proof closure for bags and travel."],["shield","Rugged Stainless Body","Dent-resistant 18/8 steel built for life on the move."],["leaf","Pure Taste","Food-grade interior keeps flavours clean, with no aftertaste."]], specs:{Material:"18/8 stainless steel",Insulation:"Double-wall vacuum",Retention:"Hot/Cold 24 hrs",Care:"Hand wash",Warranty:"1 year"}, variants:["500 ml","750 ml","1 L"] },
    serveware: { features:[["shine","Splendid Mirror Finish","High-polish stainless steel that elevates every table."],["heat","Stay-Warm Insulation","Double-wall builds keep food warm for hours."],["shield","Heavy-Gauge Build","Sturdy, premium-weight steel made for daily dining."],["leaf","Food-Safe Steel","Hygienic, rust-free and easy to clean."]], specs:{Material:"Stainless steel",Finish:"Mirror polish",Type:"Serveware",Care:"Hand wash",Warranty:"2 years"}, variants:["Small","Medium","Large"] },
    lighters: { features:[["power","Sure, Single-Press Spark","Reliable ignition every time, even for deep burners."],["shield","Stainless-Steel Body","Premium, corrosion-resistant build that lasts."],["refill","Refillable","Refillable gas design for long, economical life."],["grip","Comfort Grip","Balanced, easy-hold body for safe lighting."]], specs:{Material:"Stainless steel",Mechanism:"Flintless / refillable",Care:"Wipe clean",Warranty:"6 months"}, variants:["Standard","305 mm","380 mm"] },
    appliances: { features:[["power","Powerful Performance","Engineered motors and elements for fast, efficient results."],["shield","Safe & Reliable","Auto cut-off and quality components for peace of mind."],["precision","Smart Controls","Intuitive controls for effortless everyday use."],["leaf","Energy Efficient","Designed to deliver more while drawing less power."]], specs:{Material:"Stainless steel / ABS",Power:"Energy efficient",Compatibility:"220–240V",Care:"Wipe clean",Warranty:"1 year"}, variants:["Standard"] },
    cooktop: { features:[["heat","Even Flame Distribution","Engineered burners deliver a steady, even flame for consistent cooking."],["shield","Rust-Resistant Build","Toughened top and sturdy pan supports built for daily use."],["power","Strong Ignition","Reliable spark ignition gets your flame going instantly, every time."],["leaf","Efficient Burners","Optimised burner design cooks faster while using less gas."]], specs:{Material:"Toughened glass / stainless steel",Burners:"Multiple, brass",Ignition:"Auto / manual spark",Care:"Wipe clean",Warranty:"1 year"}, variants:["2 Burner","3 Burner","4 Burner"] },
    "oil-pourer": { features:[["precision","Controlled Pour","Fine-flow spout or nozzle for precise, mess-free pouring."],["shield","Leak-Proof Design","Secure cap and seal keep oil in the bottle, not on your counter."],["leaf","Healthier Cooking","Portion-controlled flow helps you cook with less oil."],["grip","Easy-Grip Body","Comfortable handle and body for one-handed, effortless use."]], specs:{Material:"Stainless steel / glass",Capacity:"500 ml – 1 L",Type:"Pourer / Sprayer",Care:"Hand wash",Warranty:"6 months"}, variants:["500 ml","750 ml","1 L"] },
    "wood-range": { features:[["leaf","Natural Teakwood","Crafted from genuine teakwood for a warm, natural finish."],["shine","Elegant Finish","Smooth, handcrafted finish that elevates any table setting."],["shield","Sturdy & Durable","Solid construction built to withstand daily use."],["grip","Table-Safe Design","Protects table surfaces from heat, moisture and scratches."]], specs:{Material:"Teakwood",Finish:"Natural polish",Type:"Serveware / décor",Care:"Wipe with a dry cloth",Warranty:"Not applicable"}, variants:["Standard"] },
    peelers: { features:[["blade","Sharp Peeling Edge","Precision blade peels fruits and vegetables quickly and evenly."],["grip","Ergonomic Handle","Comfortable, non-slip grip for safe, effortless peeling."],["shield","Rust-Resistant Steel","Stainless steel blade stays sharp and hygienic wash after wash."],["leaf","Lightweight & Easy","Light body makes everyday peeling quick and fatigue-free."]], specs:{Material:"Stainless steel",Blade:"Fixed / swivel",Handle:"Ergonomic",Care:"Hand wash",Warranty:"6 months"}, variants:["Standard"] },
    "chopping-boards": { features:[["shield","Knife-Friendly Surface","Durable surface that's gentle on blade edges."],["leaf","Food-Safe Material","Hygienic, food-grade material safe for daily food prep."],["grip","Non-Slip Base","Stable base keeps the board steady while you cut."],["stack","Easy to Store","Compact, lightweight design that's easy to store and clean."]], specs:{Material:"Plastic / wood",Size:"Standard / large",Care:"Wash with mild soap",Warranty:"Not applicable"}, variants:["Small","Medium","Large"] },
    trolleys: { features:[["stack","Multi-Tier Storage","Multiple tiers give you organised storage for kitchen essentials."],["spin","Smooth-Rolling Wheels","Easy-glide castor wheels for effortless movement around the kitchen."],["shield","Sturdy Frame","Strong, rust-resistant frame built to carry daily loads."],["grip","Space-Saving Design","Compact footprint that fits neatly into any kitchen corner."]], specs:{Material:"Stainless steel / metal",Tiers:"2–3",Wheels:"Castor, lockable",Care:"Wipe clean",Warranty:"1 year"}, variants:["2-Tier","3-Tier"] },
    "kitchen-tools": { features:[["shield","Durable Build","Sturdy, rust-resistant construction made for daily kitchen use."],["grip","Comfortable Grip","Ergonomic handles designed for safe, effortless handling."],["leaf","Food-Safe Materials","Hygienic, food-grade materials safe for everyday cooking."],["precision","Purpose-Built Design","Thoughtfully shaped for the specific job it's designed to do."]], specs:{Material:"Stainless steel / nylon",Handle:"Ergonomic",Care:"Hand wash",Warranty:"6 months"}, variants:["Standard"] },
    "manual-appliances": { features:[["power","Effortless Manual Action","Smooth, easy-to-operate mechanism that needs no electricity."],["shield","Sturdy Construction","Durable build engineered for years of everyday use."],["grip","Comfortable Handle","Ergonomic grip designed for safe, fatigue-free operation."],["leaf","Easy to Clean","Simple design that's quick to clean after every use."]], specs:{Material:"Stainless steel / ABS",Mechanism:"Manual",Care:"Wipe / hand wash",Warranty:"6 months"}, variants:["Standard"] },
    "water-filter": { features:[["shield","Effective Filtration","Filters out impurities for cleaner, safer drinking water."],["leaf","Food-Safe Materials","Built with hygienic, food-grade materials throughout."],["lock","Secure Fit","Tight, leak-proof fit keeps your filtration system sealed."],["refill","Easy Cartridge Change","Simple, tool-free replacement when it's time for a new filter."]], specs:{Material:"Plastic / stainless steel",Capacity:"Standard",Care:"Rinse per instructions",Warranty:"6 months"}, variants:["Standard"] },
  };
  CAT_TPL.knives = CAT_TPL.cutlery;
  CAT_TPL.servers = CAT_TPL.serveware;
  CAT_TPL["water-bottle"] = CAT_TPL.flasks;
  CAT_TPL["lunch-box"] = CAT_TPL.storage;
  CAT_TPL["pressure-cooker"] = CAT_TPL.cookware;

  // Real catalog loaded from product-data/products.json (see bootstrap at
  // the bottom of this script). P/BY_ID start empty and are populated once
  // the manifest fetch resolves.
  let P = [];
  let BY_ID = {};

  /* ---- size-variant visual scaling: bigger cm/ml/mm = bigger on-screen image ---- */
  const MIN_IMG_SCALE = 0.62;
  function parseSizeNum(label) {
    const m = /(\d+(\.\d+)?)/.exec(label || "");
    return m ? parseFloat(m[1]) : null;
  }
  function sizeScaleFor(siblingsArr, p) {
    if (!siblingsArr || siblingsArr.length < 2) return 1;
    const nums = siblingsArr.map(s => parseSizeNum(s.vlabel)).filter(n => n !== null);
    const own = parseSizeNum(p.vlabel);
    if (own === null || !nums.length) return 1;
    const min = Math.min(...nums), max = Math.max(...nums);
    if (max === min) return 1;
    return MIN_IMG_SCALE + (own - min) / (max - min) * (1 - MIN_IMG_SCALE);
  }

  /* ---- resolve product ---- */
  function renderProduct() {
  const params = new URLSearchParams(location.search);
  const wanted = (window.__PRODUCT_ID__ || params.get("p") || "").toLowerCase();
  const prod = BY_ID[wanted] || P[0];
  /* An old Product.html?p= link, now that the product has a page of its own:
     carry the visitor there. Done here rather than server-side because the
     site is plain files; the address map arrives in product-urls.js. */
  if (!window.__PRODUCT_ID__ && prod && window.PRODUCT_URLS && window.PRODUCT_URLS[prod.id]) {
    var rest = new URLSearchParams(location.search); rest.delete("p");
    location.replace(productHref(prod.id) + (rest.toString() ? "?" + rest.toString() : "") + location.hash);
    return;
  }
  if (!prod) { document.body.innerHTML = "<p style='padding:80px;text-align:center'>Product catalog failed to load.</p>"; return; }
  const brand = BRANDS[prod.b] || Object.values(BRANDS)[0];
  const CAT_TPL_ALIAS = { "electric-appliances": "appliances", "cleaning-aid": "cleaning" };
  const tpl = CAT_TPL[prod.sub] || CAT_TPL[prod.c] || CAT_TPL[CAT_TPL_ALIAS[prod.c]] || Object.values(CAT_TPL)[0];
  const siblings = prod.vgroup ? P.filter(p => p.vgroup === prod.vgroup).sort((a, b) => a.vorder - b.vorder) : [];
  const specs = Object.assign({}, tpl.specs, prod.specs || {});
  let gallery = [prod.img, ...(prod.gallery || [])].filter(Boolean);
  const PLAY_ICON = '<svg viewBox="0 0 24 24" fill="#fff" stroke="none"><path d="M8 5v14l11-7z"/></svg>';
  function videoThumbHtml(p) {
    return p.video ? `<div class="g-thumb g-thumb-video" data-video="${p.video}"><img src="${p.img}" alt="${p.n} video" loading="lazy"><span class="g-play">${PLAY_ICON}</span></div>` : "";
  }
  function showMainImage(src, alt) {
    const wrap = document.getElementById("gMainWrap"), vid = document.getElementById("gMainVideo");
    wrap.classList.remove("showing-video");
    vid.pause(); vid.removeAttribute("src"); vid.load();
    document.getElementById("gMain").src = src;
    document.getElementById("gMain").alt = alt;
  }
  function showMainVideo(src) {
    const wrap = document.getElementById("gMainWrap"), vid = document.getElementById("gMainVideo");
    wrap.classList.add("showing-video");
    vid.src = src;
    vid.play().catch(() => {});
  }

  /* Hover magnifier on the main image. The zoom layer repaints the current photo
     scaled up, positioned so the point under the cursor stays under the cursor.
     Pointer-only — touch devices keep the plain image. */
  (function wireZoom() {
    const wrap = document.getElementById("gMainWrap");
    const img = document.getElementById("gMain");
    const lens = document.getElementById("gZoom");
    if (!wrap || !img || !lens || wrap.dataset.zoomWired) return;
    if (window.matchMedia("(hover: none)").matches) return;
    wrap.dataset.zoomWired = "1";
    wrap.classList.add("zoomable");
    const ZOOM = 2.5;

    function place(e) {
      if (wrap.classList.contains("showing-video")) { wrap.classList.remove("zooming"); return; }
      const nw = img.naturalWidth, nh = img.naturalHeight;
      if (!nw || !nh) return;
      const r = wrap.getBoundingClientRect();
      // the image is object-fit:contain, so work out its rendered box first
      const scale = Math.min(r.width / nw, r.height / nh);
      const cw = nw * scale, ch = nh * scale;
      const ox = (r.width - cw) / 2, oy = (r.height - ch) / 2;
      const px = e.clientX - r.left, py = e.clientY - r.top;
      const fx = Math.min(1, Math.max(0, (px - ox) / cw));
      const fy = Math.min(1, Math.max(0, (py - oy) / ch));
      const zw = cw * ZOOM, zh = ch * ZOOM;
      lens.style.backgroundImage = 'url("' + img.currentSrc + '")';
      lens.style.backgroundSize = zw + "px " + zh + "px";
      lens.style.backgroundPosition = (px - fx * zw) + "px " + (py - fy * zh) + "px";
      wrap.classList.add("zooming");
    }

    wrap.addEventListener("mousemove", place);
    wrap.addEventListener("mouseleave", () => wrap.classList.remove("zooming"));
  })();

  /* Tab title and the summary Google and the share cards show. Both come from
     the dashboard when someone has written them there, and otherwise stay
     exactly what this page has always produced. */
  function applySeo(p) {
    document.title = (p.mt || (p.n + " — CRYSTAL"));
    var summary = p.md || p.intro || p.desc || "";
    [["name", "description"], ["property", "og:description"]].forEach(function (a) {
      if (!summary) return;
      var el = document.head.querySelector("meta[" + a[0] + '="' + a[1] + '"]');
      if (!el) {
        el = document.createElement("meta");
        el.setAttribute(a[0], a[1]);
        document.head.appendChild(el);
      }
      el.setAttribute("content", summary);
    });
    var addr = productHref(p.id);
    if (addr.charAt(0) === "/") {
      var full = location.origin + addr;
      [["link[rel=canonical]", "href"], ['meta[property="og:url"]', "content"]].forEach(function (a) {
        var el = document.head.querySelector(a[0]);
        if (el) el.setAttribute(a[1], full);
      });
    }
    var ogt = document.head.querySelector('meta[property="og:title"]');
    if (!ogt) {
      ogt = document.createElement("meta");
      ogt.setAttribute("property", "og:title");
      document.head.appendChild(ogt);
    }
    ogt.setAttribute("content", p.mt || p.n);
  }

  if (window.__PRODUCT_ID__ !== prod.id) applySeo(prod);

  /* ---- shared nav renders ---- */
  const brandList = Object.keys(BRANDS);
  document.getElementById("ddMenu").innerHTML = brandList.map(s => `<a href="All-Products.html?brand=${s}"${s===prod.b?' class="active"':''}><b>${BRANDS[s].name}</b><span>${BRANDS[s].tagline}</span></a>`).join("");
  document.getElementById("footBrands").innerHTML = brandList.map(s => `<li><a href="All-Products.html?brand=${s}">${BRANDS[s].name}</a></li>`).join("");
  document.getElementById("mmBrands").innerHTML = brandList.map(s => `<a href="All-Products.html?brand=${s}" class="mm-link">${BRANDS[s].name}</a>`).join("");

  /* ---- breadcrumb ---- */
  document.getElementById("crumb").innerHTML = `
    <li><a href="index.html#top">Home</a></li><li class="sep">/</li>
    <li><a href="All-Products.html">Products</a></li><li class="sep">/</li>
    <li><a href="All-Products.html?brand=${prod.b}">${brand.name}</a></li><li class="sep">/</li>
    <li class="cur">${prod.n}</li>`;

  /* ---- hero ---- */
  showMainImage(gallery[0], prod.n);
  document.getElementById("gMain").style.transform = "scale(" + sizeScaleFor(siblings, prod) + ")";
  {
    const thumbs = gallery.map((src, i) => `<div class="g-thumb${i===0?' active':''}" data-i="${i}"><img src="${src}" alt="${prod.n} view ${i+1}" loading="lazy"></div>`);
    const vThumb = videoThumbHtml(prod);
    if (vThumb) thumbs.splice(1, 0, vThumb);
    document.getElementById("gThumbs").innerHTML = thumbs.join("");
  }
  document.getElementById("infoEyebrow").innerHTML = `<span class="pip"></span>${brand.name} · ${prod.col}`;
  document.getElementById("catChip").textContent = CAT_LABEL[prod.c];
  document.getElementById("pTitle").textContent = prod.n;
  document.getElementById("pSku").textContent = prod.sku ? "Code: " + prod.sku.toUpperCase() : "";
  document.getElementById("pIntro").textContent = prod.intro;
  // ---- Enquire / Buy / quantity wiring ----
  var _pid = prod.id || (new URLSearchParams(location.search)).get("p") || "";
  function wireEnq(btn, p, gal) { if (!btn) return; p = p || prod; gal = gal || gallery; btn.dataset.id = p.id; btn.dataset.name = p.n; btn.dataset.brand = brand.name; btn.dataset.cat = CAT_LABEL[p.c] || p.c; btn.dataset.img = gal[0] || ""; }
  wireEnq(document.getElementById("enqAddBtn"));
  wireEnq(document.getElementById("sEnq"));
  var AMAZON_LOGO = "brand-logos/amazon.svg";
  // Where a product is genuinely listed on Amazon we show the logo. Where it is
  // NOT, the page used to show the same logo pointing at an Amazon SEARCH for
  // the product name -- which reads as "this is on Amazon" when it is not, and
  // hid from the client which products still need a link. A missing link now
  // says so, in red, so it is obvious on the page itself.
  function mkLink(url, name, logo) {
    return '<a class="mk-brand" href="' + url + '" target="_blank" rel="noopener nofollow sponsored">'
      + '<img src="' + logo + '" alt="' + name + '" onerror="this.parentNode.textContent=&quot;' + name + '&quot;">'
      + '</a>';
  }

  /* Amazon comes from the catalogue's own amazon_link; any other shop comes
     from the dashboard's marketplace links for this product, so adding a
     Flipkart or JioMart listing there shows up here with no rebuild. */
  function otherMarkets(p) {
    return (Array.isArray(p.markets) ? p.markets : []).filter(function (m) {
      return m && m.url && m.name;
    });
  }

  function marketplaceRow(p) {
    var link = (p.alink && p.alink !== "No") ? p.alink : "";
    var extra = otherMarkets(p);
    if (!link && !extra.length) {
      return '<span class="mk-missing">Amazon link not added</span>';
    }
    var out = "Available on: ";
    if (link) out += mkLink(link, "Amazon", AMAZON_LOGO);
    for (var i = 0; i < extra.length; i++) {
      out += mkLink(extra[i].url, extra[i].name, extra[i].logo || "");
    }
    return out;
  }

  function wireBuy(btn, p) {
    if (!btn) return;
    btn.dataset.name = p.n;
    var rows = [];
    if (p.alink && p.alink !== "No") rows.push({ name: "Amazon", url: p.alink, logo: AMAZON_LOGO });
    otherMarkets(p).forEach(function (m) { rows.push({ name: m.name, url: m.url, logo: m.logo || "" }); });
    if (rows.length) btn.dataset.mk = JSON.stringify(rows);
    else delete btn.dataset.mk;
  }
  wireBuy(document.getElementById("buyNowBtn"), prod);
  wireBuy(document.getElementById("sBuy"), prod);
  document.getElementById("mkInline").innerHTML = marketplaceRow(prod);
  (function () { var qi = document.getElementById("qtyInput"); var mn = document.getElementById("qtyMinus"), pl = document.getElementById("qtyPlus"); if (qi && mn && pl) { mn.onclick = function () { qi.value = Math.max(1, (parseInt(qi.value, 10) || 1) - 1); }; pl.onclick = function () { qi.value = (parseInt(qi.value, 10) || 1) + 1; }; } })();

  // Size selectable both via gallery thumbnails (one photo per size) and these text pills.
  function renderSizeChips(activeId) {
    document.getElementById("vChips").innerHTML = siblings.map(p => `<button class="vchip${p.id===activeId?' active':''}" data-id="${p.id}">${p.vlabel}</button>`).join("");
  }
  const vsel = document.querySelector(".vsel");
  const vSecHeading = document.getElementById("vSecHeading");
  const vChips2El = document.getElementById("vChips2");
  if (vSecHeading) vSecHeading.style.display = "none";
  if (vChips2El) vChips2El.style.display = "none";
  if (siblings.length > 1) {
    if (vsel) vsel.style.display = "";
    renderSizeChips(prod.id);
    document.getElementById("vCurrent").textContent = "· " + prod.vlabel;
  } else {
    if (vsel) vsel.style.display = "none";
  }

  /* ---- size switch: update image + code + title + copy in place, no page reload ---- */
  let currentId = prod.id;
  function applySizeVariant(newP) {
    const newGallery = [newP.img, ...(newP.gallery || [])].filter(Boolean);
    gallery = newGallery;
    applySeo(newP);
    document.getElementById("pTitle").textContent = newP.n;
    document.getElementById("pSku").textContent = newP.sku ? "Code: " + newP.sku.toUpperCase() : "";
    document.getElementById("pIntro").textContent = newP.intro;
    showMainImage(newGallery[0], newP.n);
    document.getElementById("gMain").style.transform = "scale(" + sizeScaleFor(siblings, newP) + ")";
    {
      const thumbs = newGallery.map((src, i) => `<div class="g-thumb${i===0?' active':''}" data-i="${i}"><img src="${src}" alt="${newP.n} view ${i+1}" loading="lazy"></div>`);
      const vThumb = videoThumbHtml(newP);
      if (vThumb) thumbs.splice(1, 0, vThumb);
      document.getElementById("gThumbs").innerHTML = thumbs.join("");
    }
    const crumbCur = document.querySelector("#crumb .cur");
    if (crumbCur) crumbCur.textContent = newP.n;
    document.getElementById("vCurrent").textContent = "· " + newP.vlabel;
    renderSizeChips(newP.id);
    wireEnq(document.getElementById("enqAddBtn"), newP, newGallery);
    wireEnq(document.getElementById("sEnq"), newP, newGallery);
    wireBuy(document.getElementById("buyNowBtn"), newP);
    wireBuy(document.getElementById("sBuy"), newP);
    document.getElementById("mkInline").innerHTML = marketplaceRow(newP);
    document.getElementById("ovLead").textContent = newP.intro;
    document.getElementById("ovDesc").innerHTML = `<p>${newP.desc}</p>`;
    document.getElementById("ovImg").src = newGallery[1] || newGallery[0];
    document.getElementById("ovImg").alt = newP.n;
    const newLgImgs = [...new Set(newGallery)].filter(Boolean).slice(0, 5);
    const lgCls = ["tall", "", "wide", "", ""];
    document.getElementById("lgGrid").innerHTML = newLgImgs.map((src, i) => `<div class="lg-item ${lgCls[i] || ""}"><img src="${src}" alt="${newP.n} lifestyle ${i+1}" loading="lazy"></div>`).join("");
    history.replaceState(null, "", productHref(newP.id));
    currentId = newP.id;
  }

  /* This product's own Amazon bullets when we have them; the category
     boilerplate otherwise, so every item still shows four features. */
  const FEATURES = prod.feats || tpl.features;

  // hero highlight list = first 3 feature titles + a warranty line
  const hiItems = FEATURES.slice(0, 3).map(f => f[1]).concat([(specs.Warranty ? specs.Warranty + " warranty" : "Crystal assured quality")]);
  document.getElementById("hiList").innerHTML = hiItems.map(t => `<li><span class="tick"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5L20 6"/></svg></span>${t}</li>`).join("");

  /* ---- overview ---- */
  document.getElementById("ovLead").textContent = prod.intro;
  document.getElementById("ovDesc").innerHTML = `<p>${prod.desc}</p>`;
  document.getElementById("ovImg").src = gallery[1] || gallery[0];
  document.getElementById("ovImg").alt = prod.n;
  const benefits = FEATURES.map(f => f[2] ? f[1] + " — " + f[2] : f[1]);
  document.getElementById("ovBenefits").innerHTML = benefits.map(b => `<li><span class="d"></span><span>${b}</span></li>`).join("");

  /* ---- features ---- */
  document.getElementById("featGrid").innerHTML = FEATURES.map(f => `
    <div class="feat-card" data-fade>
      <span class="feat-ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${ICONS[f[0]] || ICONS.shield}</svg></span>
      <h4>${f[1]}</h4>
      <p>${f[2]}</p>
    </div>`).join("");

  /* ---- specs ---- */
  const specRows = Object.assign({ Brand: brand.name, Category: CAT_LABEL[prod.c], Collection: prod.col }, specs);
  document.getElementById("specTable").innerHTML = Object.keys(specRows).map(k => `<div class="spec-row"><span class="k">${k}</span><span class="v">${specRows[k]}</span></div>`).join("");

  /* ---- lifestyle gallery ---- */
  const lgImgs = [...new Set(gallery)].filter(Boolean).slice(0, 5);
  const lgCls = ["tall", "", "wide", "", ""];
  document.getElementById("lgGrid").innerHTML = lgImgs.map((src, i) => `<div class="lg-item ${lgCls[i] || ""}"><img src="${src}" alt="${prod.n} lifestyle ${i+1}" loading="lazy"></div>`).join("");

  /* ---- why ---- */
  document.getElementById("whyLead").textContent = `Every ${brand.name} product is held to the same Crystal standard — quality, innovation and durability, since 1971.`;
  const WHY = [
    ["01", "Trusted Since 1971", `Part of the Crystal family — over half a century of quality Indian manufacturing behind every ${brand.name} product.`],
    ["02", "Engineered to Last", "Premium materials and rigorous testing for dependable, everyday performance you can rely on."],
    ["03", "Designed for Real Kitchens", "Thoughtful details that make daily cooking, serving and cleaning genuinely effortless."],
  ];
  document.getElementById("whyGrid").innerHTML = WHY.map(w => `<div class="why-card" data-fade><span class="wn">${w[0]}</span><h4>${w[1]}</h4><p>${w[2]}</p></div>`).join("");

  /* ---- related (same brand, else same category) ---- */
  let rel = P.filter(p => p.b === prod.b && p.id !== prod.id);
  if (rel.length < 4) rel = rel.concat(P.filter(p => p.c === prod.c && p.b !== prod.b && p.id !== prod.id));
  rel = rel.slice(0, 4);
  document.getElementById("relTitle").innerHTML = "More from<br>" + brand.name;
  document.getElementById("relAll").href = "All-Products.html?brand=" + prod.b;
  document.getElementById("relGrid").innerHTML = rel.map(p => `
    <a class="rcard" href="${productHref(p.id)}">
      <div class="rimg"><span class="rbrand">${BRANDS[p.b].name}</span><img src="${p.img}" alt="${p.n}" loading="lazy"></div>
      <div class="rbody"><h3 class="rname">${p.n}</h3><span class="rlink">View product <span>↗</span></span></div>
    </a>`).join("");

  /* ---- brand story ---- */
  document.getElementById("bsImg").src = brand.img;
  document.getElementById("bsImg").alt = brand.name;
  document.getElementById("bsTitle").textContent = brand.name + " — " + brand.tagline;
  document.getElementById("bsBlurb").textContent = brand.story;
  document.getElementById("bsStory").textContent = "Designed and manufactured in India and held to the Crystal standard of quality, every piece is made to earn a lasting place in your home.";
  document.getElementById("bsBrandName").textContent = brand.name;
  document.getElementById("bsBrandBtn").href = "All-Products.html?brand=" + prod.b;

  /* ---- size pill switch ---- */
  document.body.addEventListener("click", e => {
    const c = e.target.closest(".vchip");
    if (!c || !c.dataset.id || c.dataset.id === currentId) return;
    const newP = BY_ID[c.dataset.id];
    if (newP) applySizeVariant(newP);
  });

  /* ---- gallery thumb switch (size-variant thumbs call applySizeVariant; plain photo thumbs just swap the main image) ---- */
  document.getElementById("gThumbs").addEventListener("click", e => {
    const t = e.target.closest(".g-thumb"); if (!t) return;
    if (t.dataset.vid) {
      if (t.dataset.vid === currentId) return;
      const newP = BY_ID[t.dataset.vid];
      if (newP) applySizeVariant(newP);
      return;
    }
    if (t.dataset.video) {
      showMainVideo(t.dataset.video);
      document.querySelectorAll(".g-thumb").forEach(x => x.classList.toggle("active", x === t));
      return;
    }
    const i = +t.dataset.i;
    showMainImage(gallery[i], prod.n);
    document.querySelectorAll(".g-thumb").forEach(x => x.classList.toggle("active", x === t));
  });
  } // end renderProduct()

  /* ---------- CATALOG BOOTSTRAP: load real product data, then render ---------- */
  (async function loadCatalog() {
    try {
      const res = await fetch("product-data/products.json", { cache: "no-cache" });
      const data = await res.json();
      P = data.products.map(p => ({
        id: p.id, sku: p.sku || p.id || "", n: p.name, b: p.brand, c: p.category, sub: p.subcategory, col: p.collection || p.subcategory || "",
        img: p.hero || "about-assets/placeholder.svg", gallery: p.gallery || [], tags: p.tags || [],
        intro: p.highlight || p.description || "", desc: p.description || p.highlight || "",
        variants: undefined, mrp: p.mrp, alink: p.amazon_link || "", video: p.video || "",
        vgroup: p.variant_group || null, vlabel: p.variant_label || null, vorder: p.variant_order || 0,
    feats: Array.isArray(p.features) && p.features.length ? p.features : null,
        mt: p.meta_title || "", md: p.meta_description || "",
        markets: Array.isArray(p.marketplaces) ? p.marketplaces : [],
      }));
      BY_ID = Object.fromEntries(P.map(p => [p.id, p]));
    } catch (e) {
      console.warn("Could not load product-data/products.json", e);
    }
    renderProduct();
  })();


  /* ---- word split ---- */
  function splitWords(el) {
    const out = [];
    el.childNodes.forEach(node => {
      if (node.nodeType === 3) node.textContent.trim().split(/\s+/).filter(Boolean).forEach(w => out.push(`<span class="w-mask"><span class="word">${w}</span></span>`));
      else if (node.nodeType === 1) { const cls = node.getAttribute("class") || ""; node.textContent.trim().split(/\s+/).filter(Boolean).forEach(w => out.push(`<span class="w-mask"><span class="word ${cls}">${w}</span></span>`)); }
    });
    el.innerHTML = out.join(" ");
  }
  document.querySelectorAll("[data-split]").forEach(splitWords);

  /* ---- header / menu ---- */
  const hdr = document.getElementById("hdr");
  addEventListener("scroll", () => hdr.classList.toggle("scrolled", scrollY > 30), { passive: true });
  const mmEl = document.getElementById("mobileMenu");
  document.getElementById("burger").addEventListener("click", () => mmEl.classList.add("open"));
  document.getElementById("mmClose").addEventListener("click", () => mmEl.classList.remove("open"));
  document.querySelectorAll(".mm-link:not(.mm-acc-tog)").forEach(a => a.addEventListener("click", () => mmEl.classList.remove("open")));

  /* site search: loads the real product catalog and filters by name/category/brand/tags */
  (function () {
    const ov = document.getElementById("searchOv"), input = document.getElementById("searchInput"),
      results = document.getElementById("searchResults"), closeBtn = document.getElementById("searchClose");
    let items = [], loaded = false;

    function openSearch() {
      ov.classList.add("open");
      setTimeout(() => input.focus(), 50);
      if (!loaded) {
        loaded = true;
        fetch("product-data/products.json", { cache: "no-cache" }).then(r => r.json()).then(data => {
          items = (data.products || []).map(p => ({
            name: p.name, cat: p.subcategory || p.category || "", brand: p.brand || "",
            img: p.hero || "about-assets/placeholder.svg", id: p.id || p.sku || "",
            hay: [p.name, p.category, p.subcategory, p.brand, p.sku, p.id, ...(p.tags || [])].join(" ").toLowerCase(),
          }));
          renderResults(input.value.trim());
        }).catch(() => { results.innerHTML = '<div class="search-empty">Could not load product catalog.</div>'; });
      }
    }
    function closeSearch() { ov.classList.remove("open"); input.value = ""; results.innerHTML = ""; }
    function renderResults(q) {
      if (!q) { results.innerHTML = '<div class="search-hint">Start typing to search products…</div>'; return; }
      const ql = q.toLowerCase();
      const hits = items.filter(p => p.hay.includes(ql)).slice(0, 8);
      if (!hits.length) { results.innerHTML = '<div class="search-empty">No products found for “' + q + '”.</div>'; return; }
      results.innerHTML = hits.map(p =>
        `<a class="search-hit" href="${productHref(p.id)}">
          <img src="${p.img.startsWith('about-assets/') || p.img.startsWith('product-photos/') ? p.img : 'about-assets/placeholder.svg'}" alt="" loading="lazy">
          <div><div class="sh-name">${p.name}</div><div class="sh-cat">${p.cat}${p.brand ? " · " + p.brand : ""}</div></div>
        </a>`).join("");
    }

    document.getElementById("searchBtn").addEventListener("click", openSearch);
    closeBtn.addEventListener("click", closeSearch);
    ov.addEventListener("click", e => { if (e.target === ov) closeSearch(); });
    document.addEventListener("keydown", e => {
      if (e.key === "Escape" && ov.classList.contains("open")) closeSearch();
    });
    input.addEventListener("input", () => renderResults(input.value.trim()));
  })();


  /* ---- GSAP ---- */
  function initGSAP() {
    if (!window.gsap || !window.ScrollTrigger) return;
    gsap.registerPlugin(ScrollTrigger);
    const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
    tl.from(".crumb", { y: 16, opacity: 0, duration: 0.5, delay: 0.05 })
      .from(".gallery", { y: 40, opacity: 0, duration: 0.7 }, "-=0.2")
      .from(".info .top, .info h1, .info .intro, .trust-row, .vsel, .info-cta, .hi-list", { y: 26, opacity: 0, duration: 0.6, stagger: 0.08 }, "-=0.5");
    gsap.utils.toArray("[data-split]").forEach(h => {
      gsap.from(h.querySelectorAll(".word"), { yPercent: 118, duration: 0.8, stagger: 0.05, ease: "power3.out", scrollTrigger: { trigger: h, start: "top 86%", once: true } });
    });
    gsap.utils.toArray("[data-fade]").forEach(el => {
      if (el.closest("#hero")) return;
      gsap.from(el, { y: 36, opacity: 0, duration: 0.65, ease: "power2.out", scrollTrigger: { trigger: el, start: "top 90%", once: true } });
    });
    ScrollTrigger.refresh();
  }
  if (!RM) { try { initGSAP(); } catch (e) { console.warn("GSAP", e); } }

  function failsafe() {
    if (window.gsap) gsap.set(".crumb, .gallery, .info .top, .info h1, .info .intro, .trust-row, .vsel, .info-cta, .hi-list, [data-split] .word, [data-fade]", { clearProps: "opacity,transform,x,y,xPercent,yPercent,scale" });
  }
  if (document.hidden || !window.gsap || RM) failsafe();
  let ok = false; requestAnimationFrame(() => { ok = true; });
  setTimeout(() => { if (!ok) failsafe(); }, 1100);
  addEventListener("load", () => { if (window.ScrollTrigger) ScrollTrigger.refresh(); });
  setTimeout(() => { if (window.ScrollTrigger) ScrollTrigger.refresh(); }, 1400);
