"""STEP 4A: UX 결함 해결 및 사용자 흐름 완성 (1회성 적용 스크립트, STEP 3C 커밋 상태에서 실행).

- 수신자 UX: P12 3번 폰을 옆자리 관객(11열 5번)의 체험 폰으로 연결 (PairIntent '교환 제안 받기' 설정 · PairReceive 제안 검토)
  신청자(1번 폰)와 수신자(3번 폰)는 페이지 로직의 같은 상태(demo3c_pair.js)를 본다.
- 개인정보: 후보 화면은 연결 가능한 후보만 보여주고, 다른 관객의 수신 의향·자격·조건·동행 여부를 좌석별로 표시하지 않는다.
- 용어: 교환 제안 받기 / 교환 제안 보내기 / 제안 수락 / 최종 확인 중 / 교환 완료. 공용 화면(StatusSent·ExCancelled)은 흐름별 문구.
- 연석 흐름: 단계 표시(1/4~4/4), 첫 화면의 유지할 좌석·제공할 좌석 안내, 후보 없음 → 반대 방향 찾기, 거절 → 다른 후보·이전 단계.
- 시연 제어: 휴대폰 화면 안의 데모 패널을 없애고, 폰 밖 '시연 제어판'(P08 1번 폰 아래, P12 오른쪽 카드)으로 옮긴다.
- 접근성: 화면 전환·상태를 짧게 알리는 aria-live 영역, 상태 메시지 role="status", 비활성 버튼에 잠금 아이콘·점선 테두리.
사용법: python3 tools/authoring/apply_ux_4a.py
"""
import json
import re
import sys
import uuid as uuidlib
from hashlib import sha256
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_demo_3b as B3            # noqa: E402
import apply_pair_3c as C3            # noqa: E402
from dc_kit import *                  # noqa: E402,F401

SRC, COMP = B3.SRC, B3.COMP
patch, demo_only, back_link = C3.patch, C3.demo_only, C3.back_link
EXP_TAG, SIM_NOTE = C3.EXP_TAG, C3.SIM_NOTE
LOCK = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true" style="vertical-align: -2px; margin-right: 6px"><rect x="4" y="11" width="16" height="9" rx="2"/>'
        '<path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>')
B_TAG = ('<span style="align-self: flex-start; font-size: 12px; font-weight: 700; color: #4A4F5C; background: #F0F1F4; padding: 5px 9px; '
         'border-radius: 6px">11열 5번 관객의 화면</span>')
STATUS_P = 'role="status" style="margin: 0; font-size: 13px; line-height: 1.5; font-weight: 700; color: #A3440B"'


def read(rel):
    return (COMP / rel).read_text(encoding='utf-8')


def write(rel, t):
    (COMP / rel).write_text(t, encoding='utf-8')


def sub1(t, old, new, rel=''):
    if t.count(old) != 1:
        sys.exit('%s: 치환 대상 %d회 (%s)' % (rel, t.count(old), old[:80]))
    return t.replace(old, new)


def step_bar(n, label):
    bars = ''.join('<span style="flex: 1; height: 4px; border-radius: 2px; background: %s"></span>' % ('#5B3DF5' if i <= n else '#E6E8EC')
                   for i in range(1, 5))
    return ('<div role="group" aria-label="연석 만들기 진행 단계 %d/4: %s" style="display: flex; flex-direction: column; gap: 6px; flex-shrink: 0">'
            '<div style="display: flex; justify-content: space-between; align-items: center"><span style="font-size: 12px; font-weight: 700; color: #3A26C4">'
            '단계 %d/4 · %s</span>%s</div><div aria-hidden="true" style="display: flex; gap: 4px">%s</div></div>'
            % (n, label, n, label, '<span style="font-size: 11px; font-weight: 700; color: #A3440B; background: #FFF1E6; padding: 2px 6px; border-radius: 4px">실험 기능</span>', bars))


def insert_after_main(t, html, rel):
    m = re.search(r'<main style="[^"]*">\n?', t)
    if not m:
        sys.exit(rel + ': main 없음')
    return t[:m.end()] + html + t[m.end():]


def badge_kind(var, size=11):
    return B3.badge_switch(var, size)


def row_tpl(var, label_style='font-size: 12px; color: #4A4F5C'):
    return ('<div style="display: flex; flex-direction: column; gap: 1px; padding: 4px 0; border-top: 1px solid #EEF0F3">'
            '<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px">'
            '<span style="%s">{{%s.label}}</span>%s</div>'
            '<sc-if value="{{%s.hasDetail}}"><span style="font-size: 12px; line-height: 1.4; color: #5F6370">{{%s.detail}}</span></sc-if></div>'
            % (label_style, var, badge_kind(var), var, var))


def cmp_tpl(var, cols='62px 1fr auto'):
    """비교 한 줄: 항목 | 지금 → 교환 후 | 결과 (텍스트 태그)"""
    return ('<div style="display: grid; grid-template-columns: %s; gap: 8px; padding: 5px 0; border-top: 1px solid #EEF0F3; align-items: center">'
            '<span style="font-size: 12px; font-weight: 700; color: #5F6370">{{%s.label}}</span>'
            '<span style="font-size: 13px; line-height: 1.35; font-weight: 700">{{%s.change}}</span>'
            '<span style="{{%s.tagStyle}}">{{%s.text}}</span></div>' % (cols, var, var, var, var))


def cmp_head(a, b, cols='62px 1fr auto'):
    return ('<div style="display: grid; grid-template-columns: %s; gap: 8px; padding-bottom: 4px"><span></span>'
            '<span style="font-size: 11px; font-weight: 700; color: #5F6370">%s → <span style="color: #3A26C4">%s</span></span><span></span></div>'
            % (cols, a, b))


