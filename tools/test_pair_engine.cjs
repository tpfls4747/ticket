#!/usr/bin/env node
/* 연석 만들기 데모 엔진 단위 테스트 (브라우저 없이, STEP 4A 모델). 사용법: node tools/test_pair_engine.cjs */
const D = require('./authoring/demo3b_store.js');
const P = require('./authoring/demo3c_pair.js');
const results = [];
const t = (name, cond) => results.push({ name, pass: !!cond });
const S = (o) => Object.assign(P.initialState(), o || {});
const ON = (o) => S(Object.assign({ consent: true, intentDraft: true }, o || {}));      // 수신자가 '교환 제안 받기'를 켠 상태
const seat = (row, n, extra) => Object.assign({ round: 'R3', zone: 'B', row, seat: n }, extra || {});
const run = (s, actions) => actions.reduce((acc, a) => { const r = P.reduce(acc.s, a); return { s: r.state, nav: r.nav, navB: r.navB }; }, { s, nav: null, navB: null });
const cand = (s, key) => P.candidates(s).find((c) => c.key === key);
const SEND = [{ type: 'choose', val: '11-5' }, { type: 'ack', checked: true }, { type: 'send' }];

/* ---- 실제 인접 판정 (배치도) — STEP 3C 그대로 ---- */
t('같은 블록·확인된 배치도의 이웃 좌석 → 인접 (11열 4·5번)', P.adjacency(seat(11, 4), seat(11, 5)).res === 'ok');
t('번호가 이어져도 통로로 나뉘면 인접 아님 (7열 12·13번)', P.adjacency(seat(7, 12), seat(7, 13)).res === 'no' && P.adjacency(seat(7, 12), seat(7, 13)).reason === '통로로 분리');
t('배치도 데이터가 없는 구간은 "확인 필요" (7열 11·12번)', P.adjacency(seat(7, 11), seat(7, 12)).res === 'unknown');
t('같은 열이 아니면 인접 아님', P.adjacency(seat(7, 12), seat(8, 12)).res === 'no');
t('번호가 이어지지 않으면 인접 아님', P.adjacency(seat(11, 4), seat(11, 6)).res === 'no');
t('회차·구역이 다르면 인접 아님', P.adjacency(seat(11, 4), seat(11, 5, { round: 'R4' })).res === 'no' && P.adjacency(seat(11, 4), seat(11, 5, { zone: 'A' })).res === 'no');

/* ---- 교환 제안 받기 (수신자 사전 의향) ---- */
t('초기값: 수신자는 교환 제안을 받지 않음', P.initialState().consent === false && P.initialState().intentDraft === false);
t('받지 않으면 11열 5번은 후보가 아님 (hidden)', cand(S(), '11-5').status === 'hidden' && !P.proposable(S(), '11-5'));
let r = run(S(), [{ type: 'intent', val: 'on', role: 'B' }]);
t('받기를 고르기만 하면 적용 안 됨 (저장 필요)', r.s.intentDraft === true && r.s.consent === false && !P.proposable(r.s, '11-5'));
r = run(r.s, [{ type: 'intentSave', role: 'B' }]);
t('설정 저장 → 받는 중, 11열 5번 연결 가능', r.s.consent === true && P.proposable(r.s, '11-5') && /보낼 수 있어요/.test(r.s.intentMsg));
r = run(ON(), [{ type: 'choose', val: '11-5' }, { type: 'intent', val: 'off', role: 'B' }, { type: 'intentSave', role: 'B', screenA: 'PairWarn' }]);
t('철회 → 신청자 선택 해제 + 중립 안내 + 최종 비교 화면이면 후보 화면으로', r.s.consent === false && r.s.cand === null && /연결할 수 없어요/.test(r.s.notice) && r.nav.reset.slice(-1)[0] === 'PairAdjacency');
r = run(ON(), SEND.concat([{ type: 'intent', val: 'off', role: 'B' }, { type: 'intentSave', role: 'B' }]));
t('진행 중인 제안이 있으면 끌 수 없음 (받는 중 유지 + 안내)', r.s.consent === true && /끌 수 없어요/.test(r.s.intentMsg));
t('11열 3번(배경 데이터)은 제안을 받지 않음', cand(ON(), '11-3').status === 'hidden');

