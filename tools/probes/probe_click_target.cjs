#!/usr/bin/env node
/* P08 링크 클릭이 실행마다 달라지는 원인 조사용 프로브.
 * 사용법: node tools/probes/probe_click_target.cjs <번들.html> [반복수=4]
 *
 * 클릭 시점(로드 후 2s/6s/12s)별로,
 *   - 마우스 좌표에서 실제로 맨 위에 있는 요소(elementFromPoint)가 의도한 링크인지
 *   - 클릭 이벤트가 어느 요소에 도달했는지, 버블 단계에서 defaultPrevented 였는지
 *   - 프레임이 about:blank#blocked 로 이동했는지
 * 를 기록한다. (프레임 3번째 인자: 7=P08, 0=P01)
 */
const path = require('path');
const { chromium } = require('playwright');
const file = process.argv[2];
const reps = Number(process.argv[3] || 4);
const frameIdx = Number(process.argv[4] || 7);
const label = process.argv[5] || '옆자리 2곳에 제안 보내기';
const delays = [2000, 6000, 12000];
(async () => {
  const b = await chromium.launch(process.env.HTTPS_PROXY ? { proxy: { server: process.env.HTTPS_PROXY } } : {});
  const rows = [];
  for (const delay of delays) {
    for (let r = 0; r < reps; r++) {
      const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true });
      const page = await ctx.newPage();
      const nav = [];
      page.on('framenavigated', (f) => nav.push(f.url().slice(0, 30)));
      await page.goto('file://' + path.resolve(file));
      await page.waitForSelector('section.board iframe');
      const frames = [];
      for (const h of await page.$$('section.board iframe')) frames.push(await h.contentFrame());
      await page.waitForTimeout(delay);
      const f = frames[frameIdx];
      await f.evaluate(() => {
        window.__ev = null;
        const rec = (phase) => (e) => {
          const a = e.target.closest && e.target.closest('a');
          window.__ev = Object.assign(window.__ev || {}, { [phase]: { tag: e.target.tagName, a: a ? a.getAttribute('href') : null, dp: e.defaultPrevented } });
        };
        document.addEventListener('click', rec('capture'), true);
        document.addEventListener('click', rec('bubble'), false);
      });
      const el = await f.$('a:has-text("' + label + '")');
      if (!el) throw new Error('링크를 찾지 못함: ' + label + ' (문구가 바뀐 빌드라면 5번째 인자로 지정)');
      // 요소 자체의 안정화 대기는 쓰지 않고(원본에서 시간 초과가 반복됨) 보드를 직접 스크롤한다.
      await (await page.$$('section.board iframe'))[frameIdx].evaluate((e) => e.scrollIntoView({ block: 'center' }));
      await page.waitForTimeout(400);
      const box = await el.boundingBox();
      const cx = box.x + box.width / 2, cy = box.y + box.height / 2;
      // 프레임 안 좌표로 환산해 최상단 요소 확인
      // 프레임은 불투명 origin 이라 frameElement 를 쓸 수 없으므로, 부모 쪽에서 iframe 위치를 구해 환산한다.
      const fb = await (await page.$$('section.board iframe'))[frameIdx].boundingBox();
      const top = await f.evaluate(([x, y]) => {
        const e = document.elementFromPoint(x, y);
        const a = e && e.closest && e.closest('a');
        return { tag: e && e.tagName, a: a ? a.getAttribute('href') : null };
      }, [cx - fb.x, cy - fb.y]);
      nav.length = 0;
      await page.mouse.click(cx, cy);
      await page.waitForTimeout(1500);
      const ev = await f.evaluate(() => window.__ev).catch(() => 'frame-replaced');
      rows.push({ delay, top, ev: ev === 'frame-replaced' ? ev : { target: ev && ev.capture && ev.capture.a, bubbleDP: ev && ev.bubble && ev.bubble.dp }, nav: nav.length ? nav : '-' });
      await ctx.close();
    }
  }
  const summary = {};
  for (const r of rows) {
    const k = 'delay ' + r.delay + 'ms | topIsLink=' + (r.top.a !== null) + ' | reachedLink=' + (r.ev !== 'frame-replaced' && !!(r.ev && r.ev.target)) + ' | bubbleDefaultPrevented=' + (r.ev && r.ev.bubbleDP) + ' | nav=' + JSON.stringify(r.nav);
    summary[k] = (summary[k] || 0) + 1;
  }
  console.log(JSON.stringify(summary, null, 1));
  await b.close();
})();