# ================================================================ 신청자 연석 화면
def patch_mode():
    rel = 'pair/PairMode.dc.html'
    t = read(rel)
    concept = ('<div style="display: flex; gap: 8px; align-items: flex-start; background: #F0EDFF; border-radius: 12px; padding: 10px 12px; flex-shrink: 0">%s'
               '<p style="margin: 0; font-size: 13px; line-height: 1.5; color: #3A26C4">2장 중 한 장은 <b>유지할 좌석</b>으로 두고, 다른 한 장을 <b>교환에 제공할 좌석</b>으로 '
               '옆자리 관객 좌석과 바꿔요. 유지할 좌석은 다음 단계에서 골라요.</p></div>' % icon('info', PRIMARY_DARK, 16, 2.2))
    t = insert_after_main(t, step_bar(1, '교환 방식') + concept, rel)
    t = sub1(t, '<main style="flex: 1; display: flex; flex-direction: column; gap: 28px;', '<main style="flex: 1; display: flex; flex-direction: column; gap: 10px;', rel)
    t = t.replace('떨어진 2장을 나란히 붙여요. 제안 수신에 동의한 옆자리 관객에게 제안을 보내요 (수요 미검증)',
                  "떨어진 2장을 나란히 붙여요. '교환 제안 받기'를 켠 옆자리 관객에게만 제안을 보내요 (수요 미검증)")
    write(rel, t)
    patch(rel, [], key='mode')   # 기본 화면 데이터도 4A 엔진 값으로


def patch_seat():
    rel = 'pair/PairSeat.dc.html'
    t = read(rel)
    t = insert_after_main(t, step_bar(2, '유지할 좌석'), rel)
    t = sub1(t, '>동의한 옆자리에 제안 보내기</a>', '>옆자리 후보 확인하기</a>', rel)
    t = sub1(t, '></span>지킬 좌석</span>', '></span>유지할 좌석</span>', rel)
    t = sub1(t, '></span>내놓을 좌석</span>', '></span>제공할 좌석</span>', rel)
    t = sub1(t, '<legend style="font-size: 16px; font-weight: 700; padding: 0; margin-bottom: 10px">어느 쪽으로 모을까요?</legend>',
             '<legend style="font-size: 16px; font-weight: 700; padding: 0; margin-bottom: 10px">어느 좌석을 유지할까요?</legend>', rel)
    old = re.search(r'<p style="margin: 0; font-size: 12px; line-height: 1.5; color: #5F6370">교환 의향을 등록했거나[^<]*</p>', t)
    if not old:
        sys.exit(rel + ': 안내 문단 없음')
    t = t.replace(old.group(0), '<p style="margin: 0; font-size: 12px; line-height: 1.5; color: #5F6370">'
                  "'교환 제안 받기'를 켠 관객에게만 제안해요 (서비스 설계 가정). 번호가 이어져도 인접 여부는 배치도로 따로 확인해요. "
                  '상대가 제안을 수락해도 최종 확인 뒤에 교환돼요.</p>')
    write(rel, t)
    patch(rel, [], key='seat')   # 기본 화면 데이터도 4A 엔진 값으로


def build_adjacency():
    card = ('<section style="{{c.border}}; border-radius: 14px; padding: 12px 14px; display: flex; flex-direction: column; gap: 4px">'
            '<div style="display: flex; justify-content: space-between; align-items: center; gap: 8px"><b style="font-size: 15px">{{c.title}}</b>%s</div>'
            '<sc-for list="{{c.rows}}" as="r">%s</sc-for>'
            '<sc-if value="{{c.hasNote}}"><span style="font-size: 12px; line-height: 1.45; color: #4A4F5C">{{c.note}}</span></sc-if>'
            '<button type="button" data-act="choose" data-val="{{c.key}}" aria-pressed="{{c.pressed}}" disabled="{{c.cantPick}}" style="{{c.pickStyle}}; margin-top: 6px">{{c.pickText}}</button>'
            '</section>' % (badge_kind('c', 12), row_tpl('r')))
    empty = ('<sc-if value="{{noCandidate}}"><section role="status" style="border: 1.5px dashed #C9CDD5; background: #F5F6F8; border-radius: 14px; padding: 14px; display: flex; flex-direction: column; gap: 6px">'
             '<b style="font-size: 15px">{{emptyTitle}}</b><span style="font-size: 13px; line-height: 1.5; color: #4A4F5C">{{emptyText}}</span>'
             '<sc-if value="{{canFlip}}"><button type="button" data-act="flipDir" style="margin-top: 4px; height: 40px; border-radius: 12px; font-family: inherit; font-size: 14px; '
             'font-weight: 700; background: #FFFFFF; color: #3A26C4; border: 1.5px solid #5B3DF5">{{flipText}}</button></sc-if></section></sc-if>')
    facts = ('<sc-if value="{{hasFacts}}"><div style="border: 1px solid #E6E8EC; border-radius: 14px; padding: 10px 14px; display: flex; flex-direction: column; gap: 2px">'
             '<b style="font-size: 12px">배치도에서 제외한 좌석 (좌석 정보)</b>'
             '<span style="font-size: 12px; line-height: 1.45; color: #5F6370">번호가 이어져도 통로가 있거나 배치도 정보가 없으면 옆자리로 보지 않아요.</span>'
             '<sc-for list="{{facts}}" as="r">%s</sc-for></div></sc-if>' % row_tpl('r', 'font-size: 12px; font-weight: 700'))
    main = ''.join([
        step_bar(3, '옆자리 후보'),
        '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px">'
        '<div style="border: 1.5px solid #5B3DF5; background: #F7F5FF; border-radius: 14px; padding: 8px 12px; display: flex; flex-direction: column; gap: 1px">'
        '<span style="font-size: 12px; font-weight: 700; color: #3A26C4">유지할 좌석</span><span style="font-size: 15px; font-weight: 700">{{keepName}}</span></div>'
        '<div style="border: 1px solid #DADDE3; border-radius: 14px; padding: 8px 12px; display: flex; flex-direction: column; gap: 1px">'
        '<span style="font-size: 12px; font-weight: 700; color: #5F6370">교환에 제공할 좌석</span><span style="font-size: 15px; font-weight: 700">{{offerName}}</span></div></div>',
        '<sc-if value="{{hasNotice}}"><p %s>{{notice}}</p></sc-if>' % STATUS_P,
        '<sc-for list="{{cards}}" as="c">%s</sc-for>' % card,
        empty, facts,
        B3.para("후보는 '교환 제안 받기'를 켠 관객 중 조건이 맞는 좌석만 보여줘요. 다른 관객의 설정·사유는 표시하지 않아요.", 12, SUB),
    ])
    footer = ('<sc-if value="{{nextHint}}"><p %s>{{nextHint}}</p></sc-if>' % STATUS_P
              + '<sc-if value="{{canNext}}">%s</sc-if><sc-if value="{{cantNext}}">%s</sc-if>'
              % (B3.act(cta('선택한 후보와 최종 비교하기'), 'toWarn'), cta('선택한 후보와 최종 비교하기', disabled=True)))
    write('pair/PairAdjacency.dc.html', screen('연석 후보 확인', '연석 후보 확인', main, footer=footer, gap=8))
    patch('pair/PairAdjacency.dc.html', [], key='adj', back=True)


