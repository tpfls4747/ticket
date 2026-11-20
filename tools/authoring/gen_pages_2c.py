"""STEP 2C 신규 보드(페이지) 생성 + bundle.json / 루트 템플릿 등록 + 표지·P10 보정 (1회성).

기존 10개 페이지는 그대로 두고, 같은 1920x1080 보드 형식의 보조 보드 6개를 해당 섹션 뒤에 끼워 넣는다.
"""
import json
import re
import sys
import uuid as uuidlib
from hashlib import sha256
from pathlib import Path
from dc_kit import *

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
SUPPORT = '__SUPPORT__'


# ---------------------------------------------------------------- 보드 공통 틀
def page_html(title, numeral, pill, h1, body, footer_label, bg='#F7F7FA'):
    return f'''<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8">
<title>{title}</title>
<script src="{SUPPORT}"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&amp;display=swap">
<style>
body{{margin:0}}
a{{color:#5B3DF5}}a:hover{{color:#4328D9}}
</style>
</helmet>
<div style="width: 1920px; height: 1080px; box-sizing: border-box; padding: 88px 120px 56px; background: {bg}; font-family: 'Noto Sans KR', sans-serif; color: #191B22; display: flex; flex-direction: column; gap: 36px; overflow: hidden">
<div style="display: flex; align-items: flex-start; gap: 32px">
<span aria-hidden="true" style="font-size: 128px; font-weight: 900; line-height: 0.82; color: #DCD5FF; letter-spacing: -4px">{numeral}</span>
<div style="display: flex; flex-direction: column; gap: 14px">
<span style="align-self: flex-start; font-size: 14px; font-weight: 700; letter-spacing: 2px; color: #5B3DF5; background: #E9E5FF; padding: 6px 14px; border-radius: 999px">{pill}</span>
<h1 style="margin: 0; font-size: 48px; font-weight: 900; line-height: 1.25; letter-spacing: -1px">{h1}</h1>
</div>
</div>
{body}
<div style="display: flex; justify-content: space-between; align-items: center; font-size: 14px; color: #6B7080"><span style="display: flex; align-items: center; gap: 10px"><span aria-hidden="true" style="display: flex; gap: 3px"><span style="width: 10px; height: 10px; border-radius: 3px; background: #5B3DF5"></span><span style="width: 10px; height: 10px; border-radius: 3px; background: #5B3DF5"></span></span>좌석·회차 교환 UX/UI</span><span>{footer_label}</span></div>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script="" data-props="{{&quot;$preview&quot;:{{&quot;width&quot;:1920,&quot;height&quot;:1080}}}}">
class Component extends DCLogic {{
renderVals() {{
return {{}};
}}
}}
</script>


</body></html>'''


def fig(n, comp, name, desc, line=True, warn=False):
    if warn:
        circle = ('<span style="width: 32px; height: 32px; border-radius: 16px; background: #FFB37A; color: #5A2A06; font-size: 15px; font-weight: 900; '
                  'display: flex; align-items: center; justify-content: center; flex-shrink: 0">!</span>')
        title_c = '#FFD2AE'
    else:
        circle = ('<span style="width: 32px; height: 32px; border-radius: 16px; background: #FFFFFF; color: #5B3DF5; font-size: 15px; font-weight: 900; '
                  'display: flex; align-items: center; justify-content: center; flex-shrink: 0">%s</span>' % n)
        title_c = '#FFFFFF'
    ln = '<span style="flex: 1; height: 2px; background: #8E7BFA; margin-right: -52px"></span>' if line else ''
    return (f'<figure style="margin: 0; width: 226px; display: flex; flex-direction: column; gap: 16px">\n'
            f'<div style="display: flex; align-items: center; gap: 10px">{circle}{ln}</div>\n'
            f'<div style="width: 226px; height: 490px; border-radius: 22px; overflow: hidden; background: #FFFFFF; box-shadow: 0 18px 40px rgba(18, 8, 70, 0.35)">'
            f'<div style="width: 390px; height: 844px; transform: scale(0.58); transform-origin: top left"><dc-import name="{comp}" hint-size="390px,844px"></dc-import></div></div>\n'
            f'<figcaption style="display: flex; flex-direction: column; gap: 6px"><b style="font-size: 17px; color: {title_c}">{name}</b>'
            f'<span style="font-size: 15px; line-height: 1.55; color: #E3DDFF">{desc}</span></figcaption>\n</figure>')


