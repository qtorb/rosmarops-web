/* RosmarOps home: the download buttons follow the visitor's system (GTM-129, signed by Albert 10-11).
   Without JavaScript, on an unknown system, on Windows, on a phone or on a tablet, nothing changes: the HTML as
   served (Windows first) is the default and what search engines see. On a Mac (no touch screen) the Mac page goes
   first; on Linux (not Android) the Linux page goes first; Windows stays second with its own link and counter
   (from, os). Reads only what the browser already says about its platform; stores and sends nothing. */
(function () {
  'use strict';
  var LABELS = {
    mac: { es: 'Descargar para Mac (vista previa)', en: 'Download for Mac (preview)', ca: 'Descarrega per a Mac (vista prèvia)' },
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
    return '';
  }

  function find(block, test) {
    var links = block.getElementsByTagName('a');
    for (var i = 0; i < links.length; i++) if (test(links[i].getAttribute('href') || '')) return links[i];
    return null;
  }

  function apply(doc, os) {
    if (os !== 'mac' && os !== 'linux') return 0;
    var l2 = (doc.documentElement.lang || 'en').slice(0, 2).toLowerCase();
    var lang = (l2 === 'es' || l2 === 'ca') ? l2 : 'en';
    var blocks = doc.querySelectorAll('.dl');
    var done = 0;
    for (var i = 0; i < blocks.length; i++) {
      var b = blocks[i];
      var win = find(b, function (h) { return /[?&]os=windows(&|$)/.test(h); });
      var mac = find(b, function (h) { return /\/macos\/$/.test(h); });
      var lin = find(b, function (h) { return /\/linux\/$/.test(h); });
      if (!win || !mac || !lin) continue;
      var first = os === 'mac' ? mac : lin;
      var third = os === 'mac' ? lin : mac;
      first.className = 'hbtn primary';
      first.textContent = LABELS[os][lang];
      win.className = 'hbtn';
      win.textContent = 'Windows';
      b.appendChild(first);
      b.appendChild(win);
      b.appendChild(third);
      done++;
    }
    // The note about the Windows warning only concerns Windows.
    var notes = doc.querySelectorAll('.dl-note');
    for (var j = 0; j < notes.length; j++) {
      if (/^\s*Windows\b/.test(notes[j].textContent || '')) notes[j].hidden = true;
    }
    return done;
  }

  if (typeof module !== 'undefined' && module.exports) { module.exports = { detect: detect, apply: apply }; return; }
  try { apply(document, detect(navigator)); } catch (e) { /* keep the HTML as served */ }
})();
