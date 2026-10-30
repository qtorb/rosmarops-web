// Sample report captures for the homes and the sample report pages (GTM-45).
// Usage: node tools/sample-captures/cap.js <folder with sample-report.en.html and .es.html> <output folder>
// Serves the input folder with «python3 -m http.server 8777» and writes the eight PNG to the output folder.
const { spawn } = require('child_process');
const net = require('net');
const path = require('path');
const { chromium } = require('playwright');

const [inDir, outDir] = process.argv.slice(2);
if (!inDir || !outDir) {
  console.error('usage: node cap.js <input folder> <output folder>');
  process.exit(2);
}

function waitForPort(port, ms) {
  const end = Date.now() + ms;
  return new Promise((resolve, reject) => {
    const tryOnce = () => {
      const s = net.connect(port, '127.0.0.1');
      s.on('connect', () => { s.end(); resolve(); });
      s.on('error', () => (Date.now() > end ? reject(new Error('server did not start')) : setTimeout(tryOnce, 100)));
    };
    tryOnce();
  });
}

(async () => {
  const server = spawn('python3', ['-m', 'http.server', '8777', '--bind', '127.0.0.1'], { cwd: path.resolve(inDir), stdio: 'ignore' });
  let code = 0;
  try {
    await waitForPort(8777, 10000);
    const b = await chromium.launch();
    try {
      for (const l of ['en', 'es']) {
        for (const [kind, w, sel] of [['desktop', 1280, 'section.now .tbox'], ['mobile', 390, 'section.now .proj']]) {
          for (const dsf of [1, 2]) {
            const ctx = await b.newContext({ viewport: { width: w, height: 900 }, deviceScaleFactor: dsf });
            const p = await ctx.newPage();
            await p.goto(`http://127.0.0.1:8777/sample-report.${l}.html`, { waitUntil: 'load' });
            const bottom = await p.evaluate((sel) => {
              const e = document.querySelector(sel);
              return e ? e.getBoundingClientRect().bottom + scrollY : null;
            }, sel);
            if (bottom === null) throw new Error(`${sel} not found in sample-report.${l}.html`);
            const h = Math.ceil(bottom + 24);
            const file = path.join(outDir, `sample-${kind}.${l}${dsf === 2 ? '@2x' : ''}.png`);
            await p.screenshot({ path: file, clip: { x: 0, y: 0, width: w, height: h }, fullPage: true });
            console.log(`${file} ${w}x${h} css px, scale ${dsf}`);
            await ctx.close();
          }
        }
      }
    } finally {
      await b.close();
    }
  } catch (e) {
    console.error(e.message);
    code = 1;
  } finally {
    server.kill();
  }
  process.exit(code);
})();