def figures(items, gap=52):
    out = []
    for i, it in enumerate(items):
        n, comp, name, desc = it[:4]
        warn = len(it) > 4 and it[4] == 'warn'
        out.append(fig(n, comp, name, desc, line=(i < len(items) - 1), warn=warn))
    return '<div style="background: #5B3DF5; border-radius: 32px; padding: 36px 32px; display: flex; gap: %dpx; min-height: 0">%s</div>' % (gap, '\n'.join(out))


def panel(label, headline, inner):
    return ('<section style="flex: 1; background: #FFFFFF; border-radius: 32px; padding: 32px; display: flex; flex-direction: column; gap: 16px; min-width: 0">'
            '<span style="align-self: flex-start; font-size: 13px; font-weight: 700; letter-spacing: 2px; color: #FFFFFF; background: #191B22; padding: 6px 12px; border-radius: 999px">%s</span>'
            '<h2 style="margin: 0; font-size: 24px; font-weight: 700; line-height: 1.4">%s</h2>%s</section>' % (label, headline, inner))


def rule_list(items):
    rows = ''.join('<li style="display: flex; gap: 10px; align-items: flex-start; font-size: 16px; line-height: 1.55; color: #2B2E36">'
                   '<span style="width: 8px; height: 8px; border-radius: 4px; background: #5B3DF5; margin-top: 9px; flex-shrink: 0"></span><span>%s</span></li>' % t for t in items)
    return '<ul style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 12px">%s</ul>' % rows


def row_board(left, right=''):
    return '<div style="flex: 1; display: flex; gap: 24px; min-height: 0">%s%s</div>' % (left, right)


# ---------------------------------------------------------------- 보드 정의
PAGES = {}   # slug -> dict(title, html, comps)

PAGES['p07b-conditions-match'] = dict(title='UI 조건·양방향 매칭·비교', comps=['Eligibility', 'ConditionsCast', 'MatchCheck', 'Compare'], html=page_html(
    'UI 조건·양방향 매칭·비교', '06', 'UI DESIGN · A-2 · 자격 확인 · 조건 · 매칭 · 비교',
    '조건은 <span style="color: #5B3DF5">양쪽을 따로</span> 확인해요',
    row_board(figures([
        (1, 'Eligibility', '교환 자격 확인', '가능 · 확인 필요 · 불가를 텍스트와 함께 보여줘요'),
        (2, 'ConditionsCast', '조건 설정 · 캐스팅 공연', '중요도를 고르기 전에는 &#39;무관&#39;으로 처리하지 않아요'),
        (3, 'MatchCheck', '양방향 조건 확인', '한쪽만 맞으면 매칭 완료가 아니에요'),
        (4, 'Compare', '교환 전후 비교', '정보가 없으면 추정하지 않고 확인 필요로 표시해요'),
    ]), panel('DESIGN RULES', '후보 발견 ≠ 매칭 완료 ≠ 교환 완료', rule_list([
        '<b>필수</b>가 맞지 않으면 후보에 올리지 않아요',
        '<b>선호</b>가 다르면 후보로 두고 차이를 설명해요',
        '<b>무관</b>은 비교하지 않아요',
        '미입력은 &#39;무관&#39;이 아니라 <b>선택 필요</b>예요 (기본값)',
        '내 조건과 상대 조건을 <b>각각</b> 확인해요',
        '캐스팅은 캐스팅이 있는 공연에서만 보여줘요',
        '판정과 데이터는 <b>시연용</b>이에요. 실제 예매처 정책 검증 결과가 아니에요 (서비스 설계 가정)',
    ]))), '<b style="color: #191B22">07</b> / 10 · A-2'))

