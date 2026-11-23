#!/usr/bin/env node
/* STEP 3A 실험: 보드의 첫 번째 폰에서 링크를 눌러 같은 자리 화면 전환이 되는지 확인.
 * 사용법: node tools/probes/probe_nav_once.cjs <번들.html> [보드 제목 일부]
 */
const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const want = process.argv[3] || 'P07 UI 좌석·회차 교환';
  const launch = { args: ['--disable-gpu'] };
  if (process.env.HTTPS_PROXY) launch.proxy = { server: process.env.HTTPS_PROXY };
  const b = await chromium.launch(launch);
  const page = await (await b.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true })).newPage();
  const logs = [];
  page.on('console', (m) => { if (m.type() !== 'log') logs.push(m.type() + ': ' + m.text().slice(0, 160)); });
  page.on('pageerror', (e) => logs.push('pageerror: ' + String(e).slice(0, 160)));
  page.on('framenavigated', (f) => logs.push('framenavigated: ' + f.url().slice(0, 50)));
  await page.goto('file://' + path.resolve(process.argv[2]));
  await page.waitForSelector('section.board iframe');
  const titles = await page.$$eval('section.board h2', (a) => a.map((x) => x.textContent));
  const idx = titles.findIndex((t) => t.startsWith(want));
  const fh = (await page.$$('section.board iframe'))[idx];
  const f = await fh.contentFrame();
  await page.waitForTimeout(7000);
  const visible = () => f.evaluate(() => [...document.querySelectorAll('[data-nav-host]')].map((h) =>
    [...h.children].filter((c) => getComputedStyle(c).display !== 'none').map((c) => (c.querySelector('h1') || {}).textContent || '?')));
  console.log('보드:', titles[idx], '| 초기 보이는 화면:', JSON.stringify(await visible()));
  const clickText = async (host, text) => {
    const el = await f.evaluateHandle(([h, t]) => [...document.querySelectorAll('[data-nav-host="' + h + '"] a[href]')]
      .find((a) => a.offsetParent !== null && (a.textContent.trim() === t || a.getAttribute('aria-label') === t)), [host, text]);
    const ae = el.asElement();
    if (!ae) { console.log('  링크 없음:', host, text); return; }
    await fh.evaluate((e) => e.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(200);
    const box = await ae.boundingBox();
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
    await page.waitForTimeout(500);
    console.log('  클릭 [' + text + '] →', JSON.stringify((await visible())[host]), '| 프레임 URL', f.url().slice(0, 30));
  };
  await clickText(0, '좌석·회차 교환 신청');
  await clickText(0, '교환 신청 등록');
  await clickText(0, '뒤로');
  await clickText(0, '뒤로');
  console.log('로그:', JSON.stringify(logs));
  await b.close();
})();
