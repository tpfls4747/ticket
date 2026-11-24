#!/usr/bin/env node
/* STEP 4B 시각 다듬기 검증 (실제 마우스·키보드 입력). 사용법: node tools/test_ux_4b.cjs <번들.html> [결과 JSON] [스크린샷 디렉터리]
 *
 * 1 보드 16개 · 2 화면 확대 보기(가독성·상태 유지·조작·Esc·포커스 복귀·Tab 순환·이전/다음) · 3 A·B 함께 크게 보기
 * 4 시연 제어판 통일(P08=P12) · 5 수신자 상태별 제목·CTA = 엔진 · 6 공용 단계 표시 · 7 정보 위계 · 8 P13 설명용 화면 · 9 정적 보드 확대
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const P = require('./authoring/demo3c_pair.js');

const file = path.resolve(process.argv[2]);
const outJson = process.argv[3];
const shotDir = process.argv[4];
const results = [];
let journey = '';
const ok = (name, pass, detail) => results.push({ journey, name, pass: !!pass, detail: pass ? '' : String(detail || '') });

(async () => {
  const launch = { args: ['--disable-gpu', '--font-render-hinting=none', '--disable-lcd-text', '--force-color-profile=srgb'] };
  if (process.env.HTTPS_PROXY) launch.proxy = { server: process.env.HTTPS_PROXY };
  const browser = await chromium.launch(launch);
  if (shotDir) fs.mkdirSync(shotDir, { recursive: true });
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  const problems = [];
  page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) problems.push(m.type() + ': ' + m.text().slice(0, 160)); });
  page.on('pageerror', (e) => problems.push('pageerror: ' + String(e).slice(0, 160)));
  page.on('requestfailed', (r) => problems.push('requestfailed: ' + r.url().slice(0, 120)));
  await page.goto('file://' + file);
  await page.waitForSelector('section.board iframe');
  const titles = await page.$$eval('section.board', (a) => a.map((x) => x.dataset.board))  // STEP 4C-2A: 보드 표시 이름 대신 바뀌지 않는 식별자(slug)로 찾는다;
  const handles = await page.$$('section.board iframe');
  await page.waitForTimeout(9000);

  async function board(prefix) {
    const idx = titles.findIndex((t) => t.startsWith(prefix));
    const handle = handles[idx];
    const f = await handle.contentFrame();
    await handle.evaluate((e) => e.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(400);
    const visJs = (h) => `[...document.querySelectorAll('[data-nav-host="${h}"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none')`;
    const H = {
      f, handle,
      async clickEl(e) {
        await handle.evaluate((x) => x.scrollIntoView({ block: 'center' }));
        await f.evaluate(() => document.querySelectorAll('[data-zoom-host]').forEach((x) => { if (x.parentElement) x.parentElement.scrollTop = 0; }));
        await page.waitForTimeout(100);
        const b = await e.boundingBox();
        await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
        await page.waitForTimeout(400);
      },
      async click(scope, sel, text) {
        const e = (await f.evaluateHandle(([js, s, tx]) => {
          const root = js === 'panel' ? document.querySelector('[data-demo-ctl]') : js === 'zoom' ? document.querySelector('[data-zoom-ctl]') : js === 'doc' ? document : eval(js);
          return [...root.querySelectorAll(s)].find((x) => !tx || x.textContent.trim() === tx || x.getAttribute('aria-label') === tx) || null;
        }, [typeof scope === 'number' ? visJs(scope) : scope, sel, text || null])).asElement();
        if (!e) throw new Error('요소 없음: ' + scope + ' ' + sel + ' ' + (text || ''));
        await H.clickEl(e);
      },
      screen: (h) => f.evaluate((js) => { const v = eval(js); return v ? v.getAttribute('data-nav-screen') : null; }, visJs(h)),
      text: (h) => f.evaluate((js) => { const v = eval(js); return v ? v.innerText.replace(/\s+/g, ' ') : ''; }, visJs(h)),
      zoomed: () => f.evaluate(() => [...document.querySelectorAll('[data-zoom-host]')].filter((e) => getComputedStyle(e).position === 'fixed').map((e) => +e.getAttribute('data-zoom-host'))),
      rect: (i) => f.evaluate((k) => { const r = document.querySelector('[data-zoom-host="' + k + '"]').getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; }, i),
      active: () => f.evaluate(() => { const a = document.activeElement; if (!a) return null; const z = a.closest('[data-zoom-host]'); return z ? 'host' + z.getAttribute('data-zoom-host') : a.closest('[data-zoom-ctl]') ? 'zoomctl' : a.getAttribute('data-zoom-btn') !== null ? 'btn' + a.getAttribute('data-zoom-btn') : a.tagName; }),
      async key(k) { await page.keyboard.press(k); await page.waitForTimeout(350); },
      async shot(name) { if (shotDir) await page.screenshot({ path: path.join(shotDir, name + '.png'), clip: await handle.boundingBox() }); },
    };
    return H;
  }
  // 확대된 폰에서 실제로 보이는 가장 작은 글자 크기 (CSS px × 배율)
  const minFont = (H, i) => H.f.evaluate((k) => {
    const host = document.querySelector('[data-zoom-host="' + k + '"]');
    const scale = host.getBoundingClientRect().width / 390;
    const vis = [...host.querySelectorAll(':scope > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none') || host;
    let min = 99;
    vis.querySelectorAll('*').forEach((e) => { if (e.childNodes.length && [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()) && e.offsetParent !== null) min = Math.min(min, parseFloat(getComputedStyle(e).fontSize)); });
    return Math.round(min * scale * 10) / 10;
  }, i);

  /* ---------------------------------------------------------------- 1. 보드 */
  journey = '1 보드 구성';
  ok('보드 16개 유지', titles.length === 16, titles.length);

  /* ---------------------------------------------------------------- 2. 확대 보기 (P12 신청자 A) */
  journey = '2 화면 확대 보기';
  {
    const H = await board('p08-ui-pair');
    const before = await minFont(H, 0);
    ok('확대 전: 보드 위 최소 글자 크기가 작음 (0.58배)', before < 7, before);
    await H.shot('00-p12-board');
    await H.click('doc', '[data-zoom-btn="0"]');
    ok('크게 보기 버튼 → A 폰만 확대', JSON.stringify(await H.zoomed()) === '[0]', await H.zoomed());
    const r = await H.rect(0);
    ok('확대 크기 = 실제 폰 크기 390×844 (보드 1920×1080 안)', r[2] === 390 && r[3] === 844 && r[0] >= 0 && r[0] + r[2] <= 1920 && r[1] + r[3] <= 1080, r);
    const after = await minFont(H, 0);
    ok('확대 후 최소 글자 크기 ≥ 11px (확대 전 ' + before + 'px)', after >= 11, after);
    const tf = await H.f.evaluate(() => getComputedStyle(document.querySelector('[data-zoom-host="0"]')).transform);
    ok('확대 화면은 배율 변환 없이 그려짐 (흐림 없음)', tf === 'none', tf);
    ok('확대 시 포커스가 폰으로 이동', (await H.active()) === 'host0', await H.active());
    await H.shot('01-zoom-a');
    // 확대 상태에서 조작 → 닫아도 상태 유지
    await H.click(0, 'a[data-act="next"]');
    ok('확대 상태에서 조작 가능 (다음 → 유지할 좌석 화면)', (await H.screen(0)) === 'PairSeat', await H.screen(0));
    // Tab 순환: 확대된 폰과 확대 패널 안에서만
    const seen = new Set();
    for (let k = 0; k < 14; k++) { await H.key('Tab'); seen.add((await H.active()) || ''); }
    ok('Tab 이 확대 영역(폰·패널) 안에서만 순환', [...seen].every((s) => s === 'host0' || s === 'zoomctl'), [...seen]);
    await H.key('Escape');
    ok('Esc → 확대 닫힘', (await H.zoomed()).length === 0);
    ok('닫은 뒤 포커스 = 해당 폰의 크게 보기 버튼', (await H.active()) === 'btn0', await H.active());
    ok('닫아도 체험 상태 유지 (PairSeat, Esc 로 초기화되지 않음)', (await H.screen(0)) === 'PairSeat', await H.screen(0));
    const s = await H.f.evaluate(() => getComputedStyle(document.querySelector('[data-zoom-host="0"]')).transform);
    ok('닫으면 보드 배율(0.58) 복귀', /matrix\(0\.58/.test(s), s);
    // 이전·다음 (보드 순서: A → B → 예시 → 예시)
    await H.click('doc', '[data-zoom-btn="0"]');
    await H.click('zoom', 'button', '다음 화면 →');
    ok('다음 화면 → 수신자 B (보드 순서대로)', JSON.stringify(await H.zoomed()) === '[2]', await H.zoomed());
    ok('확대 패널에 역할 표시 (수신자 B · 체험)', (await H.f.evaluate(() => document.querySelector('[data-zoom-ctl]').innerText)).includes('수신자 B · 체험'));
    await H.click('zoom', 'button', '닫기 (Esc)');
    ok('닫기 버튼 → 닫힘', (await H.zoomed()).length === 0);
    await H.click('doc', '[data-zoom-btn="1"]');
    const bd = await (await H.f.$('[data-zoom-backdrop]')).boundingBox();   // 가운데는 확대된 폰이 덮으므로 빈 모서리를 누른다
    await page.mouse.click(bd.x + 20, bd.y + bd.height - 20);
    await page.waitForTimeout(400);
    ok('배경 클릭 → 닫힘', (await H.zoomed()).length === 0);
    await H.key('Escape');
  }

  /* ---------------------------------------------------------------- 3. A·B 함께 크게 보기 + 수신자 상태 */
  journey = '3 A·B 함께 보기 · 수신자 상태';
  {
    const H = await board('p08-ui-pair');
    await H.f.evaluate(() => document.querySelector('[data-nav-host="0"]').focus());
    await H.key('Escape');   // 체험 초기화
    await H.click('panel', 'button', 'A·B 함께 크게 보기');
    const z = await H.zoomed();
    const ra = await H.rect(0), rb = await H.rect(2);
    ok('제어판 → A·B 두 폰을 나란히 실제 크기로', JSON.stringify(z) === '[0,2]' && ra[2] === 390 && rb[2] === 390 && rb[0] > ra[0] + 390 && ra[1] === rb[1], JSON.stringify([z, ra, rb]));
    // 확대 상태에서 A·B 를 오가며 체험
    await H.click(2, 'input[data-act="intent"][data-val="on"]');
    await H.click(2, 'button', '설정 저장');
    await H.click(0, 'a[data-act="next"]');
    await H.click(0, 'a[data-act="toCandidates"]');
    await H.click(0, '[data-act="choose"][data-val="11-5"]');
    await H.click(0, 'button', '선택한 후보와 최종 비교하기');
    await H.click(0, 'input[data-act="ack"]');
    await H.click(0, 'button', '11열 5번 관객에게 교환 제안 보내기');
    let tb = await H.text(2);
    ok('제안 도착: 수신자 설정 화면에 "새 교환 제안이 도착했어요" 카드 (아직 열어보지 않음)', (await H.screen(2)) === 'PairIntent' && tb.includes('새 교환 제안이 도착했어요') && tb.includes('새 제안'), tb.slice(0, 200));
    await H.shot('02-ab-zoom-arrived');
    const states = [];
    const check = async (label, eng) => {
      const t = await H.text(2);
      const pass = t.includes(eng.statusBadge) && t.includes(eng.title);
      states.push(label);
      ok('수신자 상태 "' + label + '": 화면 = 엔진 (배지 ' + eng.statusBadge + ' · 제목 ' + eng.title + ')', pass, t.slice(0, 260));
      return t;
    };
    const st = Object.assign(P.initialState(), { consent: true, intentDraft: true, cand: '11-5', step: 'proposed', bSeen: true });
    await H.click(2, 'button', '제안 검토하기 →');
    tb = await check('검토 중', P.views(st, true).receive);
    ok('검토 중 CTA: 거절 · 제안 수락', !!(await H.f.evaluate(() => [...document.querySelectorAll('[data-nav-host="2"] button')].some((b) => b.textContent.trim() === '제안 수락' && b.offsetParent !== null))));
    await H.shot('03-receive-reviewing');
    await H.click(2, 'button', '제안 수락');
    tb = await check('수락함', P.views(Object.assign({}, st, { step: 'accepted' }), true).receive);
    ok('수락함 CTA: 응답 버튼 대신 대기 상태 문구', tb.includes('응답 완료 · 예매처 최종 확인을 기다리는 중') && !tb.includes('제안 수락 거절'), tb.slice(-200));
    await H.shot('04-receive-accepted');
    await H.click('zoom', 'button', '닫기 (Esc)');
    await H.click('panel', 'button', '최종 확인 시작');
    tb = await check('최종 확인 중', P.views(Object.assign({}, st, { step: 'final' }), true).receive);
    await H.click('panel', 'button', '최종 확인 성공');
    tb = await check('교환 완료', P.views(Object.assign({}, st, { step: 'done' }), true).receive);
    ok('교환 완료 CTA: 설정 화면으로 돌아가기', tb.includes('설정 화면으로 돌아가기'), tb.slice(-120));
    await H.shot('05-board-done');
    ok('수신자 단계 표시: 교환 완료 = 모든 단계 완료', tb.includes('모든 단계 완료'), tb.slice(0, 160));
    // 거절·실패·취소 상태
    for (const [label, acts, step] of [['거절함', ['거절'], 'declined'], ['교환 실패', ['제안 수락', 'P:최종 확인 시작', 'P:최종 확인 실패'], 'failed'], ['신청자 취소', ['A:제안 취소하기'], 'cancelled']]) {
      await H.f.evaluate(() => document.querySelector('[data-nav-host="0"]').focus());
      await H.key('Escape');
      await H.click(2, 'input[data-act="intent"][data-val="on"]');
      await H.click(2, 'button', '설정 저장');
      await H.click(0, 'a[data-act="next"]');
      await H.click(0, 'a[data-act="toCandidates"]');
      await H.click(0, '[data-act="choose"][data-val="11-5"]');
      await H.click(0, 'button', '선택한 후보와 최종 비교하기');
      await H.click(0, 'input[data-act="ack"]');
      await H.click(0, 'button', '11열 5번 관객에게 교환 제안 보내기');
      await H.click(2, 'button', '제안 검토하기 →');
      for (const a of acts) {
        if (a.startsWith('P:')) await H.click('panel', 'button', a.slice(2));
        else if (a.startsWith('A:')) await H.click(0, 'button', a.slice(2));
        else await H.click(2, 'button', a);
      }
      await check(label, P.views(Object.assign({}, st, { step }), true).receive);
      if (label === '교환 실패') await H.shot('06-receive-failed');
    }
    ok('수신자 상태 7종 + 신청자 취소 모두 확인', states.length === 7, states);
    await H.f.evaluate(() => document.querySelector('[data-nav-host="0"]').focus());
    await H.key('Escape');
  }

  /* ---------------------------------------------------------------- 4. 시연 제어판 통일 */
  journey = '4 시연 제어판 통일';
  {
    const sig = async (prefix) => {
      const H = await board(prefix);
      return H.f.evaluate(() => {
        const p = document.querySelector('[data-demo-ctl]');
        const cs = getComputedStyle(p);
        const r = p.getBoundingClientRect();
        return { pos: cs.position, right: cs.right, top: cs.top, width: Math.round(r.width), border: cs.borderStyle + ' ' + cs.borderWidth, bg: cs.backgroundColor, radius: cs.borderRadius,
          rows: p.children.length, head: p.children[0].innerText.replace(/\s+/g, ' '), labels: [...p.querySelectorAll('span')].map((s) => s.textContent).filter((x) => x === '시나리오' || x === '조작'),
          inPhone: !!p.closest('[data-nav-host]'), reset: [...p.querySelectorAll('button')].some((b) => b.textContent.trim() === '처음부터 다시') };
      });
    };
    const a = await sig('p07-ui-exchange'), b = await sig('p08-ui-pair');
    const keys = ['pos', 'right', 'top', 'width', 'border', 'bg', 'radius', 'rows'];
    ok('P08·P12 제어판 위치·크기·테두리·배경·구조 동일', keys.every((k) => a[k] === b[k]), JSON.stringify([a, b]));
    ok('두 제어판 모두 "시연용 제어 · 실제 서비스 기능이 아니에요" · 시나리오·조작 행 · 처음부터 다시', [a, b].every((x) => x.head.includes('시연용 제어') && x.head.includes('실제 서비스 기능이 아니에요') && x.labels.length === 2 && x.reset && !x.inPhone), JSON.stringify([a.head, b.head]));
    for (const pre of ['p07b-conditions-match', 'p07c-status', 'p07d-exceptions', 'p08b-pair-states']) {
      const H = await board(pre);
      const s = await H.f.evaluate(() => { const e = document.querySelector('[aria-label="설명용 화면 안내"]'); if (!e) return null; const cs = getComputedStyle(e); return [cs.position, cs.right, e.innerText]; });
      ok(pre.split(' ')[0] + ' 정적 보드: 같은 자리(오른쪽 위)에 설명용 표시', s && s[0] === 'absolute' && s[1] === a.right && /직접 체험은 (08|10)장/.test(s[2])  /* STEP 4C-2A: 새 장 번호 */, JSON.stringify(s));
    }
  }

  /* ---------------------------------------------------------------- 5. 공용 단계 표시 */
  journey = '5 공용 단계 표시';
  {
    const G = await board('p07-ui-exchange');
    await G.click(0, 'a', '좌석·회차 교환 신청');
    const sg = await G.f.evaluate(() => { const v = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
      const g = v.querySelector('[role="group"][aria-label^="진행 단계"]'); return g ? [g.getAttribute('aria-label'), g.querySelectorAll('li').length, g.querySelectorAll('li[aria-current="step"]').length, g.innerText.replace(/\s+/g, ' ')] : null; });
    ok('일반 교환 조건 등록: "단계 1/6 · 조건 등록" · 6단계 · 현재 단계 1개(aria-current)', sg && sg[0].includes('단계 1/6 · 조건 등록') && sg[1] === 6 && sg[2] === 1, JSON.stringify(sg));
    ok('단계마다 스크린 리더용 상태 문구', sg && sg[3].includes('1단계 조건 등록: 현재 단계') && sg[3].includes('2단계 후보 확인: 남은 단계'), sg && sg[3]);
    await G.f.evaluate(() => document.querySelector('[data-nav-host="0"]').focus());
    await G.key('Escape');
    const H = await board('p08-ui-pair');
    await H.click(2, 'input[data-act="intent"][data-val="on"]');
    await H.click(2, 'button', '설정 저장');
    await H.click(0, 'a[data-act="next"]');
    await H.click(0, 'a[data-act="toCandidates"]');
    let t = await H.text(0);
    ok('연석 후보 화면: 같은 컴포넌트 "단계 3/6 · 인접 확인" (인접 확인 단계 유지)', t.includes('단계 3/6 · 인접 확인') && t.includes('3단계 인접 확인: 현재 단계') && t.includes('5단계 상대 수락: 남은 단계'), t.slice(0, 200));
    await H.click(0, '[data-act="choose"][data-val="11-5"]');
    await H.click(0, 'button', '선택한 후보와 최종 비교하기');
    await H.click(0, 'input[data-act="ack"]');
    await H.click(0, 'button', '11열 5번 관객에게 교환 제안 보내기');
    await H.click(2, 'button', '제안 검토하기 →');
    await H.click(2, 'button', '거절');
    t = await H.text(0);
    ok('거절 화면: 상대 수락 단계에 실패 표시 (텍스트로도)', t.includes('5단계 상대 수락: 실패') && t.includes('제안을 거절했어요'), t.slice(0, 220));
    await H.shot('07-declined-stepper');
    await H.f.evaluate(() => document.querySelector('[data-nav-host="0"]').focus());
    await H.key('Escape');
  }

  /* ---------------------------------------------------------------- 6. 정보 위계 */
  journey = '6 비교표·후보 카드 정보 위계';
  {
    const G = await board('p07-ui-exchange');
    await G.click(0, 'a', '좌석·회차 교환 신청');
    await G.click(0, 'a', '교환 신청 등록');
    await G.click(0, '[data-act="notify"]');
    const m = await G.f.evaluate(() => { const v = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
      const d = v.querySelector('details'); return { t: v.innerText.replace(/\s+/g, ' '), open: d ? d.open : null, sum: d ? d.querySelector('summary').textContent : '' }; });
    const order = ['12.21 (월) 14:00 · 4회차', 'R석 A구역 5열 8번', '필수 조건: 양쪽 모두 충족', '선호 조건 차이', '미확인 2건'].map((s) => m.t.indexOf(s));
    ok('양방향 확인: 공연·회차 → 교환 전후 좌석 → 필수 충족 → 선호 차이 → 상태 순서', order.every((x, k) => x >= 0 && (k === 0 || x > order[k - 1])), JSON.stringify(order));
    ok('양방향 확인: 전체 조건은 접힘 (조건 전체 보기)', m.open === false && m.sum.includes('조건 전체 보기'), JSON.stringify([m.open, m.sum]));
    await G.shot('08-matchcheck');
    await G.click(0, '[data-act="toCompare"]');
    const c = await G.f.evaluate(() => { const v = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].find((x) => getComputedStyle(x).display !== 'none');
      const d = v.querySelector('details'); return { t: v.innerText.replace(/\s+/g, ' '), open: d.open, sum: d.querySelector('summary').textContent }; });
    ok('전후 비교: 받을 티켓 좌석이 맨 위 · 달라지는 항목 먼저 · 같은 항목은 접힘', c.t.indexOf('R석 A구역 5열 8번') < c.t.indexOf('달라지는 항목') && c.open === false && c.sum === '같은 항목 2개 보기' && !c.t.includes('캐스팅'), c.t.slice(0, 300));
    await G.shot('09-compare');
    await G.click(0, 'summary', '같은 항목 2개 보기');
    ok('같은 항목 펼치기 (상세 보기)', (await G.text(0)).includes('캐스팅 해당 없음 해당 없음 같음'));
    await G.f.evaluate(() => document.querySelector('[data-nav-host="0"]').focus());
    await G.key('Escape');
    const H = await board('p08-ui-pair');
    await H.click(2, 'input[data-act="intent"][data-val="on"]');
    await H.click(2, 'button', '설정 저장');
    await H.click(0, 'a[data-act="next"]');
    await H.click(0, 'a[data-act="toCandidates"]');
    const card = await H.f.evaluate(() => [...document.querySelectorAll('[data-nav-host="0"] section')].filter((s) => s.querySelector('[data-act="choose"]') && s.offsetParent !== null).map((s) => s.innerText.replace(/\s+/g, ' '))[0]);
    ok('후보 카드: 좌석 → 교환 결과(나란히) → 확인 칩 → 선택', card && card.indexOf('11열 5번 · 오른쪽') < card.indexOf('교환하면 11열 4번, 5번 나란히') && card.indexOf('교환하면') < card.indexOf('배치도상 옆자리 ✓') && card.indexOf('✓') < card.indexOf('이 후보 선택'), card);
    await H.f.evaluate(() => document.querySelector('[data-nav-host="0"]').focus());
    await H.key('Escape');
  }

  /* ---------------------------------------------------------------- 7. P13 설명용 화면 */
  journey = '7 P13 설명용 화면';
  {
    const H = await board('p08b-pair-states');
    const inputs = await H.f.evaluate(() => [...document.querySelectorAll('[data-zoom-host] input')].length);
    ok('P13 의 설명용 폰에는 입력 요소가 없음 (체크박스·라디오 → 그림)', inputs === 0, inputs);
    const t = await H.f.evaluate(() => document.body.innerText.replace(/\s+/g, ' '));
    ok('설명용 표시: "설명용 화면 · 체험은 10장" · 보내기 버튼은 비활성 + 이유', t.includes('설명용 화면 · 체험은 10장') && t.includes('위 내용을 확인했다고 선택하면 보낼 수 있어요'), '');
    await H.click('doc', '[data-zoom-btn="3"]');
    const r = await H.rect(3);
    ok('정적 보드도 크게 보기 (390×844)', r[2] === 390 && r[3] === 844, r);
    const help = await H.f.evaluate(() => document.querySelector('[data-zoom-ctl]').innerText);
    ok('정적 확대 패널: "설명용 정적 화면" 안내', help.includes('설명용 정적 화면'), help);
    await H.shot('10-p13-zoom');
    await H.key('Escape');
    ok('Esc → 닫힘, 포커스 복귀', (await H.zoomed()).length === 0 && (await H.active()) === 'btn3', await H.active());
  }

  /* ---------------------------------------------------------------- 8. 다른 정적 보드 확대 */
  journey = '8 정적 보드 확대';
  for (const pre of ['p07b-conditions-match', 'p07c-status', 'p07d-exceptions']) {
    const H = await board(pre);
    await H.click('doc', '[data-zoom-btn="0"]');
    const r = await H.rect(0);
    ok(pre.split(' ')[0] + ' 1번 폰 크게 보기 (390×844)', r[2] === 390 && r[3] === 844, r);
    await H.click('zoom', 'button', '다음 화면 →');
    ok(pre.split(' ')[0] + ' 다음 화면 → 2번 폰', JSON.stringify(await H.zoomed()) === '[1]', await H.zoomed());
    await H.key('Escape');
    ok(pre.split(' ')[0] + ' Esc 로 닫힘', (await H.zoomed()).length === 0);
  }

  journey = '공통';
  ok('콘솔 오류·경고·리소스 로드 실패 0건', problems.length === 0, problems.join(' | '));
  await browser.close();
  const fail = results.filter((r) => !r.pass);
  let cur = '';
  for (const r of results) {
    if (r.journey !== cur) { cur = r.journey; console.log('\n[' + cur + ']'); }
    console.log((r.pass ? '  PASS ' : '  FAIL ') + r.name + (r.pass ? '' : '  — ' + r.detail.slice(0, 400)));
  }
  console.log('\n합계 %d건, 실패 %d건', results.length, fail.length);
  if (outJson) fs.writeFileSync(outJson, JSON.stringify(results, null, 1));
  process.exit(fail.length ? 1 : 0);
})().catch((e) => { console.error('테스트 실행 실패:', e); process.exit(2); });