def build_warn():
    li = ''.join('<li style="display: flex; gap: 8px; align-items: flex-start; font-size: 12px; line-height: 1.5; color: %s">%s<span>%s</span></li>'
                 % (SUB2, icon('dot', WARN, 12, 3), b) for b in [
                     '거절·취소되면 지금 좌석이 그대로 유지돼요',
                     '제안이 수락돼도 최종 확인에 실패하면 교환되지 않아요',
                     '상대는 일행과 함께 예매했거나 다른 이유로 거절할 수 있어요'])
    main = ''.join([
        step_bar(4, '최종 비교'),
        B3.box('<div style="display: flex; justify-content: space-between; align-items: center; padding-bottom: 4px"><b style="font-size: 12px">좌석·조건 최종 비교</b>%s</div>' % SIM_NOTE
               + cmp_head('지금', '교환 후') + '<sc-for list="{{compare}}" as="r">%s</sc-for>' % cmp_tpl('r')
               + '',
               bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='9px 14px', gap=0),
        B3.box('<b style="font-size: 12px">양방향 확인</b><sc-for list="{{twoWay}}" as="r">%s</sc-for>' % row_tpl('r', 'font-size: 12px; font-weight: 700')
               + '<span style="font-size: 12px; line-height: 1.45; color: #4A4F5C; padding-top: 4px">{{twoWayNote}}</span>',
               bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='9px 14px', gap=0),
        B3.box('<b style="font-size: 13px">보내기 전에 확인해 주세요</b><ul style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 4px">%s</ul>' % li,
               bg=WARN_BG, pad='10px 14px', gap=6),
        demo_only('<label style="display: flex; align-items: flex-start; gap: 10px; font-size: 14px; line-height: 1.5; color: %s">'
                  '<input type="checkbox" style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 0; flex-shrink: 0">위 내용을 확인했어요</label>' % TEXT,
                  '<label style="display: flex; align-items: flex-start; gap: 10px; font-size: 14px; line-height: 1.5; color: %s">'
                  '<input type="checkbox" data-act="ack" checked="{{ack}}" style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 0; flex-shrink: 0">위 내용을 확인했어요</label>' % TEXT),
    ])
    footer = ('<sc-if value="{{sendHint}}"><p %s>{{sendHint}}</p></sc-if>' % STATUS_P
              + '<sc-if value="{{canSend}}">%s</sc-if><sc-if value="{{cantSend}}">%s</sc-if>'
              % (B3.act(cta('{{sendText}}'), 'send'), cta('{{sendText}}', disabled=True)))
    write('pair/PairWarn.dc.html', screen('보내기 전 최종 비교', '보내기 전 최종 비교', main, footer=footer, gap=8))
    patch('pair/PairWarn.dc.html', [], key='warn', back=True)


def patch_results():
    rel = 'pair/PairAccepted.dc.html'
    t = read(rel)
    t = sub1(t, B3.panel('다음 단계 진행', [('최종 확인 시작', 'toFinal', 'primary')]), '', rel)
    t = sub1(t, '>옆자리 관객이 수락했어요<', '>옆자리 관객이 제안을 수락했어요<', rel)
    t = sub1(t, '제안 전송 <span', '교환 제안 보내기 <span', rel)
    t = sub1(t, '상대방 수락 <span', '제안 수락 <span', rel)
    t = sub1(t, '옆자리 관객도 수락했어요', '옆자리 관객이 제안을 수락했어요', rel)
    t = sub1(t, '>상대방 수락</span>', '>제안 수락</span>', rel)
    write(rel, t)
    print('컴포넌트:', rel)
    rel = 'pair/PairDeclined.dc.html'
    t = read(rel)
    t = sub1(t, B3.act(cta('다른 후보 확인하기'), 'otherCandidate'), B3.act(cta('다른 후보 찾기'), 'otherCandidate'), rel)
    t = sub1(t, B3.act(cta('반대 방향으로 모으기 보기', 'ghost'), 'otherDir'), B3.act(cta('이전 단계로 (유지할 좌석 다시 고르기)', 'ghost'), 'toSeat'), rel)
    t = sub1(t, '여전히 일행과 떨어진 좌석이에요. 다른 후보를 확인하거나 반대 방향으로 모으는 방법을 볼 수 있어요.',
             '여전히 일행과 떨어진 좌석이에요. 같은 방향의 다른 후보를 찾거나, 이전 단계에서 유지할 좌석을 다시 고를 수 있어요.', rel)
    write(rel, t)
    print('컴포넌트:', rel)
    rel = 'pair/PairDone.dc.html'
    t = read(rel)
    t = sub1(t, '시연용 모의 화면이에요. 의향을 등록한 다른 후보에게 보낸 제안은 닫혔어요.',
             '시연용 모의 화면이에요. 교환에 제공한 {{gave}} 좌석은 옆자리 관객의 새 좌석이 됐어요.', rel)
    write(rel, t)
    print('컴포넌트:', rel)


