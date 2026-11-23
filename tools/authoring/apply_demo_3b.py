"""STEP 3B: 일반 좌석·회차 교환 인터랙션 (1회성 적용 스크립트).

- 상태·매칭: tools/authoring/demo3b_store.js (원본) → P07 일반 교환 페이지 로직에 삽입
- 컴포넌트: 페이지가 넘겨주는 demo 데이터만 그리는 템플릿으로 바꾼다. demo 가 없으면(다른 폰·다른 보드)
  같은 엔진으로 계산한 기본값(DEFAULT_VIEW)을 그려 기존 정적 화면을 유지한다.
- 버튼·링크에는 data-act 속성만 붙인다. 동작은 체험 폰(P07 보드 1번 폰)에서만 페이지 로직이 처리한다.
사용법: python3 tools/authoring/apply_demo_3b.py   (대상 파일을 git 기준 상태에서 실행할 것)
"""
import json
import re
import subprocess
import sys
import uuid as uuidlib
from hashlib import sha256
from pathlib import Path
from dc_kit import *

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
COMP = SRC / 'components'
STORE = Path(__file__).resolve().parent / 'demo3b_store.js'

DEFAULTS = json.loads(subprocess.check_output(
    ['node', '-e', "process.stdout.write(JSON.stringify(require(%s).defaultViews()))" % json.dumps(str(STORE))]).decode('utf-8'))

KINDS5 = ['ok', 'plan', 'no', 'mute', 'need']
BACK_SPAN = ('<span aria-hidden="true" style="width: 44px; height: 44px; display: flex; align-items: center; justify-content: center">%s</span>'
             % icon('back', TEXT, 24, 2))
BACK_BTN = ('<button type="button" data-act="back" aria-label="뒤로" style="width: 44px; height: 44px; display: flex; align-items: center; '
            'justify-content: center; border: 0; padding: 0; background: transparent; cursor: pointer">%s</button>' % icon('back', TEXT, 24, 2))
DEFAULT_LOGIC = 'class Component extends DCLogic {\nrenderVals() {\nreturn {};\n}\n}'


def badge_switch(var, size=12):
    return ''.join('<sc-if value="{{%s.k_%s}}">%s</sc-if>' % (var, k, badge(k, '{{%s.text}}' % var, size)) for k in KINDS5)


def logic(key):
    """renderVals: 체험 폰이면 페이지가 준 demo[key], 아니면 기본 화면 데이터."""
    dv = DEFAULTS.get(key, {}) if key else {}
    sel = '(d && d.%s) || DEFAULT_VIEW' % key if key else 'DEFAULT_VIEW'
    return ('var DEFAULT_VIEW = %s;\nclass Component extends DCLogic {\nrenderVals() {\nvar d = this.props.demo;\nvar v = %s;\n'
            'var o = {};\nfor (var k in v) o[k] = v[k];\no.isDemo = !!(d && d.isDemo);\no.notDemo = !o.isDemo;\nreturn o;\n}\n}'
            % (json.dumps(dv, ensure_ascii=False), sel))


def act(html, a):
    """첫 번째 <button>/<a> 에 data-act 를 붙인다."""
    m = re.search(r'<(button|a)\b', html)
    return html[:m.end()] + ' data-act="%s"' % a + html[m.end():]


def patch(rel, pairs, key=None, back=False):
    p = COMP / rel
    t = p.read_text(encoding='utf-8')
    for old, new in pairs:
        if t.count(old) != 1:
            sys.exit('%s: 치환 대상 %d회 (%s)' % (rel, t.count(old), old[:80]))
        t = t.replace(old, new)
    if back:
        if t.count(BACK_SPAN) != 1:
            sys.exit('%s: 뒤로 표시를 찾지 못함' % rel)
        t = t.replace(BACK_SPAN, '<sc-if value="{{notDemo}}">%s</sc-if><sc-if value="{{isDemo}}">%s</sc-if>' % (BACK_SPAN, BACK_BTN))
    if t.count(DEFAULT_LOGIC) != 1:
        sys.exit('%s: 기본 로직 블록을 찾지 못함' % rel)
    t = t.replace(DEFAULT_LOGIC, logic(key))
    p.write_text(t, encoding='utf-8')
    print('컴포넌트:', rel)


