/* Seat Swap 일반 교환 데모 — 상태·매칭 엔진 (STEP 3B)
 *
 * 이 파일이 원본이다. tools/authoring/apply_demo_3b.py 가 P07(일반 교환) 페이지 로직에 그대로 넣고,
 * 같은 코드로 컴포넌트의 기본 화면 데이터를 계산하며, tools/test_demo_engine.cjs 가 단위 테스트한다.
 *
 * - 모든 티켓·조건·가격·판정은 시연용 모의 데이터다. 실제 예매처·결제·티켓 변경과 연결되지 않는다.
 * - 상대방의 수락·거절과 최종 확인 결과는 사용자가 누르는 '데모 모드' 버튼으로 시뮬레이션한다.
 * - 외부 라이브러리 없음. ES5 문법만 쓴다 (런타임의 new Function 안에서 실행됨).
 */
var DEMO = (function () {
  /* ------------------------------------------------------------------ 모의 데이터 */
  var SHOW = '2026 Blue Hour 단독 콘서트';
  var ROUNDS = [
    { id: 'R1', label: '12.19 (토) 19:30', n: 1 },
    { id: 'R2', label: '12.20 (일) 14:00', n: 2 },
    { id: 'R3', label: '12.20 (일) 18:00', n: 3 },
    { id: 'R4', label: '12.21 (월) 14:00', n: 4 },
  ];
  var ZONES = [{ id: 'A', label: 'A구역' }, { id: 'B', label: 'B구역' }, { id: 'C', label: 'C구역' }, { id: 'ANY', label: '상관없음' }];
  var ROW_LIMIT = 20;
  // 내 티켓 (A). 콘서트라 캐스팅 구분이 없다 (casting: null = 해당 없음)
  var MY = { round: 'R3', grade: 'R석', zone: 'B', row: 7, seat: 12, price: '154,000원 (가상)', casting: null, policy: '시연 판정: 교환 가능', booking: 'T26112-0471' };
  // 교환 후보 티켓과 그 소유자가 등록한 조건. null 은 '정보 없음' → 화면에 '확인 필요'
  var POOL = [
    { id: 'C1', ticket: { round: 'R4', grade: 'R석', zone: 'A', row: 5, seat: 8, price: null, casting: null, policy: null, booking: 'T26112-0839' },
      wants: { rounds: ['R3'], roundImp: '필수', zones: ['A'], zoneImp: '선호', rowMax: 20, rowImp: '무관', castImp: null } },
    { id: 'C2', ticket: { round: 'R3', grade: 'R석', zone: 'A', row: 6, seat: 3, price: '154,000원 (가상)', casting: null, policy: '시연 판정: 교환 가능', booking: 'T26112-0912' },
      wants: { rounds: ['R3'], roundImp: '필수', zones: ['B'], zoneImp: '필수', rowMax: 10, rowImp: '선호', castImp: null } },
    { id: 'C3', ticket: { round: 'R1', grade: 'R석', zone: 'B', row: 9, seat: 4, price: '154,000원 (가상)', casting: null, policy: '시연 판정: 교환 가능', booking: 'T26112-0355' },
      wants: { rounds: ['R2'], roundImp: '필수', zones: ['ANY'], zoneImp: '무관', rowMax: 20, rowImp: '무관', castImp: null } },
    { id: 'C4', ticket: { round: 'R4', grade: 'R석', zone: 'C', row: 2, seat: 7, price: '154,000원 (가상)', casting: null, policy: '시연 판정: 교환 가능', booking: 'T26112-0777' },
      wants: { rounds: ['R3'], roundImp: '필수', zones: ['C'], zoneImp: '필수', rowMax: 20, rowImp: '무관', castImp: null } },
  ];
  var DEFAULT_COND = { rounds: ['R1', 'R4'], roundImp: '필수', zones: ['A', 'B'], zoneImp: '선호', rowMax: 10, rowImp: '선호', castImp: null };
  var IMPS = ['필수', '선호', '무관'];

  /* ------------------------------------------------------------------ 표시용 문자열 */
  function round(id) { for (var i = 0; i < ROUNDS.length; i++) if (ROUNDS[i].id === id) return ROUNDS[i]; return null; }
  function roundsText(ids) {
    return ROUNDS.filter(function (r) { return ids.indexOf(r.id) >= 0; }).map(function (r) { return r.label; }).join(', ');
  }
  function zonesShort(z) { return z.indexOf('ANY') >= 0 ? '상관없음' : z.slice().sort().join('·') + '구역'; }
  function ticketLine(t) { return round(t.round).label + ' · ' + round(t.round).n + '회차 · ' + t.grade + ' ' + t.zone + '구역 ' + t.row + '열 ' + t.seat + '번'; }
  function dateLine(t) { return round(t.round).label + ' · ' + round(t.round).n + '회차'; }

  /* ------------------------------------------------------------------ 매칭 규칙 */
  // 조건 하나: res = ok(충족) | pref(선호와 다름) | fail(필수 불일치) | skip(무관·해당 없음) | unknown(정보 없음)
  function judge(imp, pass) {
    if (imp === '무관' || imp === null) return 'skip';
    if (pass === null) return 'unknown';
    if (pass) return 'ok';
    return imp === '필수' ? 'fail' : 'pref';
  }
  // cond(원하는 조건) 를 ticket(상대 티켓) 에 적용. side = 'mine'(내 조건↔후보 티켓) | 'theirs'(후보 조건↔내 티켓)
  function evaluate(cond, t, side) {
    var who = side === 'mine' ? '내 조건 ' : '후보 조건 ';
    var obj = side === 'mine' ? ' · 후보 ' : ' · 내 티켓 ';
    var rows = [];
    var zAny = cond.zones.indexOf('ANY') >= 0;
    rows.push({ dim: '회차', imp: cond.roundImp, res: judge(cond.roundImp, cond.rounds.indexOf(t.round) >= 0),
      detail: (cond.roundImp === '무관' ? who + '없음' : who + roundsText(cond.rounds)) + obj + round(t.round).n + '회차',
      want: roundsText(cond.rounds), have: round(t.round).label });
    rows.push({ dim: '구역', imp: zAny ? '무관' : cond.zoneImp, res: zAny ? 'skip' : judge(cond.zoneImp, cond.zones.indexOf(t.zone) >= 0),
      detail: (zAny || cond.zoneImp === '무관' ? who + '없음' : who + zonesShort(cond.zones) + obj + t.zone + '구역'),
      want: zonesShort(cond.zones), have: t.zone + '구역' });
    rows.push({ dim: '열', imp: cond.rowImp, res: judge(cond.rowImp, t.row >= 1 && t.row <= cond.rowMax),
      detail: (cond.rowImp === '무관' ? who + '없음' : who + '1~' + cond.rowMax + '열' + obj + t.row + '열'),
      want: '1~' + cond.rowMax + '열', have: t.row + '열' });
    if (cond.castImp === '필수' || cond.castImp === '선호') {
      rows.push({ dim: '캐스팅', imp: cond.castImp, res: judge(cond.castImp, t.casting === null ? null : true),
        detail: who + '캐스팅' + obj + (t.casting || '정보 없음'), want: '캐스팅', have: t.casting || '정보 없음' });
    }
    return rows;
  }
  function count(rows, res) { return rows.filter(function (r) { return r.res === res; }).length; }
  function unknownInfo(t) {
    var u = [];
    if (t.price === null) u.push('권종·가격');
    if (t.policy === null) u.push('정책 확인 상태');
    return u;
  }
  // 후보 탐색. 결과: found(양쪽 필수 충족) | mismatch(선택한 회차에 티켓은 있지만 필수가 안 맞음) | none(선택한 회차에 티켓 없음)
  function search(cond, excluded) {
    var all = POOL.filter(function (c) { return (excluded || []).indexOf(c.id) < 0; }).map(function (c) {
      var a = evaluate(cond, c.ticket, 'mine');
      var b = evaluate(c.wants, MY, 'theirs');
      var reqUnknown = a.concat(b).filter(function (r) { return r.res === 'unknown' && r.imp === '필수'; }).length;
      return { id: c.id, c: c, a: a, b: b, fails: count(a, 'fail') + count(b, 'fail') + reqUnknown,
        prefs: count(a, 'pref') + count(b, 'pref'), inRound: a[0].res !== 'fail' };
    });
    var eligible = all.filter(function (x) { return x.fails === 0; }).sort(function (x, y) { return x.prefs - y.prefs; });
    var inRound = all.filter(function (x) { return x.inRound && x.fails > 0; }).sort(function (x, y) { return x.fails - y.fails; });
    var excluded2 = all.filter(function (x) { return x.fails > 0; }).length;
    if (eligible.length) return { kind: 'found', best: eligible[0], eligibleCount: eligible.length, excludedCount: excluded2 };
    if (inRound.length) return { kind: 'mismatch', best: inRound[0], eligibleCount: 0, excludedCount: excluded2 };
    return { kind: 'none', best: null, eligibleCount: 0, excludedCount: excluded2 };
  }
  function validate(cond) {
    if (!cond.rounds.length) return '원하는 회차를 1개 이상 선택해 주세요.';
    if (!cond.zones.length) return "원하는 구역을 고르거나 '상관없음'을 선택해 주세요.";
    if (cond.roundImp === null || cond.rowImp === null || (cond.zoneImp === null && cond.zones.indexOf('ANY') < 0)) {
      return "중요도를 모두 선택해 주세요. 고르지 않은 조건은 '무관'으로 처리하지 않아요.";
    }
    if (cond.rounds.length === 1 && cond.rounds[0] === MY.round && cond.roundImp === '필수'
        && cond.zones.indexOf(MY.zone) >= 0 && cond.zones.length === 1 && cond.zoneImp === '필수' && MY.row <= cond.rowMax && cond.rowImp === '필수') {
      return '지금 좌석과 같은 조건이에요. 다른 구역이나 열을 포함해 주세요.';
    }
    return '';
  }

  /* ------------------------------------------------------------------ 상태 */
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function initialState() {
    return { cond: clone(DEFAULT_COND), step: 'edit', candId: null, result: null, consent: false, consentKey: 0, declined: [] };
  }
  function toggle(list, v) {
    var i = list.indexOf(v);
    if (i >= 0) list.splice(i, 1); else list.push(v);
    return list;
  }
  var ACTIVE = ['proposed', 'accepted', 'final'];
  // 제안 이후 공용 진행 흐름 (STEP 3C 연석 만들기도 같은 규칙을 쓴다): 행동 → [필요한 현재 단계, 다음 단계]
  // 상대방의 제안 수락·거절과 최종 확인 결과는 시연 제어판(폰 밖) 또는 수신자 체험 폰에서만 일어나는 시뮬레이션이다.
  var FLOW = { simAccept: ['proposed', 'accepted'], simDecline: ['proposed', 'declined'], toFinal: ['accepted', 'final'],
               simOk: ['final', 'done'], simFail: ['final', 'failed'] };
  function flowNext(step, type) { var f = FLOW[type]; return f && f[0] === step ? f[1] : null; }
  // 신청자가 취소할 수 있는 단계 (최종 확인 시작 전까지)
  var CANCELABLE = ['searching', 'found', 'mismatch', 'none', 'proposed', 'accepted', 'declined'];
  var TERMINAL = ['declined', 'cancelled', 'failed', 'done'];
  var FLOW_SCREEN = { accepted: 'StatusAccepted', declined: 'ExDeclined', final: 'StatusFinal', done: 'Done', failed: 'ExFinalFailed' };

  // action: { type, val, row, checked, screen } → { state, nav }
  // nav: null | {push: 화면} | {reset: [화면...]} | {pop: true} | {stay: true}
  function reduce(st, action) {
    var s = clone(st);
    var c = s.cond;
    var t = action.type;
    var editing = function () { s.step = 'edit'; s.result = null; s.candId = null; s.consent = false; s.consentKey += 1; };
    var runSearch = function () {
      var r = search(c, s.declined);
      s.result = { kind: r.kind, id: r.best ? r.best.id : null, eligibleCount: r.eligibleCount, excludedCount: r.excludedCount };
      s.candId = r.best ? r.best.id : null;
      s.consent = false; s.consentKey += 1;
      s.step = r.kind === 'found' ? 'found' : r.kind;
      return r.kind === 'found' ? 'MatchCheck' : r.kind === 'mismatch' ? 'ExMismatch' : 'ExNoCandidate';
    };
    switch (t) {
      case 'round':
        if (ACTIVE.indexOf(s.step) >= 0) return { state: st, nav: null };
        toggle(c.rounds, action.val); editing(); return { state: s, nav: null };
      case 'zone':
        if (ACTIVE.indexOf(s.step) >= 0) return { state: st, nav: null };
        if (action.val === 'ANY') { c.zones = c.zones.indexOf('ANY') >= 0 ? [] : ['ANY']; if (c.zones.length) c.zoneImp = '무관'; }
        else {
          // ‘상관없음’에서 특정 구역으로 바꾸면 중요도를 다시 고르게 한다 (‘무관’으로 남겨 조건이 무시되지 않게)
          if (c.zones.indexOf('ANY') >= 0) c.zoneImp = null;
          c.zones = c.zones.filter(function (z) { return z !== 'ANY'; }); toggle(c.zones, action.val);
        }
        editing(); return { state: s, nav: null };
      case 'imp':
        if (ACTIVE.indexOf(s.step) >= 0 || IMPS.indexOf(action.val) < 0) return { state: st, nav: null };
        var key = { round: 'roundImp', zone: 'zoneImp', row: 'rowImp' }[action.row];
        if (!key) return { state: st, nav: null };
        c[key] = c[key] === action.val ? null : action.val;   // 같은 값을 다시 누르면 '선택 필요'로
        editing(); return { state: s, nav: null };
      case 'rowMinus':
        if (c.rowMax > 1) { c.rowMax -= 1; editing(); } return { state: s, nav: null };
      case 'rowPlus':
        if (c.rowMax < ROW_LIMIT) { c.rowMax += 1; editing(); } return { state: s, nav: null };
      case 'start':
        if (ACTIVE.indexOf(s.step) >= 0) return { state: st, nav: { stay: true } };
        editing(); return { state: s, nav: { push: 'Request' } };
      case 'edit':
        if (ACTIVE.indexOf(s.step) >= 0) return { state: st, nav: { stay: true } };
        editing(); return { state: s, nav: { push: 'Request' } };
      case 'submit':
        if (validate(c)) return { state: st, nav: { stay: true } };
        s.step = 'searching'; s.result = null; s.candId = null;
        return { state: s, nav: { push: 'Waiting' } };
      case 'notify':
        if (s.step !== 'searching' && s.step !== 'found' && s.step !== 'mismatch' && s.step !== 'none') return { state: st, nav: { stay: true } };
        return { state: s, nav: { push: runSearch() } };
      case 'retry':          // 거절된 뒤 다른 후보 찾기 (거절한 후보는 제외)
        return { state: s, nav: { reset: ['Main', 'Request', 'Waiting', runSearch()] } };
      case 'toCompare':
        if (s.step !== 'found') return { state: st, nav: { stay: true } };
        return { state: s, nav: { push: 'Compare' } };
      case 'consent':
        if (s.step !== 'found') return { state: st, nav: null };
        s.consent = !!action.checked; return { state: s, nav: null };
      case 'send':
        if (s.step !== 'found' || !s.consent) return { state: st, nav: { stay: true } };
        s.step = 'proposed'; return { state: s, nav: { push: 'StatusSent' } };
      case 'simAccept': case 'simDecline': case 'toFinal': case 'simOk': case 'simFail':
        var nx = flowNext(s.step, t);
        if (!nx) return { state: st, nav: { stay: true } };
        s.step = nx; if (nx === 'declined') s.declined.push(s.candId);
        return { state: s, nav: { push: FLOW_SCREEN[nx] } };
      case 'cancel':         // 신청자 취소 (최종 확인 시작 전까지)
        if (CANCELABLE.indexOf(s.step) < 0) return { state: st, nav: { stay: true } };
        s.cancelledFrom = s.step; s.step = 'cancelled'; return { state: s, nav: { push: 'ExCancelled' } };
      case 'relax':          // 필수 불일치 화면: 내 쪽에서 불일치한 필수 조건을 선호로 바꾸고 조건 화면으로
        var r = search(c, s.declined);
        if (!r.best) return { state: st, nav: { stay: true } };
        var changed = false;
        r.best.a.forEach(function (row) {
          if (row.res === 'fail') { var k = { '회차': 'roundImp', '구역': 'zoneImp', '열': 'rowImp' }[row.dim]; if (k) { c[k] = '선호'; changed = true; } }
        });
        if (!changed) return { state: st, nav: { stay: true } };
        editing(); return { state: s, nav: { reset: ['Main', 'Request'] } };
      case 'restart':        // 조건은 유지하고 다시 신청
        editing(); s.declined = []; return { state: s, nav: { reset: ['Main', 'Request'] } };
      case 'home':           // 예매 상세로: 데모를 처음 상태로
        return { state: initialState(), nav: { reset: ['Main'] } };
      case 'back':
        if (ACTIVE.indexOf(s.step) >= 0) return { state: st, nav: { stay: true } };       // 진행 중에는 '취소'로만 빠져나간다
        if (TERMINAL.indexOf(s.step) >= 0) return { state: initialState(), nav: { reset: ['Main'] } };
        if (action.screen === 'MatchCheck' || action.screen === 'ExMismatch' || action.screen === 'ExNoCandidate') s.step = 'searching';
        return { state: s, nav: { pop: true } };
      default:
        return { state: st, nav: null };
    }
  }

  /* ------------------------------------------------------------------ 화면 데이터 (컴포넌트는 이 값만 그린다) */
  var STY = {
    roundOn: 'height: 46px; border: 1.5px solid #5B3DF5; border-radius: 12px; background: #F0EDFF; font-family: inherit; font-size: 14px; font-weight: 700; color: #3A26C4',
    roundOff: 'height: 46px; border: 1px solid #DADDE3; border-radius: 12px; background: #FFFFFF; font-family: inherit; font-size: 14px; font-weight: 500; color: #191B22',
    curOff: 'height: 46px; border: 1px dashed #DADDE3; border-radius: 12px; background: #F5F6F8; font-family: inherit; font-size: 13px; font-weight: 500; color: #6B7080; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px',
    curOn: 'height: 46px; border: 1.5px solid #5B3DF5; border-radius: 12px; background: #F0EDFF; font-family: inherit; font-size: 13px; font-weight: 700; color: #3A26C4; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px',
    zoneOn: 'height: 38px; padding: 0 16px; border: 1.5px solid #5B3DF5; border-radius: 22px; background: #F0EDFF; font-family: inherit; font-size: 14px; font-weight: 700; color: #3A26C4',
    zoneOff: 'height: 38px; padding: 0 16px; border: 1px solid #DADDE3; border-radius: 22px; background: #FFFFFF; font-family: inherit; font-size: 14px; font-weight: 500; color: #191B22',
    segBase: 'height: 28px; padding: 0 10px; font-family: inherit; font-size: 12px; border-radius: 8px; ',
    segOff: 'background: #FFFFFF; color: #4A4F5C; font-weight: 500; border: 1px solid #DADDE3',
    seg: { '필수': 'background: #191B22; color: #FFFFFF; font-weight: 700; border: 1px solid #191B22',
           '선호': 'background: #E9E5FF; color: #3A26C4; font-weight: 700; border: 1px solid #E9E5FF',
           '무관': 'background: #E6E8EC; color: #4A4F5C; font-weight: 700; border: 1px solid #E6E8EC' },
    segWrap: 'display: flex; gap: 4px',
    segWrapNone: 'display: flex; gap: 4px; padding: 3px; border-radius: 11px; border: 1.5px dashed #D9620F; background: #FFF8F2',
    impTag: { '필수': 'font-size: 11px; font-weight: 700; color: #FFFFFF; background: #191B22; padding: 2px 6px; border-radius: 4px',
              '선호': 'font-size: 11px; font-weight: 700; color: #3A26C4; background: #E9E5FF; padding: 2px 6px; border-radius: 4px',
              '무관': 'font-size: 11px; font-weight: 700; color: #4A4F5C; background: #E6E8EC; padding: 2px 6px; border-radius: 4px' },
    noteBox: 'background: #F5F6F8; border-radius: 14px; padding: 14px 16px; display: flex; gap: 10px; align-items: flex-start',
    noteBoxErr: 'background: #FFF1E6; border-radius: 14px; padding: 14px 16px; display: flex; gap: 10px; align-items: flex-start',
    noteText: 'margin: 0; font-size: 13px; line-height: 1.55; color: #4A4F5C',
    noteTextErr: 'margin: 0; font-size: 13px; line-height: 1.55; color: #A3440B; font-weight: 700',
  };
  var NOTE = "중요도를 고르지 않은 조건은 '무관'으로 처리하지 않아요. 필수는 맞지 않으면 후보에서 제외돼요. 양쪽 수락과 최종 확인이 끝나야 교환이 완료돼요 (서비스 설계 가정).";
  var RES_TEXT = { ok: '충족', pref: '선호와 달라요', fail: '불일치', skip: '비교 안 함', unknown: '확인 필요' };
  var RES_KIND = { ok: 'ok', pref: 'plan', fail: 'no', skip: 'mute', unknown: 'need' };

  function seg(row, imp) {
    return { wrap: imp ? STY.segWrap : STY.segWrapNone, items: IMPS.map(function (n) {
      return { name: n, row: row, pressed: n === imp ? 'true' : 'false', style: STY.segBase + (n === imp ? STY.seg[n] : STY.segOff) };
    }) };
  }
  function flags(kind) { return { k_ok: kind === 'ok', k_plan: kind === 'plan', k_no: kind === 'no', k_mute: kind === 'mute', k_need: kind === 'need' }; }
  function resultRow(r, side) {
    var kind = RES_KIND[r.res];
    var note = '';
    if (r.res === 'pref') note = side === 'mine' ? '필수가 아니라 후보로 남겨요. 내 선호는 ' + r.want + '이지만 후보는 ' + r.have + '이에요.' : '필수가 아니라 후보로 남겨요. 후보는 ' + r.want + '을 선호해요.';
    if (r.res === 'fail') note = side === 'mine' ? '내 필수 조건이라 이 후보는 제외돼요.' : '후보의 필수 조건이라 이 후보는 제외돼요. 상대의 조건은 내가 바꿀 수 없어요.';
    if (r.res === 'unknown') note = '정보가 없어 추정하지 않아요. 확인 전에는 후보로 확정하지 않아요.';
    var o = { label: r.dim, imp: r.imp === null ? '선택 필요' : r.imp, impStyle: STY.impTag[r.imp] || STY.impTag['무관'], detail: r.detail, text: RES_TEXT[r.res], note: note, hasNote: !!note };
    var f = flags(kind); for (var k in f) o[k] = f[k];
    return o;
  }
  function badgeItem(kind, text) { var o = { text: text }; var f = flags(kind); for (var k in f) o[k] = f[k]; return o; }

  function viewRequest(c, demo) {
    var err = demo ? validate(c) : '';
    return {
      rounds: ROUNDS.map(function (r) {
        var on = c.rounds.indexOf(r.id) >= 0;
        if (r.id === MY.round) {
          if (!demo) return { label: r.label, sub: '현재 회차', val: r.id, pressed: 'false', disabled: true, style: STY.curOff };
          return { label: r.label, sub: '현재 회차 · 좌석만', val: r.id, pressed: on ? 'true' : 'false', disabled: false, style: on ? STY.curOn : STY.curOff };
        }
        return { label: r.label, sub: '', val: r.id, pressed: on ? 'true' : 'false', disabled: false, style: on ? STY.roundOn : STY.roundOff };
      }),
      roundSeg: seg('round', c.roundImp),
      zones: ZONES.map(function (z) {
        var on = c.zones.indexOf(z.id) >= 0;
        return { label: z.label, val: z.id, pressed: on ? 'true' : 'false', style: on ? STY.zoneOn : STY.zoneOff };
      }),
      zoneSeg: seg('zone', c.zones.indexOf('ANY') >= 0 ? '무관' : c.zoneImp),
      rowLabel: '1열 ~ ' + c.rowMax + '열',
      rowPct: (c.rowMax / ROW_LIMIT * 100) + '%',
      rowSeg: seg('row', c.rowImp),
      showStep: !!demo, canMinus: c.rowMax > 1, cantMinus: c.rowMax <= 1, canPlus: c.rowMax < ROW_LIMIT, cantPlus: c.rowMax >= ROW_LIMIT,
      stepLabel: c.rowMax + '열까지',
      note: err || NOTE, noteBox: err ? STY.noteBoxErr : STY.noteBox, noteText: err ? STY.noteTextErr : STY.noteText,
      valid: !err, invalid: !!err, stepper: stepper(GEN_STEPS, 0),
    };
  }
  function viewWaiting(c) {
    var imp = function (v) { return v === null ? '선택 필요' : v; };
    return {
      roundsText: roundsText(c.rounds) + ' · ' + imp(c.roundImp),
      zonesText: c.zones.indexOf('ANY') >= 0 ? 'R석 전체 (상관없음)' : 'R석 ' + zonesShort(c.zones) + ' · ' + imp(c.zoneImp),
      rowText: '1열 ~ ' + c.rowMax + '열 · ' + imp(c.rowImp), stepper: stepper(GEN_STEPS, 1),
    };
  }
  function viewMatch(c, id) {
    var x = search(c, []);
    var cand = POOL.filter(function (p) { return p.id === id; })[0];
    var a = evaluate(c, cand.ticket, 'mine').filter(function (r) { return true; });
    var b = evaluate(cand.wants, MY, 'theirs');
    var unknown = unknownInfo(cand.ticket);
    var mineOk = count(a, 'fail') === 0, theirsOk = count(b, 'fail') === 0;
    return {
      mine: ticketLine(MY), cand: ticketLine(cand.ticket),
      dirA: a.map(function (r) { return resultRow(r, 'mine'); }),
      dirB: b.map(function (r) { return resultRow(r, 'theirs'); }),
      badges: [badgeItem(mineOk ? 'ok' : 'no', mineOk ? '내 필수 충족' : '내 필수 불일치'),
               badgeItem(theirsOk ? 'ok' : 'no', theirsOk ? '후보 필수 충족' : '후보 필수 불일치')]
        .concat(unknown.length ? [badgeItem('need', '미확인 ' + unknown.length + '건')] : []),
      summary: (unknown.length ? '미확인: 후보 티켓의 ' + unknown.join(', ') + '. ' : '') + "아직 '매칭 완료'가 아니고, 한쪽만 맞아도 완료로 표시하지 않아요.",
      excludedNote: x.excludedCount ? '필수 조건이 맞지 않아 제외한 티켓 ' + x.excludedCount + '장' : '',
      // STEP 4B 정보 위계: ① 공연·회차 ② 교환 전후 좌석 ③ 필수 충족 ④ 선호 차이 ⑤ 상태 ⑥ 부가 정보(전체 조건은 접힘)
      hero: hero(cand.ticket),
      reqOk: mineOk && theirsOk, reqNo: !(mineOk && theirsOk),
      reqText: mineOk && theirsOk ? '필수 조건: 양쪽 모두 충족' : '필수 조건: 맞지 않는 항목이 있어요',
      prefRows: a.filter(function (r) { return r.res === 'pref'; }).map(function (r) { return resultRow(r, 'mine'); })
        .concat(b.filter(function (r) { return r.res === 'pref'; }).map(function (r) { return resultRow(r, 'theirs'); })),
      hasPref: a.concat(b).some(function (r) { return r.res === 'pref'; }), noPref: !a.concat(b).some(function (r) { return r.res === 'pref'; }),
      stepper: stepper(GEN_STEPS, 1),
    };
  }
  function cmp(label, a, b, kind, text) { var o = { label: label, a: a, b: b, text: text }; var f = flags(kind); for (var k in f) o[k] = f[k]; return o; }
  // 교환 전후 핵심 (공연·회차 → 좌석)
  function hero(t) {
    var sameDate = dateLine(MY) === dateLine(t);
    return { show: SHOW, date: sameDate ? dateLine(MY) + ' · 같은 회차' : dateLine(MY) + ' → ' + dateLine(t),
      from: MY.grade + ' ' + MY.zone + '구역 ' + MY.row + '열 ' + MY.seat + '번', to: t.grade + ' ' + t.zone + '구역 ' + t.row + '열 ' + t.seat + '번' };
  }
  function splitRows(rows) {
    return { diffRows: rows.filter(function (r) { return !r.k_mute; }), sameRows: rows.filter(function (r) { return r.k_mute; }),
      sameTitle: '같은 항목 ' + rows.filter(function (r) { return r.k_mute; }).length + '개 보기' };
  }
  function viewNone() { return { stepper: stepper(GEN_STEPS, 1, 'fail', '맞는 후보 없음 · 신청은 유지') }; }
  function viewDeclined() { return { stepper: stepper(GEN_STEPS, 3, 'fail', '상대방이 제안을 거절 · 내 티켓 그대로') }; }
  function viewCompare(id, consent, consentKey, step) {
    var t = POOL.filter(function (p) { return p.id === id; })[0].ticket;
    var same = function (x, y) { return x === y ? ['mute', '같음'] : ['plan', '다름']; };
    var d = same(dateLine(MY), dateLine(t)), z = same(MY.zone, t.zone), s = same(MY.row + '-' + MY.seat, t.row + '-' + t.seat);
    var canSend = step === 'found' && consent;
    var rows = [
        cmp('공연명', SHOW, SHOW, 'mute', '같음'),
        cmp('날짜·회차', dateLine(MY), dateLine(t), d[0], d[1]),
        cmp('구역', MY.grade + ' ' + MY.zone + '구역', t.grade + ' ' + t.zone + '구역', z[0], z[1]),
        cmp('열·좌석', MY.row + '열 ' + MY.seat + '번', t.row + '열 ' + t.seat + '번', s[0], s[1]),
        cmp('캐스팅', MY.casting || '해당 없음', t.casting || '해당 없음', 'mute', '같음'),
        t.price === null ? cmp('권종·가격', MY.grade + ' · ' + MY.price, t.grade + ' · 가격 정보 없음', 'need', '확인 필요')
                         : cmp('권종·가격', MY.grade + ' · ' + MY.price, t.grade + ' · ' + t.price, MY.price === t.price ? 'mute' : 'plan', MY.price === t.price ? '같음' : '다름'),
        t.policy === null ? cmp('정책 확인', MY.policy, '정책 확인 상태 없음', 'need', '확인 필요')
                          : cmp('정책 확인', MY.policy, t.policy, 'mute', '같음'),
      ];
    var sp = splitRows(rows);
    return {
      rows: rows, diffRows: sp.diffRows, sameRows: sp.sameRows, sameTitle: sp.sameTitle,
      consentKey: 'consent-' + consentKey, canSend: canSend, cantSend: !canSend,
      sendHint: step !== 'found' ? '이미 제안을 보냈거나 진행할 수 없는 상태예요.' : (consent ? '' : '위 동의 항목을 선택하면 제안을 보낼 수 있어요.'),
      hero: hero(t), stepper: stepper(GEN_STEPS, 2),
    };
  }
  function viewDone(id) {
    var t = POOL.filter(function (p) { return p.id === id; })[0].ticket;
    return { date: dateLine(t), seat: t.grade + ' · ' + t.zone + '구역 ' + t.row + '열 ' + t.seat + '번', booking: t.booking,
      prev: round(MY.round).label + ' · ' + MY.zone + '구역 ' + MY.row + '열 ' + MY.seat + '번' };
  }
  function viewMismatch(c, declined) {
    var r = search(c, declined || []);
    if (!r.best) return { rows: [], canRelax: false, cantRelax: true, cand: '', stepper: stepper(GEN_STEPS, 1, 'fail', '필수 조건이 맞지 않아 후보에서 제외') };
    var rows = r.best.a.map(function (x) { return { r: x, side: 'mine' }; }).concat(r.best.b.map(function (x) { return { r: x, side: 'theirs' }; }));
    var fails = rows.filter(function (x) { return x.r.res === 'fail' || (x.r.res === 'unknown' && x.r.imp === '필수'); });
    var oks = rows.filter(function (x) { return x.r.res === 'ok'; }).slice(0, 1);
    var mineFail = r.best.a.filter(function (x) { return x.res === 'fail'; }).length > 0;
    return { cand: ticketLine(r.best.c.ticket), rows: fails.concat(oks).map(function (x) { return resultRow(x.r, x.side); }),
      canRelax: mineFail, cantRelax: !mineFail, stepper: stepper(GEN_STEPS, 1, 'fail', '필수 조건이 맞지 않아 후보에서 제외') };
  }
  // 최종 확인 실패 화면: 유지되는 내 티켓 (목표 UX)
  function viewFailed() { return { mine: ticketLine(MY), keepText: '유지 (목표)', stepper: stepper(GEN_STEPS, 4, 'fail', '최종 확인 실패 · 내 티켓 유지 (목표)') }; }

  /* ---- STEP 4A: 일반 교환·연석 교환이 함께 쓰는 화면의 문구 분기 · 시연 제어판 · 상태 안내 ---- */
  // 용어 기준: 교환 제안 받기(사전 수신 의향) · 교환 제안 보내기(신청자) · 제안 수락(수신자 개별 동의) · 최종 확인 중 · 교환 완료
  var TL_COLOR = { done: '#191B22', now: '#3A26C4', todo: '#8B909C' };
  var TL_TEXT = { done: '완료', now: '지금 단계', todo: '남은 단계' };
  function timeline(list, nowIdx) {
    return list.map(function (x, i) {
      var st = i < nowIdx ? 'done' : i === nowIdx ? 'now' : 'todo';
      return { label: x[0], sub: x[1], done: st === 'done', now: st === 'now', todo: st === 'todo', hasLine: i < list.length - 1,
        color: TL_COLOR[st], stText: TL_TEXT[st] };
    });
  }
  /* ---- STEP 4B: 공용 단계 표시 (일반 교환·연석 교환) ----
   * items 하나 = 단계. state: done(완료) | now(현재) | todo(남은 단계) | fail(실패·거절) | stop(취소로 중단)
   * 색만이 아니라 텍스트(현재 단계 이름, 상태 문구, 스크린 리더용 단계 상태)로도 전달한다. */
  var STEP_BAR = { done: 'background: #5B3DF5', now: 'background: #5B3DF5; box-shadow: 0 0 0 2px #FFFFFF, 0 0 0 4px #5B3DF5',
    todo: 'background: #E6E8EC', fail: 'background: #B03A3A', stop: 'background: #8B909C' };
  var STEP_SR = { done: '완료', now: '현재 단계', todo: '남은 단계', fail: '실패', stop: '중단' };
  function stepper(list, idx, end, endText, exp) {
    // end: null | 'fail' | 'stop' | 'done' — idx 단계에서 끝난 상태
    var items = list.map(function (label, i) {
      var st = end === 'done' ? 'done' : i < idx ? 'done' : i > idx ? 'todo' : (end || 'now');
      return { label: label, n: i + 1, bar: 'display: block; height: 6px; border-radius: 3px; ' + STEP_BAR[st], cur: i === idx && !end ? 'step' : 'false',
        sr: (i + 1) + '단계 ' + label + ': ' + STEP_SR[st] };
    });
    var head = end === 'done' ? '모든 단계 완료' : '단계 ' + (idx + 1) + '/' + list.length + ' · ' + list[idx];
    var color = end === 'fail' ? '#B03A3A' : end === 'stop' ? '#4A4F5C' : end === 'done' ? '#1F7A4D' : '#3A26C4';
    return { items: items, head: head, headStyle: 'font-size: 14px; font-weight: 700; color: ' + color,
      note: !end && idx + 1 < list.length ? '다음: ' + list[idx + 1] : '', hasNote: !end && idx + 1 < list.length,
      endNote: end && endText ? endText : '', hasEnd: !!(end && endText),
      noteStyle: 'font-size: 12px; font-weight: 700; ' + (end === 'fail' ? 'color: #B03A3A' : end === 'stop' ? 'color: #4A4F5C' : 'color: #5F6370'),
      exp: !!exp, label: '진행 단계: ' + head + (end && endText ? ', ' + endText : '') };
  }
  var GEN_STEPS = ['조건 등록', '후보 확인', '비교·제안', '상대 수락', '최종 확인', '교환 완료'];
  var GEN_CANCEL_AT = { searching: 1, found: 1, mismatch: 1, none: 1, proposed: 3, accepted: 4, declined: 3 };
  var SENT_STEPS = [['교환 신청', '조건 등록 완료'], ['후보 확인', '양방향 조건 확인 통과'], ['교환 제안 보내기', '비교 화면에서 내 동의 완료'],
    ['상대방 검토', '응답 기한은 가상 규칙이에요 (예: 12시간)'], ['제안 수락', '상대방이 제안을 수락해야 다음으로 가요'],
    ['최종 확인 중', '티켓·조건을 마지막으로 확인해요'], ['교환 완료', '최종 확인을 통과해야 표시돼요']];
  function viewSent() { return { steps: timeline(SENT_STEPS, 3), sub: '상대방이 검토하는 동안 내 티켓은 그대로 유효해요.' }; }
  function viewCancelled(from) {
    return { stepper: stepper(GEN_STEPS, GEN_CANCEL_AT[from] === undefined ? 3 : GEN_CANCEL_AT[from], 'stop', '신청 취소 · 내 티켓 그대로'), title: '교환 신청을 취소했어요',
      body: "진행 중이던 제안은 닫혔어요. 상대방에게는 '취소됨'으로 보인다고 가정했어요 (서비스 설계 가정). 내 티켓은 그대로 유효해요.",
      primary: '교환 다시 신청', secondary: '예매 상세로' };
  }
  var STATUS = { edit: '조건 입력 중', searching: '후보 찾는 중', found: '후보 확인 중', mismatch: '필수 조건 불일치', none: '맞는 후보 없음',
    proposed: '교환 제안 보냄 · 상대방 검토 중', accepted: '상대방 제안 수락 · 최종 확인 전', final: '최종 확인 중', done: '교환 완료 (시연)',
    declined: '상대방이 제안을 거절함', cancelled: '교환 신청 취소', failed: '최종 확인 실패 · 내 티켓 유지 (목표)' };
  // 시연 제어판 (폰 밖, 실제 서비스 기능 아님): 상대방 계정의 응답과 예매처의 최종 확인 결과를 정한다
  var CTL_STY = {
    primary: 'height: 34px; padding: 0 12px; border-radius: 10px; font-family: inherit; font-size: 13px; font-weight: 700; background: #191B22; color: #FFFFFF; border: 0',
    bad: 'height: 34px; padding: 0 12px; border-radius: 10px; font-family: inherit; font-size: 13px; font-weight: 700; background: #FFFFFF; color: #B03A3A; border: 1.5px solid #B03A3A' };
  function ctlBtn(act, label, kind) { return { act: act, val: '', label: label, style: CTL_STY[kind || 'primary'], pressed: 'false' }; }
  function viewCtl(s) {
    var b = [], hint;
    if (s.step === 'proposed') { hint = '상대방 계정의 응답을 정해 보세요.'; b = [ctlBtn('simAccept', '상대방 제안 수락'), ctlBtn('simDecline', '상대방 거절', 'bad')]; }
    else if (s.step === 'accepted') { hint = '양쪽이 수락했어요. 예매처의 최종 확인을 시작해요.'; b = [ctlBtn('toFinal', '최종 확인 시작')]; }
    else if (s.step === 'final') { hint = '최종 확인 결과를 정해 보세요.'; b = [ctlBtn('simOk', '최종 확인 성공'), ctlBtn('simFail', '최종 확인 실패', 'bad')]; }
    else if (TERMINAL.indexOf(s.step) >= 0) { hint = "결과 화면이에요. '처음부터 다시'로 다시 체험해요."; }
    else { hint = '폰에서 교환 제안을 보내면 여기서 상대방 응답을 정해요.'; }
    return { hint: hint, buttons: b, hasButtons: b.length > 0, status: STATUS[s.step] || '' };
  }
  function views(s, demo) {
    var v = { isDemo: !!demo, step: s.step, request: viewRequest(s.cond, demo), waiting: viewWaiting(s.cond), failed: viewFailed(),
      sent: viewSent(), cancelled: viewCancelled(s.cancelledFrom), ctl: viewCtl(s), statusA: STATUS[s.step] || '',
      none: viewNone(), declined: viewDeclined() };
    if (s.candId) { v.match = viewMatch(s.cond, s.candId); v.compare = viewCompare(s.candId, s.consent, s.consentKey, s.step); v.done = viewDone(s.candId); }
    if (s.step === 'mismatch') v.mismatch = viewMismatch(s.cond, s.declined);
    return v;
  }
  // 정적 보드(다른 폰·다른 보드)가 쓰는 기본 화면 데이터. 기존 정적 화면과 같은 장면을 같은 규칙으로 계산한다.
  function defaultViews() {
    var c4 = { rounds: ['R4'], roundImp: '필수', zones: ['A', 'B'], zoneImp: '선호', rowMax: 10, rowImp: '선호', castImp: null };
    var c1 = { rounds: ['R1'], roundImp: '필수', zones: ['A', 'B'], zoneImp: '선호', rowMax: 10, rowImp: '선호', castImp: null };
    return {
      request: viewRequest(DEFAULT_COND, false), waiting: viewWaiting(DEFAULT_COND),
      match: viewMatch(c4, 'C1'), compare: viewCompare('C1', true, 0, 'found'), done: viewDone('C1'),
      mismatch: viewMismatch(c1, []), failed: viewFailed(), sent: viewSent(), cancelled: viewCancelled('proposed'), none: viewNone(), declined: viewDeclined(), isDemo: false,
    };
  }

  return { ROUNDS: ROUNDS, POOL: POOL, MY: MY, DEFAULT_COND: DEFAULT_COND, evaluate: evaluate, search: search, validate: validate,
    initialState: initialState, reduce: reduce, views: views, defaultViews: defaultViews,
    // STEP 3C 연석 만들기가 다시 쓰는 공용 부품 (판정 규칙·진행 흐름·표시 형식)
    SHOW: SHOW, STY: STY, judge: judge, round: round, ticketLine: ticketLine, dateLine: dateLine, count: count, clone: clone,
    flags: flags, resultRow: resultRow, badgeItem: badgeItem, flowNext: flowNext, FLOW: FLOW, CANCELABLE: CANCELABLE, TERMINAL: TERMINAL,
    timeline: timeline, STATUS: STATUS, ctlBtn: ctlBtn, CTL_STY: CTL_STY, stepper: stepper, GEN_STEPS: GEN_STEPS };
})();
if (typeof module !== 'undefined') module.exports = DEMO;
