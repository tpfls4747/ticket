#!/usr/bin/env node
/* STEP 3B 일반 교환 체험 폰 — 사용자 여정 자동 테스트 (실제 마우스·키보드 입력).
 * 사용법: node tools/test_demo_flows.cjs <번들.html> [결과 JSON] [스크린샷 디렉터리]
 *
 * 여정: 1 같은 회차 성공 · 2 다른 회차 성공 · 3 필수 조건 불일치 · 4 선호만 불일치 · 5 후보 없음
 *       6 상대방 거절 · 7 신청자 취소 · 8 최종 확인 실패
 * 각 단계에서 보이는 화면과 문구가 모의 데이터·상태와 맞는지, 모순된 안내(예: 수락 단계에서 '교환이 완료됐어요')가
 * 없는지, 다른 폰이 영향을 받지 않는지, 콘솔 오류·빈 화면 이동이 없는지 확인한다.
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
const CTL = { '상대방 수락': '상대방 제안 수락', '상대방 거절': '상대방 거절', '최종 확인 시작': '최종 확인 시작', '최종 확인 성공': '최종 확인 성공', '최종 확인 실패': '최종 확인 실패' };
const ok = (name, pass, detail) => results.push({ journey, name, pass: !!pass, detail: pass ? '' : String(detail || '') });

(async () => {
  const launch = { args: ['--disable-gpu'] };
  if (process.env.HTTPS_PROXY) launch.proxy = { server: process.env.HTTPS_PROXY };
  const browser = await chromium.launch(launch);
  if (shotDir) fs.mkdirSync(shotDir, { recursive: true });

  async function openBoard() {
    const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, ignoreHTTPSErrors: true });
    const page = await ctx.newPage();
    const problems = [];
    page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) problems.push(m.type() + ': ' + m.text().slice(0, 160)); });
    page.on('pageerror', (e) => problems.push('pageerror: ' + String(e).slice(0, 160)));
    page.on('framenavigated', (f) => { if (/about:blank#blocked/.test(f.url())) problems.push('blocked: ' + f.url()); });
    await page.goto('file://' + file);
    await page.waitForSelector('section.board iframe');
    const titles = await page.$$eval('section.board h2', (a) => a.map((x) => x.textContent));
    const idx = titles.findIndex((t) => t.startsWith('P07 UI'));
    const handle = (await page.$$('section.board iframe'))[idx];
    const f = await handle.contentFrame();
    await page.waitForTimeout(8000);
    await handle.evaluate((e) => e.scrollIntoView({ block: 'center' }));
    await page.waitForTimeout(300);
    const H = {
      page, f, handle, problems, ctx,
      screen: () => f.evaluate(() => {
        const vis = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].filter((c) => getComputedStyle(c).display !== 'none');
        return vis.map((c) => c.getAttribute('data-nav-screen')).join(',');
      }),
      text: () => f.evaluate(() => {
        const v = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
        if (!v) return '';
        // STEP 4B: 접힌 '같은 항목'·'조건 전체 보기'까지 읽고 원래대로 되돌린다
        const ds = [...v.querySelectorAll('details')]; const was = ds.map((d) => d.open); ds.forEach((d) => { d.open = true; });
        const tx = v.innerText.replace(/\s+/g, ' '); ds.forEach((d, k) => { d.open = was[k]; }); return tx;
      }),
      async el(sel, text) {
        const h = await f.evaluateHandle(([s, tx]) => {
          const vis = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
          return [...vis.querySelectorAll(s)].find((e) => !tx || e.textContent.trim() === tx || e.getAttribute('aria-label') === tx) || null;
        }, [sel, text || null]);
        return h.asElement();
      },
      ptext: () => f.evaluate(() => { const p = document.querySelector('[data-demo-ctl]'); return p ? p.innerText.replace(/\s+/g, ' ') : ''; }),
      async click(sel, text) {
        let e = await H.el(sel, text);
        // STEP 4A: 상대방 응답·최종 확인 결과는 폰 밖 시연 제어판에서 정한다
        if (!e && CTL[text]) {
          e = (await f.evaluateHandle((tx) => [...document.querySelectorAll('[data-demo-ctl] button')].find((b) => b.textContent.trim() === tx) || null, CTL[text])).asElement();
        }
        if (!e) throw new Error('요소 없음: ' + sel + ' ' + (text || '') + ' (현재 화면 ' + (await H.screen()) + ')');
        // 스크린샷 등으로 스크롤이 바뀌었을 수 있으므로 보드와 폰 잘림 영역을 매번 원위치한다
        await handle.evaluate((x) => x.scrollIntoView({ block: 'center' }));
        await f.evaluate(() => { const h = document.querySelector('[data-nav-host="0"]'); if (h && h.parentElement) h.parentElement.scrollTop = 0; });
        await page.waitForTimeout(100);
        const b = await e.boundingBox();
        await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
        await page.waitForTimeout(350);
        const clip = await f.evaluate(() => {
          const vis = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
          const m = vis && vis.querySelector('main');
          return m ? [vis.getAttribute('data-nav-screen'), m.scrollHeight - m.clientHeight] : null;
        });
        if (clip) { seenScreens.add(clip[0]); if (clip[1] > 1) clipped.add(clip[0] + '(' + clip[1] + 'px)'); }
      },
      async isDisabled(sel, text) { const e = await H.el(sel, text); return e ? e.evaluate((x) => !!x.disabled) : null; },
      pressed: (sel) => f.evaluate((s) => {
        const vis = [...document.querySelectorAll('[data-nav-host="0"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
        return [...vis.querySelectorAll(s)].filter((b) => b.getAttribute('aria-pressed') === 'true').map((b) => b.getAttribute('data-val'));
      }, sel),
      async shot(name) {
        if (!shotDir) return;
        // 요소 스크린샷은 폰 틀을 감싼 잘림 영역(overflow:hidden)을 스크롤시켜 이후 클릭이 어긋난다.
        // 스크롤 없이 화면 영역만 잘라 찍는다.
        const clip = await (await f.$('[data-nav-host="0"]')).evaluateHandle((e) => e.parentElement);
        const bb = await clip.asElement().boundingBox();
        await page.screenshot({ path: path.join(shotDir, name + '.png'), clip: bb });
      },
    };
    return H;
  }

  // 공통: 조건 화면까지 가서 회차·구역을 원하는 값으로 맞춘다
  async function toRequest(H) {
    await H.click('a', '좌석·회차 교환 신청');
    ok('예매 상세 → 조건 등록', (await H.screen()) === 'Request', await H.screen());
  }
  async function setRounds(H, want) {
    const cur = await H.pressed('[data-act="round"]');
    for (const v of ['R1', 'R2', 'R3', 'R4']) {
      if (cur.includes(v) !== want.includes(v)) await H.click('[data-act="round"][data-val="' + v + '"]');
    }
    const after = await H.pressed('[data-act="round"]');
    ok('회차 선택 반영 ' + want.join(','), JSON.stringify(after.sort()) === JSON.stringify(want.slice().sort()), after);
  }
  async function setZones(H, want) {
    const cur = await H.pressed('[data-act="zone"]');
    for (const v of ['A', 'B', 'C']) {
      if (cur.includes(v) !== want.includes(v)) await H.click('[data-act="zone"][data-val="' + v + '"]');
    }
    const after = await H.pressed('[data-act="zone"]');
    ok('구역 선택 반영 ' + want.join(','), JSON.stringify(after.sort()) === JSON.stringify(want.slice().sort()), after);
  }
  async function submitAndSearch(H, expectScreen, summary) {
    await H.click('a', '교환 신청 등록');
    ok('신청 등록 → 신청 현황', (await H.screen()) === 'Waiting', await H.screen());
    const tx = await H.text();
    for (const s of summary) ok('신청 현황에 조건 유지: ' + s, tx.includes(s), tx.slice(0, 200));
    await H.click('[data-act="notify"]');
    ok('후보 탐색 결과 화면 = ' + expectScreen, (await H.screen()) === expectScreen, await H.screen());
  }
  async function compareAndSend(H, expectRows) {
    await H.click('[data-act="toCompare"]');
    ok('양방향 확인 → 전후 비교', (await H.screen()) === 'Compare', await H.screen());
    const tx = await H.text();
    for (const s of expectRows) ok('비교 화면 데이터: ' + s, tx.includes(s), tx.slice(0, 300));
    ok('동의 전에는 제안 보내기 비활성', (await H.isDisabled('button', '교환 제안 보내기')) === true);
    ok('동의 안내 표시', tx.includes('동의 항목을 선택하면'), tx.slice(-200));
    await H.click('input[data-act="consent"]');
    ok('동의 후 제안 보내기 활성', (await H.isDisabled('button', '교환 제안 보내기')) === false);
    await H.shot('compare-consented');
    await H.click('button', '교환 제안 보내기');
    ok('제안 전송 → 상대방 검토 화면', (await H.screen()) === 'StatusSent', await H.screen());
    const t2 = await H.text();
    const p2 = await H.ptext();
    ok('상대방 응답은 폰 밖 시연 제어판에서 (폰 화면에는 데모 조작 없음)', p2.includes('시연용 제어') && p2.includes('상대방 제안 수락') && !t2.includes('데모 모드'), p2 + ' | ' + t2.slice(-120));
    ok('상대방 검토 중에는 완료 안내 없음', !t2.includes('교환이 완료됐어요'), t2);
  }
  async function acceptToFinal(H) {
    await H.click('button', '상대방 수락');
    ok('상대방 수락 → 수락 화면 (완료 아님)', (await H.screen()) === 'StatusAccepted', await H.screen());
    const t = await H.text();
    ok('수락 화면: "아직 교환이 완료된 것은 아니에요"', t.includes('아직 교환이 완료된 것은 아니에요'), t.slice(0, 200));
    ok('수락 화면에 완료 안내 없음', !t.includes('교환이 완료됐어요'), t);
    await H.shot('status-accepted');
    await H.click('button', '최종 확인 시작');
    ok('최종 확인 중 화면', (await H.screen()) === 'StatusFinal', await H.screen());
  }
  async function otherPhonesUntouched(H) {
    const st = await H.f.evaluate(() => [1, 2, 3, 4, 5].map((h) => {
      const vis = [...document.querySelectorAll('[data-nav-host="' + h + '"] > [data-nav-screen]')].find((c) => getComputedStyle(c).display !== 'none');
      return vis.getAttribute('data-nav-screen');
    }));
    const req = await H.f.evaluate(() => [...document.querySelectorAll('[data-nav-host="1"] [data-nav-screen="Request"] [data-act="round"]')]
      .filter((b) => b.getAttribute('aria-pressed') === 'true').map((b) => b.getAttribute('data-val')));
    ok('다른 폰(2~6)은 그대로', JSON.stringify(st) === JSON.stringify(['Request', 'Waiting', 'Match', 'Done', 'Expired']) && JSON.stringify(req) === JSON.stringify(['R1', 'R4']), st + ' / ' + req);
  }
  async function finish(H) {
    ok('콘솔 오류·경고·빈 화면 이동 0건', H.problems.length === 0, H.problems.join(' | '));
    ok('프레임이 blob 문서에 머무름', H.f.url().startsWith('blob:'), H.f.url());
    await otherPhonesUntouched(H);
    await H.ctx.close();
  }

  /* ---------------------------------------------------------------- 1. 같은 회차 좌석 교환 성공 */
  journey = '1 같은 회차 좌석 교환 성공';
  {
    const H = await openBoard();
    await toRequest(H);
    await setRounds(H, ['R3']);
    await setZones(H, ['A']);
    await H.shot('01-request-same-round');
    await submitAndSearch(H, 'MatchCheck', ['12.20 (일) 18:00 · 필수', 'R석 A구역 · 선호', '1열 ~ 10열 · 선호']);
    const m = await H.text();
    ok('후보 = 같은 회차 A구역 6열 3번', m.includes('12.20 (일) 18:00 · 3회차 · R석 A구역 6열 3번'), m.slice(0, 300));
    ok('양쪽 필수 충족 표시', m.includes('내 필수 충족') && m.includes('후보 필수 충족'), m);
    ok('매칭 완료로 표시하지 않음', m.includes("아직 '매칭 완료'가 아니고"), m.slice(-200));
    await H.shot('01-matchcheck');
    await compareAndSend(H, ['날짜·회차 12.20 (일) 18:00 · 3회차 12.20 (일) 18:00 · 3회차 같음', '구역 R석 B구역 R석 A구역 다름', '열·좌석 7열 12번 6열 3번 다름', '154,000원 (가상) 같음']);
    await H.shot('01-status-sent');
    await acceptToFinal(H);
    await H.shot('01-status-final');
    await H.click('button', '최종 확인 성공');
    ok('최종 확인 성공 → 교환 완료', (await H.screen()) === 'Done', await H.screen());
    const d = await H.text();
    ok('완료 화면 = 받은 티켓 A구역 6열 3번, 이전 티켓 B구역 7열 12번', d.includes('R석 · A구역 6열 3번') && d.includes('12.20 (일) 18:00 · 3회차') && d.includes('12.20 (일) 18:00 · B구역 7열 12번') && d.includes('T26112-0912'), d);
    await H.shot('01-done');
    await H.click('a', '예매 내역으로');
    ok('예매 내역으로 → 예매 상세 (데모 처음 상태)', (await H.screen()) === 'Main', await H.screen());
    await finish(H);
  }

  /* ---------------------------------------------------------------- 2. 다른 회차 교환 성공 (+뒤로) */
  journey = '2 다른 회차 교환 성공';
  {
    const H = await openBoard();
    await toRequest(H);
    await setRounds(H, ['R4']);
    await submitAndSearch(H, 'MatchCheck', ['12.21 (월) 14:00 · 필수', 'R석 A·B구역 · 선호']);
    const m = await H.text();
    ok('후보 = 12.21 A구역 5열 8번', m.includes('12.21 (월) 14:00 · 4회차 · R석 A구역 5열 8번'), m.slice(0, 300));
    ok('후보의 선호(A구역)와 내 B구역 차이를 설명', m.includes('선호와 달라요') && m.includes('후보는 A구역을 선호해요'), m);
    ok('미확인 정보(가격·정책) 표시', m.includes('미확인 2건') && m.includes('권종·가격, 정책 확인 상태'), m);
    ok('제외된 후보(C4, 상대 필수 불일치)는 표시되지 않음', !m.includes('C구역 2열 7번'), m);
    await H.click('[data-act="toCompare"]');
    await H.click('[data-act="back"]');
    ok('뒤로: 전후 비교 → 양방향 확인', (await H.screen()) === 'MatchCheck', await H.screen());
    await H.click('[data-act="back"]');
    ok('뒤로: 양방향 확인 → 신청 현황', (await H.screen()) === 'Waiting', await H.screen());
    await H.click('[data-act="notify"]');
    await compareAndSend(H, ['12.21 (월) 14:00 · 4회차 다름', 'R석 · 가격 정보 없음 확인 필요', '정책 확인 상태 없음 확인 필요']);
    await H.click('[data-act="back"]');
    ok('진행 중(상대방 검토)에는 뒤로 눌러도 머무름', (await H.screen()) === 'StatusSent', await H.screen());
    await acceptToFinal(H);
    await H.click('button', '최종 확인 성공');
    const d = await H.text();
    ok('완료 화면 = 12.21 (월) 14:00 · 4회차, A구역 5열 8번', (await H.screen()) === 'Done' && d.includes('12.21 (월) 14:00 · 4회차') && d.includes('R석 · A구역 5열 8번'), d);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 3. 필수 조건 불일치 */
  journey = '3 필수 조건 불일치';
  {
    const H = await openBoard();
    await toRequest(H);
    await setRounds(H, ['R1']);
    await submitAndSearch(H, 'ExMismatch', ['12.19 (토) 19:30 · 필수']);
    const t = await H.text();
    ok('제외한 후보 = 12.19 B구역 9열 4번', t.includes('12.19 (토) 19:30 · 1회차 · R석 B구역 9열 4번'), t);
    ok('후보의 필수(12.20 14:00) 불일치 이유', t.includes('후보 조건 12.20 (일) 14:00') && t.includes('불일치'), t);
    ok('상대 필수는 바꿀 수 없음 → "필수를 선호로" 비활성', (await H.isDisabled('button', '필수를 선호로 바꿔 보기')) === true);
    await H.shot('03-mismatch');
    await H.click('button', '조건 수정하기');
    ok('조건 수정하기 → 조건 등록 (선택 유지)', (await H.screen()) === 'Request' && JSON.stringify(await H.pressed('[data-act="round"]')) === JSON.stringify(['R1']), await H.screen());
    // 내 쪽 필수 불일치: 12.21 + C구역 필수 → C1 이 내 필수에서 빠지고 C4 는 상대 필수 불일치
    await setRounds(H, ['R4']);
    await setZones(H, ['C']);
    await H.click('[data-act="imp"][data-row="zone"][data-val="필수"]');
    await submitAndSearch(H, 'ExMismatch', ['R석 C구역 · 필수']);
    const t2 = await H.text();
    ok('불일치 화면이 실제 후보·조건과 일치', t2.includes('불일치'), t2);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 4. 선호 조건만 불일치 */
  journey = '4 선호 조건만 불일치';
  {
    const H = await openBoard();
    await toRequest(H);
    await setRounds(H, ['R4']);
    await setZones(H, ['C']);
    await submitAndSearch(H, 'MatchCheck', ['R석 C구역 · 선호']);
    const m = await H.text();
    ok('후보로 표시됨 (필수는 모두 충족)', m.includes('내 필수 충족') && m.includes('후보 필수 충족'), m);
    ok('내 선호 차이 설명: C구역 vs A구역', m.includes('내 선호는 C구역이지만 후보는 A구역이에요'), m);
    ok('후보 선호 차이 설명', m.includes('후보는 A구역을 선호해요'), m);
    await H.shot('04-pref-only');
    await compareAndSend(H, ['구역 R석 B구역 R석 A구역 다름']);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 5. 후보 없음 (+입력 검증·키보드) */
  journey = '5 후보 없음';
  {
    const H = await openBoard();
    await toRequest(H);
    // 진행 제한: 회차를 모두 빼면 등록 불가
    await setRounds(H, []);
    let tx = await H.text();
    ok('회차 미선택 → 신청 버튼 비활성 + 안내', (await H.isDisabled('button', '교환 신청 등록')) === true && tx.includes('원하는 회차를 1개 이상 선택해 주세요'), tx.slice(-250));
    // 키보드로 칩 선택: Tab 포커스 후 Space
    const chip = await H.el('[data-act="round"][data-val="R2"]');
    await chip.focus();
    await H.page.keyboard.press('Space');
    await H.page.waitForTimeout(300);
    ok('키보드(Space)로 회차 칩 선택', JSON.stringify(await H.pressed('[data-act="round"]')) === JSON.stringify(['R2']));
    // 중요도 미선택 → 진행 불가 (같은 값을 다시 누르면 선택 해제)
    await H.click('[data-act="imp"][data-row="row"][data-val="선호"]');
    tx = await H.text();
    ok('중요도 미선택 → 비활성 + "무관으로 처리하지 않아요"', (await H.isDisabled('button', '교환 신청 등록')) === true && tx.includes("'무관'으로 처리하지 않아요"), tx.slice(-250));
    await H.shot('05-validation');
    await H.click('[data-act="imp"][data-row="row"][data-val="무관"]');
    ok('중요도 다시 선택 → 활성', (await H.el('a', '교환 신청 등록')) !== null);
    // 열 범위 조절 (키보드 Enter)
    const plus = await H.el('[data-act="rowPlus"]');
    await plus.focus();
    await H.page.keyboard.press('Enter');
    await H.page.waitForTimeout(300);
    ok('열 범위 + (키보드 Enter) → 1열 ~ 11열', (await H.text()).includes('1열 ~ 11열'));
    await submitAndSearch(H, 'ExNoCandidate', ['12.20 (일) 14:00 · 필수', '1열 ~ 11열 · 무관']);
    const t = await H.text();
    ok('후보 없음 안내 + 신청 유지', t.includes('지금은 맞는 후보가 없어요') && t.includes('교환 신청은 유지돼요'), t);
    await H.shot('05-none');
    await H.click('button', '조건 수정하기');
    ok('조건 수정하기 → 조건 유지된 조건 등록', (await H.screen()) === 'Request' && JSON.stringify(await H.pressed('[data-act="round"]')) === JSON.stringify(['R2']), await H.screen());
    await finish(H);
  }

  /* ---------------------------------------------------------------- 6. 상대방 거절 */
  journey = '6 상대방 거절';
  {
    const H = await openBoard();
    await toRequest(H);
    await submitAndSearch(H, 'MatchCheck', ['12.19 (토) 19:30, 12.21 (월) 14:00 · 필수']);
    await compareAndSend(H, ['R석 A구역']);
    await H.click('button', '상대방 거절');
    ok('상대방 거절 → 거절 화면', (await H.screen()) === 'ExDeclined', await H.screen());
    const t = await H.text();
    ok('거절 화면: 내 티켓 변경 없음, 완료 안내 없음', t.includes('변경 없음') && !t.includes('교환이 완료됐어요'), t);
    await H.shot('06-declined');
    await H.click('button', '다른 후보 찾기');
    const s = await H.screen();
    ok('다른 후보 찾기: 거절한 후보 제외 후 재탐색 (남은 후보는 필수 불일치)', s === 'ExMismatch' && !(await H.text()).includes('A구역 5열 8번'), s);
    await finish(H);
  }

  /* ---------------------------------------------------------------- 7. 신청자 취소 */
  journey = '7 신청자 취소';
  {
    const H = await openBoard();
    await toRequest(H);
    await submitAndSearch(H, 'MatchCheck', ['R석 A·B구역 · 선호']);
    await compareAndSend(H, ['R석 A구역']);
    await H.click('button', '제안 취소하기');
    ok('제안 취소하기 → 취소 화면', (await H.screen()) === 'ExCancelled', await H.screen());
    const t = await H.text();
    ok('취소 화면: 내 티켓 유효, 완료 안내 없음', t.includes('내 티켓은 그대로 유효해요') && !t.includes('교환이 완료됐어요'), t);
    await H.shot('07-cancelled');
    await H.click('button', '교환 다시 신청');
    ok('교환 다시 신청 → 조건 등록 (조건 유지)', (await H.screen()) === 'Request' && JSON.stringify(await H.pressed('[data-act="round"]')) === JSON.stringify(['R1', 'R4']), await H.screen());
    await submitAndSearch(H, 'MatchCheck', ['R석 A·B구역 · 선호']);
    await H.click('[data-act="toCompare"]');
    ok('다시 신청하면 동의가 초기화되어 제안 버튼 비활성', (await H.isDisabled('button', '교환 제안 보내기')) === true);
    // 신청 현황에서의 취소
    await H.page.keyboard.press('Escape');
    await H.page.waitForTimeout(300);
    ok('Esc → 데모 처음 화면(예매 상세)', (await H.screen()) === 'Main', await H.screen());
    await toRequest(H);
    await H.click('a', '교환 신청 등록');
    await H.click('button', '교환 신청 취소');
    ok('신청 현황에서 교환 신청 취소 → 취소 화면', (await H.screen()) === 'ExCancelled', await H.screen());
    await finish(H);
  }

  /* ---------------------------------------------------------------- 8. 최종 확인 실패 */
  journey = '8 최종 확인 실패';
  {
    const H = await openBoard();
    await toRequest(H);
    await submitAndSearch(H, 'MatchCheck', ['1열 ~ 10열 · 선호']);
    await compareAndSend(H, ['R석 A구역']);
    await acceptToFinal(H);
    const tf = await H.text();
    ok('최종 확인 중: 제어판에 결과 버튼, 폰에는 취소 버튼 없음', (await H.ptext()).includes('최종 확인 성공') && !tf.includes('교환 취소하기'), tf.slice(-250));
    await H.click('button', '최종 확인 실패');
    ok('최종 확인 실패 → 실패 화면', (await H.screen()) === 'ExFinalFailed', await H.screen());
    const t = await H.text();
    ok('실패 화면: 원 티켓 유지(목표 UX) 안내, 완료 안내 없음', t.includes('원래 티켓이 그대로 유지되는 것을 목표로') && !t.includes('교환이 완료됐어요'), t);
    await H.shot('08-failed');
    await H.click('button', '내 티켓 확인');
    ok('내 티켓 확인 → 예매 상세', (await H.screen()) === 'Main', await H.screen());
    await finish(H);
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