def panel(title, buttons):
    st = {'primary': 'background: #5B3DF5; color: #FFFFFF; border: 0',
          'bad': 'background: #FFFFFF; color: #B03A3A; border: 1px solid #F2C6C6'}
    bt = ''.join('<button type="button" data-act="%s" style="flex: 1; height: 40px; border-radius: 10px; font-family: inherit; font-size: 13px; font-weight: 700; %s">%s</button>'
                 % (a, st[k], txt) for txt, a, k in buttons)
    return ('<sc-if value="{{isDemo}}"><div style="border: 1.5px dashed #C9BFFF; background: #F7F5FF; border-radius: 14px; padding: 10px 12px; display: flex; flex-direction: column; gap: 8px">'
            '<span style="display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 700; color: #3A26C4">%s데모 모드 · %s</span>'
            '<div style="display: flex; gap: 8px">%s</div></div></sc-if>' % (icon('info', PRIMARY_DARK, 14, 2.2), title, bt))


# ---------------------------------------------------------------- 공용 조각 (gen_screens_2c 와 같은 마크업)
def box(inner, bg=BG, pad='12px 14px', gap=6, border=''):
    return ('<div style="background: %s; border-radius: 14px; padding: %s; display: flex; flex-direction: column; gap: %dpx; %s">%s</div>'
            % (bg, pad, gap, border, inner))


def para(text, size=12, color=SUB2, weight=400):
    return '<p style="margin: 0; font-size: %dpx; line-height: 1.5; font-weight: %d; color: %s">%s</p>' % (size, weight, color, text)


def row_c(var):
    return ('<div style="display: flex; flex-direction: column; gap: 2px; padding: 5px 0; border-top: 1px solid #EEF0F3">'
            '<div style="display: flex; align-items: center; justify-content: space-between; gap: 6px">'
            '<span style="display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700">{{%(v)s.label}}<span style="{{%(v)s.impStyle}}">{{%(v)s.imp}}</span></span>%(b)s</div>'
            '<span style="font-size: 11px; line-height: 1.4; color: %(c2)s">{{%(v)s.detail}}</span>'
            '<sc-if value="{{%(v)s.hasNote}}"><span style="font-size: 11px; line-height: 1.4; color: %(c1)s">{{%(v)s.note}}</span></sc-if></div>'
            % {'v': var, 'b': badge_switch(var, 11), 'c1': SUB, 'c2': SUB2})


def row_full(var):
    return ('<div style="display: flex; flex-direction: column; gap: 4px; padding: 8px 0; border-top: 1px solid #EEF0F3">'
            '<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px">'
            '<span style="display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700">{{%(v)s.label}}<span style="{{%(v)s.impStyle}}">{{%(v)s.imp}}</span></span>%(b)s</div>'
            '<span style="font-size: 12px; color: %(c2)s">{{%(v)s.detail}}</span>'
            '<sc-if value="{{%(v)s.hasNote}}"><span style="font-size: 12px; line-height: 1.45; color: %(c1)s">{{%(v)s.note}}</span></sc-if></div>'
            % {'v': var, 'b': badge_switch(var, 12), 'c1': SUB, 'c2': SUB2})


# ================================================================ 컴포넌트
def build_matchcheck():
    main = ''.join([
        '<div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">%s<b style="font-size: 17px">맞을 수 있는 후보를 찾았어요</b></div>' % badge('plan', '후보 발견'),
        box('<span style="font-size: 12px; line-height: 1.45"><b style="color: %s">내 티켓(A)</b> {{mine}}</span>'
            '<span style="font-size: 12px; line-height: 1.45"><b style="color: %s">후보 티켓(B)</b> {{cand}}</span>' % (SUB, PRIMARY_DARK), pad='9px 12px', gap=3),
        box('<b style="font-size: 12px">① 내가 원하는 조건 ↔ 후보의 티켓</b><sc-for list="{{dirA}}" as="r">%s</sc-for>' % row_c('r'),
            bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='9px 12px', gap=0),
        box('<b style="font-size: 12px">② 후보가 원하는 조건 ↔ 내 티켓</b><sc-for list="{{dirB}}" as="r">%s</sc-for>' % row_c('r'),
            bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='9px 12px', gap=0),
        box('<div style="display: flex; gap: 6px; flex-wrap: wrap"><sc-for list="{{badges}}" as="b">%s</sc-for></div>' % badge_switch('b', 11)
            + para('{{summary}}', 11, SUB2), bg=SOFT, pad='9px 12px', gap=6),
    ])
    html = screen('양방향 조건 확인', '양방향 조건 확인', main, footer=act(cta('전후 정보 비교하기'), 'toCompare'), gap=8)
    (COMP / 'states/MatchCheck.dc.html').write_text(html, encoding='utf-8')
    patch('states/MatchCheck.dc.html', [], key='match', back=True)