/* ---- 후보 판정 (엔진 내부) ---- */
t('받는 중: 11열 5번 연결 가능', cand(ON(), '11-5').status === 'ok');
t('상대 필수 조건(1~6열) ↔ 내가 제공할 7열 12번 불일치 → 불가', cand(ON({ profile: 'mismatch' }), '11-5').status === 'no' && cand(ON({ profile: 'mismatch' }), '11-5').wantFail[0].dim === '열');
t('상대 자격 정보 없음 → 보류 (확인 필요)', cand(ON({ profile: 'unknown' }), '11-5').status === 'hold');
t('동행 좌석(정책 확인됨) → 막지 않음', cand(ON({ profile: 'companion' }), '11-5').status === 'ok' && cand(ON({ profile: 'companion' }), '11-5').compRes === 'warn');
const saved = P.PROFILES.companion.companion.policy;
P.PROFILES.companion.companion.policy = null;
t('동행 좌석의 좌석별 정책을 모르면 보류', cand(ON({ profile: 'companion' }), '11-5').status === 'hold');
P.PROFILES.companion.companion.policy = saved;
t('7열 12번 유지: 7열 13번 통로로 불가, 7열 11번 확인 필요로 보류', cand(ON({ keep: '7-12' }), '7-13').status === 'no' && cand(ON({ keep: '7-12' }), '7-11').status === 'hold');
t('상대 조건 판정은 STEP 3B evaluate 그대로', JSON.stringify(cand(ON(), '11-5').theirs) === JSON.stringify(D.evaluate(P.PROFILES.basic.wants, P.MINE[0], 'theirs')));

/* ---- 개인정보: 신청자 화면 데이터 ---- */
const adjOf = (s) => P.views(s, true).adj;
const flat = (o) => JSON.stringify(o);
t('받지 않음: 후보 0, 중립 문구, 좌석별 사유 없음', adjOf(S()).cards.length === 0 && adjOf(S()).noCandidate && !/후보 아님|동의|받지 않/.test(flat(adjOf(S()))));
['mismatch', 'unknown', 'companion'].forEach((p) => {
  const a = adjOf(ON({ profile: p }));
  t('11열 5번 상황 ' + p + ': 신청자 화면에 조건·자격·동행 사유 없음', !/1~6열|불일치|자격 미확인|확인 필요|11열 6번|동행/.test(flat(a)));
});
t('배치도상 옆자리인 좌석은 좌석 정보에도 나오지 않음 (11열 3번 언급 없음)', !/11열 3번/.test(flat(adjOf(ON()))));
t('통로·배치도 정보 없음은 좌석 정보로 표시 (사람 정보 아님)', adjOf(ON({ keep: '7-12' })).facts.map((f) => f.text).join() === '인접 여부 확인 필요,옆자리 아님');
t('후보 없음 → 반대 방향 찾기 버튼', adjOf(S()).canFlip && /7열 12번 유지/.test(adjOf(S()).flipText));
t('신청자 최종 비교에 동행 정보 없음 (일반 안내만)', !/11열 6번/.test(flat(P.views(ON({ profile: 'companion', cand: '11-5' }), true).warn)));

/* ---- 수신자 화면 데이터 ---- */
let s2 = run(ON(), SEND).s;
let rv = P.views(s2, true).receive;
t('제안 도착: 내 티켓 11열 5번 · 받을 좌석 7열 12번 · 응답 가능', rv.hasProposal && /11열 5번/.test(rv.mine) && /7열 12번/.test(rv.offer) && rv.canRespond);
t('비교: 열·좌석 바뀜, 무대와 거리 4열 앞으로', rv.compare.some((c) => c.change === '11열 5번 → 7열 12번') && rv.compare.some((c) => c.text === '4열 앞으로'));
t('수락해도 최종 확인이 남는다는 안내', /최종 확인을 통과해야/.test(rv.respondNote));
t('동행 좌석 있음 → 수신자에게만 분리 안내', P.views(run(ON({ profile: 'companion' }), SEND).s, true).receive.hasCompanion && /11열 6번/.test(P.views(run(ON({ profile: 'companion' }), SEND).s, true).receive.companionText));
t('수신 의향과 제안 수락은 다른 상태 (켜 둔 상태 ≠ 수락)', ON().step === 'select' && P.views(ON(), true).receive.hasProposal === false);

