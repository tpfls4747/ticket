#!/usr/bin/env node
/* STEP 4C-2A 구성 검증: 보드 16장 보존 · 본문/부록 순서 · 번호·푸터·목차 일치 · 자리표시자/내부 메모 비노출 · 보드 참조 문구
 * 사용법: node tools/test_story_4c2a.cjs <번들.html>
 */
const path = require('path');
const { chromium } = require('playwright');

const ORDER = [
  ['p01-cover', '01', null], ['p02-overview', '02', null], ['p03-problem', '03', null], ['p04-desk-research', '04', null],
  ['p05-policy', '05', null], ['p06-user-flow', '06', null], ['p06b-state-flow', '07', null], ['p07-ui-exchange', '08', null],
  ['p07b-conditions-match', '09', null], ['p08-ui-pair', '10', null], ['p10-retrospective', '11', null],
  ['p07c-status', '12', 'A'], ['p07d-exceptions', '13', 'B'], ['p08b-pair-states', '14', 'C'], ['p09-components', '15', 'D'], ['p09b-state-components', '16', 'E'],
];
const BANNED = ['[이름]', '[연락처]', '[4주]', '[Figma', '[공연장명]', '[N]', 'STEP 2C', 'STEP 3', 'STEP 4', '(STEP', '/ 10', '06·07 보드', '07 보드', 'P06-B', 'P07-B', 'P07-C', 'P07-D', 'P08-B', 'P09-B',
  '먼저 수락한 1명', '모두 거절 → 방향', '클릭 전환은 아직 없어요', '엑셀 대조 전'];
let pass = 0, fail = 0;
const ok = (name, cond, detail) => { if (cond) { pass++; console.log('  PASS ' + name); } else { fail++; console.log('  FAIL ' + name + (detail !== undefined ? '  — ' + String(detail).slice(0, 300) : '')); } };