def build_compare():
    row = ('<div style="display: grid; grid-template-columns: 62px 1fr 1fr; gap: 8px; padding: 7px 0; border-top: 1px solid #EEF0F3; align-items: start">'
           '<span style="font-size: 12px; font-weight: 700; color: %s">{{r.label}}</span>'
           '<span style="font-size: 12px; line-height: 1.4">{{r.a}}</span>'
           '<span style="display: flex; flex-direction: column; gap: 4px; font-size: 12px; line-height: 1.4; font-weight: 700">{{r.b}}%s</span></div>'
           % (SUB, badge_switch('r', 11)))
    main = ''.join([
        para('정보가 없으면 추정하지 않고 &#39;확인 필요&#39;로 표시해요. 시연용 모의 데이터예요.', 12, SUB),
        '<div style="display: flex; flex-direction: column"><div style="display: grid; grid-template-columns: 62px 1fr 1fr; gap: 8px; padding-bottom: 6px">'
        '<span></span><span style="font-size: 11px; font-weight: 700; color: %s">내 티켓 (지금)</span><span style="font-size: 11px; font-weight: 700; color: %s">받게 될 티켓</span></div>' % (SUB, PRIMARY_DARK)
        + '<sc-for list="{{rows}}" as="r">%s</sc-for></div>' % row,
        ('<label style="display: flex; align-items: flex-start; gap: 10px; font-size: 13px; line-height: 1.5; color: %s">'
         '<input type="checkbox" data-act="consent" key="{{consentKey}}" style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 0; flex-shrink: 0">이 조건으로 교환하는 데 동의해요 (내 수락)</label>' % TEXT),
    ])
    footer = ('<sc-if value="{{canSend}}">%s</sc-if><sc-if value="{{cantSend}}">%s</sc-if>'
              '<sc-if value="{{sendHint}}"><p style="margin: 0; font-size: 12px; line-height: 1.5; font-weight: 700; color: %s">{{sendHint}}</p></sc-if>'
              % (act(cta('교환 제안 보내기'), 'send'), cta('교환 제안 보내기', disabled=True), WARN_FG)
              + para('제안을 보내도 교환은 확정되지 않아요. 상대방이 수락하고 최종 확인을 통과해야 완료돼요.', 12, SUB))
    html = screen('교환 전후 비교', '교환 전후 비교', main, footer=footer, gap=10)
    (COMP / 'states/Compare.dc.html').write_text(html, encoding='utf-8')
    patch('states/Compare.dc.html', [], key='compare', back=True)


def build_mismatch():
    main = ''.join([
        '<div style="display: flex; flex-direction: column; gap: 8px"><span style="align-self: flex-start">%s %s</span>'
        '<h2 style="margin: 0; font-size: 21px; font-weight: 700; line-height: 1.4">필수 조건이 맞지 않는 후보는 보여주지 않아요</h2>%s</div>'
        % (badge('no', '후보 제외'), SIM_TAG, para('선호 조건은 맞지 않아도 후보로 남기고 차이를 알려줘요. 필수 조건은 내가 직접 바꾸기 전까지 그대로예요.')),
        ticket_row('제외한 후보 티켓', '{{cand}}'),
        box('<sc-for list="{{rows}}" as="r">%s</sc-for>' % row_full('r'), bg='#FFFFFF', border='border: 1px solid #E6E8EC', gap=0),
    ])
    footer = (act(cta('조건 수정하기'), 'edit')
              + '<sc-if value="{{canRelax}}">%s</sc-if><sc-if value="{{cantRelax}}">%s</sc-if>' % (act(cta('필수를 선호로 바꿔 보기', 'ghost'), 'relax'), cta('필수를 선호로 바꿔 보기', disabled=True))
              + '<sc-if value="{{canRelax}}">%s</sc-if><sc-if value="{{cantRelax}}">%s</sc-if>' % (
                  para('중요도는 내가 직접 고른 경우에만 바뀌어요.', 12, SUB),
                  para('후보의 필수 조건이 맞지 않는 경우예요. 상대방의 조건은 내가 바꿀 수 없어요.', 12, SUB)))
    html = screen('필수 조건 불일치', '필수 조건 불일치', main, footer=footer, gap=14)
    (COMP / 'exceptions/ExMismatch.dc.html').write_text(html, encoding='utf-8')
    patch('exceptions/ExMismatch.dc.html', [], key='mismatch', back=True)


