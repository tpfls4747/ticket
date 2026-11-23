"""STEP 3C: 연석 만들기 인터랙션 (1회성 적용 스크립트, 실험 기능 · 수요 미검증).

- 상태·판정: tools/authoring/demo3c_pair.js (원본). STEP 3B 엔진 demo3b_store.js 와 함께 P12(연석 만들기) 페이지 로직에 넣는다.
- 컴포넌트: 체험 폰(P12 보드 1번 폰)은 페이지가 넘겨주는 demo 데이터를 그리고, 다른 폰·P13 상태 보드는
  같은 엔진으로 계산한 기본값(DEFAULT_VIEW)을 그린다.
- 체험 폰의 입력 요소(체크박스·라디오)는 상태와 묶은 controlled 입력, 다른 폰은 기존 정적 입력을 그대로 둔다
  (STEP 3A 의 '다른 화면에 다녀와도 입력 유지' 동작을 깨지 않기 위해).
- 화면 전환·데모 패널·뒤로 버튼·페이지 로직은 STEP 3B 의 apply_demo_3b.py 부품을 다시 쓴다.
사용법: python3 tools/authoring/apply_pair_3c.py   (대상 파일을 git 기준 상태에서 실행할 것)
"""
import json
import re
import subprocess
import sys
import uuid as uuidlib
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_demo_3b as B3            # noqa: E402  (STEP 3B 부품: panel, act, badge_switch, BACK_*, PAGE_LOGIC ...)
from dc_kit import *                  # noqa: E402,F401

ROOT = B3.ROOT
SRC = B3.SRC
COMP = B3.COMP
STORE = B3.STORE
PAIR = Path(__file__).resolve().parent / 'demo3c_pair.js'

PDEF = json.loads(subprocess.check_output(
    ['node', '-e', "process.stdout.write(JSON.stringify(require(%s).defaultViews()))" % json.dumps(str(PAIR))]).decode('utf-8'))

SCRIPT_RE = re.compile(r'(<script type="text/x-dc" data-dc-script[^>]*>)(.*?)(</script>)', re.S)


def mk_logic(dv, key):
    """renderVals: 체험 폰이면 페이지가 준 demo[key], 아니면 기본 화면 데이터 (STEP 3B logic() 과 같은 형식)."""
    return ('\nvar DEFAULT_VIEW = %s;\nclass Component extends DCLogic {\nrenderVals() {\nvar d = this.props.demo;\nvar v = (d && d.%s) || DEFAULT_VIEW;\n'
            'var o = {};\nfor (var k in v) o[k] = v[k];\no.isDemo = !!(d && d.isDemo);\no.notDemo = !o.isDemo;\nreturn o;\n}\n}\n'
            % (json.dumps(dv.get(key, {}), ensure_ascii=False), key))


def write_logic(t, code):
    m = SCRIPT_RE.search(t)
    if not m:
        sys.exit('로직 블록 없음')
    return t[:m.start(2)] + code + t[m.end(2):]


def patch(rel, pairs, key, back=False, dv=None, regex=()):
    p = COMP / rel
    t = p.read_text(encoding='utf-8')
    for old, new in pairs:
        if t.count(old) != 1:
            sys.exit('%s: 치환 대상 %d회 (%s)' % (rel, t.count(old), old[:80]))
        t = t.replace(old, new)
    for pat, fn in regex:
        t, n = re.subn(pat, fn, t, count=1, flags=re.S)
        if n != 1:
            sys.exit('%s: 패턴을 찾지 못함 (%s)' % (rel, pat[:60]))
    if back:
        if t.count(B3.BACK_SPAN) != 1:
            sys.exit('%s: 뒤로 표시를 찾지 못함' % rel)
        t = t.replace(B3.BACK_SPAN, '<sc-if value="{{notDemo}}">%s</sc-if><sc-if value="{{isDemo}}">%s</sc-if>' % (B3.BACK_SPAN, B3.BACK_BTN))
    t = write_logic(t, mk_logic(dv if dv is not None else PDEF, key))
    p.write_text(t, encoding='utf-8')
    print('컴포넌트:', rel)


