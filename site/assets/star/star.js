// GTM-206: after a click on a download button, show the card that asks for a star on GitHub, under the block that
// was clicked. Once per visit to the page. Nothing is stored in the browser and nothing is sent.
(function () {
  'use strict';
  var card = document.getElementById('star-card');
  if (!card) return;
  var shown = false;
  var route = /^\/(download|es\/descargar|ca\/descarregar)\/?$/;

  document.addEventListener('click', function (e) {
    if (shown) return;
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a || !route.test(a.pathname)) return;
    var block = a.closest('[data-star-block]');
    if (!block) return;
    shown = true;
    if (block.getAttribute('data-star-block') === 'inside') block.appendChild(card);
    else block.parentNode.insertBefore(card, block.nextSibling);
    card.hidden = false;
  });
})();