/* ---- 상태 전이 ---- */
r = run(ON(), [{ type: 'choose', val: '11-3' }]);
t('받지 않는 좌석 선택 시도 → 무시', r.s.cand === null);
r = run(ON(), [{ type: 'choose', val: '11-5' }, { type: 'send' }]);
t('확인(ack) 없이 보내기 → 머무름', r.s.step === 'select' && r.nav.stay);
r = run(ON(), SEND);
t('교환 제안 보내기 → proposed · 신청자 StatusSent · 수신자 폰 PairReceive', r.s.step === 'proposed' && r.nav.push === 'StatusSent' && r.navB.push === 'PairReceive');
t('진행 중 신청자 뒤로 → 머무름', run(r.s, [{ type: 'back' }]).nav.stay);
t('수신자 뒤로 → 수신자 폰만 이전 화면', run(r.s, [{ type: 'back', role: 'B' }]).navB.pop === true && run(r.s, [{ type: 'back', role: 'B' }]).s.step === 'proposed');
const acc = run(r.s, [{ type: 'recvAccept', role: 'B' }]);
t('제안 수락 (수신자) → accepted · 신청자 PairAccepted', acc.s.step === 'accepted' && acc.nav.push === 'PairAccepted');
t('최종 확인 전에 성공 처리 불가 (STEP 3B 흐름 규칙)', run(acc.s, [{ type: 'simOk', role: 'ctl' }]).s.step === 'accepted');
t('제어판: 최종 확인 시작 → 성공 → done', run(acc.s, [{ type: 'toFinal', role: 'ctl' }, { type: 'simOk', role: 'ctl' }]).s.step === 'done');
t('최종 확인 실패 → failed · ExFinalFailed', run(acc.s, [{ type: 'toFinal', role: 'ctl' }, { type: 'simFail', role: 'ctl' }]).nav.push === 'ExFinalFailed');
t('최종 확인 중에는 취소 불가', run(acc.s, [{ type: 'toFinal', role: 'ctl' }, { type: 'cancel' }]).s.step === 'final');
const dec = run(r.s, [{ type: 'recvDecline', role: 'B' }]);
t('수신자 거절 → declined · 거절 기록 · 신청자 PairDeclined', dec.s.step === 'declined' && dec.s.declined[0] === '11-5' && dec.nav.push === 'PairDeclined');
const oc = run(dec.s, [{ type: 'otherCandidate' }]);
t('거절 후 다른 후보 → 후보 화면, 거절한 후보 다시 불가, 수신자 폰 초기화', oc.nav.reset.slice(-1)[0] === 'PairAdjacency' && !P.proposable(oc.s, '11-5') && oc.navB.reset[0] === 'PairIntent');
t('거절 카드: "거절된 제안" (신청자 자신의 제안 결과)', P.views(oc.s, true).adj.cards[0].text === '거절된 제안' && P.views(oc.s, true).adj.cards[0].cantPick);
const ts = run(dec.s, [{ type: 'toSeat' }]);
t('거절 후 이전 단계로 → 좌석 방향 화면, 유지할 좌석 그대로', ts.nav.reset.join() === 'PairMode,PairSeat' && ts.s.keep === '11-4');
const fl = run(ON(), [{ type: 'flipDir' }]);
t('반대 방향으로 찾아보기 → 7열 12번 유지, 같은 화면', fl.s.keep === '7-12' && fl.nav === null);
r = run(ON(), [{ type: 'choose', val: '11-5' }, { type: 'profile', val: 'mismatch', role: 'ctl' }]);
t('제어판에서 상대 조건이 바뀌면 선택 해제 + 중립 안내', r.s.cand === null && /연결할 수 없어요/.test(r.s.notice));
t('제안 뒤에는 티켓 상황 변경 불가', run(run(ON(), SEND).s, [{ type: 'profile', val: 'mismatch', role: 'ctl' }]).s.profile === 'basic');
r = run(ON({ keep: '7-12' }), [{ type: 'home' }]);
t('처음으로(신청자): 신청자만 초기화, 수신자 설정은 유지', r.s.keep === '11-4' && r.s.consent === true && r.navB.reset[0] === 'PairIntent');
t('전체 초기화(reset): 수신자 설정도 기본값', P.reset(ON()).consent === false);

/* ---- 공용 화면 문구 분기 ---- */
const pv = P.views(ON(), true), dv = D.views(D.initialState(), true);
t('진행 현황: 연석은 "좌석 방향 선택", 일반은 "교환 신청"', pv.sent.steps[0].label === '좌석 방향 선택' && dv.sent.steps[0].label === '교환 신청');
t('진행 현황: 둘 다 용어 기준 (교환 제안 보내기 · 제안 수락 · 최종 확인 중 · 교환 완료)', ['교환 제안 보내기', '제안 수락', '최종 확인 중', '교환 완료'].every((x) => pv.sent.steps.some((s) => s.label === x) && dv.sent.steps.some((s) => s.label === x)));
t('취소 화면: 연석 "교환 제안을 취소했어요" / 일반 "교환 신청을 취소했어요"', pv.cancelled.title === '교환 제안을 취소했어요' && dv.cancelled.title === '교환 신청을 취소했어요');
t('최종 실패: 연석 2장 / 일반 1장', P.views(ON(), true).failed.keepText === '2장 모두 유지 (목표)' && D.defaultViews().failed.keepText === '유지 (목표)');
t('정적 기본값: 다른 폰·P13 은 데모가 아님', P.defaultViews().isDemo === false && P.defaultViews().adj.canFlip === false);

const fail = results.filter((x) => !x.pass);
for (const x of results) console.log((x.pass ? 'PASS ' : 'FAIL ') + x.name);
console.log('\n합계 %d건, 실패 %d건', results.length, fail.length);
process.exit(fail.length ? 1 : 0);