def demo_only(static, demo):
    return '<sc-if value="{{notDemo}}">%s</sc-if><sc-if value="{{isDemo}}">%s</sc-if>' % (static, demo)


def back_link(m):
    """3A 의 '뒤로' 링크는 다른 폰에서 그대로, 체험 폰에서는 상태 기반 뒤로 버튼."""
    return demo_only(m.group(0), B3.BACK_BTN)


SIM_NOTE = '<span style="font-size: 11px; font-weight: 700; color: #4A4F5C; background: #F0F1F4; padding: 2px 6px; border-radius: 4px; white-space: nowrap">시연용 모의 데이터</span>'
EXP_TAG = '<span style="font-size: 11px; font-weight: 700; color: #A3440B; background: #FFF1E6; padding: 2px 6px; border-radius: 4px; white-space: nowrap">실험 기능 · 수요 미검증</span>'


# ================================================================ PairMode: 교환할 티켓 2장 · 교환 방식
def patch_mode():
    rel = 'pair/PairMode.dc.html'
    t = (COMP / rel).read_text(encoding='utf-8')
    labels = re.findall(r'<label .*?</label>', t, flags=re.S)
    tickets, modes = labels[:2], labels[2:]
    inp_ck = '<input type="checkbox" checked style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 0">'
    tk_demo = ('<sc-for list="{{tickets}}" as="t"><label style="{{t.style}}">'
               '<input type="checkbox" data-act="pick" data-val="{{t.val}}" checked="{{t.checked}}" style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 0">'
               '<span style="display: flex; flex-direction: column; gap: 2px"><span style="font-size: 15px; font-weight: 700">{{t.title}}</span>'
               '<span style="font-size: 12px; color: #5F6370">{{t.sub}}</span></span></label></sc-for>')
    if any(inp_ck not in x for x in tickets):
        sys.exit('PairMode: 티켓 체크박스 형식이 다름')
    t = t.replace('\n'.join(tickets), demo_only('\n'.join(tickets), tk_demo), 1) if '\n'.join(tickets) in t else sys.exit('PairMode: 티켓 묶음 없음')
    # 교환 방식 라디오
    gen, pair = modes
    gen_d = gen.replace('<label style="display: flex; align-items: flex-start; gap: 12px; border: 1px solid #DADDE3; border-radius: 16px; padding: 16px">', '<label style="{{generalStyle}}">', 1)
    gen_d = gen_d.replace('<input type="radio" name="mode" style=', '<input type="radio" name="mode" data-act="mode" data-val="general" checked="{{generalChecked}}" style=', 1)
    pair_d = pair.replace('<label style="display: flex; align-items: flex-start; gap: 12px; border: 1.5px solid #5B3DF5; background: #F7F5FF; border-radius: 16px; padding: 16px">', '<label style="{{pairStyle}}">', 1)
    pair_d = pair_d.replace('<input type="radio" name="mode" checked style=', '<input type="radio" name="mode" data-act="mode" data-val="pair" checked="{{pairChecked}}" style=', 1)
    if gen_d == gen or pair_d == pair or 'generalChecked' not in gen_d or 'pairChecked' not in pair_d:
        sys.exit('PairMode: 라디오 형식이 다름')
    both = gen + '\n' + pair
    if t.count(both) != 1:
        sys.exit('PairMode: 라디오 묶음 없음')
    t = t.replace(both, demo_only(both, gen_d + pair_d))
    hint = ('<sc-if value="{{hasHint}}"><p role="status" style="margin: 0; font-size: 13px; line-height: 1.5; font-weight: 700; color: #A3440B; '
            'background: #FFF1E6; border-radius: 12px; padding: 10px 12px">{{hint}}</p></sc-if>')
    t = t.replace('</fieldset>\n</main>', '</fieldset>\n' + hint + '\n</main>', 1) if t.count('</fieldset>\n</main>') == 1 else sys.exit('PairMode: fieldset 끝 없음')
    (COMP / rel).write_text(t, encoding='utf-8')
    patch(rel, [('<a href="PairSeat.dc.html" style=', '<a href="PairSeat.dc.html" data-act="next" style=')], key='mode',
          regex=[(r'<a href="Main\.dc\.html" aria-label="뒤로".*?</a>', back_link)])


