// GTM-129b, GTM-137: the download rows of a home in Chromium, with a Mac or Windows agent.
// node download-os-layout.js <site dir> <path> <width> <mac|windows>
//   → prints JSON {rows: [[[text, top, height], ...], ...], others: [[visible items], ...], heroRowBottom, overflow}
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const [root, page_, width, os] = process.argv.slice(2);
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json', '.jpg': 'image/jpeg' };
const AGENTS = {
  mac: ['Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15', 'macOS', 'MacIntel'],
  windows: ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36', 'Windows', 'Win32'],
};
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
    const [ua, uaPlatform, platform] = AGENTS[os || 'mac'];
    const ctx = await b.newContext({ viewport: { width: Number(width), height: 800 }, userAgent: ua });
    await ctx.addInitScript(([u, p]) => {
      Object.defineProperty(navigator, 'userAgentData', { get: () => ({ platform: u }) });
      Object.defineProperty(navigator, 'platform', { get: () => p });
      Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
    }, [uaPlatform, platform]);
    const pg = await ctx.newPage();
    await pg.route('**/wp-json/**', r => r.abort());
    await pg.route('**/assets/visits/**', r => r.abort());
    await pg.goto(`http://127.0.0.1:${srv.address().port}${page_}`, { waitUntil: 'load' });
    await pg.waitForTimeout(200);
    console.log(JSON.stringify(await pg.evaluate(() => {
      const vis = e => getComputedStyle(e).display !== 'none' && !e.hidden;
      const rows = [...document.querySelectorAll('.dlrow')].map(d => [...d.children].filter(vis).map(a => {
        const r = a.getBoundingClientRect();
        return [a.textContent || (a.querySelector('img') || {}).alt || '', Math.round(r.top + scrollY), Math.round(r.height)];
      }));
      const others = [...document.querySelectorAll('.oth')].map(o => [...o.querySelectorAll('.os-o')].filter(vis).map(s => s.textContent));
      const first = document.querySelector('.dlrow').getBoundingClientRect();
      return { rows, others, heroRowBottom: Math.round(first.bottom + scrollY), overflow: document.documentElement.scrollWidth > innerWidth };
    })));
  } finally { await b.close(); srv.close(); }
});
