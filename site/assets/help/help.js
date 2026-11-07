// AP-25 «i» help (signed by Albert 07-11 12:48): vigil docs/research/2026-11-07-ap-25-ayuda-i-y-glosario.md §2.
// Without JavaScript each «i» is a plain link to its glossary entry. With it, the «i» becomes a button
// that opens the definition right below its paragraph or list item. Definitions come from
// /assets/help/glossary.json, generated from tools/glossary/terms.json (the one source).
(function () {
  'use strict';
  var MORE = { en: 'More in the glossary', es: 'Más en el glosario', ca: 'Més al glossari' };
  var lang = (document.documentElement.lang || 'en').slice(0, 2);
  if (!MORE[lang]) lang = 'en';
  var data = null, loading = null, seq = 0;

  function load() {
    if (data) return Promise.resolve(data);
    if (!loading) loading = fetch('/assets/help/glossary.json', { credentials: 'same-origin' })
      .then(function (r) { if (!r.ok) throw new Error('glossary ' + r.status); return r.json(); })
      .then(function (j) { data = j; return j; });
    return loading;
  }
  function blockOf(el) { return el.closest('li, p, dd, td') || el.parentNode; }

  function close(btn, focus) {
    var p = document.getElementById(btn.getAttribute('aria-controls'));
    if (p) p.remove();
    btn.setAttribute('aria-expanded', 'false');
    if (focus) btn.focus();
  }

  function open(btn) {
    var id = btn.dataset.gi, href = btn.dataset.href, block = blockOf(btn);
    document.querySelectorAll('.gi[aria-expanded="true"]').forEach(function (b) {
      if (b !== btn && blockOf(b) === block) close(b, false);
    });
    load().then(function (j) {
      var t = j[lang] && j[lang][id];
      if (!t) { window.location.href = href; return; }
      var panel = document.createElement('div');
      panel.className = 'gi-panel gi-enter';
      panel.id = btn.getAttribute('aria-controls');
      var p = document.createElement('p'), b = document.createElement('b');
      b.textContent = t[0];
      p.appendChild(b);
      p.appendChild(document.createTextNode(' ' + t[1]));
      var a = document.createElement('a');
      a.href = href;
      a.textContent = MORE[lang];
      panel.appendChild(p);
      panel.appendChild(a);
      if (block.tagName === 'LI' || block.tagName === 'DD' || block.tagName === 'TD') {
        block.appendChild(panel);
      } else {
        block.parentNode.insertBefore(panel, block.nextSibling);
        var gap = parseFloat(getComputedStyle(block.parentNode).rowGap) || 0;
        if (gap) panel.style.marginTop = (8 - gap) + 'px';
      }
      btn.setAttribute('aria-expanded', 'true');
      requestAnimationFrame(function () { panel.classList.remove('gi-enter'); });
    }).catch(function () { window.location.href = href; });
  }

  function upgrade(a) {
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'gi';
    btn.dataset.gi = a.dataset.gi;
    btn.dataset.href = a.getAttribute('href');
    btn.setAttribute('aria-label', a.getAttribute('aria-label'));
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-controls', 'gi-' + a.dataset.gi + '-' + (++seq));
    btn.innerHTML = '<span aria-hidden="true">i</span>';
    btn.addEventListener('click', function () {
      if (btn.getAttribute('aria-expanded') === 'true') close(btn, false); else open(btn);
    });
    a.replaceWith(btn);
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var openBtn = document.activeElement && document.activeElement.closest &&
      (document.activeElement.closest('.gi-panel') ? document.querySelector('.gi[aria-controls="' + document.activeElement.closest('.gi-panel').id + '"]') : null);
    var btns = openBtn ? [openBtn] : Array.prototype.slice.call(document.querySelectorAll('.gi[aria-expanded="true"]'));
    if (!btns.length) return;
    var focusBtn = (document.activeElement && document.activeElement.classList && document.activeElement.classList.contains('gi')) ? document.activeElement : btns[btns.length - 1];
    btns.forEach(function (b) { close(b, false); });
    focusBtn.focus();
  });

  function init() { document.querySelectorAll('a.gi[data-gi]').forEach(upgrade); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
