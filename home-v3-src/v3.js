/* ==========================================================================
   HOME v3 — scroll choreography
   --------------------------------------------------------------------------
   No pinned sections and no scroll hijacking: pinning read as "scroll is
   stuck" and was cut. Every section scrolls past normally; animations are
   either scrubbed to the section's own passage (word fill, map zoom) or fire
   once on entry (fly-ins, counters). The hero keeps its card-stack intro on
   desktop only.
   ========================================================================== */
(function () {
  if (!window.gsap || !window.Swiper) return;
  gsap.registerPlugin(ScrollTrigger);

  var mm = gsap.matchMedia();
  var DESK = "(min-width: 1025px)";
  var MOB = "(max-width: 1024px)";

  /* ---------- 01 HERO ---------- */
  var heroSwiper = null;

  function mainHeroSwiper() {
    heroSwiper = new Swiper(".hero3-swiper", {
      effect: "fade",
      fadeEffect: { crossFade: true },
      loop: true,
      initialSlide: 2,
      allowTouchMove: false,
      speed: 800,
      autoplay: { delay: 5000, disableOnInteraction: false },
    });
  }

  function heroIntro() {
    // the stack the animation opens from — cards effect, middle slide on top
    heroSwiper = new Swiper(".hero3-swiper", {
      effect: "cards",
      grabCursor: true,
      initialSlide: 2,
      cardsEffect: { rotate: 0, perSlideOffset: 18, slideShadows: false },
    });

    var slides = gsap.utils.toArray(".hero3-swiper .swiper-slide .hero3-vid");
    // rise in from the middle outwards rather than left to right
    var ordered = [slides[2], slides[1], slides[3], slides[0], slides[4]].filter(Boolean);

    gsap.set([".hero3-vid", ".hero3-txt"], { y: 1000 });

    gsap.timeline({
      delay: 0.4,
      defaults: { duration: 1.8, ease: "power3.inOut" },
      onComplete: function () {
        heroSwiper.destroy(true, true);
        mainHeroSwiper();
        ScrollTrigger.refresh();
      },
    })
      .to(ordered, { y: 0, opacity: 1, duration: 1.5, stagger: { each: 0.08 } }, 0)
      .to(".hero3-txt", { y: 0, opacity: 1, duration: 1.5 }, 0.2)
      .to(".hero3-swiper-wrap", { height: "100vh", width: "100vw" })
      .to(".hero3-swiper .swiper-slide, .hero3-vid", { borderRadius: "0px" }, 1.8)
      .to(".hero3", { paddingTop: 0 }, 1.8)
      .to(".hero3-title", { color: "#fff" }, 1.8)
      .to(".hero3-txt", { scale: 0.9 }, 1.8)
      .to(".hero3-txt .v-btn", { borderColor: "#fff" }, 1.8);
  }

  mm.add(DESK, function () {
    heroIntro();
    return function () { if (heroSwiper) { heroSwiper.destroy(true, true); heroSwiper = null; } };
  });

  mm.add(MOB, function () {
    mainHeroSwiper();
    return function () { if (heroSwiper) { heroSwiper.destroy(true, true); heroSwiper = null; } };
  });

  /* ---------- word splitter (own, so no premium GSAP plugin is needed) ---------- */
  function splitWords(el) {
    if (el.dataset.split) return Array.prototype.slice.call(el.querySelectorAll(".word"));
    el.dataset.split = "1";
    var out = [];
    (function walk(node) {
      Array.prototype.slice.call(node.childNodes).forEach(function (n) {
        if (n.nodeType === 3) {
          var frag = document.createDocumentFragment();
          n.nodeValue.split(/(\s+)/).forEach(function (chunk) {
            if (!chunk) return;
            if (/^\s+$/.test(chunk)) { frag.appendChild(document.createTextNode(chunk)); return; }
            var s = document.createElement("span");
            s.className = "word";
            s.textContent = chunk;
            frag.appendChild(s);
            out.push(s);
          });
          node.replaceChild(frag, n);
        } else if (n.nodeType === 1) {
          walk(n);
        }
      });
    })(el);
    return out;
  }

  /* ---------- vertical parallax slider used by split + map ---------- */
  var INTERLEAVE = 0.75;
  function parallaxSwiper(sel, extra) {
    var el = document.querySelector(sel);
    if (!el) return null;
    return new Swiper(el, Object.assign({
      direction: "vertical",
      speed: 1100,
      loop: true,
      allowTouchMove: false,
      watchSlidesProgress: true,
      autoplay: { delay: 3200 },
      on: {
        setTranslate: function () {
          var s = this;
          s.slides.forEach(function (slide) {
            var inner = slide.querySelector(".slide-inner");
            if (inner) gsap.set(inner, { y: slide.progress * s.height * INTERLEAVE, force3D: true });
          });
        },
        setTransition: function (speed) {
          this.slides.forEach(function (slide) {
            slide.style.transition = speed + "ms";
            var inner = slide.querySelector(".slide-inner");
            if (inner) inner.style.transition = speed + "ms";
          });
        },
      },
    }, extra || {}));
  }

  /* ---------- 02 SPLIT — one scroll pass drives the words AND the slides ----
     Both sides read the same progress value, so the photo changes in step with
     the sentence filling instead of running on its own timer.

     Built inside gsap.matchMedia so the desktop/mobile choice is re-evaluated
     on resize. Reading matchMedia once at load baked the wrong branch in
     whenever the page first rendered narrow - which is how the pin silently
     never appeared. */
  var splitSwiper = parallaxSwiper(".split3-swiper", { loop: false, autoplay: false });
  var splitText = document.querySelector(".anim-text");
  var splitWordList = splitText ? splitWords(splitText) : [];
  if (splitWordList.length) {
    gsap.set(splitWordList, { backgroundPositionX: "100%", opacity: 0.3 });
  }

  function splitProgress(p) {
    if (splitSwiper && splitSwiper.slides.length) {
      var last = splitSwiper.slides.length - 1;
      splitSwiper.setTranslate(-p * last * splitSwiper.height);
      splitSwiper.updateActiveIndex();
      splitSwiper.updateSlidesClasses();
    }
    var filled = Math.floor(p * splitWordList.length);
    splitWordList.forEach(function (w, i) {
      gsap.to(w, {
        backgroundPositionX: i <= filled ? "0%" : "100%",
        opacity: i <= filled ? 1 : 0.3,
        duration: 0.15,
        overwrite: "auto",
      });
    });
  }

  if (splitSwiper || splitText) {
    // desktop: the section holds the viewport while both sides advance
    mm.add(DESK, function () {
      var st = ScrollTrigger.create({
        trigger: ".split3",
        start: "top top",
        end: function () { return "+=" + Math.round(window.innerHeight * 2.2); },
        pin: true,
        anticipatePin: 1,
        scrub: 1,
        onUpdate: function (self) { splitProgress(self.progress); },
      });
      return function () { st.kill(); };
    });

    // mobile: no pin - a held viewport fights touch scrolling
    mm.add(MOB, function () {
      var st = ScrollTrigger.create({
        trigger: ".split3",
        start: "top 75%",
        end: "bottom 40%",
        scrub: 1,
        onUpdate: function (self) { splitProgress(self.progress); },
      });
      return function () { st.kill(); };
    });
  }

  mm.add(DESK, function () {
    var inTl = gsap.timeline({
      scrollTrigger: { trigger: ".split3", start: "top 85%", end: "top 30%", scrub: 1.5 },
    })
      .from(".split3 .left-txt", { x: -220, opacity: 0 })
      .from(".split3-swiper-wrap", { x: 420, opacity: 0 }, 0);

    /* ---------- 06 MAP — zoomed crop settles as the section scrolls in ---------- */
    var mapTl = gsap.timeline({
      scrollTrigger: { trigger: ".map3", start: "top 85%", end: "top 15%", scrub: 1 },
    })
      .from(".map3-left", { scale: 1.7, y: 180, transformOrigin: "50% 60%" }, 0)
      .from(".map3-state", { fill: "#ED282E", clearProps: "fill" }, 0)
      .from(".map3-float", { scale: 1.4, x: 180, y: -80 }, 0)
      .from(".map3-right", { opacity: 0, x: 320 }, 0.15);

    // A scrubbed parallax leaves the heart wherever the tween happens to be
    // when scrolling stops, which is how it ended up sunk into the footer.
    // One-shot instead: it rises once on entry and its resting position is
    // plain CSS, so the tip always lands on the footer edge.
    // The heart rises as the section scrolls. The scrub ends when the footer
    // reaches the bottom of the viewport - roughly a footer's height before
    // the page bottoms out - so it has always finished travelling by the time
    // scrolling stops, and cannot be left parked mid-tween inside the footer.
    var preTl = gsap.from(".pre3-right", {
      y: 140, ease: "none",
      scrollTrigger: {
        trigger: ".pre3", start: "top 90%",
        endTrigger: "#footer", end: "top bottom",
        scrub: 1,
      },
    });

    return function () {
      [inTl, mapTl, preTl].forEach(function (t) {
        t.scrollTrigger && t.scrollTrigger.kill();
        t.kill();
      });
    };
  });

  mm.add(MOB, function () {
    var mapTl = gsap.timeline({
      scrollTrigger: { trigger: ".map3", start: "top 75%", once: true },
    })
      .from(".map3-container", { y: 220, opacity: 0, duration: 0.7, ease: "power2.out" })
      .from(".map3-right", { y: 220, opacity: 0, duration: 0.7, ease: "power2.out" }, "-=0.35");
    return function () { mapTl.scrollTrigger && mapTl.scrollTrigger.kill(); mapTl.kill(); };
  });

  /* ---------- 06 MAP — tabs drive the slider ---------- */
  var mapSwiper = parallaxSwiper(".map3-swiper .swiper", { loop: false, autoplay: false, speed: 800 });
  var mapTabs = document.querySelectorAll(".map3-tabs li");
  mapTabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      mapTabs.forEach(function (t) { t.classList.remove("active"); });
      tab.classList.add("active");
      if (mapSwiper) mapSwiper.slideTo(+tab.dataset.slide, 800);
    });
  });
  if (mapSwiper) mapSwiper.slideTo(0, 0);

  /* ---------- 03 ABOUT — one entry animation, then done ---------- */
  gsap.timeline({
    scrollTrigger: { trigger: ".about3", start: "top 85%", once: true },
    defaults: { duration: 0.8, ease: "power2.out", immediateRender: false,
                clearProps: "transform,opacity" },
  })
    .from(".about3-left", { x: window.innerWidth > 990 ? -160 : 0, y: window.innerWidth > 990 ? 0 : 120, opacity: 0 })
    .from(".about3-right", { x: window.innerWidth > 990 ? 160 : 0, y: window.innerWidth > 990 ? 0 : 120, opacity: 0 }, "-=0.55")
    .from(".counter3-wrap", { y: 60, opacity: 0, stagger: 0.08 }, "-=0.4");

  // the line draws with plain dash offset, so no DrawSVG plugin is needed
  var redLine = document.querySelector(".red-line");
  if (redLine && redLine.getTotalLength) {
    var len = redLine.getTotalLength();
    gsap.set(redLine, { strokeDasharray: len + 1, strokeDashoffset: len + 1 });
    gsap.to(redLine, {
      strokeDashoffset: 0,
      ease: "none",
      scrollTrigger: { trigger: ".about3", start: "top 90%", end: "bottom 55%", scrub: 1 },
    });
  }

  document.querySelectorAll(".count3").forEach(function (counter) {
    var target = +counter.dataset.target;
    var suffix = counter.dataset.suffix || "";
    counter.textContent = "0" + suffix;
    gsap.fromTo(counter, { innerText: 0 }, {
      innerText: target,
      duration: 2,
      ease: "power3.out",
      snap: { innerText: 1 },
      scrollTrigger: { trigger: ".counter3", start: "top 88%", once: true },
      onUpdate: function () {
        counter.textContent = Math.floor(counter.innerText) + suffix;
      },
    });
  });

  /* ---------- 04 OUR BRANDS — accordion, gallery filter, section colour ---------- */
  var BRAND_SHOTS = {
    crystal: ["1-1.jpg", "3-2.jpg", "3.jpg", "5.jpg", "6.jpg", "7.jpg", "8.jpg", "9.jpg", "10.jpg", "11.jpg", "13.jpg", "12-1.jpg"],
    crystalina: ["14.jpg", "15.jpg", "16.jpg", "17.jpg", "18.jpg"],
    sparkmate: ["19.jpg", "20.jpg", "21.jpg", "22.jpg", "23.jpg"],
    valmate: ["ChatGPT-Image-May-1-2026-10_29_19-AM.png", "25.jpg", "26.jpg"],
  };

  var brandSwiper = new Swiper(".brand3-swiper", {
    spaceBetween: 10,
    slidesPerView: 1,
    speed: 700,
    navigation: { nextEl: ".brand3-next", prevEl: ".brand3-prev" },
  });
  var brandSec = document.querySelector(".brand3");
  var brandCta = document.getElementById("brand3Cta");

  function showBrand(item) {
    var brand = item.dataset.brand;
    brandSwiper.removeAllSlides();
    brandSwiper.appendSlide((BRAND_SHOTS[brand] || []).map(function (f) {
      return '<div class="swiper-slide"><img src="home-v3-assets/img/' + f + '" alt="' + brand + ' range" loading="lazy"></div>';
    }));
    brandSwiper.slideTo(0, 0, false);
    brandSwiper.update();

    if (item.dataset.bg) {
      brandSec.style.backgroundColor = item.dataset.bg;
      brandCta.style.backgroundColor = item.dataset.bg;
    }
    if (item.dataset.ctaUrl) brandCta.setAttribute("href", item.dataset.ctaUrl);
    if (item.dataset.ctaText) brandCta.querySelector(".label").textContent = item.dataset.ctaText;
  }

  var accItems = Array.prototype.slice.call(document.querySelectorAll(".acc3-item"));
  accItems.forEach(function (item) {
    var panel = item.querySelector(".acc3-panel");
    panel.style.display = item.classList.contains("active") ? "block" : "none";

    item.querySelector(".acc3-btn").addEventListener("click", function () {
      if (item.classList.contains("active")) return;
      accItems.forEach(function (o) {
        o.classList.remove("active");
        o.querySelector(".acc3-panel").style.display = "none";
      });
      item.classList.add("active");
      panel.style.display = "block";
      showBrand(item);
    });
  });
  if (accItems.length) showBrand(accItems.find(function (i) { return i.classList.contains("active"); }) || accItems[0]);

  gsap.timeline({
    scrollTrigger: { trigger: ".brand3", start: "top 85%", once: true },
    defaults: { duration: 0.7, ease: "power2.out", immediateRender: false,
                clearProps: "transform,opacity" },
  })
    .from(".brand3-left .v-head-wrap", { x: window.innerWidth > 1024 ? -160 : 0, y: window.innerWidth > 1024 ? 0 : 120, opacity: 0 })
    .from(".brand3-right", { x: window.innerWidth > 1024 ? 160 : 0, y: window.innerWidth > 1024 ? 0 : 120, opacity: 0 }, "-=0.5")
    .from(".brand3-acc .acc3-item", { y: 70, opacity: 0, stagger: 0.09 }, "-=0.35");

  /* ---------- 05 + 07 simple reveals ---------- */
  gsap.from(".trust3-logo", {
    y: 30, opacity: 0, duration: 0.5, stagger: 0.04, ease: "power2.out",
    immediateRender: false, clearProps: "transform,opacity",
    scrollTrigger: { trigger: ".trust3-grid", start: "top 92%", once: true },
  });
  gsap.from(".res3 .blog3", {
    y: 50, opacity: 0, duration: 0.6, stagger: 0.12, ease: "power2.out",
    immediateRender: false, clearProps: "transform,opacity",
    scrollTrigger: { trigger: ".res3-grid", start: "top 92%", once: true },
  });

  // Net: if any reveal never ran, nothing stays invisible.
  function unhideStragglers() {
    document.querySelectorAll(
      ".trust3-logo, .res3 .blog3, .about3-left, .about3-right, .counter3-wrap," +
      " .brand3-left .v-head-wrap, .brand3-right, .acc3-item, .map3-right"
    ).forEach(function (el) {
      if (parseFloat(getComputedStyle(el).opacity) < 0.05) {
        gsap.set(el, { clearProps: "transform,opacity" });
      }
    });
  }
  setTimeout(unhideStragglers, 2500);

  addEventListener("load", function () { ScrollTrigger.refresh(); unhideStragglers(); });
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(function () { ScrollTrigger.refresh(); });
  }
  setTimeout(function () { ScrollTrigger.refresh(); }, 1400);
})();