PAGES['p07c-status'] = dict(title='UI 교환 처리 상태', comps=['StatusSent', 'StatusAccepted', 'StatusFinal', 'Done'], html=page_html(
    'UI 교환 처리 상태', '06', 'UI DESIGN · A-3 · 처리 상태',
    '수락과 완료는 <span style="color: #5B3DF5">다른 상태</span>예요',
    row_board(figures([
        (1, 'StatusSent', '제안 전송 · 상대방 검토', '내가 동의하고 제안을 보냈어요. 내 티켓은 그대로예요'),
        (2, 'StatusAccepted', '상대방 수락', '수락은 완료가 아니에요. 최종 확인이 남아 있어요'),
        (3, 'StatusFinal', '최종 확인 중', '실패하면 원 티켓 유지가 목표예요 (목표 UX)'),
        (4, 'Done', '교환 완료 (모의)', '최종 확인을 통과한 뒤에만 완료를 표시해요'),
    ]), panel('10 STATES', '처리 상태 10가지', '<div style="display: flex; flex-wrap: wrap; gap: 10px">%s</div>%s' % (
        ''.join(badge(k, t, 14) for k, t in [('plan', '교환 신청'), ('plan', '후보 발견'), ('plan', '제안 전송'), ('wait', '상대방 검토'), ('ok', '상대방 수락'),
                                              ('wait', '최종 확인 중'), ('done', '교환 완료'), ('no', '거절'), ('cancel', '취소'), ('fail', '실패')]),
        rule_list(['양쪽이 <b>명시적으로 수락</b>하고 <b>최종 확인</b>을 통과해야 교환 완료를 표시해요',
                   '거절·취소·실패에서는 내 티켓이 그대로예요 (실패는 <b>목표 UX·시스템 요구사항</b>)',
                   '이 보드의 상태는 모두 <b>시연용 모의 데이터</b>예요. 실제 처리 기능은 없어요'])))), '<b style="color: #191B22">07</b> / 10 · A-3'))

PAGES['p07d-exceptions'] = dict(title='UI 교환 예외 상황', comps=['ExMismatch', 'ExNoCandidate', 'ExDeclined', 'ExCancelled', 'ExTicketChanged', 'ExFinalFailed'], html=page_html(
    'UI 교환 예외 상황', '06', 'UI DESIGN · A-4 · 예외 상황',
    '막혀도 <span style="color: #5B3DF5">다음 행동</span>을 알려줘요',
    row_board(figures([
        ('!', 'ExMismatch', '필수 조건 불일치', '후보에서 제외하고 이유를 보여줘요', 'warn'),
        ('!', 'ExNoCandidate', '후보 없음', '신청은 유지하고 조건을 넓히는 방법을 알려줘요', 'warn'),
        ('!', 'ExDeclined', '상대방 거절', '내 티켓은 그대로예요', 'warn'),
        ('!', 'ExCancelled', '신청자 취소', '진행 중인 제안을 닫아요', 'warn'),
        ('!', 'ExTicketChanged', '티켓 상태 변경', '진행을 멈추고 상태를 다시 확인해요', 'warn'),
        ('!', 'ExFinalFailed', '최종 확인 실패', '원 티켓 유지가 목표예요 (목표 UX)', 'warn'),
    ], gap=24).replace('padding: 36px 32px', 'padding: 36px 32px; flex: 1'), ''), '<b style="color: #191B22">07</b> / 10 · A-4'))

PAGES['p08b-pair-states'] = dict(title='UI 연석 의향·인접·동의·상태', comps=['PairIntent', 'PairAdjacency', 'PairWarn', 'PairAccepted', 'PairDeclined'], html=page_html(
    'UI 연석 의향·인접·동의·상태', '07', 'UI DESIGN · B-2 · 실험 기능 · 수요 미검증',
    '연석은 <span style="color: #5B3DF5">의향 확인</span>부터 시작해요',
    row_board(figures([
        (1, 'PairIntent', '제안 수신 의향', '기본값은 받지 않기예요. 켜기 전에는 제안이 가지 않아요'),
        (2, 'PairAdjacency', '인접 · 자격 확인', '번호가 이어져도 배치도로 따로 확인해요'),
        (3, 'PairWarn', '제안 전 확인', '전후 좌석 비교와 동행석 분리 가능성을 알려줘요'),
        (4, 'PairAccepted', '수락 · 최종 확인 전', '수락은 완료가 아니에요'),
        (5, 'PairDeclined', '수신자 거절', '거절할 권한은 수신자에게 있어요'),
    ], gap=36).replace('padding: 36px 32px', 'padding: 36px 32px; flex: 1'), ''), '<b style="color: #191B22">08</b> / 10 · B-2'))


