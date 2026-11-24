#!/usr/bin/env node
/* STEP 4A 사용자 흐름 검증 (실제 마우스·키보드 입력). 사용법: node tools/test_ux_4a.cjs <번들.html> [결과 JSON] [스크린샷 디렉터리]
 *
 * P12 보드: 1번 폰 = 신청자(7열 12번·11열 4번), 3번 폰 = 수신자(11열 5번 관객), 오른쪽 카드 = 시연 제어판.
 * 시나리오: 1 수신 의향 등록 후 제안 수신 · 2 미등록 시 제안 불가 · 3 수신 의향 철회 · 4 제안 수락 · 5 제안 거절 · 6 동행 좌석 분리 안내
 *           7 인접 후보 없음 · 8 반대 방향 탐색 · 9 뒤로 가기 상태 유지·접근성 · 10 개인정보 비노출 · 11 일반/연석 공용 문구 분기 · 12 시연 제어판 분리
 * 화면에 보이는 값은 같은 엔진(tools/authoring/demo3c_pair.js)의 결과와도 대조한다.
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
const seen = new Set();
const clipped = new Set();
const ok = (name, pass, detail) => results.push({ journey, name, pass: !!pass, detail: pass ? '' : String(detail || '') });
const A = 0, B = 2;
const ONLY = (process.env.ONLY || '').split(',').filter(Boolean);   // 예: ONLY=3,9 (일부 시나리오만)
const run = (n) => !ONLY.length || ONLY.includes(n);

(async () => {
  const launch = { args: ['--disable-gpu', '--font-render-hinting=none', '--disable-lcd-text', '--force-color-profile=srgb'] };
  if (process.env.HTTPS_PROXY) launch.proxy = { server: process.env.HTTPS_PROXY };
  const browser = await chromium.launch(launch);
  if (shotDir) fs.mkdirSync(shotDir, { recursive: true });

  async function openBoard(prefix) {
    const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    const problems = [];
    page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) problems.push(m.type() + ': ' + m.text().slice(0, 160)); });
    page.on('pageerror', (e) => problems.push('pageerror: ' + String(e).slice(0, 160)));
    await page.goto('file://' + file);
    await page.waitForSelector('section.board iframe');
    const titles = await page.$$eval('section.board', (a) => a.map((x) => x.dataset.board))  // STEP 4C-2A: 보드 표시 이름 대신 바뀌지 않는 식별자(slug)로 찾는다;
    const idx = titles.findIndex((t) => t.startsWith(prefix || 'p08-ui-pair'));
    const handle = (await page.$$('section.board iframe'))[idx];
    const f = await handle.contentFrame();
    await page.waitForTimeout(8000);
    await handle.evaluate((e) => e.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(300);
    const visJs = (h) => `[...document.querySelectorAll('[data-nav-host="${h}"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none')`;
    const H = {
      page, f, handle, problems, ctx,
      screen: (h) => f.evaluate((js) => { const v = eval(js); return v ? v.getAttribute('data-nav-screen') : null; }, visJs(h)),
      text: (h) => f.evaluate((js) => { const v = eval(js); if (!v) return ''; const ds = [...v.querySelectorAll('details')]; const was = ds.map((d) => d.open); ds.forEach((d) => { d.open = true; }); const tx = v.innerText.replace(/\s+/g, ' '); ds.forEach((d, k) => { d.open = was[k]; }); return tx; }, visJs(h)),
      ptext: () => f.evaluate(() => { const p = document.querySelector('[data-demo-ctl]'); return p ? p.innerText.replace(/\s+/g, ' ') : ''; }),
      live: (h) => f.evaluate((hh) => { const p = document.querySelector('[data-live="' + hh + '"]'); return p ? p.textContent : null; }, h),
      async el(h, sel, text) {
        const e = await f.evaluateHandle(([js, s, tx]) => {
          const root = js === 'panel' ? document.querySelector('[data-demo-ctl]') : eval(js);
          return [...root.querySelectorAll(s)].find((x) => !tx || x.textContent.trim() === tx || x.getAttribute('aria-label') === tx) || null;
        }, [h === 'panel' ? 'panel' : visJs(h), sel, text || null]);
        return e.asElement();
      },
      async click(h, sel, text) {
        const e = await H.el(h, sel, text);
        if (!e) throw new Error('요소 없음: ' + h + ' ' + sel + ' ' + (text || '') + ' (화면 ' + (await H.screen(A)) + '/' + (await H.screen(B)) + ')');
        await handle.evaluate((x) => x.scrollIntoView({ block: 'center' }));
        await f.evaluate(() => document.querySelectorAll('[data-nav-host]').forEach((x) => { if (x.parentElement) x.parentElement.scrollTop = 0; }));
        await page.waitForTimeout(100);
        const b = await e.boundingBox();
        await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
        await page.waitForTimeout(350);
        await H.track();
      },
      pclick: (label) => H.click('panel', 'button', label),
      async track() {
        for (const h of [A, B]) {
          const c = await f.evaluate((js) => { const v = eval(js); const m = v && v.querySelector('main'); return m ? [v.getAttribute('data-nav-screen'), m.scrollHeight - m.clientHeight] : null; }, visJs(h));
          if (c) { seen.add(c[0]); if (c[1] > 1) clipped.add(c[0] + '(' + c[1] + 'px)'); }
        }
      },
      async key(k) { await page.keyboard.press(k); await page.waitForTimeout(350); await H.track(); },
      async disabled(h, sel, text) { const e = await H.el(h, sel, text); return e ? e.evaluate((x) => !!x.disabled) : null; },
      checked: (h, sel) => f.evaluate(([js, s]) => [...eval(js).querySelectorAll(s)].map((x) => (x.getAttribute('data-val') || '') + ':' + x.checked), [visJs(h), sel]),
      cards: () => f.evaluate((js) => [...eval(js).querySelectorAll('main section')].filter((s) => s.querySelector('[data-act="choose"]')).map((s) => {
        const b = s.querySelector('[data-act="choose"]');
        return { title: s.querySelector('b').textContent.trim(), text: s.innerText.replace(/\s+/g, ' '), disabled: b.disabled, pressed: b.getAttribute('aria-pressed'), label: b.textContent.trim() };
      }), visJs(A)),
      async shot(name, h) {
        if (!shotDir) return;
        await f.evaluate(() => document.querySelectorAll('[data-nav-host]').forEach((x) => { if (x.parentElement) x.parentElement.scrollTop = 0; }));
        let bb;
        if (h === 'board') { await page.screenshot({ path: path.join(shotDir, name + '.png') }); return; }
        if (h === 'panel') bb = await (await f.$('[data-demo-ctl]')).boundingBox();
        else bb = await (await (await f.$('[data-nav-host="' + h + '"]')).evaluateHandle((e) => e.parentElement)).asElement().boundingBox();
        await page.screenshot({ path: path.join(shotDir, name + '.png'), clip: bb });
      },
    };
    return H;
  }
  async function registerB(H, on) {
    await H.click(B, 'input[data-act="intent"][data-val="' + (on ? 'on' : 'off') + '"]');
    await H.click(B, 'button', '설정 저장');
  }
  async function aToAdjacency(H, keep) {
    await H.click(A, 'a[data-act="next"]');
    if (keep === '7-12') await H.click(A, 'input[data-act="dir"][data-val="7-12"]');
    await H.click(A, 'a[data-act="toCandidates"]');
  }
  async function aSend(H) {
    await H.click(A, '[data-act="choose"][data-val="11-5"]');
    await H.click(A, 'button', '선택한 후보와 최종 비교하기');
    await H.click(A, 'input[data-act="ack"]');
    await H.click(A, 'button', '11열 5번 관객에게 교환 제안 보내기');
    await H.click(B, 'button', '제안 검토하기 →');   // STEP 4B: 도착 알림 카드에서 직접 열기
  }
  async function finish(H) {
    ok('콘솔 오류·경고 0건', H.problems.length === 0, H.problems.join(' | '));
    const other = await H.f.evaluate(() => [1, 3].map((h) => [...document.querySelectorAll('[data-nav-host="' + h + '"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none').getAttribute('data-nav-screen')));
    ok('정적 폰(2·4번)은 그대로', JSON.stringify(other) === JSON.stringify(['PairSeat', 'PairDone']), other);
    await H.ctx.close();
  }
  const NO_DONE = (t) => !t.includes('교환이 완료됐어요') && !t.includes('이제 나란히 앉아요') && !t.includes('교환 완료 (시연)');

  /* ---------------------------------------------------------------- 1. 수신 의향 등록 후 제안 수신 */
  journey = '1 수신 의향 등록 후 제안 수신';
  if (run('1')) {
    const H = await openBoard();
    await H.shot('00-board-start', 'board');
    let tb = await H.text(B);
    ok('수신자 시작 화면 = 교환 제안 받기 설정, 기본값 "받지 않음"', (await H.screen(B)) === 'PairIntent' && tb.includes('지금: 교환 제안 받지 않음 (기본값)')
      && JSON.stringify(await H.checked(B, 'input[data-act="intent"]')) === JSON.stringify(['on:false', 'off:true']), tb.slice(0, 300));
    ok("'교환 제안 받기'와 '제안 수락'의 차이 안내", tb.includes("'교환 제안 받기'와 '제안 수락'은 달라요") && tb.includes('교환에 동의하는 것이 아니에요'), tb);
    await H.shot('01-intent-off', B);
    await H.click(B, 'input[data-act="intent"][data-val="on"]');
    tb = await H.text(B);
    ok('받기를 고르기만 하면 아직 적용 안 됨 (저장 안내)', tb.includes("'설정 저장'을 눌러야 적용돼요") && tb.includes('지금: 교환 제안 받지 않음'), tb.slice(0, 400));
    await H.click(B, 'button', '설정 저장');
    tb = await H.text(B);
    ok('설정 저장 → "교환 제안 받는 중" + 저장 메시지', tb.includes('지금: 교환 제안 받는 중') && tb.includes('이제 옆자리 관객이 교환 제안을 보낼 수 있어요'), tb.slice(0, 400));
    await H.shot('01-intent-on', B);
    await aToAdjacency(H);
    const cards = await H.cards();
    ok('신청자 후보 화면: 11열 5번 "연결 가능" 카드 1개', cards.length === 1 && cards[0].title === '11열 5번 · 오른쪽' && cards[0].text.includes('연결 가능'), JSON.stringify(cards));
    const ev = P.views(Object.assign(P.initialState(), { consent: true, intentDraft: true }), true).adj;
    ok('화면 = 엔진 결과 (후보 카드 제목)', JSON.stringify(cards.map((c) => c.title)) === JSON.stringify(ev.cards.map((c) => c.title)), JSON.stringify(ev.cards.map((c) => c.title)));
    ok('단계 표시 3/6 (인접 확인)', (await H.text(A)).includes('단계 3/6 · 인접 확인'), (await H.text(A)).slice(0, 100));
    await H.shot('01-adjacency', A);
    await H.click(A, '[data-act="choose"][data-val="11-5"]');
    await H.click(A, 'button', '선택한 후보와 최종 비교하기');
    const tw = await H.text(A);
    ok('최종 비교: 유지할 좌석 그대로 · 제공할 좌석 바뀜 · 나란히(완료 시에만)', ['유지할 좌석', '그대로', '제공할 좌석', '7열 12번 → 11열 5번 받음', '떨어짐 → 11열 4번, 5번', '나란히 · 완료 시에만', '등급·가격'].every((s) => tw.includes(s)), tw.slice(0, 500));
    ok("최종 비교: \"아직 '교환 완료'가 아니에요\" · 단계 4/4", tw.includes("아직 '교환 완료'가 아니에요") && tw.includes('단계 4/6 · 비교·제안'), tw.slice(0, 200));
    await H.shot('01-warn', A);
    await H.click(A, 'input[data-act="ack"]');
    await H.click(A, 'button', '11열 5번 관객에게 교환 제안 보내기');
    ok('신청자 → 상대방 검토 (StatusSent)', (await H.screen(A)) === 'StatusSent', await H.screen(A));
    ok('수신자 폰: 제안 도착 알림 카드 (아직 열어보지 않음)', (await H.screen(B)) === 'PairIntent' && (await H.text(B)).includes('새 교환 제안이 도착했어요'), await H.text(B));
    await H.click(B, 'button', '제안 검토하기 →');
    ok('제안 검토하기 → 제안 검토 화면', (await H.screen(B)) === 'PairReceive', await H.screen(B));
    tb = await H.text(B);
    ok('제안 검토: 내 티켓 11열 5번 · 상대 제공 7열 12번 · 비교(무대와 거리 4열 앞으로)', tb.includes('지금 내 좌석') && tb.includes('11열 5번') && tb.includes('7열 12번') && tb.includes('4열 앞으로') && tb.includes('추가 결제 없음') && tb.includes('11열 5번 → 7열 12번'), tb);
    ok('제안 검토: 수락해도 최종 확인이 남는다는 안내', tb.includes("최종 확인을 통과해야 '교환 완료'예요"), tb.slice(-200));
    await H.shot('01-receive', B);
    const ts = await H.text(A);
    ok('신청자 진행 현황: 연석 단계 문구 (좌석 방향 선택 → 교환 제안 보내기 → 제안 수락)', ['좌석 방향 선택', '옆자리 후보 확인', '교환 제안 보내기', '상대방 검토', '제안 수락', '최종 확인 중', '교환 완료'].every((s) => ts.includes(s)) && ts.includes('내 티켓 2장은 그대로 유효해요'), ts);
    ok('휴대폰 화면 안에 데모 조작 없음', !ts.includes('데모 모드') && !ts.includes('상대방 수락') && !tb.includes('데모 모드'), ts.slice(-200));
    await H.shot('01-sent', A);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 2. 미등록 시 제안 불가 */
  journey = '2 수신 의향 미등록 시 제안 불가';
  if (run('2')) {
    const H = await openBoard();
    await aToAdjacency(H);
    const t = await H.text(A);
    ok('후보 0 · "현재 연결 가능한 후보가 없습니다" · 선택 버튼 없음', (await H.cards()).length === 0 && t.includes('현재 연결 가능한 후보가 없습니다'), t);
    ok('다음 버튼 비활성 + 이유 텍스트', (await H.disabled(A, 'button', '선택한 후보와 최종 비교하기')) === true && t.includes('연결 가능한 후보가 없어 다음으로 갈 수 없어요'), t.slice(-200));
    await H.click(B, 'input[data-act="intent"][data-val="on"]');
    ok('수신자가 저장하지 않으면 여전히 후보 없음', (await H.cards()).length === 0 && (await H.text(A)).includes('현재 연결 가능한 후보가 없습니다'));
    ok('수신자 폰: 도착한 제안 없음 (제안 보기 버튼 없음)', !(await H.text(B)).includes('도착한 교환 제안 1건 보기'), await H.text(B));
    ok('시연 제어판 안내: 수신자 B 폰에서 먼저 켜기', (await H.ptext()).includes("수신자 B 폰에서 '교환 제안 받기'를 켜고 저장하세요"), await H.ptext());
    await H.shot('02-no-intent', A);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 3. 수신 의향 철회 */
  journey = '3 수신 의향 철회';
  if (run('3')) {
    const H = await openBoard();
    await registerB(H, true);
    await aToAdjacency(H);
    await H.click(A, '[data-act="choose"][data-val="11-5"]');
    await H.click(A, 'button', '선택한 후보와 최종 비교하기');
    ok('신청자가 최종 비교 화면에 있음', (await H.screen(A)) === 'PairWarn');
    await registerB(H, false);
    let t = await H.text(A);
    ok('철회 → 신청자는 후보 화면으로, 중립 안내', (await H.screen(A)) === 'PairAdjacency' && t.includes('선택했던 후보와 지금은 연결할 수 없어요') && t.includes('현재 연결 가능한 후보가 없습니다'), t);
    ok('철회 사유·개인 설정은 신청자에게 안 보임', !t.includes('받지 않') && !t.includes('철회') && !t.includes('동의'), t);
    ok('수신자: "이제 교환 제안을 받지 않아요"', (await H.text(B)).includes('이제 교환 제안을 받지 않아요'));
    await H.shot('03-withdrawn', A);
    // 진행 중인 제안이 있으면 끌 수 없음
    await registerB(H, true);
    await aSend(H);
    await H.click(B, 'button', '뒤로');
    ok('수신자 뒤로 → 설정 화면, "검토 중인 교환 제안" 카드 + 잠금 안내', (await H.screen(B)) === 'PairIntent' && (await H.text(B)).includes('검토 중인 교환 제안') && (await H.text(B)).includes('제안에 응답한 뒤 끌 수 있어요'), await H.text(B));
    await registerB(H, false);
    t = await H.text(B);
    ok('진행 중 철회 시도 → 거부 안내, 받는 중 유지', t.includes('진행 중인 교환 제안이 있어 지금은 끌 수 없어요') && t.includes('지금: 교환 제안 받는 중'), t);
    await H.click(B, 'button', '이어서 검토하기 →');
    ok('제안 보기 → 제안 검토 화면', (await H.screen(B)) === 'PairReceive');
    await finish(H);
  }

  /* ---------------------------------------------------------------- 4. 수신자 제안 수락 */
  journey = '4 수신자 제안 수락';
  if (run('4')) {
    const H = await openBoard();
    await registerB(H, true);
    await aToAdjacency(H);
    await aSend(H);
    await H.click(B, 'button', '제안 수락');
    let tb = await H.text(B);
    ok('수신자: "제안을 수락했어요" + 아직 교환 완료 아님, 응답 버튼 사라짐', tb.includes('제안을 수락했어요') && tb.includes("아직 '교환 완료'가 아니에요") && !(await H.el(B, 'button', '제안 수락')), tb);
    ok('신청자: PairAccepted (완료 아님)', (await H.screen(A)) === 'PairAccepted' && NO_DONE(await H.text(A)) && (await H.text(A)).includes('옆자리 관객이 제안을 수락했어요'), await H.text(A));
    ok('제어판: 최종 확인 시작 버튼', (await H.ptext()).includes('최종 확인 시작'), await H.ptext());
    await H.shot('04-accepted-a', A); await H.shot('04-accepted-b', B); await H.shot('04-panel', 'panel');
    await H.pclick('최종 확인 시작');
    ok('최종 확인 중: 신청자 StatusFinal · 수신자 "최종 확인 중"', (await H.screen(A)) === 'StatusFinal' && (await H.text(B)).includes('최종 확인 중') && NO_DONE(await H.text(B)), await H.text(B));
    await H.pclick('최종 확인 성공');
    ok('성공: 신청자 PairDone · 수신자 "교환 완료 (시연)" 새 좌석 7열 12번', (await H.screen(A)) === 'PairDone' && (await H.text(B)).includes('교환 완료 (시연)') && (await H.text(B)).includes('새 좌석은 7열 12번'), await H.text(B));
    ok('완료 화면 문구: 동시 제안 관련 문구 없음', !(await H.text(A)).includes('다른 후보에게 보낸 제안') && (await H.text(A)).includes('교환에 제공한 B구역 7열 12번 좌석은 옆자리 관객의 새 좌석이 됐어요'), await H.text(A));
    await H.shot('04-done-a', A); await H.shot('04-done-b', B);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 5. 수신자 제안 거절 */
  journey = '5 수신자 제안 거절';
  if (run('5')) {
    const H = await openBoard();
    await registerB(H, true);
    await aToAdjacency(H);
    await aSend(H);
    await H.click(B, 'button', '거절');
    ok('수신자: "제안을 거절했어요" · 내 좌석 그대로 · 사유 비공개', (await H.text(B)).includes('제안을 거절했어요') && (await H.text(B)).includes('거절 사유는 신청자에게 공개되지 않아요'), await H.text(B));
    let t = await H.text(A);
    ok('신청자: PairDeclined · 내 좌석 변경 없음 · 다른 후보/이전 단계', (await H.screen(A)) === 'PairDeclined' && t.includes('7열 12번 · 11열 4번 (변경 없음)') && t.includes('다른 후보 찾기') && t.includes('이전 단계로 (유지할 좌석 다시 고르기)'), t);
    await H.shot('05-declined-a', A); await H.shot('05-declined-b', B);
    await H.click(A, 'button', '다른 후보 찾기');
    const c = (await H.cards())[0];
    t = await H.text(A);
    ok('다른 후보 찾기 → 거절된 제안 카드(다시 보낼 수 없음) + 후보 없음 + 반대 방향 버튼', (await H.screen(A)) === 'PairAdjacency' && c && c.text.includes('거절된 제안') && c.disabled
      && t.includes('현재 연결 가능한 후보가 없습니다') && t.includes('반대 방향으로 찾아보기'), t);
    ok('수신자 폰은 설정 화면으로 돌아감', (await H.screen(B)) === 'PairIntent', await H.screen(B));
    await H.shot('05-after-decline', A);
    await H.click(A, 'button', '뒤로');
    ok('이전 단계(좌석 방향)로 이동, 선택 유지', (await H.screen(A)) === 'PairSeat' && JSON.stringify(await H.checked(A, 'input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false']));
    await finish(H);
    const H2 = await openBoard();
    await registerB(H2, true);
    await aToAdjacency(H2);
    await aSend(H2);
    await H2.click(B, 'button', '거절');
    await H2.click(A, 'button', '이전 단계로 (유지할 좌석 다시 고르기)');
    ok('거절 후 이전 단계로 → 좌석 방향 화면 (11열 4번 유지 그대로)', (await H2.screen(A)) === 'PairSeat' && JSON.stringify(await H2.checked(A, 'input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false']));
    await finish(H2);
  }

  /* ---------------------------------------------------------------- 6. 동행 좌석 분리 안내 */
  journey = '6 동행 좌석 분리 안내';
  if (run('6')) {
    const H = await openBoard();
    await H.pclick('동행 좌석 있음');
    ok('제어판: 티켓 상황 = 동행 좌석 있음 (aria-pressed)', (await (await H.el('panel', 'button', '동행 좌석 있음')).getAttribute('aria-pressed')) === 'true');
    await registerB(H, true);
    await aToAdjacency(H);
    let t = await H.text(A);
    ok('신청자 후보 화면에는 동행 정보 없음 (개인정보)', (await H.cards()).length === 1 && !t.includes('11열 6번') && !t.includes('동행'), t);
    await H.click(A, '[data-act="choose"][data-val="11-5"]');
    await H.click(A, 'button', '선택한 후보와 최종 비교하기');
    t = await H.text(A);
    ok('신청자 최종 비교: 일반 안내만 ("일행과 함께 예매했거나 … 거절할 수 있어요")', t.includes('상대는 일행과 함께 예매했거나 다른 이유로 거절할 수 있어요') && !t.includes('11열 6번'), t);
    await H.click(A, 'input[data-act="ack"]');
    await H.click(A, 'button', '11열 5번 관객에게 교환 제안 보내기');
    await H.click(B, 'button', '제안 검토하기 →');
    const tb = await H.text(B);
    ok('수신자 제안 검토: "동행 좌석이 분리될 수 있어요" · 11열 6번 · 거절 가능', tb.includes('동행 좌석이 분리될 수 있어요') && tb.includes('함께 예매한 11열 6번과 떨어져 앉게 돼요') && tb.includes('거절해도 돼요'), tb);
    ok('제안을 보낸 뒤에는 티켓 상황 변경 불가 (비활성 + 안내)', (await H.disabled('panel', 'button', '조건 불일치')) === true
      && (await H.f.evaluate(() => document.querySelector('[data-demo-ctl] [role="group"]').getAttribute('aria-label'))).includes('제안을 보낸 뒤에는 바꿀 수 없어요'));
    await H.shot('06-companion-b', B);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 7. 인접 후보 없음 */
  journey = '7 인접 후보 없음';
  if (run('7')) {
    const H = await openBoard();
    await registerB(H, true);
    await aToAdjacency(H, '7-12');
    const t = await H.text(A);
    ok('7열 12번 유지: 후보 없음 + 배치도에서 제외한 좌석 (통로·배치도 정보 없음)', (await H.cards()).length === 0 && t.includes('현재 연결 가능한 후보가 없습니다') && t.includes('배치도에서 제외한 좌석')
      && t.includes('7열 13번 (오른쪽)') && t.includes('번호는 이어지지만 사이에 통로가 있어요') && t.includes('7열 11번 (왼쪽)') && t.includes('인접 여부 확인 필요'), t);
    ok('좌석 정보에는 사람(동의·조건) 이야기가 없음', !/동의|조건 불일치|자격|후보 아님/.test(t.replace("'교환 제안 받기'를 켠 관객 중 조건이 맞는 좌석만", '')), t);
    await H.shot('07-no-adjacent', A);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 8. 반대 방향 탐색 */
  journey = '8 반대 방향 탐색';
  if (run('8')) {
    const H = await openBoard();
    await aToAdjacency(H, '7-12');
    await H.click(A, 'button', '반대 방향으로 찾아보기 (11열 4번 유지)');
    let t = await H.text(A);
    ok('반대 방향 → 11열 4번 유지로 바뀜 (같은 화면)', (await H.screen(A)) === 'PairAdjacency' && t.includes('유지할 좌석 11열 4번') && t.includes('반대 방향으로 찾아보기 (7열 12번 유지)'), t.slice(0, 300));
    await registerB(H, true);
    ok('수신자가 켜면 신청자 화면에 바로 후보 표시 (같은 상태 참조)', (await H.cards()).length === 1, JSON.stringify(await H.cards()));
    await H.click(A, 'button', '뒤로');
    ok('방향 화면에도 반영 (11열 4번 유지 선택됨)', JSON.stringify(await H.checked(A, 'input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false']), await H.checked(A, 'input[data-act="dir"]'));
    await H.shot('08-flip', A);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 9. 뒤로 가기 후 상태 유지 · 접근성 */
  journey = '9 뒤로 가기 후 상태 유지 · 접근성';
  if (run('9')) {
    const H = await openBoard();
    await registerB(H, true);
    let t = await H.text(A);
    ok('첫 화면: 유지할 좌석·교환에 제공할 좌석 개념 + 단계 1/4', t.includes('유지할 좌석') && t.includes('교환에 제공할 좌석') && t.includes('단계 1/6 · 교환 방식'), t.slice(0, 300));
    await H.shot('09-mode', A);
    await aToAdjacency(H);
    await H.click(A, '[data-act="choose"][data-val="11-5"]');
    await H.click(A, 'button', '선택한 후보와 최종 비교하기');
    await H.click(A, 'input[data-act="ack"]');
    await H.click(A, 'button', '뒤로');
    ok('최종 비교 → 뒤로 → 후보 선택 유지', (await H.screen(A)) === 'PairAdjacency' && (await H.cards())[0].pressed === 'true');
    await H.click(A, 'button', '뒤로');
    await H.click(A, 'button', '뒤로');
    ok('뒤로 ×2 → 교환 방식 (티켓 2장 선택 유지)', (await H.screen(A)) === 'PairMode' && JSON.stringify(await H.checked(A, 'input[data-act="pick"]')) === JSON.stringify(['7-12:true', '11-4:true']));
    await H.click(A, 'a[data-act="next"]');
    await H.click(A, 'a[data-act="toCandidates"]');
    await H.click(A, 'button', '선택한 후보와 최종 비교하기');
    ok('다시 들어가도 확인 체크 유지', JSON.stringify(await H.checked(A, 'input[data-act="ack"]')) === JSON.stringify([':true']));
    // 알림 영역: 화면 제목 + 상태만
    const lv = await H.live(A);
    ok('aria-live 알림: 화면 제목과 상태만 짧게', lv === '보내기 전 최종 비교 화면. 연석 만들기 준비 중', lv);
    const roles = await H.f.evaluate(() => [...document.querySelectorAll('[aria-live]')].map((e) => e.getAttribute('aria-live') + ':' + e.textContent.length));
    ok('aria-live 영역은 polite·짧은 문장 (화면 전체가 아님)', roles.length >= 3 && roles.every((r) => r.startsWith('polite:') && +r.split(':')[1] < 120), roles);
    const foc = await H.f.evaluate(() => document.activeElement && document.activeElement.getAttribute('data-nav-host'));
    ok('화면 전환 후 포커스 = 해당 폰 틀', foc === '0', foc);
    // 비활성 버튼: 색 외에 잠금 아이콘·점선
    const dis = await H.f.evaluate(() => { const b = [...document.querySelectorAll('[data-nav-host="0"] [data-nav-screen="PairAdjacency"] button[disabled]')].pop(); return b ? [!!b.querySelector('svg'), getComputedStyle(b).borderStyle] : null; });
    ok('비활성 CTA: 잠금 아이콘 + 점선 테두리', dis === null || (dis[0] && dis[1] === 'dashed'), JSON.stringify(dis));
    // 키보드: 제어판 버튼을 Tab 으로 조작 · 수신자 응답을 키보드로
    await H.click(A, 'button', '11열 5번 관객에게 교환 제안 보내기');
    await H.click(B, 'button', '제안 검토하기 →');
    const acc = await H.el(B, 'button', '제안 수락');
    await acc.focus();
    await H.key('Enter');
    ok('키보드(Enter)로 제안 수락', (await H.screen(A)) === 'PairAccepted');
    const lb = await H.live(B);
    ok('수신자 알림: "좌석 교환 제안 화면. 제안 수락함 · 최종 확인 전"', lb === '좌석 교환 제안 화면. 제안 수락함 · 최종 확인 전', lb);
    const pb = await H.el('panel', 'button', '최종 확인 시작');
    await pb.focus();
    await H.key('Enter');
    const pf = await H.f.evaluate(() => { const p = document.querySelector('[data-demo-ctl]'); return p.contains(document.activeElement); });
    ok('제어판 키보드 조작 후 포커스가 제어판에 남음', (await H.screen(A)) === 'StatusFinal' && pf, pf);
    await H.key('Escape');
    ok('제어판에서 Esc → 두 폰 모두 처음 상태 (수신자 설정도 기본값)', (await H.screen(A)) === 'PairMode' && (await H.screen(B)) === 'PairIntent' && (await H.text(B)).includes('지금: 교환 제안 받지 않음'), (await H.screen(A)) + '/' + (await H.screen(B)));
    await finish(H);
  }

  /* ---------------------------------------------------------------- 10. 개인정보 비노출 */
  journey = '10 개인정보 비노출';
  if (run('10')) {
    const H = await openBoard();
    await aToAdjacency(H);
    const banned = ['후보 아님', '수신 동의', '동의함', '동의 없음', '받지 않', '조건 불일치', '자격 미확인', '확인 필요', '11열 3번', '11열 6번', '동행'];
    const check = async (label) => {
      const t = await H.text(A);
      const hit = banned.filter((b) => t.includes(b));
      ok('신청자 후보 화면에 개인 정보·사유 없음: ' + label, hit.length === 0, hit.join(', ') + ' | ' + t.slice(0, 300));
    };
    await check('수신자 미등록');
    await registerB(H, true);
    for (const [p, label] of [['조건 불일치', '조건 불일치'], ['자격 미확인', '자격 미확인'], ['동행 좌석 있음', '동행 좌석']]) {
      await H.pclick(p);
      await check('11열 5번 = ' + label);
    }
    await H.pclick('조건 불일치');
    const t = await H.text(A);
    ok('조건이 안 맞으면 사유 없이 "현재 연결 가능한 후보가 없습니다"', t.includes('현재 연결 가능한 후보가 없습니다') && t.includes('좌석별로 빠진 이유는 개인정보라 알려드리지 않아요'), t);
    await H.shot('10-privacy', A);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 11. 공용 문구 분기 (일반 교환 / 연석) */
  journey = '11 일반·연석 공용 문구 분기';
  if (run('11')) {
    const H = await openBoard('p08-ui-pair');   // P12 연석
    await registerB(H, true);
    await aToAdjacency(H);
    await aSend(H);
    await H.click(A, 'button', '제안 취소하기');
    let t = await H.text(A);
    ok('연석 취소: "교환 제안을 취소했어요" · 내 티켓 2장 · 좌석 방향 다시 고르기 / 처음으로', (await H.screen(A)) === 'ExCancelled' && t.includes('교환 제안을 취소했어요') && t.includes('내 티켓 2장은 그대로 유효해요') && t.includes('좌석 방향 다시 고르기') && t.includes('처음으로'), t);
    ok('수신자: "신청자가 제안을 취소했어요"', (await H.text(B)).includes('신청자가 제안을 취소했어요'), await H.text(B));
    await H.shot('11-pair-cancelled', A);
    await H.click(A, 'button', '좌석 방향 다시 고르기');
    ok('좌석 방향 다시 고르기 → PairSeat', (await H.screen(A)) === 'PairSeat');
    await finish(H);
    const G = await openBoard('p07-ui-exchange');  // P08 일반 교환
    await G.click(A, 'a', '좌석·회차 교환 신청');
    await G.click(A, 'a', '교환 신청 등록');
    await G.click(A, '[data-act="notify"]');
    await G.click(A, '[data-act="toCompare"]');
    await G.click(A, 'input[data-act="consent"]');
    await G.click(A, 'button', '교환 제안 보내기');
    t = await G.text(A);
    ok('일반 교환 진행 현황: 일반 단계 문구 (교환 신청 → 후보 확인 …), 연석 문구 없음', ['교환 신청', '후보 확인', '교환 제안 보내기', '상대방 검토', '제안 수락'].every((s) => t.includes(s)) && !t.includes('좌석 방향 선택') && !t.includes('2장'), t);
    ok('일반 교환 시연 제어판(폰 밖)에 상대방 응답 버튼', (await G.ptext()).includes('상대방 제안 수락') && !t.includes('데모 모드'), await G.ptext());
    await G.shot('11-general-panel', 'panel');
    await G.click(A, 'button', '제안 취소하기');
    t = await G.text(A);
    ok('일반 교환 취소: "교환 신청을 취소했어요" · 교환 다시 신청 / 예매 상세로', t.includes('교환 신청을 취소했어요') && t.includes('교환 다시 신청') && t.includes('예매 상세로') && !t.includes('2장'), t);
    ok('콘솔 오류·경고 0건 (일반 교환)', G.problems.length === 0, G.problems.join(' | '));
    await G.ctx.close();
  }

  /* ---------------------------------------------------------------- 12. 시연 제어판 분리 */
  journey = '12 시연 제어판 분리';
  if (run('12')) {
    const H = await openBoard();
    const inside = await H.f.evaluate(() => { const p = document.querySelector('[data-demo-ctl]'); return !!p.closest('[data-nav-host]'); });
    ok('시연 제어판은 휴대폰 틀 밖에 있음', inside === false);
    const pt = await H.ptext();
    ok('제어판에 "실제 서비스 기능이 아니에요" 표시', pt.includes('DEMO') && pt.includes('실제 서비스 기능이 아니에요'), pt);
    const phoneDemo = await H.f.evaluate(() => [...document.querySelectorAll('[data-nav-host] [data-nav-screen]')].filter((s) => /데모 모드|상대방 행동 시뮬레이션/.test(s.textContent)).map((s) => s.getAttribute('data-nav-screen')));
    ok('어느 폰 화면에도 데모 패널 없음', phoneDemo.length === 0, phoneDemo);
    await H.shot('12-panel', 'panel');
    await finish(H);
  }

  journey = '공통';
  ok('체험 중 지나간 화면(' + seen.size + '종)의 본문 잘림 0', clipped.size === 0, [...clipped].join(', '));
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