# ================================================================ PairSeat: 배치도 · 지킬 좌석/내놓을 좌석
def patch_seat():
    rel = 'pair/PairSeat.dc.html'
    t = (COMP / rel).read_text(encoding='utf-8')
    labels = re.findall(r'<label .*?</label>', t, flags=re.S)
    both = '\n'.join(labels)
    if len(labels) != 2 or t.count(both) != 1:
        sys.exit('PairSeat: 방향 라디오 묶음 없음')
    opt = ('<sc-for list="{{options}}" as="o"><label style="{{o.style}}">'
           '<input type="radio" name="dir" data-act="dir" data-val="{{o.val}}" checked="{{o.checked}}" style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 2px 0 0">'
           '<span style="display: flex; flex-direction: column; gap: 4px"><span style="font-size: 15px; font-weight: 700">{{o.title}}</span>'
           '<span style="font-size: 13px; line-height: 1.5; color: #4A4F5C">{{o.desc}}</span>'
           '<sc-if value="{{o.tag}}"><span style="align-self: flex-start; font-size: 11px; font-weight: 700; color: #4A4F5C; background: #EEF0F3; padding: 2px 6px; border-radius: 4px; margin-top: 2px">상대 좌석 변경</span></sc-if>'
           '</span></label></sc-for>')
    t = t.replace(both, demo_only(both, opt))
    (COMP / rel).write_text(t, encoding='utf-8')
    seat_cand = ('<sc-if value="{{seat.cand}}" hint-placeholder-val="{{false}}"><span style="width: 16px; height: 16px; border-radius: 4px; background: #FFE3CC; '
                 'border: 2px solid #D9620F; box-sizing: border-box"></span></sc-if>')
    seat_offer = ('<sc-if value="{{seat.offer}}" hint-placeholder-val="{{false}}"><span style="width: 16px; height: 16px; border-radius: 4px; background: #FFFFFF; '
                  'border: 2px solid #5B3DF5; box-sizing: border-box"></span></sc-if>')
    seat_other = ('<sc-if value="{{seat.other}}" hint-placeholder-val="{{true}}"><span style="width: 16px; height: 16px; border-radius: 4px; background: #DADDE3"></span></sc-if>')
    aisle = '<sc-if value="{{seat.aisle}}" hint-placeholder-val="{{false}}"><span aria-hidden="true" style="width: 2px; height: 16px; border-left: 2px dashed #8B909C"></span></sc-if>'
    legend_old = ('<span style="display: flex; align-items: center; gap: 5px"><span style="width: 10px; height: 10px; border-radius: 3px; background: #5B3DF5"></span>내 좌석</span>\n'
                  '<span style="display: flex; align-items: center; gap: 5px"><span style="width: 10px; height: 10px; border-radius: 3px; background: #FFE3CC; border: 2px solid #D9620F; box-sizing: border-box"></span>제안 후보 옆자리</span>')
    legend_new = ('<span style="display: flex; align-items: center; gap: 5px"><span style="width: 10px; height: 10px; border-radius: 3px; background: #5B3DF5"></span>지킬 좌석</span>\n'
                  '<span style="display: flex; align-items: center; gap: 5px"><span style="width: 10px; height: 10px; border-radius: 3px; background: #FFFFFF; border: 2px solid #5B3DF5; box-sizing: border-box"></span>내놓을 좌석</span>\n'
                  '<span style="display: flex; align-items: center; gap: 5px"><span style="width: 10px; height: 10px; border-radius: 3px; background: #FFE3CC; border: 2px solid #D9620F; box-sizing: border-box"></span>옆자리</span>\n'
                  '<span style="display: flex; align-items: center; gap: 5px"><span style="width: 2px; height: 10px; border-left: 2px dashed #8B909C"></span>통로</span>')
    cta_old = ('<a href="PairReceive.dc.html" style="height: 54px; border-radius: 14px; background: #5B3DF5; color: #FFFFFF; display: flex; align-items: center; '
               'justify-content: center; font-size: 16px; font-weight: 700; text-decoration: none">동의한 옆자리에 제안 보내기</a>')
    cta_demo = cta_old.replace('<a href="PairReceive.dc.html" ', '<a href="PairAdjacency.dc.html" data-act="toCandidates" ').replace('동의한 옆자리에 제안 보내기', '옆자리 후보 확인하기')
    patch(rel, [(seat_cand, seat_cand + seat_offer), (seat_other, seat_other + aisle),
                ('<div style="display: flex; gap: 14px; font-size: 11px; color: #4A4F5C; margin-top: 8px">', '<div style="display: flex; gap: 10px; font-size: 11px; color: #4A4F5C; margin-top: 8px">'),
                (legend_old, legend_new), (cta_old, demo_only(cta_old, cta_demo))],
          key='seat', regex=[(r'<a href="PairMode\.dc\.html" aria-label="뒤로".*?</a>', back_link)])