# ---- P06b 상태 흐름 -------------------------------------------------------------------------
def state_box(kind, name, desc, ticket):
    return ('<div style="flex: 1; min-width: 0; background: #FFFFFF; border: 1px solid #E6E8EC; border-radius: 16px; padding: 14px; display: flex; flex-direction: column; gap: 8px">'
            '<span>%s</span><span style="font-size: 13px; line-height: 1.45; color: #4A4F5C">%s</span>'
            '<span style="font-size: 12px; font-weight: 700; color: #5F6370">%s</span></div>' % (badge(kind, name, 14), desc, ticket))


ARROW = '<span aria-hidden="true" style="display: flex; align-items: center; flex-shrink: 0">%s</span>' % icon('arrow', '#8B909C', 20, 2.2)


def chain(boxes):
    out = []
    for i, b in enumerate(boxes):
        out.append(b)
        if i < len(boxes) - 1:
            out.append(ARROW)
    return '<div style="display: flex; gap: 8px; align-items: stretch">%s</div>' % ''.join(out)


def lane(label_html, right, inner, bg, border):
    return ('<section style="background: %s; border: 1px solid %s; border-radius: 28px; padding: 20px 24px; display: flex; flex-direction: column; gap: 14px">'
            '<div style="display: flex; align-items: center; justify-content: space-between; gap: 16px">%s<span style="font-size: 14px; color: #4A4F5C">%s</span></div>%s</section>'
            % (bg, border, label_html, right, inner))


LANE_A = ('<span style="display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 700; color: #3A26C4">'
          '<span style="width: 24px; height: 24px; border-radius: 8px; background: #5B3DF5; color: #FFFFFF; font-size: 13px; display: flex; align-items: center; justify-content: center">A</span>좌석·회차 교환 (핵심 기능)</span>')
LANE_B = ('<span style="display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 700; color: #A3440B">'
          '<span style="width: 24px; height: 24px; border-radius: 8px; background: #D9620F; color: #FFFFFF; font-size: 13px; display: flex; align-items: center; justify-content: center">B</span>연석 만들기 (실험 기능 · 수요 미검증)</span>')

main_chain = chain([
    state_box('plan', '교환 신청', '조건을 등록하고 후보를 찾아요', '내 티켓: 유효'),
    state_box('plan', '후보 발견', '양방향 조건 확인을 통과해요. 매칭 완료가 아니에요', '내 티켓: 유효'),
    state_box('plan', '제안 전송', '내가 동의(수락)하고 제안을 보내요', '내 티켓: 유효'),
    state_box('wait', '상대방 검토', '상대방이 제안을 확인해요', '내 티켓: 유효'),
    state_box('ok', '상대방 수락', '상대방도 동의했어요. 아직 완료가 아니에요', '내 티켓: 유효'),
    state_box('wait', '최종 확인 중', '티켓·조건·정책 상태를 마지막으로 확인해요', '내 티켓: 유효'),
    state_box('done', '교환 완료', '확인을 통과한 뒤에만 표시해요 (시연용 모의)', '새 티켓 (모의)'),
])
end_row = ('<div style="display: flex; gap: 12px; align-items: stretch">'
           + ''.join('<div style="flex: 1; display: flex; gap: 10px; align-items: center; background: #FFFFFF; border: 1px dashed #C4C8D0; border-radius: 14px; padding: 10px 14px">%s<span style="font-size: 13px; line-height: 1.45; color: #4A4F5C">%s</span></div>' % (badge(k, t, 13), d)
                     for k, t, d in [('no', '거절', '상대방 검토 중 거절 → 내 티켓 그대로'),
                                     ('cancel', '취소', '신청자가 최종 확인 전에 취소 → 내 티켓 그대로'),
                                     ('fail', '실패', '최종 확인 실패 → 원 티켓 유지가 목표 (목표 UX·시스템 요구사항)')]) + '</div>')

