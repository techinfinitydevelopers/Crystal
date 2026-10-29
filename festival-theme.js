/* Festival themes (Diwali, Holi, Christmas...) switched on from the dashboard.

   Same inversion as content-sync.js: the site is static files and the
   dashboard a separate service. Every page loads this file; it asks
   /api/theme.json which theme is live (at most one) and dresses the page:

     - data-festival="<slug>" on <html>, and festival-theme.css injected
     - a slim greeting ribbon between the red support bar and the header
       (the header moves down by the ribbon's height while it shows, and the
       ribbon tucks away once the visitor scrolls), a toran/garland under it
     - festival props on every page: decorations hanging from the header at
       the viewport edges, an ornament behind and a festive divider under the
       main section headings, motifs in section corners (bunting/toran across
       sections for some festivals), header props (Christmas: snow on the nav,
       Santa hat on the logo), a band on the footer, festival glow on cards
     - light falling particles (+ fireworks, balloons, Holi colour bursts on
       tap) if the theme has effects on
     - on the Home page, a greeting badge in the hero (+ a card if the theme
       has a banner picture)

   How much of it shows is the theme's Intensity: subtle | festive | full.
   Decorations sit at edges and in paddings, never take clicks, and stand
   still for visitors who asked for reduced motion.

   The answer is kept in localStorage so the next page paints the theme with
   no wait, then refreshed. Dashboard down or no answer = the normal site.

   ?theme=<slug> previews a theme for this visitor only (kept for the tab's
   session as they click around); ?theme=off stops previewing. Add
   &intensity=subtle|festive|full to compare. Nothing reaches the dashboard. */
