/* Seat Swap 연석 만들기 데모 — 상태·판정 엔진 (STEP 3C → STEP 4A, 실험 기능 · 수요 미검증)
 *
 * 이 파일이 원본이다. tools/authoring/apply_ux_4a.py 가 P12(연석 만들기) 페이지 로직에 demo3b_store.js 와 함께 넣고,
 * 같은 코드로 컴포넌트의 기본 화면 데이터를 계산하며, tools/test_pair_engine.cjs 가 단위 테스트한다.
 *
 * 두 사람이 같은 상태를 본다: 신청자 A(1번 폰, 7열 12번·11열 4번 보유)와 수신자 B(3번 폰, 11열 5번 관객).
 * - B 의 '교환 제안 받기'(사전 수신 의향)는 B 가 자기 폰에서 직접 켜고 끈다. 기본값은 받지 않음.
 * - A 가 보낸 '교환 제안'은 B 의 폰에 도착하고, B 가 '제안 수락' 또는 거절을 고른다.
 * - 예매처의 최종 확인 결과와 B 티켓의 상황(동행 좌석 등)은 폰 밖 '시연 제어판'에서 정한다 (실제 서비스 기능 아님).
 * - A 의 화면에는 다른 관객의 수신 의향·자격·조건·동행 여부를 좌석별로 보여주지 않는다 (개인정보 보호).
 *   좌석 배치(통로·배치도 정보 유무)는 개인정보가 아니므로 좌석 단위로 보여준다.
 *
 * STEP 3B 엔진(DEMO)에서 다시 쓰는 것: 조건 판정(evaluate), 진행 흐름(flowNext·CANCELABLE·TERMINAL), 진행 단계(timeline), 표시 형식.
 * 모든 좌석·배치도·정책 판정은 시연용 모의 데이터다. 외부 라이브러리 없음, ES5 문법만 쓴다.
 */
