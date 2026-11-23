/* Seat Swap 연석 만들기 데모 — 상태·판정 엔진 (STEP 3C, 실험 기능 · 수요 미검증)
 *
 * 이 파일이 원본이다. tools/authoring/apply_pair_3c.py 가 P12(연석 만들기) 페이지 로직에 demo3b_store.js 와 함께 넣고,
 * 같은 코드로 컴포넌트의 기본 화면 데이터를 계산하며, tools/test_pair_engine.cjs 가 단위 테스트한다.
 *
 * STEP 3B 엔진(DEMO)에서 다시 쓰는 것: 조건 판정(evaluate·judge), 제안 이후 진행 흐름(flowNext·CANCELABLE·TERMINAL),
 * 표시 형식(resultRow·flags·ticketLine). 여기서 새로 정의하는 것은 연석에만 있는 판정(배치도 인접·수신 동의·동행 좌석)과 화면 데이터다.
 *
 * - 모든 좌석·배치도·동의·정책 판정은 시연용 모의 데이터다. 실제 예매처·결제·티켓 변경과 연결되지 않는다.
 * - 옆자리 관객의 '제안 수신 동의'와 수락·거절, 최종 확인 결과는 데모 모드 버튼으로 시뮬레이션한다.
 * - 외부 라이브러리 없음. ES5 문법만 쓴다 (런타임의 new Function 안에서 실행됨).
 */