# ================================================================ 수신자 화면
def build_intent():
    info = ['제안 받기는 제안을 받아 보겠다는 설정이에요. 교환에 동의하는 것이 아니에요',
            "제안이 오면 하나씩 보고 '제안 수락' 또는 거절을 직접 골라요. 거절해도 불이익이 없다고 가정했어요",
            '같은 가격·등급 좌석의 제안만 받아요 (MVP 범위)',
            '언제든 끌 수 있어요 (진행 중인 제안이 있으면 응답한 뒤)']
    li = ''.join('<li style="display: flex; gap: 8px; align-items: flex-start; font-size: 12px; line-height: 1.5; color: %s">%s<span>%s</span></li>'
                 % (SUB2, icon('check', OK, 12, 3), x) for x in info)
    radio = lambda val, title, desc, checked, style: (
        '<label style="%s"><input type="radio" name="intent"%s style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 2px 0 0; flex-shrink: 0">'
        '<span style="display: flex; flex-direction: column; gap: 3px"><b style="font-size: 14px; display: flex; gap: 6px; align-items: center">%s</b>'
        '<span style="font-size: 12px; line-height: 1.5; color: #4A4F5C">%s</span></span></label>' % (style, checked, title, desc))
    on_t, on_d = '받기', '옆자리 관객이 좌석 교환을 제안할 수 있어요.'
    off_t = '받지 않기 <span style="font-size: 11px; font-weight: 700; color: #3A26C4; background: #E9E5FF; padding: 2px 6px; border-radius: 4px">기본값</span>'
    off_d = '켜기 전에는 어떤 제안도 나에게 전송되지 않아요.'
    st_on = 'display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border-radius: 14px; border: 1.5px solid #5B3DF5; background: #F7F5FF'
    st_off = 'display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border-radius: 14px; border: 1px solid #E6E8EC; background: #FFFFFF'
    static_r = radio('on', on_t, on_d, '', st_off) + radio('off', off_t, off_d, ' checked', st_on)
    demo_r = (radio('on', on_t, on_d, ' data-act="intent" data-val="on" checked="{{onChecked}}"', '{{onStyle}}')
              + radio('off', off_t, off_d, ' data-act="intent" data-val="off" checked="{{offChecked}}"', '{{offStyle}}'))
    main = ''.join([
        B_TAG,
        '<div style="display: flex; gap: 6px; flex-wrap: wrap">%s%s</div>' % (EXP_TAG, tag('서비스 설계 가정', PRIMARY_DARK, SOFT2)),
        B3.box('<span style="font-size: 12px; font-weight: 500; color: #5F6370">내 티켓</span><span style="font-size: 13px; font-weight: 700">{{myTicket}}</span>', pad='10px 14px', gap=3),
        '<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px"><h2 style="margin: 0; font-size: 16px; font-weight: 700">교환 제안 받기</h2>'
        '<sc-if value="{{statusOn}}">%s</sc-if><sc-if value="{{statusOff}}">%s</sc-if></div>' % (badge('ok', '{{statusText}}', 11), badge('mute', '{{statusText}}', 11)),
        demo_only(static_r, demo_r),
        '<sc-if value="{{dirty}}"><p %s>{{dirtyText}}</p></sc-if>' % STATUS_P,
        '<sc-if value="{{hasMsg}}"><p role="status" style="margin: 0; font-size: 13px; line-height: 1.5; font-weight: 700; color: #1F7A4D">{{msg}}</p></sc-if>',
        '<sc-if value="{{locked}}"><p style="margin: 0; font-size: 12px; line-height: 1.5; color: #4A4F5C">%s{{lockText}}</p></sc-if>' % LOCK,
        '<sc-if value="{{hasProposal}}"><button type="button" data-act="toReceive" style="height: 44px; border-radius: 12px; font-family: inherit; font-size: 14px; '
        'font-weight: 700; background: #FFFFFF; color: #3A26C4; border: 1.5px solid #5B3DF5">{{proposalText}} →</button></sc-if>',
        B3.box("<b style=\"font-size: 13px\">'교환 제안 받기'와 '제안 수락'은 달라요</b>"
               '<ul style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 6px">%s</ul>' % li, pad='12px 14px', gap=7),
    ])
    footer = ('<button type="button" data-act="intentSave" style="height: 50px; border-radius: 14px; font-family: inherit; font-size: 15px; font-weight: 700; '
              'background: #5B3DF5; color: #FFFFFF; border: 0">설정 저장</button>')
    write('pair/PairIntent.dc.html', screen('옆자리 교환 제안 설정', '옆자리 교환 제안 설정', main, footer=footer, gap=10))
    patch('pair/PairIntent.dc.html', [], key='intent')


def build_receive():
    old = read('pair/PairReceive.dc.html')
    close = re.search(r'<button aria-label="닫기".*?</button>', old, flags=re.S).group(0)
    banner = ('<sc-if value="{{responded}}"><div role="status" style="border-radius: 14px; padding: 12px 14px; display: flex; flex-direction: column; gap: 4px; '
              'background: #F5F6F8; border: 1.5px solid #DADDE3"><div style="display: flex; align-items: center; gap: 8px">%s<b style="font-size: 14px">{{statusTitle}}</b></div>'
              '<span style="font-size: 12px; line-height: 1.5; color: #4A4F5C">{{statusText}}</span></div></sc-if>'
              % ''.join('<sc-if value="{{k_%s}}">%s</sc-if>' % (k, badge(k, '{{statusBadge}}', 11))
                        for k in ['ok', 'plan', 'no', 'mute', 'need']))
    proposal = ''.join([
        '<div style="display: flex; flex-direction: column; gap: 6px"><h2 style="margin: 0; font-size: 20px; font-weight: 700; line-height: 1.4">다른 좌석으로 옮기자는<br>교환 제안이에요</h2>'
        '<p style="margin: 0; font-size: 13px; line-height: 1.5; color: #4A4F5C">{{from}} 같은 R석이라 추가 결제는 없어요. '
        "'교환 제안 받기'를 켠 경우에만 받는 알림이에요 (서비스 설계 가정).</p></div>",
        '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px">%s%s</div>' % (
            ticket_row('지금 내 좌석', '{{mine}}'), ticket_row('바뀔 좌석 · 같은 회차', '{{offer}}', accent=True)),
        B3.box(cmp_head('지금', '바뀐 뒤', '72px 1fr auto') + '<sc-for list="{{compare}}" as="r">%s</sc-for>' % cmp_tpl('r', '72px 1fr auto'), bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='8px 14px', gap=0),
        '<sc-if value="{{hasCompanion}}">%s</sc-if>' % B3.box(
            '<b style="font-size: 13px">동행 좌석이 분리될 수 있어요</b><p style="margin: 0; font-size: 12px; line-height: 1.5; color: #A3440B; font-weight: 700">{{companionText}}</p>'
            '<span style="font-size: 11px; color: #4A4F5C">{{companionPolicy}}</span>', bg=WARN_BG, pad='10px 14px', gap=4),
        banner,
        B3.para('교환은 예매처 안에서 처리된다고 가정했어요. 송금이나 연락은 필요 없어요. 응답 기한은 가상 규칙이에요.', 12, SUB),
    ])
    empty = ('<div role="status" style="border: 1.5px dashed #C9CDD5; background: #F5F6F8; border-radius: 14px; padding: 16px; display: flex; flex-direction: column; gap: 6px">'
             '<b style="font-size: 15px">도착한 교환 제안이 없어요</b><span style="font-size: 13px; line-height: 1.5; color: #4A4F5C">{{emptyText}}</span></div>')
    main = B_TAG + '<sc-if value="{{noProposal}}">%s</sc-if><sc-if value="{{hasProposal}}">%s</sc-if>' % (empty, proposal)
    footer = ('<sc-if value="{{canRespond}}"><p style="margin: 0; font-size: 12px; line-height: 1.5; color: #4A4F5C">{{respondNote}}</p>'
              '<div style="display: flex; gap: 10px"><button type="button" data-act="recvDecline" style="width: 112px; height: 54px; border: 1px solid #8B909C; border-radius: 14px; '
              'background: #FFFFFF; font-family: inherit; font-size: 15px; font-weight: 700; color: #4A4F5C">거절</button>'
              '<button type="button" data-act="recvAccept" style="flex: 1; height: 54px; border-radius: 14px; background: #5B3DF5; color: #FFFFFF; border: 0; '
              'font-family: inherit; font-size: 16px; font-weight: 700">제안 수락</button></div></sc-if>')
    html = screen('좌석 교환 제안', '좌석 교환 제안', main, footer=footer, gap=10)
    html = sub1(html, B3.BACK_SPAN, demo_only(close, B3.BACK_BTN), 'PairReceive')
    write('pair/PairReceive.dc.html', html)
    patch('pair/PairReceive.dc.html', [], key='receive')


