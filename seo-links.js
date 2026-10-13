/* Where a product's, or a blog post's, own page is.
 *
 * Every product has an address of its own -- /products/crystal-peeler -- and so
 * does every blog post -- /blog/why-triply. Every place on the site that links to
 * one calls productHref(id) or blogHref(slug) instead of building
 * "Product.html?p=<id>" or "Article.html?id=<slug>" by hand. That is what lets an
 * address be changed in the dashboard without a link anywhere being edited.
 *
 * The maps are in product-urls.js, which the dashboard writes. It is loaded
 * before this file; if it is missing or empty, links fall back to the old
 * query-string forms, which Product.html and Article.html forward on to the real
 * address themselves. So a page that cannot see the maps still goes somewhere
 * correct.
 */
(function () {
  "use strict";
  var products = window.PRODUCT_URLS = window.PRODUCT_URLS || {};
  var posts = window.BLOG_URLS = window.BLOG_URLS || {};

  window.productHref = function (id) {
    id = String(id == null ? "" : id);
    var slug = products[id] || products[id.toLowerCase()];
    return slug ? "/products/" + slug : "Product.html?p=" + encodeURIComponent(id);
  };

  window.blogHref = function (slug) {
    slug = String(slug == null ? "" : slug);
    return posts[slug] ? "/blog/" + slug : "Article.html?id=" + encodeURIComponent(slug);
  };
})();