pair_chain = chain([
    state_box('plan', '수신자 사전 의향', '제안 수신에 동의한(교환 의향 등록) 관객만 후보가 돼요', '의향 없으면 제안 안 보내요'),
    state_box('plan', '인접·자격 확인', '배치도로 인접 여부와 교환 자격을 따로 확인해요', '확인 못하면 제안 보류'),
    state_box('need', '동행석 분리 안내', '거절·실패하면 떨어진 좌석이 유지될 수 있어요', '전후 좌석 비교 + 내 동의'),
    '<div style="flex: 2; min-width: 0; background: #FFFFFF; border: 1px solid #E6E8EC; border-radius: 16px; padding: 14px; display: flex; flex-direction: column; gap: 8px">'
    '<span style="display: flex; gap: 6px; flex-wrap: wrap">%s%s%s%s</span><span style="font-size: 13px; line-height: 1.45; color: #4A4F5C">이후는 일반 교환과 같은 상태로 진행해요. 수신자는 언제든 거절할 수 있고, 수락은 완료가 아니에요</span></div>'
    % (badge('plan', '제안 전송', 12), badge('wait', '상대방 검토', 12), badge('ok', '상대방 수락', 12), badge('wait', '최종 확인 중', 12)),
])

exc_row = ('<div style="display: flex; gap: 10px">' + ''.join(
    '<div style="flex: 1; min-width: 0; background: #FFFFFF; border: 1px solid #E6E8EC; border-radius: 14px; padding: 12px; display: flex; flex-direction: column; gap: 6px">%s<b style="font-size: 14px">%s</b><span style="font-size: 12px; line-height: 1.45; color: #4A4F5C">%s</span></div>' % (badge(k, bt, 12), t, d)
    for k, bt, t, d in [('no', '후보 제외', '필수 조건 불일치', '후보 목록에 올리지 않고 이유를 보여줘요'),
                        ('mute', '후보 없음', '교환 가능한 후보 없음', '신청은 유지하고 조건을 넓히도록 안내해요'),
                        ('no', '거절', '상대방 제안 거절', '내 티켓은 그대로예요'),
                        ('cancel', '취소', '신청자 취소', '진행 중인 제안을 닫아요'),
                        ('need', '일시 중지', '티켓 상태 변경', '진행을 멈추고 상태를 다시 확인해요'),
                        ('fail', '실패', '최종 확인 실패', '원 티켓 유지가 목표예요 (목표 UX)')]) + '</div>')

PAGES['p06b-state-flow'] = dict(title='상태 흐름', comps=[], html=page_html(
    '상태 흐름', '05', 'USER FLOW · 상태 · 예외',
    '수락과 완료는 <span style="color: #5B3DF5">다른 상태</span>예요',
    '<div style="flex: 1; display: flex; flex-direction: column; gap: 14px; min-height: 0">'
    + lane(LANE_A, '양쪽이 명시적으로 수락하고 최종 확인을 통과해야 &#39;교환 완료&#39;를 표시해요', main_chain + end_row, '#FAF9FF', '#ECE8FF')
    + lane(LANE_B, '일반 교환의 앞에 의향·인접·동행석 확인 단계가 붙어요', pair_chain, '#FFF9F4', '#FBE6D6')
    + lane('<span style="font-size: 16px; font-weight: 700">예외 상황 → 상태</span>', '모든 상태와 데이터는 시연용 모의예요. 실제 매칭·처리 기능은 없어요', exc_row, '#FFFFFF', '#E6E8EC')
    + '</div>', '<b style="color: #191B22">06</b> / 10 · 상태', bg='#FFFFFF'))


# ---- P09b 상태 컴포넌트 ---------------------------------------------------------------------
def comp_card(title, inner):
    return ('<section style="background: #FFFFFF; border-radius: 28px; padding: 26px; display: flex; flex-direction: column; gap: 16px; min-width: 0">'
            '<h2 style="margin: 0; font-size: 20px; font-weight: 700">%s</h2>%s</section>' % (title, inner))


def desc_row(b, d):
    return ('<div style="display: flex; flex-direction: column; gap: 5px"><span>%s</span><span style="font-size: 13px; line-height: 1.5; color: #4A4F5C">%s</span></div>' % (b, d))