def patch_status():
    patch('states/StatusSent.dc.html', [(cta('제안 취소하기', 'ghost'),
          panel('상대방 행동 시뮬레이션', [('상대방 수락', 'simAccept', 'primary'), ('상대방 거절', 'simDecline', 'bad')]) + act(cta('제안 취소하기', 'ghost'), 'cancel'))], back=True)
    patch('states/StatusAccepted.dc.html', [(cta('교환 취소하기 (최종 확인 전)', 'ghost'),
          panel('다음 단계 진행', [('최종 확인 시작', 'toFinal', 'primary')]) + act(cta('교환 취소하기 (최종 확인 전)', 'ghost'), 'cancel'))], back=True)
    patch('states/StatusFinal.dc.html', [(cta('확인이 끝나면 알려드려요', disabled=True),
          panel('최종 확인 결과 시뮬레이션', [('최종 확인 성공', 'simOk', 'primary'), ('최종 확인 실패', 'simFail', 'bad')]) + cta('확인이 끝나면 알려드려요', disabled=True))], back=True)
    for rel, pairs in [('exceptions/ExNoCandidate.dc.html', [('조건 수정하기', 'edit'), ('교환 신청 취소', 'cancel')]),
                       ('exceptions/ExDeclined.dc.html', [('다른 후보 찾기', 'retry'), ('교환 신청 취소', 'cancel')]),
                       ('exceptions/ExCancelled.dc.html', [('교환 다시 신청', 'restart'), ('예매 상세로', 'home')]),
                       ('exceptions/ExFinalFailed.dc.html', [('내 티켓 확인', 'home'), ('다시 신청', 'restart')])]:
        reps = []
        for text, a in pairs:
            kind = 'primary' if pairs.index((text, a)) == 0 else 'ghost'
            reps.append((cta(text, kind), act(cta(text, kind), a)))
        patch(rel, reps, back=True)