# ================================================================ 공용 상태 화면 (일반 교환·연석 교환)
def tl_template():
    done = ('<span style="width: 22px; height: 22px; border-radius: 11px; background: #1F7A4D; display: flex; align-items: center; justify-content: center; flex-shrink: 0">%s</span>'
            % icon('check', '#FFFFFF', 12, 3.5))
    now = ('<span style="width: 22px; height: 22px; border-radius: 11px; border: 2px solid #5B3DF5; background: #FFFFFF; box-sizing: border-box; display: flex; align-items: center; '
           'justify-content: center; flex-shrink: 0"><span style="width: 8px; height: 8px; border-radius: 4px; background: #5B3DF5"></span></span>')
    todo = '<span style="width: 22px; height: 22px; border-radius: 11px; border: 2px solid #DADDE3; background: #FFFFFF; box-sizing: border-box; flex-shrink: 0"></span>'
    li = ('<li style="position: relative; display: flex; gap: 12px; align-items: flex-start; padding-bottom: 12px">'
          '<sc-if value="{{s.hasLine}}"><span style="position: absolute; left: 10px; top: 24px; bottom: -8px; width: 2px; background: #E6E8EC"></span></sc-if>'
          '<sc-if value="{{s.done}}">%s</sc-if><sc-if value="{{s.now}}">%s</sc-if><sc-if value="{{s.todo}}">%s</sc-if>'
          '<span style="display: flex; flex-direction: column; gap: 1px"><span style="font-size: 14px; font-weight: 700; color: {{s.color}}">{{s.label}} '
          '<span style="font-size: 11px; font-weight: 500; color: {{s.color}}">· {{s.stText}}</span></span>'
          '<span style="font-size: 12px; line-height: 1.45; color: #5F6370">{{s.sub}}</span></span></li>' % (done, now, todo))
    return '<ol aria-label="진행 단계" style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column"><sc-for list="{{steps}}" as="s">%s</sc-for></ol>' % li


def patch_shared():
    rel = 'states/StatusSent.dc.html'
    t = read(rel)
    t = sub1(t, B3.panel('상대방 행동 시뮬레이션', [('상대방 수락', 'simAccept', 'primary'), ('상대방 거절', 'simDecline', 'bad')]), '', rel)
    t, n = re.subn(r'<ol aria-label="진행 단계".*?</ol>', lambda m: tl_template(), t, count=1, flags=re.S)
    if n != 1:
        sys.exit(rel + ': 타임라인 없음')
    t = sub1(t, '>상대방이 검토하는 동안 내 티켓은 그대로 유효해요.<', '>{{sub}}<', rel)
    write(rel, t)
    patch(rel, [], key='sent', dv=B3.DEFAULTS)
    rel = 'states/StatusAccepted.dc.html'
    t = read(rel)
    t = sub1(t, B3.panel('다음 단계 진행', [('최종 확인 시작', 'toFinal', 'primary')]), '', rel)
    for a, b in [('>상대방 수락</span>', '>상대방 제안 수락</span>'), ('>상대방이 수락했어요<', '>상대방이 제안을 수락했어요<'),
                 ('후보 발견 <span', '후보 확인 <span'), ('제안 전송 <span', '교환 제안 보내기 <span'), ('내 수락(동의) 완료', '비교 화면에서 내 동의 완료'),
                 ('상대방 수락 <span', '제안 수락 <span'), ('양쪽이 모두 수락했어요', '상대방이 제안을 수락했어요')]:
        t = sub1(t, a, b, rel)
    write(rel, t)
    print('컴포넌트:', rel)
    rel = 'states/StatusFinal.dc.html'
    t = read(rel)
    t = sub1(t, B3.panel('최종 확인 결과 시뮬레이션', [('최종 확인 성공', 'simOk', 'primary'), ('최종 확인 실패', 'simFail', 'bad')]), '', rel)
    write(rel, t)
    print('컴포넌트:', rel)
    rel = 'exceptions/ExCancelled.dc.html'
    t = read(rel)
    t = sub1(t, '>교환 신청을 취소했어요<', '>{{title}}<', rel)
    t = sub1(t, '>진행 중이던 제안은 닫혔어요. 상대방에게는 &#39;취소됨&#39;으로 보인다고 가정했어요 (서비스 설계 가정). 내 티켓은 그대로 유효해요.<', '>{{body}}<', rel)
    t = sub1(t, '>교환 다시 신청</button>', '>{{primary}}</button>', rel)
    t = sub1(t, '>예매 상세로</button>', '>{{secondary}}</button>', rel)
    write(rel, t)
    patch(rel, [], key='cancelled', dv=B3.DEFAULTS)


def mark_disabled():
    """비활성 버튼: 색상만이 아니라 잠금 아이콘·점선 테두리로도 구분한다."""
    pat = re.compile(r'(<button\b[^>]*?)background: #E6E8EC; color: #8B909C; border: 0([^>]*>)')
    for p in sorted(COMP.glob('*/*.dc.html')):
        t = p.read_text(encoding='utf-8')
        n2 = pat.sub(lambda m: m.group(1) + 'background: #EEF0F3; color: #5F6370; border: 1.5px dashed #9AA0AC' + m.group(2) + LOCK, t)
        if n2 != t:
            p.write_text(n2, encoding='utf-8')
            print('비활성 버튼 표시:', p.relative_to(COMP))


