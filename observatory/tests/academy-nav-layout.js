// GTM-230: how many lines the header menu takes, in Chromium.
// node academy-nav-layout.js <site dir> <width> <path> [<path> ...]
//   → prints JSON {path: {lines, entries, overflow}}: lines counts the distinct tops of the menu links.
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const [root, width, ...paths] = process.argv.slice(2);
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
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
  const out = {};
  try {
    const ctx = await b.newContext({ viewport: { width: Number(width), height: 800 } });
    const pg = await ctx.newPage();
    await pg.route('**/wp-json/**', r => r.abort());
    await pg.route('**/assets/visits/**', r => r.abort());
    for (const p of paths) {
      await pg.goto(`http://127.0.0.1:${srv.address().port}${p}`, { waitUntil: 'load' });
      if (process.env.LAYOUT_FONT) await pg.addStyleTag({ content: `*{font-family:"${process.env.LAYOUT_FONT}",Arial,sans-serif !important}` });
      await pg.waitForTimeout(100);
      out[p] = await pg.evaluate(() => {
        const a = [...document.querySelector('header nav').querySelectorAll('a')];
        return { lines: new Set(a.map(x => Math.round(x.getBoundingClientRect().top))).size, entries: a.map(x => x.textContent.trim()),
                 overflow: document.documentElement.scrollWidth > innerWidth };
      });
    }
  } finally { await b.close(); srv.close(); }
  console.log(JSON.stringify(out));
});