# ================================================================ PairAdjacency: 옆자리 후보 판정 (재작성)
def build_adjacency():
    row = ('<div style="display: flex; flex-direction: column; gap: 1px; padding: 3px 0; border-top: 1px solid #EEF0F3">'
           '<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px">'
           '<span style="font-size: 12px; color: %s">{{r.label}}</span>%s</div>'
           '<sc-if value="{{r.hasDetail}}"><span style="font-size: 11px; line-height: 1.35; color: %s">{{r.detail}}</span></sc-if></div>'
           % (SUB2, B3.badge_switch('r', 11), SUB))
    hidden = ('<sc-if value="{{c.hidden}}"><section style="border: 1px dashed #DADDE3; background: %s; border-radius: 14px; padding: 9px 14px; display: flex; flex-direction: column; gap: 3px">'
              '<div style="display: flex; justify-content: space-between; align-items: center; gap: 8px"><b style="font-size: 13px; color: %s">{{c.title}}</b>%s</div>'
              '<span style="font-size: 11px; line-height: 1.45; color: %s">{{c.note}}</span></section></sc-if>'
              % (BG, SUB2, badge('mute', '후보 아님', 11), SUB))
    shown = ('<sc-if value="{{c.shown}}"><section style="{{c.border}}; border-radius: 14px; padding: 9px 14px; display: flex; flex-direction: column; gap: 3px">'
             '<div style="display: flex; justify-content: space-between; align-items: center; gap: 8px"><b style="font-size: 13px">{{c.title}}</b>%s</div>'
             '<sc-for list="{{c.rows}}" as="r">%s</sc-for>'
             '<button type="button" data-act="choose" data-val="{{c.key}}" aria-pressed="{{c.pressed}}" disabled="{{c.cantPick}}" style="{{c.pickStyle}}; margin-top: 2px">{{c.pickText}}</button>'
             '</section></sc-if>' % (B3.badge_switch('c', 11), row))
    profiles = ('<sc-if value="{{showProfiles}}"><div style="border: 1.5px dashed #C9BFFF; background: #F7F5FF; border-radius: 14px; padding: 9px 12px; display: flex; flex-direction: column; gap: 7px">'
                '<span style="display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 700; color: #3A26C4">%s데모 모드 · 11열 5번 관객의 상황 바꾸기</span>'
                '<div style="display: flex; flex-wrap: wrap; gap: 6px"><sc-for list="{{profiles}}" as="p">'
                '<button type="button" data-act="profile" data-val="{{p.val}}" aria-pressed="{{p.pressed}}" style="{{p.style}}">{{p.label}}</button></sc-for></div></div></sc-if>'
                % icon('info', PRIMARY_DARK, 14, 2.2))
    main = ''.join([
        banner('번호가 이어져도 붙어 있다고 판단하지 않고 배치도로 통로·단절을 확인해요. 수신 동의한 관객만 후보예요 (시연).', 'plan'),
        '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px">'
        '<div style="border: 1.5px solid #5B3DF5; background: #F7F5FF; border-radius: 14px; padding: 6px 12px; display: flex; flex-direction: column; gap: 1px">'
        '<span style="font-size: 11px; font-weight: 700; color: #3A26C4">지킬 좌석</span><span style="font-size: 14px; font-weight: 700">{{keepName}}</span></div>'
        '<div style="border: 1px solid #E6E8EC; border-radius: 14px; padding: 6px 12px; display: flex; flex-direction: column; gap: 1px">'
        '<span style="font-size: 11px; font-weight: 700; color: #5F6370">내놓을 좌석</span><span style="font-size: 14px; font-weight: 700">{{offerName}}</span></div></div>',
        '<sc-for list="{{cards}}" as="c">%s%s</sc-for>' % (hidden, shown),
        profiles,
    ])
    footer = ('<sc-if value="{{canNext}}">%s</sc-if><sc-if value="{{cantNext}}">%s</sc-if>'
              '<sc-if value="{{nextHint}}"><p role="status" style="margin: 0; font-size: 12px; line-height: 1.5; font-weight: 700; color: %s">{{nextHint}}</p></sc-if>'
              % (B3.act(cta('선택한 후보로 제안 준비하기'), 'toWarn'), cta('선택한 후보로 제안 준비하기', disabled=True), WARN_FG))
    html = screen('연석 후보 확인', '연석 후보 확인', main, footer=footer, gap=6)
    (COMP / 'pair/PairAdjacency.dc.html').write_text(html, encoding='utf-8')
    patch('pair/PairAdjacency.dc.html', [], key='adj', back=True)