# ================================================================ 페이지: 공용 로직 · 시연 제어판 · 알림 영역
PAGE_LOGIC = r'''
var INITIAL = __INITIAL__;
var HOSTS = __HOSTS__;
var ROLES = __ROLES__;
var TITLES = __TITLES__;
__STORE__
var ROLE_HOST = {};
for (var rk in ROLES) ROLE_HOST[ROLES[rk]] = +rk;
function topOf(stacks, i) { var s = (i === undefined || i === null) ? null : stacks[i]; return s ? s[s.length - 1] : null; }
function applyNav(stacks, i, nav) {
if (i === undefined || i === null || !nav) return;
var s = stacks[i];
if (nav.push && HOSTS[i].indexOf(nav.push) >= 0 && s[s.length - 1] !== nav.push) { s.push(nav.push); }
else if (nav.reset) { var r = nav.reset.filter(function (x) { return HOSTS[i].indexOf(x) >= 0; }); stacks[i] = r.length ? r : [INITIAL[i]]; }
else if (nav.pop && s.length > 1) { s.pop(); }
}
function focusEl(el) { if (el && el.focus) { try { el.focus({ preventScroll: true }); } catch (err) { /* 무시 */ } } }
class Component extends DCLogic {
constructor(props) {
super(props);
this.state = { stacks: INITIAL.map(function (s) { return [s]; }), demo: ENGINE.initialState() };
}
navigate(i, e) {
var t = e && e.target;
var hostEl = t && t.closest ? t.closest('[data-nav-host]') : null;
// 체험 폰(신청자·수신자): data-act 가 붙은 버튼·입력은 상태 변경으로 처리한다 (입력 요소는 기본 동작 유지)
if (ROLES[i] && t && t.closest) {
var actEl = t.closest('[data-act]');
if (actEl && !actEl.disabled) {
if (actEl.tagName !== 'INPUT') e.preventDefault();
this.dispatch({ type: actEl.getAttribute('data-act'), val: actEl.getAttribute('data-val'), row: actEl.getAttribute('data-row'), checked: !!actEl.checked, role: ROLES[i] }, hostEl, i);
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
}, function () { if (moved) focusEl(hostEl); });
}
// 시연 제어판 (폰 밖): 상대방 계정·예매처 처리 결과를 정하는 시뮬레이션 전용 조작
control(e) {
var t = e && e.target;
var el = t && t.closest ? t.closest('[data-act]') : null;
var panel = t && t.closest ? t.closest('[data-demo-ctl]') : null;
if (!el || el.disabled) return;
e.preventDefault();
if (el.getAttribute('data-act') === 'demoReset') { this.resetDemo(panel); return; }
this.dispatch({ type: el.getAttribute('data-act'), val: el.getAttribute('data-val'), role: 'ctl' }, panel, null);
}
resetDemo(keepFocus) {
this.setState(function (st) {
var stacks = st.stacks.map(function (x) { return x.slice(); });
for (var hk in ROLES) stacks[hk] = [INITIAL[hk]];
return { stacks: stacks, demo: ENGINE.reset ? ENGINE.reset(st.demo) : ENGINE.initialState() };
}, function () { focusEl(keepFocus); });
}
dispatch(action, el, src) {
var moved = false;
this.setState(function (st) {
var stacks = st.stacks.map(function (x) { return x.slice(); });
action.screen = topOf(stacks, src === null ? ROLE_HOST.A : src);
action.screenA = topOf(stacks, ROLE_HOST.A);
action.screenB = topOf(stacks, ROLE_HOST.B);
var r = ENGINE.reduce(st.demo, action);
applyNav(stacks, ROLE_HOST.A, r.nav);
applyNav(stacks, ROLE_HOST.B, r.navB);
moved = src === null ? true : JSON.stringify(stacks[src]) !== JSON.stringify(st.stacks[src]);
return { stacks: stacks, demo: r.state };
}, function () {
// 화면이 바뀌면 누른 요소가 사라지므로 그 폰 틀(또는 제어판)로 포커스를 옮긴다. 제어판은 누른 버튼이 남아 있으면 그대로 둔다
if (src === null) { if (el && !el.contains(document.activeElement)) focusEl(el); }
else if (moved) focusEl(el);
});
}
keydown(i, e) {
if (e && e.key === 'Escape') {
if (ROLES[i]) { this.resetDemo(e.currentTarget); return; }
this.setState(function (st) {
var stacks = st.stacks.map(function (x) { return x.slice(); });
stacks[i] = [INITIAL[i]];
return { stacks: stacks };
});
}
}
renderVals() {
var self = this;
var stacks = (this.state && this.state.stacks) || INITIAL.map(function (s) { return [s]; });
var demo = ENGINE.views(this.state.demo, true);
var v = { nosubmit: function (e) { if (e && e.preventDefault) e.preventDefault(); }, demo: demo, ctlView: demo.ctl,
ctl: function (e) { self.control(e); },
ctlKey: function (e) { if (e && e.key === 'Escape') self.resetDemo(e.currentTarget); } };
INITIAL.forEach(function (_, i) {
var cur = stacks[i][stacks[i].length - 1];
HOSTS[i].forEach(function (s) { v['v_' + i + '_' + s] = s === cur ? 'block' : 'none'; });
v['nav_' + i] = function (e) { self.navigate(i, e); };
v['key_' + i] = function (e) { self.keydown(i, e); };
// 화면 제목과 상태만 짧게 알린다 (화면 전체를 다시 읽지 않음)
if (ROLES[i]) v['live_' + i] = (TITLES[cur] || cur) + ' 화면. ' + ((ROLES[i] === 'B' ? demo.statusB : demo.statusA) || '');
});
return v;
}
}
'''

SR_ONLY = 'position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0'
RESET_STY = ('height: 30px; padding: 0 10px; border-radius: 9px; font-family: inherit; font-size: 12px; font-weight: 700; background: #FFFFFF; '
             'color: #191B22; border: 1.5px solid #191B22')
DEMO_TAG = ('<span style="font-size: 11px; font-weight: 900; letter-spacing: 1px; color: #FFFFFF; background: #191B22; padding: 3px 7px; border-radius: 6px; '
            'flex-shrink: 0">DEMO</span>')


def titles():
    out = {}
    for p in COMP.glob('*/*.dc.html'):
        m = re.search(r'<h1[^>]*>([^<]*)', p.read_text(encoding='utf-8'))
        if m:
            out[p.name.replace('.dc.html', '')] = m.group(1).strip()
    return out


