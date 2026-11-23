#!/usr/bin/env node
/* 연석 만들기 데모 엔진 단위 테스트 (브라우저 없이). 사용법: node tools/test_pair_engine.cjs */
const D = require('./authoring/demo3b_store.js');
const P = require('./authoring/demo3c_pair.js');
const results = [];
const t = (name, cond) => results.push({ name, pass: !!cond });
const S = (o) => Object.assign(P.initialState(), o || {});
const seat = (row, n, extra) => Object.assign({ round: 'R3', zone: 'B', row, seat: n }, extra || {});
const run = (s, actions) => actions.reduce((acc, a) => { const r = P.reduce(acc.s, a); return { s: r.state, nav: r.nav }; }, { s, nav: null });
const cand = (s, key) => P.candidates(s).find((c) => c.key === key);

/* ---- 실제 인접 판정 (배치도) ---- */
t('같은 블록·확인된 배치도의 이웃 좌석 → 인접 (11열 4·5번)', P.adjacency(seat(11, 4), seat(11, 5)).res === 'ok');
t('번호가 이어져도 통로로 나뉘면 인접 아님 (7열 12·13번)', P.adjacency(seat(7, 12), seat(7, 13)).res === 'no' && P.adjacency(seat(7, 12), seat(7, 13)).reason === '통로로 분리');
t('배치도 데이터가 없는 구간은 "확인 필요" (7열 11·12번)', P.adjacency(seat(7, 11), seat(7, 12)).res === 'unknown');
t('같은 열이 아니면 인접 아님 (7열 12번 · 8열 12번)', P.adjacency(seat(7, 12), seat(8, 12)).res === 'no');
t('번호가 이어지지 않으면 인접 아님 (11열 4·6번)', P.adjacency(seat(11, 4), seat(11, 6)).res === 'no');
t('회차가 다르면 인접 아님', P.adjacency(seat(11, 4), seat(11, 5, { round: 'R4' })).res === 'no');
t('구역이 다르면 인접 아님', P.adjacency(seat(11, 4), seat(11, 5, { zone: 'A' })).res === 'no');
t('판정 순서: 같은 회차 → 구역·열 → 번호 연속 → 배치도', P.adjacency(seat(11, 4), seat(11, 5)).checks.map((c) => c.dim).join('>') === '같은 회차>같은 구역·열>번호 연속>배치도 (통로·단절)');

/* ---- 후보 판정 ---- */
t('수신 동의 없는 11열 3번은 후보 아님(hidden)', cand(S(), '11-3').status === 'hidden' && !cand(S(), '11-3').proposable);
t('기본: 11열 5번 제안 가능', cand(S(), '11-5').status === 'ok' && cand(S(), '11-5').proposable);
t('동의 철회: 11열 5번도 후보 아님', cand(S({ profile: 'noConsent' }), '11-5').status === 'hidden');
t('상대 필수 조건(1~6열) ↔ 내가 줄 7열 12번 불일치 → 제안 불가', cand(S({ profile: 'mismatch' }), '11-5').status === 'no' && cand(S({ profile: 'mismatch' }), '11-5').wantFail[0].dim === '열');
t('상대 교환 자격 정보 없음 → 보류(확인 필요), 제안 불가', cand(S({ profile: 'unknown' }), '11-5').status === 'hold' && !cand(S({ profile: 'unknown' }), '11-5').proposable);
const comp = cand(S({ profile: 'companion' }), '11-5');
t('동행 좌석(정책 확인됨): 막지 않고 제안 가능 + 경고(warn)', comp.status === 'ok' && comp.compRes === 'warn' && comp.companion.key === '11-6');
// 좌석별 정책을 모르는 동행 좌석 → 확인 필요 (보류)
const saved = P.PROFILES.companion.companion.policy;
P.PROFILES.companion.companion.policy = null;
const comp2 = cand(S({ profile: 'companion' }), '11-5');
t('동행 좌석의 좌석별 정책을 모르면 "확인 필요"로 보류', comp2.status === 'hold' && comp2.compRes === 'unknown' && !comp2.proposable);
P.PROFILES.companion.companion.policy = saved;
t('7열 12번을 지키면: 7열 13번 통로로 제안 불가, 7열 11번 확인 필요로 보류', cand(S({ keep: '7-12' }), '7-13').status === 'no' && cand(S({ keep: '7-12' }), '7-11').status === 'hold');
t('거절한 후보는 다시 제안 불가', cand(S({ declined: ['11-5'] }), '11-5').status === 'declined' && !P.proposable(S({ declined: ['11-5'] }), '11-5'));
t('상대 조건 판정은 STEP 3B evaluate 그대로 (같은 결과)', JSON.stringify(cand(S(), '11-5').theirs) === JSON.stringify(D.evaluate(P.PROFILES.basic.wants, P.MINE[0], 'theirs')));

