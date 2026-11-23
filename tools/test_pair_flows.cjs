#!/usr/bin/env node
/* STEP 3C 연석 만들기 체험 폰 — 사용자 여정 자동 테스트 (실제 마우스·키보드 입력).
 * 사용법: node tools/test_pair_flows.cjs <번들.html> [결과 JSON] [스크린샷 디렉터리]
 *
 * 여정: 1 정상 성공 · 2 수신 동의 없음 · 3 번호는 이어지지만 통로로 분리 · 4 상대에게 동행 좌석 · 5 상대 조건 불일치
 *       6 상대 거절 · 7 교환 자격 확인 불가 · 8 최종 확인 실패 · 9 뒤로 가기 선택 유지 · 10 일반 교환 회귀
 * 클릭 도우미·잘림 검사·스크린샷 방식은 tools/test_demo_flows.cjs (STEP 3B) 와 같다.
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const file = path.resolve(process.argv[2]);
const outJson = process.argv[3];
const shotDir = process.argv[4];
const results = [];
let journey = '';
const seenScreens = new Set();
const clipped = new Set();
const ok = (name, pass, detail) => results.push({ journey, name, pass: !!pass, detail: pass ? '' : String(detail || '') });

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
    const titles = await page.$$eval('section.board h2', (a) => a.map((x) => x.textContent));
    const idx = titles.findIndex((t) => t.startsWith(prefix || 'P08 UI'));
    const handle = (await page.$$('section.board iframe'))[idx];
    const f = await handle.contentFrame();
    await page.waitForTimeout(8000);
    await handle.evaluate((e) => e.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(300);
    const VIS = '[...document.querySelectorAll(\'[data-nav-host="0"] > [data-nav-screen]\')].find((c) => getComputedStyle(c).display !== \'none\')';
    const H = {
      page, f, handle, problems, ctx,
      screen: () => f.evaluate(() => [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')]
        .filter((c) => getComputedStyle(c).display !== 'none').map((c) => c.getAttribute('data-nav-screen')).join(',')),
      text: () => f.evaluate(() => {
        const vis = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
        return vis ? vis.innerText.replace(/\s+/g, ' ') : '';
      }),
      async el(sel, text) {
        const h = await f.evaluateHandle(([s, tx]) => {
          const vis = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
          return [...vis.querySelectorAll(s)].find((e) => !tx || e.textContent.trim() === tx || e.getAttribute('aria-label') === tx) || null;
        }, [sel, text || null]);
        return h.asElement();
      },
      async click(sel, text) {
        const e = await H.el(sel, text);
        if (!e) throw new Error('요소 없음: ' + sel + ' ' + (text || '') + ' (현재 화면 ' + (await H.screen()) + ')');
        // 스크린샷·포커스로 스크롤이 바뀌었을 수 있으므로 보드와 폰 잘림 영역을 매번 원위치한다
        await handle.evaluate((x) => x.scrollIntoView({ block: 'center' }));
        await f.evaluate(() => { const h = document.querySelector('[data-nav-host="0"]'); if (h && h.parentElement) h.parentElement.scrollTop = 0; });
        await page.waitForTimeout(100);
        const b = await e.boundingBox();
        await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
        await page.waitForTimeout(350);
        await H.track();
      },
      async track() {
        const clip = await f.evaluate(() => {
          const vis = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
          const m = vis && vis.querySelector('main');
          return m ? [vis.getAttribute('data-nav-screen'), m.scrollHeight - m.clientHeight] : null;
        });
        if (clip) { seenScreens.add(clip[0]); if (clip[1] > 1) clipped.add(clip[0] + '(' + clip[1] + 'px)'); }
      },
      async key(k) { await page.keyboard.press(k); await page.waitForTimeout(350); await H.track(); },
      async isDisabled(sel, text) { const e = await H.el(sel, text); return e ? e.evaluate((x) => !!x.disabled) : null; },
      checked: (sel) => f.evaluate((s) => {
        const vis = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
        return [...vis.querySelectorAll(s)].map((x) => (x.getAttribute('data-val') || '') + ':' + x.checked);
      }, sel),
      // 후보 카드: [좌석, 상태 배지 텍스트, 선택 버튼 상태]
      cards: () => f.evaluate(() => {
        const vis = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
        return [...vis.querySelectorAll('main section')].map((s) => {
          const b = s.querySelector('[data-act="choose"]');
          return { title: s.querySelector('b').textContent.trim(), text: s.innerText.replace(/\s+/g, ' '),
            btn: b ? { disabled: b.disabled, pressed: b.getAttribute('aria-pressed'), label: b.textContent.trim() } : null };
        });
      }),
      async shot(name) {
        if (!shotDir) return;
        // 요소 스크린샷은 폰 잘림 영역(overflow:hidden)을 스크롤시키므로 화면 영역만 잘라 찍는다 (STEP 3B 와 같은 방식)
        await f.evaluate(() => { const h = document.querySelector('[data-nav-host="0"]'); if (h && h.parentElement) h.parentElement.scrollTop = 0; });
        const clip = await (await f.$('[data-nav-host="0"]')).evaluateHandle((e) => e.parentElement);
        const bb = await clip.asElement().boundingBox();
        await page.screenshot({ path: path.join(shotDir, name + '.png'), clip: bb });
      },
    };
    void VIS;
    return H;
  }

  const NO_DONE = (t) => !t.includes('교환이 완료됐어요') && !t.includes('이제 나란히 앉아요');
  const NO_MATCH_DONE = (t) => !/매칭 완료(?!'가 아니)/.test(t.replace(/'매칭 완료'가 아니/g, ''));
  async function toAdjacency(H, keep) {
    await H.click('a[data-act="next"]');
    ok('교환 방식 → 좌석 방향 선택', (await H.screen()) === 'PairSeat', await H.screen());
    if (keep && keep !== '11-4') await H.click('input[data-act="dir"][data-val="' + keep + '"]');
    await H.click('a[data-act="toCandidates"]');
    ok('좌석 방향 → 옆자리 후보 확인', (await H.screen()) === 'PairAdjacency', await H.screen());
  }
  async function setProfile(H, p, label) {
    await H.click('[data-act="profile"][data-val="' + p + '"]');
    const pr = await H.f.evaluate(() => [...document.querySelectorAll('[data-nav-host="0"] [data-nav-screen="PairAdjacency"] [data-act="profile"]')]
      .filter((b) => b.getAttribute('aria-pressed') === 'true').map((b) => b.getAttribute('data-val')));
    ok('데모 모드: 11열 5번 관객 상황 = ' + label, JSON.stringify(pr) === JSON.stringify([p]), pr);
  }
  async function chooseAndWarn(H) {
    await H.click('[data-act="choose"][data-val="11-5"]');
    const c = (await H.cards()).find((x) => x.title.startsWith('11열 5번'));
    ok('후보 선택 → "선택됨" 표시 (aria-pressed)', c && c.btn && c.btn.pressed === 'true' && c.btn.label === '선택됨', JSON.stringify(c && c.btn));
    ok('후보 선택 후 다음 버튼 활성', (await H.isDisabled('button', '선택한 후보로 제안 준비하기')) === false);
    await H.click('button', '선택한 후보로 제안 준비하기');
    ok('후보 확인 → 제안 보내기 전 확인', (await H.screen()) === 'PairWarn', await H.screen());
  }
  async function ackAndSend(H) {
    ok('확인 전에는 제안 보내기 비활성', (await H.isDisabled('button', '11열 5번 관객에게 제안 보내기')) === true);
    await H.click('input[data-act="ack"]');
    ok('확인 후 제안 보내기 활성', (await H.isDisabled('button', '11열 5번 관객에게 제안 보내기')) === false);
    await H.click('button', '11열 5번 관객에게 제안 보내기');
    ok('제안 전송 → 상대방 검토 (StatusSent 재사용)', (await H.screen()) === 'StatusSent', await H.screen());
    const t = await H.text();
    ok('상대방 검토: 데모 모드(시뮬레이션) 표시, 완료 안내 없음', t.includes('데모 모드') && t.includes('상대방 행동 시뮬레이션') && NO_DONE(t), t.slice(-200));
  }
  async function otherPhonesUntouched(H) {
    const st = await H.f.evaluate(() => [1, 2, 3].map((h) => {
      const vis = [...document.querySelectorAll('[data-nav-host="' + h + '"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
      return vis.getAttribute('data-nav-screen');
    }));
    const radios = await H.f.evaluate(() => [1, 2, 3].map((h) => [...document.querySelectorAll('[data-nav-host="' + h + '"] [data-nav-screen="PairSeat"] input[name=dir]')].map((r) => r.checked)));
    ok('다른 폰(2~4)은 그대로 (화면·기본 선택)', JSON.stringify(st) === JSON.stringify(['PairSeat', 'PairReceive', 'PairDone'])
      && radios.every((g) => JSON.stringify(g) === JSON.stringify([true, false])), st + ' / ' + JSON.stringify(radios));
  }
  async function finish(H, other) {
    ok('콘솔 오류·경고·빈 화면 이동 0건', H.problems.length === 0, H.problems.join(' | '));
    ok('프레임이 blob 문서에 머무름', H.f.url().startsWith('blob:'), H.f.url());
    if (other !== false) await otherPhonesUntouched(H);
    await H.ctx.close();
  }

  /* ---------------------------------------------------------------- 1. 정상 성공 */
  journey = '1 정상 성공';
  {
    const H = await openBoard();
    let t = await H.text();
    ok('시작 화면 = 교환 방식 선택 (실험 기능 표시)', (await H.screen()) === 'PairMode' && t.includes('실험 기능'), t.slice(0, 200));
    ok('내 티켓 2장과 자격 표시 (시연 판정)', t.includes('R석 · B구역 7열 12번') && t.includes('R석 · B구역 11열 4번') && (t.match(/교환 가능 \(시연 판정\)/g) || []).length === 2, t.slice(0, 300));
    await H.shot('01-mode');
    await H.click('a[data-act="next"]');
    t = await H.text();
    ok('좌석 방향: 기본 = 11열로 모으기 (11열 4번 지킴)', JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false']), await H.checked('input[data-act="dir"]'));
    ok('지킬 좌석·내놓을 좌석 구분 표시', t.includes('지킬 좌석 11열 4번 · 내놓을 좌석 7열 12번') && t.includes('지킬 좌석') && t.includes('내놓을 좌석') && t.includes('통로'), t.slice(0, 400));
    await H.shot('01-seat');
    await H.click('a[data-act="toCandidates"]');
    t = await H.text();
    let cards = await H.cards();
    ok('후보 화면: 지킬 11열 4번 / 내놓을 7열 12번', t.includes('지킬 좌석 11열 4번') && t.includes('내놓을 좌석 7열 12번'), t.slice(0, 300));
    ok('옆자리 2곳 판정: 11열 3번 후보 아님 · 11열 5번 제안 가능', cards.length === 2 && cards[0].text.includes('후보 아님') && cards[1].text.includes('제안 가능'), JSON.stringify(cards.map((c) => c.text.slice(0, 60))));
    ok('11열 5번: 동의·인접(배치도)·자격·상대 조건 모두 충족', ['동의함 (시연)', '인접 확인 (배치도)', '양쪽 교환 가능 (시연)', '충족'].every((s) => cards[1].text.includes(s)), cards[1].text);
    ok('선택 전 다음 버튼 비활성 + 안내', (await H.isDisabled('button', '선택한 후보로 제안 준비하기')) === true && t.includes('제안할 후보를 선택해 주세요'), t.slice(-200));
    await H.shot('01-adjacency');
    await chooseAndWarn(H);
    t = await H.text();
    ok('보내기 전 확인: 양방향 모두 충족 + "아직 매칭 완료 아님"', (t.match(/충족/g) || []).length >= 2 && t.includes("아직 '매칭 완료'가 아니에요") && NO_MATCH_DONE(t), t.slice(0, 500));
    ok('완료 후 좌석 = 11열 4번, 5번 (완료 시에만)', t.includes('11열 4번, 5번 · 나란히 (완료 시에만)'), t.slice(0, 300));
    ok('실험 기능 · 수요 미검증 표시', t.includes('실험 기능 · 수요 미검증'), t.slice(0, 80));
    await H.shot('01-warn');
    await ackAndSend(H);
    await H.shot('01-sent');
    await H.click('button', '상대방 수락');
    t = await H.text();
    ok('상대방 수락(시뮬레이션) → PairAccepted, 완료 아님', (await H.screen()) === 'PairAccepted' && t.includes('아직 교환이 완료된 것은 아니에요') && NO_DONE(t), t.slice(0, 200));
    ok('수락 화면 좌석 데이터: 지금 7열 12번 · 11열 4번 → 11열 4번, 5번', t.includes('7열 12번 · 11열 4번') && t.includes('11열 4번, 5번'), t.slice(0, 400));
    ok('수락 화면: 데모 모드 패널 표시', t.includes('데모 모드 · 다음 단계 진행'), t.slice(-300));
    await H.shot('01-accepted');
    await H.click('button', '최종 확인 시작');
    ok('최종 확인 중 (StatusFinal 재사용)', (await H.screen()) === 'StatusFinal' && NO_DONE(await H.text()), await H.screen());
    await H.click('button', '최종 확인 성공');
    t = await H.text();
    ok('최종 확인 성공 → 연석 완료 화면', (await H.screen()) === 'PairDone' && t.includes('R석 · B구역 11열 4번, 5번') && t.includes('B구역 7열 12번') && t.includes('11열 5번 관객의 수락'), t.slice(0, 400));
    await H.shot('01-done');
    await H.click('a[data-act="home"]');
    ok('예매 내역으로 → 처음 화면, 선택 초기화', (await H.screen()) === 'PairMode', await H.screen());
    await finish(H);
  }

  /* ---------------------------------------------------------------- 2. 수신 동의 없음 */
  journey = '2 수신 동의 없음';
  {
    const H = await openBoard();
    await toAdjacency(H);
    let cards = await H.cards();
    const c3 = cards.find((c) => c.title.startsWith('11열 3번'));
    ok('동의하지 않은 11열 3번: "후보 아님", 선택 버튼 없음', c3 && c3.text.includes('후보 아님') && c3.btn === null && c3.text.includes('제안을 보내지 않아요'), JSON.stringify(c3));
    await setProfile(H, 'noConsent', '동의 없음');
    cards = await H.cards();
    const t = await H.text();
    ok('11열 5번도 동의 철회 → 후보 0, 선택 버튼 0', cards.every((c) => c.btn === null && c.text.includes('후보 아님')), JSON.stringify(cards.map((c) => c.text.slice(0, 50))));
    ok('다음 버튼 비활성 + 반대 방향 안내', (await H.isDisabled('button', '선택한 후보로 제안 준비하기')) === true && t.includes('제안할 수 있는 옆자리가 없어요'), t.slice(-200));
    await H.shot('02-no-consent');
    // 동의한 상태로 골랐다가 동의를 철회하면 선택이 풀린다
    await setProfile(H, 'basic', '기본');
    await H.click('[data-act="choose"][data-val="11-5"]');
    await setProfile(H, 'noConsent', '동의 없음');
    ok('선택 후 동의 철회 → 선택 해제, 진행 불가', (await H.isDisabled('button', '선택한 후보로 제안 준비하기')) === true, await H.text());
    await finish(H);
  }

  /* ---------------------------------------------------------------- 3. 번호는 이어지지만 통로로 분리 */
  journey = '3 번호 연속이지만 통로로 분리';
  {
    const H = await openBoard();
    await toAdjacency(H, '7-12');
    const t = await H.text();
    const cards = await H.cards();
    const c13 = cards.find((c) => c.title.startsWith('7열 13번'));
    const c11 = cards.find((c) => c.title.startsWith('7열 11번'));
    ok('지킬 좌석 7열 12번 / 내놓을 좌석 11열 4번', t.includes('지킬 좌석 7열 12번') && t.includes('내놓을 좌석 11열 4번'), t.slice(0, 300));
    ok('7열 13번: 동의했지만 "인접 아님" (통로) · 제안 불가 · 선택 불가', c13 && c13.text.includes('제안 불가') && c13.text.includes('인접 아님') && c13.text.includes('번호는 이어지지만 사이에 통로가 있어요') && c13.btn && c13.btn.disabled, JSON.stringify(c13));
    ok('7열 11번: 배치도 데이터 없음 → "인접 여부 확인 필요" · 제안 보류 · 선택 불가', c11 && c11.text.includes('인접 여부 확인 필요') && c11.text.includes('제안 보류') && c11.btn && c11.btn.disabled, JSON.stringify(c11));
    ok('번호만으로 인접 판단하지 않는다는 안내', t.includes('번호만 보고 판단하지 않아요') && t.includes('번호가 이어져도 붙어 있다고 판단하지 않고'), t.slice(0, 300));
    ok('제안 가능한 후보 없음 → 진행 불가', (await H.isDisabled('button', '선택한 후보로 제안 준비하기')) === true, t.slice(-200));
    ok('11열 5번 관객 상황 패널은 이 방향에서 숨김', !t.includes('11열 5번 관객의 상황 바꾸기'), t.slice(-200));
    await H.shot('03-aisle');
    // 비활성 버튼 클릭은 아무 일도 일으키지 않는다
    await H.click('[data-act="choose"][data-val="7-13"]');
    ok('비활성 후보 클릭 → 변화 없음', (await H.screen()) === 'PairAdjacency' && (await H.isDisabled('button', '선택한 후보로 제안 준비하기')) === true);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 4. 상대에게 동행 좌석 */
  journey = '4 상대에게 동행 좌석';
  {
    const H = await openBoard();
    await toAdjacency(H);
    await setProfile(H, 'companion', '동행 좌석 있음');
    const c5 = (await H.cards()).find((c) => c.title.startsWith('11열 5번'));
    ok('동행 좌석이 있어도 막지 않음: "제안 가능 · 동행 주의"', c5 && c5.text.includes('제안 가능 · 동행 주의') && c5.btn && !c5.btn.disabled, JSON.stringify(c5));
    ok('동행 좌석 행: 11열 6번 · 분리될 수 있어요 · 상대가 거절할 수 있어요', c5 && c5.text.includes('분리될 수 있어요') && c5.text.includes('11열 6번과 함께 예매') && c5.text.includes('상대가 거절할 수 있어요'), c5 && c5.text);
    await H.shot('04-companion-adjacency');
    await chooseAndWarn(H);
    const t = await H.text();
    ok('보내기 전 확인: 동행 분리 경고와 거절 가능 안내', t.includes('상대의 동행 좌석(11열 6번)이 분리될 수 있어요') && t.includes('거절할 수 있어요') && t.includes('막지는 않아요'), t.slice(0, 600));
    await H.shot('04-companion-warn');
    await ackAndSend(H);
    await H.click('button', '상대방 거절');
    ok('동행 때문에 상대가 거절 → 거절 화면, 내 좌석 그대로', (await H.screen()) === 'PairDeclined' && (await H.text()).includes('7열 12번 · 11열 4번 (변경 없음)'), await H.text());
    await finish(H);
  }

  /* ---------------------------------------------------------------- 5. 상대 조건 불일치 */
  journey = '5 상대 조건 불일치';
  {
    const H = await openBoard();
    await toAdjacency(H);
    await setProfile(H, 'mismatch', '조건 불일치');
    const c5 = (await H.cards()).find((c) => c.title.startsWith('11열 5번'));
    ok('11열 5번: 인접은 확인됐지만 상대 필수 조건(1~6열) ↔ 내가 줄 7열 12번 불일치', c5 && c5.text.includes('인접 확인 (배치도)') && c5.text.includes('불일치') && c5.text.includes('열 필수 · 1~6열 / 내 좌석 7열'), c5 && c5.text);
    ok('제안 불가 · 선택 불가 · "상대의 조건은 내가 바꿀 수 없어요"', c5.text.includes('제안 불가') && c5.btn.disabled && c5.text.includes('상대의 조건은 내가 바꿀 수 없어요'), c5.text);
    ok('진행 불가', (await H.isDisabled('button', '선택한 후보로 제안 준비하기')) === true);
    await H.shot('05-mismatch');
    await finish(H);
  }

  /* ---------------------------------------------------------------- 6. 상대 거절 */
  journey = '6 상대 거절';
  {
    const H = await openBoard();
    await toAdjacency(H);
    await chooseAndWarn(H);
    await ackAndSend(H);
    await H.click('button', '상대방 거절');
    let t = await H.text();
    ok('상대방 거절(시뮬레이션) → PairDeclined', (await H.screen()) === 'PairDeclined', await H.screen());
    ok('거절 화면: 내 좌석 변경 없음 · 11열 5번 거절됨 · 완료 안내 없음', t.includes('7열 12번 · 11열 4번 (변경 없음)') && t.includes('11열 5번') && t.includes('거절됨') && NO_DONE(t), t);
    await H.shot('06-declined');
    await H.click('button', '다른 후보 확인하기');
    t = await H.text();
    const c5 = (await H.cards()).find((c) => c.title.startsWith('11열 5번'));
    ok('다른 후보 확인 → 후보 화면, 거절한 11열 5번은 "거절됨"·선택 불가', (await H.screen()) === 'PairAdjacency' && c5.text.includes('거절됨') && c5.btn.disabled, c5 && c5.text);
    ok('다시 보낼 후보 없음 → 진행 불가 + 반대 방향 안내', (await H.isDisabled('button', '선택한 후보로 제안 준비하기')) === true && t.includes('반대 방향으로 모으기'), t.slice(-200));
    await H.shot('06-after-decline');
    await finish(H);
    // 반대 방향으로 모으기
    const H2 = await openBoard();
    await toAdjacency(H2);
    await chooseAndWarn(H2);
    await ackAndSend(H2);
    await H2.click('button', '상대방 거절');
    await H2.click('button', '반대 방향으로 모으기 보기');
    ok('반대 방향으로 모으기 → 좌석 방향 화면, 7열 12번 지킴으로 바뀜', (await H2.screen()) === 'PairSeat'
      && JSON.stringify(await H2.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:false', '7-12:true']), await H2.checked('input[data-act="dir"]'));
    ok('반대 방향 설명: 지킬 7열 12번 · 내놓을 11열 4번', (await H2.text()).includes('지킬 좌석 7열 12번 · 내놓을 좌석 11열 4번'), (await H2.text()).slice(0, 400));
    await finish(H2);
  }

  /* ---------------------------------------------------------------- 7. 교환 자격 확인 불가 */
  journey = '7 교환 자격 확인 불가';
  {
    const H = await openBoard();
    await toAdjacency(H);
    await setProfile(H, 'unknown', '자격 미확인');
    const c5 = (await H.cards()).find((c) => c.title.startsWith('11열 5번'));
    ok('11열 5번: 교환 자격 "확인 필요" → 제안 보류 · 선택 불가', c5 && c5.text.includes('확인 필요') && c5.text.includes('제안 보류') && c5.btn.disabled
      && c5.text.includes('확인 전에는 제안하지 않아요'), c5 && c5.text);
    ok('확인 안 된 후보를 "제안 가능"으로 표시하지 않음', !c5.text.includes('제안 가능'), c5.text);
    ok('진행 불가', (await H.isDisabled('button', '선택한 후보로 제안 준비하기')) === true);
    await H.shot('07-eligibility-unknown');
    await finish(H);
  }

  /* ---------------------------------------------------------------- 8. 최종 확인 실패 */
  journey = '8 최종 확인 실패';
  {
    const H = await openBoard();
    await toAdjacency(H);
    await chooseAndWarn(H);
    await ackAndSend(H);
    await H.click('button', '상대방 수락');
    await H.click('button', '최종 확인 시작');
    await H.click('button', '최종 확인 실패');
    const t = await H.text();
    ok('최종 확인 실패(시뮬레이션) → ExFinalFailed 재사용', (await H.screen()) === 'ExFinalFailed', await H.screen());
    ok('실패 화면: 내 티켓 2장 유지(목표 UX), 완료 안내 없음', t.includes('7열 12번 · 11열 4번') && t.includes('2장 모두 유지 (목표)') && t.includes('목표 UX') && NO_DONE(t), t);
    ok('원 티켓 유지를 보장된 기능으로 쓰지 않음 ("목표로 설계")', t.includes('유지되는 것을 목표로') && t.includes('실제 티켓을 처리하지 않아요'), t);
    await H.shot('08-failed');
    await H.click('button', '다시 신청');
    ok('다시 신청 → 좌석 방향 화면, 고른 방향 유지', (await H.screen()) === 'PairSeat' && JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false']), await H.screen());
    await finish(H);
  }

  /* ---------------------------------------------------------------- 9. 뒤로 가기 선택 유지 · 키보드 */
  journey = '9 뒤로 가기 선택 유지';
  {
    const H = await openBoard();
    // 교환 방식: 좌석·회차 교환을 고르면 이 폰에서는 진행하지 않고 안내
    await H.click('input[data-act="mode"][data-val="general"]');
    await H.click('a[data-act="next"]');
    let t = await H.text();
    ok('좌석·회차 교환 선택 → 머무르며 07 보드 안내', (await H.screen()) === 'PairMode' && t.includes('07 일반 교환 보드'), t.slice(-250));
    await H.click('input[data-act="mode"][data-val="pair"]');
    // 티켓 한 장 해제 → 진행 불가 안내
    await H.click('input[data-act="pick"][data-val="7-12"]');
    await H.click('a[data-act="next"]');
    t = await H.text();
    ok('티켓 1장만 선택 → 머무르며 2장 필요 안내', (await H.screen()) === 'PairMode' && t.includes('같은 회차 티켓 2장이 필요해요'), t.slice(-250));
    await H.click('input[data-act="pick"][data-val="7-12"]');
    await H.click('a[data-act="next"]');
    await H.click('input[data-act="dir"][data-val="7-12"]');
    await H.click('a[data-act="toCandidates"]');
    await H.click('button[data-act="back"]');
    ok('후보 → 뒤로 → 방향 화면에서 7열 선택 유지', (await H.screen()) === 'PairSeat' && JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:false', '7-12:true']), await H.checked('input[data-act="dir"]'));
    // 키보드: 방향 라디오는 화살표 키로 바꿀 수 있고, 배치도·설명이 같이 바뀐다
    const dirEl = await H.el('input[data-act="dir"][data-val="7-12"]');
    await dirEl.focus();
    await H.key('ArrowUp');
    ok('키보드(화살표)로 방향 변경 → 11열 지킴, 설명 갱신', JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false'])
      && (await H.text()).includes('지킬 좌석 11열 4번 · 내놓을 좌석 7열 12번'), await H.checked('input[data-act="dir"]'));
    await H.click('a[data-act="toCandidates"]');
    ok('화살표로 바꾼 방향이 후보 화면에 반영', (await H.text()).includes('지킬 좌석 11열 4번'), (await H.text()).slice(0, 200));
    // 키보드: Tab 포커스 후 Enter 로 후보 선택
    const btn = await H.el('[data-act="choose"][data-val="11-5"]');
    await btn.focus();
    await H.key('Enter');
    ok('키보드(Enter)로 후보 선택', ((await H.cards()).find((c) => c.title.startsWith('11열 5번')) || {}).btn.pressed === 'true');
    await H.click('button', '선택한 후보로 제안 준비하기');
    await H.click('input[data-act="ack"]');
    await H.click('button[data-act="back"]');
    ok('보내기 전 확인 → 뒤로 → 후보 선택 유지', (await H.screen()) === 'PairAdjacency' && ((await H.cards()).find((c) => c.title.startsWith('11열 5번')) || {}).btn.pressed === 'true', await H.screen());
    await H.click('button', '선택한 후보로 제안 준비하기');
    ok('다시 들어가도 확인 체크 유지', JSON.stringify(await H.checked('input[data-act="ack"]')) === JSON.stringify([':true']), await H.checked('input[data-act="ack"]'));
    // 키보드: Space 로 확인 체크 해제 → 보내기 비활성, 다시 Space → 활성
    const ackEl = await H.el('input[data-act="ack"]');
    await ackEl.focus();
    await H.key('Space');
    ok('키보드(Space)로 확인 해제 → 보내기 비활성', JSON.stringify(await H.checked('input[data-act="ack"]')) === JSON.stringify([':false'])
      && (await H.isDisabled('button', '11열 5번 관객에게 제안 보내기')) === true, await H.checked('input[data-act="ack"]'));
    await H.key('Space');
    ok('키보드(Space)로 다시 확인 → 보내기 활성', (await H.isDisabled('button', '11열 5번 관객에게 제안 보내기')) === false);
    await H.click('button[data-act="back"]');
    await H.click('button[data-act="back"]');
    await H.click('button[data-act="back"]');
    ok('뒤로 ×3 → 교환 방식 화면, 티켓 2장·연석 선택 유지', (await H.screen()) === 'PairMode'
      && JSON.stringify(await H.checked('input[data-act="pick"]')) === JSON.stringify(['7-12:true', '11-4:true'])
      && JSON.stringify(await H.checked('input[data-act="mode"]')) === JSON.stringify(['general:false', 'pair:true']), await H.checked('input[data-act="pick"]'));
    // 진행 중에는 뒤로가 동작하지 않고 취소로만 나간다
    await H.click('a[data-act="next"]');
    await H.click('a[data-act="toCandidates"]');
    await H.click('button', '선택한 후보로 제안 준비하기');
    await H.click('button', '11열 5번 관객에게 제안 보내기');
    await H.click('button[data-act="back"]');
    ok('제안 보낸 뒤 뒤로 → 상대방 검토 화면에 머무름', (await H.screen()) === 'StatusSent', await H.screen());
    await H.click('button', '제안 취소하기');
    t = await H.text();
    ok('제안 취소 → 취소 화면 (내 티켓 그대로)', (await H.screen()) === 'ExCancelled' && t.includes('내 티켓은 그대로 유효해요'), t);
    await H.click('button', '교환 다시 신청');
    ok('교환 다시 신청 → 방향 화면, 선택 유지', (await H.screen()) === 'PairSeat' && JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false']), await H.screen());
    // Esc → 처음 상태 (입력도 초기화)
    await H.click('input[data-act="dir"][data-val="7-12"]');
    await H.key('Escape');
    ok('Esc → 처음 화면', (await H.screen()) === 'PairMode', await H.screen());
    await H.click('a[data-act="next"]');
    ok('Esc 후 방향 선택도 처음 값(11열)', JSON.stringify(await H.checked('input[data-act="dir"]')) === JSON.stringify(['11-4:true', '7-12:false']), await H.checked('input[data-act="dir"]'));
    // 포커스: 화면이 바뀌면 폰 틀로 포커스가 옮겨진다
    const foc = await H.f.evaluate(() => document.activeElement && document.activeElement.getAttribute('data-nav-host'));
    ok('화면 전환 후 포커스 = 폰 틀 (키보드 위치 유지)', foc === '0', foc);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 10. 일반 교환 회귀 (P07 체험 폰) */
  journey = '10 일반 교환 회귀';
  {
    const H = await openBoard('P07 UI');
    await H.click('a', '좌석·회차 교환 신청');
    await H.click('a', '교환 신청 등록');
    await H.click('[data-act="notify"]');
    ok('일반 교환: 후보 발견 (MatchCheck)', (await H.screen()) === 'MatchCheck', await H.screen());
    await H.click('[data-act="toCompare"]');
    await H.click('input[data-act="consent"]');
    await H.click('button', '교환 제안 보내기');
    await H.click('button', '상대방 수락');
    ok('일반 교환: 수락 화면은 StatusAccepted 그대로', (await H.screen()) === 'StatusAccepted', await H.screen());
    await H.click('button', '최종 확인 시작');
    await H.click('button', '최종 확인 실패');
    const t = await H.text();
    ok('일반 교환 실패 화면: 내 티켓 1장(7열 12번) · 유지 (목표) — 연석 문구 섞이지 않음', (await H.screen()) === 'ExFinalFailed'
      && t.includes('12.20 (일) 18:00 · 3회차 · R석 B구역 7열 12번') && t.includes('유지 (목표)') && !t.includes('2장 모두'), t);
    await H.click('button', '다시 신청');
    ok('일반 교환: 다시 신청 → 조건 등록', (await H.screen()) === 'Request', await H.screen());
    ok('콘솔 오류·경고·빈 화면 이동 0건', H.problems.length === 0, H.problems.join(' | '));
    await H.ctx.close();
  }

  journey = '공통';
  ok('체험 중 지나간 화면(' + seenScreens.size + '종)의 본문 잘림 0', clipped.size === 0, [...clipped].join(', '));
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
