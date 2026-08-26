import io, glob, os

BLOCK = u"""
/* ==========================================================================
   HEADING SIZE — every h1 and h2 on the site renders at 37px
   --------------------------------------------------------------------------
   Appended last so it wins over the per-section clamp() scales without those
   having to be hunted down one by one. Phones get a smaller step, since a
   fixed size in a 360px viewport overflows on any multi-word heading.
   ========================================================================== */
h1, h2,
.v3 h1, .v3 h2,
.v3 .v-head, .v3 .hero3-title,
.sec-head h2, .hero h1, main h2 {
  font-size: 37px !important;
  line-height: 1.15;
}
@media (max-width: 900px) {
  h1, h2,
  .v3 h1, .v3 h2,
  .v3 .v-head, .v3 .hero3-title,
  .sec-head h2, .hero h1, main h2 {
    font-size: clamp(26px, 6.4vw, 34px) !important;
  }
}
/* A forced size can outgrow a narrow column; a flex child defaults to
   min-width:auto and would widen its track rather than wrap. */
h1, h2 { overflow-wrap: break-word; }
.v3 .map3-right, .v3 .map3-container, .v3 .brand3-left, .v3 .split3 .left-txt { min-width: 0; }
"""

MARK = "HEADING SIZE \u2014 every h1 and h2"
done = skipped = 0
for p in sorted(glob.glob("*.html")):
    s = io.open(p, encoding="utf-8").read()
    if MARK in s:
        skipped += 1
        continue
    i = s.rfind("</style>")
    if i < 0:
        print("  no <style> in", p)
        skipped += 1
        continue
    io.open(p, "w", encoding="utf-8").write(s[:i] + BLOCK + s[i:])
    done += 1
print("%d pages updated, %d skipped" % (done, skipped))
