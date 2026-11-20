#!/usr/bin/env node
/* 모든 폰 화면(390x844)의 본문(main)이 잘리는지 점검한다.
 * 사용법: node tools/check_phones.cjs <번들.html>
 * main 의 scrollHeight 가 clientHeight 보다 크면 아래가 잘리는(overflow:hidden) 화면이다.
 * 출력: 페이지 번호, 화면 제목, 남는 높이(음수면 잘림) 목록.
 */
const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const launch = { args: ['--disable-gpu'] };
  if (process.env.HTTPS_PROXY) launch.proxy = { server: process.env.HTTPS_PROXY };
  const b = await chromium.launch(launch);
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  await page.goto('file://' + path.resolve(process.argv[2]));
  await page.waitForSelector('section.board iframe');
  const frames = [];
  for (const h of await page.$$('section.board iframe')) frames.push(await h.contentFrame());
  await page.waitForTimeout(9000);
  let bad = 0, total = 0;
  for (let i = 0; i < frames.length; i++) {
    const rows = await frames[i].evaluate(async () => {
      await document.fonts.ready;
      const out = [];
      for (const m of document.querySelectorAll('main')) {
        const root = m.parentElement;
        if (!root || root.offsetWidth !== 390 || root.offsetHeight !== 844) continue;
        const h1 = root.querySelector('h1');
        out.push({ title: h1 ? h1.textContent.trim() : '?', free: m.clientHeight - m.scrollHeight, h: m.clientHeight });
      }
      return out;
    });
    const seen = new Set();
    for (const r of rows) {
      const key = r.title + r.free;
      if (seen.has(key)) continue;
      seen.add(key);
      total++;
      const flag = r.free < 0 ? '잘림' : '  OK';
      if (r.free < 0) bad++;
      console.log(`P${String(i + 1).padStart(2, '0')}  ${flag}  남는 높이 ${String(r.free).padStart(4)} px  ${r.title}`);
    }
  }
  console.log('폰 화면 %d개 중 잘림 %d개', total, bad);
  await b.close();
})();
