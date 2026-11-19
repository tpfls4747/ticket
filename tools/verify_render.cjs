#!/usr/bin/env node
/* 번들 HTML 하나를 Chromium 으로 열어 렌더링·DOM·인터랙션·콘솔 정보를 수집한다.
 *
 * 사용법: node tools/verify_render.cjs <번들.html> <출력디렉터리>
 *
 * 수집물 (출력디렉터리/):
 *   desktop/Pxx.png            1920x1080 보드 스크린샷 (10개)
 *   mobile/…png                390x844 뷰포트 + 390x844 폰 화면 요소 스크린샷
 *   dom/Pxx.html, text/Pxx.txt 정규화한 DOM / 화면 텍스트
 *   report.json                핑거프린트, 인터랙션, 콘솔/네트워크 로그, 리소스 목록
 * 비교는 tools/compare_render.py 가 한다.
 * 프록시가 설정된 환경(HTTPS_PROXY)에서는 그 프록시를 사용한다 (Google Fonts 로드용).
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const [, , htmlPath, outDir] = process.argv;
if (!htmlPath || !outDir) { console.error('usage: verify_render.cjs <html> <outdir>'); process.exit(2); }
const url = 'file://' + path.resolve(htmlPath);
const mk = (p) => fs.mkdirSync(p, { recursive: true });
['desktop', 'mobile', 'phones', 'dom', 'text'].forEach((d) => mk(path.join(outDir, d)));

const NORM = (s) => s
  .replace(/blob:null\/[0-9a-f-]{36}/g, 'blob:null/<id>')
  .replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g, '<uuid>');

// 프레임 안에서 실행: 화면 구조 핑거프린트 (태그·배경색·크기별 개수)
const FINGERPRINT = () => {
  const h = {};
  for (const el of document.body.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const key = [el.tagName, cs.backgroundColor, cs.color, cs.fontSize, cs.fontWeight,
      cs.fontFamily.split(',')[0], Math.round(r.width) + 'x' + Math.round(r.height)].join('|');
    h[key] = (h[key] || 0) + 1;
  }
  return h;
};
const INTERACTIVE_SEL = 'button, a[href], [aria-pressed], input, select, textarea, [tabindex], [onclick], summary';
const DESCRIBE = (el) => ({
  tag: el.tagName.toLowerCase(),
  text: (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 40),
  ariaLabel: el.getAttribute('aria-label'),
  ariaPressed: el.getAttribute('aria-pressed'),
  cursor: getComputedStyle(el).cursor,
  href: el.getAttribute('href'),
  type: el.getAttribute('type'),
  name: el.getAttribute('name'),
  checked: el.checked === undefined ? null : el.checked,
});

// 헤드리스 Chromium 은 큰 iframe 을 래스터화하기 전에 찍으면 빈(흰) PNG 를 돌려줄 때가 있다
// (원본·재번들 모두에서 무작위로 발생함을 확인). 색 종류가 너무 적으면 빈 화면으로 보고 다시 찍는다.
const retryLog = [];
async function robustShot(page, target, file, label) {
  for (let attempt = 1; attempt <= 10; attempt++) {
    const buf = await target.screenshot();
    const colors = await page.evaluate(async (b64) => {
      const bmp = await createImageBitmap(await (await fetch('data:image/png;base64,' + b64)).blob());
      const c = document.createElement('canvas'); c.width = bmp.width; c.height = bmp.height;
      const g = c.getContext('2d'); g.drawImage(bmp, 0, 0);
      const d = g.getImageData(0, 0, c.width, c.height).data; const s = new Set();
      for (let i = 0; i < d.length; i += 4 * 97) { s.add((d[i] << 16) | (d[i + 1] << 8) | d[i + 2]); if (s.size > 40) break; }
      return s.size;
    }, buf.toString('base64'));
    if (colors > 8) {
      // 렌더링이 아직 안정되지 않았을 수 있으므로(폰트 서브셋 지연 로드 등) 연속 두 번 같을 때만 채택한다.
      await page.waitForTimeout(250);
      const again = await target.screenshot();
      if (again.equals(buf)) { fs.writeFileSync(file, buf); if (attempt > 1) retryLog.push(label + ' x' + (attempt - 1)); return; }
    }
    await page.waitForTimeout(500);
  }
  throw new Error('빈 화면 캡처가 계속됨: ' + label);
}

async function waitReady(page, boards) {
  const t0 = Date.now();
  let prev = '', stable = 0;
  while (Date.now() - t0 < 40000) {
    const sig = [];
    for (const f of boards) {
      try {
        sig.push(await f.evaluate(async () => { await document.fonts.ready;
          return document.body.innerText.length + ':' + document.querySelectorAll('*').length; }));
      } catch (e) { sig.push('err'); }
    }
    const s = sig.join(',');
    if (s === prev && !s.includes('err') && !s.includes(':0,')) { if (++stable >= 6) return; } else { stable = 0; prev = s; }
    await page.waitForTimeout(250);
  }
  throw new Error('렌더링 안정화 시간 초과');
}

(async () => {
  // 글자 가장자리 렌더링(안티앨리어싱·힌팅)이 실행마다 달라지지 않도록 고정하는 옵션
  const launchOpts = { args: ['--font-render-hinting=none', '--disable-lcd-text', '--force-color-profile=srgb', '--disable-gpu'] };
  if (process.env.HTTPS_PROXY) launchOpts.proxy = { server: process.env.HTTPS_PROXY };
  const browser = await chromium.launch(launchOpts);
  const report = { url, logs: [], pages: {}, mobile: {}, root: {} };
  const log = (kind, detail) => report.logs.push({ kind, detail: NORM(String(detail)).slice(0, 300) });

  async function open(viewport) {
    const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) log('console.' + m.type(), m.text()); });
    page.on('pageerror', (e) => log('pageerror', e));
    page.on('requestfailed', (r) => log('requestfailed', r.url() + ' ' + (r.failure() || {}).errorText));
    page.on('response', (r) => { if (r.status() >= 400) log('http' + r.status(), r.url()); });
    page.on('popup', () => log('popup', 'new window opened'));
    await page.goto(url);
    await page.waitForSelector('section.board iframe');
    const frames = [];
    for (const h of await page.$$('section.board iframe')) frames.push(await h.contentFrame());
    await waitReady(page, frames);
    return { ctx, page, frames };
  }

  /* ---------- 데스크톱 1920x1080 ---------- */
  {
    const { ctx, page, frames } = await open({ width: 1920, height: 1080 });
    const handles = await page.$$('section.board iframe');
    report.root = {
      title: await page.title(),
      boardTitles: await page.$$eval('section.board h2', (a) => a.map((x) => x.textContent)),
      scrollHeight: await page.evaluate(() => document.documentElement.scrollHeight),
      iframeRects: await page.$$eval('section.board iframe', (a) => a.map((x) => { const r = x.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; })),
    };
    for (let i = 0; i < frames.length; i++) {
      const id = 'P' + String(i + 1).padStart(2, '0');
      const f = frames[i];
      await robustShot(page, handles[i], path.join(outDir, 'desktop', id + '.png'), 'desktop/' + id);
      {
        // 390x844 폰 화면 요소 (P01 은 0.877 배 축소 표시, P07/P08 은 원 크기)
        const phonesH = await f.evaluateHandle(() => [...document.querySelectorAll('div')].filter((d) => d.offsetWidth === 390 && d.offsetHeight === 844));
        let n = 0; const titles = [];
        for (const ph of (await phonesH.getProperties()).values()) {
          const el = ph.asElement(); if (!el) continue; n++;
          titles.push(await el.evaluate((e) => { const h = e.querySelector('h1,h2'); return h ? h.textContent.trim().replace(/\s+/g, ' ').slice(0, 20) : ''; }));
          await robustShot(page, el, path.join(outDir, 'phones', id + '-phone' + String(n).padStart(2, '0') + '.png'), 'phones/' + id + '-' + n);
        }
        (report.phones = report.phones || {})[id] = { count: n, titles };
      }
      const dom = NORM(await f.evaluate(() => document.documentElement.outerHTML));
      fs.writeFileSync(path.join(outDir, 'dom', id + '.html'), dom);
      const text = await f.evaluate(() => document.body.innerText);
      fs.writeFileSync(path.join(outDir, 'text', id + '.txt'), text);
      const info = await f.evaluate(() => ({
        title: document.title,
        resources: Object.keys(window.__resources || {}).sort(),
        scripts: [...document.scripts].map((s) => (s.type || 'js') + ':' + (s.src ? 'src' : 'inline')),
        stylesheets: [...document.querySelectorAll('link[rel=stylesheet]')].map((l) => l.href),
        fontsLoaded: [...document.fonts].filter((x) => x.status === 'loaded').map((x) => x.family + ' ' + x.weight).sort(),
        fontsFailed: [...document.fonts].filter((x) => x.status === 'error').map((x) => x.family + ' ' + x.weight),
        images: [...document.images].map((im) => im.currentSrc.slice(0, 40) + ':' + im.naturalWidth),
      }));
      const fp = await f.evaluate(FINGERPRINT);
      const phones = await f.evaluate(() => [...document.querySelectorAll('div')].filter((d) => d.offsetWidth === 390 && d.offsetHeight === 844).length);

      report.pages[id] = { info, fingerprint: fp, phoneFrames390x844: phones };
    }
    /* 스크롤 내비게이션: 각 보드로 스크롤했을 때 위치 */
    report.root.scrollTops = [];
    for (let i = 0; i < handles.length; i++) {
      await handles[i].scrollIntoViewIfNeeded();
      report.root.scrollTops.push(await page.evaluate(() => Math.round(window.scrollY)));
    }
    await ctx.close();
  }

  /* ---------- 인터랙션 (스크린샷과 분리된 새 페이지 로드에서 수행) ---------- */
  {
    const { ctx, page, frames } = await open({ width: 1920, height: 1080 });
    for (let i = 0; i < frames.length; i++) {
      const id = 'P' + String(i + 1).padStart(2, '0');
      const f = frames[i];
      const els = await f.$$(INTERACTIVE_SEL);
      const interactive = [];
      for (const el of els) interactive.push(await el.evaluate(DESCRIBE));
      /* 키보드: 이 프레임의 포커스 가능한 요소 수만큼만 Tab (다음 프레임으로 새지 않게) */
      const focusable = await f.evaluate((sel) => [...document.querySelectorAll(sel)].filter((e) =>
        !e.disabled && e.tabIndex >= 0 && getComputedStyle(e).visibility !== 'hidden').length, INTERACTIVE_SEL);
      const tabOrder = [];
      await f.evaluate(() => { document.body.tabIndex = -1; document.body.focus(); });
      for (let k = 0; k < focusable; k++) {
        await page.keyboard.press('Tab');
        tabOrder.push(await f.evaluate(() => { const a = document.activeElement;
          return a && a !== document.body ? a.tagName.toLowerCase() + ':' + (a.innerText || '').trim().slice(0, 20) : 'body'; }));
      }
      await f.evaluate(() => { if (document.activeElement) document.activeElement.blur(); });
      /* 클릭은 모두 '실제 마우스 클릭'으로 한다. Playwright 의 click({force:true}) 는 요소가 안정화되기 전의
         좌표로 눌러 빗나가는 경우가 있어(STEP 2B 조사로 확인), 결과가 실행마다 달라 보이는 원인이 되었다.
         보드를 화면 가운데로 스크롤한 뒤 요소의 실제 좌표를 누른다. */
      const realClick = async (el) => {
        await (await page.$$('section.board iframe'))[i].evaluate((e) => e.scrollIntoView({ block: 'center' }));
        await page.waitForTimeout(300);
        const box = await el.boundingBox();
        await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
      };
      /* 라디오·체크박스: 하나씩 눌러 보며 전체 checked 상태 기록 (네이티브 컨트롤 → 결정적) */
      const controlSteps = [];
      const ctlCount = await f.evaluate(() => document.querySelectorAll('input[type=radio],input[type=checkbox]').length);
      for (let k = 0; k < ctlCount; k++) {
        const ctl = (await f.$$('input[type=radio],input[type=checkbox]'))[k];
        await realClick(ctl);
        await page.waitForTimeout(300);
        controlSteps.push(await f.evaluate((idx) => ({
          clicked: idx,
          state: [...document.querySelectorAll('input[type=radio],input[type=checkbox]')].map((e) => e.type[0] + ':' + (e.name || '-') + ':' + (e.checked ? 1 : 0)).join(','),
        }), k));
      }
      /* 링크 클릭: 첫 번째 링크만 실제 마우스로 누른다. 누르면 프레임이 이동해 이후 요소가 사라지므로
         링크 하나당 한 번만 측정할 수 있다 (모든 링크의 동작은 같은 구조라 대표값으로 비교한다). */
      const firstLinkIdx = interactive.findIndex((x) => x.tag === 'a' && x.href);
      let firstLinkClick = null;
      if (firstLinkIdx >= 0) {
        const urlBefore = f.url();
        await realClick(els[firstLinkIdx]);
        await page.waitForTimeout(1200);
        const urlAfter = f.url();
        const bodyLen = await f.evaluate(() => document.body ? document.body.innerText.length : -1).catch(() => 'frame-replaced');
        firstLinkClick = { href: interactive[firstLinkIdx].href, urlChanged: urlAfter !== urlBefore,
          urlAfter: urlAfter.startsWith('blob:') ? 'blob:' : urlAfter, bodyTextAfter: bodyLen };
      }
      Object.assign(report.pages[id], { interactive, focusable, controlSteps, tabOrder, firstLinkClick });
    }
    await ctx.close();
  }

  /* ---------- 모바일 390x844 ---------- */
  {
    const { ctx, page, frames } = await open({ width: 390, height: 844 });
    report.mobile.rootScrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: path.join(outDir, 'mobile', 'viewport-top.png') });
    const mHandles = await page.$$('section.board iframe');
    for (let i = 0; i < mHandles.length; i++) {
      const id = 'P' + String(i + 1).padStart(2, '0');
      await mHandles[i].evaluate((e) => e.scrollIntoView({ block: 'start', inline: 'start' }));
      await page.waitForTimeout(150);
      await robustShot(page, page, path.join(outDir, 'mobile', id + '-viewport.png'), 'mobile/' + id);
      report.mobile[id] = { scrollX: await page.evaluate(() => Math.round(window.scrollX)), scrollY: await page.evaluate(() => Math.round(window.scrollY)) };
    }
    await ctx.close();
  }

  report.blankRetries = retryLog;   // 비교 대상 아님: 캡처 재시도 기록(투명성용)
  report.logs.sort((a, b) => (a.kind + a.detail).localeCompare(b.kind + b.detail));
  fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(report, null, 1));
  await browser.close();
  console.log('수집 완료:', outDir, '| 콘솔/네트워크 경고·오류:', report.logs.length);
})().catch((e) => { console.error('실패:', e); process.exit(1); });
