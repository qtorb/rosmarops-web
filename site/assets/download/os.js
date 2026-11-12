/* RosmarOps home: the download rows follow the visitor's system (GTM-129, 10-11; GTM-137, 12-11).
   Each download row (.dlrow) has the Microsoft Store badge (.store), which is the Windows download (Albert, 12-11: no
   Windows button), and a main button (.osmain) that is hidden as served. Under it, the line of other systems (.os-o
   items: Windows, to the Store with its counter; the Mac page; the Linux page).
   Without JavaScript, or on an unknown system, a phone or a tablet, nothing changes: the HTML as served (the Store
   badge, the three systems in the line) is the default and what search engines see. On Windows the line leaves out
   Windows. On a Mac (no touch screen) the main button appears and goes to the Mac page, the line leaves out Mac and
   the Store badge and its line are hidden; on Linux (not Android) the same with Linux. Reads only what the browser
   already says about its platform; stores and sends nothing. */
(function () {
  'use strict';
  var LABELS = {
    mac: { es: 'Descargar para Mac', en: 'Download for Mac', ca: 'Descarrega per a Mac' },
    linux: { es: 'Descargar para Linux', en: 'Download for Linux', ca: 'Descarrega per a Linux' }
  };

  function detect(nav) {
    var ua = String(nav.userAgent || '');
    var p = nav.userAgentData && nav.userAgentData.platform
      ? String(nav.userAgentData.platform)
      : String(nav.platform || '') + ' ' + ua;
    var touch = (nav.maxTouchPoints || 0) > 0;
    if (/mac/i.test(p) && !touch) return 'mac';
    if (/linux/i.test(p) && !/android/i.test(p + ' ' + ua)) return 'linux';
    if (/\bwin(dows|32|64)\b/i.test(p) && !/windows phone/i.test(ua)) return 'windows';
    return '';
  }

  function apply(doc, os) {
    if (os !== 'mac' && os !== 'linux' && os !== 'windows') return 0;
    var l2 = (doc.documentElement.lang || 'en').slice(0, 2).toLowerCase();
    var lang = (l2 === 'es' || l2 === 'ca') ? l2 : 'en';
    // The line of other systems: the visitor's own system is not repeated.
    var items = doc.querySelectorAll('.os-o');
    var pages = {};
    for (var i = 0; i < items.length; i++) {
      var key = items[i].getAttribute('data-os');
      var a = items[i].querySelector('a');
      if (a && !pages[key]) pages[key] = a.getAttribute('href');
      if (key === os) items[i].hidden = true;
    }
    if (os === 'windows') return items.length;
    // Mac or Linux: the main button appears and goes to that system's page.
    var rows = doc.querySelectorAll('.dlrow');
    var done = 0;
    for (var j = 0; j < rows.length; j++) {
      var main = rows[j].querySelector('.osmain');
      if (!main || !pages[os]) continue;
      main.setAttribute('href', pages[os]);
      main.textContent = LABELS[os][lang];
      main.hidden = false;
      done++;
    }
    // The Microsoft Store badge and its line are for Windows only (GTM-135b).
    var stores = doc.querySelectorAll('.store');
    for (var k = 0; k < stores.length; k++) stores[k].hidden = true;
    return done;
  }

  if (typeof module !== 'undefined' && module.exports) { module.exports = { detect: detect, apply: apply }; return; }
  try { apply(document, detect(navigator)); } catch (e) { /* keep the HTML as served */ }
})();
