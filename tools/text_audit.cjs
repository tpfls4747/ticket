#!/usr/bin/env node
/* 모바일 화면 텍스트 감사: 보드의 모든 폰 화면을 하나씩 펼쳐 '보이는 글자'를 화면(컴포넌트)별로 모은다.
 * 사용법: node tools/text_audit.cjs <번들.html> <결과 JSON>
 * - 스크린 리더 전용(1px·clip) 글자와 닫힌 <details> 안의 글자는 '기본으로 보이는 글자'에서 뺀다 (따로 hidden 으로 센다)
 * - 같은 화면이 여러 보드에 있으면 처음 만난 것(기본 장면)을 쓴다
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const launch = { args: ['--disable-gpu', '--font-render-hinting=none'] };
  if (process.env.HTTPS_PROXY) launch.proxy = { server: process.env.HTTPS_PROXY };
  const browser = await chromium.launch(launch);
  const page = await (await browser.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true })).newPage();
  await page.goto('file://' + path.resolve(process.argv[2]));
  await page.waitForSelector('section.board iframe');
  const titles = await page.$$eval('section.board h2', (a) => a.map((x) => x.textContent));
  const handles = await page.$$('section.board iframe');
  await page.waitForTimeout(9000);
  const out = {};
  for (let i = 0; i < handles.length; i++) {
    const f = await handles[i].contentFrame();
    const rows = await f.evaluate(() => {
      const visibleText = (root) => {
        // 보이는 글자만: 스크린 리더 전용·닫힌 details 내용 제외
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        const parts = [];
        let n;
        while ((n = walker.nextNode())) {
          const t = n.textContent.replace(/\s+/g, ' ').trim();
          if (!t) continue;
          let hidden = false;
          for (let a = n.parentElement; a && a !== root; a = a.parentElement) {
            const cs = getComputedStyle(a);
            if (cs.display === 'none' || (cs.clip && cs.clip !== 'auto' && a.getBoundingClientRect().width <= 2)) { hidden = true; break; }
            if (a.parentElement && a.parentElement.tagName === 'DETAILS' && !a.parentElement.open && a.tagName !== 'SUMMARY') { hidden = true; break; }
            if (a.tagName === 'SCRIPT' || a.tagName === 'STYLE') { hidden = true; break; }
          }
          if (!hidden) parts.push(t);
        }
        return parts;
      };
      const res = [];
      // 화면 단위: [data-nav-screen] (전환형) 또는 확대 단위 폰(정적 보드)
      const screens = [...document.querySelectorAll('[data-nav-screen]')];
      const statics = [...document.querySelectorAll('[data-zoom-host]')].filter((h) => !h.querySelector('[data-nav-screen]'));
      const items = screens.map((s) => ({ el: s, name: s.getAttribute('data-nav-screen') }))
        .concat(statics.map((h) => ({ el: h, name: null })));
      for (const it of items) {
        const was = it.el.style.display;
        it.el.style.display = 'block';
        const root = it.el.querySelector('div') || it.el;
        let name = it.name;
        if (!name) { const t = root.querySelector('h1'); name = 'static:' + (t ? t.textContent.trim() : '?'); }
        const parts = visibleText(it.el);
        const all = it.el.innerText.replace(/\s+/g, ' ').trim();
        res.push({ name, parts, chars: parts.join('').replace(/\s/g, '').length });
        it.el.style.display = was;
      }
      return res;
    });
    for (const r of rows) {
      if (!out[r.name]) out[r.name] = { board: titles[i], chars: r.chars, parts: r.parts };
    }
  }
  await browser.close();
  fs.writeFileSync(process.argv[3], JSON.stringify(out, null, 1));
  const names = Object.keys(out).sort();
  let total = 0;
  for (const n of names) { total += out[n].chars; console.log(String(out[n].chars).padStart(5), n, '·', out[n].board); }
  console.log('합계 화면 %d개, 보이는 글자 %d자', names.length, total);
})().catch((e) => { console.error(e); process.exit(2); });
