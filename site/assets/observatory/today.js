// Live parts of the Observatory pages, rendered by the rosmarops-daily mu-plugin from data it validated
// (texts escaped in PHP), so the static pages need no deploy to stay current.
// - «Today in the Observatory» (GTM-88): hidden until the block arrives.
// - Security changes list, «Latest security change» column and agent histories (GTM-89): they replace what the
//   static HTML brings; if a request fails, the static HTML stays as it is.
(function () {
  if (!window.fetch) return;
  function get(url) {
    return fetch(url, { credentials: 'omit' }).then(function (r) {
      if (!r.ok) throw new Error(String(r.status));
      return r.text();
    });
  }
  var s = document.getElementById('today');
  if (s) {
    get(s.getAttribute('data-src')).then(function (h) {
      if (!h) return;
      s.querySelector('.today-all').insertAdjacentHTML('beforebegin', h);
      s.hidden = false;
    }).catch(function () {});
  }
  Array.prototype.forEach.call(document.querySelectorAll('[data-live]'), function (sec) {
    get(sec.getAttribute('data-live')).then(function (h) {
      var target = sec.querySelector('[data-live-target]');
      if (h && target) target.outerHTML = h;
    }).catch(function () {});
  });
  var col = document.querySelector('[data-last-src]');
  if (col) {
    get(col.getAttribute('data-last-src')).then(function (h) {
      if (!h) return;
      var tpl = document.createElement('template');
      tpl.innerHTML = h;
      Array.prototype.forEach.call(tpl.content.querySelectorAll('span[data-agent]'), function (sp) {
        Array.prototype.forEach.call(document.querySelectorAll('td[data-last]'), function (td) {
          if (td.getAttribute('data-last') === sp.getAttribute('data-agent')) td.innerHTML = sp.innerHTML;
        });
      });
    }).catch(function () {});
  }
})();
