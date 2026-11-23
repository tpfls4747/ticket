#!/usr/bin/env node
/* STEP 3A 화면 전환 자동 테스트.
 * 사용법: node tools/test_nav.cjs <번들.html> [결과 JSON 경로]
 *
 * 검사:
 *  1. 링크 클릭: 모든 폰의 처음 화면에 있는 모든 링크를 실제 마우스로 눌러
 *     - 목적지가 이 보드에 있으면 그 화면이 보이는지, 없으면 현재 화면이 유지되는지
 *     - 프레임이 about:blank#blocked 등으로 이동하지 않는지
 *     매 클릭 후 Esc 로 처음 화면 복귀도 함께 확인한다.
 *  2. 뒤로: 다음 → 다음 → 뒤로 → 뒤로 가 기록대로 돌아오는지
 *  3. 키보드: Tab 으로 링크에 포커스 → Enter 로 이동되는지
 *  4. 입력 상태 보존: 라디오를 바꾼 뒤 다른 화면에 다녀와도 선택이 유지되는지
 *  5. 콘솔 오류·경고, 페이지 오류, 차단된 이동 이벤트가 0인지
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const file = process.argv[2];
const outJson = process.argv[3];
const results = [];
const ok = (name, pass, detail) => { results.push({ name, pass, detail: detail || '' }); };

(async () => {
  const launch = { args: ['--disable-gpu'] };
  if (process.env.HTTPS_PROXY) launch.proxy = { server: process.env.HTTPS_PROXY };
  const b = await chromium.launch(launch);
  const ctx = await b.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  const problems = [];
  page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) problems.push(m.type() + ': ' + m.text().slice(0, 160)); });
  page.on('pageerror', (e) => problems.push('pageerror: ' + String(e).slice(0, 160)));
  page.on('framenavigated', (f) => { if (/about:blank#blocked/.test(f.url())) problems.push('blocked navigation: ' + f.url()); });
  await page.goto('file://' + path.resolve(file));
  await page.waitForSelector('section.board iframe');
  const titles = await page.$$eval('section.board h2', (a) => a.map((x) => x.textContent));
  const handles = await page.$$('section.board iframe');
  const frames = [];
  for (const h of handles) frames.push(await h.contentFrame());
  await page.waitForTimeout(8000);

  const visible = (f, host) => f.evaluate((h) => {
    const el = document.querySelector('[data-nav-host="' + h + '"]');
    const vis = [...el.querySelectorAll(':scope > [data-nav-screen]')].filter((c) => getComputedStyle(c).display !== 'none');
    return vis.map((c) => c.getAttribute('data-nav-screen'));
  }, host);
  const hostInfo = (f) => f.evaluate(() => [...document.querySelectorAll('[data-nav-host]')].map((h) => ({
    screens: [...h.querySelectorAll(':scope > [data-nav-screen]')].map((c) => c.getAttribute('data-nav-screen')),
  })));
  const linksOnVisible = (f, host) => f.evaluate((h) => {
    const el = document.querySelector('[data-nav-host="' + h + '"]');
    const vis = [...el.querySelectorAll(':scope > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
    return [...vis.querySelectorAll('a[href]')].map((a, k) => ({ k, href: a.getAttribute('href'), label: a.getAttribute('aria-label') || a.textContent.trim().slice(0, 20) }));
  }, host);
  const clickLink = async (fi, host, k) => {
    const f = frames[fi];
    await handles[fi].evaluate((e) => e.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(150);
    const el = await f.evaluateHandle(([h, kk]) => {
      const host = document.querySelector('[data-nav-host="' + h + '"]');
      const vis = [...host.querySelectorAll(':scope > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
      return vis.querySelectorAll('a[href]')[kk];
    }, [host, k]);
    const ae = el.asElement();
    if (!ae) return false;
    const box = await ae.boundingBox();
    await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
    await page.waitForTimeout(350);
    return true;
  };
  const pressEsc = async () => { await page.keyboard.press('Escape'); await page.waitForTimeout(300); };
  const graph = [];

  /* ---- 1. 모든 링크 ---- */
  for (let fi = 0; fi < frames.length; fi++) {
    const f = frames[fi];
    const hosts = await hostInfo(f);
    for (let h = 0; h < hosts.length; h++) {
      const start = (await visible(f, h))[0];
      const links = await linksOnVisible(f, h);
      for (const ln of links) {
        const urlBefore = f.url();
        await clickLink(fi, h, ln.k);
        const after = await visible(f, h);
        const m = /^([A-Za-z0-9_-]+)\.dc\.html$/.exec(ln.href);
        const target = m ? m[1] : null;
        const available = target && hosts[h].screens.includes(target);
        const isBack = ln.label === '뒤로';
        // 처음 화면에서의 '뒤로'는 이전 기록이 없으므로 링크 목적지로 간다(목적지가 있을 때)
        const expected = available ? target : start;
        const pass = f.url() === urlBefore && after.length === 1 && after[0] === expected;
        graph.push({ board: titles[fi], host: h, from: start, link: ln.label, href: ln.href, to: after[0], result: available ? '이동' : '현재 화면 유지(이 보드에 없는 화면)', pass });
        ok('링크 ' + titles[fi].split(' ')[0] + ' 폰' + (h + 1) + ' [' + start + '] ' + ln.label + ' → ' + (target || '?'), pass,
          '기대 ' + expected + ', 결과 ' + after.join(',') + (isBack ? ' (뒤로)' : ''));
        await pressEsc();
        const reset = await visible(f, h);
        ok('Esc 초기화 ' + titles[fi].split(' ')[0] + ' 폰' + (h + 1) + ' (' + ln.label + ' 이후)', reset[0] === start, '결과 ' + reset.join(','));
      }
    }
  }

  /* ---- 2. 뒤로 (P07 보드 폰1: 예매 상세 → 조건 등록 → 신청 현황 → 뒤로 → 뒤로) ---- */
  const fiEx = titles.findIndex((t) => t.startsWith('P07 UI'));
  {
    const f = frames[fiEx];
    const seq = [];
    const clickByLabel = async (label) => {
      const links = await linksOnVisible(f, 0);
      const ln = links.find((l) => l.label === label);
      if (!ln) { seq.push('링크 없음:' + label); return; }
      await clickLink(fiEx, 0, ln.k);
      seq.push((await visible(f, 0))[0]);
    };
    await clickByLabel('좌석·회차 교환 신청');
    await clickByLabel('교환 신청 등록');
    await clickByLabel('뒤로');
    await clickByLabel('뒤로');
    ok('뒤로: 기록대로 돌아오기', JSON.stringify(seq) === JSON.stringify(['Request', 'Waiting', 'Request', 'Main']), JSON.stringify(seq));
    await pressEsc();
  }

  /* ---- 3. 키보드: Tab 으로 링크에 포커스 후 Enter ---- */
  {
    const f = frames[fiEx];
    await handles[fiEx].evaluate((e) => e.scrollIntoView({ block: 'center' }));
    await f.evaluate(() => { document.body.tabIndex = -1; document.body.focus(); });
    let reached = null;
    for (let k = 0; k < 6; k++) {
      await page.keyboard.press('Tab');
      reached = await f.evaluate(() => { const a = document.activeElement; return a && a.tagName === 'A' ? (a.getAttribute('aria-label') || a.textContent.trim()) : null; });
      if (reached === '좌석·회차 교환 신청') break;
    }
    await page.keyboard.press('Enter');
    await page.waitForTimeout(350);
    const after = (await visible(f, 0))[0];
    ok('키보드: Tab 으로 링크 포커스 → Enter 이동', reached === '좌석·회차 교환 신청' && after === 'Request', '포커스 ' + reached + ', 결과 ' + after);
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    ok('키보드: Esc 로 처음 화면', (await visible(f, 0))[0] === 'Main', (await visible(f, 0))[0]);
  }

  /* ---- 4. 입력 상태 보존 (P08 연석 보드 폰1: 교환 방식 라디오) ---- */
  const fiPair = titles.findIndex((t) => t.startsWith('P08 UI'));
  {
    const f = frames[fiPair];
    const radios = () => f.evaluate(() => {
      const host = document.querySelector('[data-nav-host="0"] [data-nav-screen="PairMode"]');
      return [...host.querySelectorAll('input[name=mode]')].map((r) => r.checked);
    });
    const before = await radios();
    // 첫 번째 라디오(좌석·회차 교환) 선택
    await handles[fiPair].evaluate((e) => e.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(150);
    const r0 = await f.evaluateHandle(() => document.querySelector('[data-nav-host="0"] [data-nav-screen="PairMode"] input[name=mode]'));
    const rb = await r0.asElement().boundingBox();
    await page.mouse.click(rb.x + rb.width / 2, rb.y + rb.height / 2);
    await page.waitForTimeout(250);
    const changed = await radios();
    // 다음 화면으로 갔다가 뒤로
    const links = await linksOnVisible(f, 0);
    const next = links.find((l) => l.href === 'PairSeat.dc.html');
    await clickLink(fiPair, 0, next.k);
    const mid = (await visible(f, 0))[0];
    const back = (await linksOnVisible(f, 0)).find((l) => l.label === '뒤로');
    await clickLink(fiPair, 0, back.k);
    const end = (await visible(f, 0))[0];
    const kept = await radios();
    ok('입력 보존: 라디오 선택 후 다른 화면에 다녀와도 유지', JSON.stringify(changed) !== JSON.stringify(before) && mid === 'PairSeat' && end === 'PairMode' && JSON.stringify(kept) === JSON.stringify(changed),
      '처음 ' + JSON.stringify(before) + ' → 선택 ' + JSON.stringify(changed) + ' → ' + mid + ' → ' + end + ' → ' + JSON.stringify(kept));
    // 전환 이후 입력이 계속 동작하는지 (두 번째 라디오로 다시 바꾸기)
    const r1 = await f.evaluateHandle(() => document.querySelectorAll('[data-nav-host="0"] [data-nav-screen="PairMode"] input[name=mode]')[1]);
    const rb1 = await r1.asElement().boundingBox();
    await page.mouse.click(rb1.x + rb1.width / 2, rb1.y + rb1.height / 2);
    await page.waitForTimeout(250);
    const again = await radios();
    ok('전환 이후 입력 요소 동작', JSON.stringify(again) === JSON.stringify([false, true]), JSON.stringify(again));
    await pressEsc();
  }

  /* ---- 4-2. 기존 <button>(type 없음 = 제출 버튼) 이 폼 제출·이동을 일으키지 않는지 ---- */
  {
    const f = frames[fiEx];
    await handles[fiEx].evaluate((e) => e.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(150);
    const btn = await f.evaluateHandle(() => [...document.querySelectorAll('[data-nav-host="2"] [data-nav-screen="Waiting"] button')]
      .find((x) => x.textContent.trim() === '교환 신청 취소'));
    const urlBefore = f.url();
    const bb = await btn.asElement().boundingBox();
    await page.mouse.click(bb.x + bb.width / 2, bb.y + bb.height / 2);
    await page.waitForTimeout(400);
    ok('기존 버튼 클릭 시 제출·이동 없음 (교환 신청 취소)', f.url() === urlBefore && (await visible(f, 2))[0] === 'Waiting', f.url().slice(0, 30));
  }
  /* ---- 4-3. 같은 화면이 여러 폰에 있어도 라디오 그룹이 섞이지 않는지 (P08 연석 보드의 기본 선택) ---- */
  {
    const f = frames[fiPair];
    const st = await f.evaluate(() => [...document.querySelectorAll('[data-nav-host] [data-nav-screen="PairSeat"]')]
      .map((s) => [...s.querySelectorAll('input[name=dir]')].map((r) => r.checked)));
    const allDefault = st.every((g) => JSON.stringify(g) === JSON.stringify([true, false]));
    ok('복제된 화면의 라디오 그룹이 서로 섞이지 않음 (PairSeat 기본 선택이 모두 유지)', allDefault, JSON.stringify(st));
  }

  /* ---- 5. 오류 ---- */
  const allBlob = frames.every((f) => f.url().startsWith('blob:'));
  ok('모든 보드 프레임이 blob 문서에 머무름 (빈 화면 이동 없음)', allBlob, frames.filter((f) => !f.url().startsWith('blob:')).map((f) => f.url()).join(', '));
  ok('콘솔 오류·경고, 페이지 오류, 차단된 이동 0건', problems.length === 0, problems.slice(0, 5).join(' | '));

  await b.close();
  const fail = results.filter((r) => !r.pass);
  for (const r of results) console.log((r.pass ? 'PASS ' : 'FAIL ') + r.name + (r.pass ? '' : '  — ' + r.detail));
  console.log('\n합계 %d건, 실패 %d건', results.length, fail.length);
  if (outJson) fs.writeFileSync(outJson, JSON.stringify({ results, graph }, null, 1));
  process.exit(fail.length ? 1 : 0);
})().catch((e) => { console.error('테스트 실행 실패:', e); process.exit(2); });