def patch_exchange():
    # 예매 상세: 신청 링크에 data-act (체험 폰에서만 의미)
    patch('exchange/Main.dc.html', [('<a href="Request.dc.html" style=', '<a href="Request.dc.html" data-act="start" style=')])
    # 조건 등록
    seg_old = {k: importance_seg(v) for k, v in (('round', '필수'), ('zone', '선호'), ('row', '선호'))}
    seg_tpl = lambda k: ('<span style="{{%sSeg.wrap}}"><sc-for list="{{%sSeg.items}}" as="b"><button type="button" data-act="imp" data-row="{{b.row}}" '
                         'data-val="{{b.name}}" aria-pressed="{{b.pressed}}" style="{{b.style}}">{{b.name}}</button></sc-for></span>' % (k, k))
    t = (COMP / 'exchange/Request.dc.html').read_text(encoding='utf-8')
    grid_start = t.index('<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px">\n') + len('<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px">\n')
    grid_end = t.index('</div>', grid_start)
    rounds_old = t[grid_start:grid_end]
    zone_start = t.index('<div style="display: flex; flex-wrap: wrap; gap: 8px">\n') + len('<div style="display: flex; flex-wrap: wrap; gap: 8px">\n')
    zone_end = t.index('</div>', zone_start)
    zones_old = t[zone_start:zone_end]
    rounds_tpl = ('<sc-for list="{{rounds}}" as="r"><button data-act="round" data-val="{{r.val}}" aria-pressed="{{r.pressed}}" disabled="{{r.disabled}}" style="{{r.style}}">'
                  '{{r.label}}<sc-if value="{{r.sub}}"><span style="font-size: 11px">{{r.sub}}</span></sc-if></button></sc-for>\n')
    zones_tpl = ('<sc-for list="{{zones}}" as="z"><button data-act="zone" data-val="{{z.val}}" aria-pressed="{{z.pressed}}" style="{{z.style}}">{{z.label}}</button></sc-for>\n')
    step = ('width: 28px; height: 24px; border: 1px solid #DADDE3; border-radius: 6px; background: #FFFFFF; font-family: inherit; '
            'font-size: 14px; font-weight: 700; color: #4A4F5C; padding: 0')
    stepper = ('<sc-if value="{{showStep}}"><span style="display: flex; align-items: center; gap: 6px">'
               '<button type="button" data-act="rowMinus" aria-label="열 범위 줄이기" disabled="{{cantMinus}}" style="%s">−</button>'
               '<span style="font-size: 12px; font-weight: 700; color: #3A26C4">{{stepLabel}}</span>'
               '<button type="button" data-act="rowPlus" aria-label="열 범위 늘리기" disabled="{{cantPlus}}" style="%s">+</button></span></sc-if>' % (step, step))
    note_old_p = ('<p style="margin: 0; font-size: 13px; line-height: 1.55; color: #4A4F5C">중요도를 고르지 않은 조건은 &#39;무관&#39;으로 처리하지 않아요. '
                  '필수는 맞지 않으면 후보에서 제외돼요. 양쪽 수락과 최종 확인이 끝나야 교환이 완료돼요 (서비스 설계 가정).</p>')
    cta_old = ('<a href="Waiting.dc.html" style="height: 54px; border-radius: 14px; background: #5B3DF5; color: #FFFFFF; display: flex; align-items: center; '
               'justify-content: center; font-size: 16px; font-weight: 700; text-decoration: none">교환 신청 등록</a>')
    cta_new = ('<sc-if value="{{valid}}">%s</sc-if><sc-if value="{{invalid}}"><button type="button" disabled style="width: 100%%; height: 54px; border-radius: 14px; '
               'background: #E6E8EC; color: #8B909C; border: 0; font-family: inherit; font-size: 16px; font-weight: 700">교환 신청 등록</button></sc-if>'
               % cta_old.replace('<a href="Waiting.dc.html" ', '<a href="Waiting.dc.html" data-act="submit" ', 1))
    patch('exchange/Request.dc.html', [
        (seg_old['round'], seg_tpl('round')),
        ('<span style="font-size: 13px; font-weight: 700; color: #3A26C4">1열 ~ 10열</span>' + seg_old['row'],
         '<span style="font-size: 13px; font-weight: 700; color: #3A26C4">{{rowLabel}}</span>' + seg_tpl('row')),
        (rounds_old, rounds_tpl),
        (seg_old['zone'], seg_tpl('zone')),
        (zones_old, zones_tpl),
        ('<div style="position: absolute; left: 0; width: 50%; height: 6px;', '<div style="position: absolute; left: 0; width: {{rowPct}}; height: 6px;'),
        ('<div style="position: absolute; left: calc(50% - 12px);', '<div style="position: absolute; left: calc({{rowPct}} - 12px);'),
        ('<span>1열</span><span>20열</span>', '<span>1열</span>' + stepper + '<span>20열</span>'),
        ('<div style="background: #F5F6F8; border-radius: 14px; padding: 14px 16px; display: flex; gap: 10px; align-items: flex-start">', '<div style="{{noteBox}}">'),
        (note_old_p, '<p style="{{noteText}}">{{note}}</p>'),
        (cta_old, cta_new),
    ], key='request')
    # 신청 현황
    patch('exchange/Waiting.dc.html', [
        ('>12.19 (토) 19:30, 12.21 (월) 14:00 · 필수<', '>{{roundsText}}<'),
        ('>R석 A·B구역 · 선호<', '>{{zonesText}}<'),
        ('>1열 ~ 10열 · 선호<', '>{{rowText}}<'),
        ('<a href="Request.dc.html" style=', '<a href="Request.dc.html" data-act="edit" style='),
        ('<a href="Match.dc.html" style=', '<a href="Match.dc.html" data-act="notify" style='),
        ('>교환 신청 취소</button>', '>교환 신청 취소</button>'),
    ], key='waiting')
    t = (COMP / 'exchange/Waiting.dc.html').read_text(encoding='utf-8')
    m = re.search(r'<button ([^>]*)>교환 신청 취소</button>', t)
    t = t.replace(m.group(0), '<button data-act="cancel" %s>교환 신청 취소</button>' % m.group(1))
    (COMP / 'exchange/Waiting.dc.html').write_text(t, encoding='utf-8')
    # 교환 완료
    patch('exchange/Done.dc.html', [
        ('>12.21 (월) 14:00 · 4회차<', '>{{date}}<'),
        ('>R석 · A구역 5열 8번<', '>{{seat}}<'),
        ('>T26112-0839<', '>{{booking}}<'),
        ('>12.20 (일) 18:00 · B구역 7열 12번<', '>{{prev}}<'),
        ('<a href="Main.dc.html" style=', '<a href="Main.dc.html" data-act="home" style='),
    ], key='done')