card1 = comp_card('교환 자격', ''.join([
    desc_row(badge('ok', '교환 가능', 14), '시연 판정: 허용 공연 · 신청 기간 안 · 다음 행동은 조건 등록'),
    desc_row(badge('need', '확인 필요', 14), '정보가 없으면 추정하지 않고 표시 · 확인 전에는 신청이 열리지 않아요 (설계 가정)'),
    desc_row(badge('no', '교환 불가', 14), '허용하지 않는 공연 · 신청 불가 · 공연 안내 확인을 안내해요'),
    '<p style="margin: 0; font-size: 12px; line-height: 1.5; color: #5F6370">판정은 시연용 가상 데이터예요. 실제 예매처 정책 검증 결과가 아니에요.</p>']))

card2 = comp_card('조건 중요도', ''.join([
    desc_row(importance_seg('필수'), '맞지 않으면 후보에서 제외해요'),
    desc_row(importance_seg('선호'), '맞지 않아도 후보로 두고 차이를 설명해요'),
    desc_row(importance_seg('무관'), '비교하지 않아요'),
    desc_row(importance_seg(None) + '', '기본값 · 고르기 전에는 &#39;무관&#39;으로 처리하지 않아요'),
    '<div style="display: flex; flex-wrap: wrap; gap: 6px">%s</div>' % ''.join(badge(k, t, 12) for k, t in [('ok', '충족'), ('plan', '선호와 달라요'), ('no', '필수 불일치'), ('need', '확인 필요'), ('mute', '비교 안 함')])]))

STATE_DESC = [('plan', '교환 신청', '조건 등록, 후보 탐색'), ('plan', '후보 발견', '매칭 완료 아님'), ('plan', '제안 전송', '내 수락 완료'),
              ('wait', '상대방 검토', '상대가 확인 중'), ('ok', '상대방 수락', '아직 완료 아님'), ('wait', '최종 확인 중', '티켓·조건 재확인'),
              ('done', '교환 완료', '확인 통과 후 (모의)'), ('no', '거절', '내 티켓 그대로'), ('cancel', '취소', '내 티켓 그대로'), ('fail', '실패', '원 티켓 유지가 목표')]
card3 = comp_card('처리 상태', '<div style="display: flex; flex-direction: column; gap: 9px">%s</div>' % ''.join(
    '<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px">%s<span style="font-size: 12px; color: #5F6370; text-align: right">%s</span></div>' % (badge(k, t, 13), d) for k, t, d in STATE_DESC))

card4 = comp_card('시연·가정 표기', ''.join([
    '<div style="display: flex; flex-direction: column; gap: 10px">%s</div>' % ''.join(
        '<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px">%s<span style="font-size: 12px; color: #5F6370; text-align: right">%s</span></div>' % (t, d)
        for t, d in [(SIM_TAG, '모의 데이터 화면'), (ASSUME_TAG, 'NOL 약관으로 확인 못한 기능'), (VIRTUAL_TAG, '12시간·1회 등 예시 값'), (NEED_TAG, '정보·정책 미확인'),
                     (GOAL_TAG, '목표 UX·시스템 요구사항'), (tag('실험 기능 · 수요 미검증', WARN_FG, WARN_BG), '연석 만들기')]),
    '<div style="height: 1px; background: #EEF0F3"></div>',
    '<b style="font-size: 14px">전후 비교 표시</b><div style="display: flex; gap: 6px; flex-wrap: wrap">%s%s%s</div>' % (badge('plan', '다름', 12), badge('mute', '같음', 12), badge('need', '확인 필요', 12)),
    '<p style="margin: 0; font-size: 12px; line-height: 1.5; color: #5F6370">색만으로 구분하지 않고 아이콘과 텍스트를 함께 써요.</p>']))

PAGES['p09b-state-components'] = dict(title='컴포넌트 상태', comps=[], html=page_html(
    '컴포넌트 상태', '08', 'COMPONENTS · 상태 확장',
    '상태를 <span style="color: #5B3DF5">텍스트와 함께</span> 읽히게 해요',
    '<div style="flex: 1; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 20px; min-height: 0">%s%s%s%s</div>' % (card1, card2, card3, card4),
    '<b style="color: #191B22">09</b> / 10 · 상태'))