var PAIR = (function (DEMO) {
  /* ------------------------------------------------------------------ 모의 데이터 */
  var POLICY_OK = '시연 판정: 교환 가능';
  // 나(A)의 같은 회차 티켓 2장. 한 장은 지키고(keep) 다른 한 장을 옆자리 관객에게 내놓는다(offer).
  var MINE = [
    { key: '7-12', label: '티켓 1', round: 'R3', grade: 'R석', zone: 'B', row: 7, seat: 12, price: '154,000원 (가상)', casting: null, policy: POLICY_OK },
    { key: '11-4', label: '티켓 2', round: 'R3', grade: 'R석', zone: 'B', row: 11, seat: 4, price: '154,000원 (가상)', casting: null, policy: POLICY_OK },
  ];
  // 배치도 (모의). 좌석 번호가 이어져도 블록이 다르면(통로) 붙어 있지 않다. 확인 범위 밖 좌석은 '인접 여부 확인 필요'.
  var LAYOUT = {
    round: 'R3', zone: 'B', firstRow: 5, lastRow: 12, seats: 14,
    blocks: [[1, 12], [13, 14]],                 // 12번과 13번 사이에 세로 통로
    verified: { 11: [[1, 14]], 7: [[12, 14]] },  // 배치도 데이터로 확인한 범위 (7열 1~11번은 데이터 없음)
  };
  // 옆자리 관객(B)이 등록한 조건: 같은 회차는 필수, 구역은 선호
  var WANTS_R3 = { rounds: ['R3'], roundImp: '필수', zones: ['B'], zoneImp: '선호', rowMax: 20, rowImp: '무관', castImp: null };
  var WANTS_FRONT = { rounds: ['R3'], roundImp: '필수', zones: ['B'], zoneImp: '선호', rowMax: 6, rowImp: '필수', castImp: null };
  // 좌석별 소유자 상태. consent = 제안 수신 동의 (동의하지 않은 관객에게는 제안을 보내지 않는다)
  var HOLDERS = {
    '11-3': { consent: false },
    '7-11': { consent: true, policy: POLICY_OK, wants: WANTS_R3, companion: null },
    '7-13': { consent: true, policy: POLICY_OK, wants: WANTS_R3, companion: null },
  };
  // 11열 5번 관객의 상황은 데모 모드에서 바꿔 볼 수 있다
  var FLEX = '11-5';
  var PROFILES = {
    basic: { label: '기본', consent: true, policy: POLICY_OK, wants: WANTS_R3, companion: null },
    companion: { label: '동행 좌석 있음', consent: true, policy: POLICY_OK, wants: WANTS_R3, companion: { key: '11-6', policy: '시연 판정: 좌석별 교환 가능' } },
    mismatch: { label: '조건 불일치', consent: true, policy: POLICY_OK, wants: WANTS_FRONT, companion: null },
    unknown: { label: '자격 미확인', consent: true, policy: null, wants: WANTS_R3, companion: null },
    noConsent: { label: '동의 없음', consent: false },
  };
  var PROFILE_ORDER = ['basic', 'companion', 'mismatch', 'unknown', 'noConsent'];

  /* ------------------------------------------------------------------ 좌석 도우미 */
  function parse(key) { var p = key.split('-'); return { row: +p[0], seat: +p[1] }; }
  function seatName(key) { var p = parse(key); return p.row + '열 ' + p.seat + '번'; }
  function mine(key) { for (var i = 0; i < MINE.length; i++) if (MINE[i].key === key) return MINE[i]; return null; }
  function other(keep) { return MINE[0].key === keep ? MINE[1] : MINE[0]; }
  function holderOf(key, profile) {
    var h = key === FLEX ? PROFILES[profile] : HOLDERS[key];
    if (!h) return null;
    var p = parse(key);
    return { key: key, consent: !!h.consent, policy: h.policy === undefined ? null : h.policy, wants: h.wants || null, companion: h.companion || null,
      ticket: { round: LAYOUT.round, grade: 'R석', zone: LAYOUT.zone, row: p.row, seat: p.seat, price: '154,000원 (가상)', casting: null, policy: h.policy === undefined ? null : h.policy } };
  }
  function neighbors(keep) {
    var a = mine(keep), out = [];
    [a.seat - 1, a.seat + 1].forEach(function (n) { if (n >= 1 && n <= LAYOUT.seats) out.push(a.row + '-' + n); });
    return out;
  }
  function inRanges(list, n) { for (var i = 0; i < (list || []).length; i++) if (n >= list[i][0] && n <= list[i][1]) return true; return false; }
  function blockOf(n) { for (var i = 0; i < LAYOUT.blocks.length; i++) if (inRanges([LAYOUT.blocks[i]], n)) return i; return -1; }

  /* ------------------------------------------------------------------ 판정 */
  // 실제 인접 여부: 같은 회차 → 같은 구역 → 같은 열 → 번호 연속 → 배치도 확인 범위 → 같은 블록(통로·단절 없음).
  // 번호가 이어지는 것만으로는 인접으로 판단하지 않는다. res = ok | no | unknown
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
  // 옆자리 후보 하나를 판정한다. 결과: hidden(동의 없음 → 후보 아님) | ok(제안 가능) | no(제안 불가) | hold(확인 필요로 보류) | declined(이미 거절)
  function judgeCandidate(keep, key, profile, declined) {
    var h = holderOf(key, profile);
    var a = mine(keep), give = other(keep);
    if (!h || !h.consent) return { key: key, status: 'hidden', consent: false, proposable: false };
    var adj = adjacency(a, h.ticket);
    // ② 상대가 원하는 조건 ↔ 내가 내놓을 좌석 (STEP 3B 의 양방향 판정 규칙 그대로)
    var theirs = DEMO.evaluate(h.wants, give, 'theirs');
    var wantFail = theirs.filter(function (r) { return r.res === 'fail' || (r.res === 'unknown' && r.imp === '필수'); });
    var elig = { mine: give.policy, theirs: h.policy };
    var eligOk = elig.mine !== null && elig.theirs !== null;
    var comp = h.companion;
    var compRes = !comp ? 'skip' : (comp.policy === null ? 'unknown' : 'warn');
    var status = 'ok', reason = '';
    if ((declined || []).indexOf(key) >= 0) { status = 'declined'; reason = '이 제안은 거절됐어요. 다시 보내지 않아요.'; }
    else if (adj.res === 'no') { status = 'no'; reason = '인접 아님 · ' + adj.reason; }
    else if (wantFail.length) { status = 'no'; reason = '상대의 필수 조건과 맞지 않아요'; }
    else if (adj.res === 'unknown') { status = 'hold'; reason = '인접 여부 확인 필요'; }
    else if (!eligOk) { status = 'hold'; reason = '교환 자격 확인 필요'; }
    else if (compRes === 'unknown') { status = 'hold'; reason = '동행 좌석의 좌석별 교환 정책 확인 필요'; }
    return { key: key, status: status, reason: reason, consent: true, adj: adj, theirs: theirs, wantFail: wantFail, elig: elig, eligOk: eligOk,
      companion: comp, compRes: compRes, holder: h, proposable: status === 'ok' };
  }
  function candidates(s) {
    return neighbors(s.keep).map(function (k) { return judgeCandidate(s.keep, k, s.profile, s.declined); });
  }
  function proposable(s, key) {
    if (!key) return false;
    if (neighbors(s.keep).indexOf(key) < 0) return false;
    return judgeCandidate(s.keep, key, s.profile, s.declined).proposable;
  }

  /* ------------------------------------------------------------------ 상태 */
  function initialState() {
    return { picked: [MINE[0].key, MINE[1].key], mode: 'pair', formKey: 0, keep: '11-4', dirKey: 0, profile: 'basic',
      cand: null, ack: false, ackKey: 0, step: 'select', declined: [], hint: '' };
  }
  // 처음 상태로 (입력 요소의 key 를 바꿔 브라우저에 남은 체크 상태까지 지운다)
  function reset(st) {
    var s = initialState();
    if (st) { s.formKey = st.formKey + 1; s.dirKey = st.dirKey + 1; s.ackKey = st.ackKey + 1; }
    return s;
  }
  var ACTIVE = ['proposed', 'accepted', 'final'];
  var FLOW_SCREEN = { accepted: 'PairAccepted', declined: 'PairDeclined', final: 'StatusFinal', done: 'PairDone', failed: 'ExFinalFailed' };
  var HINT_GENERAL = '좌석·회차 교환은 07 일반 교환 보드의 체험 폰에서 해볼 수 있어요. 이 폰은 연석 만들기(실험 기능)를 체험해요.';
  var HINT_PICK = '연석 만들기는 같은 회차 티켓 2장이 필요해요. 2장을 모두 선택해 주세요.';

  // action: { type, val, checked, screen } → { state, nav }   (nav 형식은 STEP 3B 와 같다)
  function reduce(st, action) {
    var s = DEMO.clone(st);
    var t = action.type;
    var clearPick = function () { s.cand = null; s.ack = false; s.ackKey += 1; };
    var selecting = s.step === 'select';
    switch (t) {
      case 'pick':           // 교환할 티켓 체크박스 (기본 동작 유지)
        if (!selecting || !mine(action.val)) return { state: st, nav: null };
        var i = s.picked.indexOf(action.val);
        if (action.checked && i < 0) s.picked.push(action.val);
        if (!action.checked && i >= 0) s.picked.splice(i, 1);
        s.hint = ''; return { state: s, nav: null };
      case 'mode':           // 교환 방식 라디오
        if (!selecting || (action.val !== 'pair' && action.val !== 'general')) return { state: st, nav: null };
        s.mode = action.val; s.hint = ''; return { state: s, nav: null };
      case 'next':
        if (!selecting) return { state: st, nav: { stay: true } };
        if (s.mode !== 'pair') { s.hint = HINT_GENERAL; return { state: s, nav: { stay: true } }; }
        if (s.picked.length < 2) { s.hint = HINT_PICK; return { state: s, nav: { stay: true } }; }
        s.hint = ''; return { state: s, nav: { push: 'PairSeat' } };
      case 'dir':            // 어느 좌석을 지킬지 (= 어느 쪽으로 모을지)
        if (!selecting || !mine(action.val)) return { state: st, nav: null };
        if (s.keep !== action.val) { s.keep = action.val; clearPick(); }
        return { state: s, nav: null };
      case 'toCandidates':
        if (!selecting) return { state: st, nav: { stay: true } };
        return { state: s, nav: { push: 'PairAdjacency' } };
      case 'profile':        // 데모 모드: 11열 5번 관객의 상황 바꾸기
        if (!selecting || !PROFILES[action.val]) return { state: st, nav: null };
        s.profile = action.val;
        if (s.cand && !proposable(s, s.cand)) clearPick();
        s.ack = false; s.ackKey += 1;
        return { state: s, nav: null };
      case 'choose':         // 후보 선택 (제안 가능한 후보만)
        if (!selecting || !proposable(s, action.val)) return { state: st, nav: null };
        if (s.cand !== action.val) { s.cand = action.val; s.ack = false; s.ackKey += 1; }
        return { state: s, nav: null };
      case 'toWarn':
        if (!selecting || !proposable(s, s.cand)) return { state: st, nav: { stay: true } };
        return { state: s, nav: { push: 'PairWarn' } };
      case 'ack':            // 제안 전 확인 체크박스 (기본 동작 유지)
        if (!selecting || !s.cand) return { state: st, nav: null };
        s.ack = !!action.checked; return { state: s, nav: null };
      case 'send':
        if (!selecting || !s.ack || !proposable(s, s.cand)) return { state: st, nav: { stay: true } };
        s.step = 'proposed'; return { state: s, nav: { push: 'StatusSent' } };
      case 'simAccept': case 'simDecline': case 'toFinal': case 'simOk': case 'simFail':
        var nx = DEMO.flowNext(s.step, t);          // STEP 3B 와 같은 진행 규칙
        if (!nx) return { state: st, nav: { stay: true } };
        s.step = nx; if (nx === 'declined') s.declined.push(s.cand);
        return { state: s, nav: { push: FLOW_SCREEN[nx] } };
      case 'cancel':
        if (DEMO.CANCELABLE.indexOf(s.step) < 0) return { state: st, nav: { stay: true } };
        s.step = 'cancelled'; return { state: s, nav: { push: 'ExCancelled' } };
      case 'otherCandidate': // 거절 뒤: 같은 방향의 다른 후보 보기 (거절한 후보는 다시 고를 수 없다)
        if (s.step !== 'declined') return { state: st, nav: { stay: true } };
        s.step = 'select'; clearPick(); return { state: s, nav: { reset: ['PairMode', 'PairSeat', 'PairAdjacency'] } };
      case 'otherDir':       // 거절 뒤: 반대 방향으로 모으기
        if (s.step !== 'declined') return { state: st, nav: { stay: true } };
        s.step = 'select'; s.keep = other(s.keep).key; s.dirKey += 1; clearPick();
        return { state: s, nav: { reset: ['PairMode', 'PairSeat'] } };
      case 'restart':        // 취소·실패 뒤 다시 신청: 고른 방향은 유지
        if (DEMO.TERMINAL.indexOf(s.step) < 0) return { state: st, nav: { stay: true } };
        s.step = 'select'; s.declined = []; clearPick(); return { state: s, nav: { reset: ['PairMode', 'PairSeat'] } };
      case 'home':
        return { state: reset(s), nav: { reset: ['PairMode'] } };
      case 'back':
        if (ACTIVE.indexOf(s.step) >= 0) return { state: st, nav: { stay: true } };   // 진행 중에는 '취소'로만 빠져나간다
        if (DEMO.TERMINAL.indexOf(s.step) >= 0) return { state: reset(s), nav: { reset: ['PairMode'] } };
        return { state: s, nav: { pop: true } };
      default:
        return { state: st, nav: null };
    }
  }

  /* ------------------------------------------------------------------ 화면 데이터 */
  var CHIP_ON = 'height: 30px; padding: 0 10px; border-radius: 15px; font-family: inherit; font-size: 12px; font-weight: 700; border: 1.5px solid #5B3DF5; background: #F0EDFF; color: #3A26C4';
  var CHIP_OFF = 'height: 30px; padding: 0 10px; border-radius: 15px; font-family: inherit; font-size: 12px; font-weight: 500; border: 1px solid #DADDE3; background: #FFFFFF; color: #191B22';
  var OPT_ON = 'display: flex; align-items: flex-start; gap: 12px; border: 1.5px solid #5B3DF5; background: #F7F5FF; border-radius: 14px; padding: 14px';
  var OPT_OFF = 'display: flex; align-items: flex-start; gap: 12px; border: 1px solid #DADDE3; border-radius: 14px; padding: 14px';
  var TICKET_ON = 'display: flex; align-items: center; gap: 12px; border: 1.5px solid #5B3DF5; background: #F7F5FF; border-radius: 14px; padding: 14px 16px';
  var TICKET_OFF = 'display: flex; align-items: center; gap: 12px; border: 1px solid #DADDE3; background: #FFFFFF; border-radius: 14px; padding: 14px 16px';
  var MODE_ON = 'display: flex; align-items: flex-start; gap: 12px; border: 1.5px solid #5B3DF5; background: #F7F5FF; border-radius: 16px; padding: 16px';
  var MODE_OFF = 'display: flex; align-items: flex-start; gap: 12px; border: 1px solid #DADDE3; border-radius: 16px; padding: 16px';
  var PICK_ON = 'align-self: flex-start; height: 26px; padding: 0 12px; border-radius: 10px; font-family: inherit; font-size: 12px; font-weight: 700; border: 0; background: #5B3DF5; color: #FFFFFF';
  var PICK_OFF = 'align-self: flex-start; height: 26px; padding: 0 12px; border-radius: 10px; font-family: inherit; font-size: 12px; font-weight: 700; border: 1px solid #C9BFFF; background: #FFFFFF; color: #3A26C4';
  var PICK_NO = 'align-self: flex-start; height: 26px; padding: 0 12px; border-radius: 10px; font-family: inherit; font-size: 12px; font-weight: 700; border: 0; background: #E6E8EC; color: #8B909C';

  function item(kind, text, label, detail) {
    var o = { label: label || '', text: text, detail: detail || '', hasDetail: !!detail };
    var f = DEMO.flags(kind); for (var k in f) o[k] = f[k];
    return o;
  }
  function pairText(a, b) {   // 같은 열 두 좌석 → '11열 4번, 5번'
    var x = parse(a), y = parse(b);
    var lo = Math.min(x.seat, y.seat), hi = Math.max(x.seat, y.seat);
    return x.row + '열 ' + lo + '번, ' + hi + '번';
  }
  function bothMine() { return seatName(MINE[0].key) + ' · ' + seatName(MINE[1].key); }

  function viewMode(s, demo) {
    return {
      tickets: MINE.map(function (m) {
        var on = s.picked.indexOf(m.key) >= 0;
        return { val: m.key, title: m.grade + ' · ' + m.zone + '구역 ' + seatName(m.key), sub: m.label + ' · ' + (m.policy ? '교환 가능 (시연 판정)' : '교환 자격 확인 필요'),
          checked: on, style: on ? TICKET_ON : TICKET_OFF };
      }),
      pairChecked: s.mode === 'pair', generalChecked: s.mode !== 'pair',
      pairStyle: s.mode === 'pair' ? MODE_ON : MODE_OFF, generalStyle: s.mode === 'pair' ? MODE_OFF : MODE_ON,
      formKey: 'f' + s.formKey, hint: demo ? s.hint : '', hasHint: !!(demo && s.hint),
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
        seats.push({ mine: kind === 'keep', offer: kind === 'offer', cand: kind === 'near', other: kind === 'other',
          aisle: n === LAYOUT.blocks[0][1] });
      }
      rows.push({ label: r + '열', seats: seats });
    }
    return {
      rows: rows, dirKey: 'd' + s.dirKey,
      options: MINE.slice().reverse().map(function (m) {   // 11열로 모으기(11열 4번을 지킴)가 먼저
        var g = other(m.key), on = s.keep === m.key;
        return { val: m.key, checked: on, style: on ? OPT_ON : OPT_OFF,
          title: m.row + '열로 모으기 → ' + m.row + '열 ' + (m.seat - 1) + '·' + m.seat + '번 또는 ' + m.seat + '·' + (m.seat + 1) + '번',
          desc: '지킬 좌석 ' + seatName(m.key) + ' · 내놓을 좌석 ' + seatName(g.key) + '. 옆자리 관객이 ' + seatName(g.key) + '으로 옮겨 가요. 같은 R석이지만 좌석 위치는 바뀌어요',
          tag: on };
      }),
      keepName: seatName(keep.key), offerName: seatName(give.key),
    };
  }
  function candCard(s, c) {
    var title = seatName(c.key);
    var side = parse(c.key).seat < mine(s.keep).seat ? '왼쪽' : '오른쪽';
    if (c.status === 'hidden') {
      return { key: c.key, hidden: true, shown: false, title: title + ' · ' + side, note: '제안 수신 동의가 확인되지 않은 좌석이라 후보에서 뺐어요. 이 관객에게는 제안을 보내지 않아요.' };
    }
    var give = other(s.keep);
    var adjText = { ok: '인접 확인 (배치도)', no: '인접 아님', unknown: '인접 여부 확인 필요' }[c.adj.res];
    var adjKind = { ok: 'ok', no: 'no', unknown: 'need' }[c.adj.res];
    var last = c.adj.checks[c.adj.checks.length - 1];
    var adjDetail = c.adj.res === 'ok' ? '같은 회차·열 · 번호 연속 · ' + last.detail : last.detail + (c.adj.res === 'no' && last.dim.indexOf('배치도') === 0 ? ' (번호만 보고 판단하지 않아요)' : '');
    var rows = [
      item('ok', '동의함 (시연)', '제안 수신 동의'),
      item(adjKind, adjText, '인접 여부 (' + seatName(s.keep) + ' 옆)', adjDetail),
      c.eligOk ? item('ok', '양쪽 교환 가능 (시연)', '교환 자격')
               : item('need', '확인 필요', '교환 자격', (c.elig.theirs === null ? '상대 티켓의' : '내 티켓의') + ' 교환 정책 확인 상태가 없어요. 확인 전에는 제안하지 않아요.'),
      c.wantFail.length ? item('no', '불일치', '상대 조건 ↔ 내가 줄 ' + seatName(give.key),
                               c.wantFail.map(function (r) { return r.dim + ' ' + r.imp + ' · ' + r.want + ' / 내 좌석 ' + r.have; }).join(', ') + '. 상대의 조건은 내가 바꿀 수 없어요.')
                        : item('ok', '충족', '상대 조건 ↔ 내가 줄 ' + seatName(give.key), c.theirs.filter(function (r) { return r.res !== 'skip'; }).map(function (r) { return r.dim + ' ' + r.imp; }).join(' · ')),
    ];
    if (c.companion) {
      rows.push(c.compRes === 'unknown'
        ? item('need', '확인 필요', '동행 좌석', seatName(c.companion.key) + '과 함께 예매 · 좌석별 교환 정책을 확인하지 못했어요')
        : item('plan', '분리될 수 있어요', '동행 좌석', seatName(c.companion.key) + '과 함께 예매 · 상대가 거절할 수 있어요 · ' + c.companion.policy));
    }
    var st = { ok: ['ok', c.companion ? '제안 가능 · 동행 주의' : '제안 가능'], no: ['no', '제안 불가'], hold: ['need', '제안 보류'], declined: ['mute', '거절됨'] }[c.status];
    var selected = s.cand === c.key;
    var o = { key: c.key, hidden: false, shown: true, title: title + ' · ' + side, rows: rows, text: st[1], reason: c.reason, hasReason: !!c.reason,
      canPick: c.proposable, cantPick: !c.proposable, pressed: selected ? 'true' : 'false',
      pickText: selected ? '선택됨' : c.proposable ? '이 후보 선택' : '선택할 수 없음', pickStyle: selected ? PICK_ON : c.proposable ? PICK_OFF : PICK_NO,
      border: selected ? 'border: 1.5px solid #5B3DF5; background: #F7F5FF' : 'border: 1px solid #E6E8EC; background: #FFFFFF' };
    var f = DEMO.flags(st[0]); for (var k in f) o[k] = f[k];
    return o;
  }
  function viewAdj(s, demo) {
    var cs = candidates(s);
    var ok = s.cand && proposable(s, s.cand);
    var anyOk = cs.some(function (c) { return c.proposable; });
    var nb = neighbors(s.keep);
    return {
      keepName: seatName(s.keep), offerName: seatName(other(s.keep).key),
      cards: cs.map(function (c) { return candCard(s, c); }),
      showProfiles: !!demo && nb.indexOf(FLEX) >= 0,
      profiles: PROFILE_ORDER.map(function (p) { return { val: p, label: PROFILES[p].label, pressed: s.profile === p ? 'true' : 'false', style: s.profile === p ? CHIP_ON : CHIP_OFF }; }),
      canNext: !!ok, cantNext: !ok,
      nextHint: ok ? '' : anyOk ? '제안할 후보를 선택해 주세요.' : '제안할 수 있는 옆자리가 없어요. 뒤로 가서 반대 방향으로 모으기를 확인해 보세요.',
    };
  }
  function twoWay(s, c) {
    var give = other(s.keep);
    return [
      item(c.adj.res === 'ok' ? 'ok' : 'need', c.adj.res === 'ok' ? '충족' : '확인 필요', '① 내 조건: ' + seatName(s.keep) + ' 바로 옆', '배치도로 인접 확인 · ' + seatName(c.key)),
      item(c.wantFail.length ? 'no' : 'ok', c.wantFail.length ? '불일치' : '충족', '② 상대 조건 ↔ 내가 줄 ' + seatName(give.key),
           c.theirs.filter(function (r) { return r.res !== 'skip'; }).map(function (r) { return r.dim + ' ' + r.imp; }).join(' · ')),
    ];
  }
  function viewWarn(s) {
    if (!s.cand) return null;
    var c = judgeCandidate(s.keep, s.cand, s.profile, s.declined);
    if (c.status === 'hidden') return null;
    var give = other(s.keep), canSend = s.step === 'select' && s.ack && c.proposable;
    return {
      now: bothMine() + ' · 떨어져 있어요',
      after: pairText(s.keep, s.cand) + ' · 나란히 (완료 시에만)',
      candTitle: '상대 후보 (' + seatName(s.cand) + ') 좌석 변화',
      candMove: seatName(s.cand) + ' → ' + seatName(give.key) + '으로 옮겨요. 좋고 나쁨은 사람마다 달라요.',
      twoWay: twoWay(s, c),
      twoWayNote: "양쪽 조건이 맞아도 아직 '매칭 완료'가 아니에요. 상대 수락과 최종 확인이 남아 있어요.",
      warnTitle: c.companion ? '상대의 동행 좌석(' + seatName(c.companion.key) + ')이 분리될 수 있어요' : '보내기 전에 확인해 주세요',
      hasCompanion: !!c.companion,
      companionText: c.companion ? '상대는 ' + seatName(c.companion.key) + '과 함께 예매했어요. 교환하면 상대 일행이 떨어지게 되므로 거절할 수 있어요. 예매 1건에 좌석이 여럿이라는 이유만으로 막지는 않아요 (' + (c.companion.policy || '좌석별 교환 정책 확인 필요') + ').' : '',
      ackKey: 'a' + s.ackKey, canSend: canSend, cantSend: !canSend, sendText: seatName(s.cand) + ' 관객에게 제안 보내기',
      ack: !!s.ack,
      sendHint: s.step !== 'select' ? '이미 제안을 보냈거나 진행할 수 없는 상태예요.' : (!c.proposable ? '이 후보에게는 지금 제안할 수 없어요.' : (s.ack ? '' : '위 내용을 확인했다고 선택하면 제안을 보낼 수 있어요.')),
    };
  }
  function viewAfter(s, key) {
    return { now: bothMine(), after: pairText(s.keep, key), cand: seatName(key), candLabel: '옆자리 후보 · ' + (parse(key).seat < mine(s.keep).seat ? '왼쪽' : '오른쪽') };
  }
  function viewDone(s, key) {
    var give = other(s.keep);
    return { cand: seatName(key), date: DEMO.dateLine(mine(s.keep)), seats: 'R석 · B구역 ' + pairText(s.keep, key), gave: 'B구역 ' + seatName(give.key) };
  }
  function viewFailed() {
    return { mine: DEMO.dateLine(MINE[0]) + ' · R석 B구역 ' + bothMine(), keepText: '2장 모두 유지 (목표)' };
  }
  function views(s, demo) {
    var v = { isDemo: !!demo, step: s.step, mode: viewMode(s, demo), seat: viewSeat(s), adj: viewAdj(s, demo), failed: viewFailed() };
    var w = viewWarn(s);
    if (w) v.warn = w;
    if (s.cand) { v.after = viewAfter(s, s.cand); v.done = viewDone(s, s.cand); }
    return v;
  }
  // 정적 보드(다른 폰·P13 상태 보드)가 쓰는 기본 화면 데이터: 11열 4번을 지키고 11열 5번에 제안하는 장면
  function defaultViews() {
    var base = initialState();
    var sel = initialState(); sel.cand = FLEX;
    var comp = initialState(); comp.cand = FLEX; comp.profile = 'companion';
    return { mode: viewMode(base, false), seat: viewSeat(base), adj: viewAdj(sel, false), warn: viewWarn(comp),
      after: viewAfter(sel, FLEX), done: viewDone(sel, FLEX), failed: viewFailed(), isDemo: false };
  }

  return { MINE: MINE, LAYOUT: LAYOUT, HOLDERS: HOLDERS, PROFILES: PROFILES, FLEX: FLEX, adjacency: adjacency, judgeCandidate: judgeCandidate,
    candidates: candidates, neighbors: neighbors, proposable: proposable, holderOf: holderOf,
    initialState: initialState, reset: reset, reduce: reduce, views: views, defaultViews: defaultViews };
})(typeof DEMO !== 'undefined' ? DEMO : require('./demo3b_store.js'));
if (typeof module !== 'undefined') module.exports = PAIR;
