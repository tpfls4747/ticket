#!/usr/bin/env node
/* 연석 만들기 체험 — STEP 3C 여정 10개를 STEP 4A 모델로 다시 검증 (실제 마우스·키보드 입력).
 * 사용법: node tools/test_pair_flows.cjs <번들.html> [결과 JSON] [스크린샷 디렉터리]
 *
 * STEP 4A 에서 바뀐 전제 (의도한 변경):
 * - 옆자리 관객(11열 5번)의 '교환 제안 받기'는 3번 폰(수신자)에서 직접 켠다. 기본값은 받지 않음.
 * - 신청자 후보 화면은 연결 가능한 후보만 보여주고, 좌석별 수신 의향·자격·조건 사유를 표시하지 않는다 (개인정보).
 *   좌석 배치(통로·배치도 정보 없음)는 좌석 정보로 계속 보여준다.
 * - 상대방 수락·거절은 3번 폰에서, 최종 확인 결과와 11열 5번 티켓 상황은 폰 밖 시연 제어판에서 정한다.
 * 여정: 1 정상 성공 · 2 교환 제안 받기 꺼짐 · 3 번호 연속이지만 통로 · 4 동행 좌석 · 5 상대 조건 불일치
 *       6 상대 거절 · 7 교환 자격 확인 불가 · 8 최종 확인 실패 · 9 뒤로 가기·키보드 · 10 일반 교환 회귀
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const file = path.resolve(process.argv[2]);
const outJson = process.argv[3];
const shotDir = process.argv[4];
const results = [];
let journey = '';
const seen = new Set();
const clipped = new Set();
const ok = (name, pass, detail) => results.push({ journey, name, pass: !!pass, detail: pass ? '' : String(detail || '') });
const A = 0, B = 2;

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
    page.on('framenavigated', (f) => { if (/about:blank#blocked/.test(f.url())) problems.push('blocked: ' + f.url()); });
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
      screen: (h = A) => f.evaluate((js) => { const v = eval(js); return v ? v.getAttribute('data-nav-screen') : null; }, visJs(h)),
      text: (h = A) => f.evaluate((js) => { const v = eval(js); if (!v) return ''; const ds = [...v.querySelectorAll('details')]; const was = ds.map((d) => d.open); ds.forEach((d) => { d.open = true; }); const tx = v.innerText.replace(/\s+/g, ' '); ds.forEach((d, k) => { d.open = was[k]; }); return tx; }, visJs(h)),
      ptext: () => f.evaluate(() => document.querySelector('[data-demo-ctl]').innerText.replace(/\s+/g, ' ')),
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
      async track() {
        for (const h of [A, B]) {
          const c = await f.evaluate((js) => { const v = eval(js); const m = v && v.querySelector('main'); return m ? [v.getAttribute('data-nav-screen'), m.scrollHeight - m.clientHeight] : null; }, visJs(h));
          if (c) { seen.add(c[0]); if (c[1] > 1) clipped.add(c[0] + '(' + c[1] + 'px)'); }
        }
      },
      async key(k) { await page.keyboard.press(k); await page.waitForTimeout(350); await H.track(); },
      async disabled(h, sel, text) { const e = await H.el(h, sel, text); return e ? e.evaluate((x) => !!x.disabled) : null; },
      checked: (sel, h = A) => f.evaluate(([js, s]) => [...eval(js).querySelectorAll(s)].map((x) => (x.getAttribute('data-val') || '') + ':' + x.checked), [visJs(h), sel]),
      cards: () => f.evaluate((js) => [...eval(js).querySelectorAll('main section')].filter((s) => s.querySelector('[data-act="choose"]')).map((s) => {
        const b = s.querySelector('[data-act="choose"]');
        return { title: s.querySelector('b').textContent.trim(), text: s.innerText.replace(/\s+/g, ' '), btn: { disabled: b.disabled, pressed: b.getAttribute('aria-pressed'), label: b.textContent.trim() } };
      }), visJs(A)),
      async shot(name, h = A) {
        if (!shotDir) return;
        await f.evaluate(() => document.querySelectorAll('[data-nav-host]').forEach((x) => { if (x.parentElement) x.parentElement.scrollTop = 0; }));
        const bb = await (await (await f.$('[data-nav-host="' + h + '"]')).evaluateHandle((e) => e.parentElement)).asElement().boundingBox();
        await page.screenshot({ path: path.join(shotDir, name + '.png'), clip: bb });
      },
    };
    return H;
  }

  const NO_DONE = (t) => !t.includes('교환이 완료됐어요') && !t.includes('이제 나란히 앉아요');
  const CTA = '선택한 후보와 최종 비교하기';
  const SEND = '11열 5번 관객에게 교환 제안 보내기';
  async function registerB(H, on) {
    await H.click(B, 'input[data-act="intent"][data-val="' + (on ? 'on' : 'off') + '"]');
    await H.click(B, 'button', '설정 저장');
  }
  async function toAdjacency(H, keep, register = true) {
    if (register) await registerB(H, true);
    await H.click(A, 'a[data-act="next"]');
    ok('교환 방식 → 좌석 방향 선택', (await H.screen()) === 'PairSeat', await H.screen());
    if (keep && keep !== '11-4') await H.click(A, 'input[data-act="dir"][data-val="' + keep + '"]');
    await H.click(A, 'a[data-act="toCandidates"]');
    ok('좌석 방향 → 옆자리 후보 확인', (await H.screen()) === 'PairAdjacency', await H.screen());
  }
  const PROFILE_LABEL = { basic: '기본', companion: '동행 좌석 있음', mismatch: '조건 불일치', unknown: '자격 미확인' };
  async function setProfile(H, p) {
    await H.click('panel', 'button', PROFILE_LABEL[p]);
    const pr = await H.f.evaluate(() => [...document.querySelectorAll('[data-demo-ctl] [data-act="profile"]')].filter((b) => b.getAttribute('aria-pressed') === 'true').map((b) => b.getAttribute('data-val')));
    ok('시연 제어판: 11열 5번 티켓 상황 = ' + PROFILE_LABEL[p], JSON.stringify(pr) === JSON.stringify([p]), pr);
  }
  async function chooseAndWarn(H) {
    await H.click(A, '[data-act="choose"][data-val="11-5"]');
    const c = (await H.cards()).find((x) => x.title.startsWith('11열 5번'));
    ok('후보 선택 → "선택됨" 표시 (aria-pressed)', c && c.btn.pressed === 'true' && c.btn.label === '선택됨 ✓', JSON.stringify(c && c.btn));
    ok('후보 선택 후 다음 버튼 활성', (await H.disabled(A, 'button', CTA)) === false);
    await H.click(A, 'button', CTA);
    ok('후보 확인 → 보내기 전 최종 비교', (await H.screen()) === 'PairWarn', await H.screen());
  }
  async function ackAndSend(H) {
    ok('확인 전에는 교환 제안 보내기 비활성', (await H.disabled(A, 'button', SEND)) === true);
    await H.click(A, 'input[data-act="ack"]');
    ok('확인 후 교환 제안 보내기 활성', (await H.disabled(A, 'button', SEND)) === false);
    await H.click(A, 'button', SEND);
    ok('교환 제안 보내기 → 상대방 검토 (StatusSent 재사용)', (await H.screen()) === 'StatusSent', await H.screen());
    ok('수신자 폰에 제안 도착 알림', (await H.screen(B)) === 'PairIntent' && (await H.text(B)).includes('새 교환 제안이 도착했어요'), await H.text(B));
    await H.click(B, 'button', '제안 검토하기 →');
    ok('수신자가 열면 제안 검토 화면', (await H.screen(B)) === 'PairReceive', await H.screen(B));
    const t = await H.text();
    ok('상대방 검토: 완료 안내 없음, 폰 안에 데모 조작 없음', NO_DONE(t) && !t.includes('데모 모드'), t.slice(-200));
  }
  async function finish(H) {
    ok('콘솔 오류·경고·빈 화면 이동 0건', H.problems.length === 0, H.problems.join(' | '));
    ok('프레임이 blob 문서에 머무름', H.f.url().startsWith('blob:'), H.f.url());
    const st = await H.f.evaluate(() => [1, 3].map((h) => [...document.querySelectorAll('[data-nav-host="' + h + '"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none').getAttribute('data-nav-screen')));
    const radios = await H.f.evaluate(() => [...document.querySelectorAll('[data-nav-host="1"] [data-nav-screen="PairSeat"] input[name=dir]')].map((r) => r.checked));
    ok('정적 폰(2·4번)은 그대로 (화면·기본 선택)', JSON.stringify(st) === JSON.stringify(['PairSeat', 'PairDone']) && JSON.stringify(radios) === JSON.stringify([true, false]), st + ' / ' + JSON.stringify(radios));
    await H.ctx.close();
  }

  /* ---------------------------------------------------------------- 1. 정상 성공 */
  journey = '1 정상 성공';
  {
    const H = await openBoard();
    let t = await H.text();
    ok('시작 화면 = 교환 방식 선택 (실험 기능·단계 1/4)', (await H.screen()) === 'PairMode' && t.includes('실험 기능') && t.includes('단계 1/6'), t.slice(0, 200));
    ok('내 티켓 2장과 자격 표시 (시연 판정)', t.includes('R석 · B구역 7열 12번') && t.includes('R석 · B구역 11열 4번') && (t.match(/교환 가능 \(시연 판정\)/g) || []).length === 2, t.slice(0, 400));
    await registerB(H, true);
    await H.click(A, 'a[data-act="next"]');
    t = await H.text();
    ok('좌석 방향: 기본 = 11열로 모으기 (11열 4번 유지)', JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false']), await H.checked('input[data-act="dir"]'));
    ok('유지할 좌석·제공할 좌석 구분 표시 (배치도 범례 포함)', t.includes('11열 4번 유지 · 7열 12번 제공') && t.includes('제공할 좌석') && t.includes('통로'), t.slice(0, 400));
    await H.click(A, 'a[data-act="toCandidates"]');
    t = await H.text();
    const cards = await H.cards();
    ok('후보 화면: 유지할 11열 4번 / 교환에 제공할 7열 12번', t.includes('유지할 좌석 11열 4번') && t.includes('교환에 제공할 좌석 7열 12번'), t.slice(0, 300));
    ok('연결 가능한 후보만: 11열 5번 1장 (11열 3번은 언급 없음)', cards.length === 1 && cards[0].text.includes('연결 가능') && !t.includes('11열 3번'), JSON.stringify(cards.map((c) => c.text.slice(0, 60))));
    ok('11열 5번: 배치도상 옆자리·양쪽 자격·상대 조건 충족', ['배치도상 옆자리', '양쪽 교환 자격', '충족', '교환하면 11열 4번, 5번 나란히'].every((s) => cards[0].text.includes(s)), cards[0].text);
    ok('선택 전 다음 버튼 비활성 + 안내', (await H.disabled(A, 'button', CTA)) === true && t.includes('제안할 후보를 선택해 주세요'), t.slice(-200));
    await chooseAndWarn(H);
    t = await H.text();
    ok("최종 비교: 양방향 충족 + \"아직 '교환 완료'가 아니에요\"", (t.match(/충족/g) || []).length >= 2 && t.includes("아직 '교환 완료'가 아니에요"), t.slice(0, 500));
    ok('완료 시 좌석 = 11열 4번, 5번 (완료 시에만)', t.includes('떨어짐 → 11열 4번, 5번') && t.includes('나란히 · 완료 시에만'), t.slice(0, 400));
    await ackAndSend(H);
    await H.click(B, 'button', '제안 수락');
    t = await H.text();
    ok('수신자 제안 수락 → PairAccepted, 완료 아님', (await H.screen()) === 'PairAccepted' && t.includes('아직 교환이 완료된 것은 아니에요') && NO_DONE(t), t.slice(0, 200));
    ok('수락 화면 좌석 데이터: 지금 7열 12번 · 11열 4번 → 11열 4번, 5번', t.includes('7열 12번 · 11열 4번') && t.includes('11열 4번, 5번'), t.slice(0, 400));
    ok('시연 제어판에 "최종 확인 시작"', (await H.ptext()).includes('최종 확인 시작'), await H.ptext());
    await H.click('panel', 'button', '최종 확인 시작');
    ok('최종 확인 중 (StatusFinal 재사용)', (await H.screen()) === 'StatusFinal' && NO_DONE(await H.text()), await H.screen());
    await H.click('panel', 'button', '최종 확인 성공');
    t = await H.text();
    ok('최종 확인 성공 → 연석 완료 화면', (await H.screen()) === 'PairDone' && t.includes('R석 · B구역 11열 4번, 5번') && t.includes('B구역 7열 12번') && t.includes('11열 5번 관객의 수락'), t.slice(0, 400));
    await H.click(A, 'a[data-act="home"]');
    ok('예매 내역으로 → 처음 화면', (await H.screen()) === 'PairMode', await H.screen());
    await finish(H);
  }

  /* ---------------------------------------------------------------- 2. 교환 제안 받기 꺼짐 (STEP 3C: 수신 동의 없음) */
  journey = '2 교환 제안 받기 꺼짐';
  {
    const H = await openBoard();
    await toAdjacency(H, '11-4', false);
    let t = await H.text();
    ok('수신자가 켜지 않으면 후보 0 · 선택 버튼 0 · 중립 안내', (await H.cards()).length === 0 && t.includes('현재 연결 가능한 후보가 없습니다'), t);
    ok('동의 여부를 좌석별로 표시하지 않음 (STEP 3C 의 "후보 아님" 카드 제거)', !t.includes('후보 아님') && !t.includes('11열 3번') && !t.includes('동의'), t);
    ok('다음 버튼 비활성', (await H.disabled(A, 'button', CTA)) === true);
    await registerB(H, true);
    await H.click(A, '[data-act="choose"][data-val="11-5"]');
    await registerB(H, false);
    t = await H.text();
    ok('선택 후 수신자가 끄면 선택 해제, 진행 불가, 중립 안내', (await H.disabled(A, 'button', CTA)) === true && t.includes('선택했던 후보와 지금은 연결할 수 없어요'), t);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 3. 번호 연속이지만 통로로 분리 */
  journey = '3 번호 연속이지만 통로로 분리';
  {
    const H = await openBoard();
    await toAdjacency(H, '7-12');
    const t = await H.text();
    ok('유지할 좌석 7열 12번 / 교환에 제공할 좌석 11열 4번', t.includes('유지할 좌석 7열 12번') && t.includes('교환에 제공할 좌석 11열 4번'), t.slice(0, 300));
    ok('7열 13번: 번호는 이어지지만 통로 → 옆자리 아님 (좌석 정보)', t.includes('7열 13번 (오른쪽)') && t.includes('옆자리 아님') && t.includes('번호는 이어지지만 사이에 통로가 있어요'), t);
    ok('7열 11번: 배치도 데이터 없음 → "인접 여부 확인 필요"', t.includes('7열 11번 (왼쪽)') && t.includes('인접 여부 확인 필요'), t);
    ok('번호만으로 인접 판단하지 않는다는 안내', t.includes('번호가 이어져도 통로가 있거나 배치도 정보가 없으면 옆자리로 보지 않아요'), t);
    ok('제안 가능한 후보 없음 → 선택 버튼 없음·진행 불가', (await H.cards()).length === 0 && (await H.disabled(A, 'button', CTA)) === true, t.slice(-200));
    await H.shot('03-aisle');
    await finish(H);
  }

  /* ---------------------------------------------------------------- 4. 상대에게 동행 좌석 */
  journey = '4 상대에게 동행 좌석';
  {
    const H = await openBoard();
    await setProfile(H, 'companion');
    await toAdjacency(H);
    const c5 = (await H.cards())[0];
    ok('동행 좌석이 있어도 막지 않음: 연결 가능 · 선택 가능', c5 && c5.text.includes('연결 가능') && !c5.btn.disabled, JSON.stringify(c5));
    ok('신청자에게 상대의 동행 정보는 보이지 않음', !(await H.text()).includes('11열 6번') && !(await H.text()).includes('동행'), await H.text());
    await chooseAndWarn(H);
    ok('최종 비교: 일반 안내 (일행 예매 등으로 거절 가능)', (await H.text()).includes('상대는 일행과 함께 예매했거나 다른 이유로 거절할 수 있어요'), await H.text());
    await ackAndSend(H);
    const tb = await H.text(B);
    ok('수신자: 동행 좌석 분리 안내 (11열 6번) · 거절 가능', tb.includes('동행 좌석이 분리될 수 있어요') && tb.includes('11열 6번') && tb.includes('거절해도 돼요'), tb);
    await H.click(B, 'button', '거절');
    ok('동행 때문에 상대가 거절 → 거절 화면, 내 좌석 그대로', (await H.screen()) === 'PairDeclined' && (await H.text()).includes('7열 12번 · 11열 4번 (변경 없음)'), await H.text());
    await finish(H);
  }

  /* ---------------------------------------------------------------- 5. 상대 조건 불일치 */
  journey = '5 상대 조건 불일치';
  {
    const H = await openBoard();
    await toAdjacency(H);
    await setProfile(H, 'mismatch');
    const t = await H.text();
    ok('상대 필수 조건(1~6열)과 맞지 않으면 후보에서 빠짐 (사유 비공개)', (await H.cards()).length === 0 && t.includes('현재 연결 가능한 후보가 없습니다') && !t.includes('1~6열') && !t.includes('불일치'), t);
    ok('진행 불가', (await H.disabled(A, 'button', CTA)) === true);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 6. 상대 거절 */
  journey = '6 상대 거절';
  {
    const H = await openBoard();
    await toAdjacency(H);
    await chooseAndWarn(H);
    await ackAndSend(H);
    await H.click(B, 'button', '거절');
    let t = await H.text();
    ok('수신자 거절 → PairDeclined, 내 좌석 변경 없음 · 11열 5번 거절됨', (await H.screen()) === 'PairDeclined' && t.includes('7열 12번 · 11열 4번 (변경 없음)') && t.includes('11열 5번') && t.includes('거절됨') && NO_DONE(t), t);
    await H.click(A, 'button', '다른 후보 찾기');
    const c5 = (await H.cards())[0];
    t = await H.text();
    ok('다른 후보 찾기 → 거절된 제안(다시 보낼 수 없음)', (await H.screen()) === 'PairAdjacency' && c5.text.includes('거절된 제안') && c5.btn.disabled, c5 && c5.text);
    ok('다시 보낼 후보 없음 → 반대 방향으로 찾아보기 제공', (await H.disabled(A, 'button', CTA)) === true && t.includes('반대 방향으로 찾아보기 (7열 12번 유지)'), t.slice(-300));
    await H.click(A, 'button', '반대 방향으로 찾아보기 (7열 12번 유지)');
    ok('반대 방향 → 7열 12번 유지로 바뀜', (await H.text()).includes('유지할 좌석 7열 12번'), (await H.text()).slice(0, 200));
    await H.click(A, 'button', '뒤로');
    ok('뒤로 → 좌석 방향 화면에 7열 12번 유지 반영', (await H.screen()) === 'PairSeat' && JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:false', '7-12:true']), await H.checked('input[data-act="dir"]'));
    await finish(H);
  }

  /* ---------------------------------------------------------------- 7. 교환 자격 확인 불가 */
  journey = '7 교환 자격 확인 불가';
  {
    const H = await openBoard();
    await toAdjacency(H);
    await setProfile(H, 'unknown');
    const t = await H.text();
    ok('상대 자격을 확인할 수 없으면 "제안 가능"으로 보이지 않음 (후보에서 빠짐)', (await H.cards()).length === 0 && !t.includes('제안 가능') && !t.includes('연결 가능 ') && t.includes('현재 연결 가능한 후보가 없습니다'), t);
    ok('진행 불가', (await H.disabled(A, 'button', CTA)) === true);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 8. 최종 확인 실패 */
  journey = '8 최종 확인 실패';
  {
    const H = await openBoard();
    await toAdjacency(H);
    await chooseAndWarn(H);
    await ackAndSend(H);
    await H.click(B, 'button', '제안 수락');
    await H.click('panel', 'button', '최종 확인 시작');
    await H.click('panel', 'button', '최종 확인 실패');
    const t = await H.text();
    ok('최종 확인 실패(시뮬레이션) → ExFinalFailed 재사용', (await H.screen()) === 'ExFinalFailed', await H.screen());
    ok('실패 화면: 내 티켓 2장 유지(목표 UX), 완료 안내 없음', t.includes('7열 12번 · 11열 4번') && t.includes('2장 모두 유지 (목표)') && t.includes('유지돼요 (목표)') && NO_DONE(t), t);
    ok('원 티켓 유지를 보장된 기능으로 쓰지 않음 ((목표) 표기 + 시연 표시)', t.includes('(목표)') && t.includes('시연') && !t.includes('보장'), t);
    ok('수신자: 최종 확인 실패 · 원래 좌석 유지(목표)', (await H.text(B)).includes('최종 확인에 실패했어요') && (await H.text(B)).includes('유지해요 (목표)'), await H.text(B));
    await H.click(A, 'button', '다시 신청');
    ok('다시 신청 → 좌석 방향 화면, 고른 방향 유지', (await H.screen()) === 'PairSeat' && JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false']), await H.screen());
    await finish(H);
  }

  /* ---------------------------------------------------------------- 9. 뒤로 가기 선택 유지 · 키보드 */
  journey = '9 뒤로 가기 선택 유지';
  {
    const H = await openBoard();
    await registerB(H, true);
    await H.click(A, 'input[data-act="mode"][data-val="general"]');
    await H.click(A, 'a[data-act="next"]');
    let t = await H.text();
    ok('좌석·회차 교환 선택 → 머무르며 06 보드 안내', (await H.screen()) === 'PairMode' && t.includes("'06 UI 좌석·회차 교환' 보드"), t.slice(-250));
    await H.click(A, 'input[data-act="mode"][data-val="pair"]');
    await H.click(A, 'input[data-act="pick"][data-val="7-12"]');
    await H.click(A, 'a[data-act="next"]');
    t = await H.text();
    ok('티켓 1장만 선택 → 머무르며 2장 필요 안내', (await H.screen()) === 'PairMode' && t.includes('같은 회차 티켓 2장이 필요해요'), t.slice(-250));
    await H.click(A, 'input[data-act="pick"][data-val="7-12"]');
    await H.click(A, 'a[data-act="next"]');
    await H.click(A, 'input[data-act="dir"][data-val="7-12"]');
    await H.click(A, 'a[data-act="toCandidates"]');
    await H.click(A, 'button', '뒤로');
    ok('후보 → 뒤로 → 방향 화면에서 7열 선택 유지', (await H.screen()) === 'PairSeat' && JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:false', '7-12:true']), await H.checked('input[data-act="dir"]'));
    const dirEl = await H.el(A, 'input[data-act="dir"][data-val="7-12"]');
    await dirEl.focus();
    await H.key('ArrowUp');
    ok('키보드(화살표)로 방향 변경 → 11열 유지, 설명 갱신', JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false'])
      && (await H.text()).includes('11열 4번 유지 · 7열 12번 제공'), await H.checked('input[data-act="dir"]'));
    await H.click(A, 'a[data-act="toCandidates"]');
    const btn = await H.el(A, '[data-act="choose"][data-val="11-5"]');
    await btn.focus();
    await H.key('Enter');
    ok('키보드(Enter)로 후보 선택', ((await H.cards())[0] || { btn: {} }).btn.pressed === 'true');
    await H.click(A, 'button', CTA);
    await H.click(A, 'input[data-act="ack"]');
    const ackEl = await H.el(A, 'input[data-act="ack"]');
    await ackEl.focus();
    await H.key('Space');
    ok('키보드(Space)로 확인 해제 → 보내기 비활성', JSON.stringify(await H.checked('input[data-act="ack"]')) === JSON.stringify([':false']) && (await H.disabled(A, 'button', SEND)) === true);
    await H.key('Space');
    ok('키보드(Space)로 다시 확인 → 보내기 활성', (await H.disabled(A, 'button', SEND)) === false);
    await H.click(A, 'button', '뒤로');
    ok('최종 비교 → 뒤로 → 후보 선택 유지', (await H.screen()) === 'PairAdjacency' && (await H.cards())[0].btn.pressed === 'true', await H.screen());
    await H.click(A, 'button', CTA);
    ok('다시 들어가도 확인 체크 유지', JSON.stringify(await H.checked('input[data-act="ack"]')) === JSON.stringify([':true']));
    await H.click(A, 'button', '뒤로');
    await H.click(A, 'button', '뒤로');
    await H.click(A, 'button', '뒤로');
    ok('뒤로 ×3 → 교환 방식 화면, 티켓 2장·연석 선택 유지', (await H.screen()) === 'PairMode'
      && JSON.stringify(await H.checked('input[data-act="pick"]')) === JSON.stringify(['7-12:true', '11-4:true'])
      && JSON.stringify(await H.checked('input[data-act="mode"]')) === JSON.stringify(['general:false', 'pair:true']), await H.checked('input[data-act="pick"]'));
    await H.click(A, 'a[data-act="next"]');
    await H.click(A, 'a[data-act="toCandidates"]');
    await H.click(A, 'button', CTA);
    await H.click(A, 'button', SEND);
    await H.click(A, 'button', '뒤로');
    ok('제안 보낸 뒤 뒤로 → 상대방 검토 화면에 머무름', (await H.screen()) === 'StatusSent', await H.screen());
    await H.click(A, 'button', '제안 취소하기');
    t = await H.text();
    ok('제안 취소 → 취소 화면 (내 티켓 2장 그대로)', (await H.screen()) === 'ExCancelled' && t.includes('내 티켓 2장은 그대로 유효해요'), t);
    await H.click(A, 'button', '좌석 방향 다시 고르기');
    ok('좌석 방향 다시 고르기 → 방향 화면, 선택 유지', (await H.screen()) === 'PairSeat' && JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false']), await H.screen());
    await H.click(A, 'input[data-act="dir"][data-val="7-12"]');
    await H.key('Escape');
    ok('폰에서 Esc → 처음 화면', (await H.screen()) === 'PairMode' && (await H.screen(B)) === 'PairIntent', await H.screen());
    await H.click(A, 'a[data-act="next"]');
    ok('Esc 후 방향 선택도 처음 값(11열)', JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false']), await H.checked('input[data-act="dir"]'));
    const foc = await H.f.evaluate(() => document.activeElement && document.activeElement.getAttribute('data-nav-host'));
    ok('화면 전환 후 포커스 = 폰 틀 (키보드 위치 유지)', foc === '0', foc);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 10. 일반 교환 회귀 (P07 체험 폰) */
  journey = '10 일반 교환 회귀';
  {
    const H = await openBoard('p07-ui-exchange');
    await H.click(A, 'a', '좌석·회차 교환 신청');
    await H.click(A, 'a', '교환 신청 등록');
    await H.click(A, '[data-act="notify"]');
    ok('일반 교환: 후보 발견 (MatchCheck)', (await H.screen()) === 'MatchCheck', await H.screen());
    await H.click(A, '[data-act="toCompare"]');
    await H.click(A, 'input[data-act="consent"]');
    await H.click(A, 'button', '교환 제안 보내기');
    await H.click('panel', 'button', '상대방 제안 수락');
    ok('일반 교환: 수락 화면은 StatusAccepted 그대로', (await H.screen()) === 'StatusAccepted', await H.screen());
    await H.click('panel', 'button', '최종 확인 시작');
    await H.click('panel', 'button', '최종 확인 실패');
    const t = await H.text();
    ok('일반 교환 실패 화면: 내 티켓 1장(7열 12번) · 유지 (목표) — 연석 문구 섞이지 않음', (await H.screen()) === 'ExFinalFailed'
      && t.includes('12.20 (일) 18:00 · 3회차 · R석 B구역 7열 12번') && t.includes('유지 (목표)') && !t.includes('2장 모두'), t);
    await H.click(A, 'button', '다시 신청');
    ok('일반 교환: 다시 신청 → 조건 등록', (await H.screen()) === 'Request', await H.screen());
    ok('콘솔 오류·경고·빈 화면 이동 0건', H.problems.length === 0, H.problems.join(' | '));
    await H.ctx.close();
  }

  journey = '공통';
  ok('체험 중 지나간 화면(' + seen.size + '종)의 본문 잘림 0', clipped.size === 0, [...clipped].join(', '));
  await browser.close();
  const fail = results.filter((r) => !r.pass);
  let cur = '';
  for (const r of results) {
    if (r.journey !== cur) { cur = r.journey; console.log('\n[' + cur + ']'); }
    console.log((r.pass ? '  PASS ' : '  FAIL ') + r.name + (r.pass ? '' : '  — ' + r.detail.slice(0, 300)));
  }
  console.log('\n합계 %d건, 실패 %d건', results.length, fail.length);
  if (outJson) fs.writeFileSync(outJson, JSON.stringify(results, null, 1));
  process.exit(fail.length ? 1 : 0);
})().catch((e) => { console.error('테스트 실행 실패:', e); process.exit(2); });
