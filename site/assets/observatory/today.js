// «Today in the Observatory» (GTM-88): the rosmarops-daily mu-plugin renders the block from the latest validated
// daily file (texts escaped in PHP); this only inserts it, so the static page needs no deploy to stay current.
// If the request fails, the section stays hidden.
(function () {
  var s = document.getElementById('today');
  if (!s || !window.fetch) return;
  fetch(s.getAttribute('data-src'), { credentials: 'omit' })
    .then(function (r) { if (!r.ok) throw new Error(String(r.status)); return r.text(); })
    .then(function (h) {
      if (!h) return;
      s.querySelector('.today-all').insertAdjacentHTML('beforebegin', h);
      s.hidden = false;
    })
    .catch(function () {});
})();
