#!/usr/bin/env node
/* 일반 교환 데모 엔진 단위 테스트 (브라우저 없이). 사용법: node tools/test_demo_engine.cjs */
const D = require('./authoring/demo3b_store.js');
const results = [];
const t = (name, cond) => results.push({ name, pass: !!cond });
const C = (o) => Object.assign(JSON.parse(JSON.stringify(D.DEFAULT_COND)), o);
const res = (rows, dim) => rows.find((r) => r.dim === dim).res;

// 매칭 규칙
let r = D.search(C({ rounds: ['R3'], zones: ['A'] }));
t('같은 회차 좌석 교환: 후보 C2 (12.20 18:00 A구역 6열 3번)', r.kind === 'found' && r.best.id === 'C2');
r = D.search(C({ rounds: ['R4'] }));
t('다른 회차 교환: 후보 C1 (12.21 14:00 A구역 5열 8번)', r.kind === 'found' && r.best.id === 'C1');
t('다른 회차: C4 는 상대 필수(C구역) 불일치로 제외', r.excludedCount >= 1);
r = D.search(C({ rounds: ['R1'] }));
t('필수 불일치: 12.19 회차의 C3 는 상대 필수(12.20 14:00)가 안 맞아 mismatch', r.kind === 'mismatch' && r.best.id === 'C3' && res(r.best.b, '회차') === 'fail');
r = D.search(C({ rounds: ['R4'], zones: ['C'] }));
t('선호만 불일치: 후보로 남고 양쪽 선호 차이가 pref 로 표시', r.kind === 'found' && r.best.id === 'C1' && res(r.best.a, '구역') === 'pref' && res(r.best.b, '구역') === 'pref');
r = D.search(C({ rounds: ['R2'] }));
t('후보 없음: 12.20 14:00 회차에는 티켓이 없음', r.kind === 'none');
r = D.search(C({ rounds: ['R4'], zones: ['C'], zoneImp: '필수' }));
t('내 필수(구역 C) 불일치: C1 제외, C4 는 상대 필수 불일치 → mismatch', r.kind === 'mismatch');
const ev = D.evaluate(C({ castImp: '필수' }), D.POOL[0].ticket, 'mine');
t('캐스팅 조건이 있고 정보가 없으면 확인 필요(unknown)', res(ev, '캐스팅') === 'unknown');
r = D.search(C({ rounds: ['R4'], castImp: '필수' }));
t('필수 조건 정보가 없으면 후보로 확정하지 않음', r.kind !== 'found');

// 입력 검증
t('회차를 모두 빼면 진행 불가', D.validate(C({ rounds: [] })) !== '');
t('중요도 미선택이면 진행 불가', D.validate(C({ rowImp: null })) !== '');
t('기본 조건은 진행 가능', D.validate(C({})) === '');

// 상태 전이
const go = (s, type, extra) => D.reduce(s, Object.assign({ type }, extra || {}));
let s = D.initialState();
let o = go(s, 'imp', { row: 'round', val: '필수' });
t('같은 중요도를 다시 누르면 선택 필요(null)', o.state.cond.roundImp === null);
o = go(s, 'submit'); s = o.state;
t('신청 등록 → 교환 신청(searching), 신청 현황 화면', s.step === 'searching' && o.nav.push === 'Waiting');
o = go(s, 'notify'); s = o.state;
t('알림 도착 → 후보 발견(found), 양방향 확인 화면', s.step === 'found' && o.nav.push === 'MatchCheck' && s.candId === 'C1');
o = go(s, 'send');
t('동의 없이 제안 전송 불가', o.state.step === 'found' && o.nav.stay);
s = go(s, 'consent', { checked: true }).state;
o = go(s, 'send'); s = o.state;
t('동의 후 제안 전송 → proposed(상대방 검토)', s.step === 'proposed' && o.nav.push === 'StatusSent');
t('제안 후에는 조건 변경 불가', go(s, 'round', { val: 'R2' }).state.cond.rounds.join() === s.cond.rounds.join());
t('진행 중 뒤로는 머무름', go(s, 'back').nav.stay === true);
t('상대 수락 전에는 완료로 갈 수 없음', go(s, 'simOk').state.step === 'proposed');
let acc = go(s, 'simAccept').state;
t('상대방 수락 → accepted (완료 아님)', acc.step === 'accepted');
let fin = go(acc, 'toFinal').state;
t('최종 확인 중 → final', fin.step === 'final');
t('최종 확인 성공 → done', go(fin, 'simOk').state.step === 'done');
t('최종 확인 실패 → failed', go(fin, 'simFail').state.step === 'failed');
t('최종 확인 중에는 취소 불가', go(fin, 'cancel').state.step === 'final');
let dec = go(s, 'simDecline').state;
t('상대방 거절 → declined, 거절한 후보 기록', dec.step === 'declined' && dec.declined.indexOf('C1') >= 0);
o = go(dec, 'retry');
t('다른 후보 찾기: 거절한 C1 제외 후 재탐색', o.state.candId !== 'C1');
t('제안 단계에서 신청 취소 → cancelled', go(s, 'cancel').state.step === 'cancelled');
t('예매 상세로 → 처음 상태', go(dec, 'home').state.step === 'edit' && go(dec, 'home').nav.reset[0] === 'Main');

// 기본 화면 데이터가 기존 정적 화면과 같은 장면인지
const dv = D.defaultViews();
t('기본 조건 화면: 12.19·12.21 선택, 현재 회차 비활성', dv.request.rounds.filter((x) => x.pressed === 'true').length === 2 && dv.request.rounds[2].disabled === true);
t('기본 신청 현황 요약', dv.waiting.roundsText === '12.19 (토) 19:30, 12.21 (월) 14:00 · 필수' && dv.waiting.zonesText === 'R석 A·B구역 · 선호' && dv.waiting.rowText === '1열 ~ 10열 · 선호');
t('기본 비교 화면: 가격·정책 확인 필요', dv.compare.rows[5].k_need && dv.compare.rows[6].k_need);
t('기본 완료 화면: 12.21 A구역 5열 8번', dv.done.seat === 'R석 · A구역 5열 8번' && dv.done.date === '12.21 (월) 14:00 · 4회차');

let fail = 0;
for (const x of results) { console.log((x.pass ? 'PASS ' : 'FAIL ') + x.name); if (!x.pass) fail++; }
console.log('\n합계 %d건, 실패 %d건', results.length, fail);
process.exit(fail ? 1 : 0);
