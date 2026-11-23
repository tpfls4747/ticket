#!/usr/bin/env node
/* 링크 클릭 시 about:blank#blocked 로 가는 원인 조사 (STEP 3A).
 * 사용법: node tools/probes/probe_link_cause.cjs <번들.html> [보드 제목 일부=UI 좌석·회차 교환]
 * 기록: 프레임 URL·baseURI·origin, 링크 href 원문과 해석값, URL 해석 오류, iframe 속성,
 *       클릭 후 내비게이션·콘솔 메시지, 같은 문서 해시 이동(#)과의 비교.
 */
const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const file = process.argv[2];
  const want = process.argv[3] || 'UI 좌석·회차 교환';
  const launch = { args: ['--disable-gpu'] };
  if (process.env.HTTPS_PROXY) launch.proxy = { server: process.env.HTTPS_PROXY };
  const b = await chromium.launch(launch);
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  const log = [];
  page.on('console', (m) => log.push('console.' + m.type() + ': ' + m.text().slice(0, 200)));
  page.on('framenavigated', (f) => log.push('framenavigated: ' + f.url().slice(0, 80)));
  page.on('requestfailed', (r) => log.push('requestfailed: ' + r.url().slice(0, 80) + ' ' + (r.failure() || {}).errorText));
  await page.goto('file://' + path.resolve(file));
  await page.waitForSelector('section.board iframe');
  const handles = await page.$$('section.board iframe');
  const titles = await page.$$eval('section.board h2', (a) => a.map((x) => x.textContent));
  const idx = titles.findIndex((t) => t.includes(want));
  const fh = handles[idx];
  const f = await fh.contentFrame();
  await page.waitForTimeout(7000);
  const iframeAttrs = await fh.evaluate((e) => ({ src: e.getAttribute('src').slice(0, 40), sandbox: e.getAttribute('sandbox'), allow: e.getAttribute('allow') }));
  const info = await f.evaluate(() => {
    const a = document.querySelector('a[href]');
    let parsed;
    try { parsed = new URL(a.getAttribute('href'), document.baseURI).href; } catch (e) { parsed = 'URL 해석 오류: ' + e.message; }
    return {
      url: location.href.slice(0, 50), baseURI: document.baseURI.slice(0, 50), origin: window.origin,
      isTop: window.top === window, hrefAttr: a.getAttribute('href'), hrefProp: a.href, parsed,
      target: a.getAttribute('target'), baseTag: !!document.querySelector('base'),
      links: document.querySelectorAll('a[href]').length,
      hrefKinds: [...new Set([...document.querySelectorAll('a[href]')].map((x) => x.getAttribute('href')))],
    };
  });
  console.log('보드:', titles[idx]);
  console.log('iframe 속성:', JSON.stringify(iframeAttrs));
  console.log('프레임 문서:', JSON.stringify(info, null, 1));
  // 실제 마우스 클릭
  const a = await f.$('a[href]');
  await fh.evaluate((e) => e.scrollIntoView({ block: 'center' }));
  await page.waitForTimeout(300);
  const box = await a.boundingBox();
  log.length = 0;
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await page.waitForTimeout(1500);
  console.log('클릭 후 프레임 URL:', f.url().slice(0, 60));
  console.log('클릭 후 로그:', JSON.stringify(log, null, 1));
  // 비교: 같은 blob 문서 안의 해시 링크는 차단되는가?
  const page2 = await ctx.newPage();
  await page2.goto('file://' + path.resolve(file));
  await page2.waitForSelector('section.board iframe');
  const f2 = await (await page2.$$('section.board iframe'))[idx].contentFrame();
  await page2.waitForTimeout(6000);
  const hashTest = await f2.evaluate(() => {
    const before = location.href;
    const a = document.createElement('a'); a.href = '#probe'; document.body.appendChild(a); a.click();
    return { before: before.slice(0, 50), after: location.href.slice(0, 60), sameDoc: location.href.startsWith(before) };
  });
  console.log('해시 링크 비교:', JSON.stringify(hashTest));
  await b.close();
})();