(function () {
  "use strict";

  if (window.__crystalFestival) return;
  window.__crystalFestival = true;

  var ONRAILWAY = location.hostname.endsWith(".up.railway.app");
  var API = (ONRAILWAY ? "https://crystal-production-eb2e.up.railway.app" : "") + "/api/theme.json";
  var KEY = "crystal-festival";
  var PKEY = "crystal-festival-preview";
  var DKEY = "crystal-festival-hidden";
  var MAX_STALE = 3 * 24 * 3600 * 1000;   // a cached theme with no refresh for 3 days is dropped
  var LEVELS = { subtle: 1, festive: 2, full: 3 };

  var me = document.currentScript;
  var CSS_URL = (function () {
    var src = me && me.src ? me.src : "festival-theme.js";
    return src.replace(/festival-theme\.js(\?[^#]*)?/, function (_, q) { return "festival-theme.css" + (q || ""); });
  })();

  function store(kind) { try { return window[kind]; } catch (e) { return null; } }
  function get(kind, k) { try { var s = store(kind); return s ? s.getItem(k) : null; } catch (e) { return null; } }
  function put(kind, k, v) { try { var s = store(kind); if (s) { if (v == null) s.removeItem(k); else s.setItem(k, v); } } catch (e) {} }

  /* ── SVG helpers ───────────────────────────────────────────────────────── */
  function r1(n) { return Math.round(n * 10) / 10; }
  function pt(cx, cy, r, deg) { var a = (deg - 90) * Math.PI / 180; return [r1(cx + r * Math.cos(a)), r1(cy + r * Math.sin(a))]; }
  function starPts(cx, cy, n, ro, ri, rot) {
    var p = [];
    for (var i = 0; i < n * 2; i++) { var q = pt(cx, cy, i % 2 ? ri : ro, (rot || 0) + i * 180 / n); p.push(q[0] + "," + q[1]); }
    return p.join(" ");
  }
  function wedge(cx, cy, ra, rb, a0, a1, fill) {
    var p0 = pt(cx, cy, rb, a0), p1 = pt(cx, cy, rb, a1), p2 = pt(cx, cy, ra, a1), p3 = pt(cx, cy, ra, a0);
    return "<path d='M" + p0 + "A" + rb + " " + rb + " 0 0 1 " + p1 + "L" + p2 + "A" + ra + " " + ra + " 0 0 0 " + p3 + "Z' fill='" + fill + "'/>";
  }
  function ring(n, r, fn) { var s = ""; for (var i = 0; i < n; i++) s += fn(i, i * 360 / n, pt(50, 50, r, i * 360 / n)); return s; }
  function svgDoc(w, h, vb, body) {
    return "<svg xmlns='http://www.w3.org/2000/svg' width='" + w + "' height='" + h + "' viewBox='" + vb + "'>" + body + "</svg>";
  }
  function dataUri(svg) { return 'url("data:image/svg+xml,' + encodeURIComponent(svg) + '")'; }

  /* ── Motifs, drawn in a 100×100 box ───────────────────────────────────── */
  var LEAF = "M0 0Q8-10 22-12Q20-8 24-5Q18-2 20 3Q12 5 0 0Z";
  var MODAK = "M0-14C4-8 10-2 10 4C10 10 5 13 0 13S-10 10-10 4C-10-2-4-8 0-14Z";
  var M = {
    rangoli: function () {
      var c = ["#D6336C", "#F08C00", "#FCC419", "#2B8A3E"];
      return "<circle cx='50' cy='50' r='47' fill='none' stroke='#D6336C' stroke-width='1.6' stroke-dasharray='2 3'/>" +
        ring(8, 0, function (i, a) { return "<ellipse cx='50' cy='22' rx='8' ry='17' fill='" + c[i % 2 ? 1 : 0] + "' transform='rotate(" + a + " 50 50)'/>"; }) +
        ring(8, 0, function (i, a) { return "<ellipse cx='50' cy='29' rx='4' ry='9' fill='" + c[2] + "' transform='rotate(" + (a + 22.5) + " 50 50)'/>"; }) +
        ring(16, 43, function (i, a, p) { return "<circle cx='" + p[0] + "' cy='" + p[1] + "' r='2.2' fill='" + c[i % 2 ? 3 : 2] + "'/>"; }) +
        "<circle cx='50' cy='50' r='14' fill='#D6336C'/><circle cx='50' cy='50' r='9' fill='#FCC419'/><circle cx='50' cy='50' r='4' fill='#fff'/>";
    },
    diya: function () {
      return "<circle cx='50' cy='42' r='34' fill='#FFD36E' fill-opacity='.28'/><path d='M50 8c10 14 15 24 15 32a15 15 0 0 1-30 0c0-8 5-18 15-32z' fill='#FFB938'/>" +
        "<path d='M50 24c4 6 6 10 6 14a6 6 0 0 1-12 0c0-4 2-8 6-14z' fill='#FFF1C1'/><path d='M8 56h84c-3 18-21 30-42 30S11 74 8 56z' fill='#B5541B'/>" +
        "<path d='M8 56h84' stroke='#E9A23B' stroke-width='4'/><path d='M22 68h56' stroke='#E9A23B' stroke-width='2' stroke-dasharray='3 4'/>";
    },
    splash: function () {
      var d = [[50, 50, 24, "#E3367A"], [72, 36, 13, "#F5C518"], [30, 30, 11, "#2F7BE3"], [28, 66, 13, "#2FB36B"], [70, 70, 11, "#F08A24"],
        [86, 54, 5, "#E3367A"], [12, 48, 5, "#9C36B5"], [52, 14, 5, "#F08A24"], [50, 88, 6, "#2F7BE3"], [86, 20, 3, "#2FB36B"], [14, 86, 3.5, "#F5C518"], [90, 84, 3, "#9C36B5"]];
      return d.map(function (x) { return "<circle cx='" + x[0] + "' cy='" + x[1] + "' r='" + x[2] + "' fill='" + x[3] + "' fill-opacity='.85'/>"; }).join("");
    },
    chakra: function () {
      return "<circle cx='50' cy='50' r='44' fill='none' stroke='#0B3D91' stroke-width='4'/>" +
        ring(24, 0, function (i, a) { var p = pt(50, 50, 9, a), q = pt(50, 50, 42, a); return "<line x1='" + p[0] + "' y1='" + p[1] + "' x2='" + q[0] + "' y2='" + q[1] + "' stroke='#0B3D91' stroke-width='1.6'/>"; }) +
        ring(24, 44, function (i, a, p) { return "<circle cx='" + p[0] + "' cy='" + p[1] + "' r='1.6' fill='#0B3D91' transform='rotate(7.5 50 50)'/>"; }) +
        "<circle cx='50' cy='50' r='8' fill='#0B3D91'/>";
    },
    flag: function () {
      var w = function (y) { return "M16 " + y + "Q36 " + (y - 6) + " 56 " + y + "T96 " + y; };
      return "<path d='M14 6V96' stroke='#8a6d3b' stroke-width='3.4' stroke-linecap='round'/><circle cx='14' cy='5' r='3' fill='#C9A227'/>" +
        "<path d='" + w(10) + "V24Q76 18 56 24T16 24Z' fill='#FF9933'/>" +
        "<path d='" + w(24) + "V38Q76 32 56 38T16 38Z' fill='#fff' stroke='#d9d9d9' stroke-width='.6'/>" +
        "<path d='" + w(38) + "V52Q76 46 56 52T16 52Z' fill='#138808'/>" +
        "<circle cx='56' cy='31' r='5' fill='none' stroke='#0B3D91' stroke-width='1.2'/>";
    },
    snowflake: function () {
      var arm = "<path d='M50 50V8M50 22l-9-8M50 22l9-8M50 34l-7-6M50 34l7-6' stroke='#7FA7CF' stroke-width='4.5' stroke-linecap='round' fill='none'/>";
      return ring(6, 0, function (i, a) { return "<g transform='rotate(" + a + " 50 50)'>" + arm + "</g>"; }) + "<circle cx='50' cy='50' r='6' fill='#7FA7CF'/>";
    },
    holly: function () {
      var lf = function (a, c) { return "<path d='" + LEAF + "' fill='" + c + "' transform='translate(50 52) rotate(" + a + ") scale(1.7)'/>"; };
      return lf(200, "#2B8A3E") + lf(-20, "#237032") + lf(95, "#2F9E44") +
        "<circle cx='45' cy='50' r='7' fill='#E03131'/><circle cx='56' cy='46' r='6.5' fill='#C92A2A'/><circle cx='53' cy='58' r='6.5' fill='#E03131'/>" +
        "<circle cx='43' cy='47' r='2' fill='#fff' fill-opacity='.6'/>";
    },
    star: function () { return "<polygon points='" + starPts(50, 52, 5, 44, 19) + "' fill='#F2C14E' stroke='#C9A227' stroke-width='2' stroke-linejoin='round'/>"; },
    mandala: function () {
      var c = ["#C2255C", "#F08C00", "#FCC419", "#7B2CBF"];
      return ring(12, 0, function (i, a) { return "<ellipse cx='50' cy='18' rx='6' ry='14' fill='" + c[i % 2] + "' transform='rotate(" + a + " 50 50)'/>"; }) +
        ring(12, 34, function (i, a, p) { return "<circle cx='" + p[0] + "' cy='" + p[1] + "' r='3' fill='" + c[2] + "' transform='rotate(15 50 50)'/>"; }) +
        "<circle cx='50' cy='50' r='16' fill='" + c[3] + "'/><circle cx='50' cy='50' r='10' fill='" + c[2] + "'/><circle cx='50' cy='50' r='4' fill='" + c[0] + "'/>";
    },
    dandiya: function () {
      var stick = function (a, col) {
        return "<g transform='rotate(" + a + " 50 50)'><rect x='46' y='6' width='8' height='88' rx='4' fill='" + col + "'/>" +
          "<rect x='46' y='20' width='8' height='6' fill='#FCC419'/><rect x='46' y='38' width='8' height='4' fill='#2F9E44'/><rect x='46' y='58' width='8' height='4' fill='#2F9E44'/><rect x='46' y='74' width='8' height='6' fill='#FCC419'/>" +
          "<circle cx='50' cy='50' r='2.4' fill='#fff'/></g>";
      };
      return stick(-32, "#C2255C") + stick(32, "#E8590C") + "<circle cx='50' cy='50' r='7' fill='#7B2CBF'/><circle cx='50' cy='50' r='3' fill='#FCC419'/>";
    },
    marigold: function () {
      return ring(16, 40, function (i, a, p) { return "<circle cx='" + p[0] + "' cy='" + p[1] + "' r='7' fill='" + (i % 2 ? "#FFB703" : "#F08C00") + "' stroke='#B35500' stroke-width='1' stroke-dasharray='1.5 1.5'/>"; }) +
        ring(10, 25, function (i, a, p) { return "<circle cx='" + p[0] + "' cy='" + p[1] + "' r='6' fill='" + (i % 2 ? "#F08C00" : "#FFD43B") + "'/>"; }) +
        "<circle cx='50' cy='50' r='13' fill='#E03131'/><circle cx='50' cy='50' r='6' fill='#FFD43B'/>";
    },
    modak: function () {
      var m = function (x, y, s) {
        return "<g transform='translate(" + x + " " + y + ") scale(" + s + ")'><path d='" + MODAK + "' fill='#FFF4D6' stroke='#D9A441' stroke-width='1.1'/>" +
          "<path d='M0-14Q-6 0-6 12M0-14V13M0-14Q6 0 6 12' fill='none' stroke='#D9A441' stroke-width='.9'/></g>";
      };
      return "<ellipse cx='50' cy='80' rx='40' ry='9' fill='#C8742B' fill-opacity='.85'/><ellipse cx='50' cy='78' rx='36' ry='6' fill='#E9A23B'/>" +
        m(32, 58, 1.7) + m(68, 58, 1.7) + m(50, 44, 2) +
        "<circle cx='14' cy='70' r='5' fill='#F08C00'/><circle cx='86' cy='70' r='5' fill='#FFB703'/>";
    },
    rakhi: function () {
      return "<path d='M0 50Q12 42 24 50T48 50M52 50Q64 58 76 50T100 50' fill='none' stroke='#E64980' stroke-width='3'/>" +
        "<path d='M0 50Q12 58 24 50T48 50M52 50Q64 42 76 50T100 50' fill='none' stroke='#FCC419' stroke-width='2'/>" +
        ring(8, 18, function (i, a, p) { return "<circle cx='" + p[0] + "' cy='" + p[1] + "' r='9' fill='" + (i % 2 ? "#FCC419" : "#F783AC") + "'/>"; }) +
        "<circle cx='50' cy='50' r='13' fill='#E64980'/><circle cx='50' cy='50' r='6' fill='#FFF3BF'/>";
    },
    feather: function () {
      var barbs = "";
      for (var i = 0; i < 9; i++) {
        var y = 92 - i * 7;
        barbs += "<path d='M50 " + y + "Q" + (34 - i) + " " + (y - 6) + " " + (28 - i) + " " + (y - 16) + "M50 " + y + "Q" + (66 + i) + " " + (y - 6) + " " + (72 + i) + " " + (y - 16) + "' stroke='#2E9E6E' stroke-width='1.2' fill='none'/>";
      }
      return barbs + "<path d='M50 99Q52 62 50 30' stroke='#3B7A57' stroke-width='2' fill='none'/>" +
        "<ellipse cx='50' cy='30' rx='22' ry='28' fill='#2E9E6E'/><ellipse cx='50' cy='33' rx='14' ry='19' fill='#1C7ED6'/>" +
        "<ellipse cx='50' cy='35' rx='14' ry='19' fill='none' stroke='#E9B949' stroke-width='2'/><ellipse cx='50' cy='36' rx='7' ry='9' fill='#0B2E59'/>";
    },
    kite: function () {
      return "<path d='M50 4L86 42 50 84 14 42Z' fill='#F03E3E'/><path d='M50 4L86 42H14Z' fill='#FAB005'/><path d='M50 4V84M14 42H86' stroke='#7a2a00' stroke-width='1.4'/>" +
        "<path d='M50 84Q42 90 52 94T48 100' fill='none' stroke='#555' stroke-width='1.2'/><path d='M46 90l-5 2 5 2zM54 96l5 2-5 2z' fill='#1C7ED6'/>";
    },
    pookalam: function () {
      var pal = ["#F59F00", "#E8590C", "#FFFFFF", "#7B2CBF", "#2F9E44", "#FFD43B"], s = "";
      [[38, 47, 16, 0], [29, 38, 12, 2], [20, 29, 8, 4], [11, 20, 8, 1]].forEach(function (r) {
        for (var i = 0; i < r[2]; i++) s += wedge(50, 50, r[0], r[1], i * 360 / r[2], (i + 1) * 360 / r[2], pal[(i + r[3]) % pal.length]);
      });
      return s + "<circle cx='50' cy='50' r='11' fill='#fff'/><circle cx='50' cy='50' r='5' fill='#7B2CBF'/>";
    },
    boat: function () {
      var row = "";
      for (var i = 0; i < 9; i++) row += "<circle cx='" + (16 + i * 7) + "' cy='" + (53 - i * .3) + "' r='2.2' fill='#3B2A1A'/><path d='M" + (16 + i * 7) + " 55l-5 9' stroke='#6b4a1f' stroke-width='1'/>";
      return "<path d='M2 60Q40 70 78 62Q90 58 97 30Q93 50 84 55Q48 60 2 56Z' fill='#3B2A1A'/>" + row +
        "<path d='M60 50V38' stroke='#6b4a1f' stroke-width='1.4'/><path d='M53 39a7 5 0 0 1 14 0z' fill='#E0A100'/>" +
        "<path d='M0 72q8-4 16 0t16 0 16 0 16 0 16 0 16 0' fill='none' stroke='#4DABF7' stroke-width='2'/>";
    },
    star8: function () {
      return "<polygon points='" + starPts(50, 50, 8, 46, 35) + "' fill='none' stroke='#C9A227' stroke-width='2.6'/>" +
        "<polygon points='" + starPts(50, 50, 8, 32, 24, 22.5) + "' fill='#0E8A66' fill-opacity='.85'/>" +
        ring(8, 40, function (i, a, p) { return "<circle cx='" + p[0] + "' cy='" + p[1] + "' r='2.2' fill='#C9A227'/>"; }) +
        "<circle cx='50' cy='50' r='9' fill='#F5D98B'/>";
    },
    crescent: function () {
      return "<path d='M58 10A40 40 0 1 0 90 72 32 32 0 1 1 58 10Z' fill='#E9C46A'/><polygon points='" + starPts(76, 30, 5, 10, 4.2) + "' fill='#E9C46A'/>";
    },
    lantern: function () {
      return "<path d='M50 0V14' stroke='#C9A227' stroke-width='2'/><path d='M38 14h24l-3 6H41z' fill='#C9A227'/>" +
        "<path d='M40 20h20l7 14-7 34H40l-7-34z' fill='#FFD36E' fill-opacity='.95' stroke='#B8860B' stroke-width='2'/><path d='M50 20v48M33 34h34' stroke='#B8860B' stroke-width='1.2'/>" +
        "<path d='M41 68h18l-9 12z' fill='#C9A227'/><path d='M50 80v14' stroke='#C9A227' stroke-width='2'/>";
    },
    burst: function () {
      var c = ["#D4AF37", "#ED3338", "#C0C6CC", "#F1D27A"];
      return ring(16, 0, function (i, a) { var p = pt(50, 50, 14, a), q = pt(50, 50, i % 2 ? 34 : 40, a); return "<line x1='" + p[0] + "' y1='" + p[1] + "' x2='" + q[0] + "' y2='" + q[1] + "' stroke='" + c[i % 4] + "' stroke-width='3' stroke-linecap='round'/>"; }) +
        ring(16, 45, function (i, a, p) { return "<circle cx='" + p[0] + "' cy='" + p[1] + "' r='2.4' fill='" + c[(i + 1) % 4] + "'/>"; }) +
        "<polygon points='" + starPts(50, 50, 4, 11, 4) + "' fill='#D4AF37'/>";
    }
  };
  function motif(name) { return (M[name] || M.burst)(); }
  function motifUri(name) { return dataUri(svgDoc(100, 100, "0 0 100 100", motif(name))); }

  /* Divider under headings: two fading lines with the festival's mark between. */
  function dividerUri(name, lineA, lineB) {
    var body = "<defs><linearGradient id='l' x1='0' x2='1'><stop offset='0' stop-color='" + lineA + "' stop-opacity='0'/><stop offset='1' stop-color='" + lineA + "'/></linearGradient>" +
      "<linearGradient id='r' x1='0' x2='1'><stop offset='0' stop-color='" + lineB + "'/><stop offset='1' stop-color='" + lineB + "' stop-opacity='0'/></linearGradient></defs>" +
      "<rect x='2' y='10' width='62' height='2.4' rx='1.2' fill='url(#l)'/><rect x='96' y='10' width='62' height='2.4' rx='1.2' fill='url(#r)'/>" +
      "<svg x='68' y='-1' width='24' height='24' viewBox='0 0 100 100'>" + motif(name) + "</svg>";
    return dataUri(svgDoc(160, 22, "0 0 160 22", body));
  }

  /* ── Hanging decorations: one string each, drawn from the attach point down ── */
  var H = {
    kandil: [58, function (c) {
      return "<polygon points='" + starPts(0, 24, 6, 18, 10) + "' fill='" + (c || "#E8590C") + "' stroke='#FFD36E' stroke-width='1.2'/>" +
        "<circle cx='0' cy='24' r='8' fill='#FFE9A8'/><circle cx='0' cy='24' r='4' fill='#fff' fill-opacity='.8'/>" +
        "<path d='M-6 40l-2 16M0 42v16M6 40l2 16' stroke='" + (c || "#E8590C") + "' stroke-width='2'/><circle cx='0' cy='58' r='2' fill='#FFD36E'/>";
    }],
    diya: [26, function () {
      return "<path d='M0 0L-10 12M0 0L10 12' stroke='#8a5a12' stroke-width='.9'/><circle cx='0' cy='8' r='12' fill='#FFD36E' fill-opacity='.25'/>" +
        "<path d='M0 0c3 4 4 6 4 8a4 4 0 0 1-8 0c0-2 1-4 4-8z' fill='#FFB938' transform='translate(0 2)'/>" +
        "<path d='M-12 12h24c-1 7-6 11-12 11s-11-4-12-11z' fill='#B5541B'/><path d='M-12 12h24' stroke='#E9A23B' stroke-width='1.6'/>";
    }],
    bauble: [26, function (c) {
      return "<rect x='-3.5' y='0' width='7' height='5' rx='1' fill='#C9A227'/><circle cx='0' cy='15' r='10.5' fill='" + (c || "#C92A2A") + "'/>" +
        "<path d='M-10 13q10 5 20 0' stroke='#fff' stroke-opacity='.55' stroke-width='1.4' fill='none'/><ellipse cx='-4' cy='10' rx='3' ry='2' fill='#fff' fill-opacity='.5'/>";
    }],
    star: [26, function (c) { return "<polygon points='" + starPts(0, 13, 5, 12, 5) + "' fill='" + (c || "#F2C14E") + "' stroke='#C9A227' stroke-width='1'/>"; }],
    lantern: [40, function () {
      return "<path d='M-6 0h12l-2 4h-8z' fill='#C9A227'/><path d='M-6 4h12l5 9-5 18h-12l-5-18z' fill='#FFD36E' fill-opacity='.95' stroke='#B8860B' stroke-width='1.2'/>" +
        "<path d='M0 4v27M-11 13h22' stroke='#B8860B' stroke-width='.7'/><path d='M-5 31h10l-5 7z' fill='#C9A227'/><circle cx='0' cy='17' r='9' fill='#FFE9A8' fill-opacity='.35'/>";
    }],
    crescent: [26, function () {
      return "<path d='M3 2A12 12 0 1 0 12 20 9.5 9.5 0 1 1 3 2Z' fill='#E9C46A'/><polygon points='" + starPts(9, 8, 5, 3.6, 1.5) + "' fill='#E9C46A'/>";
    }],
    matki: [30, function () {
      return "<path d='M0 0L-8 9M0 0L8 9' stroke='#8A4B14' stroke-width='.8'/><rect x='-6' y='8' width='12' height='4' rx='1' fill='#8A4B14'/>" +
        "<ellipse cx='0' cy='8.5' rx='5' ry='2' fill='#FFF8E1'/><ellipse cx='0' cy='20' rx='10' ry='9' fill='#B5651D'/><path d='M-9 19h18' stroke='#E9B949' stroke-width='1.4'/>" +
        "<path d='M-6 24h12' stroke='#E9B949' stroke-width='.8' stroke-dasharray='2 2'/>";
    }],
    feather: [40, function () {
      return "<path d='M0 0v14' stroke='#3B7A57' stroke-width='1'/><ellipse cx='0' cy='26' rx='7' ry='12' fill='#2E9E6E'/>" +
        "<ellipse cx='0' cy='27' rx='4.6' ry='8' fill='#1C7ED6'/><ellipse cx='0' cy='27.5' rx='2.3' ry='3.6' fill='#0B2E59'/>" +
        "<ellipse cx='0' cy='27' rx='4.6' ry='8' fill='none' stroke='#E9B949' stroke-width='.8'/>";
    }],
    kite: [50, function (c) {
      return "<path d='M0 2l11 13-11 17-11-17z' fill='" + (c || "#F03E3E") + "'/><path d='M0 2l11 13h-22z' fill='#FAB005'/><path d='M0 2v30M-11 15h22' stroke='#7a2a00' stroke-width='.6'/>" +
        "<path d='M0 32q-4 5 1 9t-1 9' fill='none' stroke='#555' stroke-width='.8'/><path d='M-1 38l-4 1.5 4 1.5zM1 45l4 1.5-4 1.5z' fill='#1C7ED6'/>";
    }],
    balloon: [44, function (c) {
      return "<path d='M0 0q-3 6 0 12t0 12' stroke='#888' stroke-width='.7' fill='none'/><path d='M-2 26h4l-2-3z' fill='" + (c || "#E3367A") + "'/>" +
        "<ellipse cx='0' cy='34' rx='9' ry='11' fill='" + (c || "#E3367A") + "' transform='rotate(180 0 30)'/><ellipse cx='-3' cy='28' rx='2' ry='3' fill='#fff' fill-opacity='.5'/>";
    }],
    tassel: [44, function () {
      var cs = ["#E3367A", "#F08A24", "#F5C518", "#2FB36B", "#2F7BE3", "#9C36B5"], s = "<circle cx='0' cy='7' r='7' fill='#E3367A'/><rect x='-6' y='13' width='12' height='4' rx='2' fill='#F5C518'/>";
      for (var i = 0; i < 6; i++) s += "<path d='M" + (-5 + i * 2) + " 17L" + (-7 + i * 2.8) + " 42' stroke='" + cs[i] + "' stroke-width='1.8' stroke-linecap='round'/>";
      return s;
    }],
    marigold: [50, function () {
      var s = "";
      for (var i = 0; i < 6; i++) s += "<circle cx='0' cy='" + (5 + i * 7.2) + "' r='4.2' fill='" + (i % 2 ? "#FFB703" : "#F08C00") + "' stroke='#B35500' stroke-width='.7' stroke-dasharray='1 1'/>";
      return s + "<path d='M0 46c4 3 4 7 0 11-4-4-4-8 0-11z' fill='#2F7D32'/>";
    }],
    bell: [26, function () {
      return "<path d='M0 0v4' stroke='#B8860B' stroke-width='1.4'/><path d='M-8 18c0-9 3-14 8-14s8 5 8 14l3 3h-22z' fill='#E0A100' stroke='#B8860B' stroke-width='.8'/>" +
        "<circle cx='0' cy='23' r='2.4' fill='#B8860B'/><path d='M-4 10q4-3 8 0' stroke='#FFE08A' stroke-width='1' fill='none'/>";
    }],
    dandiya: [44, function () {
      return "<g transform='rotate(-24)'><rect x='-2' y='2' width='4' height='40' rx='2' fill='#C2255C'/><rect x='-2' y='10' width='4' height='3' fill='#FCC419'/><rect x='-2' y='30' width='4' height='3' fill='#FCC419'/></g>" +
        "<g transform='rotate(24)'><rect x='-2' y='2' width='4' height='40' rx='2' fill='#E8590C'/><rect x='-2' y='10' width='4' height='3' fill='#2F9E44'/><rect x='-2' y='30' width='4' height='3' fill='#2F9E44'/></g>" +
        "<circle cx='0' cy='4' r='3' fill='#7B2CBF'/>";
    }],
    rakhi: [30, function () {
      var s = "<path d='M0 0v4' stroke='#E64980' stroke-width='1.2'/>";
      for (var i = 0; i < 8; i++) { var p = pt(0, 14, 7, i * 45); s += "<circle cx='" + p[0] + "' cy='" + p[1] + "' r='3.6' fill='" + (i % 2 ? "#FCC419" : "#F783AC") + "'/>"; }
      return s + "<circle cx='0' cy='14' r='5' fill='#E64980'/><circle cx='0' cy='14' r='2.2' fill='#FFF3BF'/><path d='M-3 21l-2 8M3 21l2 8' stroke='#E64980' stroke-width='1'/><circle cx='-5' cy='29' r='1.6' fill='#FCC419'/><circle cx='5' cy='29' r='1.6' fill='#FCC419'/>";
    }],
    flag: [20, function () {
      return "<path d='M-12 0h24' stroke='#8a6d3b' stroke-width='1.6' stroke-linecap='round'/><rect x='-11' y='1' width='22' height='5' fill='#FF9933'/><rect x='-11' y='6' width='22' height='5' fill='#fff' stroke='#ddd' stroke-width='.4'/>" +
        "<rect x='-11' y='11' width='22' height='5' fill='#138808'/><circle cx='0' cy='8.5' r='2' fill='none' stroke='#0B3D91' stroke-width='.6'/>";
    }],
    pennants: [52, function () {
      return "<path d='M0 0l14 6-14 6z' fill='#FF9933' transform='translate(0 4)'/><path d='M0 0l14 6-14 6z' fill='#fff' stroke='#ccc' stroke-width='.5' transform='translate(0 20)'/>" +
        "<path d='M0 0l14 6-14 6z' fill='#138808' transform='translate(0 36)'/><path d='M0 0v50' stroke='#666' stroke-width='.7'/>";
    }],
    flower: [32, function () {
      var s = "";
      for (var i = 0; i < 10; i++) s += wedge(0, 16, 5, 13, i * 36, (i + 1) * 36, ["#F59F00", "#E8590C", "#FFD43B", "#7B2CBF", "#fff"][i % 5]);
      return "<path d='M0 0v3' stroke='#8a5a12'/>" + s + "<circle cx='0' cy='16' r='5' fill='#fff'/><circle cx='0' cy='16' r='2.4' fill='#7B2CBF'/>";
    }],
    streamer: [60, function (c) {
      return "<path d='M0 0q8 6 0 12t0 12 0 12 0 12 0 12' fill='none' stroke='" + (c || "#D4AF37") + "' stroke-width='2.4' stroke-linecap='round'/>";
    }]
  };

  /* ── Iconic objects for the festive "shelf" rows (100×100, inline so parts can move) ──
     .fest-lit  = the flame/glow that lights up when the row scrolls into view
     .fest-flame flickers, .fest-glow breathes, .fest-spin turns, .fest-wave flutters, .fest-float bobs */
  var FLAME = "<g class='fest-lit'><circle class='fest-glow' cx='50' cy='34' r='26' fill='#FFD36E' fill-opacity='.35'/>" +
    "<g class='fest-flame'><path d='M50 10c9 12 13 21 13 28a13 13 0 0 1-26 0c0-7 4-16 13-28z' fill='#FF9F1C'/><path d='M50 24c4 6 6 10 6 14a6 6 0 0 1-12 0c0-4 2-8 6-14z' fill='#FFF1C1'/></g></g>";
  var S = {
    diya: function () {
      return FLAME + "<path d='M50 50v6' stroke='#3b2a1a' stroke-width='2'/>" +
        "<path d='M12 56h76c-2 16-18 27-38 27S14 72 12 56z' fill='#B5541B'/><ellipse cx='50' cy='56' rx='38' ry='5.5' fill='#D9822B'/><ellipse cx='50' cy='56' rx='31' ry='3' fill='#7a3d0a'/>" +
        "<g fill='#F2C14E'><circle cx='28' cy='67' r='2.2'/><circle cx='39' cy='71' r='2.2'/><circle cx='50' cy='72.5' r='2.2'/><circle cx='61' cy='71' r='2.2'/><circle cx='72' cy='67' r='2.2'/></g>" +
        "<ellipse cx='50' cy='86' rx='15' ry='3.4' fill='#8a3d12'/>";
    },
    kandil: function () {
      return "<path d='M50 0v10' stroke='#8a5a12' stroke-width='1.6'/><rect x='43' y='8' width='14' height='5' rx='1' fill='#C9A227'/>" +
        "<polygon points='" + starPts(50, 40, 6, 30, 17) + "' fill='#E8590C' stroke='#FFD36E' stroke-width='2'/>" +
        "<polygon points='" + starPts(50, 40, 6, 18, 10) + "' fill='#FFB938'/>" +
        "<g class='fest-lit'><circle class='fest-glow' cx='50' cy='40' r='11' fill='#FFF1C1'/></g>" +
        "<path d='M40 64l-4 30M50 66v32M60 64l4 30' stroke='#C2255C' stroke-width='3.4' stroke-linecap='round'/><g fill='#FFD36E'><circle cx='36' cy='95' r='2.4'/><circle cx='50' cy='98' r='2.4'/><circle cx='64' cy='95' r='2.4'/></g>";
    },
    gulal: function (c) {
      return "<path d='M18 60Q28 28 50 24Q72 28 82 60Z' fill='" + c + "'/><g fill='#fff' fill-opacity='.28'><circle cx='40' cy='40' r='3'/><circle cx='56' cy='34' r='2.4'/><circle cx='64' cy='48' r='3'/><circle cx='34' cy='52' r='2'/></g>" +
        "<path d='M12 60h76c-3 16-19 26-38 26S15 76 12 60z' fill='#C9A227'/><ellipse cx='50' cy='60' rx='38' ry='6' fill='#E0B83C'/><path d='M22 72h56' stroke='#9c7a12' stroke-width='1.4' stroke-dasharray='3 3'/>" +
        "<g fill='" + c + "'><circle cx='8' cy='84' r='3'/><circle cx='92' cy='82' r='2.4'/><circle cx='14' cy='90' r='1.8'/></g>";
    },
    pichkari: function () {
      return "<g class='fest-float'><g transform='rotate(-22 50 50)'><rect x='2' y='38' width='7' height='26' rx='2' fill='#E3367A'/><rect x='8' y='47' width='16' height='8' fill='#9aa0a6'/>" +
        "<rect x='22' y='40' width='46' height='22' rx='11' fill='#2F7BE3'/><rect x='34' y='40' width='6' height='22' fill='#F5C518'/><rect x='50' y='40' width='6' height='22' fill='#F5C518'/>" +
        "<path d='M66 45L88 49V53L66 57Z' fill='#F08A24'/></g></g>" +
        "<g fill-opacity='.9'><circle cx='92' cy='30' r='4' fill='#E3367A'/><circle cx='98' cy='22' r='2.6' fill='#2FB36B'/><circle cx='86' cy='22' r='2.2' fill='#F5C518'/><circle cx='96' cy='38' r='2' fill='#9C36B5'/></g>";
    },
    tree: function () {
      return "<rect x='44' y='80' width='12' height='14' fill='#8B5A2B'/><path d='M50 46L88 82H12Z' fill='#237032'/><path d='M50 28L80 62H20Z' fill='#2B8A3E'/><path d='M50 10L72 42H28Z' fill='#2F9E44'/>" +
        "<path d='M26 58Q50 66 74 56M20 76Q50 86 82 74' fill='none' stroke='#F2C14E' stroke-width='2' stroke-dasharray='2 3'/>" +
        "<g><circle cx='38' cy='50' r='3.4' fill='#E03131'/><circle cx='62' cy='46' r='3.4' fill='#FCC419'/><circle cx='30' cy='70' r='3.4' fill='#FCC419'/><circle cx='56' cy='66' r='3.4' fill='#E03131'/><circle cx='72' cy='76' r='3.4' fill='#74C0FC'/></g>" +
        "<g class='fest-lit'><polygon class='fest-glow' points='" + starPts(50, 9, 5, 9, 4) + "' fill='#FCC419'/></g>";
    },
    gift: function (c) {
      return "<rect x='18' y='46' width='64' height='42' rx='3' fill='" + c + "'/><rect x='14' y='36' width='72' height='14' rx='3' fill='" + c + "' style='filter:brightness(.85)'/>" +
        "<rect x='45' y='36' width='10' height='52' fill='#FCC419'/><ellipse cx='40' cy='30' rx='11' ry='6' fill='#FCC419' transform='rotate(-25 40 30)'/><ellipse cx='60' cy='30' rx='11' ry='6' fill='#FCC419' transform='rotate(25 60 30)'/><circle cx='50' cy='34' r='4' fill='#E0A100'/>";
    },
    bauble: function (c) {
      return "<path d='M50 0v8' stroke='#888' stroke-width='1.2'/><rect x='43' y='8' width='14' height='9' rx='2' fill='#C9A227'/>" +
        "<g class='fest-float'><circle cx='50' cy='52' r='32' fill='" + c + "'/><path d='M20 50q15 10 30 0t30 0' fill='none' stroke='#fff' stroke-opacity='.75' stroke-width='3'/>" +
        "<path d='M22 62q14 8 28 0t28 0' fill='none' stroke='#FCC419' stroke-width='2'/><ellipse cx='38' cy='38' rx='7' ry='5' fill='#fff' fill-opacity='.5'/></g>";
    },
    star: function () { return "<g class='fest-lit'><circle class='fest-glow' cx='50' cy='52' r='34' fill='#FFE8A3' fill-opacity='.4'/></g>" + M.star(); },
    flag: function () {
      return "<path d='M14 4V98' stroke='#8a6d3b' stroke-width='3.4' stroke-linecap='round'/><circle cx='14' cy='4' r='3.2' fill='#C9A227'/>" +
        "<g class='fest-wave'><path d='M16 10Q36 4 56 10T96 10V24Q76 18 56 24T16 24Z' fill='#FF9933'/>" +
        "<path d='M16 24Q36 18 56 24T96 24V38Q76 32 56 38T16 38Z' fill='#fff' stroke='#d9d9d9' stroke-width='.6'/>" +
        "<path d='M16 38Q36 32 56 38T96 38V52Q76 46 56 52T16 52Z' fill='#138808'/><circle cx='56' cy='31' r='5' fill='none' stroke='#0B3D91' stroke-width='1.2'/></g>";
    },
    chakra: function () { return "<g class='fest-spin'>" + M.chakra() + "</g>"; },
    dandiya: function () { return M.dandiya(); },
    garba: function () {
      var holes = "";
      for (var row = 0; row < 3; row++) for (var i = 0; i < 5; i++) holes += "<circle cx='" + (30 + i * 10 + (row % 2) * 5) + "' cy='" + (56 + row * 10) + "' r='2.6' fill='#FFD36E'/>";
      return "<g transform='translate(0 -12)'>" + FLAME + "</g>" +
        "<rect x='38' y='36' width='24' height='10' rx='2' fill='#8A3D12'/>" +
        "<path d='M24 50C18 70 30 92 50 92S82 70 76 50C72 42 62 44 50 44S28 42 24 50Z' fill='#B5541B'/>" +
        "<g class='fest-glow'>" + holes + "</g><path d='M24 50q26 8 52 0' fill='none' stroke='#F2C14E' stroke-width='2'/>";
    },
    dancer: function (c) {
      return "<path d='M46 28L32 12M54 28L68 12' stroke='#5c1a33' stroke-width='3.4' stroke-linecap='round'/><path d='M32 12L25 3M68 12L75 3' stroke='#E8590C' stroke-width='3' stroke-linecap='round'/>" +
        "<circle cx='50' cy='16' r='7.5' fill='#5c1a33'/><circle cx='56.5' cy='12' r='3.2' fill='#5c1a33'/>" +
        "<path d='M44 25h12l-2 19h-8z' fill='" + c + "' style='filter:brightness(.8)'/>" +
        "<g class='fest-float'><path d='M45 42Q26 68 14 88Q50 99 86 88Q74 68 55 42Z' fill='" + c + "'/><path d='M14 88Q50 99 86 88L84 92Q50 103 16 92Z' fill='#FCC419'/>" +
        "<g fill='#fff' fill-opacity='.8'><circle cx='40' cy='66' r='1.8'/><circle cx='52' cy='72' r='1.8'/><circle cx='62' cy='62' r='1.8'/><circle cx='34' cy='80' r='1.8'/><circle cx='66' cy='80' r='1.8'/></g></g>";
    },
    modak: function () { return M.modak(); },
    marigold: function () { return "<g class='fest-spin' style='animation-duration:24s'>" + M.marigold() + "</g>"; },
    rakhi: function () { return M.rakhi(); },
    matki: function () {
      return "<path d='M50 0L28 40M50 0L72 40' stroke='#8A4B14' stroke-width='1.6'/><ellipse cx='50' cy='36' rx='17' ry='7' fill='#FFF8E1'/><path d='M38 38q-2 8 2 10M60 38q2 6-1 9' stroke='#FFF8E1' stroke-width='3' fill='none' stroke-linecap='round'/>" +
        "<rect x='34' y='38' width='32' height='9' rx='3' fill='#8A4B14'/><ellipse cx='50' cy='68' rx='32' ry='26' fill='#B5651D'/>" +
        "<path d='M20 64q30 12 60 0' fill='none' stroke='#F2C14E' stroke-width='3'/><g fill='#F2C14E'><circle cx='34' cy='78' r='2.4'/><circle cx='50' cy='82' r='2.4'/><circle cx='66' cy='78' r='2.4'/></g>";
    },
    feather: function () { return "<g class='fest-float'>" + M.feather() + "</g>"; },
    flute: function () {
      return "<g transform='rotate(-30 50 50)'><rect x='4' y='45' width='92' height='10' rx='5' fill='#9C6B30'/><rect x='14' y='45' width='4' height='10' fill='#F2C14E'/><rect x='82' y='45' width='4' height='10' fill='#F2C14E'/>" +
        "<g fill='#3b2a1a'><circle cx='40' cy='50' r='2'/><circle cx='49' cy='50' r='2'/><circle cx='58' cy='50' r='2'/><circle cx='67' cy='50' r='2'/><circle cx='26' cy='50' r='2.4'/></g>" +
        "<path d='M16 55v14M18 55l3 13' stroke='#E03131' stroke-width='1.8'/><circle cx='16' cy='70' r='2.6' fill='#F2C14E'/></g>";
    },
    kite: function () { return "<g class='fest-float'>" + M.kite() + "</g>"; },
    spool: function () {
      var t = "";
      for (var i = 0; i < 6; i++) t += "<path d='M28 " + (34 + i * 7) + "h44' stroke='#fff' stroke-opacity='.35'/>";
      return "<rect x='46' y='2' width='8' height='24' rx='3' fill='#8B5A2B'/><rect x='46' y='74' width='8' height='24' rx='3' fill='#8B5A2B'/>" +
        "<rect x='28' y='28' width='44' height='46' fill='#E03131'/>" + t + "<ellipse cx='50' cy='28' rx='26' ry='7' fill='#C8742B'/><ellipse cx='50' cy='74' rx='26' ry='7' fill='#C8742B'/>" +
        "<path d='M72 50q14-6 26-30' fill='none' stroke='#E03131' stroke-width='1'/>";
    },
    pookalam: function () { return "<g class='fest-spin' style='animation-duration:40s'>" + M.pookalam() + "</g>"; },
    boat: function () { return "<g class='fest-float'>" + M.boat() + "</g>"; },
    lantern: function () { return "<g class='fest-lit'><circle class='fest-glow' cx='50' cy='44' r='26' fill='#FFE08A' fill-opacity='.4'/></g>" + M.lantern(); },
    crescent: function () { return "<g class='fest-float'>" + M.crescent() + "</g>"; },
    balloons: function () {
      return "<path d='M30 40Q40 70 50 96M50 36V96M70 40Q60 70 50 96' stroke='#888' stroke-width='1' fill='none'/>" +
        "<g class='fest-float'><ellipse cx='30' cy='26' rx='15' ry='19' fill='#ED3338'/><ellipse cx='70' cy='26' rx='15' ry='19' fill='#C0C6CC'/><ellipse cx='50' cy='20' rx='16' ry='20' fill='#D4AF37'/>" +
        "<g fill='#fff' fill-opacity='.45'><ellipse cx='25' cy='18' rx='3.4' ry='5'/><ellipse cx='45' cy='12' rx='3.4' ry='5'/><ellipse cx='65' cy='18' rx='3.4' ry='5'/></g></g>";
    },
    burst: function () { return "<g class='fest-spin' style='animation-duration:20s'>" + M.burst() + "</g>"; },
    splash: function () { return M.splash(); },
    rangoli: function () { return "<g class='fest-spin' style='animation-duration:40s'>" + M.rangoli() + "</g>"; }
  };
  var WIDE = { boat: 1 };
  function shelfHtml(list) {
    return list.map(function (it, i) {
      var p = it.split(":"), name = p[0], arg = p[1];
      var fn = S[name] || S.star;
      return "<span class='fest-si fest-si-" + name + (WIDE[name] ? " fest-si-wide" : "") + "' style='--i:" + i + "'>" +
        "<svg viewBox='0 0 100 100' preserveAspectRatio='xMidYMax meet' focusable='false'>" + fn(arg) + "</svg></span>";
    }).join("");
  }

  /* ── Built-in looks. The dashboard sends the words; the look lives here. ─
     hang: [type, string length, colour?] per string, left side (right mirrors)
     wm: ornament behind headings; div: mark in the heading divider
     corner: section-corner motif (cut = drawn as a quarter from the corner)
     band: a garland strung across the top of sections */
  var P = {
    "diwali": { icon: "diya", garland: "toran", fx: "spark", extras: ["fireworks"], accent: "#E9A23B",
      fxColors: ["#FFD36E", "#FFB938", "#FF8A3D", "#FFF1C1"],
      hang: [["kandil", 70, "#E8590C"], ["diya", 140], ["kandil", 34, "#C2255C"]],
      wm: "rangoli", div: "diya", corner: { m: "rangoli", cut: true }, band3: "lights", lines: ["#E9A23B", "#E9A23B"],
      greeting: "Happy Diwali from Crystal!", sub: "May your home glow with light, warmth and good food." },
    "holi": { icon: "splash", garland: "splash", fx: "powder", extras: ["clickburst"], accent: "#E3367A",
      fxColors: ["#E3367A", "#F08A24", "#F5C518", "#2FB36B", "#2F7BE3", "#9C36B5"],
      hang: [["tassel", 60], ["balloon", 120, "#2F7BE3"], ["balloon", 40, "#F5C518"]],
      wm: "splash", div: "splash", corner: { m: "splash", cut: true }, lines: ["#E3367A", "#2F7BE3"],
      greeting: "Happy Holi from Crystal!", sub: "Wishing you a season full of colour, laughter and sweets." },
    "navratri": { icon: "dandiya", garland: "toran", fx: "petal", accent: "#E8590C",
      fxColors: ["#F08C00", "#FFB703", "#E8590C", "#D6336C"],
      hang: [["dandiya", 60], ["marigold", 120], ["bell", 40]],
      wm: "mandala", div: "dandiya", corner: { m: "mandala", cut: true }, band3: "toran", lines: ["#C2255C", "#E8590C"],
      greeting: "Happy Navratri & Dussehra from Crystal!", sub: "Nine nights of devotion, dandiya and festive feasts." },
    "ganesh-chaturthi": { icon: "marigold", garland: "toran", fx: "petal", accent: "#F28C1B",
      fxColors: ["#F08C00", "#FFB703", "#E03131"],
      hang: [["marigold", 60], ["bell", 130], ["marigold", 30]],
      wm: "marigold", div: "modak", corner: { m: "modak", cut: false }, band3: "toran", lines: ["#F28C1B", "#E03131"],
      greeting: "Happy Ganesh Chaturthi from Crystal!", sub: "Ganpati Bappa Morya! Wishing your home wisdom and prosperity." },
    "raksha-bandhan": { icon: "rakhi", garland: "rakhi", fx: "petal", accent: "#D6336C",
      fxColors: ["#F783AC", "#E64980", "#FCC419", "#FFD8E4"],
      hang: [["rakhi", 70], ["rakhi", 130], ["star", 36, "#FCC419"]],
      wm: "rakhi", div: "rakhi", corner: { m: "rakhi", cut: true }, band2: "rakhi", lines: ["#E64980", "#FCC419"],
      greeting: "Happy Raksha Bandhan from Crystal!", sub: "Celebrating the bond that holds a family together." },
    "janmashtami": { icon: "feather", garland: "peacock", fx: "feather", accent: "#1C7ED6",
      fxColors: ["#2E9E6E", "#1C7ED6", "#E9B949"],
      hang: [["matki", 60], ["feather", 120], ["matki", 30]],
      wm: "feather", div: "feather", corner: { m: "feather", cut: false }, lines: ["#2E9E6E", "#1C7ED6"],
      greeting: "Happy Janmashtami from Crystal!", sub: "May Kanha fill your home with joy and makhan-mishri." },
    "independence-day": { icon: "flag", garland: "bunting", fx: "petal", accent: "#FF9933",
      fxColors: ["#FF9933", "#FFFFFF", "#138808"],
      hang: [["flag", 60], ["pennants", 110], ["flag", 30]],
      wm: "chakra", div: "chakra", corner: { m: "flag", cut: false, hero: true }, band2: "bunting", lines: ["#FF9933", "#138808"],
      greeting: "Happy Independence Day from Crystal!", sub: "Celebrating the spirit of a free India." },
    "republic-day": { icon: "flag", garland: "bunting", fx: "petal", accent: "#FF9933",
      fxColors: ["#FF9933", "#FFFFFF", "#138808"],
      hang: [["flag", 60], ["pennants", 110], ["flag", 30]],
      wm: "chakra", div: "chakra", corner: { m: "flag", cut: false, hero: true }, band2: "bunting", lines: ["#FF9933", "#138808"],
      greeting: "Happy Republic Day from Crystal!", sub: "Saluting the spirit of our Constitution." },
    "sankranti": { icon: "kite", garland: "kites", fx: "kite", accent: "#1098AD",
      fxColors: ["#F03E3E", "#FAB005", "#1C7ED6", "#37B24D", "#AE3EC9"],
      hang: [["kite", 70, "#1C7ED6"], ["kite", 130, "#F03E3E"], ["kite", 30, "#37B24D"]],
      wm: "kite", div: "kite", corner: { m: "kite", cut: false }, lines: ["#1098AD", "#FAB005"],
      greeting: "Happy Sankranti, Pongal & Lohri!", sub: "May the harvest season fill every kitchen with abundance." },
    "onam": { icon: "flower", garland: "pookalam", fx: "petal", accent: "#E0A100",
      fxColors: ["#F59F00", "#E8590C", "#FFFFFF", "#7B2CBF"],
      hang: [["flower", 60], ["bell", 120], ["flower", 30]],
      wm: "pookalam", div: "pookalam", corner: { m: "pookalam", cut: true, alt: "boat" }, lines: ["#C9A227", "#C9A227"],
      greeting: "Happy Onam from Crystal!", sub: "Wishing you a sadya-full season of joy and togetherness." },
    "eid": { icon: "crescent", garland: "lanterns", fx: "twinkle", accent: "#0E8A66",
      fxColors: ["#F5D98B", "#E9C46A", "#FFF3C4"],
      hang: [["lantern", 70], ["crescent", 140], ["lantern", 30]],
      wm: "star8", div: "crescent", corner: { m: "star8", cut: true }, lines: ["#C9A227", "#0E8A66"],
      greeting: "Eid Mubarak from Crystal!", sub: "Wishing you peace, joy and feasts shared with loved ones." },
    "christmas": { icon: "tree", garland: "holly", fx: "snow", accent: "#C92A2A", christmas: true,
      fxColors: ["#FFFFFF"],
      hang: [["bauble", 70, "#C92A2A"], ["star", 140], ["bauble", 34, "#2B8A3E"]],
      wm: "snowflake", div: "holly", corner: { m: "holly", cut: true }, band3: "holly", lines: ["#2B8A3E", "#C92A2A"],
      greeting: "Merry Christmas from Crystal!", sub: "Warm wishes for a season of togetherness and good food." },
    "new-year": { icon: "sparkle", garland: "confetti", fx: "confetti", extras: ["fireworks", "balloons"], accent: "#D4AF37",
      fxColors: ["#D4AF37", "#F1D27A", "#C0C6CC", "#ED3338"],
      hang: [["star", 60], ["streamer", 120, "#ED3338"], ["bauble", 34, "#C0C6CC"]],
      wm: "burst", div: "star", corner: { m: "burst", cut: true }, lines: ["#D4AF37", "#D4AF37"],
      greeting: "Happy New Year from Crystal!", sub: "Here is to a year of great meals and greater company." }
  };
  var GENERIC = { icon: "sparkle", garland: "confetti", fx: "confetti", accent: "#D4AF37",
    fxColors: ["#D4AF37", "#F1D27A", "#ED3338"], hang: [["star", 60], ["streamer", 110, "#D4AF37"], ["star", 30, "#F1D27A"]],
    wm: "burst", div: "star", corner: { m: "burst", cut: true }, lines: ["#D4AF37", "#D4AF37"],
    greeting: "Season's greetings from Crystal!", sub: "" };

  // Each festival's iconic objects (a row under the hero and above the footer), and the
  // short burst played once when a section heading scrolls into view.
  var SHELF = {
    "diwali": ["diya", "kandil", "diya", "diya", "rangoli", "diya", "diya", "kandil", "diya"],
    "holi": ["gulal:#E3367A", "gulal:#F5C518", "pichkari", "gulal:#2FB36B", "splash", "gulal:#2F7BE3", "pichkari", "gulal:#F08A24", "gulal:#9C36B5"],
    "navratri": ["dandiya", "dancer:#C2255C", "garba", "dancer:#E8590C", "dandiya", "dancer:#7B2CBF", "garba", "dancer:#2F9E44", "dandiya"],
    "ganesh-chaturthi": ["marigold", "modak", "diya", "modak", "marigold", "modak", "diya", "modak", "marigold"],
    "raksha-bandhan": ["rakhi", "diya", "rakhi", "gift:#E64980", "rakhi", "gift:#FCC419", "rakhi", "diya", "rakhi"],
    "janmashtami": ["feather", "matki", "flute", "feather", "matki", "feather", "flute", "matki", "feather"],
    "independence-day": ["chakra", "flag", "chakra", "flag", "chakra", "flag", "chakra", "flag", "chakra"],
    "republic-day": ["chakra", "flag", "chakra", "flag", "chakra", "flag", "chakra", "flag", "chakra"],
    "sankranti": ["kite", "spool", "kite", "kite", "spool", "kite", "kite", "spool", "kite"],
    "onam": ["pookalam", "boat", "pookalam", "boat", "pookalam", "boat", "pookalam"],
    "eid": ["lantern", "crescent", "lantern", "star", "lantern", "star", "lantern", "crescent", "lantern"],
    "christmas": ["gift:#C92A2A", "bauble:#C92A2A", "tree", "star", "gift:#2B8A3E", "tree", "bauble:#1C7ED6", "gift:#E0A100", "tree"],
    "new-year": ["balloons", "gift:#D4AF37", "star", "balloons", "burst", "balloons", "star", "gift:#ED3338", "balloons"]
  };
  var POP = {
    "diwali": "firework", "new-year": "confetti", "holi": "powder", "christmas": "stars", "eid": "stars",
    "independence-day": "petals", "republic-day": "petals", "navratri": "petals", "ganesh-chaturthi": "petals",
    "raksha-bandhan": "petals", "janmashtami": "petals", "onam": "petals", "sankranti": ""
  };
  P.diwali.band2 = "lights";
  Object.keys(P).forEach(function (k) { P[k].shelf = SHELF[k]; P[k].pop = POP[k]; });
  GENERIC.shelf = ["star", "burst", "star", "balloons", "star", "burst", "star"];
  GENERIC.pop = "confetti";

  var ICONS = {
    diya: '<path d="M2.5 13.5h19c-.8 4.2-4.6 7-9.5 7s-8.7-2.8-9.5-7z" fill="currentColor"/><path d="M12 2.5c2.2 3 3.2 5 3.2 6.9a3.2 3.2 0 0 1-6.4 0c0-1.9 1-3.9 3.2-6.9z" fill="#FFB938"/><path d="M12 6.5c.9 1.3 1.3 2.2 1.3 3a1.3 1.3 0 0 1-2.6 0c0-.8.4-1.7 1.3-3z" fill="#FFF1C1"/>',
    splash: '<circle cx="8" cy="9" r="5" fill="#E3367A"/><circle cx="15.5" cy="8" r="4.2" fill="#F5C518"/><circle cx="12.5" cy="15.5" r="5" fill="#2F7BE3" fill-opacity=".9"/><circle cx="18" cy="15" r="2.6" fill="#2FB36B"/><circle cx="5" cy="17" r="1.8" fill="#F08A24"/>',
    dandiya: '<path d="M5 20 18 4M19 20 6 4" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" fill="none"/><path d="M15.4 7.2l2 1.6M8.6 7.2l-2 1.6" stroke="#FFB703" stroke-width="2.4" stroke-linecap="round"/>',
    marigold: '<circle cx="12" cy="12" r="9" fill="#F08C00"/><circle cx="12" cy="12" r="9" fill="none" stroke="#C85D00" stroke-width="1.4" stroke-dasharray="1.6 1.6"/><circle cx="12" cy="12" r="5.5" fill="#FFB703"/><circle cx="12" cy="12" r="2.2" fill="#C85D00"/>',
    rakhi: '<path d="M1 12h22" stroke="#E64980" stroke-width="2"/><g fill="#FCC419"><circle cx="12" cy="6.5" r="3"/><circle cx="12" cy="17.5" r="3"/><circle cx="6.5" cy="12" r="3"/><circle cx="17.5" cy="12" r="3"/></g><circle cx="12" cy="12" r="4" fill="#E64980"/><circle cx="12" cy="12" r="1.7" fill="#FFF3BF"/>',
    feather: '<path d="M12 23V12" stroke="currentColor" stroke-width="1.4"/><ellipse cx="12" cy="9" rx="6" ry="8" fill="#2E9E6E"/><ellipse cx="12" cy="9.6" rx="3.9" ry="5.4" fill="#1C7ED6"/><ellipse cx="12" cy="10" rx="2" ry="2.8" fill="#0B2E59"/><ellipse cx="12" cy="9.6" rx="3.9" ry="5.4" fill="none" stroke="#E9B949" stroke-width=".9"/>',
    flag: '<path d="M4 2v20" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><rect x="5" y="4" width="16" height="4" fill="#FF9933"/><rect x="5" y="8" width="16" height="4" fill="#fff"/><rect x="5" y="12" width="16" height="4" fill="#138808"/><circle cx="13" cy="10" r="1.5" fill="none" stroke="#0B3D91" stroke-width=".8"/>',
    kite: '<path d="M12 2l7 9-7 10-7-10z" fill="#F03E3E"/><path d="M12 2l7 9H5z" fill="#FAB005"/><path d="M12 2v19M5 11h14" stroke="#7a2a00" stroke-width=".8"/><path d="M12 21c-1 1.2 1 1.6 0 2.6" stroke="currentColor" stroke-width="1" fill="none"/>',
    flower: '<circle cx="12" cy="12" r="10" fill="#F59F00"/><circle cx="12" cy="12" r="7.4" fill="#E8590C"/><circle cx="12" cy="12" r="5" fill="#fff"/><circle cx="12" cy="12" r="2.8" fill="#7B2CBF"/>',
    crescent: '<path d="M14.5 3.2A9 9 0 1 0 20.8 16 7.2 7.2 0 1 1 14.5 3.2z" fill="currentColor"/><path d="M18.5 5.5l.8 1.8 1.9.2-1.4 1.3.4 1.9-1.7-1-1.7 1 .4-1.9-1.4-1.3 1.9-.2z" fill="currentColor"/>',
    tree: '<path d="M12 3l6 8h-3l4.5 6h-15L9 11H6z" fill="#2B8A3E"/><rect x="10.8" y="17" width="2.4" height="4" fill="#8B5A2B"/><path d="M12 .8l.9 1.9 2 .2-1.5 1.4.4 2-1.8-1-1.8 1 .4-2-1.5-1.4 2-.2z" fill="#FCC419"/><circle cx="10" cy="13" r="1" fill="#E03131"/><circle cx="14.5" cy="15" r="1" fill="#FCC419"/>',
    sparkle: '<path d="M12 1.5l2.3 7.2 7.2 2.3-7.2 2.3L12 20.5l-2.3-7.2L2.5 11l7.2-2.3z" fill="currentColor"/><circle cx="19.5" cy="19" r="1.6" fill="currentColor"/>'
  };
  function icon(name, cls) {
    return '<svg class="' + (cls || "fest-ico") + '" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' + (ICONS[name] || ICONS.sparkle) + "</svg>";
  }

  // Garland tiles that repeat along the bottom of the ribbon, the footer top and across sections.
  var G = {
    lights: [108, 26, "<defs><radialGradient id='g'><stop offset='0' stop-color='#FFE9A8' stop-opacity='.95'/><stop offset='1' stop-color='#FFB938' stop-opacity='0'/></radialGradient></defs><path d='M0 2 Q18 12 36 2 Q54 12 72 2 Q90 12 108 2' fill='none' stroke='#4a2e14' stroke-opacity='.6'/>" +
      "<circle cx='18' cy='14' r='9' fill='url(#g)'/><rect x='16.6' y='6' width='2.8' height='3' rx='.6' fill='#6b4a1f'/><ellipse cx='18' cy='13' rx='3' ry='4.4' fill='#FFC94D'/>" +
      "<circle cx='54' cy='14' r='9' fill='url(#g)'/><rect x='52.6' y='6' width='2.8' height='3' rx='.6' fill='#6b4a1f'/><ellipse cx='54' cy='13' rx='3' ry='4.4' fill='#FF8A3D'/>" +
      "<circle cx='90' cy='14' r='9' fill='url(#g)'/><rect x='88.6' y='6' width='2.8' height='3' rx='.6' fill='#6b4a1f'/><ellipse cx='90' cy='13' rx='3' ry='4.4' fill='#FFE7A3'/>"],
    toran: [60, 30, "<path d='M0 1.5H60' stroke='#8a5a12' stroke-width='1.4'/>" +
      "<g stroke='#B35500' stroke-width='.8' stroke-dasharray='1.1 1.1'><circle cx='15' cy='6.5' r='3.6' fill='#F08C00'/><circle cx='15' cy='13.4' r='3.6' fill='#FFB703'/><circle cx='15' cy='20.3' r='3.6' fill='#F08C00'/><circle cx='15' cy='27' r='2.6' fill='#FFB703'/></g>" +
      "<path d='M45 1.5C51 6 50.5 13 45 19 39.5 13 39 6 45 1.5Z' fill='#2F7D32'/><path d='M45 3v14' stroke='#A9D18E' stroke-width='.7'/>" +
      "<path d='M30 1.5C33 4 33 8 30 11 27 8 27 4 30 1.5Z' fill='#3E8E41'/>"],
    splash: [150, 18, "<g fill-opacity='.85'><circle cx='10' cy='3' r='5' fill='#E3367A'/><circle cx='22' cy='8' r='2.2' fill='#E3367A'/><circle cx='40' cy='2' r='6' fill='#F5C518'/><circle cx='52' cy='10' r='2.5' fill='#F08A24'/><circle cx='70' cy='4' r='5' fill='#2FB36B'/><circle cx='80' cy='12' r='1.6' fill='#2FB36B'/><circle cx='98' cy='3' r='6.5' fill='#2F7BE3'/><circle cx='110' cy='11' r='2' fill='#9C36B5'/><circle cx='126' cy='2' r='5' fill='#F08A24'/><circle cx='140' cy='9' r='2.4' fill='#E3367A'/><circle cx='32' cy='13' r='1.2' fill='#2F7BE3'/><circle cx='88' cy='15' r='1.1' fill='#F5C518'/></g>"],
    bunting: [60, 20, "<path d='M0 1.5 Q30 5 60 1.5' fill='none' stroke='#555' stroke-opacity='.55'/><path d='M4 2.3H16L10 16Z' fill='#FF9933'/><path d='M24 3.3H36L30 17Z' fill='#fff' stroke='#c8c8c8' stroke-width='.6'/><circle cx='30' cy='7.5' r='2' fill='none' stroke='#0B3D91' stroke-width='.7'/><path d='M44 2.3H56L50 16Z' fill='#138808'/>"],
    rakhi: [140, 22, "<path d='M0 5 Q17.5 1 35 5 T70 5 T105 5 T140 5' fill='none' stroke='#E64980' stroke-width='1.6'/><path d='M0 5 Q17.5 9 35 5 T70 5 T105 5 T140 5' fill='none' stroke='#FCC419' stroke-width='1.1'/>" +
      "<path d='M66 8v9M74 8v9' stroke='#E64980' stroke-width='.9'/><circle cx='66' cy='18' r='1.6' fill='#FCC419'/><circle cx='74' cy='18' r='1.6' fill='#FCC419'/>" +
      "<g fill='#FCC419'><circle cx='70' cy='1.6' r='2.6'/><circle cx='70' cy='10.4' r='2.6'/><circle cx='65.6' cy='6' r='2.6'/><circle cx='74.4' cy='6' r='2.6'/></g><circle cx='70' cy='6' r='3.2' fill='#E64980'/><circle cx='70' cy='6' r='1.3' fill='#FFF3BF'/>"],
    peacock: [72, 28, "<path d='M0 1.5H72' stroke='#0B2E59' stroke-opacity='.5'/><path d='M18 1.5v6' stroke='#2E9E6E'/><ellipse cx='18' cy='15' rx='5.2' ry='7.6' fill='#2E9E6E'/><ellipse cx='18' cy='15.6' rx='3.4' ry='5' fill='#1C7ED6'/><ellipse cx='18' cy='16' rx='1.7' ry='2.5' fill='#0B2E59'/><ellipse cx='18' cy='15.6' rx='3.4' ry='5' fill='none' stroke='#E9B949' stroke-width='.8'/>" +
      "<path d='M51 1.5 49 9M57 1.5 59 9' stroke='#8A4B14' stroke-width='.7'/><ellipse cx='54' cy='16' rx='6.5' ry='5.6' fill='#B5651D'/><rect x='49.5' y='9' width='9' height='3' rx='1' fill='#8A4B14'/><ellipse cx='54' cy='9.4' rx='3.6' ry='1.5' fill='#FFF8E1'/><path d='M48.5 16h11' stroke='#E9B949' stroke-width='.9'/>"],
    kites: [84, 26, "<path d='M0 2 Q42 8 84 2' fill='none' stroke='#555' stroke-opacity='.5' stroke-width='.7'/>" +
      "<path d='M21 4l6 7-6 9-6-9z' fill='#F03E3E'/><path d='M21 4l6 7H15z' fill='#FAB005'/><path d='M21 20c-1.5 1.4 1.5 2.4 0 4' fill='none' stroke='#F03E3E' stroke-width='.8'/>" +
      "<path d='M63 5l6 7-6 9-6-9z' fill='#1C7ED6'/><path d='M63 5v16' stroke='#fff' stroke-width='.8'/><path d='M63 21c-1.5 1.4 1.5 2.4 0 4' fill='none' stroke='#1C7ED6' stroke-width='.8'/>"],
    pookalam: [44, 20, "<path d='M0 1H44' stroke='#C9A227' stroke-width='1.2'/><circle cx='22' cy='10' r='7.6' fill='#F59F00'/><circle cx='22' cy='10' r='5.6' fill='#E8590C'/><circle cx='22' cy='10' r='3.7' fill='#fff'/><circle cx='22' cy='10' r='2' fill='#7B2CBF'/><path d='M6 8c3-3 6-1 6 2-3 1-5 0-6-2zM38 8c-3-3-6-1-6 2 3 1 5 0 6-2z' fill='#2F9E44'/>"],
    lanterns: [96, 32, "<path d='M0 1.5H96' stroke='#C9A227' stroke-opacity='.7'/><path d='M24 1.5v7M72 1.5v4' stroke='#C9A227' stroke-width='.7'/>" +
      "<path d='M20 8.5h8l-1 2h-6z' fill='#C9A227'/><path d='M20.5 10.5h7l2 4-2 9h-7l-2-9z' fill='#FFD36E' fill-opacity='.9' stroke='#B8860B' stroke-width='.8'/><path d='M24 10.5v13M18.5 14.5h11' stroke='#B8860B' stroke-width='.5'/><path d='M21 23.5h6l-3 3z' fill='#C9A227'/>" +
      "<path d='M73 6a6 6 0 1 0 5.4 8.6 4.7 4.7 0 1 1-5.4-8.6z' fill='#E9C46A'/><path d='M80.5 6.5l.6 1.4 1.5.1-1.1 1 .3 1.5-1.3-.8-1.3.8.3-1.5-1.1-1 1.5-.1z' fill='#E9C46A'/>"],
    holly: [64, 22, "<path d='M0 3 Q16 9 32 3 T64 3' fill='none' stroke='#1B5E33' stroke-width='1.6'/>" +
      "<path d='M16 7c-4-1-7 1-9 4 3 0 4 1 4 3 2-2 4-3 5-7z' fill='#2B8A3E'/><path d='M16 7c4-1 7 1 9 4-3 0-4 1-4 3-2-2-4-3-5-7z' fill='#237032'/><circle cx='15' cy='8.5' r='2' fill='#E03131'/><circle cx='18' cy='9' r='1.8' fill='#C92A2A'/><circle cx='16.5' cy='11.2' r='1.8' fill='#E03131'/>" +
      "<circle cx='48' cy='9' r='2.2' fill='#FCC419'/><circle cx='48' cy='9' r='4.5' fill='#FCC419' fill-opacity='.18'/><rect x='47' y='4.6' width='2' height='2.4' fill='#555'/>"],
    confetti: [120, 18, "<g><rect x='6' y='2' width='3' height='6' rx='.6' fill='#D4AF37' transform='rotate(20 7.5 5)'/><circle cx='22' cy='9' r='1.6' fill='#ED3338'/><rect x='34' y='3' width='3' height='6' rx='.6' fill='#C0C6CC' transform='rotate(-30 35.5 6)'/><path d='M50 4l1 2.4 2.4 1-2.4 1-1 2.4-1-2.4-2.4-1 2.4-1z' fill='#D4AF37'/><rect x='64' y='8' width='3' height='6' rx='.6' fill='#ED3338' transform='rotate(45 65.5 11)'/><circle cx='78' cy='4' r='1.4' fill='#D4AF37'/><rect x='90' y='2' width='3' height='6' rx='.6' fill='#F1D27A' transform='rotate(-15 91.5 5)'/><circle cx='104' cy='11' r='1.5' fill='#C0C6CC'/><path d='M114 6l.8 1.8 1.8.8-1.8.8-.8 1.8-.8-1.8-1.8-.8 1.8-.8z' fill='#ED3338'/></g>"]
  };
  function garlandCss(name) {
    var g = G[name] || G.confetti;
    // drawn at 80%: hangs a little way into the header, never far
    return { image: dataUri(svgDoc(g[0], g[1], "0 0 " + g[0] + " " + g[1], g[2])), w: Math.round(g[0] * 0.8), h: Math.round(g[1] * 0.8) };
  }

  /* ── Where are we ──────────────────────────────────────────────────────── */
  function isHome() {
    var p = location.pathname.replace(/\/+$/, "/");
    return p === "/" || /\/(index|index-v2)(\.html?)?$/i.test(p);
  }
  function today() {
    var d = new Date();
    return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  }
  function inWindow(t) {
    var d = today();
    if (t.starts_on && d < t.starts_on) return false;
    if (t.ends_on && d > t.ends_on) return false;
    return true;
  }
  var reduced = false;
  try { reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) {}

  /* ── Which theme ───────────────────────────────────────────────────────── */
  var qs = (function () { try { return new URLSearchParams(location.search); } catch (e) { return null; } })();
  var q = qs ? (qs.get("theme") || "").trim().toLowerCase() : "";
  var qLevel = qs ? (qs.get("intensity") || "").trim().toLowerCase() : "";
  if (q === "off" || q === "none" || q === "0") { put("sessionStorage", PKEY, null); q = ""; }
  else if (q && /^[a-z0-9-]{1,40}$/.test(q)) {
    put("sessionStorage", PKEY, JSON.stringify({ slug: q, t: null, level: LEVELS[qLevel] ? qLevel : "" }));
    put("sessionStorage", DKEY, null);
  } else q = "";
  var preview = null;
  try { preview = JSON.parse(get("sessionStorage", PKEY) || "null"); } catch (e) { preview = null; }

  function fallbackFor(slug) {
    var p = P[slug] || GENERIC;
    return { slug: slug, name: slug, greeting: p.greeting, sub_text: p.sub, link_text: "", link_url: "",
      effects: true, scope: "site", intensity: "festive", accent: "", banner: null, starts_on: null, ends_on: null };
  }

  var current = null;   // the theme drawn now, as JSON, so a refresh that changes nothing does nothing

  function choose(t) {
    if (!t || !t.slug) return null;
    if (!preview && !inWindow(t)) return null;
    if (t.scope === "home" && !isHome()) return null;
    if (preview && preview.level) { t = JSON.parse(JSON.stringify(t)); t.intensity = preview.level; }
    return t;
  }

  /* ── Drawing ───────────────────────────────────────────────────────────── */
  var root = document.documentElement;
  var els = [];          // everything we added, for a clean teardown
  var cleanups = [];
  var cssLink = null;

  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }
  function deco(tag, cls) { var n = el(tag, cls); n.setAttribute("aria-hidden", "true"); return n; }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function safeHref(u) {
    u = String(u || "").trim();
    if (!u) return "";
    if (/^(https?:)?\/\//i.test(u) || /^[\w./#?=&%-]+$/.test(u)) return u;
    return "";
  }
  function addClass(n, c) { n.classList.add(c); cleanups.push(function () { n.classList.remove(c); }); }

  function teardown() {
    cleanups.forEach(function (f) { try { f(); } catch (e) {} });
    cleanups = [];
    els.forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
    els = [];
    Array.prototype.forEach.call(document.querySelectorAll(".fest-in"), function (n) { n.classList.remove("fest-in"); });
    heroEl = null; pops = 0;
    root.removeAttribute("data-festival");
    root.removeAttribute("data-fest-level");
    root.classList.remove("fest-on", "fest-rib-on", "fest-rib-up");
    ["--fest-accent", "--fest-top", "--fest-rib-h", "--fest-hdr-b", "--fest-wm", "--fest-div", "--fest-corner", "--fest-corner2"].forEach(function (v) { root.style.removeProperty(v); });
    var h = document.querySelector(".fest-hdr");
    if (h) h.classList.remove("fest-hdr");
  }

  function loadCss(done) {
    if (cssLink && cssLink.__ready) return done(true);
    if (!cssLink) {
      cssLink = document.createElement("link");
      cssLink.rel = "stylesheet";
      cssLink.href = CSS_URL;
      cssLink.__waiters = [];
      cssLink.onload = function () { cssLink.__ready = true; cssLink.__waiters.forEach(function (f) { f(true); }); cssLink.__waiters = []; };
      cssLink.onerror = function () { cssLink.__waiters.forEach(function (f) { f(false); }); cssLink.__waiters = []; };
      document.head.appendChild(cssLink);
    }
    cssLink.__waiters.push(done);
  }

  function findHeader() {
    var h = document.getElementById("hdr");
    if (h && h.tagName === "HEADER") return h;
    var all = document.getElementsByTagName("header");
    for (var i = 0; i < all.length; i++) {
      if (getComputedStyle(all[i]).position === "fixed") return all[i];
    }
    return null;
  }

  function apply(t) {
    var key = t ? JSON.stringify(t) : "";
    if (key === current) return;
    current = key;
    teardown();
    if (!t) return;
    var preset = P[t.slug] || GENERIC;
    var level = LEVELS[t.intensity] ? t.intensity : "festive";
    root.setAttribute("data-festival", P[t.slug] ? t.slug : "generic");
    root.setAttribute("data-fest-level", level);
    root.classList.add("fest-on");
    if (t.accent && /^#[0-9a-f]{6}$/i.test(t.accent)) root.style.setProperty("--fest-accent", t.accent);

    loadCss(function (ok) {
      if (!ok || current !== key) return;
      draw(t, preset, LEVELS[level]);
    });
  }

  function draw(t, preset, lvl) {
    var gl = garlandCss(preset.garland);
    var body = document.body;
    var greeting = t.greeting || preset.greeting;
    var sub = t.sub_text || "";
    var href = safeHref(t.link_url);
    var hidden = get("sessionStorage", DKEY) === t.slug;
    var header = findHeader();

    /* Ribbon + garland + spacer */
    if (!hidden) {
      var rib = el("div", "fest-rib");
      rib.setAttribute("role", "region");
      rib.setAttribute("aria-label", "Festive greeting");
      rib.setAttribute("translate", "yes");
      rib.innerHTML =
        '<div class="fest-rib-in">' + icon(preset.icon) +
        '<span class="fest-msg"><b class="fest-greet">' + esc(greeting) + "</b>" +
        (sub ? '<span class="fest-sub">' + esc(sub) + "</span>" : "") + "</span>" +
        (t.link_text && href ? '<a class="fest-cta" href="' + esc(href) + '">' + esc(t.link_text) + ' <span aria-hidden="true">&rarr;</span></a>' : "") +
        "</div>" +
        '<button type="button" class="fest-x" aria-label="Hide the greeting" translate="no">' +
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg></button>';
      var garland = deco("div", "fest-garland");
      garland.style.backgroundImage = gl.image;
      garland.style.backgroundSize = gl.w + "px " + gl.h + "px";
      garland.style.height = gl.h + "px";
      var spacer = deco("div", "fest-spacer");

      body.insertBefore(spacer, body.firstChild);
      body.appendChild(garland);
      body.appendChild(rib);
      els.push(spacer, garland, rib);

      if (header) header.classList.add("fest-hdr");

      var place = function () {
        // Straight under the support bar; never lower than where the header starts.
        var sb = document.querySelector(".support-bar");
        var top = sb ? sb.getBoundingClientRect().height : 0;
        if (header) {
          var hTop = parseFloat(getComputedStyle(header).top);
          if (hTop >= 0 && (!sb || hTop < top)) top = hTop;
        }
        root.style.setProperty("--fest-top", top + "px");
        root.style.setProperty("--fest-rib-h", rib.offsetHeight + "px");
      };
      place();
      root.classList.add("fest-rib-on");
      // Transitions only from here on: the first paint must not slide the header.
      var animT = setTimeout(function () { root.classList.add("fest-anim"); }, 500);
      cleanups.push(function () { clearTimeout(animT); root.classList.remove("fest-anim"); });
      var onResize = function () { place(); };
      addEventListener("resize", onResize, { passive: true });
      cleanups.push(function () { removeEventListener("resize", onResize); });

      // Tuck away once the visitor scrolls, back at the top of the page.
      var up = false;
      var onScroll = function () {
        var y = window.pageYOffset || document.documentElement.scrollTop || 0;
        if (!up && y > 140) { up = true; root.classList.add("fest-rib-up"); }
        else if (up && y < 60) { up = false; root.classList.remove("fest-rib-up"); if (document.querySelector(".fest-hang")) hangCheck(); }
      };
      addEventListener("scroll", onScroll, { passive: true });
      cleanups.push(function () { removeEventListener("scroll", onScroll); });
      onScroll();

      rib.querySelector(".fest-x").addEventListener("click", function () {
        put("sessionStorage", DKEY, t.slug);
        root.classList.remove("fest-rib-on", "fest-rib-up");
        root.style.removeProperty("--fest-rib-h");
        [spacer, garland, rib].forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
        if (header) header.classList.remove("fest-hdr");
        stopFx();
        refreshScroll();
      });
      refreshScroll();
    }

    /* Footer band */
    var foot = document.querySelector("footer");
    if (foot) {
      var band = deco("div", "fest-foot");
      band.style.backgroundImage = gl.image;
      band.style.backgroundSize = gl.w + "px " + gl.h + "px";
      band.style.height = gl.h + "px";
      if (getComputedStyle(foot).position === "static") {
        foot.style.position = "relative";
        cleanups.push(function () { foot.style.position = ""; });
      }
      foot.insertBefore(band, foot.firstChild);
      els.push(band);
    }

    /* Particles first: the scroll effects below play their bursts on this canvas */
    if (t.effects !== false && !hidden) startFx(preset, lvl);

    /* Props on every page */
    if (lvl >= 2) {
      root.style.setProperty("--fest-wm", motifUri(preset.wm));
      root.style.setProperty("--fest-div", dividerUri(preset.div, preset.lines[0], preset.lines[1]));
      setupReveal(preset);
      drawHangers(preset, lvl, header);
      drawHeaderProps(preset, header);
      decorate(preset, lvl);
      drawShelves(preset);
      setupScrollFx();
      // Listing grids, product pages and articles render after this runs; catch up once things settle.
      var t1 = setTimeout(function () { decorate(preset, lvl); hangCheck(); }, 1800);
      var onLoad = function () { decorate(preset, lvl); hangCheck(); };
      addEventListener("load", onLoad);
      cleanups.push(function () { clearTimeout(t1); removeEventListener("load", onLoad); });
    }

    /* Home hero */
    if (isHome()) drawHero(t, preset, greeting, sub);

    /* Preview chip */
    if (preview) {
      var chip = el("div", "fest-chip");
      chip.setAttribute("translate", "no");
      var label = t.name && t.name !== t.slug ? t.name
        : t.slug.replace(/-/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase(); });
      chip.title = "Only you see this theme. Visitors see whatever the dashboard has switched on.";
      chip.innerHTML = "Preview: <b>" + esc(label) + "</b>" +
        '<a href="' + esc(location.pathname + "?theme=off") + '">Exit</a>';
      body.appendChild(chip);
      els.push(chip);
    }

  }

  /* ── Scroll: things play once as they come into view ───────────────────── */
  var io = null, heroEl = null, lastPop = 0, pops = 0;
  function setupReveal(preset) {
    if (reduced || !("IntersectionObserver" in window)) { io = null; return; }
    io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        var n = e.target;
        io.unobserve(n);
        n.classList.add("fest-in");
        if (n.classList.contains("fest-h")) popAt(n, preset);
      });
    }, { threshold: 0.35, rootMargin: "0px 0px -6% 0px" });
    root.classList.add("fest-io");
    cleanups.push(function () { if (io) io.disconnect(); io = null; root.classList.remove("fest-io"); });
  }
  function observe(n) { if (io) io.observe(n); else n.classList.add("fest-in"); }
  function popAt(h, preset) {
    if (!fx || !preset.pop) return;
    var now = Date.now();
    if (now - lastPop < 300 || pops > 16) return;
    lastPop = now; pops++;
    var r = h.getBoundingClientRect(), al = h.getAttribute("data-fest-h");
    var x = al === "c" ? (r.left + r.right) / 2 : al === "r" ? r.right - 60 : r.left + 60;
    fx.pop(x, Math.max(90, r.top - 6), preset.pop);
  }

  /* The festival's iconic objects in a row: under the hero and above the footer. */
  function drawShelves(preset) {
    if (!preset.shelf || document.querySelector(".fest-shelf")) return;
    var mk = function (where) {
      var d = deco("div", "fest-shelf fest-shelf-" + where);
      d.innerHTML = shelfHtml(preset.shelf);
      els.push(d);
      observe(d);
      return d;
    };
    var foot = document.querySelector("footer");
    if (foot && foot.parentNode) foot.parentNode.insertBefore(mk("foot"), foot);
    var hero = heroEl;
    if (hero && hero.parentNode && /^(block|flow-root)$/.test(getComputedStyle(hero.parentNode).display)) {
      hero.parentNode.insertBefore(mk("hero"), hero.nextSibling);
      refreshScroll();
    }
  }

  /* Scroll speed nudges the hanging decorations and stirs the particles. */
  function setupScrollFx() {
    var lastY = window.pageYOffset || 0, ticking = false, settle = 0;
    var strs = Array.prototype.slice.call(document.querySelectorAll(".fest-str"));
    var onS = function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        ticking = false;
        var y = window.pageYOffset || 0, dy = y - lastY;
        lastY = y;
        if (!dy) return;
        if (fx) fx.kick(dy);
        if (reduced || !strs.length) return;
        var k = Math.max(-9, Math.min(9, -dy * 0.18));
        strs.forEach(function (s) { s.style.transform = "rotate(" + k.toFixed(2) + "deg)"; });
        clearTimeout(settle);
        settle = setTimeout(function () { strs.forEach(function (s) { s.style.transform = ""; }); }, 140);
      });
    };
    addEventListener("scroll", onS, { passive: true });
    cleanups.push(function () { removeEventListener("scroll", onS); clearTimeout(settle); });
  }

  /* Strings of decorations hanging from under the header at both edges. */
  function drawHangers(preset, lvl, header) {
    if (!preset.hang || !header) return;
    // The strings start under the ribbon (behind the header) and fall past it, so
    // each one is lengthened by how far the header reaches below the ribbon.
    var top = (parseFloat(root.style.getPropertyValue("--fest-top")) || 0) + (parseFloat(root.style.getPropertyValue("--fest-rib-h")) || 0);
    var extra = Math.max(40, Math.min(140, Math.round(header.getBoundingClientRect().bottom - top)));
    ["l", "r"].forEach(function (side) {
      var box = deco("div", "fest-hang fest-hang-" + side);
      preset.hang.forEach(function (h, i) {
        var def = H[h[0]] || H.star;
        var len = h[1] + extra - 6, ih = def[0], w = 40;
        var svg = "<svg viewBox='-20 0 40 " + (len + ih) + "' width='" + w + "' height='" + (len + ih) + "'>" +
          "<path d='M0 0V" + len + "' stroke='rgba(90,70,40,.55)' stroke-width='.9'/>" +
          "<g transform='translate(0 " + len + ")'>" + def[1](h[2]) + "</g></svg>";
        // outer span: nudged by scroll speed; inner span: the slow idle sway
        var s = el("span", "fest-str fest-str-" + i);
        var sw = el("span", "fest-sw", svg);
        sw.style.animationDelay = (-(i * 1.3 + (side === "r" ? 0.7 : 0))) + "s";
        sw.style.animationDuration = (4.6 + i * 0.9) + "s";
        s.appendChild(sw);
        box.appendChild(s);
      });
      document.body.appendChild(box);
      els.push(box);
    });
    hangCheck();
  }

  /* A hanging decoration that would sit over words or a picture is taken down. Checked with
     the page at the top (the strings fade out once the visitor scrolls). */
  function hangCheck() {
    if (root.classList.contains("fest-rib-up")) return;
    Array.prototype.forEach.call(document.querySelectorAll(".fest-str"), function (s) {
      s.classList.remove("fest-str-off");
      var svg = s.querySelector("svg");
      if (!svg || getComputedStyle(s).display === "none" || getComputedStyle(s.parentNode).display === "none") return;
      var r = svg.getBoundingClientRect(), y0 = Math.max(r.top, r.bottom - 46);
      var pts = [[r.left + r.width / 2, (y0 + r.bottom) / 2], [r.left + 4, r.bottom - 6], [r.right - 4, r.bottom - 6], [r.left + r.width / 2, y0]];
      for (var i = 0; i < pts.length; i++) {
        if (busyAt(pts[i][0], pts[i][1])) { s.classList.add("fest-str-off"); return; }
      }
    });
  }
  function busyAt(x, y) {
    if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) return false;
    var list = document.elementsFromPoint ? document.elementsFromPoint(x, y) : [];
    for (var i = 0; i < list.length; i++) {
      var e = list[i];
      if (e === document.documentElement || e === document.body) continue;
      if (e.closest(".fest-hang, .fest-fx, .fest-rib, .fest-garland, .fest-corner, .fest-band, .fest-shelf, .fest-spacer, .fest-chip")) continue;
      if (e.closest("header")) return true;
      if (/^(IMG|VIDEO|CANVAS|PICTURE|IFRAME|BUTTON|INPUT|SELECT|TEXTAREA|A)$/.test(e.tagName)) return true;
      if (Array.prototype.some.call(e.childNodes, function (n) { return n.nodeType === 3 && n.textContent.trim(); })) return true;
      var bg = getComputedStyle(e).backgroundImage;
      if (bg && bg.indexOf("url(") >= 0) return true;
    }
    return false;
  }

  /* Header props: Christmas snow on the nav pill and a Santa hat on the logo. */
  function drawHeaderProps(preset, header) {
    if (!header || !preset.christmas) return;
    var nav = header.querySelector(".nav");
    if (nav) {
      if (getComputedStyle(nav).position === "static") addClass(nav, "fest-rel");
      var cap = deco("span", "fest-snowcap");
      nav.appendChild(cap);
      els.push(cap);
    }
    var logo = header.querySelector(".logo");
    if (logo) {
      if (getComputedStyle(logo).position === "static") addClass(logo, "fest-rel");
      var hat = deco("span", "fest-hat");
      hat.innerHTML = "<svg viewBox='0 0 40 34'><path d='M4 26C8 12 18 4 30 6c4 1 6 5 5 9-3-3-6-4-8-2 2 4 1 9-1 13z' fill='#D62828'/>" +
        "<circle cx='35' cy='17' r='4' fill='#fff'/><rect x='1' y='24' width='30' height='8' rx='4' fill='#fff'/><path d='M3 28h26' stroke='#e9ecef' stroke-width='1'/></svg>";
      logo.appendChild(hat);
      els.push(hat);
    }
  }

  /* Heading ornaments, section corners and bands. Safe to run more than once. */
  function decorate(preset, lvl) {
    var skip = "header, footer, nav, .mobile-menu, .search-ov, dialog, [role=dialog], .fest-rib, .modal, .drawer";
    var vw = innerWidth;

    // 1) main section headings: ornament behind, divider under
    var hs = Array.prototype.slice.call(document.querySelectorAll("h2"));
    var reads = [];
    hs.forEach(function (h) {
      if (h.hasAttribute("data-fest-h") || h.closest(skip)) return;
      var cs = getComputedStyle(h);
      var fs = parseFloat(cs.fontSize) || 0;
      if (fs < 22 || (cs.position !== "static" && cs.position !== "relative") || cs.display === "none" || cs.visibility === "hidden" || cs.backgroundClip === "text" || cs.webkitBackgroundClip === "text") return;
      var r = h.getBoundingClientRect();
      if (r.width < 60) return;
      var next = h.nextElementSibling;
      while (next && (next.offsetParent === null || getComputedStyle(next).position === "absolute")) next = next.nextElementSibling;
      var gap = next ? next.getBoundingClientRect().top - r.bottom : 99;
      // Where the words actually sit: a narrow heading centred by its parent reads as centred
      // whatever its own text-align says.
      var al = "l";
      try {
        var rg = document.createRange(); rg.selectNodeContents(h);
        var rs = rg.getClientRects(), L = Infinity, R = -Infinity;
        for (var i = 0; i < rs.length; i++) { if (rs[i].width > 1) { L = Math.min(L, rs[i].left); R = Math.max(R, rs[i].right); } }
        var pr = h.parentElement.getBoundingClientRect();
        if (cs.textAlign === "center" || (L - pr.left > 12 && Math.abs((L + R) / 2 - (pr.left + pr.right) / 2) < 8 && L - r.left < 4)) al = "c";
        else if (cs.textAlign === "right" || cs.textAlign === "end") al = "r";
        else if (L - r.left > 12 && Math.abs((L + R) / 2 - (r.left + r.right) / 2) < 8) al = "c";
      } catch (e) {}
      reads.push([h, al, gap]);
    });
    reads.forEach(function (x) {
      var h = x[0], al = x[1];
      h.setAttribute("data-fest-h", al);
      addClass(h, "fest-h"); observe(h);
      if (x[2] < 30) { h.style.setProperty("--fest-hpad", Math.min(30, Math.round(30 - Math.max(0, x[2]))) + "px"); addClass(h, "fest-h-pad"); }
      cleanups.push(function () { h.removeAttribute("data-fest-h"); h.style.removeProperty("--fest-hpad"); });
    });

    // 2) sections: corner motifs, and bands strung across the top
    var cfg = preset.corner || {};
    var secs = Array.prototype.slice.call(document.querySelectorAll("section, .hero, .hero-banner"));
    var picked = [];
    secs.forEach(function (s) {
      if (s.closest(skip) || s.hasAttribute("data-fest-s")) return;
      for (var i = 0; i < picked.length; i++) if (picked[i].contains(s)) return;
      var r = s.getBoundingClientRect();
      if (r.height < 260 || r.width < vw * 0.85) return;
      picked.push(s);
    });
    var size = vw < 768 ? 46 : vw < 1200 ? 70 : 92;
    var band = (lvl >= 2 && preset.band2) || (lvl >= 3 && preset.band3) || "";
    picked.forEach(function (s, i) {
      s.setAttribute("data-fest-s", "1");
      cleanups.push(function () { s.removeAttribute("data-fest-s"); });
      var hero = i === 0 && s.getBoundingClientRect().top + scrollY < 260;
      // the hero keeps its photo clear: it gets the row of festival objects underneath instead
      if (hero) { heroEl = s; return; }
      if (lvl < 3 && i % 2 === 0) return;     // festive: every other section; full: all
      // sections whose content is moved by scroll animations (Home's pinned panels, sliders)
      // would carry their content under a corner later on: leave those alone
      if (s.closest(".pin-spacer") || s.querySelector(".pin-spacer, .swiper-wrapper, [data-speed], [data-parallax], img[style*='transform']")) return;
      if (getComputedStyle(s).position === "static") addClass(s, "fest-rel");
      var content = contentIn(s);
      // try the preferred diagonal first, then the other two corners; a corner that would
      // touch any text, button, link or photo is simply not drawn
      var order = i % 2 ? ["tl", "br", "tr", "bl"] : ["tr", "bl", "tl", "br"], placed = 0;
      order.forEach(function (c) {
        if (placed >= 2) return;
        var name = cfg.alt && placed === 1 ? cfg.alt : cfg.m;
        var cut = cfg.cut && name === cfg.m;
        var sz = Math.round(size * (cut ? 1 : 0.9));
        var n = deco("span", "fest-corner fest-c-" + c + (cut ? " fest-cut" : ""));
        n.style.width = n.style.height = sz + "px";
        n.style.backgroundImage = motifUri(name);
        n.style.backgroundSize = cut ? (sz * 2) + "px " + (sz * 2) + "px" : "contain";
        s.appendChild(n);
        if (collides(n, content)) { s.removeChild(n); return; }
        els.push(n);
        placed++;
      });
      if (band) {
        var g = garlandCss(band);
        var b = deco("span", "fest-band");
        b.style.backgroundImage = g.image;
        b.style.backgroundSize = g.w + "px " + g.h + "px";
        b.style.height = g.h + "px";
        s.appendChild(b);
        if (collides(b, content)) s.removeChild(b);
        else { observe(b); els.push(b); }
      }
    });

    // Listing grids and galleries fill in after load: take back any decoration they now reach.
    Array.prototype.forEach.call(document.querySelectorAll(".fest-corner, .fest-band"), function (n) {
      var sec = n.parentNode;
      if (sec && collides(n, contentIn(sec))) sec.removeChild(n);
    });
  }

  // What must stay clear in a section: words, controls and pictures.
  function contentIn(scope) {
    return Array.prototype.filter.call(scope.querySelectorAll("img, video, picture, canvas, iframe, button, a, input, select, textarea, label, p, h1, h2, h3, h4, h5, h6, li, span, figure, svg"), function (e) {
      if (e.closest(".fest-shelf, .fest-corner, .fest-band, .fest-hang")) return false;
      if (e.tagName === "SPAN" && !Array.prototype.some.call(e.childNodes, function (x) { return x.nodeType === 3 && x.textContent.trim(); })) return false;
      if ((e.tagName === "A" || e.tagName === "LI") && !e.textContent.trim() && !e.querySelector("img")) return false;
      var r = e.getBoundingClientRect();
      return r.width > 3 && r.height > 3;
    });
  }
  function collides(n, list) {
    var a = n.getBoundingClientRect();
    for (var i = 0; i < list.length; i++) {
      var b = list[i].getBoundingClientRect();
      if (Math.min(a.right, b.right) - Math.max(a.left, b.left) > 2 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 2) {
        var cs = getComputedStyle(list[i]);
        if (cs.visibility !== "hidden" && cs.display !== "none") return true;
      }
    }
    return false;
  }

  // The festival's signature object, drawn large and alive, for the Home greeting badge.
  var ICONIC = { "diwali": "diya", "holi": "gulal:#E3367A", "christmas": "tree", "independence-day": "flag", "republic-day": "flag",
    "navratri": "garba", "ganesh-chaturthi": "modak", "raksha-bandhan": "rakhi", "janmashtami": "matki", "sankranti": "kite",
    "onam": "pookalam", "eid": "lantern", "new-year": "balloons" };
  function badgeArt() {
    var it = (ICONIC[root.getAttribute("data-festival")] || "star").split(":");
    return "<span class='fest-badge-ico'><svg viewBox='0 0 100 100' focusable='false'>" + (S[it[0]] || S.star)(it[1]) + "</svg></span>";
  }

  function drawHero(t, preset, greeting, sub) {
    var host = document.querySelector(".hero3-txt") || document.querySelector(".hero-v2 .wrap") || document.querySelector(".hero .wrap");
    if (!host || host.querySelector(".fest-badge")) return;
    var banner = t.banner && /^https?:\/\//i.test(t.banner) ? t.banner : "";
    var badge = el("div", "fest-badge");
    badge.setAttribute("translate", "yes");
    badge.innerHTML = (banner ? '<img class="fest-badge-img" src="' + esc(banner) + '" alt="">' : badgeArt()) +
      '<span class="fest-badge-txt">' + esc(greeting) + "</span>";
    host.insertBefore(badge, host.firstChild);
    els.push(badge);

    var hero = host.closest(".hero3, .hero-v2, .hero, section");
    if (!hero || !banner) return;
    var card = el("figure", "fest-card");
    card.setAttribute("translate", "yes");
    card.innerHTML = '<img src="' + esc(banner) + '" alt="" loading="lazy" decoding="async">' +
      "<figcaption><b>" + esc(greeting) + "</b>" + (sub ? "<span>" + esc(sub) + "</span>" : "") + "</figcaption>";
    var img = card.querySelector("img");
    img.onerror = function () { if (card.parentNode) card.parentNode.removeChild(card); };
    hero.appendChild(card);
    els.push(card);
  }

  function refreshScroll() {
    // Home's pinned sections measured the page before the spacer existed.
    try { if (window.ScrollTrigger && window.ScrollTrigger.refresh) window.ScrollTrigger.refresh(); } catch (e) {}
  }
  addEventListener("load", function () { if (current) refreshScroll(); });

  /* ── Particles: one canvas, capped, paused when hidden, never clickable. ─ */
  var fx = null;
  function stopFx() { if (fx) { fx.stop(); fx = null; } }

  function startFx(preset, lvl) {
    stopFx();
    var kind = preset.fx, colors = preset.fxColors, extras = preset.extras || [];
    if (reduced || !kind) return;
    var cv = deco("canvas", "fest-fx");
    document.body.appendChild(cv);
    els.push(cv);
    var ctx = cv.getContext("2d");
    if (!ctx) return;
    var W = 0, H = 0, dpr = 1, raf = 0, last = 0, running = true, parts = [], sparks = [], balloons = [];
    var small = Math.min(innerWidth, innerHeight || innerWidth) < 600;
    var BASE = { spark: 30, powder: 22, petal: 22, snow: 46, confetti: 30, twinkle: 26, kite: 6, feather: 9 }[kind] || 20;
    var N = Math.round(BASE * (small ? 0.5 : 1) * ({ 1: 0.6, 2: 1, 3: 1.4 })[lvl]);
    var MAXSPARK = small ? 160 : 320;
    var nextBurst = 0, nextBalloon = 0;

    function rnd(a, b) { return a + Math.random() * (b - a); }
    function pick(list) { list = list || colors; return list[(Math.random() * list.length) | 0]; }
    function size() {
      dpr = Math.min(2, window.devicePixelRatio || 1);
      W = innerWidth; H = innerHeight;
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    function make(initial) {
      var p = { x: rnd(0, W), y: initial ? rnd(0, H) : -20, c: pick(), r: rnd(0, Math.PI * 2), vr: rnd(-1.2, 1.2),
        ph: rnd(0, Math.PI * 2), a: 1 };
      switch (kind) {
        case "spark": p.y = initial ? rnd(0, H) : H + 10; p.s = rnd(1, 2.3); p.vy = -rnd(14, 34); p.vx = rnd(-6, 6); break;
        case "snow": p.s = rnd(1.4, 3.6); p.vy = rnd(18, 42); p.vx = rnd(-8, 8); break;
        case "powder": p.s = rnd(3, 9); p.vy = rnd(10, 22); p.vx = rnd(-10, 10); p.a = rnd(0.22, 0.42); break;
        case "petal": p.s = rnd(3.5, 6); p.vy = rnd(22, 46); p.vx = rnd(-12, 12); break;
        case "confetti": p.s = rnd(3, 5); p.vy = rnd(30, 60); p.vx = rnd(-14, 14); p.vr = rnd(-4, 4); break;
        case "twinkle": p.y = rnd(0, H); p.s = rnd(2, 4.5); p.vy = rnd(2, 6); p.vx = 0; break;
        case "kite": p.x = initial ? rnd(0, W) : -40; p.y = initial ? rnd(H * 0.1, H * 0.8) : rnd(H * 0.3, H * 0.9); p.s = rnd(10, 15); p.vy = -rnd(8, 16); p.vx = rnd(18, 34); break;
        case "feather": p.s = rnd(6, 9); p.vy = rnd(14, 26); p.vx = rnd(-6, 6); p.vr = rnd(-0.6, 0.6); break;
      }
      return p;
    }
    function star(x, y, s) {
      ctx.beginPath();
      ctx.moveTo(x, y - s); ctx.lineTo(x + s * 0.28, y - s * 0.28); ctx.lineTo(x + s, y);
      ctx.lineTo(x + s * 0.28, y + s * 0.28); ctx.lineTo(x, y + s); ctx.lineTo(x - s * 0.28, y + s * 0.28);
      ctx.lineTo(x - s, y); ctx.lineTo(x - s * 0.28, y - s * 0.28); ctx.closePath(); ctx.fill();
    }
    function drawP(p, tm) {
      ctx.globalAlpha = p.a;
      ctx.fillStyle = p.c;
      switch (kind) {
        case "spark":
          var f = 0.55 + 0.45 * Math.sin(tm * 6 + p.ph);
          ctx.globalAlpha = 0.18 * f; ctx.beginPath(); ctx.arc(p.x, p.y, p.s * 3.2, 0, 7); ctx.fill();
          ctx.globalAlpha = 0.9 * f; ctx.beginPath(); ctx.arc(p.x, p.y, p.s, 0, 7); ctx.fill();
          break;
        case "snow":
          ctx.globalAlpha = 0.9; ctx.beginPath(); ctx.arc(p.x, p.y, p.s, 0, 7); ctx.fill();
          ctx.globalAlpha = 0.35; ctx.strokeStyle = "#8aa2bd"; ctx.lineWidth = 0.6; ctx.stroke();
          break;
        case "powder":
          ctx.beginPath(); ctx.arc(p.x, p.y, p.s, 0, 7); ctx.fill();
          break;
        case "petal":
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.scale(1, 0.55 + 0.45 * Math.abs(Math.sin(tm * 1.6 + p.ph)));
          ctx.globalAlpha = 0.85; ctx.beginPath(); ctx.ellipse(0, 0, p.s, p.s * 0.55, 0, 0, 7); ctx.fill();
          if (p.c.toUpperCase() === "#FFFFFF") { ctx.strokeStyle = "rgba(120,120,120,.45)"; ctx.lineWidth = 0.6; ctx.stroke(); }
          ctx.restore();
          break;
        case "confetti":
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.scale(1, Math.cos(tm * 3 + p.ph));
          ctx.globalAlpha = 0.85; ctx.fillRect(-p.s / 2, -p.s, p.s, p.s * 2); ctx.restore();
          break;
        case "twinkle":
          ctx.globalAlpha = 0.25 + 0.6 * Math.max(0, Math.sin(tm * 1.4 + p.ph)); star(p.x, p.y, p.s);
          break;
        case "kite":
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(Math.sin(tm + p.ph) * 0.2 + 0.25);
          ctx.globalAlpha = 0.85; ctx.beginPath(); ctx.moveTo(0, -p.s); ctx.lineTo(p.s * 0.75, 0); ctx.lineTo(0, p.s * 1.15); ctx.lineTo(-p.s * 0.75, 0); ctx.closePath(); ctx.fill();
          ctx.globalAlpha = 0.5; ctx.fillStyle = "#fff"; ctx.beginPath(); ctx.moveTo(0, -p.s); ctx.lineTo(p.s * 0.75, 0); ctx.lineTo(-p.s * 0.75, 0); ctx.closePath(); ctx.fill();
          ctx.restore();
          // the string, trailing down to someone on a terrace below
          ctx.globalAlpha = 0.35; ctx.strokeStyle = "#555"; ctx.lineWidth = 0.7; ctx.beginPath();
          ctx.moveTo(p.x, p.y + p.s); ctx.quadraticCurveTo(p.x - 40, p.y + 90, p.x - 120, p.y + 260); ctx.stroke();
          break;
        case "feather":
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r);
          ctx.globalAlpha = 0.75; ctx.strokeStyle = "#2E9E6E"; ctx.lineWidth = 0.8; ctx.beginPath(); ctx.moveTo(0, p.s * 0.9); ctx.lineTo(0, p.s * 2.2); ctx.stroke();
          ctx.fillStyle = "#2E9E6E"; ctx.beginPath(); ctx.ellipse(0, 0, p.s * 0.62, p.s, 0, 0, 7); ctx.fill();
          ctx.fillStyle = "#1C7ED6"; ctx.beginPath(); ctx.ellipse(0, p.s * 0.08, p.s * 0.4, p.s * 0.64, 0, 0, 7); ctx.fill();
          ctx.fillStyle = "#0B2E59"; ctx.beginPath(); ctx.ellipse(0, p.s * 0.12, p.s * 0.2, p.s * 0.3, 0, 0, 7); ctx.fill();
          ctx.restore();
          break;
      }
    }

    // Fireworks: a burst every few seconds high on the screen.
    var FWC = kind === "spark" ? ["#FFD36E", "#FF8A3D", "#FFF1C1", "#F783AC", "#69DB7C"] : ["#D4AF37", "#F1D27A", "#ED3338", "#C0C6CC", "#74C0FC"];
    function burst(x, y, n, list, speed, life) {
      var c = pick(list);
      for (var i = 0; i < n && sparks.length < MAXSPARK; i++) {
        var a = Math.PI * 2 * i / n + rnd(-0.08, 0.08), v = rnd(speed * 0.55, speed);
        sparks.push({ x: x, y: y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, t: 0, life: rnd(life * 0.75, life), c: Math.random() < 0.7 ? c : pick(list), s: rnd(1.2, 2.2) });
      }
    }
    var hasFw = extras.indexOf("fireworks") >= 0 && lvl >= 2;
    var hasBal = extras.indexOf("balloons") >= 0 && lvl >= 2;
    var gap = lvl >= 3 ? [2.6, 5] : [5, 9];

    // One short burst, played when a section heading scrolls into view.
    function pop(x, y, type) {
      var k = small ? 0.6 : 1, i, n;
      if (type === "firework") { burst(x, y, Math.round(34 * k), FWC, small ? 100 : 140, 1.4); return; }
      var add = function (o) { if (sparks.length < MAXSPARK) sparks.push(o); };
      if (type === "confetti") {
        n = Math.round(30 * k);
        for (i = 0; i < n; i++) add({ sh: "rect", x: x + rnd(-20, 20), y: y, vx: rnd(-150, 150), vy: rnd(-260, -90), g: 300, t: 0, life: rnd(1.4, 2.1), c: pick(FWC), s: rnd(3, 5), rot: rnd(0, 6), vr: rnd(-9, 9) });
      } else if (type === "powder") {
        n = Math.round(18 * k);
        for (i = 0; i < n; i++) { var a = rnd(0, Math.PI * 2), v = rnd(30, 120); add({ sh: "puff", x: x, y: y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 20, g: 0, t: 0, life: rnd(1.1, 1.7), c: pick(), s: rnd(6, 14) }); }
      } else if (type === "stars") {
        n = Math.round(14 * k);
        for (i = 0; i < n; i++) { var b = rnd(0, Math.PI * 2), w = rnd(40, 100); add({ sh: "star", x: x, y: y, vx: Math.cos(b) * w, vy: Math.sin(b) * w, g: 20, t: 0, life: rnd(1, 1.5), c: pick(["#F5D98B", "#FCC419", "#FFF3C4"]), s: rnd(3, 5.5) }); }
      } else {
        n = Math.round(20 * k);
        for (i = 0; i < n; i++) add({ sh: "petal", x: x + rnd(-20, 20), y: y, vx: rnd(-110, 110), vy: rnd(-190, -60), g: 140, t: 0, life: rnd(1.5, 2.2), c: pick(), s: rnd(3.5, 6), rot: rnd(0, 6), vr: rnd(-4, 4) });
      }
    }

    // Holi: a soft puff of colour where the visitor taps or clicks.
    var onTap = null;
    if (extras.indexOf("clickburst") >= 0 && lvl >= 2) {
      onTap = function (e) { if (running) pop(e.clientX, e.clientY, "powder"); };
      document.addEventListener("pointerdown", onTap, { passive: true, capture: true });
    }

    // Scrolling stirs things: kites climb, colour drifts, snow thickens.
    function kick(dy) {
      dy = Math.max(-160, Math.min(160, dy));
      var a = Math.abs(dy);
      for (var i = 0; i < parts.length; i++) {
        var p = parts[i];
        if (kind === "kite") { p.y -= a * 0.35; p.x += a * 0.12; }
        else if (kind === "powder") { p.x += dy * 0.12; p.y -= dy * 0.18; }
        else if (kind === "spark") p.y -= dy * 0.15;
        else p.y -= dy * 0.08;
      }
      if (kind === "snow" && dy > 0) {
        for (var j = Math.min(5, Math.round(dy / 30)); j > 0 && parts.length < N * 2; j--) { var q = make(false); q.y = rnd(-20, H * 0.25); q.tmp = 1; parts.push(q); }
      }
    }

    function step(now) {
      if (!running) return;
      raf = requestAnimationFrame(step);
      var dt = last ? Math.min(0.05, (now - last) / 1000) : 0.016;
      last = now;
      var tm = now / 1000;
      ctx.clearRect(0, 0, W, H);
      for (var i = 0; i < parts.length; i++) {
        var p = parts[i];
        p.x += (p.vx + Math.sin(tm * 0.9 + p.ph) * 8) * dt;
        p.y += p.vy * dt;
        p.r += p.vr * dt;
        var gone = kind === "spark" ? p.y < -40 : kind === "kite" ? (p.y < -60 || p.x > W + 60) : p.y > H + 30;
        if (gone || p.x < -60 || p.x > W + 60) {
          if (p.tmp) { parts.splice(i, 1); i--; continue; }   // extra flakes from scrolling just melt away
          parts[i] = make(false);
        }
        drawP(parts[i], tm);
      }
      if (hasFw) {
        if (!nextBurst) nextBurst = tm + rnd(1, 2.5);
        if (tm > nextBurst) { burst(rnd(W * 0.12, W * 0.88), rnd(H * 0.12, H * 0.42), small ? 22 : 36, FWC, small ? 90 : 130, 1.5); nextBurst = tm + rnd(gap[0], gap[1]); }
      }
      if (hasBal) {
        if (!nextBalloon) nextBalloon = tm + rnd(1, 3);
        if (tm > nextBalloon && balloons.length < (small ? 2 : 4)) {
          balloons.push({ x: rnd(W * 0.05, W * 0.95), y: H + 40, vy: -rnd(36, 60), ph: rnd(0, 6), c: pick(["#D4AF37", "#ED3338", "#C0C6CC", "#F1D27A"]), s: rnd(9, 13) });
          nextBalloon = tm + rnd(gap[0], gap[1]);
        }
        for (var b = balloons.length - 1; b >= 0; b--) {
          var B = balloons[b];
          B.y += B.vy * dt; var bx = B.x + Math.sin(tm * 1.2 + B.ph) * 10;
          if (B.y < -60) { balloons.splice(b, 1); continue; }
          ctx.globalAlpha = 0.8; ctx.fillStyle = B.c; ctx.beginPath(); ctx.ellipse(bx, B.y, B.s * 0.82, B.s, 0, 0, 7); ctx.fill();
          ctx.globalAlpha = 0.45; ctx.strokeStyle = "#777"; ctx.lineWidth = 0.7; ctx.beginPath(); ctx.moveTo(bx, B.y + B.s);
          ctx.quadraticCurveTo(bx - 6, B.y + B.s * 2.5, bx + 2, B.y + B.s * 4); ctx.stroke();
        }
      }
      for (var k = sparks.length - 1; k >= 0; k--) {
        var s = sparks[k];
        s.t += dt;
        if (s.t > s.life) { sparks.splice(k, 1); continue; }
        var drag = s.sh === "puff" ? 0.95 : 0.985;
        s.vx *= drag; s.vy = s.vy * drag + (s.g == null ? 55 : s.g) * dt;
        s.x += s.vx * dt; s.y += s.vy * dt;
        if (s.vr) s.rot += s.vr * dt;
        var fade = 1 - s.t / s.life;
        ctx.fillStyle = s.c;
        if (s.sh === "rect") {
          ctx.save(); ctx.translate(s.x, s.y); ctx.rotate(s.rot); ctx.scale(1, Math.cos(s.t * 8 + s.rot));
          ctx.globalAlpha = 0.9 * fade; ctx.fillRect(-s.s / 2, -s.s, s.s, s.s * 2); ctx.restore();
        } else if (s.sh === "petal") {
          ctx.save(); ctx.translate(s.x, s.y); ctx.rotate(s.rot);
          ctx.globalAlpha = 0.85 * fade; ctx.beginPath(); ctx.ellipse(0, 0, s.s, s.s * 0.55, 0, 0, 7); ctx.fill();
          if (String(s.c).toUpperCase() === "#FFFFFF") { ctx.strokeStyle = "rgba(120,120,120,.45)"; ctx.lineWidth = 0.6; ctx.stroke(); }
          ctx.restore();
        } else if (s.sh === "puff") {
          ctx.globalAlpha = 0.4 * fade; ctx.beginPath(); ctx.arc(s.x, s.y, s.s * (1 + s.t * 0.6), 0, 7); ctx.fill();
        } else if (s.sh === "star") {
          ctx.globalAlpha = 0.95 * fade; star(s.x, s.y, s.s);
        } else {
          ctx.globalAlpha = 0.2 * fade; ctx.beginPath(); ctx.arc(s.x, s.y, s.s * 2.6, 0, 7); ctx.fill();
          ctx.globalAlpha = 0.95 * fade; ctx.beginPath(); ctx.arc(s.x, s.y, s.s, 0, 7); ctx.fill();
        }
      }
      ctx.globalAlpha = 1;
    }
    function play() { if (!running) { running = true; last = 0; raf = requestAnimationFrame(step); } }
    function pause() { running = false; cancelAnimationFrame(raf); }
    function onVis() { if (document.hidden) pause(); else play(); }
    var onSize = function () { size(); };

    size();
    for (var i = 0; i < N; i++) parts.push(make(true));
    raf = requestAnimationFrame(step);
    document.addEventListener("visibilitychange", onVis);
    addEventListener("resize", onSize, { passive: true });

    fx = {
      pop: function (x, y, type) { if (running) pop(x, y, type); },
      kick: function (dy) { if (running) kick(dy); },
      stop: function () {
        pause();
        document.removeEventListener("visibilitychange", onVis);
        removeEventListener("resize", onSize);
        if (onTap) document.removeEventListener("pointerdown", onTap, { capture: true });
        if (cv.parentNode) cv.parentNode.removeChild(cv);
      }
    };
    cleanups.push(stopFx);
  }

  /* ── Go ────────────────────────────────────────────────────────────────── */
  function fromFeed(data) {
    return data && typeof data === "object" && data.theme && typeof data.theme === "object" ? data.theme : null;
  }

  function start() {
    if (preview) {
      // Paint the preview at once from what we know, then ask the dashboard for its words.
      apply(choose(preview.t || fallbackFor(preview.slug)));
      fetch(API + "?preview=" + encodeURIComponent(preview.slug), { mode: "cors", credentials: "omit", cache: "no-store" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (data) {
          var t = fromFeed(data);
          if (!t) return;
          preview.t = t;
          put("sessionStorage", PKEY, JSON.stringify(preview));
          apply(choose(t));
        })
        .catch(function () {});
      return;
    }

    var cached = null;
    try { cached = JSON.parse(get("localStorage", KEY) || "null"); } catch (e) { cached = null; }
    if (cached && cached.at && Date.now() - cached.at < MAX_STALE) apply(choose(cached.t));

    fetch(API, { mode: "cors", credentials: "omit" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        if (!data || typeof data !== "object" || !("theme" in data)) throw new Error("shape");
        var t = fromFeed(data);
        put("localStorage", KEY, JSON.stringify({ t: t, at: Date.now() }));
        apply(choose(t));
      })
      .catch(function () { /* dashboard down: keep whatever is showing (cached or the normal site) */ });
  }

  if (document.body) start();
  else document.addEventListener("DOMContentLoaded", start);
})();