# ================================================================ 페이지 (P07 일반 교환 보드)
HOST0 = ['Main', 'Request', 'Waiting', 'MatchCheck', 'Compare', 'StatusSent', 'StatusAccepted', 'StatusFinal', 'Done',
         'ExMismatch', 'ExNoCandidate', 'ExDeclined', 'ExCancelled', 'ExFinalFailed']
NEW_COMPS = ['MatchCheck', 'Compare', 'StatusSent', 'StatusAccepted', 'StatusFinal', 'ExMismatch', 'ExNoCandidate', 'ExDeclined', 'ExCancelled', 'ExFinalFailed']

PAGE_LOGIC = r'''
var INITIAL = __INITIAL__;
var HOSTS = __HOSTS__;
var DEMO_HOST = 0;
__STORE__
class Component extends DCLogic {
constructor(props) {
super(props);
this.state = { stacks: INITIAL.map(function (s) { return [s]; }), demo: DEMO.initialState() };
}
navigate(i, e) {
var t = e && e.target;
var hostEl = t && t.closest ? t.closest('[data-nav-host]') : null;
// 체험 폰: data-act 가 붙은 버튼·링크는 상태 변경으로 처리한다 (동의 체크박스는 기본 동작 유지)
if (i === DEMO_HOST && t && t.closest) {
var actEl = t.closest('[data-act]');
if (actEl && !actEl.disabled) {
var type = actEl.getAttribute('data-act');
if (type !== 'consent') e.preventDefault();
this.dispatch(i, { type: type, val: actEl.getAttribute('data-val'), row: actEl.getAttribute('data-row'), checked: !!actEl.checked }, hostEl);
return;
}
}
var a = t && t.closest ? t.closest('a[href]') : null;
if (!a) return;
var href = a.getAttribute('href') || '';
var m = /^(?:\.\/)?([A-Za-z0-9_-]+)\.dc\.html$/.exec(href);
if (!m) return;
e.preventDefault();
var target = m[1];
var back = a.getAttribute('aria-label') === '뒤로';
var screens = HOSTS[i];
var moved = false;
this.setState(function (st) {
var stacks = st.stacks.map(function (x) { return x.slice(); });
var s = stacks[i];
if (back && s.length > 1) { s.pop(); }
else if (screens.indexOf(target) < 0) { /* 이 보드에 없는 화면: 현재 화면 유지 */ }
else if (back) { stacks[i] = [target]; }
else if (s[s.length - 1] !== target) { s.push(target); }
moved = JSON.stringify(stacks[i]) !== JSON.stringify(st.stacks[i]);
return { stacks: stacks };
}, function () {
if (moved && hostEl && hostEl.focus) { try { hostEl.focus({ preventScroll: true }); } catch (err) { /* 무시 */ } }
});
}
dispatch(i, action, hostEl) {
var moved = false;
this.setState(function (st) {
var stacks = st.stacks.map(function (x) { return x.slice(); });
var s = stacks[i];
action.screen = s[s.length - 1];
var r = DEMO.reduce(st.demo, action);
var nav = r.nav;
if (nav && nav.push && HOSTS[i].indexOf(nav.push) >= 0 && s[s.length - 1] !== nav.push) { s.push(nav.push); }
else if (nav && nav.reset) { stacks[i] = nav.reset.filter(function (x) { return HOSTS[i].indexOf(x) >= 0; }); }
else if (nav && nav.pop && s.length > 1) { s.pop(); }
moved = JSON.stringify(stacks[i]) !== JSON.stringify(st.stacks[i]);
return { stacks: stacks, demo: r.state };
}, function () {
if (moved && hostEl && hostEl.focus) { try { hostEl.focus({ preventScroll: true }); } catch (err) { /* 무시 */ } }
});
}
keydown(i, e) {
if (e && e.key === 'Escape') {
this.setState(function (st) {
var stacks = st.stacks.map(function (x) { return x.slice(); });
stacks[i] = [INITIAL[i]];
return i === DEMO_HOST ? { stacks: stacks, demo: DEMO.initialState() } : { stacks: stacks };
});
}
}
renderVals() {
var self = this;
var stacks = (this.state && this.state.stacks) || INITIAL.map(function (s) { return [s]; });
var v = { nosubmit: function (e) { if (e && e.preventDefault) e.preventDefault(); }, demo: DEMO.views(this.state.demo, true) };
INITIAL.forEach(function (_, i) {
var cur = stacks[i][stacks[i].length - 1];
HOSTS[i].forEach(function (s) { v['v_' + i + '_' + s] = s === cur ? 'block' : 'none'; });
v['nav_' + i] = function (e) { self.navigate(i, e); };
v['key_' + i] = function (e) { self.keydown(i, e); };
});
return v;
}
}
'''


