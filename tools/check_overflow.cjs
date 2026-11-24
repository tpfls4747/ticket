#!/usr/bin/env node
/* 문구 수정 후 레이아웃이 넘치지 않는지 점검한다.
 * 사용법: node tools/check_overflow.cjs <번들.html>
 *
 * 각 페이지(1920x1080)와 폰 화면(390x844)에서
 *  (a) 컨테이너 밖으로 삐져나간 요소 (overflow:hidden 으로 잘릴 수 있음)
 *  (b) overflow:hidden 요소 중 내용이 더 큰 것 (텍스트 잘림 후보)
 * 의 개수를 센다. 원본과 수정본에서 같은 명령으로 돌려 비교한다.
 */
const path = require('path');
const { chromium } = require('playwright');
const file = process.argv[2];
(async () => {
  const b = await chromium.launch(process.env.HTTPS_PROXY ? { proxy: { server: process.env.HTTPS_PROXY } } : {});
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  await page.goto('file://' + path.resolve(file));
  await page.waitForSelector('section.board iframe');
  const frames = [];
  for (const h of await page.$$('section.board iframe')) frames.push(await h.contentFrame());
  await page.waitForTimeout(7000);
  const out = [];
  for (let i = 0; i < frames.length; i++) {
    const r = await frames[i].evaluate(async () => {
      await document.fonts.ready;
      const res = { outside: [], clipped: [] };
      const boxes = [{ name: 'page', el: document.body, w: 1920, h: 1080 }];
      for (const d of document.querySelectorAll('div')) {
        if (d.offsetWidth === 390 && d.offsetHeight === 844) boxes.push({ name: 'phone', el: d });
      }
      for (const bx of boxes) {
        const rc = bx.el.getBoundingClientRect();
        const scale = rc.width / (bx.el.offsetWidth || 1);   // 표지의 0.877배 축소 대응
        const W = bx.w ? bx.w : rc.width, H = bx.h ? bx.h : rc.height;
        const left = bx.w ? 0 : rc.left, top = bx.w ? 0 : rc.top;
        // STEP 4B: 화면에 보이지 않는 요소는 제외한다
        //  - 스크린 리더 전용(1px·clip) 요소와 그 안의 글자, 닫힌 <details> 안의 내용(브라우저가 화면 밖에 배치해 둠)
        const hiddenAnc = (el) => {
          for (let a = el; a && a !== bx.el; a = a.parentElement) {
            const c = getComputedStyle(a);
            if (c.clip && c.clip !== 'auto' && a.getBoundingClientRect().width <= 2) return true;
            if (a.parentElement && a.parentElement.tagName === 'DETAILS' && !a.parentElement.open && a.tagName !== 'SUMMARY') return true;
          }
          return false;
        };
        for (const el of bx.el.querySelectorAll('*')) {
          const cs = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          if (r.width === 0 || r.height === 0 || cs.position === 'absolute' && el.closest('svg')) continue;
          if (hiddenAnc(el)) continue;
          if (r.bottom > top + H + 1 || r.right > left + W + 1) {
            res.outside.push(bx.name + ':' + el.tagName.toLowerCase() + ':' + (el.textContent || '').trim().slice(0, 20));
          }
          if ((cs.overflow === 'hidden' || cs.overflowY === 'hidden') && el !== bx.el && el.scrollHeight > el.clientHeight + 2 && el.clientHeight > 0) {
            res.clipped.push(bx.name + ':' + el.tagName.toLowerCase() + ':' + (el.textContent || '').trim().slice(0, 20));
          }
        }
      }
      return res;
    });
    out.push({ page: 'P' + String(i + 1).padStart(2, '0'), outside: r.outside.length, clipped: r.clipped.length, sample: r.outside.concat(r.clipped).slice(0, 3) });
  }
  console.log(JSON.stringify(out));
  await b.close();
})();
