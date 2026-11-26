// GTM-206, GTM-227: the course lessons. Lesson 1: the piece «Who decides?»; lesson 2: the piece «Break the chain»;
// both: the game and the test. Texts come from the page itself (<script type="application/json" id="cs-data">),
// built from observatory/data/course/the-inspector.json and the-chain.json. State lives only in this page: nothing
// is read from or written to the address, the browser's storage or cookies, and nothing is sent anywhere.
(function () {
  'use strict';
  var node = document.getElementById('cs-data');
  if (!node) return;
  var T = JSON.parse(node.textContent);

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  // **x** is bold and `x` is code, as in the signed texts.
  function fmt(s) {
    return esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/`(.+?)`/g, '<code>$1</code>');
  }
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  // ---- Lesson 1, «Who decides?»: three modes, four actions ----
  function modes() {
    var M = T.modes, mode = 'manual';
    var btns = Array.prototype.slice.call(document.querySelectorAll('#cs-modes .cs-pill'));
    function render() {
      btns.forEach(function (b) {
        var on = b.getAttribute('data-m') === mode;
        b.setAttribute('aria-checked', String(on));
        b.tabIndex = on ? 0 : -1;
      });
      $('cs-rows').innerHTML = M.actions.map(function (a, k) {
        var s = M.states[mode][k];
        return '<div class="cs-row"><div class="cs-act"><span class="cs-num">' + (k + 1) + '</span><span>' + esc(a) +
          '</span></div><span class="cs-mtag ' + s + '">' + esc(M.tags[s]) + '</span></div>';
      }).join('');
      var msg = $('cs-mmsg');
      msg.className = 'cs-msg ' + mode;
      msg.innerHTML = fmt(M.msg[mode]);
    }
    btns.forEach(function (b, i) {
      b.addEventListener('click', function () { mode = b.getAttribute('data-m'); render(); });
      b.addEventListener('keydown', function (e) {
        var d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
        if (!d) return;
        e.preventDefault();
        var n = btns[(i + d + btns.length) % btns.length];
        mode = n.getAttribute('data-m');
        render();
        n.focus();
      });
    });
    render();
  }

  // ---- Lesson 2, «Break the chain» ----
  function chain() {
  var P = T.piece, A = 'allow', B = false, K = 0;
  var tags = Array.prototype.slice.call(document.querySelectorAll('.cs-tag'));
  var pills = Array.prototype.slice.call(document.querySelectorAll('#cs-a .cs-pill'));
  var sw = $('cs-b');

  function state() { return A === 'allow' ? 'whole' : (B ? 'part' : 'cut'); }

  function render() {
    var st = state();
    var msg = $('cs-msg');
    msg.className = 'cs-msg ' + st;
    msg.innerHTML = fmt(P.msg[A + (B ? '1' : '0')]) + (st === 'part' ? '<small>' + esc(P.sandbox) + '</small>' : '');
    $('cs-a23').className = 'cs-arr' + (st === 'cut' ? ' cut' : st === 'part' ? ' part' : '');
    $('cs-a23t').textContent = st === 'cut' ? P.arrows.broken : st === 'part' ? P.arrows.partly : P.arrows.reaches;
    tags[2].classList.toggle('off', st === 'cut');
    tags[3].classList.toggle('off', st === 'cut');
    $('cs-s2').textContent = P.small2[A] + (st === 'part' ? P.partly_suffix : '');
    $('cs-bt').textContent = B ? P.b.yes : P.b.no;
    sw.setAttribute('aria-checked', String(B));
    pills.forEach(function (p) {
      var on = p.getAttribute('data-a') === A;
      p.setAttribute('aria-checked', String(on));
      p.tabIndex = on ? 0 : -1;
    });
    tags.forEach(function (t, i) { t.setAttribute('aria-pressed', String(i === K)); });
    var link = P.links[K];
    $('cs-det').innerHTML = '<span class="cs-l">' + esc(link[0]) + '</span><h3>' + esc(link[1]) + '</h3><dl>' +
      P.detail[K].map(function (p) { return '<dt>' + esc(p[0]) + '</dt><dd>' + fmt(p[1]) + '</dd>'; }).join('') + '</dl>';
  }

  tags.forEach(function (t, i) { t.addEventListener('click', function () { K = i; render(); }); });
  pills.forEach(function (p, i) {
    p.addEventListener('click', function () { A = p.getAttribute('data-a'); render(); });
    p.addEventListener('keydown', function (e) {
      var d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
      if (!d) return;
      e.preventDefault();
      var n = pills[(i + d + pills.length) % pills.length];
      A = n.getAttribute('data-a');
      render();
      n.focus();
    });
  });
  sw.addEventListener('click', function () { B = !B; render(); });
  render();
  }
  if (T.modes) modes();
  if (T.piece) chain();

  // ---- Game and test: one card at a time ----
  function button(text, cls, onClick) {
    var b = el('button', 'cs-btn' + (cls ? ' ' + cls : ''));
    b.type = 'button';
    b.textContent = text;
    b.addEventListener('click', onClick);
    return b;
  }

  function game() {
    var G = T.game, box = $('cs-game'), i = 0, score = 0;
    function card() {
      var it = G.items[i], picked = [];
      box.innerHTML = '';
      var c = el('div', 'cs-c');
      c.appendChild(el('span', 'cs-l', esc(G.card.replace('{i}', i + 1))));
      c.appendChild(el('h3', '', fmt(it.text)));
      var qid = 'cs-gq' + i;
      var group = el('div', 'cs-pills');
      group.setAttribute('role', 'group');
      if (G.question) {
        var q = el('p', 'cs-q', esc(G.question)); q.id = qid;
        c.appendChild(q);
        group.setAttribute('aria-labelledby', qid);
      } else {
        group.setAttribute('aria-label', G.header);
      }
      var opts = G.options.map(function (o, k) {
        var b = el('button', 'cs-pill');
        b.type = 'button';
        b.textContent = o;
        b.setAttribute('aria-pressed', 'false');
        b.addEventListener('click', function () {
          // An option in G.exclusive goes on its own: lesson 2's «Nowhere», and both answers of lesson 1.
          var at = picked.indexOf(k), only = G.exclusive || [];
          if (at >= 0) picked.splice(at, 1);
          else if (only.indexOf(k) >= 0) picked = [k];
          else { picked = picked.filter(function (x) { return only.indexOf(x) < 0; }); picked.push(k); }
          opts.forEach(function (ob, j) { ob.setAttribute('aria-pressed', String(picked.indexOf(j) >= 0)); });
          check.disabled = picked.length === 0;
        });
        group.appendChild(b);
        return b;
      });
      c.appendChild(group);
      var actions = el('div', 'cs-actions');
      var msg = el('div', 'cs-msg', ''); msg.setAttribute('role', 'status'); msg.hidden = true;
      var check = button(G.buttons.check, '', function () {
        var ok = picked.length === it.answer.length && it.answer.every(function (a) { return picked.indexOf(a) >= 0; });
        if (ok) score++;
        opts.forEach(function (ob) { ob.disabled = true; });
        msg.className = 'cs-msg ' + (ok ? 'right' : 'wrong');
        msg.innerHTML = '<b>' + esc(ok ? G.right : G.wrong) + '</b> ' + fmt(it.expl) +
          '<small>' + esc(G.source.replace('{source}', it.source)) + '</small>';
        msg.hidden = false;
        actions.innerHTML = '';
        var last = i === G.items.length - 1;
        var next = button(last ? G.buttons.result : G.buttons.next, '', function () { if (last) end(); else { i++; card(); } });
        actions.appendChild(next);
        next.focus();
      });
      check.disabled = true;
      actions.appendChild(check);
      c.appendChild(msg);
      c.appendChild(actions);
      box.appendChild(c);
    }
    function end() {
      box.innerHTML = '';
      var c = el('div', 'cs-c');
      var key = score >= 5 ? 'high' : score >= 3 ? 'mid' : 'low';
      var msg = el('div', 'cs-msg end', '<b>' + esc(G.end[key]) + '</b><p>' + esc(G.always) + '</p>');
      msg.setAttribute('role', 'status');
      c.appendChild(msg);
      var actions = el('div', 'cs-actions');
      actions.appendChild(button(G.buttons.again, '', function () { i = 0; score = 0; card(); }));
      c.appendChild(actions);
      box.appendChild(c);
    }
    card();
  }

  function test() {
    var Q = T.test, box = $('cs-test'), i = 0, score = 0;
    function card() {
      var it = Q.items[i];
      box.innerHTML = '';
      var c = el('div', 'cs-c');
      c.appendChild(el('span', 'cs-l', esc(Q.counter.replace('{i}', i + 1))));
      var hid = 'cs-tq' + i;
      var h = el('h3', '', fmt(it.q)); h.id = hid;
      c.appendChild(h);
      var group = el('div', 'cs-pills');
      group.setAttribute('role', 'radiogroup');
      group.setAttribute('aria-labelledby', hid);
      var msg = el('div', 'cs-msg', ''); msg.setAttribute('role', 'status'); msg.hidden = true;
      var actions = el('div', 'cs-actions');
      var opts = it.options.map(function (o, k) {
        var b = el('button', 'cs-pill');
        b.type = 'button';
        b.setAttribute('role', 'radio');
        b.setAttribute('aria-checked', 'false');
        b.textContent = o;
        b.addEventListener('click', function () {
          var ok = k === it.answer;
          if (ok) score++;
          opts.forEach(function (ob, j) { ob.setAttribute('aria-checked', String(j === k)); ob.disabled = true; });
          msg.className = 'cs-msg ' + (ok ? 'right' : 'wrong');
          msg.innerHTML = '<b>' + esc(ok ? Q.right : Q.wrong) + '</b> ' + fmt(it.expl);
          msg.hidden = false;
          var last = i === Q.items.length - 1;
          var next = button(last ? Q.buttons.result : Q.buttons.next, '', function () { if (last) end(); else { i++; card(); } });
          actions.appendChild(next);
          next.focus();
        });
        group.appendChild(b);
        return b;
      });
      c.appendChild(group);
      c.appendChild(msg);
      c.appendChild(actions);
      box.appendChild(c);
    }
    function end() {
      box.innerHTML = '';
      var c = el('div', 'cs-c');
      var msg = el('div', 'cs-msg end', '<b>' + esc(Q.result.replace('{score}', score)) + '</b><p>' +
        esc(score === Q.items.length ? Q.all : Q.less) + '</p>');
      msg.setAttribute('role', 'status');
      c.appendChild(msg);
      var actions = el('div', 'cs-actions');
      actions.appendChild(button(Q.buttons.again, '', function () { i = 0; score = 0; card(); }));
      c.appendChild(actions);
      box.appendChild(c);
    }
    card();
  }

  game();
  test();
})();