var PAIR = (function (DEMO) {
  /* ------------------------------------------------------------------ 모의 데이터 */
  var POLICY_OK = '시연 판정: 교환 가능';
  var PRICE = '154,000원 (가상)';
  // 신청자(A)의 같은 회차 티켓 2장. 한 장은 유지하고(keep) 다른 한 장을 교환에 제공한다(offer).
  var MINE = [
    { key: '7-12', label: '티켓 1', round: 'R3', grade: 'R석', zone: 'B', row: 7, seat: 12, price: PRICE, casting: null, policy: POLICY_OK },
    { key: '11-4', label: '티켓 2', round: 'R3', grade: 'R석', zone: 'B', row: 11, seat: 4, price: PRICE, casting: null, policy: POLICY_OK },
  ];
  // 배치도 (모의). 좌석 번호가 이어져도 블록이 다르면(통로) 붙어 있지 않다. 확인 범위 밖 좌석은 '인접 여부 확인 필요'.
  var LAYOUT = {
    round: 'R3', zone: 'B', firstRow: 5, lastRow: 12, seats: 14,
    blocks: [[1, 12], [13, 14]],                 // 12번과 13번 사이에 세로 통로
    verified: { 11: [[1, 14]], 7: [[12, 14]] },  // 배치도 데이터로 확인한 범위 (7열 1~11번은 데이터 없음)
  };
  var WANTS_R3 = { rounds: ['R3'], roundImp: '필수', zones: ['B'], zoneImp: '선호', rowMax: 20, rowImp: '무관', castImp: null };
  var WANTS_FRONT = { rounds: ['R3'], roundImp: '필수', zones: ['B'], zoneImp: '선호', rowMax: 6, rowImp: '필수', castImp: null };
  // 다른 좌석 소유자 (배경 데이터, 조작 불가). consent = 교환 제안 받기
  var HOLDERS = {
    '11-3': { consent: false },
    '7-11': { consent: true, policy: POLICY_OK, wants: WANTS_R3, companion: null },
    '7-13': { consent: true, policy: POLICY_OK, wants: WANTS_R3, companion: null },
  };
  // 수신자 B = 11열 5번 관객. 교환 제안 받기는 B 의 폰에서, 티켓 상황은 시연 제어판에서 정한다.
  var FLEX = '11-5';
  var PROFILES = {
    basic: { label: '기본', policy: POLICY_OK, wants: WANTS_R3, companion: null },
    companion: { label: '동행 좌석 있음', policy: POLICY_OK, wants: WANTS_R3, companion: { key: '11-6', policy: '시연 판정: 좌석별 교환 가능' } },
    mismatch: { label: '조건 불일치', policy: POLICY_OK, wants: WANTS_FRONT, companion: null },
    unknown: { label: '자격 미확인', policy: null, wants: WANTS_R3, companion: null },
  };
  var PROFILE_ORDER = ['basic', 'companion', 'mismatch', 'unknown'];

  /* ------------------------------------------------------------------ 좌석 도우미 */
  function parse(key) { var p = key.split('-'); return { row: +p[0], seat: +p[1] }; }
  function seatName(key) { var p = parse(key); return p.row + '열 ' + p.seat + '번'; }
  function mine(key) { for (var i = 0; i < MINE.length; i++) if (MINE[i].key === key) return MINE[i]; return null; }
  function other(keep) { return MINE[0].key === keep ? MINE[1] : MINE[0]; }
  function sideOf(keep, key) { return parse(key).seat < mine(keep).seat ? '왼쪽' : '오른쪽'; }
  function ticketOf(key, policy) {
    var p = parse(key);
    return { round: LAYOUT.round, grade: 'R석', zone: LAYOUT.zone, row: p.row, seat: p.seat, price: PRICE, casting: null, policy: policy };
  }
  function holderOf(s, key) {
    var h;
    if (key === FLEX) { var pr = PROFILES[s.profile] || PROFILES.basic; h = { consent: !!s.consent, policy: pr.policy, wants: pr.wants, companion: pr.companion }; }
    else h = HOLDERS[key];
    if (!h) return null;
    var pol = h.policy === undefined ? null : h.policy;
    return { key: key, consent: !!h.consent, policy: pol, wants: h.wants || null, companion: h.companion || null, ticket: ticketOf(key, pol) };
  }
  function neighbors(keep) {
    var a = mine(keep), out = [];
    [a.seat - 1, a.seat + 1].forEach(function (n) { if (n >= 1 && n <= LAYOUT.seats) out.push(a.row + '-' + n); });
    return out;
  }
  function inRanges(list, n) { for (var i = 0; i < (list || []).length; i++) if (n >= list[i][0] && n <= list[i][1]) return true; return false; }
  function blockOf(n) { for (var i = 0; i < LAYOUT.blocks.length; i++) if (inRanges([LAYOUT.blocks[i]], n)) return i; return -1; }

  /* ------------------------------------------------------------------ 판정 */
  // 실제 인접 여부: 같은 회차 → 같은 구역·열 → 번호 연속 → 배치도 확인 범위 → 같은 블록(통로·단절 없음). res = ok | no | unknown
  function adjacency(a, b) {
    var checks = [];
    var add = function (dim, res, detail) { checks.push({ dim: dim, res: res, detail: detail }); };
    if (a.round !== b.round) { add('같은 회차', 'no', '회차가 달라요'); return { res: 'no', checks: checks, reason: '회차가 달라요' }; }
    add('같은 회차', 'ok', DEMO.round(a.round).n + '회차');
    if (a.zone !== b.zone || a.row !== b.row) { add('같은 구역·열', 'no', '구역 또는 열이 달라요'); return { res: 'no', checks: checks, reason: '같은 열이 아니에요' }; }
    add('같은 구역·열', 'ok', a.zone + '구역 ' + a.row + '열');
    if (Math.abs(a.seat - b.seat) !== 1) { add('번호 연속', 'no', '번호가 이어지지 않아요'); return { res: 'no', checks: checks, reason: '번호가 이어지지 않아요' }; }
    add('번호 연속', 'ok', a.seat + '번 · ' + b.seat + '번');
    var ver = LAYOUT.verified[a.row];
    if (!inRanges(ver, a.seat) || !inRanges(ver, b.seat)) {
      add('배치도 (통로·단절)', 'unknown', '이 구간의 배치도 데이터가 없어 통로 여부를 알 수 없어요');
      return { res: 'unknown', checks: checks, reason: '배치도 데이터 없음' };
    }
    if (blockOf(a.seat) !== blockOf(b.seat)) {
      add('배치도 (통로·단절)', 'no', '번호는 이어지지만 사이에 통로가 있어요');
      return { res: 'no', checks: checks, reason: '통로로 분리' };
    }
    add('배치도 (통로·단절)', 'ok', '같은 블록 · 사이에 통로 없음');
    return { res: 'ok', checks: checks, reason: '' };
  }
  // 옆자리 하나를 판정한다 (엔진 내부용: 결과 중 개인 사정은 A 의 화면에 그대로 내보내지 않는다).
  // status: hidden(교환 제안 받기 꺼짐) | ok(연결 가능) | no(인접 아님·조건 불일치) | hold(확인 필요) | declined(이미 거절)
  function judgeCandidate(s, key) {
    var h = holderOf(s, key);
    var a = mine(s.keep), give = other(s.keep);
    if (!h || !h.consent) return { key: key, status: 'hidden', consent: false, proposable: false, adj: adjacency(a, ticketOf(key, null)) };
    var adj = adjacency(a, h.ticket);
    var theirs = DEMO.evaluate(h.wants, give, 'theirs');      // 상대가 등록한 조건 ↔ 내가 제공할 좌석 (STEP 3B 판정 그대로)
    var wantFail = theirs.filter(function (r) { return r.res === 'fail' || (r.res === 'unknown' && r.imp === '필수'); });
    var elig = { mine: give.policy, theirs: h.policy };
    var eligOk = elig.mine !== null && elig.theirs !== null;
    var comp = h.companion;
    var compRes = !comp ? 'skip' : (comp.policy === null ? 'unknown' : 'warn');
    var status = 'ok', reason = '';
    if ((s.declined || []).indexOf(key) >= 0) { status = 'declined'; reason = '거절된 제안'; }
    else if (adj.res === 'no') { status = 'no'; reason = '인접 아님 · ' + adj.reason; }
    else if (wantFail.length) { status = 'no'; reason = '상대의 필수 조건과 맞지 않아요'; }
    else if (adj.res === 'unknown') { status = 'hold'; reason = '인접 여부 확인 필요'; }
    else if (!eligOk) { status = 'hold'; reason = '교환 자격 확인 필요'; }
    else if (compRes === 'unknown') { status = 'hold'; reason = '동행 좌석의 좌석별 교환 정책 확인 필요'; }
    return { key: key, status: status, reason: reason, consent: true, adj: adj, theirs: theirs, wantFail: wantFail, elig: elig, eligOk: eligOk,
      companion: comp, compRes: compRes, holder: h, proposable: status === 'ok' };
  }
  function candidates(s) { return neighbors(s.keep).map(function (k) { return judgeCandidate(s, k); }); }
  function proposable(s, key) {
    if (!key || neighbors(s.keep).indexOf(key) < 0) return false;
    return judgeCandidate(s, key).proposable;
  }

  /* ------------------------------------------------------------------ 상태 */
  function initialState() {
    return { picked: [MINE[0].key, MINE[1].key], mode: 'pair', formKey: 0, keep: '11-4', dirKey: 0, profile: 'basic',
      consent: false, intentDraft: false, intentMsg: '', cand: null, ack: false, ackKey: 0, step: 'select', declined: [], hint: '', notice: '',
      bSeen: false, cancelledFrom: null };
  }
  function reset(st) {
    var s = initialState();
    if (st) { s.formKey = st.formKey + 1; s.dirKey = st.dirKey + 1; s.ackKey = st.ackKey + 1; }
    return s;
  }
  // 신청자 화면만 처음으로 (수신자 B 의 설정은 B 의 것이므로 유지)
  function resetA(st) {
    var s = reset(st);
    s.consent = st.consent; s.intentDraft = st.intentDraft; s.profile = st.profile;
    return s;
  }
  var ACTIVE = ['proposed', 'accepted', 'final'];
  var FLOW_SCREEN = { accepted: 'PairAccepted', declined: 'PairDeclined', final: 'StatusFinal', done: 'PairDone', failed: 'ExFinalFailed' };
  var HINT_GENERAL = "좌석·회차 교환은 '06 UI 좌석·회차 교환' 보드에서 체험해요. 이 폰은 연석 만들기 전용이에요.";
  var HINT_PICK = '연석 만들기는 같은 회차 티켓 2장이 필요해요. 2장을 모두 선택해 주세요.';
  var NOTICE_LOST = '선택했던 후보와 지금은 연결할 수 없어요. 후보를 다시 확인해 주세요.';

  // action: { type, val, checked, role: 'A' | 'B' | 'ctl', screenA, screenB } → { state, nav(신청자 폰), navB(수신자 폰) }
  function reduce(st, action) {
    var s = DEMO.clone(st);
    var t = action.type;
    var out = function (nav, navB) { return { state: s, nav: nav || null, navB: navB || null }; };
    var keepSame = function (nav) { return { state: st, nav: nav || null, navB: null }; };
    var clearPick = function () { s.cand = null; s.ack = false; s.ackKey += 1; };
    var selecting = s.step === 'select';
    // B 의 설정·티켓 상황이 바뀌어 선택한 후보와 연결할 수 없게 되면 A 의 선택을 풀고, 확인 화면에 있었다면 후보 화면으로 돌려보낸다
    var recheck = function () {
      if (s.cand && selecting && !proposable(s, s.cand)) {
        clearPick(); s.notice = NOTICE_LOST;
        if (action.screenA === 'PairWarn') return { reset: ['PairMode', 'PairSeat', 'PairAdjacency'] };
      }
      return null;
    };
    switch (t) {
      /* ---- 신청자 A ---- */
      case 'pick':
        if (!selecting || !mine(action.val)) return keepSame();
        var i = s.picked.indexOf(action.val);
        if (action.checked && i < 0) s.picked.push(action.val);
        if (!action.checked && i >= 0) s.picked.splice(i, 1);
        s.hint = ''; return out();
      case 'mode':
        if (!selecting || (action.val !== 'pair' && action.val !== 'general')) return keepSame();
        s.mode = action.val; s.hint = ''; return out();
      case 'next':
        if (!selecting) return keepSame({ stay: true });
        if (s.mode !== 'pair') { s.hint = HINT_GENERAL; return out({ stay: true }); }
        if (s.picked.length < 2) { s.hint = HINT_PICK; return out({ stay: true }); }
        s.hint = ''; return out({ push: 'PairSeat' });
      case 'dir':            // 어느 좌석을 유지할지 (= 어느 쪽으로 모을지)
        if (!selecting || !mine(action.val)) return keepSame();
        if (s.keep !== action.val) { s.keep = action.val; clearPick(); s.notice = ''; }
        return out();
      case 'flipDir':        // 후보가 없을 때: 반대 방향으로 찾아보기 (후보 화면에 머문다)
        if (!selecting) return keepSame();
        s.keep = other(s.keep).key; s.dirKey += 1; clearPick(); s.notice = '';
        return out();
      case 'toCandidates':
        if (!selecting) return keepSame({ stay: true });
        return out({ push: 'PairAdjacency' });
      case 'choose':
        if (!selecting || !proposable(s, action.val)) return keepSame();
        if (s.cand !== action.val) { s.cand = action.val; s.ack = false; s.ackKey += 1; }
        s.notice = ''; return out();
      case 'toWarn':
        if (!selecting || !proposable(s, s.cand)) return keepSame({ stay: true });
        return out({ push: 'PairWarn' });
      case 'ack':
        if (!selecting || !s.cand) return keepSame();
        s.ack = !!action.checked; return out();
      case 'send':           // 교환 제안 보내기 → B 의 폰에 제안이 도착한다
        if (!selecting || !s.ack || !proposable(s, s.cand)) return keepSame({ stay: true });
        // 수신자 폰에는 '제안 도착' 알림 카드가 뜬다 (수신자가 직접 열어야 '검토 중')
        s.step = 'proposed'; s.bSeen = false; return out({ push: 'StatusSent' });
      case 'cancel':
        if (DEMO.CANCELABLE.indexOf(s.step) < 0) return keepSame({ stay: true });
        s.cancelledFrom = s.step; s.step = 'cancelled'; return out({ push: 'ExCancelled' });
      case 'otherCandidate': // 거절 뒤: 같은 방향의 다른 후보 찾기 (거절한 후보는 다시 고를 수 없다)
        if (s.step !== 'declined') return keepSame({ stay: true });
        s.step = 'select'; clearPick(); return out({ reset: ['PairMode', 'PairSeat', 'PairAdjacency'] }, { reset: ['PairIntent'] });
      case 'toSeat':         // 거절 뒤: 이전 단계(좌석 방향)로. 고른 방향은 유지
        if (DEMO.TERMINAL.indexOf(s.step) < 0) return keepSame({ stay: true });
        s.step = 'select'; clearPick(); return out({ reset: ['PairMode', 'PairSeat'] }, { reset: ['PairIntent'] });
      case 'restart':        // 취소·실패 뒤 다시: 고른 방향 유지, 거절 기록은 지운다
        if (DEMO.TERMINAL.indexOf(s.step) < 0) return keepSame({ stay: true });
        s.step = 'select'; s.declined = []; clearPick(); return out({ reset: ['PairMode', 'PairSeat'] }, { reset: ['PairIntent'] });
      case 'home':
        s = resetA(s); return out({ reset: ['PairMode'] }, { reset: ['PairIntent'] });
      /* ---- 수신자 B ---- */
      case 'intent':         // 교환 제안 받기 / 받지 않기 (저장 전 선택)
        if (action.val !== 'on' && action.val !== 'off') return keepSame();
        s.intentDraft = action.val === 'on'; s.intentMsg = ''; return out();
      case 'intentSave':
        if (!s.intentDraft && s.consent && ACTIVE.indexOf(s.step) >= 0) {
          s.intentMsg = '진행 중인 교환 제안이 있어 지금은 끌 수 없어요. 제안에 응답한 뒤 바꿀 수 있어요.';
          return out();
        }
        s.consent = s.intentDraft;
        s.intentMsg = s.consent ? '저장했어요. 이제 옆자리 관객이 교환 제안을 보낼 수 있어요.' : '저장했어요. 이제 교환 제안을 받지 않아요.';
        return out(recheck());
      case 'toReceive':
        if (s.step === 'proposed') s.bSeen = true;
        return out(null, { push: 'PairReceive' });
      case 'recvAccept':     // 제안 수락 (B 의 개별 동의). 수락해도 최종 확인이 남는다
      case 'recvDecline':
        var nx = DEMO.flowNext(s.step, t === 'recvAccept' ? 'simAccept' : 'simDecline');
        if (!nx) return keepSame();
        s.step = nx; if (nx === 'declined') s.declined.push(s.cand);
        return out({ push: FLOW_SCREEN[nx] });
      /* ---- 시연 제어판 ---- */
      case 'profile':        // 옆자리 관객(11열 5번) 티켓 상황
        if (!selecting || !PROFILES[action.val]) return keepSame();
        s.profile = action.val;
        return out(recheck());
      case 'simAccept': case 'simDecline': case 'toFinal': case 'simOk': case 'simFail':
        var nx2 = DEMO.flowNext(s.step, t);
        if (!nx2) return keepSame({ stay: true });
        s.step = nx2; if (nx2 === 'declined') s.declined.push(s.cand);
        return out({ push: FLOW_SCREEN[nx2] });
      /* ---- 공통 ---- */
      case 'back':
        if (action.role === 'B') return out(null, { pop: true });
        if (ACTIVE.indexOf(s.step) >= 0) return keepSame({ stay: true });      // 진행 중에는 '취소'로만 빠져나간다
        if (DEMO.TERMINAL.indexOf(s.step) >= 0) { s = resetA(s); return out({ reset: ['PairMode'] }, { reset: ['PairIntent'] }); }
        return out({ pop: true });
      default:
        return keepSame();
    }
  }

  /* ------------------------------------------------------------------ 화면 데이터 */
  var CHIP_ON = 'height: 32px; padding: 0 12px; border-radius: 16px; font-family: inherit; font-size: 13px; font-weight: 700; border: 2px solid #191B22; background: #191B22; color: #FFFFFF';
  var CHIP_OFF = 'height: 32px; padding: 0 12px; border-radius: 16px; font-family: inherit; font-size: 13px; font-weight: 500; border: 1.5px solid #8B909C; background: #FFFFFF; color: #191B22';
  var CHIP_DIS = 'height: 32px; padding: 0 12px; border-radius: 16px; font-family: inherit; font-size: 13px; font-weight: 500; border: 1.5px dashed #B4B8C2; background: #F5F6F8; color: #6B7080';
  var OPT_ON = 'display: flex; align-items: flex-start; gap: 12px; border: 1.5px solid #5B3DF5; background: #F7F5FF; border-radius: 14px; padding: 14px';
  var OPT_OFF = 'display: flex; align-items: flex-start; gap: 12px; border: 1px solid #DADDE3; border-radius: 14px; padding: 14px';
  var TICKET_ON = 'display: flex; align-items: center; gap: 12px; border: 1.5px solid #5B3DF5; background: #F7F5FF; border-radius: 14px; padding: 12px 16px';
  var TICKET_OFF = 'display: flex; align-items: center; gap: 12px; border: 1px solid #DADDE3; background: #FFFFFF; border-radius: 14px; padding: 12px 16px';
  var MODE_ON = 'display: flex; align-items: flex-start; gap: 12px; border: 1.5px solid #5B3DF5; background: #F7F5FF; border-radius: 16px; padding: 14px 16px';
  var MODE_OFF = 'display: flex; align-items: flex-start; gap: 12px; border: 1px solid #DADDE3; border-radius: 16px; padding: 14px 16px';
  var INT_ON = 'display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border-radius: 14px; border: 1.5px solid #5B3DF5; background: #F7F5FF';
  var INT_OFF = 'display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border-radius: 14px; border: 1px solid #E6E8EC; background: #FFFFFF';
  var PICK_ON = 'width: 100%; height: 40px; border-radius: 12px; font-family: inherit; font-size: 14px; font-weight: 700; border: 0; background: #5B3DF5; color: #FFFFFF';
  var PICK_OFF = 'width: 100%; height: 40px; border-radius: 12px; font-family: inherit; font-size: 14px; font-weight: 700; border: 1.5px solid #5B3DF5; background: #FFFFFF; color: #3A26C4';
  var PICK_NO = 'width: 100%; height: 40px; border-radius: 12px; font-family: inherit; font-size: 14px; font-weight: 700; border: 1.5px dashed #9AA0AC; background: #F5F6F8; color: #6B7080';

  function item(kind, text, label, detail) {
    var o = { label: label || '', text: text, detail: detail || '', hasDetail: !!detail };
    var f = DEMO.flags(kind); for (var k in f) o[k] = f[k];
    return o;
  }
  function withFlags(o, kind) { var f = DEMO.flags(kind); for (var k in f) o[k] = f[k]; return o; }
  function pairText(a, b) {   // 같은 열 두 좌석 → '11열 4번, 5번'
    var x = parse(a), y = parse(b);
    return x.row + '열 ' + Math.min(x.seat, y.seat) + '번, ' + Math.max(x.seat, y.seat) + '번';
  }
  function bothMine() { return seatName(MINE[0].key) + ' · ' + seatName(MINE[1].key); }
  function dateRound() { return DEMO.dateLine(MINE[0]); }

  // STEP 4B 공용 단계 표시 (일반 교환과 같은 컴포넌트). 연석은 인접 확인·상대 수락 단계를 포함한다
  var PAIR_STEPS = ['교환 방식', '유지할 좌석', '인접 확인', '비교·제안', '상대 수락', '최종 확인'];
  var B_STEPS = ['제안 받기', '제안 검토', '응답', '최종 확인', '교환 완료'];
  var PAIR_CANCEL_AT = { proposed: 4, accepted: 5, declined: 4 };
  function pstep(idx, end, text) { return DEMO.stepper(PAIR_STEPS, idx, end, text, true); }
  function viewMode(s, demo) {
    return { stepper: pstep(0),
      tickets: MINE.map(function (m) {
        var on = s.picked.indexOf(m.key) >= 0;
        return { val: m.key, title: m.grade + ' · ' + m.zone + '구역 ' + seatName(m.key), sub: m.label + ' · ' + (m.policy ? '교환 가능 (시연 판정)' : '교환 자격 확인 필요'),
          checked: on, style: on ? TICKET_ON : TICKET_OFF };
      }),
      pairChecked: s.mode === 'pair', generalChecked: s.mode !== 'pair',
      pairStyle: s.mode === 'pair' ? MODE_ON : MODE_OFF, generalStyle: s.mode === 'pair' ? MODE_OFF : MODE_ON,
      hint: demo ? s.hint : '', hasHint: !!(demo && s.hint),
    };
  }
  function viewSeat(s) {
    var keep = mine(s.keep), give = other(s.keep), nb = neighbors(s.keep);
    var rows = [];
    for (var r = LAYOUT.firstRow; r <= LAYOUT.lastRow; r++) {
      var seats = [];
      for (var n = 1; n <= LAYOUT.seats; n++) {
        var k = r + '-' + n;
        var kind = k === keep.key ? 'keep' : k === give.key ? 'offer' : nb.indexOf(k) >= 0 ? 'near' : 'other';
        seats.push({ mine: kind === 'keep', offer: kind === 'offer', cand: kind === 'near', other: kind === 'other', aisle: n === LAYOUT.blocks[0][1] });
      }
      rows.push({ label: r + '열', seats: seats });
    }
    return { stepper: pstep(1),
      rows: rows,
      options: MINE.slice().reverse().map(function (m) {   // 11열로 모으기(11열 4번 유지)가 먼저
        var g = other(m.key), on = s.keep === m.key;
        return { val: m.key, checked: on, style: on ? OPT_ON : OPT_OFF,
          title: m.row + '열로 모으기 → ' + m.row + '열 ' + (m.seat - 1) + '·' + m.seat + '번 또는 ' + m.seat + '·' + (m.seat + 1) + '번',
          desc: '유지할 좌석 ' + seatName(m.key) + ' · 교환에 제공할 좌석 ' + seatName(g.key) + '. 옆자리 관객이 ' + seatName(g.key) + '으로 옮겨 가요',
          tag: on };
      }),
      keepName: seatName(keep.key), offerName: seatName(give.key),
    };
  }
  // 좌석 배치 사실 (개인정보 아님): 이 좌석이 배치도상 옆자리인지
  function seatFact(s, key) {
    var a = adjacency(mine(s.keep), ticketOf(key, null));
    var t = { ok: ['ok', '배치도상 옆자리'], no: ['no', '옆자리 아님'], unknown: ['need', '인접 여부 확인 필요'] }[a.res];
    var last = a.checks[a.checks.length - 1];
    var detail = a.res === 'ok' ? '같은 블록 · 사이에 통로 없음' : a.res === 'no' && last.dim.indexOf('배치도') === 0 ? '번호는 이어지지만 사이에 통로가 있어요' : last.detail;
    return item(t[0], t[1], seatName(key) + ' (' + sideOf(s.keep, key) + ')', detail);
  }
  function candCard(s, c) {
    var give = other(s.keep), selected = s.cand === c.key;
    var title = seatName(c.key) + ' · ' + sideOf(s.keep, c.key);
    if (c.status === 'declined') {
      return withFlags({ key: c.key, title: title, text: '거절된 제안', rows: [], checks: [], hasResult: false, note: '내가 보낸 교환 제안을 거절했어요. 같은 관객에게 다시 보내지 않아요.', hasNote: true,
        canPick: false, cantPick: true, pressed: 'false', pickText: '다시 보낼 수 없음', pickStyle: PICK_NO,
        border: 'border: 1px solid #E6E8EC; background: #FFFFFF' }, 'mute');
    }
    return withFlags({ key: c.key, title: title, text: '연결 가능', note: '', hasNote: false,
      // 위계: 교환 후 결과 → 확인 항목(한 줄 칩) → 선택
      hasResult: true, result: '교환하면 ' + pairText(s.keep, c.key) + ' 나란히', resultSub: '내 ' + seatName(give.key) + ' ↔ 상대 ' + seatName(c.key),
      checks: ['배치도상 옆자리 ✓', '양쪽 교환 자격 ✓ (시연)', '상대 조건 충족 ✓'], rows: [],
      canPick: true, cantPick: false, pressed: selected ? 'true' : 'false',
      pickText: selected ? '선택됨 ✓' : '이 후보 선택', pickStyle: selected ? PICK_ON : PICK_OFF,
      border: selected ? 'border: 2px solid #5B3DF5; background: #F7F5FF' : 'border: 1px solid #DADDE3; background: #FFFFFF' }, 'ok');
  }
  function viewAdj(s, demo) {
    var cs = candidates(s);
    var shown = cs.filter(function (c) { return c.status === 'ok' || c.status === 'declined'; });   // 연결 가능한 후보와 내가 보낸 제안의 결과만
    var anyOk = cs.some(function (c) { return c.proposable; });
    var ok = !!(s.cand && proposable(s, s.cand));
    var flipTo = other(s.keep);
    return { stepper: pstep(2),
      keepName: seatName(s.keep), offerName: seatName(flipTo.key),
      // 배치도 때문에 제외한 좌석만 좌석 단위로 알린다. 배치도상 옆자리인데 후보가 없는 좌석은 언급하지 않는다 (개인 사정 추론 방지)
      facts: neighbors(s.keep).filter(function (k) { return adjacency(mine(s.keep), ticketOf(k, null)).res !== 'ok'; }).map(function (k) { return seatFact(s, k); }),
      cards: shown.map(function (c) { return candCard(s, c); }),
      hasCards: shown.length > 0,
      hasFacts: neighbors(s.keep).some(function (k) { return adjacency(mine(s.keep), ticketOf(k, null)).res !== 'ok'; }),
      noCandidate: !anyOk,
      emptyTitle: '현재 연결 가능한 후보가 없습니다',
      emptyText: "'교환 제안 받기'를 켠 관객 중 조건이 맞는 좌석만 후보로 보여줘요. 좌석별로 빠진 이유는 개인정보라 알려드리지 않아요.",
      canFlip: !!demo && !anyOk && s.step === 'select', flipText: '반대 방향으로 찾아보기 (' + seatName(flipTo.key) + ' 유지)',
      notice: demo ? s.notice : '', hasNotice: !!(demo && s.notice),
      canNext: ok, cantNext: !ok,
      nextHint: ok ? '' : anyOk ? '제안할 후보를 선택해 주세요.' : '연결 가능한 후보가 없어 다음으로 갈 수 없어요.',
    };
  }
  var TAG_STY = { mute: 'color: #4A4F5C; background: #F0F1F4', plan: 'color: #3A26C4; background: #E9E5FF', ok: 'color: #1F7A4D; background: #E6F6EE',
    need: 'color: #A3440B; background: #FFF1E6', no: 'color: #B03A3A; background: #FDF0F0' };
  function cmpRow(label, now, after, kind, text) {
    return withFlags({ label: label, now: now, after: after, change: now === after ? now : now + ' → ' + after, text: text,
      tagStyle: 'font-size: 11px; font-weight: 700; padding: 2px 6px; border-radius: 4px; white-space: nowrap; ' + TAG_STY[kind] }, kind);
  }
  function viewWarn(s) {
    var c = s.cand ? judgeCandidate(s, s.cand) : null;
    var give = other(s.keep);
    if (!c || c.status === 'hidden') {
      return { stepper: pstep(3), compare: [], diffRows: [], sameRows: [], sameTitle: '', hero: { show: '', date: '', from: '', to: '', result: '' },
        twoWay: [], candMove: '', now: '', after: '', ack: false, canSend: false, cantSend: true, sendText: '교환 제안 보내기',
        sendHint: '선택한 후보가 없어요. 후보 화면에서 다시 골라 주세요.', twoWayNote: '' };
    }
    var canSend = s.step === 'select' && s.ack && c.proposable;
    var rowsW = [
        cmpRow('유지할 좌석', seatName(s.keep), seatName(s.keep), 'mute', '그대로'),
        cmpRow('제공할 좌석', seatName(give.key), seatName(s.cand) + ' 받음', 'plan', '바뀜'),
        cmpRow('좌석 배치', '떨어짐', pairText(s.keep, s.cand), 'ok', '나란히 · 완료 시에만'),
        cmpRow('회차', DEMO.round(MINE[0].round).n + '회차', DEMO.round(MINE[0].round).n + '회차', 'mute', '같음'),
        cmpRow('등급·가격', 'R석 · 154,000원', 'R석 · 154,000원', 'mute', '같음'),
        cmpRow('상대 좌석', seatName(s.cand), seatName(give.key), 'plan', '상대 이동'),
      ];
    var sameW = ['제공할 좌석', '좌석 배치', '회차', '등급·가격'];   // 위쪽 요약(교환 전후 좌석)에 이미 있는 항목과 같은 항목은 접는다
    return {
      stepper: pstep(3), compare: rowsW,
      // 위계: ① 공연·회차 ② 교환 전후 좌석(크게) ③ 바뀌는 항목 ④ 같은 항목은 접힘
      hero: { show: DEMO.SHOW, date: dateRound() + ' · 같은 회차', from: seatName(give.key), to: seatName(s.cand), result: '교환 후 ' + pairText(s.keep, s.cand) + ' 나란히 (완료 시에만)' },
      diffRows: rowsW.filter(function (r) { return sameW.indexOf(r.label) < 0; }), sameRows: rowsW.filter(function (r) { return sameW.indexOf(r.label) >= 0; }),
      sameTitle: '전체 비교 보기 (좌석 배치·회차·등급·가격)',
      candMove: '상대(' + seatName(s.cand) + ')는 ' + seatName(give.key) + '으로 옮겨요. 좋고 나쁨은 사람마다 달라요.',
      twoWay: [
        item('ok', '충족', '① 내 조건: ' + seatName(s.keep) + ' 바로 옆 (배치도 확인)'),
        item(c.wantFail.length ? 'no' : 'ok', c.wantFail.length ? '불일치' : '충족', '② 상대가 등록한 조건 ↔ 내가 제공할 ' + seatName(give.key)),
      ],
      twoWayNote: "양쪽 조건이 맞아도 아직 '교환 완료'가 아니에요. 상대방의 제안 수락과 최종 확인이 남아 있어요.",
      ack: !!s.ack, canSend: canSend, cantSend: !canSend, sendText: seatName(s.cand) + ' 관객에게 교환 제안 보내기',
      sendHint: s.step !== 'select' ? '이미 제안을 보냈거나 진행할 수 없는 상태예요.' : (!c.proposable ? '이 후보에게는 지금 제안할 수 없어요.' : (s.ack ? '' : '위 내용을 확인했다고 선택하면 보낼 수 있어요.')),
    };
  }
  function hasProposal(s) { return s.cand === FLEX && s.step !== 'select'; }
  // 수신자 B 의 제안 검토 화면 (STEP 4B: 상태별 제목·보조 문구·색·CTA. 색만으로 구분하지 않고 배지·제목 텍스트를 함께 준다)
  // [배지 종류, 배지, 제목, 보조 문구, CTA 종류(respond|wait|back), 대기 문구]
  var RECV = {
    arrived: ['plan', '제안 도착', '새 교환 제안이 도착했어요', '옆자리 관객이 보낸 제안이에요. 내용을 확인하고 결정하세요.', 'respond'],
    reviewing: ['plan', '검토 중', '다른 좌석으로 옮기자는 교환 제안이에요', '', 'respond'],
    accepted: ['ok', '수락함', '제안을 수락했어요', "아직 '교환 완료'가 아니에요. 예매처의 최종 확인을 기다리는 중이에요.", 'wait', '응답 완료 · 예매처 최종 확인을 기다리는 중'],
    final: ['wait', '최종 확인 중', '예매처가 최종 확인 중이에요', "티켓과 조건을 마지막으로 확인하고 있어요. 아직 '교환 완료'가 아니에요.", 'wait', '최종 확인 중 · 결과가 나오면 여기서 알려드려요'],
    done: ['done', '교환 완료 (시연)', '교환이 완료됐어요', '새 좌석은 7열 12번이에요. 시연용 모의 결과예요.', 'back'],
    failed: ['fail', '교환 실패', '최종 확인에 실패했어요', '교환은 진행되지 않았어요. 원래 좌석 11열 5번이 유지되는 것을 목표로 해요 (목표 UX).', 'back'],
    declined: ['mute', '거절함', '제안을 거절했어요', '내 좌석은 그대로예요. 거절 사유는 신청자에게 공개되지 않아요.', 'back'],
    cancelled: ['cancel', '신청자 취소', '신청자가 제안을 취소했어요', '내 좌석은 그대로예요.', 'back'],
  };
  var BAND = { plan: 'background: #F0EDFF; border: 1.5px solid #C9BFFF', ok: 'background: #E6F6EE; border: 1.5px solid #9ED5B8',
    wait: 'background: #FFF1E6; border: 1.5px solid #F2C3A0', done: 'background: #E6F6EE; border: 2px solid #1F7A4D',
    fail: 'background: #FDF0F0; border: 2px solid #B03A3A', mute: 'background: #F5F6F8; border: 1.5px solid #DADDE3', cancel: 'background: #F5F6F8; border: 1.5px solid #DADDE3' };
  function recvState(s) { return !hasProposal(s) ? null : s.step === 'proposed' ? (s.bSeen ? 'reviewing' : 'arrived') : s.step; }
  function recvStepper(st) {
    var m = { arrived: [1], reviewing: [1], accepted: [3], final: [3], done: [4, 'done'], failed: [3, 'fail', '최종 확인 실패 · 원래 좌석 유지 (목표)'],
      declined: [2, 'stop', '제안 거절 · 내 좌석 그대로'], cancelled: [1, 'stop', '신청자가 제안 취소'] }[st] || [1];
    return DEMO.stepper(B_STEPS, m[0], m[1] || null, m[2] || '', false);
  }
  function viewReceive(s) {
    var pr = PROFILES[s.profile] || PROFILES.basic;
    var give = hasProposal(s) ? other(s.keep) : MINE[0];
    var key = recvState(s) || 'reviewing';
    var r = RECV[key];
    var comp = pr.companion;
    var dRow = Math.abs(parse(FLEX).row - parse(give.key).row);
    var rows = [
      cmpRow('열·좌석', seatName(FLEX), seatName(give.key), 'plan', '바뀜'),
      cmpRow('무대와 거리', parse(FLEX).row + '열', parse(give.key).row + '열', 'plan', dRow + '열 ' + (parse(give.key).row < parse(FLEX).row ? '앞으로' : '뒤로')),
      cmpRow('회차', '3회차', '3회차', 'mute', '같음'),
      cmpRow('등급·가격', 'R석 · 154,000원', 'R석 · 154,000원', 'mute', '추가 결제 없음'),
    ];
    var v = {
      hasProposal: hasProposal(s), noProposal: !hasProposal(s),
      emptyText: "도착한 교환 제안이 없어요. '교환 제안 받기'를 켜 두면 옆자리 관객의 제안이 여기에 도착해요.",
      from: '옆자리(' + seatName(s.keep) + ') 관객이 일행과 나란히 앉고 싶어 해요.',
      mine: dateRound() + ' · B구역 ' + seatName(FLEX),
      offer: dateRound() + ' · B구역 ' + seatName(give.key),
      hero: { show: DEMO.SHOW, date: dateRound() + ' · 같은 회차', from: seatName(FLEX), to: seatName(give.key),
        result: '무대와 ' + dRow + '열 ' + (parse(give.key).row < parse(FLEX).row ? '가까워져요' : '멀어져요') + ' · 같은 회차·가격' },
      compare: rows, diffRows: rows.slice(0, 2), sameRows: rows.slice(2), sameTitle: '같은 항목 2개 보기 (회차·등급·가격)',
      hasCompanion: !!comp,
      companionText: comp ? '함께 예매한 ' + seatName(comp.key) + '과 떨어져 앉게 돼요. 일행과 상의한 뒤 결정하세요. 원하지 않으면 거절해도 돼요.' : '',
      companionPolicy: comp ? (comp.policy || '좌석별 교환 정책 확인 필요') : '',
      canRespond: s.step === 'proposed' && hasProposal(s), responded: hasProposal(s) && s.step !== 'proposed',
      respondNote: "수락해도 바로 교환되지 않아요. 최종 확인을 통과해야 '교환 완료'예요.",
      state: key, title: r[2], sub: r[3] || ('옆자리(' + seatName(s.keep) + ') 관객이 일행과 나란히 앉고 싶어 해요. 같은 R석이라 추가 결제는 없어요.'),
      statusBadge: r[1], statusTitle: r[2], statusText: r[3], bandStyle: BAND[r[0]] + '; border-radius: 14px; padding: 12px 14px; display: flex; flex-direction: column; gap: 4px',
      hasWait: r[4] === 'wait' && hasProposal(s), waitText: r[5] || '', hasBack: r[4] === 'back' && hasProposal(s), backText: '설정 화면으로 돌아가기',
      stepper: recvStepper(key),
    };
    ['plan', 'ok', 'wait', 'done', 'fail', 'mute', 'cancel'].forEach(function (k) { v['b_' + k] = r[0] === k; });
    return withFlags(v, { plan: 'plan', ok: 'ok', wait: 'need', done: 'ok', fail: 'no', mute: 'mute', cancel: 'mute' }[r[0]]);
  }
  function viewIntent(s, demo) {
    var locked = ACTIVE.indexOf(s.step) >= 0 && s.consent;
    var dirty = s.intentDraft !== s.consent;
    return {
      myTicket: dateRound() + ' · R석 B구역 ' + seatName(FLEX),
      onChecked: !!s.intentDraft, offChecked: !s.intentDraft, onStyle: s.intentDraft ? INT_ON : INT_OFF, offStyle: s.intentDraft ? INT_OFF : INT_ON,
      statusText: s.consent ? '지금: 교환 제안 받는 중' : '지금: 교환 제안 받지 않음 (기본값)',
      statusOn: s.consent, statusOff: !s.consent,
      dirty: !!demo && dirty, dirtyText: "선택을 바꿨어요. '설정 저장'을 눌러야 적용돼요.",
      msg: demo ? s.intentMsg : '', hasMsg: !!(demo && s.intentMsg),
      locked: locked, lockText: '진행 중인 교환 제안이 있어요. 제안에 응답한 뒤 끌 수 있어요.',
      hasProposal: hasProposal(s), proposalText: '도착한 교환 제안 1건 보기',
      // 제안 도착 알림 카드 (수신자가 직접 열어야 '검토 중')
      card: (function (c) { return { title: c[0], text: c[1], cta: c[2] }; })(hasProposal(s) ? (s.step === 'proposed' ? (s.bSeen ? ['검토 중인 교환 제안', '아직 응답하지 않았어요.', '이어서 검토하기'] : ['새 교환 제안이 도착했어요', '옆자리(' + seatName(s.keep) + ') 관객 · 내 11열 5번을 ' + seatName(other(s.keep).key) + '과 바꾸자는 제안', '제안 검토하기'])
        : [RECV[s.step][2], '상태: ' + RECV[s.step][1], '제안 결과 보기']) : ['', '', '']),
      cardNew: hasProposal(s) && s.step === 'proposed' && !s.bSeen,
    };
  }
  function viewAfter(s, key) {
    return { stepperDeclined: pstep(4, 'fail', '상대방이 제안을 거절 · 내 좌석 그대로'), now: bothMine(), after: pairText(s.keep, key), cand: seatName(key), candLabel: '옆자리 후보 · ' + sideOf(s.keep, key) };
  }
  function viewDone(s, key) {
    var give = other(s.keep);
    return { cand: seatName(key), date: DEMO.dateLine(mine(s.keep)), seats: 'R석 · B구역 ' + pairText(s.keep, key), gave: 'B구역 ' + seatName(give.key) };
  }
  function viewFailed() { return { mine: dateRound() + ' · R석 B구역 ' + bothMine(), keepText: '2장 모두 유지 (목표)', stepper: pstep(5, 'fail', '최종 확인 실패 · 2장 모두 유지 (목표)') }; }
  var SENT_STEPS = [['좌석 방향 선택', '유지할 좌석을 골랐어요'], ['옆자리 후보 확인', '배치도·양방향 조건 확인 통과'], ['교환 제안 보내기', '최종 비교 후 내 동의 완료'],
    ['상대방 검토', '옆자리 관객이 검토 중이에요'], ['제안 수락', '상대방이 제안을 수락해야 다음으로 가요'], ['최종 확인 중', '티켓·조건을 마지막으로 확인해요'],
    ['교환 완료', '최종 확인을 통과해야 표시돼요']];
  function viewSent() { return { steps: DEMO.timeline(SENT_STEPS, 3), sub: '상대방이 검토하는 동안 내 티켓 2장은 그대로 유효해요.' }; }
  function viewCancelled(from) {
    return { stepper: pstep(PAIR_CANCEL_AT[from] === undefined ? 4 : PAIR_CANCEL_AT[from], 'stop', '제안 취소 · 내 티켓 2장 그대로'), title: '교환 제안을 취소했어요', body: '보낸 제안은 닫혔어요. 옆자리 관객에게는 취소됐다고 보여요 (서비스 설계 가정). 내 티켓 2장은 그대로 유효해요.',
      primary: '좌석 방향 다시 고르기', secondary: '처음으로' };
  }
  var STATUS_A = { select: '연석 만들기 준비 중', proposed: '교환 제안 보냄 · 상대방 검토 중', accepted: '상대방 제안 수락 · 최종 확인 전', final: '최종 확인 중',
    done: '교환 완료 (시연)', declined: '상대방이 제안을 거절함', cancelled: '교환 제안 취소', failed: '최종 확인 실패 · 내 티켓 유지 (목표)' };
  function statusB(s) {
    if (!hasProposal(s)) return s.consent ? '교환 제안 받는 중 · 도착한 제안 없음' : '교환 제안 받지 않음';
    if (s.step === 'proposed') return s.bSeen ? '제안 검토 중 · 응답 전' : '교환 제안 도착 · 아직 열어보지 않음';
    return { proposed: '교환 제안 도착 · 응답 전', accepted: '제안 수락함 · 최종 확인 전', final: '최종 확인 중', done: '교환 완료 (시연)',
      failed: '최종 확인 실패', declined: '제안 거절함', cancelled: '신청자가 제안 취소' }[s.step];
  }
  // 시연 제어판 (폰 밖, 실제 서비스 기능 아님)
  function viewCtl(s) {
    var b = [], hint;
    if (s.step === 'select') hint = s.consent ? '② 신청자 A 폰에서 후보를 고르고 교환 제안을 보내세요.' : "① 수신자 B 폰에서 '교환 제안 받기'를 켜고 저장하세요.";
    else if (s.step === 'proposed') hint = '③ 수신자 B 폰에서 제안을 열어 수락하거나 거절하세요.';
    else if (s.step === 'accepted') { hint = '④ 양쪽이 수락했어요. 예매처 최종 확인을 시작하세요.'; b = [DEMO.ctlBtn('toFinal', '최종 확인 시작')]; }
    else if (s.step === 'final') { hint = '⑤ 최종 확인 결과를 정하세요.'; b = [DEMO.ctlBtn('simOk', '최종 확인 성공'), DEMO.ctlBtn('simFail', '최종 확인 실패', 'bad')]; }
    else hint = "결과 화면이에요. '처음부터 다시'로 다시 체험해요.";
    var can = s.step === 'select';
    return { hint: hint, buttons: b, hasButtons: b.length > 0, status: STATUS_A[s.step],
      profiles: PROFILE_ORDER.map(function (p) {
        var on = s.profile === p;
        return { val: p, label: PROFILES[p].label, pressed: on ? 'true' : 'false', disabled: !can, style: !can ? CHIP_DIS : on ? CHIP_ON : CHIP_OFF };
      }),
      profileNote: can ? '후보를 찾기 전에 바꿀 수 있어요.' : '제안을 보낸 뒤에는 바꿀 수 없어요.' };
  }
  function views(s, demo) {
    var v = { isDemo: !!demo, step: s.step, mode: viewMode(s, demo), seat: viewSeat(s), adj: viewAdj(s, demo), warn: viewWarn(s),
      receive: viewReceive(s), intent: viewIntent(s, demo), failed: viewFailed(), sent: viewSent(), cancelled: viewCancelled(s.cancelledFrom), ctl: viewCtl(s),
      statusA: STATUS_A[s.step], statusB: statusB(s) };
    if (s.cand) { v.after = viewAfter(s, s.cand); v.done = viewDone(s, s.cand); }
    return v;
  }
  // 정적 보드(다른 폰·P13 상태 보드)가 쓰는 기본 화면 데이터: 11열 4번을 유지하고 11열 5번에 제안하는 장면
  function defaultViews() {
    var base = initialState();
    var sel = initialState(); sel.consent = true; sel.intentDraft = true; sel.cand = FLEX;
    var sent = DEMO.clone(sel); sent.step = 'proposed'; sent.bSeen = true;
    return { mode: viewMode(base, false), seat: viewSeat(base), adj: viewAdj(sel, false), warn: viewWarn(sel), receive: viewReceive(sent),
      intent: viewIntent(base, false), after: viewAfter(sel, FLEX), done: viewDone(sel, FLEX), failed: viewFailed(), sent: viewSent(),
      cancelled: viewCancelled('proposed'), isDemo: false };
  }

  return { MINE: MINE, LAYOUT: LAYOUT, HOLDERS: HOLDERS, PROFILES: PROFILES, FLEX: FLEX, adjacency: adjacency, judgeCandidate: judgeCandidate,
    candidates: candidates, neighbors: neighbors, proposable: proposable, holderOf: holderOf,
    initialState: initialState, reset: reset, reduce: reduce, views: views, defaultViews: defaultViews };
})(typeof DEMO !== 'undefined' ? DEMO : require('./demo3b_store.js'));
if (typeof module !== 'undefined') module.exports = PAIR;
