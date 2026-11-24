"""STEP 4B: UX/UI 시각 다듬기 (1회성 적용 스크립트, STEP 4A 커밋 상태에서 실행).

- 화면 확대 보기: 보드의 폰(0.58배)을 같은 DOM 그대로 1배로 띄운다 (상태·입력 유지). 닫기·Esc·포커스 복귀·Tab 순환
- 신청자 A / 수신자 B: P12 에서 두 체험 폰을 나란히 두고 '제안 ⇄ 응답' 연결, 역할·보유 좌석 표시
- 시연 제어판 통일: P08·P12 같은 구조·위치(보드 오른쪽 위). 정적 보드는 같은 자리에 '설명용 화면' 표시
- 수신자 상태별 화면: 제안 도착·검토 중·수락함·거절함·최종 확인 중·교환 완료·교환 실패(+신청자 취소)
- 정보 위계: 공연·회차 → 교환 전후 좌석 → 필수 충족 → 선호 차이 → 상태 → 부가 정보(접힘)
- 공용 단계 표시: 일반 교환·연석 교환·수신자 화면이 같은 컴포넌트 (실패·중단 표현, aria-current, 단계별 스크린 리더 문구)
- P13 설명용 화면의 입력 요소를 정적 표현으로 바꿔 실제 입력으로 오해하지 않게 한다
사용법: python3 tools/authoring/apply_ux_4b.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_demo_3b as B3            # noqa: E402
import apply_pair_3c as C3            # noqa: E402
import apply_ux_4a as U4              # noqa: E402
from dc_kit import *                  # noqa: E402,F401

SRC, COMP = B3.SRC, B3.COMP
PDEF, DEF3 = C3.PDEF, B3.DEFAULTS
SR = U4.SR_ONLY
read, write, sub1 = U4.read, U4.write, U4.sub1


def logic_to(rel, key, dv):
    t = read(rel)
    write(rel, C3.write_logic(t, C3.mk_logic(dv, key)))


# ================================================================ 공용 단계 표시 (컴포넌트)
def stepper_tpl(var='stepper'):
    li = ('<sc-for list="{{%s.items}}" as="st"><li aria-current="{{st.cur}}" style="flex: 1; display: flex; flex-direction: column; position: relative">'
          '<span aria-hidden="true" style="{{st.bar}}"></span><span style="%s">{{st.sr}}</span></li></sc-for>' % (var, SR))
    return ('<div role="group" aria-label="{{%(v)s.label}}" style="display: flex; flex-direction: column; gap: 7px; flex-shrink: 0">'
            '<div style="display: flex; align-items: center; gap: 8px; min-height: 20px"><span style="{{%(v)s.headStyle}}">{{%(v)s.head}}</span>'
            '<sc-if value="{{%(v)s.exp}}"><span style="font-size: 11px; font-weight: 700; color: #A3440B; background: #FFF1E6; padding: 2px 6px; border-radius: 4px">실험 기능</span></sc-if>'
            '<span style="flex: 1"></span><sc-if value="{{%(v)s.hasNote}}"><span style="{{%(v)s.noteStyle}}">{{%(v)s.note}}</span></sc-if></div>'
            '<ol style="margin: 0; padding: 0 2px; list-style: none; display: flex; gap: 5px">%(li)s</ol>'
            '<sc-if value="{{%(v)s.hasEnd}}"><span style="{{%(v)s.noteStyle}}">{{%(v)s.endNote}}</span></sc-if></div>' % {'v': var, 'li': li})


def add_stepper(rel, var='stepper', remove=None):
    t = read(rel)
    if remove:
        t = sub1(t, remove, '', rel)
    t = U4.insert_after_main(t, stepper_tpl(var), rel)
    write(rel, t)
    print('단계 표시:', rel)


# ================================================================ 비교 위계 공용 조각
def hero_tpl(var='hero', a='지금', b='교환 후'):
    return ('<div style="background: #F7F5FF; border: 1.5px solid #C9BFFF; border-radius: 14px; padding: 10px 14px; display: flex; flex-direction: column; gap: 3px">'
            '<span style="font-size: 12px; color: #4A4F5C">{{%(v)s.show}} · {{%(v)s.date}}</span>'
            '<div style="display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap"><span style="font-size: 11px; font-weight: 700; color: #5F6370">%(a)s</span>'
            '<b style="font-size: 17px">{{%(v)s.from}}</b><span aria-hidden="true" style="font-size: 16px; color: #5B3DF5; font-weight: 700">→</span>'
            '<span style="font-size: 11px; font-weight: 700; color: #3A26C4">%(b)s</span><b style="font-size: 17px; color: #3A26C4">{{%(v)s.to}}</b></div>%(extra)s</div>'
            % {'v': var, 'a': a, 'b': b, 'extra': '<sc-if value="{{%s.result}}"><span style="font-size: 13px; font-weight: 700; color: #1F7A4D">{{%s.result}}</span></sc-if>' % (var, var)})


def details(summary, inner):
    return ('<details style="border: 1px solid #E6E8EC; border-radius: 12px; padding: 6px 12px; background: #FFFFFF">'
            '<summary style="cursor: pointer; font-size: 12px; font-weight: 700; color: #4A4F5C; padding: 4px 0">%s</summary>%s</details>' % (summary, inner))


# ================================================================ 일반 교환 화면
def build_matchcheck():
    rows = '<sc-for list="{{prefRows}}" as="r">%s</sc-for>' % B3.row_c('r')
    main = ''.join([
        stepper_tpl(),
        hero_tpl('hero', '내 티켓', '후보'),
        '<div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap"><sc-if value="{{reqOk}}">%s</sc-if><sc-if value="{{reqNo}}">%s</sc-if>'
        '<span style="font-size: 12px; color: #4A4F5C">회차·구역·열 중 필수로 고른 조건</span></div>' % (badge('ok', '{{reqText}}', 12), badge('no', '{{reqText}}', 12)),
        B3.box('<b style="font-size: 12px">선호 조건 차이 (후보로 남아요)</b><sc-if value="{{hasPref}}">%s</sc-if>'
               '<sc-if value="{{noPref}}"><span style="font-size: 12px; color: #1F7A4D; font-weight: 700; padding-top: 4px">선호 조건도 모두 맞아요</span></sc-if>' % rows,
               bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='9px 12px', gap=0),
        B3.box('<div style="display: flex; gap: 6px; flex-wrap: wrap"><sc-for list="{{badges}}" as="b">%s</sc-for></div>' % B3.badge_switch('b', 11)
               + B3.para('{{summary}}', 12, SUB2), bg=SOFT, pad='9px 12px', gap=6),
        details('조건 전체 보기 (양방향 · 티켓 정보)',
                '<span style="display: block; font-size: 12px; line-height: 1.45; padding: 4px 0"><b style="color: #5F6370">내 티켓(A)</b> {{mine}}</span>'
                '<span style="display: block; font-size: 12px; line-height: 1.45; padding-bottom: 4px"><b style="color: #3A26C4">후보 티켓(B)</b> {{cand}}</span>'
                '<b style="display: block; font-size: 12px; padding-top: 4px">① 내가 원하는 조건 ↔ 후보의 티켓</b><sc-for list="{{dirA}}" as="r">%s</sc-for>'
                '<b style="display: block; font-size: 12px; padding-top: 6px">② 후보가 원하는 조건 ↔ 내 티켓</b><sc-for list="{{dirB}}" as="r">%s</sc-for>' % (B3.row_c('r'), B3.row_c('r'))),
    ])
    html = screen('양방향 조건 확인', '양방향 조건 확인', main, footer=B3.act(cta('전후 정보 비교하기'), 'toCompare'), gap=8)
    write('states/MatchCheck.dc.html', html)
    B3.patch('states/MatchCheck.dc.html', [], key='match', back=True)


def build_compare():
    # 결과 배지는 항목 이름 아래에 둔다 (줄 높이 절약). DOM 순서는 항목·지금·받을 티켓·결과 그대로라 읽는 순서는 같다
    row = ('<div style="display: grid; grid-template-columns: 62px 1fr 1fr; grid-template-rows: auto auto; column-gap: 8px; row-gap: 3px; padding: 6px 0; '
           'border-top: 1px solid #EEF0F3; align-items: start">'
           '<span style="grid-column: 1; grid-row: 1; font-size: 12px; font-weight: 700; color: %s">{{r.label}}</span>'
           '<span style="grid-column: 2; grid-row: 1 / span 2; font-size: 12px; line-height: 1.4">{{r.a}}</span>'
           '<span style="grid-column: 3; grid-row: 1 / span 2; font-size: 12px; line-height: 1.4; font-weight: 700">{{r.b}}</span>'
           '<span style="grid-column: 1; grid-row: 2; align-self: start">%s</span></div>'
           % (SUB, B3.badge_switch('r', 11)))
    head = ('<div style="display: grid; grid-template-columns: 62px 1fr 1fr; gap: 8px; padding-bottom: 6px">'
            '<span></span><span style="font-size: 11px; font-weight: 700; color: %s">내 티켓 (지금)</span><span style="font-size: 11px; font-weight: 700; color: %s">받게 될 티켓</span></div>' % (SUB, PRIMARY_DARK))
    main = ''.join([
        stepper_tpl(),
        hero_tpl('hero', '지금', '받을 티켓'),
        '<div style="display: flex; flex-direction: column"><b style="font-size: 13px; padding-bottom: 6px">달라지는 항목 · 확인할 항목</b>' + head
        + '<sc-for list="{{diffRows}}" as="r">%s</sc-for></div>' % row,
        details('{{sameTitle}}', head + '<sc-for list="{{sameRows}}" as="r">%s</sc-for>' % row
                + '<span style="display: block; font-size: 12px; line-height: 1.45; color: #5F6370; padding: 6px 0 2px">정보가 없으면 추정하지 않고 &#39;확인 필요&#39;로 표시해요. 시연용 모의 데이터예요.</span>'),
        ('<label style="display: flex; align-items: flex-start; gap: 10px; font-size: 14px; line-height: 1.5; color: %s">'
         '<input type="checkbox" data-act="consent" key="{{consentKey}}" style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 0; flex-shrink: 0">이 조건으로 교환하는 데 동의해요 (내 수락)</label>' % TEXT),
    ])
    footer = ('<sc-if value="{{sendHint}}"><p role="status" style="margin: 0; font-size: 12px; line-height: 1.5; font-weight: 700; color: %s">{{sendHint}}</p></sc-if>'
              '<sc-if value="{{canSend}}">%s</sc-if><sc-if value="{{cantSend}}">%s</sc-if>' % (WARN_FG, B3.act(cta('교환 제안 보내기'), 'send'), cta('교환 제안 보내기', disabled=True))
              + B3.para('제안을 보내도 교환은 확정되지 않아요. 상대방이 수락하고 최종 확인을 통과해야 완료돼요.', 12, SUB))
    write('states/Compare.dc.html', screen('교환 전후 비교', '교환 전후 비교', main, footer=footer, gap=9))
    B3.patch('states/Compare.dc.html', [], key='compare', back=True)


def general_steppers():
    # 신청 현황(Waiting)은 원래 세로 진행 목록이 있어 단계 표시를 겹쳐 넣지 않는다
    for rel, key in [('exchange/Request.dc.html', 'request'), ('exceptions/ExMismatch.dc.html', 'mismatch'),
                     ('exceptions/ExNoCandidate.dc.html', 'none'), ('exceptions/ExDeclined.dc.html', 'declined'),
                     ('exceptions/ExFinalFailed.dc.html', 'failed'), ('exceptions/ExCancelled.dc.html', 'cancelled')]:
        add_stepper(rel)
        logic_to(rel, key, DEF3)   # 기본 화면 데이터(단계 표시 포함)도 현재 엔진 값으로


# ================================================================ 연석 신청자 화면
def pair_screens():
    add_stepper('pair/PairMode.dc.html', remove=U4.step_bar(1, '교환 방식'))
    logic_to('pair/PairMode.dc.html', 'mode', PDEF)
    add_stepper('pair/PairSeat.dc.html', remove=U4.step_bar(2, '유지할 좌석'))
    logic_to('pair/PairSeat.dc.html', 'seat', PDEF)
    add_stepper('pair/PairDeclined.dc.html', var='stepperDeclined')
    logic_to('pair/PairDeclined.dc.html', 'after', PDEF)


def build_adjacency():
    card = ('<section style="{{c.border}}; border-radius: 14px; padding: 12px 14px; display: flex; flex-direction: column; gap: 6px">'
            '<div style="display: flex; justify-content: space-between; align-items: center; gap: 8px"><b style="font-size: 15px">{{c.title}}</b>%s</div>'
            '<sc-if value="{{c.hasResult}}"><div style="display: flex; flex-direction: column; gap: 1px"><b style="font-size: 16px; color: #1F7A4D">{{c.result}}</b>'
            '<span style="font-size: 12px; color: #4A4F5C">{{c.resultSub}}</span></div>'
            '<div style="display: flex; flex-wrap: wrap; gap: 4px"><sc-for list="{{c.checks}}" as="k"><span style="font-size: 11px; font-weight: 700; color: #1F7A4D; '
            'background: #E6F6EE; padding: 3px 7px; border-radius: 6px">{{k}}</span></sc-for></div></sc-if>'
            '<sc-if value="{{c.hasNote}}"><span style="font-size: 12px; line-height: 1.45; color: #4A4F5C">{{c.note}}</span></sc-if>'
            '<button type="button" data-act="choose" data-val="{{c.key}}" aria-pressed="{{c.pressed}}" disabled="{{c.cantPick}}" style="{{c.pickStyle}}; margin-top: 4px">{{c.pickText}}</button>'
            '</section>' % U4.badge_kind('c', 12))
    empty = ('<sc-if value="{{noCandidate}}"><section role="status" style="border: 1.5px dashed #C9CDD5; background: #F5F6F8; border-radius: 14px; padding: 14px; display: flex; flex-direction: column; gap: 6px">'
             '<b style="font-size: 15px">{{emptyTitle}}</b><span style="font-size: 13px; line-height: 1.5; color: #4A4F5C">{{emptyText}}</span>'
             '<sc-if value="{{canFlip}}"><button type="button" data-act="flipDir" style="margin-top: 4px; height: 40px; border-radius: 12px; font-family: inherit; font-size: 14px; '
             'font-weight: 700; background: #FFFFFF; color: #3A26C4; border: 1.5px solid #5B3DF5">{{flipText}}</button></sc-if></section></sc-if>')
    facts = ('<sc-if value="{{hasFacts}}">%s</sc-if>' % details('배치도에서 제외한 좌석 (좌석 정보)',
             '<span style="display: block; font-size: 12px; line-height: 1.45; color: #5F6370; padding: 2px 0 4px">번호가 이어져도 통로가 있거나 배치도 정보가 없으면 옆자리로 보지 않아요.</span>'
             '<sc-for list="{{facts}}" as="r">%s</sc-for>' % U4.row_tpl('r', 'font-size: 12px; font-weight: 700')))
    main = ''.join([
        stepper_tpl(),
        '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px">'
        '<div style="border: 1.5px solid #5B3DF5; background: #F7F5FF; border-radius: 14px; padding: 8px 12px; display: flex; flex-direction: column; gap: 1px">'
        '<span style="font-size: 12px; font-weight: 700; color: #3A26C4">유지할 좌석</span><span style="font-size: 15px; font-weight: 700">{{keepName}}</span></div>'
        '<div style="border: 1px solid #DADDE3; border-radius: 14px; padding: 8px 12px; display: flex; flex-direction: column; gap: 1px">'
        '<span style="font-size: 12px; font-weight: 700; color: #5F6370">교환에 제공할 좌석</span><span style="font-size: 15px; font-weight: 700">{{offerName}}</span></div></div>',
        '<sc-if value="{{hasNotice}}"><p %s>{{notice}}</p></sc-if>' % U4.STATUS_P,
        '<sc-for list="{{cards}}" as="c">%s</sc-for>' % card,
        empty, facts,
        B3.para("후보는 '교환 제안 받기'를 켠 관객 중 조건이 맞는 좌석만 보여줘요. 다른 관객의 설정·사유는 표시하지 않아요.", 12, SUB),
    ])
    footer = ('<sc-if value="{{nextHint}}"><p %s>{{nextHint}}</p></sc-if>' % U4.STATUS_P
              + '<sc-if value="{{canNext}}">%s</sc-if><sc-if value="{{cantNext}}">%s</sc-if>'
              % (B3.act(cta('선택한 후보와 최종 비교하기'), 'toWarn'), cta('선택한 후보와 최종 비교하기', disabled=True)))
    write('pair/PairAdjacency.dc.html', screen('연석 후보 확인', '연석 후보 확인', main, footer=footer, gap=8))
    C3.patch('pair/PairAdjacency.dc.html', [], key='adj', back=True)


STATIC_CHECK = ('<div style="display: flex; align-items: flex-start; gap: 10px; font-size: 14px; line-height: 1.5; color: #4A4F5C">'
                '<span role="img" aria-label="체크박스 그림 (설명용, 누를 수 없음)" style="width: 20px; height: 20px; border: 2px solid #9AA0AC; border-radius: 5px; '
                'box-sizing: border-box; flex-shrink: 0; background: #F5F6F8"></span><span>위 내용을 확인했어요 <span style="font-size: 11px; font-weight: 700; color: #4A4F5C; '
                'background: #F0F1F4; padding: 2px 6px; border-radius: 4px">설명용 화면 · 체험은 07 보드</span></span></div>')


def build_warn():
    li = ''.join('<li style="display: flex; gap: 8px; align-items: flex-start; font-size: 12px; line-height: 1.5; color: %s">%s<span>%s</span></li>'
                 % (SUB2, icon('dot', WARN, 12, 3), b) for b in [
                     '거절·취소되면 지금 좌석이 그대로 유지돼요',
                     '제안이 수락돼도 최종 확인에 실패하면 교환되지 않아요',
                     '상대는 일행과 함께 예매했거나 다른 이유로 거절할 수 있어요'])
    main = ''.join([
        stepper_tpl(),
        hero_tpl('hero', '제공', '받음'),
        B3.box('<div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 4px"><b style="font-size: 12px">바뀌는 항목</b>%s</div>' % U4.SIM_NOTE
               + '<sc-for list="{{diffRows}}" as="r">%s</sc-for>' % U4.cmp_tpl('r'), bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='8px 14px', gap=0),
        details('{{sameTitle}}', '<sc-for list="{{sameRows}}" as="r">%s</sc-for>' % U4.cmp_tpl('r')),
        B3.box('<b style="font-size: 12px">양방향 확인</b><sc-for list="{{twoWay}}" as="r">%s</sc-for>' % U4.row_tpl('r', 'font-size: 12px; font-weight: 700')
               + '<span style="font-size: 12px; line-height: 1.45; color: #4A4F5C; padding-top: 4px">{{twoWayNote}}</span>',
               bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='8px 14px', gap=0),
        B3.box('<b style="font-size: 13px">보내기 전에 확인해 주세요</b><ul style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 3px">%s</ul>' % li,
               bg=WARN_BG, pad='9px 14px', gap=5),
        U4.demo_only(STATIC_CHECK,
                     '<label style="display: flex; align-items: flex-start; gap: 10px; font-size: 14px; line-height: 1.5; color: %s">'
                     '<input type="checkbox" data-act="ack" checked="{{ack}}" style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 0; flex-shrink: 0">위 내용을 확인했어요</label>' % TEXT),
    ])
    footer = ('<sc-if value="{{sendHint}}"><p %s>{{sendHint}}</p></sc-if>' % U4.STATUS_P
              + '<sc-if value="{{canSend}}">%s</sc-if><sc-if value="{{cantSend}}">%s</sc-if>'
              % (B3.act(cta('{{sendText}}'), 'send'), cta('{{sendText}}', disabled=True)))
    write('pair/PairWarn.dc.html', screen('보내기 전 최종 비교', '보내기 전 최종 비교', main, footer=footer, gap=7))
    C3.patch('pair/PairWarn.dc.html', [], key='warn', back=True)


# ================================================================ 수신자 화면
B_TAG = U4.B_TAG
KINDS7 = {'plan': 'plan', 'ok': 'ok', 'wait': 'wait', 'done': 'done', 'fail': 'fail', 'mute': 'mute', 'cancel': 'cancel'}


def status_badge():
    return ''.join('<sc-if value="{{b_%s}}">%s</sc-if>' % (k, badge(v, '{{statusBadge}}', 12)) for k, v in KINDS7.items())


def build_receive():
    old = read('pair/PairReceive.dc.html')
    close = re.search(r'<button aria-label="닫기".*?</button>', old, flags=re.S).group(0)
    band = ('<div role="status" style="{{bandStyle}}"><div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">%s'
            '<b style="font-size: 17px; line-height: 1.35">{{title}}</b></div><span style="font-size: 13px; line-height: 1.5; color: #4A4F5C">{{sub}}</span></div>' % status_badge())
    proposal = ''.join([
        band,
        hero_tpl('hero', '지금 내 좌석', '바뀔 좌석'),
        B3.box('<b style="font-size: 12px; padding-bottom: 2px">바뀌는 점</b><sc-for list="{{diffRows}}" as="r">%s</sc-for>' % U4.cmp_tpl('r', '72px 1fr auto'),
               bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='8px 14px', gap=0),
        details('{{sameTitle}}', '<sc-for list="{{sameRows}}" as="r">%s</sc-for>' % U4.cmp_tpl('r', '72px 1fr auto')),
        '<sc-if value="{{hasCompanion}}">%s</sc-if>' % B3.box(
            '<b style="font-size: 13px">동행 좌석이 분리될 수 있어요</b><p style="margin: 0; font-size: 12px; line-height: 1.5; color: #A3440B; font-weight: 700">{{companionText}}</p>'
            '<span style="font-size: 11px; color: #4A4F5C">{{companionPolicy}}</span>', bg=WARN_BG, pad='10px 14px', gap=4),
        B3.para("'교환 제안 받기'를 켠 경우에만 받는 제안이에요. 교환은 예매처 안에서 처리된다고 가정했어요 (서비스 설계 가정). 응답 기한은 가상 규칙이에요.", 12, SUB),
    ])
    empty = ('<div role="status" style="border: 1.5px dashed #C9CDD5; background: #F5F6F8; border-radius: 14px; padding: 16px; display: flex; flex-direction: column; gap: 6px">'
             '<b style="font-size: 15px">도착한 교환 제안이 없어요</b><span style="font-size: 13px; line-height: 1.5; color: #4A4F5C">{{emptyText}}</span></div>')
    main = (B_TAG + '<sc-if value="{{hasProposal}}">%s</sc-if>' % stepper_tpl()
            + '<sc-if value="{{noProposal}}">%s</sc-if><sc-if value="{{hasProposal}}">%s</sc-if>' % (empty, proposal))
    footer = ('<sc-if value="{{canRespond}}"><p style="margin: 0; font-size: 12px; line-height: 1.5; color: #4A4F5C">{{respondNote}}</p>'
              '<div style="display: flex; gap: 10px"><button type="button" data-act="recvDecline" style="width: 112px; height: 54px; border: 1.5px solid #8B909C; border-radius: 14px; '
              'background: #FFFFFF; font-family: inherit; font-size: 15px; font-weight: 700; color: #4A4F5C">거절</button>'
              '<button type="button" data-act="recvAccept" style="flex: 1; height: 54px; border-radius: 14px; background: #5B3DF5; color: #FFFFFF; border: 0; '
              'font-family: inherit; font-size: 16px; font-weight: 700">제안 수락</button></div></sc-if>'
              '<sc-if value="{{hasWait}}"><p role="status" style="margin: 0; height: 50px; border-radius: 14px; border: 1.5px dashed #F2C3A0; background: #FFF8F2; display: flex; '
              'align-items: center; justify-content: center; gap: 8px; font-size: 14px; font-weight: 700; color: #A3440B">%s{{waitText}}</p></sc-if>'
              '<sc-if value="{{hasBack}}"><button type="button" data-act="back" style="height: 50px; border-radius: 14px; font-family: inherit; font-size: 15px; font-weight: 700; '
              'background: #FFFFFF; color: #3A26C4; border: 1.5px solid #5B3DF5">{{backText}}</button></sc-if>' % icon('clock', WARN_FG, 16, 2.2))
    html = screen('좌석 교환 제안', '좌석 교환 제안', main, footer=footer, gap=8)
    html = sub1(html, B3.BACK_SPAN, U4.demo_only(close, B3.BACK_BTN), 'PairReceive')
    write('pair/PairReceive.dc.html', html)
    C3.patch('pair/PairReceive.dc.html', [], key='receive')


def build_intent():
    info = ['제안 받기는 제안을 받아 보겠다는 설정이에요. 교환에 동의하는 것이 아니에요',
            "제안이 오면 하나씩 보고 '제안 수락' 또는 거절을 직접 골라요",
            '같은 가격·등급 좌석의 제안만 받아요 (MVP 범위) · 언제든 끌 수 있어요']
    li = ''.join('<li style="display: flex; gap: 8px; align-items: flex-start; font-size: 12px; line-height: 1.5; color: %s">%s<span>%s</span></li>'
                 % (SUB2, icon('check', OK, 12, 3), x) for x in info)
    on_t, on_d = '받기', '옆자리 관객이 좌석 교환을 제안할 수 있어요.'
    off_t = '받지 않기 <span style="font-size: 11px; font-weight: 700; color: #3A26C4; background: #E9E5FF; padding: 2px 6px; border-radius: 4px">기본값</span>'
    off_d = '켜기 전에는 어떤 제안도 나에게 전송되지 않아요.'
    st_on = 'display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border-radius: 14px; border: 1.5px solid #5B3DF5; background: #F7F5FF'
    st_off = 'display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border-radius: 14px; border: 1px solid #E6E8EC; background: #FFFFFF'

    def radio(title, desc, attrs, style):
        return ('<label style="%s"><input type="radio" name="intent"%s style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 2px 0 0; flex-shrink: 0">'
                '<span style="display: flex; flex-direction: column; gap: 3px"><b style="font-size: 14px; display: flex; gap: 6px; align-items: center">%s</b>'
                '<span style="font-size: 12px; line-height: 1.5; color: #4A4F5C">%s</span></span></label>' % (style, attrs, title, desc))

    def static_opt(title, desc, on, style):   # 설명용 화면: 입력 요소가 아닌 그림
        dot = ('<span role="img" aria-label="%s (설명용 그림)" style="width: 20px; height: 20px; border-radius: 10px; border: 2px solid %s; box-sizing: border-box; '
               'flex-shrink: 0; margin-top: 2px; display: flex; align-items: center; justify-content: center">%s</span>'
               % ('선택됨' if on else '선택 안 됨', '#5B3DF5' if on else '#9AA0AC', '<span style="width: 10px; height: 10px; border-radius: 5px; background: #5B3DF5"></span>' if on else ''))
        return ('<div style="%s">%s<span style="display: flex; flex-direction: column; gap: 3px"><b style="font-size: 14px; display: flex; gap: 6px; align-items: center">%s</b>'
                '<span style="font-size: 12px; line-height: 1.5; color: #4A4F5C">%s</span></span></div>' % (style, dot, title, desc))
    static_r = (static_opt(on_t, on_d, False, st_off) + static_opt(off_t, off_d, True, st_on)
                + '<span style="align-self: flex-start; font-size: 11px; font-weight: 700; color: #4A4F5C; background: #F0F1F4; padding: 2px 6px; border-radius: 4px">설명용 화면 · 체험은 07 보드의 수신자 B 폰</span>')
    demo_r = (radio(on_t, on_d, ' data-act="intent" data-val="on" checked="{{onChecked}}"', '{{onStyle}}')
              + radio(off_t, off_d, ' data-act="intent" data-val="off" checked="{{offChecked}}"', '{{offStyle}}'))
    card = ('<sc-if value="{{hasProposal}}"><div role="status" style="border: 2px solid #5B3DF5; background: #F7F5FF; border-radius: 14px; padding: 12px 14px; display: flex; flex-direction: column; gap: 6px">'
            '<div style="display: flex; align-items: center; gap: 8px"><sc-if value="{{cardNew}}">%s</sc-if><b style="font-size: 15px">{{card.title}}</b></div>'
            '<span style="font-size: 12px; line-height: 1.5; color: #4A4F5C">{{card.text}}</span>'
            '<button type="button" data-act="toReceive" style="height: 42px; border-radius: 12px; font-family: inherit; font-size: 14px; font-weight: 700; background: #5B3DF5; color: #FFFFFF; border: 0">{{card.cta}} →</button></div></sc-if>'
            % badge('plan', '새 제안', 11))
    main = ''.join([
        '<div style="display: flex; gap: 6px; flex-wrap: wrap; align-items: center">%s%s%s</div>' % (B_TAG, U4.EXP_TAG, tag('서비스 설계 가정', PRIMARY_DARK, SOFT2)),
        card,
        B3.box('<span style="font-size: 12px; font-weight: 500; color: #5F6370">내 티켓</span><span style="font-size: 13px; font-weight: 700">{{myTicket}}</span>', pad='10px 14px', gap=3),
        '<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px"><h2 style="margin: 0; font-size: 16px; font-weight: 700">교환 제안 받기</h2>'
        '<sc-if value="{{statusOn}}">%s</sc-if><sc-if value="{{statusOff}}">%s</sc-if></div>' % (badge('ok', '{{statusText}}', 11), badge('mute', '{{statusText}}', 11)),
        U4.demo_only(static_r, demo_r),
        '<sc-if value="{{dirty}}"><p %s>{{dirtyText}}</p></sc-if>' % U4.STATUS_P,
        '<sc-if value="{{hasMsg}}"><p role="status" style="margin: 0; font-size: 13px; line-height: 1.5; font-weight: 700; color: #1F7A4D">{{msg}}</p></sc-if>',
        '<sc-if value="{{locked}}"><p style="margin: 0; font-size: 12px; line-height: 1.5; color: #4A4F5C">%s{{lockText}}</p></sc-if>' % U4.LOCK,
        B3.box("<b style=\"font-size: 13px\">'교환 제안 받기'와 '제안 수락'은 달라요</b>"
               '<ul style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 5px">%s</ul>' % li, pad='11px 14px', gap=6),
    ])
    footer = U4.demo_only('<button type="button" disabled aria-disabled="true" style="height: 50px; border-radius: 14px; font-family: inherit; font-size: 15px; font-weight: 700; '
                          'background: #EEF0F3; color: #5F6370; border: 1.5px dashed #9AA0AC">%s설정 저장 (설명용 화면)</button>' % U4.LOCK,
                          '<button type="button" data-act="intentSave" style="height: 50px; border-radius: 14px; font-family: inherit; font-size: 15px; font-weight: 700; '
                          'background: #5B3DF5; color: #FFFFFF; border: 0">설정 저장</button>')
    write('pair/PairIntent.dc.html', screen('옆자리 교환 제안 설정', '옆자리 교환 제안 설정', main, footer=footer, gap=9))
    C3.patch('pair/PairIntent.dc.html', [], key='intent')


# ================================================================ 보드: 확대 보기 · 시연 제어판 · 설명용 표시
ZOOM_CODE = r'''
var ZOOM_BASE = __ZBASE__;
var ZOOM_INFO = __ZINFO__;
var ZOOM_ORDER = __ZORDER__;
var ZOOM_DEMO = __ZDEMO__;
function zoomStyle(i, list) {
var k = list ? list.indexOf(i) : -1;
if (k < 0) return ZOOM_BASE[i];
var n = list.length, W = n * 390 + (n - 1) * 40, total = W + 40 + 320, left = Math.round((1920 - total) / 2) + k * 430;
return 'outline: none; width: 390px; height: 844px; position: fixed; left: ' + left + 'px; top: 118px; z-index: 1001; transform: none; background: #FFFFFF; border-radius: 28px; overflow: hidden; box-shadow: 0 24px 80px rgba(0, 0, 0, 0.55)';
}
function zoomPanelStyle(list) {
var n = list.length, W = n * 390 + (n - 1) * 40, total = W + 40 + 320, left = Math.round((1920 - total) / 2) + W + 40;
return 'position: fixed; left: ' + left + 'px; top: 118px; width: 320px; z-index: 1002; display: flex; flex-direction: column; gap: 14px; color: #FFFFFF; outline: none';
}
function zoomEl(i) { return document.querySelector('[data-zoom-host="' + i + '"]'); }
function zoomFocusables(list) {
var out = [];
list.forEach(function (i) {
var host = zoomEl(i);
if (!host) return;
var scr = [].slice.call(host.querySelectorAll(':scope > [data-nav-screen]')).filter(function (c) { return getComputedStyle(c).display !== 'none'; })[0] || host;
[].slice.call(scr.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), summary')).forEach(function (e) { if (e.offsetParent !== null) out.push(e); });
});
[].slice.call(document.querySelectorAll('[data-zoom-ctl] button')).forEach(function (e) { out.push(e); });
return out;
}
'''

ZOOM_METHODS = r'''
openZoom(list, trigger) {
this.zoomTrigger = trigger || null;
this.setState(function () { return { zoom: list }; }, function () { var h = zoomEl(list[0]); if (h && h.focus) { try { h.focus({ preventScroll: true }); } catch (err) { /* 무시 */ } } });
}
closeZoom() {
var z = this.state.zoom, trig = this.zoomTrigger;
this.setState(function () { return { zoom: null }; }, function () {
var el = trig || (z ? document.querySelector('[data-zoom-btn="' + z[0] + '"]') : null);
if (el && el.focus) { try { el.focus({ preventScroll: true }); } catch (err) { /* 무시 */ } }
});
}
stepZoom(d) {
var z = this.state.zoom;
if (!z || z.length !== 1) return;
var k = ZOOM_ORDER.indexOf(z[0]);
var nx = ZOOM_ORDER[(k + d + ZOOM_ORDER.length) % ZOOM_ORDER.length];
this.zoomTrigger = document.querySelector('[data-zoom-btn="' + nx + '"]');
this.setState(function () { return { zoom: [nx] }; });
}
zoomKey(e) {
var z = this.state && this.state.zoom;
if (!z || !e) return false;
if (e.key === 'Escape') { e.preventDefault(); this.closeZoom(); return true; }
if (e.key === 'Tab') {
var list = zoomFocusables(z);
if (!list.length) return false;
var k = list.indexOf(document.activeElement);
var nx = e.shiftKey ? (k <= 0 ? list.length - 1 : k - 1) : (k < 0 || k >= list.length - 1 ? 0 : k + 1);
e.preventDefault();
try { list[nx].focus({ preventScroll: true }); } catch (err) { /* 무시 */ }
return true;
}
return false;
}
'''

ZOOM_VALS = r'''
function zoomVals(self, v) {
var z = (self.state && self.state.zoom) || null;
ZOOM_BASE.forEach(function (_, i) {
v['zs_' + i] = zoomStyle(i, z);
v['zoom_' + i] = function (e) { if (e && e.preventDefault) e.preventDefault(); self.openZoom([i], e && e.currentTarget); };
v['zk_' + i] = function (e) { self.zoomKey(e); };
});
v.zoomDemo = function (e) { if (e && e.preventDefault) e.preventDefault(); self.openZoom(ZOOM_DEMO, e && e.currentTarget); };
v.zclose = function (e) { if (e && e.preventDefault) e.preventDefault(); self.closeZoom(); };
v.zprev = function (e) { if (e && e.preventDefault) e.preventDefault(); self.stepZoom(-1); };
v.znext = function (e) { if (e && e.preventDefault) e.preventDefault(); self.stepZoom(1); };
v.zkey = function (e) { self.zoomKey(e); };
v.zoomOpen = !!z;
v.zoomSingle = !!(z && z.length === 1 && ZOOM_ORDER.length > 1);
var info = z ? z.map(function (i) { return ZOOM_INFO[i]; }) : [];
v.zoomRole = info.map(function (x) { return x.role; }).join(' · ');
v.zoomTitle = info.map(function (x) { return x.title; }).join(' / ');
v.zoomHelp = info.length ? info[0].help : '';
v.zoomPos = z && z.length === 1 ? (ZOOM_ORDER.indexOf(z[0]) + 1) + ' / ' + ZOOM_ORDER.length : '';
v.zpanelStyle = z ? zoomPanelStyle(z) : 'display: none';
v.zoomLive = z ? '크게 보기 열림: ' + v.zoomTitle + '. Esc 로 닫아요.' : '';
return v;
}
'''

ZOOM_BTN = ('<button type="button" data-zoom-btn="%(i)d" onclick="{{zoom_%(i)d}}" aria-label="%(label)s 크게 보기" title="크게 보기" '
            'style="position: absolute; right: 6px; top: 6px; z-index: 3; width: 30px; height: 30px; border-radius: 15px; border: 1.5px solid #FFFFFF; '
            'background: rgba(25, 27, 34, 0.86); color: #FFFFFF; display: flex; align-items: center; justify-content: center; padding: 0; cursor: zoom-in">'
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/><path d="M11 8v6"/><path d="M8 11h6"/></svg></button>')

OVERLAY = ('<p aria-live="polite" style="%s">{{zoomLive}}</p>'
           '<sc-if value="{{zoomOpen}}"><div data-zoom-backdrop="" onclick="{{zclose}}" style="position: fixed; left: 0; top: 0; width: 1920px; height: 1080px; '
           'background: rgba(20, 16, 44, 0.8); z-index: 1000"></div>'
           '<section data-zoom-ctl="" role="dialog" aria-label="{{zoomTitle}} 크게 보기" onkeydown="{{zkey}}" style="{{zpanelStyle}}">'
           '<span style="align-self: flex-start; font-size: 13px; font-weight: 700; color: #191B22; background: #FFFFFF; padding: 5px 12px; border-radius: 999px">{{zoomRole}}</span>'
           '<b style="font-size: 26px; line-height: 1.35">{{zoomTitle}}</b>'
           '<p style="margin: 0; font-size: 16px; line-height: 1.6; color: #E3DDFF">{{zoomHelp}}</p>'
           '<sc-if value="{{zoomSingle}}"><div style="display: flex; align-items: center; gap: 10px">'
           '<button type="button" onclick="{{zprev}}" style="height: 44px; padding: 0 14px; border-radius: 12px; font-family: inherit; font-size: 15px; font-weight: 700; background: rgba(255, 255, 255, 0.14); color: #FFFFFF; border: 1.5px solid rgba(255, 255, 255, 0.5)">← 이전 화면</button>'
           '<span style="font-size: 15px; font-weight: 700">{{zoomPos}}</span>'
           '<button type="button" onclick="{{znext}}" style="height: 44px; padding: 0 14px; border-radius: 12px; font-family: inherit; font-size: 15px; font-weight: 700; background: rgba(255, 255, 255, 0.14); color: #FFFFFF; border: 1.5px solid rgba(255, 255, 255, 0.5)">다음 화면 →</button></div></sc-if>'
           '<button type="button" data-zoom-close="" onclick="{{zclose}}" style="height: 50px; border-radius: 14px; font-family: inherit; font-size: 16px; font-weight: 700; background: #FFFFFF; color: #191B22; border: 0">닫기 (Esc)</button>'
           '<span style="font-size: 14px; color: #C9BFFF">확대해도 진행 상태는 그대로예요. 닫으면 보드 화면으로 돌아가요.</span></section></sc-if>' % SR)

HELP = {'demo': '직접 눌러 체험할 수 있어요. 진행 상태와 입력은 그대로 유지돼요.',
        'nav': '설명용 화면이에요. 화면 안의 이동 링크만 동작해요.',
        'static': '설명용 정적 화면이에요. 크게 읽기 위한 보기예요.'}


def zoom_page(page, roles=None, order=None, demo_list=None, labels=None):
    """페이지의 폰마다 크게 보기 버튼과 확대 스타일을 연결하고, 오버레이·로직을 넣는다."""
    p = SRC / 'pages' / page / 'page.html'
    t = p.read_text(encoding='utf-8')
    roles = roles or {}
    nav = 'data-nav-host="' in t
    frames = list(re.finditer(r'<div style="(width: 226px; height: 490px;[^"]*)">(<div ([^>]*?)style="([^"]*transform: scale\(0\.58\)[^"]*)">)', t))
    if not frames:
        sys.exit(page + ': 폰 틀 없음')
    zbase, zinfo = {}, {}
    out, last = [], 0
    for k, m in enumerate(frames):
        attrs = m.group(3)
        hm = re.search(r'data-nav-host="(\d+)"', attrs)
        i = int(hm.group(1)) if hm else k     # 화면 배치 순서와 host 번호가 다를 수 있다 (P12: A·B 나란히)
        zbase[i] = m.group(4)
        cap = re.search(r'<figcaption[^>]*><b[^>]*>(.*?)</b>', t[m.end():])
        title = re.sub('<[^>]+>', '', cap.group(1)) if cap else '%d번 폰' % (k + 1)
        if labels and i in labels:
            title = labels[i]
        kind = 'demo' if str(i) in roles else ('nav' if nav else 'static')
        role = {'A': '신청자 A · 체험', 'B': '수신자 B · 체험'}.get(roles.get(str(i)), '%d번 화면' % (k + 1) + (' · 설명용' if kind != 'demo' else ''))
        zinfo[i] = {'role': role, 'title': title, 'help': HELP[kind]}
        frame_style = m.group(1) + '; position: relative'
        new_inner = '<div %s%sstyle="{{zs_%d}}">' % (attrs, '' if hm else 'data-zoom-host="%d" tabIndex="-1" onkeydown="{{zk_%d}}" ' % (i, i), i)
        if hm:
            new_inner = new_inner.replace('data-nav-host="%d"' % i, 'data-nav-host="%d" data-zoom-host="%d"' % (i, i), 1)
        out.append(t[last:m.start()])
        out.append('<div style="%s">' % frame_style + ZOOM_BTN % {'i': i, 'label': title} + new_inner)
        last = m.end()
    out.append(t[last:])
    t = ''.join(out)
    # 오버레이: 보드 루트의 마지막에
    end = t.rindex('</x-dc>')
    root_close = t.rindex('</div>', 0, end)
    t = t[:root_close] + OVERLAY + t[root_close:]
    # 로직
    n = len(frames)
    zbase = [zbase[i] for i in range(n)]
    zinfo = [zinfo[i] for i in range(n)]
    zcode = (ZOOM_CODE.replace('__ZBASE__', json.dumps(zbase, ensure_ascii=False)).replace('__ZINFO__', json.dumps(zinfo, ensure_ascii=False))
             .replace('__ZORDER__', json.dumps(order or list(range(len(frames))))).replace('__ZDEMO__', json.dumps(demo_list or [0])))
    m = C3.SCRIPT_RE.search(t)
    code = m.group(2)
    if 'class Component extends DCLogic {\nrenderVals() {\nreturn {};\n}\n}' in code:   # 정적 페이지
        code = ('\n' + zcode + ZOOM_VALS + 'class Component extends DCLogic {\nconstructor(props) {\nsuper(props);\nthis.state = { zoom: null };\n}\n'
                + ZOOM_METHODS + 'renderVals() {\nreturn zoomVals(this, { nosubmit: function (e) { if (e && e.preventDefault) e.preventDefault(); } });\n}\n}\n')
    else:
        code = code.replace('class Component extends DCLogic {', zcode + ZOOM_VALS + 'class Component extends DCLogic {', 1)
        n0 = code.count('this.state = { stacks: INITIAL.map(function (s) { return [s]; })')
        code = code.replace('this.state = { stacks: INITIAL.map(function (s) { return [s]; })', 'this.state = { zoom: null, stacks: INITIAL.map(function (s) { return [s]; })', 1)
        code = code.replace('keydown(i, e) {\n', ZOOM_METHODS + 'keydown(i, e) {\nif (this.zoomKey(e)) return;\n', 1)
        if n0 != 1 or 'zoomKey(e)) return;' not in code:
            sys.exit(page + ': 로직 연결 실패')
        # renderVals 마지막 return 직전에 확대 값 추가
        rv = code.index('renderVals() {')
        ret = code.rindex('\nreturn ', rv)
        code = code[:ret] + '\nzoomVals(self, v);' + code[ret:]
    if '</' in code:
        sys.exit(page + ': 로직에 </ 가 있음')
    t = t[:m.start(2)] + code + t[m.end(2):]
    # 루트 기준 위치 (제어판·표시 배지를 보드 오른쪽 위에 두기 위함)
    t = t.replace('display: flex; flex-direction: column; gap: 36px; overflow: hidden">', 'display: flex; flex-direction: column; gap: 36px; overflow: hidden; position: relative">', 1)
    p.write_text(t, encoding='utf-8')
    print('확대 보기: %s (폰 %d대)' % (page, len(frames)))


# 시연 제어판 (공통 구조): [DEMO · 시연용 제어 · 실제 기능 아님 | 체험 폰 크게 보기 | 처음부터 다시] / 다음 단계 / 시나리오 / 조작
CTL_BTN2 = ('height: 30px; padding: 0 10px; border-radius: 9px; font-family: inherit; font-size: 12px; font-weight: 700; background: #FFFFFF; '
            'color: #191B22; border: 1.5px solid #191B22')


def ctl_panel(scenario, zoom_label):
    return ('<section data-demo-ctl="" tabIndex="-1" onclick="{{ctl}}" onkeydown="{{ctlKey}}" aria-label="시연용 제어 (실제 서비스 기능 아님)" '
            'style="position: absolute; right: 120px; top: 30px; width: 600px; box-sizing: border-box; z-index: 5; outline: none; background: #F5F6F8; '
            'border: 2px dashed #191B22; border-radius: 18px; padding: 12px 16px; display: flex; flex-direction: column; gap: 8px">'
            '<div style="display: flex; align-items: center; gap: 8px">%(tag)s<b style="font-size: 15px; color: #191B22">시연용 제어</b>'
            '<span style="flex: 1; font-size: 13px; color: #4A4F5C">실제 서비스 기능이 아니에요</span>'
            '<button type="button" data-act="zoomDemo" style="%(b2)s">%(zoom)s</button><button type="button" data-act="demoReset" style="%(b2)s">처음부터 다시</button></div>'
            '<p aria-live="polite" style="margin: 0; font-size: 13px; line-height: 1.45; color: #191B22"><b style="color: #3A26C4">다음 단계</b> {{ctlView.hint}}</p>'
            '<div role="group" aria-label="시나리오 · {{ctlView.profileNote}}" style="display: flex; align-items: center; flex-wrap: wrap; gap: 6px; min-height: 32px"><span style="width: 72px; font-size: 13px; font-weight: 700; color: #4A4F5C">시나리오</span>%(scn)s</div>'
            '<div style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px; min-height: 34px"><span style="width: 72px; font-size: 13px; font-weight: 700; color: #4A4F5C">조작</span>'
            '<sc-if value="{{ctlView.hasButtons}}"><sc-for list="{{ctlView.buttons}}" as="b"><button type="button" data-act="{{b.act}}" style="{{b.style}}">{{b.label}}</button></sc-for></sc-if>'
            '<sc-if value="{{ctlView.noButtons}}"><span style="font-size: 13px; color: #5F6370">지금은 폰에서 진행해요</span></sc-if></div></section>'
            % {'tag': U4.DEMO_TAG, 'b2': CTL_BTN2, 'zoom': zoom_label, 'scn': scenario})


STATIC_BADGE = ('<div aria-label="설명용 화면 안내" style="position: absolute; right: 120px; top: 44px; z-index: 5; display: flex; align-items: center; gap: 10px; '
                'background: #FFFFFF; border: 1.5px dashed #8B909C; border-radius: 999px; padding: 8px 16px; font-size: 14px; color: #4A4F5C">'
                '<span style="font-size: 11px; font-weight: 900; letter-spacing: 1px; color: #4A4F5C; background: #E6E8EC; padding: 3px 7px; border-radius: 6px">설명용</span>'
                '정적 화면이에요 · 직접 체험은 06·07 보드 · 폰의 %s로 크게 보기</div>'
                % '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#4A4F5C" stroke-width="2.4" stroke-linecap="round" aria-label="돋보기" role="img" style="vertical-align: -2px"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>')


def insert_top(page, html, remove_re=None):
    p = SRC / 'pages' / page / 'page.html'
    t = p.read_text(encoding='utf-8')
    if remove_re:
        t, n = re.subn(remove_re, '', t, count=1, flags=re.S)
        if n != 1:
            sys.exit(page + ': 기존 제어판을 찾지 못함')
    root = re.search(r'<div style="width: 1920px; height: 1080px;[^"]*">', t)
    t = t[:root.end()] + '\n' + html + t[root.end():]
    p.write_text(t, encoding='utf-8')


OLD_PANEL_RE = r'<section data-demo-ctl="".*?</section>\n?'


def page_exchange():
    insert_top('p07-ui-exchange', ctl_panel('<span style="font-size: 13px; color: #4A4F5C">폰에서 회차·구역·열 조건을 바꾸면 결과가 달라져요 (시연 데이터)</span>', '체험 폰 크게 보기'),
               remove_re=OLD_PANEL_RE)
    zoom_page('p07-ui-exchange', roles={'0': 'A'}, demo_list=[0])


def page_pair():
    p = SRC / 'pages/p08-ui-pair/page.html'
    t = p.read_text(encoding='utf-8')
    # 1) 오른쪽 카드 안의 기존 제어판 제거 → 보드 위쪽 공통 제어판
    t, n = re.subn(OLD_PANEL_RE, '', t, count=1, flags=re.S)
    if n != 1:
        sys.exit('P12 제어판 없음')
    p.write_text(t, encoding='utf-8')
    scen = ('<sc-for list="{{ctlView.profiles}}" as="p"><button type="button" data-act="profile" data-val="{{p.val}}" aria-pressed="{{p.pressed}}" disabled="{{p.disabled}}" style="{{p.style}}">{{p.label}}</button></sc-for>'
            '<span style="font-size: 12px; color: #5F6370">B 티켓 상황</span>')
    insert_top('p08-ui-pair', ctl_panel(scen, 'A·B 함께 크게 보기'))
    t = p.read_text(encoding='utf-8')
    # 2) 신청자 A 와 수신자 B 를 나란히: 3번째 figure(B)를 2번째 자리로
    figs = list(re.finditer(r'<figure style="margin: 0; width: 226px;.*?</figure>', t, flags=re.S))
    if len(figs) != 4:
        sys.exit('P12 figure 수 %d' % len(figs))
    fA, f1, fB, f3 = [x.group(0) for x in figs]
    circ = lambda txt, bg, fg, w='32px': ('<span style="min-width: %s; height: 32px; padding: 0 %s; box-sizing: border-box; border-radius: 16px; background: %s; color: %s; font-size: 15px; '
                                          'font-weight: 900; display: flex; align-items: center; justify-content: center; flex-shrink: 0">%s</span>' % (w, '0' if w == '32px' else '10px', bg, fg, txt))
    num_re = r'<div style="display: flex; align-items: center; gap: 10px"><span style="width: 32px;[^>]*>[^<]*</span>(?:<span style="flex: 1; height: 2px; background: #8E7BFA; margin-right: -28px"></span>)?</div>'
    connector = ('<div style="display: flex; align-items: center; gap: 8px">%s<span style="flex: 1; display: flex; align-items: center; gap: 6px; margin-right: -36px; position: relative; z-index: 2">'
                 '<span style="flex: 1; height: 2px; background: #FFFFFF"></span><span style="font-size: 13px; font-weight: 700; color: #191B22; background: #FFFFFF; padding: 5px 10px; '
                 'border-radius: 999px; white-space: nowrap">제안 → ← 응답</span><span style="flex: 1; height: 2px; background: #FFFFFF"></span></span></div>' % circ('A', '#FFFFFF', '#5B3DF5'))
    rowB = ('<div style="display: flex; align-items: center; gap: 10px">%s<span style="flex: 1; height: 2px; background: #8E7BFA; margin-right: -28px; opacity: 0.6"></span></div>' % circ('B', '#FFB37A', '#5A2A06'))
    rowS = lambda: ('<div style="display: flex; align-items: center; gap: 10px">%s<span style="flex: 1; height: 2px; background: #8E7BFA; margin-right: -28px; opacity: 0.6"></span></div>'
                    % circ('예시', 'rgba(255, 255, 255, 0.22)', '#FFFFFF', 'auto'))
    def renum(f, new):
        f2, n = re.subn(num_re, lambda m: new, f, count=1)
        if n != 1:
            sys.exit('P12 번호 행 없음')
        return f2
    fA = renum(fA, connector)
    fB = renum(fB, rowB)
    f1 = renum(f1, rowS())
    f3 = renum(f3, rowS().replace('; opacity: 0.6"></span></div>', '; opacity: 0"></span></div>'))
    # 캡션: 역할과 보유 좌석을 같은 형식으로
    chip = lambda s: '<span style="font-size: 13px; font-weight: 700; color: #191B22; background: #FFFFFF; padding: 2px 8px; border-radius: 6px">%s</span>' % s
    fA = re.sub(r'<figcaption([^>]*)><b[^>]*>.*?</b><span[^>]*>.*?</span>',
                lambda m: '<figcaption%s><b style="font-size: 17px; color: #FFFFFF">신청자 A · 교환을 요청해요</b><span style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center; '
                'font-size: 14px; color: #E3DDFF">보유 %s %s → 11열 4·5번 나란히</span>' % (m.group(1), chip('7열 12번'), chip('11열 4번')), fA, count=1, flags=re.S)
    fB = re.sub(r'<figcaption([^>]*)><b[^>]*>.*?</b><span[^>]*>.*?</span>',
                lambda m: '<figcaption%s><b style="font-size: 17px; color: #FFD2AE">수신자 B · 제안에 응답해요</b><span style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center; '
                'font-size: 14px; color: #E3DDFF">보유 %s</span><span style="font-size: 14px; line-height: 1.5; color: #E3DDFF">\'교환 제안 받기\'를 켜야 제안이 도착해요</span>' % (m.group(1), chip('11열 5번')), fB, count=1, flags=re.S)
    f1 = re.sub(r'(<figcaption[^>]*><b[^>]*>)방향 선택(</b>)', r'\1예시 · 방향 선택\2', f1, count=1)
    f3 = re.sub(r'(<figcaption[^>]*><b[^>]*>)연석 완료(</b>)', r'\1예시 · 연석 완료\2', f3, count=1)
    seg_start, seg_end = figs[0].start(), figs[3].end()
    between = [t[figs[k].end():figs[k + 1].start()] for k in range(3)]
    t = t[:seg_start] + fA + between[0] + fB + between[1] + f1 + between[2] + f3 + t[seg_end:]
    flow = ('<div aria-label="양방향 흐름 요약" style="margin-top: auto; border-top: 1px solid #E6E8EC; padding-top: 18px; display: flex; flex-direction: column; gap: 10px">'
            '<b style="font-size: 16px">누가 요청하고 누가 응답할까요</b><div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 14px; font-weight: 700">'
            '%s<span aria-hidden="true" style="color: #5B3DF5">→</span>%s<span aria-hidden="true" style="color: #5B3DF5">→</span>%s<span aria-hidden="true" style="color: #5B3DF5">→</span>%s</div>'
            '<span style="font-size: 14px; line-height: 1.55; color: #4A4F5C">양쪽 조건(A: 유지할 좌석 바로 옆 · B: 등록한 조건)이 모두 맞을 때만 후보로 연결돼요. B 가 수락해도 최종 확인을 통과해야 교환 완료예요.</span></div>'
            % ('<span style="background: #F0EDFF; color: #3A26C4; padding: 5px 10px; border-radius: 999px">A 교환 제안 보내기</span>',
               '<span style="background: #FFF1E6; color: #A3440B; padding: 5px 10px; border-radius: 999px">B 제안 수락 / 거절</span>',
               '<span style="background: #F5F6F8; color: #4A4F5C; padding: 5px 10px; border-radius: 999px">최종 확인</span>',
               '<span style="background: #E6F6EE; color: #1F7A4D; padding: 5px 10px; border-radius: 999px">교환 완료</span>'))
    kd = t.index('KEY DECISION')
    sec_end = t.index('</section>', kd)
    t = t[:sec_end] + flow + t[sec_end:]
    p.write_text(t, encoding='utf-8')
    zoom_page('p08-ui-pair', roles={'0': 'A', '2': 'B'}, order=[0, 2, 1, 3], demo_list=[0, 2],
              labels={0: '신청자 A · 교환을 요청해요', 2: '수신자 B · 제안에 응답해요', 1: '예시 · 방향 선택', 3: '예시 · 연석 완료'})
    print('페이지: p08-ui-pair (A·B 나란히, 공통 제어판)')


def static_boards():
    for page in ['p07b-conditions-match', 'p07c-status', 'p07d-exceptions', 'p08b-pair-states']:
        insert_top(page, STATIC_BADGE)
        zoom_page(page)
    p = SRC / 'pages/p08b-pair-states/page.html'
    t = p.read_text(encoding='utf-8')
    t = t.replace('>제안 수신 의향</b>', '>교환 제안 받기 (수신 의향)</b>', 1)
    p.write_text(t, encoding='utf-8')


def refresh_stores():
    """페이지 로직에 들어 있는 엔진 사본을 현재 엔진(STEP 4B 화면 데이터 포함)으로 바꾼다. 판정 규칙은 그대로."""
    s3, sp = U4.store_src()
    for page, engine, code in [('p07-ui-exchange', 'DEMO', s3), ('p08-ui-pair', 'PAIR', s3 + '\n' + sp)]:
        p = SRC / 'pages' / page / 'page.html'
        t = p.read_text(encoding='utf-8')
        a = t.index('var DEMO = (function () {')
        b = t.index('\nvar ENGINE = %s;' % engine)
        t = t[:a] + code + t[b:]
        if '</' in C3.SCRIPT_RE.search(t).group(2):
            sys.exit(page + ': 로직에 </ 가 있음')
        p.write_text(t, encoding='utf-8')
        print('엔진 사본 갱신:', page)


def page_logic_ctl():
    """제어판의 '체험 폰 크게 보기' 버튼과 '조작 없음' 표시를 페이지 로직에 연결한다."""
    for page in ['p07-ui-exchange', 'p08-ui-pair']:
        p = SRC / 'pages' / page / 'page.html'
        t = p.read_text(encoding='utf-8')
        a = "if (el.getAttribute('data-act') === 'demoReset') { this.resetDemo(panel); return; }"
        if t.count(a) != 1:
            sys.exit(page + ': 제어판 로직 없음')
        t = t.replace(a, a + "\nif (el.getAttribute('data-act') === 'zoomDemo') { this.openZoom(ZOOM_DEMO, el); return; }")
        b = "var v = { nosubmit: function (e) { if (e && e.preventDefault) e.preventDefault(); }, demo: demo, ctlView: demo.ctl,"
        if t.count(b) != 1:
            sys.exit(page + ': renderVals 없음')
        t = t.replace(b, "demo.ctl.noButtons = !demo.ctl.hasButtons;\n" + b)
        p.write_text(t, encoding='utf-8')


if __name__ == '__main__':
    build_matchcheck()
    build_compare()
    general_steppers()
    pair_screens()
    build_adjacency()
    build_warn()
    build_receive()
    build_intent()
    U4.mark_disabled()
    page_exchange()
    page_pair()
    static_boards()
    refresh_stores()
    page_logic_ctl()
