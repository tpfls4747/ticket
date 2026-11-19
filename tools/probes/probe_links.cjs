const { chromium } = require('playwright');
const crypto = require('crypto');
const H = (s) => crypto.createHash('md5').update(s.replace(/blob:null\/[0-9a-f-]{36}/g, 'B')).digest('hex').slice(0, 8);
(async () => {
  const file = process.argv[2];
  const base = JSON.parse(process.argv[3]);
  const targets = [];
  for (let r = 0; r < Number(process.argv[4] || 1); r++) for (const t of base) targets.push(t);
  const b = await chromium.launch({ proxy: { server: process.env.HTTPS_PROXY } });
  for (const [fi, label] of targets) {
    const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    const nav = [];
    page.on('framenavigated', (f) => nav.push(f.url().slice(0, 50)));
    page.on('popup', () => nav.push('POPUP'));
    await page.goto('file://' + file);
    await page.waitForSelector('section.board iframe');
    const hs = await page.$$('section.board iframe');
    const frames = [];
    for (const h of hs) frames.push(await h.contentFrame());
    await page.waitForTimeout(5000);
    nav.length = 0;
    const f = frames[fi];
    const before = H(await f.evaluate(() => document.documentElement.outerHTML));
    const sel = label === '뒤로' ? 'a[aria-label="뒤로"]' : 'a:has-text("' + label + '")';
    const el = await f.$(sel);
    let res = 'NOT FOUND';
    if (el) {
      let err = '';
      try { await el.click({ force: true, timeout: 4000 }); } catch (e) { err = ' click-error:' + e.message.split('\n')[0].slice(0, 50); }
      await page.waitForTimeout(2500);
      let after;
      try { after = H(await f.evaluate(() => document.documentElement.outerHTML)); } catch (e) { after = 'ERR'; }
      res = 'domChanged=' + (before !== after) + ' nav=' + JSON.stringify(nav) + ' topUrl=' + page.url().slice(-20) + err;
    }
    console.log('P0' + (fi + 1) + ' [' + label + '] ' + res);
    await ctx.close();
  }
  await b.close();
})();