# ================================================================ PairWarn: 보내기 전 확인 (재작성)
def build_warn():
    row = ('<div style="display: flex; flex-direction: column; gap: 1px; padding: 4px 0; border-top: 1px solid #EEF0F3">'
           '<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px">'
           '<span style="font-size: 12px; font-weight: 700">{{r.label}}</span>%s</div>'
           '<sc-if value="{{r.hasDetail}}"><span style="font-size: 11px; line-height: 1.4; color: %s">{{r.detail}}</span></sc-if></div>'
           % (B3.badge_switch('r', 11), SUB))
    bullets = ['제안이 거절되거나 취소되면 지금처럼 떨어진 좌석이 유지돼요',
               '상대가 수락해도 최종 확인에 실패하면 교환되지 않아요',
               '상대는 언제든 거절할 수 있어요 (수신자의 권한)']
    li = ''.join('<li style="display: flex; gap: 8px; align-items: flex-start; font-size: 12px; line-height: 1.5; color: %s">%s<span>%s</span></li>'
                 % (SUB2, icon('dot', WARN, 12, 3), b) for b in bullets)
    main = ''.join([
        '<div style="display: flex; gap: 6px; flex-wrap: wrap">%s%s</div>' % (EXP_TAG, SIM_NOTE),
        '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px">%s%s</div>' % (
            ticket_row('내 좌석 (지금)', '{{now}}'), ticket_row('교환이 완료되면', '{{after}}', accent=True)),
        B3.box('<b style="font-size: 12px">{{candTitle}}</b>' + B3.para('{{candMove}}', 12, SUB2), pad='10px 14px', gap=3),
        B3.box('<b style="font-size: 12px">양방향 확인</b><sc-for list="{{twoWay}}" as="r">%s</sc-for>' % row
               + '<span style="font-size: 11px; line-height: 1.45; color: %s; padding-top: 4px">{{twoWayNote}}</span>' % SUB2,
               bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='9px 14px', gap=0),
        B3.box('<b style="font-size: 13px">{{warnTitle}}</b>'
               '<sc-if value="{{hasCompanion}}"><p style="margin: 0; font-size: 12px; line-height: 1.5; color: %s; font-weight: 700">{{companionText}}</p></sc-if>'
               '<ul style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 5px">%s</ul>' % (WARN_FG, li),
               bg=WARN_BG, pad='10px 14px', gap=6),
        demo_only('<label style="display: flex; align-items: flex-start; gap: 10px; font-size: 13px; line-height: 1.5; color: %s">'
                  '<input type="checkbox" style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 0; flex-shrink: 0">위 내용을 확인했어요</label>' % TEXT,
                  '<label style="display: flex; align-items: flex-start; gap: 10px; font-size: 13px; line-height: 1.5; color: %s">'
                  '<input type="checkbox" data-act="ack" checked="{{ack}}" style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 0; flex-shrink: 0">위 내용을 확인했어요</label>' % TEXT),
    ])
    footer = ('<sc-if value="{{canSend}}">%s</sc-if><sc-if value="{{cantSend}}">%s</sc-if>'
              '<sc-if value="{{sendHint}}"><p role="status" style="margin: 0; font-size: 12px; line-height: 1.5; font-weight: 700; color: %s">{{sendHint}}</p></sc-if>'
              % (B3.act(cta('{{sendText}}'), 'send'), cta('{{sendText}}', disabled=True), WARN_FG))
    html = screen('제안 보내기 전 확인', '제안 보내기 전 확인', main, footer=footer, gap=8)
    (COMP / 'pair/PairWarn.dc.html').write_text(html, encoding='utf-8')
    patch('pair/PairWarn.dc.html', [], key='warn', back=True)


