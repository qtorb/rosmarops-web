/* RosmarOps visit counter (GTM-111). Sends this page's path and the referrer's domain, once, when the page is
   actually seen, to /wp-json/rosmarops/v1/visits on this same site. Nothing else: no cookie, no storage, no
   identifier. The server keeps only a count per day, page, language and kind of referrer.
   On since the privacy policy texts were signed (Albert, 07-11): ON must match ROSMAROPS_VISITS_ON in
   wp/mu-plugins/rosmarops-downloads.php.
   GTM-126: the team's own browsers are not counted. A page opened with ?rosmarops_internal=1, or a browser marked
   by consent.js (the key rosmarops_internal in localStorage, read only), sends nothing; ?rosmarops_internal=0 counts. */
(function () {
  var ON = true;
  if (!ON || !window.fetch || window.rosmaropsVisit) return;
  var mark = null;
  try { mark = new URLSearchParams(location.search).get('rosmarops_internal'); } catch (e) { mark = null; }
  if (mark === '1') return;
  if (mark !== '0') {
    try { if (window.localStorage.getItem('rosmarops_internal') === '1') return; } catch (e) { /* no storage: count */ }
  }
  window.rosmaropsVisit = true; // one count per page view, even if the script is included twice
  var sent = false;
  function send() {
    if (sent || document.visibilityState !== 'visible') return;
    sent = true;
    var host = '';
    try { if (document.referrer) host = new URL(document.referrer).hostname; } catch (e) { host = ''; }
    var path = location.pathname;
    var m = /^\/(es|ca)\//.exec(path);
    var base = m ? '/' + m[1] : '';
    fetch(base + '/wp-json/rosmarops/v1/visits', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ p: path, r: host }),
      credentials: 'same-origin',
      keepalive: true
    }).catch(function () {});
  }
  if (document.visibilityState === 'visible') send();
  else document.addEventListener('visibilitychange', send);
})();
