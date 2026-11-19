const { chromium } = require('playwright');
(async () => {
  const file = process.argv[2];
  const tag = process.argv[3];
  const b = await chromium.launch({ proxy: { server: process.env.HTTPS_PROXY } });
  const out = [];
  for (let run = 0; run < 3; run++) {
    const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    await page.goto('file://' + file);
    await page.waitForSelector('section.board iframe');
    const hs = await page.$$('section.board iframe');
    const frames = [];
    for (const h of hs) frames.push(await h.contentFrame());
    await page.waitForTimeout(6000);
    const res = [];
    for (const i of [5, 6, 7]) {
      const buf = await hs[i].screenshot();
      const info = await frames[i].evaluate(() => ({ sy: document.scrollingElement.scrollTop, vis: document.visibilityState, n: document.querySelectorAll('*').length }));
      res.push('P0' + (i + 1) + ' png=' + buf.length + ' ' + JSON.stringify(info));
    }
    out.push(res.join(' | '));
    await ctx.close();
  }
  console.log(tag + '\n  ' + out.join('\n  '));
  await b.close();
})();