# ================================================================ 진행·결과 화면 (기존 마크업에 데이터·data-act 만 연결)
def patch_results():
    patch('pair/PairAccepted.dc.html', [
        ('>7열 12번 · 11열 4번<', '>{{now}}<'),
        ('>11열 4번 · 11열 5번<', '>{{after}}<'),
        ('내 수락(동의) 완료', '내가 제안을 보냈어요 (내 수락)'),
        ('<p style="margin: 0; font-size: 12px; line-height: 1.5; font-weight: 400; color: #5F6370">실패하면 원래 좌석이',
         B3.panel('다음 단계 진행', [('최종 확인 시작', 'toFinal', 'primary')]) + B3.act(cta('교환 취소하기 (최종 확인 전)', 'ghost'), 'cancel')
         + '<p style="margin: 0; font-size: 12px; line-height: 1.5; font-weight: 400; color: #5F6370">실패하면 원래 좌석이'),
    ], key='after', back=True)
    patch('pair/PairDeclined.dc.html', [
        ('>7열 12번 · 11열 4번 (변경 없음)<', '>{{now}} (변경 없음)<'),
        ('>옆자리 후보 1<', '>{{candLabel}}<'),
        ('>11열 5번<', '>{{cand}}<'),
        (cta('다른 후보 확인하기'), B3.act(cta('다른 후보 확인하기'), 'otherCandidate')),
        (cta('반대 방향으로 모으기 보기', 'ghost'), B3.act(cta('반대 방향으로 모으기 보기', 'ghost'), 'otherDir')),
    ], key='after', back=True)
    patch('pair/PairDone.dc.html', [
        ('>11열 5번 관객의 수락과', '>{{cand}} 관객의 수락과'),
        ('>12.20 (일) 18:00 · 3회차<', '>{{date}}<'),
        ('>R석 · B구역 11열 4번, 5번<', '>{{seats}}<'),
        ('>B구역 7열 12번<', '>{{gave}}<'),
        ('<a href="Main.dc.html" style=', '<a href="Main.dc.html" data-act="home" style='),
    ], key='done')
    # 최종 확인 실패: 일반 교환(P07)과 함께 쓰는 화면. 유지되는 티켓 문구만 데이터로 (기본값은 STEP 3B 엔진의 값)
    patch('exceptions/ExFinalFailed.dc.html', [
        ('>12.20 (일) 18:00 · 3회차 · R석 B구역 7열 12번<', '>{{mine}}<'),
        ('유지 (목표)</span>', '{{keepText}}</span>'),
    ], key='failed', dv=B3.DEFAULTS)


# ================================================================ 페이지 (P12 연석 만들기 보드)
HOST0 = ['PairMode', 'PairSeat', 'PairAdjacency', 'PairWarn', 'StatusSent', 'PairAccepted', 'StatusFinal', 'PairDone',
         'PairDeclined', 'ExCancelled', 'ExFinalFailed']
