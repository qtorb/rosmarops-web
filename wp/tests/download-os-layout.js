// GTM-129b: the three buttons of each .dl block of a home, with a Mac agent, and the top of each one.
// node download-os-layout.js <site dir> <path> <width>   → prints JSON [[ [text, top], ... ], ...]
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const [root, page_, width] = process.argv.slice(2);
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json' };
const srv = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p.endsWith('/')) p += 'index.html';
  const f = path.join(root, path.normalize(p));
  if (!f.startsWith(path.resolve(root)) || !fs.existsSync(f)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
});
srv.listen(0, '127.0.0.1', async () => {
  const b = await chromium.launch();
  try {
    const ctx = await b.newContext({ viewport: { width: Number(width), height: 800 },
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15' });
    await ctx.addInitScript(() => {
      Object.defineProperty(navigator, 'userAgentData', { get: () => ({ platform: 'macOS' }) });
      Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
      Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
    });
    const pg = await ctx.newPage();
    await pg.route('**/wp-json/**', r => r.abort());
    await pg.goto(`http://127.0.0.1:${srv.address().port}${page_}`);
    await pg.waitForFunction(() => /Mac/.test(document.querySelector('.dl a').textContent));
    console.log(JSON.stringify(await pg.evaluate(() => [...document.querySelectorAll('.dl')].map(
      d => [...d.children].map(a => [a.textContent, Math.round(a.getBoundingClientRect().top)])))));
  } finally { await b.close(); srv.close(); }
});