def page_code(t, roles, engine_var, stores):
    hosts = json.loads(re.search(r'var HOSTS = (\[.*?\]);', t).group(1))
    initial = json.loads(re.search(r'var INITIAL = (\[.*?\]);', t).group(1))
    return hosts, initial, lambda h, i: (PAGE_LOGIC.replace('__INITIAL__', json.dumps(i, ensure_ascii=False))
                                         .replace('__HOSTS__', json.dumps(h, ensure_ascii=False))
                                         .replace('__ROLES__', json.dumps(roles)).replace('__TITLES__', json.dumps(titles(), ensure_ascii=False))
                                         .replace('__STORE__', stores + '\nvar ENGINE = %s;' % engine_var))


def store_src():
    s3 = B3.STORE.read_text(encoding='utf-8').replace("if (typeof module !== 'undefined') module.exports = DEMO;", '')
    sp = C3.PAIR.read_text(encoding='utf-8').replace("if (typeof module !== 'undefined') module.exports = PAIR;", '')
    return s3, sp


def set_script(t, code):
    if '</' in code:
        sys.exit('로직에 </ 가 있어 스크립트가 끊길 수 있음')
    sc0 = t.index('<script type="text/x-dc"')
    sc1 = t.index('>', sc0) + 1
    sc2 = t.index('</script>', sc1)
    return t[:sc1] + code + t[sc2:]


def live(i):
    return '<p aria-live="polite" data-live="%d" style="%s">{{live_%d}}</p>' % (i, SR_ONLY, i)


def patch_page_exchange():
    p = SRC / 'pages/p07-ui-exchange/page.html'
    t = p.read_text(encoding='utf-8')
    s3, _ = store_src()
    hosts, initial, mk = page_code(t, {'0': 'A'}, 'DEMO', s3)
    t = set_script(t, mk(hosts, initial))
    cap_old = ('<figcaption style="display: flex; flex-direction: column; gap: 6px"><b style="font-size: 17px; color: #FFFFFF">예매 상세</b>'
               '<span style="font-size: 15px; line-height: 1.55; color: #E3DDFF">교환 가능한 공연인지 먼저 알려줘요. 이 폰은 직접 눌러 체험할 수 있어요 (데모)</span></figcaption>')
    panel = ('<section data-demo-ctl="" tabIndex="-1" onclick="{{ctl}}" onkeydown="{{ctlKey}}" aria-label="시연 제어판 (실제 서비스 기능 아님)" style="outline: none; margin-left: auto; '
             'width: 560px; flex-shrink: 0; background: #F5F6F8; border: 2px dashed #191B22; border-radius: 18px; padding: 12px 16px; display: flex; flex-direction: column; gap: 8px">'
             '<div style="display: flex; align-items: center; gap: 8px">%s<b style="flex: 1; font-size: 15px; color: #191B22">시연 제어판 · 실제 서비스 기능이 아니에요</b>'
             '<button type="button" data-act="demoReset" style="%s">처음부터 다시</button></div>'
             '<p aria-live="polite" style="margin: 0; font-size: 14px; line-height: 1.45; color: #191B22">1번 폰 체험 · {{ctlView.hint}}</p>'
             '<sc-if value="{{ctlView.hasButtons}}"><div style="display: flex; flex-wrap: wrap; gap: 8px"><sc-for list="{{ctlView.buttons}}" as="b">'
             '<button type="button" data-act="{{b.act}}" style="{{b.style}}">{{b.label}}</button></sc-for></div></sc-if></section>' % (DEMO_TAG, RESET_STY))
    hdr = t.index('</h1>\n</div>\n') + len('</h1>\n</div>\n')
    t = t[:hdr] + panel + '\n' + t[hdr:]
    t = sub1(t, cap_old, cap_old.replace('<figcaption style="display: flex; flex-direction: column; gap: 6px">',
                                          '<figcaption style="display: flex; flex-direction: column; gap: 6px; position: relative">').replace('</figcaption>', live(0) + '</figcaption>'), 'p07-ui-exchange')
    p.write_text(t, encoding='utf-8')
    print('페이지: p07-ui-exchange (시연 제어판 · 알림 영역)')


HOST2 = ['PairIntent', 'PairReceive']