(async () => {
  const browser = await chromium.launch({ args: ['--disable-gpu'] });
  const page = await (await browser.newContext({ viewport: { width: 1920, height: 1080 } })).newPage();
  const errors = [];
  page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto('file://' + path.resolve(process.argv[2]));
  await page.waitForSelector('section.board iframe');
  await page.waitForTimeout(8000);

  console.log('[1 보드 보존과 순서]');
  const secs = await page.$$eval('section.board', (a) => a.map((s) => ({ slug: s.dataset.board, id: s.id, h2: s.querySelector('h2').textContent, title: s.querySelector('iframe').title })));
  ok('보드 16장 보존', secs.length === 16, secs.length);
  ok('본문 11 + 부록 5 표시 순서', JSON.stringify(secs.map((s) => s.slug)) === JSON.stringify(ORDER.map((o) => o[0])), secs.map((s) => s.slug).join(','));
  ok('보드 앵커 id = board-01 ~ board-16', secs.every((s, i) => s.id === 'board-' + ORDER[i][1]), secs.map((s) => s.id).join(','));
  ok('보드 이름 = 번호 · 이름 / 부록 X (번호) · 이름', secs.every((s, i) => (ORDER[i][2] ? s.h2.startsWith('부록 ' + ORDER[i][2] + ' (' + ORDER[i][1] + ') · ') : s.h2.startsWith(ORDER[i][1] + ' · ')) && s.h2 === s.title), secs.map((s) => s.h2).join(' | '));

  console.log('[2 목차]');
  const toc = await page.$$eval('nav.toc a', (a) => a.map((x) => ({ href: x.getAttribute('href'), text: x.textContent })));
  ok('목차 항목 16개', toc.length === 16, toc.length);
  ok('목차 링크가 모두 실제 보드를 가리킴 (본문 → 부록 순서)', toc.every((t, i) => t.href === '#board-' + ORDER[i][1]), toc.map((t) => t.href).join(','));
  ok('목차 번호 표기 = 보드 번호', toc.every((t, i) => t.text.startsWith(ORDER[i][2] ? '부록 ' + ORDER[i][2] : ORDER[i][1])), toc.map((t) => t.text).join(' | '));
  ok('목차에 체험형 표시 2개 (08·10장)', toc.filter((t) => t.text.includes('체험')).map((t) => t.href).join(',') === '#board-08,#board-10', toc.filter((t) => t.text.includes('체험')).map((t) => t.href).join(','));
  await page.click('nav.toc a[href="#board-13"]');
  await page.waitForTimeout(400);
  const y = await page.$eval('#board-13', (e) => Math.round(e.getBoundingClientRect().top));
  ok('목차 링크 클릭 → 해당 보드로 이동', y >= 0 && y < 80, y);

  console.log('[3 보드 번호·푸터]');
  const frames = [];
  for (const h of await page.$$('section.board iframe')) frames.push(await h.contentFrame());
  for (let i = 1; i < ORDER.length; i++) {
    const [slug, no, letter] = ORDER[i];
    const r = await frames[i].evaluate(() => {
      const big = [...document.querySelectorAll('span')].find((s) => getComputedStyle(s).fontSize === '128px');
      // 푸터의 쪽 번호 요소만 본다 (본문 글 속의 '본문 · 좌석 정보' 같은 글과 섞이지 않게)
      const spans = [...document.querySelectorAll('span')].filter((s) => /^(본문 · )?\d\d \/ \d\d$/.test(s.textContent.trim()));
      const f = spans[spans.length - 1];
      const m = f ? f.textContent.trim().match(/^(본문 · )?(\d\d) \/ (\d\d)$/) : null;
      const prev = f && f.previousElementSibling ? f.previousElementSibling.textContent : '';
      return { big: big ? big.textContent.trim() : null, foot: f ? f.textContent.trim() : null, num: m ? m[2] : null, total: m ? m[3] : null, appx: (prev.match(/^부록 ([A-E]) · /) || [])[1] || null, main: !!(m && m[1]) };
    });
    ok(no + ' ' + slug + ': 큰 번호 ' + (letter || no) + ' · 푸터 ' + no + ' / 16' + (letter ? ' · 부록 ' + letter : ' · 본문'),
      r.big === (letter || no) && r.num === no && r.total === '16' && (letter ? r.appx === letter && !r.main : r.main && !r.appx), JSON.stringify(r));
  }
  const stage = await frames[3].evaluate(() => (document.querySelector('[aria-current="step"]') || {}).textContent);
  ok('본문 푸터의 이야기 흐름: 04장 현재 단계 = 조사·인사이트', stage === '조사·인사이트', stage);

  console.log('[4 자리표시자·내부 메모 비노출]');
  const rootText = await page.evaluate(() => document.body.innerText + ' ' + [...document.querySelectorAll('iframe')].map((f) => f.title).join(' ') + ' ' + document.title);
  const found = [];
  for (let i = 0; i < frames.length; i++) {
    // 숨겨진 폰 화면까지 포함해 모든 글자 (textContent) — 시연 중 어떤 화면에도 나오지 않아야 한다
    const all = await frames[i].evaluate(() => { const c = document.body.cloneNode(true); c.querySelectorAll('script,style').forEach((n) => n.remove()); return c.textContent; });
    for (const b of BANNED) if (all.includes(b)) found.push(ORDER[i][1] + ':' + b);
  }
  for (const b of BANNED) if (rootText.includes(b)) found.push('root:' + b);
  ok('금지 표기 0건 (자리표시자·STEP 메모·옛 번호·옛 흐름·옛 회고 문구)', found.length === 0, found.join(', '));

  console.log('[5 보드 간 참조]');
  const refs = [];
  for (let i = 0; i < frames.length; i++) {
    const all = await frames[i].evaluate(() => document.body.innerText);
    for (const m of all.matchAll(/(\d\d)(?:·(\d\d))?장/g)) { refs.push([ORDER[i][1], m[1]]); if (m[2]) refs.push([ORDER[i][1], m[2]]); }
    for (const m of all.matchAll(/부록 ([A-Z])/g)) refs.push([ORDER[i][1], m[1]]);
  }
  const valid = new Set(ORDER.map((o) => o[1]).concat(['A', 'B', 'C', 'D', 'E']));
  ok('장·부록 참조가 모두 실제 보드를 가리킴 (참조 ' + refs.length + '건)', refs.length > 10 && refs.every((r) => valid.has(r[1])), refs.filter((r) => !valid.has(r[1])).join(' '));
  const demo = [];
  for (let i = 0; i < frames.length; i++) {
    const all = await frames[i].evaluate(() => document.body.innerText);
    for (const m of all.matchAll(/체험은 (\d\d)장/g)) demo.push(m[1]);
  }
  ok('"직접 체험" 안내는 체험형 보드(08 교환 · 10 연석)만 가리킴', demo.length >= 4 && demo.every((d) => d === '08' || d === '10'), demo.join(','));

  console.log('[6 콘솔]');
  ok('콘솔 오류·경고 0건', errors.length === 0, errors.join(' | '));
  await browser.close();
  console.log('합계 %d건, 실패 %d건', pass + fail, fail);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