def comp_src(name):
    for d in ('exchange', 'pair', 'states', 'exceptions'):
        if (COMP / d / ('%s.dc.html' % name)).exists():
            return 'components/%s/%s.dc.html' % (d, name)
    sys.exit('컴포넌트 없음: ' + name)


def patch_page():
    p = SRC / 'pages/p07-ui-exchange/page.html'
    t = p.read_text(encoding='utf-8')
    m = re.search(r'(<div data-nav-host="0"[^>]*>)((?:<form [^>]*><dc-import [^>]*></dc-import></form>)+)(</div>)', t)
    if not m:
        sys.exit('체험 폰(폰 1) 틀을 찾지 못함')
    forms = ''.join('<form data-nav-screen="%s" onsubmit="{{nosubmit}}" style="display: {{v_0_%s}}; margin: 0"><dc-import name="%s" hint-size="390px,844px" demo="{{demo}}"></dc-import></form>'
                    % (s, s, s) for s in HOST0)
    t = t[:m.start(2)] + forms + t[m.end(2):]
    hosts = json.loads(re.search(r'var HOSTS = (\[.*?\]);', t).group(1))
    initial = json.loads(re.search(r'var INITIAL = (\[.*?\]);', t).group(1))
    hosts[0] = HOST0
    store = STORE.read_text(encoding='utf-8').replace("if (typeof module !== 'undefined') module.exports = DEMO;", '')
    sc0 = t.index('<script type="text/x-dc"')
    sc1 = t.index('>', sc0) + 1
    sc2 = t.index('</script>', sc1)
    code = PAGE_LOGIC.replace('__INITIAL__', json.dumps(initial, ensure_ascii=False)).replace('__HOSTS__', json.dumps(hosts, ensure_ascii=False)).replace('__STORE__', store)
    if '</' in code:
        sys.exit('로직에 </ 가 있어 스크립트가 끊길 수 있음')
    t = t[:sc1] + code + t[sc2:]
    cap_old = '<b style="font-size: 17px; color: #FFFFFF">예매 상세</b><span style="font-size: 15px; line-height: 1.55; color: #E3DDFF">교환 가능한 공연인지 먼저 알려줘요</span>'
    if t.count(cap_old) != 1:
        sys.exit('폰 1 캡션을 찾지 못함')
    t = t.replace(cap_old, cap_old.replace('교환 가능한 공연인지 먼저 알려줘요', '교환 가능한 공연인지 먼저 알려줘요. 이 폰은 직접 눌러 체험할 수 있어요 (데모)'))
    p.write_text(t, encoding='utf-8')
    print('페이지: p07-ui-exchange (체험 폰 화면 %d개)' % len(HOST0))
    # 번들 명세: 체험 폰이 쓰는 컴포넌트를 이 페이지 리소스에 추가
    bp = SRC / 'bundle.json'
    b = json.loads(bp.read_text(encoding='utf-8'))
    pg = b['pages']['p07-ui-exchange']
    have = {a['ext_id'] for a in pg['assets']}
    react_idx = next(i for i, u in enumerate(pg['ext_resources_order']) if any(a['uuid'] == u and a['kind'] == 'vendor' for a in pg['assets']))
    for n in NEW_COMPS:
        ext = './%s.dc.html' % n
        if ext in have:
            continue
        u = str(uuidlib.uuid4())
        src = comp_src(n)
        pg['assets'].append(dict(uuid=u, mime='text/html', compressed=True, kind='component', src=src, ext_id=ext,
                                 sha256=sha256((SRC / src).read_bytes()).hexdigest()))
        pg['ext_resources_order'].insert(react_idx, u)
        react_idx += 1
    bp.write_text(json.dumps(b, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('번들 명세: p07-ui-exchange 리소스 추가')


if __name__ == '__main__':
    build_matchcheck()
    build_compare()
    build_mismatch()
    patch_status()
    patch_exchange()
    patch_page()
