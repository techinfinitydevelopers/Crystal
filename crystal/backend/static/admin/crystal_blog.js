/* A writing surface for a blog post.
 *
 * Article.html drops this field straight into the page with innerHTML, so the
 * value really is HTML -- and a bare textarea meant writing <h2> and <p> by
 * hand. This puts a toolbar over it that wraps the selection, and a preview
 * underneath showing exactly what the article page will render.
 *
 * Deliberately not a third-party editor. Quill and Trix both inline a pasted
 * or dropped image as a base64 data URL, which would push a whole photograph
 * into this text column and through every API response that carries it. This
 * writes the same small set of tags the article's own stylesheet knows about.
 * The Image button uploads straight to blog/admin.py's own small endpoint
 * (data-upload-url on the textarea) rather than the Media library picker:
 * that picker can be switched off per admin (access.rules, base_site.html),
 * and a post's own inline photos should never depend on that switch.
 */
(function () {
  'use strict';

  var TOOLS = [
    { label: 'H2', title: 'Section heading', wrap: ['<h2>', '</h2>'], block: true },
    { label: 'H3', title: 'Sub-heading', wrap: ['<h3>', '</h3>'], block: true },
    { label: 'Paragraph', title: 'Paragraph', wrap: ['<p>', '</p>'], block: true },
    { label: 'B', title: 'Bold', wrap: ['<strong>', '</strong>'], cls: 'is-bold' },
    { label: 'I', title: 'Italic', wrap: ['<em>', '</em>'], cls: 'is-italic' },
    { label: 'List', title: 'Bulleted list', list: true },
    { label: 'Quote', title: 'Pull quote', wrap: ['<blockquote>', '</blockquote>'], block: true },
    { label: 'Link', title: 'Link', link: true },
    { label: 'Image', title: 'Insert a picture here', image: true },
  ];

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  function surround(ta, before, after, blockLevel) {
    var s = ta.selectionStart, e = ta.selectionEnd;
    var sel = ta.value.slice(s, e);
    var lead = blockLevel && s > 0 && ta.value[s - 1] !== '\n' ? '\n' : '';
    var tail = blockLevel ? '\n' : '';
    var text = lead + before + sel + after + tail;
    ta.setRangeText(text, s, e, 'end');
    // Empty selection: park the caret between the tags so typing lands inside.
    if (!sel) {
      var caret = s + lead.length + before.length;
      ta.setSelectionRange(caret, caret);
    }
    ta.focus();
    ta.dispatchEvent(new Event('input', { bubbles: true }));
  }

  function csrf() {
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  /** Pick a file, upload it, drop an <img> at the caret once it is stored. */
  function insertImage(ta) {
    var url = ta.getAttribute('data-upload-url');
    if (!url) {
      window.alert('The picture uploader is not wired up on this page.');
      return;
    }
    var input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      if (!file) return;
      var caret = ta.selectionStart;
      var marker = '\n<p data-bl-uploading>Uploading ' + file.name.replace(/[<>]/g, '') + '…</p>\n';
      ta.setRangeText(marker, caret, ta.selectionEnd, 'end');
      ta.dispatchEvent(new Event('input', { bubbles: true }));

      var fd = new FormData();
      fd.append('file', file);
      fetch(url, {
        method: 'POST', body: fd, credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrf(), 'X-Requested-With': 'XMLHttpRequest' }
      })
        .then(function (r) { return r.json().then(function (data) { return { ok: r.ok, data: data }; }); })
        .then(function (res) {
          var markerPos = ta.value.indexOf(marker);
          var replacement = res.ok
            ? '\n<img src="' + res.data.url + '" alt="">\n'
            : '';
          if (markerPos === -1) {
            // The text moved under them while it uploaded; append instead of guessing.
            ta.value += replacement;
          } else {
            ta.setRangeText(replacement, markerPos, markerPos + marker.length, 'end');
          }
          ta.dispatchEvent(new Event('input', { bubbles: true }));
          if (!res.ok) window.alert((res.data && res.data.error) || 'Could not upload that picture.');
        })
        .catch(function () {
          var markerPos = ta.value.indexOf(marker);
          if (markerPos !== -1) ta.setRangeText('', markerPos, markerPos + marker.length, 'end');
          ta.dispatchEvent(new Event('input', { bubbles: true }));
          window.alert('Could not upload that picture — check the connection and try again.');
        });
    });
    input.click();
  }

  function apply(tool, ta) {
    if (tool.list) {
      var s = ta.selectionStart, e = ta.selectionEnd;
      var sel = ta.value.slice(s, e);
      var lines = (sel || 'First point\nSecond point').split('\n').filter(function (l) {
        return l.trim();
      });
      var html = '<ul>\n' + lines.map(function (l) {
        return '  <li>' + l.trim() + '</li>';
      }).join('\n') + '\n</ul>\n';
      surround(ta, html, '', true);
      return;
    }
    if (tool.link) {
      var href = window.prompt('Link to where?', 'https://');
      if (!href) return;
      surround(ta, '<a href="' + href + '">', '</a>');
      return;
    }
    if (tool.image) {
      insertImage(ta);
      return;
    }
    surround(ta, tool.wrap[0], tool.wrap[1], tool.block);
  }

  ready(function () {
    var ta = document.querySelector('textarea.crystal-blog-body');
    if (!ta) return;

    var bar = document.createElement('div');
    bar.className = 'bl-toolbar';
    TOOLS.forEach(function (tool) {
      var b = document.createElement('button');
      b.type = 'button';                 // or it submits the change form
      b.className = 'bl-tool' + (tool.cls ? ' ' + tool.cls : '');
      b.textContent = tool.label;
      b.title = tool.title;
      b.addEventListener('click', function () { apply(tool, ta); });
      bar.appendChild(b);
    });
    ta.parentNode.insertBefore(bar, ta);

    var wrap = document.createElement('div');
    wrap.className = 'bl-preview-wrap';
    wrap.innerHTML = '<div class="bl-preview-head">How the article will read</div>' +
                     '<div class="bl-preview-body"></div>';

    // Side by side on a wide screen. Stacked, an 18-row textarea pushes the
    // preview below the fold, and a preview you have to scroll to find is not
    // doing its job.
    var split = document.createElement('div');
    split.className = 'bl-split';
    ta.parentNode.insertBefore(split, ta);
    split.appendChild(ta);
    split.appendChild(wrap);
    var body = wrap.querySelector('.bl-preview-body');

    function sync() {
      // Same assignment the article page makes, so what shows here is what it
      // will show there.
      body.innerHTML = ta.value ||
        '<span class="bl-muted">Nothing written yet.</span>';
    }
    ta.addEventListener('input', sync);
    sync();
  });
})();