/* ---- 상태 전이 ---- */
let r = run(S(), [{ type: 'choose', val: '11-3' }]);
t('동의 없는 좌석 선택 시도 → 무시', r.s.cand === null);
r = run(S(), [{ type: 'choose', val: '11-5' }, { type: 'send' }]);
t('확인(ack) 없이 보내기 → 머무름', r.s.step === 'select' && r.nav.stay);
r = run(S(), [{ type: 'choose', val: '11-5' }, { type: 'ack', checked: true }, { type: 'send' }]);
t('선택 + 확인 → 제안 전송(proposed), StatusSent 로', r.s.step === 'proposed' && r.nav.push === 'StatusSent');
t('제안만으로는 완료가 아님 (한쪽 의사만으로 매칭 완료 없음)', r.s.step !== 'done');
r = run(r.s, [{ type: 'back' }]);
t('진행 중 뒤로 → 머무름 (취소로만 빠져나감)', r.nav.stay && r.s.step === 'proposed');
const flow = run(S(), [{ type: 'choose', val: '11-5' }, { type: 'ack', checked: true }, { type: 'send' }, { type: 'simAccept' }]);
t('상대 수락(시뮬레이션) → accepted, PairAccepted', flow.s.step === 'accepted' && flow.nav.push === 'PairAccepted');
r = run(flow.s, [{ type: 'simOk' }]);
t('최종 확인 전에 성공 처리 불가 (STEP 3B 흐름 규칙)', r.s.step === 'accepted' && r.nav.stay);
r = run(flow.s, [{ type: 'toFinal' }, { type: 'simOk' }]);
t('최종 확인 → 성공 → done, PairDone', r.s.step === 'done' && r.nav.push === 'PairDone');
r = run(flow.s, [{ type: 'toFinal' }, { type: 'simFail' }]);
t('최종 확인 실패 → failed, ExFinalFailed', r.s.step === 'failed' && r.nav.push === 'ExFinalFailed');
r = run(flow.s, [{ type: 'toFinal' }, { type: 'cancel' }]);
t('최종 확인 중에는 취소 불가 (STEP 3B CANCELABLE 그대로)', r.s.step === 'final');
r = run(S(), [{ type: 'choose', val: '11-5' }, { type: 'ack', checked: true }, { type: 'send' }, { type: 'simDecline' }]);
t('상대 거절 → declined, 거절 목록에 기록', r.s.step === 'declined' && r.s.declined[0] === '11-5' && r.nav.push === 'PairDeclined');
const od = run(r.s, [{ type: 'otherDir' }]);
t('거절 후 반대 방향 → 7열 12번 지킴, 선택 초기화', od.s.keep === '7-12' && od.s.cand === null && od.s.step === 'select' && od.nav.reset.join() === 'PairMode,PairSeat');
const oc = run(r.s, [{ type: 'otherCandidate' }]);
t('거절 후 다른 후보 → 후보 화면, 거절한 후보는 제외 상태 유지', oc.nav.reset.slice(-1)[0] === 'PairAdjacency' && oc.s.declined.indexOf('11-5') >= 0);
r = run(S(), [{ type: 'choose', val: '11-5' }, { type: 'profile', val: 'mismatch' }]);
t('선택 후 상대 상황이 불일치로 바뀌면 선택 해제', r.s.cand === null);
r = run(S(), [{ type: 'choose', val: '11-5' }, { type: 'dir', val: '7-12' }]);
t('방향을 바꾸면 이전 방향의 후보 선택 해제', r.s.cand === null && r.s.keep === '7-12');
r = run(S(), [{ type: 'mode', val: 'general' }, { type: 'next' }]);
t('좌석·회차 교환을 고르고 다음 → 머무르며 안내', r.nav.stay && /07 일반 교환/.test(r.s.hint));
r = run(S(), [{ type: 'pick', val: '7-12', checked: false }, { type: 'next' }]);
t('티켓 1장만 고르면 진행 불가', r.nav.stay && /2장/.test(r.s.hint));
r = run(S({ formKey: 2, dirKey: 3, ackKey: 4, keep: '7-12', cand: '7-11' }), [{ type: 'home' }]);
t('처음으로: 상태 초기화 + 입력 key 갱신', r.s.keep === '11-4' && r.s.cand === null && r.s.formKey === 3 && r.s.dirKey === 4);

/* ---- 화면 데이터 ---- */
const v = P.views(S({ cand: '11-5' }), true);
t('후보 화면: 지킬 11열 4번 / 내놓을 7열 12번', v.adj.keepName === '11열 4번' && v.adj.offerName === '7열 12번');
t('보내기 전 확인: 완료 후 좌석 11열 4번, 5번 (완료 시에만)', v.warn.after === '11열 4번, 5번 · 나란히 (완료 시에만)');
t('보내기 전 확인: "아직 매칭 완료 아님" 문구', /아직 '매칭 완료'가 아니에요/.test(v.warn.twoWayNote));
t('최종 실패: 2장 모두 유지 (목표)', v.failed.keepText === '2장 모두 유지 (목표)' && /7열 12번 · 11열 4번/.test(v.failed.mine));
const dv = P.defaultViews();
t('정적 기본값: 다른 폰에는 데모 패널 없음', dv.isDemo === false && dv.adj.showProfiles === false);
t('정적 기본값: 방향 화면 = 11열 4번 지킴', dv.seat.options[0].checked === true && dv.seat.options[0].val === '11-4');
t('정적 기본값: 배치도에 통로(12·13번 사이) 표시', dv.seat.rows[0].seats[11].aisle === true && dv.seat.rows[0].seats.filter((x) => x.aisle).length === 1);
t('STEP 3B 실패 화면 기본값은 그대로 (1장 · 유지 (목표))', D.defaultViews().failed.keepText === '유지 (목표)' && D.defaultViews().failed.mine === '12.20 (일) 18:00 · 3회차 · R석 B구역 7열 12번');

const fail = results.filter((x) => !x.pass);
for (const x of results) console.log((x.pass ? 'PASS ' : 'FAIL ') + x.name);
console.log('\n합계 %d건, 실패 %d건', results.length, fail.length);
process.exit(fail.length ? 1 : 0);
