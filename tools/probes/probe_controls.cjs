#!/usr/bin/env node
/* P08 의 체크박스·라디오를 실제 마우스 클릭으로 하나씩 눌러 결과 분포를 센다.
 * 사용법: node tools/probes/probe_controls.cjs <번들.html> [반복수=6]
 *
 * 주의: Playwright 의 click({force:true}) 는 요소가 안정화되지 않은 상태에서 좌표를 잘못 잡아
 * 클릭이 빗나가는 경우가 있어(STEP 2B 조사에서 확인) 쓰지 않는다.
 * 보드를 직접 스크롤한 뒤 요소의 실제 좌표를 page.mouse.click 으로 누른다.
 */
const path = require('path');
const { chromium } = require('playwright');
const file = process.argv[2];
const reps = Number(process.argv[3] || 6);
const FRAME = 7; // P08
(async () => {
  const b = await chromium.launch(process.env.HTTPS_PROXY ? { proxy: { server: process.env.HTTPS_PROXY } } : {});
  const seqs = {};
  for (let r = 0; r < reps; r++) {
    const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    await page.goto('file://' + path.resolve(file));
    await page.waitForSelector('section.board iframe');
    const frames = [];
    for (const h of await page.$$('section.board iframe')) frames.push(await h.contentFrame());
    await page.waitForTimeout(5000);
    const f = frames[FRAME];
    await (await page.$$('section.board iframe'))[FRAME].evaluate((e) => e.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(500);
    const n = await f.evaluate(() => document.querySelectorAll('input[type=radio],input[type=checkbox]').length);
    const steps = [];
    for (let k = 0; k < n; k++) {
      const ctl = (await f.$$('input[type=radio],input[type=checkbox]'))[k];
      const box = await ctl.boundingBox();
      await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(400);
      steps.push(await f.evaluate(() => [...document.querySelectorAll('input[type=radio],input[type=checkbox]')].map((e) => (e.checked ? 1 : 0)).join('')));
    }
    const key = steps.join(' ');
    seqs[key] = (seqs[key] || 0) + 1;
    await ctx.close();
  }
  console.log(JSON.stringify(seqs, null, 1));
  await b.close();
})();