# ================================================================== 번들 등록
def new_uuid():
    return str(uuidlib.uuid4())


def asset(uid, src, kind, ext_id, mime, content):
    return dict(uuid=uid, mime=mime, compressed=True, kind=kind, src=src, ext_id=ext_id, sha256=sha256(content).hexdigest())


def comp_src(name):
    for d in ('exchange', 'pair', 'states', 'exceptions'):
        if (SRC / 'components' / d / ('%s.dc.html' % name)).exists():
            return 'components/%s/%s.dc.html' % (d, name)
    raise SystemExit('컴포넌트를 찾지 못함: ' + name)


def add_pages(bundle):
    insert_after = {'p06-user-flow': ['p06b-state-flow'], 'p07-ui-exchange': ['p07b-conditions-match', 'p07c-status', 'p07d-exceptions'],
                    'p08-ui-pair': ['p08b-pair-states'], 'p09-components': ['p09b-state-components']}
    sup = SRC / 'vendor/dc-runtime/support.js'
    rea = SRC / 'vendor/react/react.production.min.js'
    red = SRC / 'vendor/react/react-dom.production.min.js'
    for slug, pg in PAGES.items():
        tpl_path = SRC / 'pages' / slug / 'page.html'
        tpl_path.parent.mkdir(parents=True, exist_ok=True)
        html = pg['html'].replace(SUPPORT, '{{asset:vendor/dc-runtime/support.js}}')
        tpl_path.write_text(html, encoding='utf-8')
        assets = [asset(new_uuid(), 'vendor/dc-runtime/support.js', 'runtime', None, 'text/javascript', sup.read_bytes())]
        ext = []
        for c in pg['comps']:
            a = asset(new_uuid(), comp_src(c), 'component', './%s.dc.html' % c, 'text/html', (SRC / comp_src(c)).read_bytes())
            assets.append(a)
            ext.append(a['uuid'])
        a1 = asset(new_uuid(), 'vendor/react/react.production.min.js', 'vendor', 'https://cdn.jsdelivr.net/npm/react@18.3.1/umd/react.production.min.js', 'text/javascript', rea.read_bytes())
        a2 = asset(new_uuid(), 'vendor/react/react-dom.production.min.js', 'vendor', 'https://cdn.jsdelivr.net/npm/react-dom@18.3.1/umd/react-dom.production.min.js', 'text/javascript', red.read_bytes())
        assets += [a1, a2]
        ext += [a1['uuid'], a2['uuid']]
        bundle['pages'][slug] = dict(title=pg['title'], template='pages/%s/page.html' % slug, assets=assets, ext_resources_order=ext)
    order = bundle['root']['page_order']
    for after, slugs in insert_after.items():
        idx = next(i for i, p in enumerate(order) if p['slug'] == after)
        for k, s in enumerate(slugs):
            u = new_uuid()
            order.insert(idx + 1 + k, dict(slug=s, uuid=u))
            bundle['root']['manifest_compressed'][u] = True


BOARD_TITLES = {'p06b-state-flow': 'P06-B 상태 흐름 (STEP 2C 추가)', 'p07b-conditions-match': 'P07-B 자격·조건·양방향 매칭·비교 (STEP 2C 추가)',
                'p07c-status': 'P07-C 교환 처리 상태 (STEP 2C 추가)', 'p07d-exceptions': 'P07-D 예외 상황 (STEP 2C 추가)',
                'p08b-pair-states': 'P08-B 연석 의향·인접·동의·상태 (STEP 2C 추가)', 'p09b-state-components': 'P09-B 상태 컴포넌트 (STEP 2C 추가)'}