NEW_COMPS = ['PairAdjacency', 'PairWarn', 'StatusSent', 'PairAccepted', 'StatusFinal', 'PairDeclined', 'ExCancelled', 'ExFinalFailed']


def page_logic(initial, hosts):
    code = B3.PAGE_LOGIC
    reps = [
        ("demo: DEMO.initialState() };", "demo: ENGINE.initialState() };"),
        # 체험 폰의 체크박스·라디오는 브라우저 기본 동작을 막지 않는다 (상태와 묶인 controlled 입력)
        ("if (type !== 'consent') e.preventDefault();", "if (actEl.tagName !== 'INPUT') e.preventDefault();"),
        ("var r = DEMO.reduce(st.demo, action);", "var r = ENGINE.reduce(st.demo, action);"),
        ("{ stacks: stacks, demo: DEMO.initialState() }", "{ stacks: stacks, demo: ENGINE.reset(st.demo) }"),
        ("demo: DEMO.views(this.state.demo, true)", "demo: ENGINE.views(this.state.demo, true)"),
    ]
    for a, b in reps:
        if code.count(a) != 1:
            sys.exit('PAGE_LOGIC 치환 실패: ' + a)
        code = code.replace(a, b)
    store = STORE.read_text(encoding='utf-8').replace("if (typeof module !== 'undefined') module.exports = DEMO;", '')
    pair = PAIR.read_text(encoding='utf-8').replace("if (typeof module !== 'undefined') module.exports = PAIR;", '')
    code = (code.replace('__INITIAL__', json.dumps(initial, ensure_ascii=False)).replace('__HOSTS__', json.dumps(hosts, ensure_ascii=False))
            .replace('__STORE__', store + '\n' + pair + '\nvar ENGINE = PAIR;'))
    if '</' in code:
        sys.exit('로직에 </ 가 있어 스크립트가 끊길 수 있음')
    return code


def patch_page():
    p = SRC / 'pages/p08-ui-pair/page.html'
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
    sc0 = t.index('<script type="text/x-dc"')
    sc1 = t.index('>', sc0) + 1
    sc2 = t.index('</script>', sc1)
    t = t[:sc1] + page_logic(initial, hosts) + t[sc2:]
    cap_old = '<span style="font-size: 15px; line-height: 1.55; color: #E3DDFF">떨어진 2장을 고르면 연석 만들기(실험 기능)를 안내해요</span>'
    if t.count(cap_old) != 1:
        sys.exit('폰 1 캡션을 찾지 못함')
    t = t.replace(cap_old, cap_old.replace('안내해요</span>', '안내해요. 이 폰은 직접 눌러 체험할 수 있어요 (데모)</span>'))
    p.write_text(t, encoding='utf-8')
    print('페이지: p08-ui-pair (체험 폰 화면 %d개)' % len(HOST0))
    bp = SRC / 'bundle.json'
    b = json.loads(bp.read_text(encoding='utf-8'))
    pg = b['pages']['p08-ui-pair']
    have = {a['ext_id'] for a in pg['assets']}
    react_idx = next(i for i, u in enumerate(pg['ext_resources_order']) if any(a['uuid'] == u and a['kind'] == 'vendor' for a in pg['assets']))
    for n in NEW_COMPS:
        ext = './%s.dc.html' % n
        if ext in have:
            continue
        u = str(uuidlib.uuid4())
        src = B3.comp_src(n)
        pg['assets'].append(dict(uuid=u, mime='text/html', compressed=True, kind='component', src=src, ext_id=ext,
                                 sha256=sha256((SRC / src).read_bytes()).hexdigest()))
        pg['ext_resources_order'].insert(react_idx, u)
        react_idx += 1
    bp.write_text(json.dumps(b, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('번들 명세: p08-ui-pair 리소스 추가')


if __name__ == '__main__':
    patch_mode()
    patch_seat()
    build_adjacency()
    build_warn()
    patch_results()
    patch_page()