def patch_page_pair():
    p = SRC / 'pages/p08-ui-pair/page.html'
    t = p.read_text(encoding='utf-8')
    m = re.search(r'(<div data-nav-host="2"[^>]*>)((?:<form [^>]*><dc-import [^>]*></dc-import></form>)+)(</div>)', t)
    forms = ''.join('<form data-nav-screen="%s" onsubmit="{{nosubmit}}" style="display: {{v_2_%s}}; margin: 0"><dc-import name="%s" hint-size="390px,844px" demo="{{demo}}"></dc-import></form>'
                    % (s, s, s) for s in HOST2)
    t = t[:m.start(2)] + forms + t[m.end(2):]
    s3, sp = store_src()
    hosts, initial, mk = page_code(t, {'0': 'A', '2': 'B'}, 'PAIR', s3 + '\n' + sp)
    hosts[2] = HOST2
    initial[2] = 'PairIntent'
    t = set_script(t, mk(hosts, initial))
    # 캡션: 1번 폰(신청자) · 3번 폰(수신자) · 4번 폰 문구
    reps = [
        ('<figcaption style="display: flex; flex-direction: column; gap: 6px"><b style="font-size: 17px; color: #FFFFFF">교환 방식 선택</b>'
         '<span style="font-size: 15px; line-height: 1.55; color: #E3DDFF">떨어진 2장을 고르면 연석 만들기(실험 기능)를 안내해요. 이 폰은 직접 눌러 체험할 수 있어요 (데모)</span></figcaption>',
         '<figcaption style="display: flex; flex-direction: column; gap: 6px; position: relative"><b style="font-size: 17px; color: #FFFFFF">신청자 화면 · 교환 방식 선택</b>'
         '<span style="font-size: 15px; line-height: 1.55; color: #E3DDFF">7열 12번·11열 4번 보유. 직접 눌러 체험할 수 있어요 (데모)</span>' + live(0) + '</figcaption>'),
        ('<b style="font-size: 17px; color: #FFD2AE">옆자리 관객의 화면</b><span style="font-size: 15px; line-height: 1.55; color: #E3DDFF">받는 쪽이 판단할 정보를 첫 문장에 둬요</span>',
         '<b style="font-size: 17px; color: #FFD2AE">수신자 화면 · 11열 5번 관객</b><span style="font-size: 15px; line-height: 1.55; color: #E3DDFF">'
         "'교환 제안 받기'를 켜야 제안이 도착해요. 직접 눌러 체험할 수 있어요 (데모)</span>" + live(2)),
        ('<span style="font-size: 15px; line-height: 1.55; color: #E3DDFF">다른 후보에게 보낸 제안은 자동으로 닫혀요</span>',
         '<span style="font-size: 15px; line-height: 1.55; color: #E3DDFF">최종 확인을 통과해야 교환 완료로 표시해요</span>'),
        ('제안 수신에 동의한 관객에게', "'교환 제안 받기'를 켠 관객에게"),
    ]
    for a, b in reps:
        t = sub1(t, a, b, 'p08-ui-pair')
    if t.count('<figcaption style="display: flex; flex-direction: column; gap: 6px">') < 1:
        pass
    # 3번 폰 figcaption 에 position 추가 (알림 영역 위치 기준)
    i2 = t.index('수신자 화면 · 11열 5번 관객')
    fc = t.rfind('<figcaption style="display: flex; flex-direction: column; gap: 6px">', 0, i2)
    t = t[:fc] + '<figcaption style="display: flex; flex-direction: column; gap: 6px; position: relative">' + t[fc + len('<figcaption style="display: flex; flex-direction: column; gap: 6px">'):]
    # 오른쪽 카드 아래: 시연 제어판
    panel = ('<section data-demo-ctl="" tabIndex="-1" onclick="{{ctl}}" onkeydown="{{ctlKey}}" aria-label="시연 제어판 (실제 서비스 기능 아님)" style="outline: none; margin-top: auto; '
             'background: #F5F6F8; border: 2px dashed #191B22; border-radius: 18px; padding: 12px 16px; display: flex; flex-direction: column; gap: 8px">'
             '<div style="display: flex; align-items: center; gap: 8px">%s<b style="flex: 1; font-size: 15px; color: #191B22">시연 제어판 · 실제 서비스 기능이 아니에요</b>'
             '<button type="button" data-act="demoReset" style="%s">처음부터 다시</button></div>'
             '<p aria-live="polite" style="margin: 0; font-size: 14px; line-height: 1.45; color: #191B22">{{ctlView.hint}}</p>'
             '<div role="group" aria-label="11열 5번 티켓 상황: {{ctlView.profileNote}}" style="display: flex; align-items: center; flex-wrap: wrap; gap: 6px">'
             '<span title="{{ctlView.profileNote}}" style="font-size: 13px; font-weight: 700; color: #4A4F5C; margin-right: 2px">11열 5번 티켓 상황</span>'
             '<sc-for list="{{ctlView.profiles}}" as="p"><button type="button" data-act="profile" data-val="{{p.val}}" aria-pressed="{{p.pressed}}" disabled="{{p.disabled}}" style="{{p.style}}">{{p.label}}</button></sc-for></div>'
             '<sc-if value="{{ctlView.hasButtons}}"><div style="display: flex; flex-wrap: wrap; gap: 8px"><sc-for list="{{ctlView.buttons}}" as="b">'
             '<button type="button" data-act="{{b.act}}" style="{{b.style}}">{{b.label}}</button></sc-for></div></sc-if></section>' % (DEMO_TAG, RESET_STY))
    kd = t.index('KEY DECISION')
    sec_end = t.index('</section>', kd)
    t = t[:sec_end] + panel + t[sec_end:]
    p.write_text(t, encoding='utf-8')
    print('페이지: p08-ui-pair (수신자 체험 폰 · 시연 제어판 · 알림 영역)')
    bp = SRC / 'bundle.json'
    b = json.loads(bp.read_text(encoding='utf-8'))
    pg = b['pages']['p08-ui-pair']
    have = {a['ext_id'] for a in pg['assets']}
    react_idx = next(i for i, u in enumerate(pg['ext_resources_order']) if any(a['uuid'] == u and a['kind'] == 'vendor' for a in pg['assets']))
    for n in ['PairIntent']:
        ext = './%s.dc.html' % n
        if ext in have:
            continue
        u = str(uuidlib.uuid4())
        src = B3.comp_src(n)
        pg['assets'].append(dict(uuid=u, mime='text/html', compressed=True, kind='component', src=src, ext_id=ext,
                                 sha256=sha256((SRC / src).read_bytes()).hexdigest()))
        pg['ext_resources_order'].insert(react_idx, u)
    bp.write_text(json.dumps(b, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('번들 명세: p08-ui-pair 에 PairIntent 추가')


def patch_state_flow_board():
    """P07 상태 흐름 보드의 연석 문구를 용어 기준에 맞춘다."""
    p = SRC / 'pages/p06b-state-flow/page.html'
    t = p.read_text(encoding='utf-8')
    n0 = t
    for a, b in [('제안 수신에 동의한(교환 의향 등록) 관객만 후보가 돼요', "'교환 제안 받기'를 켠 관객만 후보가 돼요"),
                 ('의향 없으면 제안 안 보내요', '켜지 않으면 제안을 보내지 않아요'),
                 ('수신자 사전 의향', '교환 제안 받기 (사전 의향)')]:
        if t.count(a) == 1:
            t = t.replace(a, b)
        else:
            print('  (P07 문구 없음, 건너뜀):', a)
    if t != n0:
        p.write_text(t, encoding='utf-8')
        print('페이지: p06b-state-flow (연석 용어)')
    # 상태 이름 칩: '상대방 수락' → '제안 수락' (수신자의 개별 동의). '제안 전송'은 보낸 상태의 이름으로 둔다
    for page in ['p06b-state-flow', 'p07c-status', 'p09b-state-components']:
        q = SRC / 'pages' / page / 'page.html'
        s = q.read_text(encoding='utf-8')
        n = s.count('>상대방 수락<')
        if n:
            q.write_text(s.replace('>상대방 수락<', '>제안 수락<'), encoding='utf-8')
            print('페이지: %s (상태 이름 %d곳)' % (page, n))


if __name__ == '__main__':
    patch_mode()
    patch_seat()
    build_adjacency()
    build_warn()
    patch_results()
    build_intent()
    build_receive()
    patch_shared()
    mark_disabled()
    patch_page_exchange()
    patch_page_pair()
    patch_state_flow_board()