def update_root_template(bundle):
    t_path = SRC / 'root' / 'template.html'
    t = t_path.read_text(encoding='utf-8')
    for after, slug in [('p06-user-flow', 'p06b-state-flow'), ('p07-ui-exchange', 'p07b-conditions-match'), ('p07-ui-exchange', 'p07c-status'),
                        ('p07-ui-exchange', 'p07d-exceptions'), ('p08-ui-pair', 'p08b-pair-states'), ('p09-components', 'p09b-state-components')]:
        pass
    # 섹션을 순서대로 다시 구성한다 (기존 10개 섹션 문자열은 그대로 보존)
    sections = re.findall(r'<section class="board">.*?</section>', t, flags=re.S)
    by_slug = {re.search(r'\{\{page:([^}]+)\}\}', s).group(1): s for s in sections}
    head = t[:t.index('<section class="board">')]
    tail = t[t.rindex('</section>') + len('</section>'):]
    body = []
    for p in bundle['root']['page_order']:
        s = p['slug']
        if s in by_slug:
            body.append(by_slug[s])
        else:
            ttl = BOARD_TITLES[s]
            body.append('<section class="board"><h2>%s</h2><iframe src="about:blank#{{page:%s}}" title="%s" width="1920" height="1080" loading="eager" style="width:1920px;height:1080px"></iframe></section>' % (ttl, s, ttl))
    t_path.write_text(head + '\n'.join(body) + tail, encoding='utf-8')


def update_cover(bundle):
    """표지: 일반 좌석·회차 교환을 핵심으로, 연석은 실험 기능 칩으로."""
    pg = SRC / 'pages' / 'p01-cover' / 'page.html'
    t = pg.read_text(encoding='utf-8')
    reps = [
        ('떨어진 좌석을<br>나란히.', '원하는 좌석,<br>원하는 회차로.'),
        ('예매 앱 안에서 관객끼리 좌석·회차를<br>바꾸는 교환 기능 · 연석 만들기는 별도 실험',
         '예매 앱 안에서 관객끼리 좌석·회차를<br>조건으로 맞춰 바꾸는 교환 기능'),
        ('<dc-import name="PairSeat" hint-size="390px,844px">', '<dc-import name="Request" hint-size="390px,844px">'),
        ('<dc-import name="PairDone" hint-size="390px,844px">', '<dc-import name="Match" hint-size="390px,844px">'),
        ('UX/UI 개인 프로젝트</span>',
         'UX/UI 개인 프로젝트</span>\n<span style="font-size: 17px; font-weight: 500; color: #FFFFFF; border: 1.5px dashed #B7A9FF; padding: 9px 18px; border-radius: 999px">연석 만들기 · 실험 기능</span>'),
    ]
    for old, new in reps:
        if t.count(old) != 1:
            raise SystemExit('표지 치환 실패: %s (%d)' % (old[:40], t.count(old)))
        t = t.replace(old, new)
    pg.write_text(t, encoding='utf-8')
    # 표지의 리소스: PairSeat/PairDone -> Request/Match (uuid 는 유지)
    for a in bundle['pages']['p01-cover']['assets']:
        for old, new in (('PairSeat', 'Request'), ('PairDone', 'Match')):
            if a['ext_id'] == './%s.dc.html' % old:
                a['ext_id'] = './%s.dc.html' % new
                a['src'] = comp_src(new)
                a['sha256'] = sha256((SRC / a['src']).read_bytes()).hexdigest()


def update_p10():
    pg = SRC / 'pages' / 'p10-retrospective' / 'page.html'
    t = pg.read_text(encoding='utf-8')
    m = re.search(r'<li [^>]*>(?:(?!</li>).)*인터뷰·사용성 테스트는 아직 하지 않았고, 연석 수요와 제안 피로도도 검증 전이에요</span></li>', t, flags=re.S)
    if not m:
        raise SystemExit('P10 항목을 찾지 못함')
    li = m.group(0)
    new_li = li.replace('인터뷰·사용성 테스트는 아직 하지 않았고, 연석 수요와 제안 피로도도 검증 전이에요',
                        '새 상태·예외 화면은 정적 시연이에요. 실제 매칭·알림·티켓 처리와 클릭 전환은 아직 없어요')
    t = t.replace(li, li + new_li)
    pg.write_text(t, encoding='utf-8')


if __name__ == '__main__':
    bpath = SRC / 'bundle.json'
    bundle = json.loads(bpath.read_text(encoding='utf-8'))
    if 'p07b-conditions-match' in bundle['pages']:
        sys.exit('이미 등록되어 있습니다. (이 스크립트는 1회성입니다)')
    add_pages(bundle)
    update_root_template(bundle)
    update_cover(bundle)
    update_p10()
    bpath.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('보드 %d개 추가, 표지·P10 보정 완료' % len(PAGES))
