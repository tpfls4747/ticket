"""STEP 2C 신규 폰 화면(.dc.html) 생성 (1회성). 결과는 src/components/ 에 쓰인다.

모든 화면은 '시연용 모의 데이터'이며 실제 NOL 데이터·API·정책 검증 결과가 아니다.
버튼은 동작이 없는 정적 요소이고 링크(<a href>)는 쓰지 않는다 (기존 링크 문제는 STEP 3).
"""
from pathlib import Path
from dc_kit import *

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'src' / 'components'

MINE = '12.20 (일) 18:00 · 3회차 · R석 B구역 7열 12번'
CAND = '12.21 (월) 14:00 · 4회차 · R석 A구역 5열 8번'


def put(path, html):
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding='utf-8')


def box(inner, bg=BG, pad='12px 14px', gap=6, border=''):
    return ('<div style="background: %s; border-radius: 14px; padding: %s; display: flex; flex-direction: column; gap: %dpx; %s">%s</div>'
            % (bg, pad, gap, border, inner))


def p(text, size=12, color=SUB2, weight=400):
    return '<p style="margin: 0; font-size: %dpx; line-height: 1.5; font-weight: %d; color: %s">%s</p>' % (size, weight, color, text)


def title_block(b, headline, sub=''):
    return ('<div style="display: flex; flex-direction: column; gap: 8px"><span style="align-self: flex-start">%s</span>'
            '<h2 style="margin: 0; font-size: 21px; font-weight: 700; line-height: 1.4">%s</h2>%s</div>' % (b, headline, p(sub) if sub else ''))


def chip(text, selected=False):
    if selected:
        st = 'border: 1.5px solid #5B3DF5; background: #F0EDFF; font-weight: 700; color: #3A26C4'
    else:
        st = 'border: 1px solid #DADDE3; background: #FFFFFF; font-weight: 500; color: #191B22'
    return ('<button type="button" aria-pressed="%s" style="height: 34px; padding: 0 12px; border-radius: 17px; font-family: inherit; font-size: 13px; %s">%s</button>'
            % ('true' if selected else 'false', st, text))


def checkbox_row(text, checked=False):
    return ('<label style="display: flex; align-items: flex-start; gap: 10px; font-size: 13px; line-height: 1.5; color: %s">'
            '<input type="checkbox"%s style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 0; flex-shrink: 0">%s</label>'
            % (TEXT, ' checked' if checked else '', text))


def li(text, kind='info'):
    ic = {'info': ('info', SUB), 'ok': ('check', OK), 'warn': ('info', WARN_FG), 'bad': ('x', BAD)}[kind]
    return ('<li style="display: flex; gap: 8px; align-items: flex-start; font-size: 12px; line-height: 1.5; color: %s">%s<span>%s</span></li>'
            % (SUB2, icon(ic[0], ic[1], 14, 2.4), text))


def ul(items):
    return '<ul style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 7px">%s</ul>' % ''.join(items)


# ================================================================== A. 교환 자격 확인
def elig_card(name, sub, kind, label, reason, action):
    return ('<section style="border: 1px solid #E6E8EC; border-radius: 16px; padding: 12px 14px; display: flex; flex-direction: column; gap: 7px">'
            '<div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 8px">'
            '<span style="display: flex; flex-direction: column; gap: 2px"><b style="font-size: 14px">%s</b><span style="font-size: 12px; color: %s">%s</span></span>%s</div>'
            '%s%s</section>' % (name, SUB, sub, badge(kind, label), p(reason), action))


eligibility = screen('교환 자격 확인', '교환 자격 확인', ''.join([
    banner('프로토타입 판정 · 가상 데이터로 보여 주는 시연이에요. 실제 예매처 정책을 검증한 결과가 아니에요.', 'plan'),
    elig_card('2026 Blue Hour 단독 콘서트', '12.20 (일) 18:00 · 3회차 · R석 B구역 7열 12번', 'ok', '교환 가능',
              '시연 데이터 기준: 교환을 허용하는 공연으로 표시돼 있고, 신청 기간 안이며, 변경 이력이 없어요.',
              '<div>' + small_btn('교환 조건 등록하기') + '</div>'),
    elig_card('뮤지컬 〈별빛 아래〉 (가상 공연)', '12.26 (토) 19:30 · 1회차 · VIP석 2열 5번', 'need', '확인 필요',
              '교환 허용 여부 정보가 없어요. 없는 정보는 추정하지 않고 &#39;확인 필요&#39;로 표시해요.',
              '<div style="display: flex; flex-direction: column; gap: 6px"><div>' + small_btn('공연 안내에서 확인하기', 'ghost') + '</div>'
              + p('확인되기 전에는 교환 신청이 열리지 않아요 (서비스 설계 가정).', 12, SUB) + '</div>'),
    elig_card('가상 콘서트 〈Night Drive〉', '12.31 (목) 20:00 · 1회차 · S석 C구역 3열 9번', 'no', '교환 불가',
              '시연 데이터에서 교환을 허용하지 않는 공연으로 설정돼 있어요.',
              p('교환 신청을 할 수 없어요. 예매 취소·변경 가능 여부는 공연 안내에서 확인하세요.', 12, SUB)),
]), gap=10)
put('states/Eligibility.dc.html', eligibility)


# ================================================================== B. 조건 설정 (캐스팅 있는 공연)
def cond_row(name, sel, content, warn=''):
    w = ('<div style="display: flex; gap: 6px; align-items: center">%s<span style="font-size: 12px; font-weight: 700; color: %s">중요도를 선택해 주세요</span></div>'
         % (icon('info', WARN_FG, 14, 2.4), WARN_FG)) if warn else ''
    return ('<section style="display: flex; flex-direction: column; gap: 8px; padding-bottom: 10px; border-bottom: 1px solid #EEF0F3">'
            '<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px"><h2 style="margin: 0; font-size: 14px; font-weight: 700">%s</h2>%s</div>'
            '%s%s</section>' % (name, importance_seg(sel), content, w))


def chips(*items):
    return '<div style="display: flex; flex-wrap: wrap; gap: 6px">%s</div>' % ''.join(chip(t, s) for t, s in items)


conditions_cast = screen('교환 조건 설정', '교환 조건 설정', ''.join([
    box('<span style="font-size: 11px; font-weight: 500; color: %s">내 티켓 · 뮤지컬 〈별빛 아래〉 (가상 공연)</span>'
        '<span style="font-size: 13px; font-weight: 700">12.26 (토) 19:30 · 1회차 · VIP석 2열 5번 · 캐스트 A</span>' % SUB, gap=3),
    cond_row('회차·날짜', '필수', chips(('12.26 (토) 14:00', True), ('12.27 (일) 14:00', False))),
    cond_row('좌석 구역', '선호', chips(('VIP석 A구역', True), ('VIP석 B구역', False), ('상관없음', False))),
    cond_row('좌석 열', '선호', '<span style="font-size: 13px; font-weight: 700; color: %s">1열 ~ 5열</span>' % PRIMARY_DARK),
    cond_row('캐스팅 (이 공연에 적용)', None, chips(('캐스트 A', False), ('캐스트 B', True)), warn=True),
    box('<div style="display: flex; gap: 6px; flex-wrap: wrap">%s%s%s</div>' % (importance_tag('필수'), importance_tag('선호'), importance_tag('무관'))
        + p('필수는 맞지 않으면 후보에서 제외, 선호는 맞지 않아도 후보로 두고 차이를 알려줘요, 무관은 비교하지 않아요. '
            '고르지 않은 조건은 &#39;무관&#39;으로 처리하지 않아요.', 12, SUB2), gap=6),
]), footer=cta('중요도를 모두 선택하면 등록할 수 있어요', disabled=True), gap=9)
put('states/ConditionsCast.dc.html', conditions_cast)


# ================================================================== C. 양방향 매칭
match_check = screen('양방향 조건 확인', '양방향 조건 확인', ''.join([
    '<div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap">%s<b style="font-size: 17px">맞을 수 있는 후보를 찾았어요</b></div>' % badge('plan', '후보 발견'),
    box('<span style="font-size: 12px; line-height: 1.45"><b style="color: %s">내 티켓(A)</b> %s</span>'
        '<span style="font-size: 12px; line-height: 1.45"><b style="color: %s">후보 티켓(B)</b> %s</span>' % (SUB, MINE, PRIMARY_DARK, CAND), pad='9px 12px', gap=3),
    box('<b style="font-size: 12px">① 내가 원하는 조건 ↔ 후보의 티켓</b>'
        + result_row_c('회차', '내 조건 12.21 (월) 14:00 · 후보 4회차', '필수', 'ok', '충족')
        + result_row_c('구역', '내 조건 A·B구역 · 후보 A구역', '선호', 'ok', '충족')
        + result_row_c('열', '내 조건 1~10열 · 후보 5열', '선호', 'ok', '충족'), bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='9px 12px', gap=0),
    box('<b style="font-size: 12px">② 후보가 원하는 조건 ↔ 내 티켓</b>'
        + result_row_c('회차', '후보 조건 12.20 (일) 18:00 · 내 티켓 3회차', '필수', 'ok', '충족')
        + result_row_c('구역', '후보 조건 A구역 · 내 티켓 B구역', '선호', 'plan', '선호와 달라요',
                       '필수가 아니라 후보로 남겨요. 후보는 A구역을 선호해요.')
        + result_row_c('열', '후보 조건 없음', '무관', 'mute', '비교 안 함'), bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='9px 12px', gap=0),
    box('<div style="display: flex; gap: 6px; flex-wrap: wrap">%s%s%s</div>' % (badge('ok', '내 필수 충족', 11), badge('ok', '후보 필수 충족', 11), badge('need', '미확인 1건', 11))
        + p('미확인: 후보 티켓의 정책 확인 상태. 아직 &#39;매칭 완료&#39;가 아니고, 한쪽만 맞아도 완료로 표시하지 않아요.', 11, SUB2), bg=SOFT, pad='9px 12px', gap=6),
]), footer=cta('전후 정보 비교하기'), gap=8)
put('states/MatchCheck.dc.html', match_check)


# ================================================================== D. 교환 전후 비교
def cmp_row(label, a, b, mark_kind, mark_text):
    mk = {'plan': badge('plan', mark_text, 11), 'mute': badge('mute', mark_text, 11), 'need': badge('need', mark_text, 11), 'ok': badge('ok', mark_text, 11)}[mark_kind]
    return ('<div style="display: grid; grid-template-columns: 62px 1fr 1fr; gap: 8px; padding: 7px 0; border-top: 1px solid #EEF0F3; align-items: start">'
            '<span style="font-size: 12px; font-weight: 700; color: %s">%s</span>'
            '<span style="font-size: 12px; line-height: 1.4">%s</span>'
            '<span style="display: flex; flex-direction: column; gap: 4px; font-size: 12px; line-height: 1.4; font-weight: 700">%s%s</span></div>'
            % (SUB, label, a, b, mk))


compare = screen('교환 전후 비교', '교환 전후 비교', ''.join([
    p('정보가 없으면 추정하지 않고 &#39;확인 필요&#39;로 표시해요. 시연용 모의 데이터예요.', 12, SUB),
    '<div style="display: flex; flex-direction: column"><div style="display: grid; grid-template-columns: 62px 1fr 1fr; gap: 8px; padding-bottom: 6px">'
    '<span></span><span style="font-size: 11px; font-weight: 700; color: %s">내 티켓 (지금)</span><span style="font-size: 11px; font-weight: 700; color: %s">받게 될 티켓</span></div>' % (SUB, PRIMARY_DARK)
    + cmp_row('공연명', '2026 Blue Hour 단독 콘서트', '2026 Blue Hour 단독 콘서트', 'mute', '같음')
    + cmp_row('날짜·회차', '12.20 (일) 18:00 · 3회차', '12.21 (월) 14:00 · 4회차', 'plan', '다름')
    + cmp_row('구역', 'R석 B구역', 'R석 A구역', 'plan', '다름')
    + cmp_row('열·좌석', '7열 12번', '5열 8번', 'plan', '다름')
    + cmp_row('캐스팅', '해당 없음', '해당 없음', 'mute', '같음')
    + cmp_row('권종·가격', 'R석 · 154,000원 (가상)', 'R석 · 가격 정보 없음', 'need', '확인 필요')
    + cmp_row('정책 확인', '시연 판정: 교환 가능', '정책 확인 상태 없음', 'need', '확인 필요')
    + '</div>',
    checkbox_row('이 조건으로 교환하는 데 동의해요 (내 수락)'),
]), footer=cta('교환 제안 보내기') + p('제안을 보내도 교환은 확정되지 않아요. 상대방이 수락하고 최종 확인을 통과해야 완료돼요.', 12, SUB), gap=10)
put('states/Compare.dc.html', compare)


# ================================================================== E. 처리 상태
ALL = ['교환 신청', '후보 발견', '제안 전송', '상대방 검토', '상대방 수락', '최종 확인 중', '교환 완료']
status_sent = screen('교환 진행 현황', '교환 진행 현황', ''.join([
    title_block(badge('wait', '상대방 검토 중') + ' ' + SIM_TAG, '제안을 보냈어요', '상대방이 검토하는 동안 내 티켓은 그대로 유효해요.'),
    timeline([('교환 신청', '조건 등록 완료', 'done'), ('후보 발견', '양방향 조건 확인 통과', 'done'),
              ('제안 전송', '내 수락(동의) 완료', 'done'), ('상대방 검토', '응답 기한은 가상 규칙이에요 (예: 12시간)', 'now'),
              ('상대방 수락', '상대방도 동의해야 다음으로 가요', 'todo'), ('최종 확인 중', '티켓·조건을 마지막으로 확인해요', 'todo'),
              ('교환 완료', '최종 확인을 통과해야 표시돼요', 'todo')]),
]), footer=cta('제안 취소하기', 'ghost'), gap=14)
put('states/StatusSent.dc.html', status_sent)

status_accepted = screen('교환 진행 현황', '교환 진행 현황', ''.join([
    title_block(badge('ok', '상대방 수락') + ' ' + SIM_TAG, '상대방이 수락했어요'),
    banner('아직 교환이 완료된 것은 아니에요. 최종 확인이 끝나기 전까지 내 티켓은 그대로 유효해요.', 'warn'),
    timeline([('교환 신청', '조건 등록 완료', 'done'), ('후보 발견', '양방향 조건 확인 통과', 'done'),
              ('제안 전송', '내 수락(동의) 완료', 'done'), ('상대방 검토', '검토 완료', 'done'),
              ('상대방 수락', '양쪽이 모두 수락했어요', 'now'), ('최종 확인 중', '다음 단계예요', 'todo'),
              ('교환 완료', '최종 확인을 통과해야 표시돼요', 'todo')]),
]), footer=cta('교환 취소하기 (최종 확인 전)', 'ghost') + p('최종 확인 전 취소 가능 여부는 서비스 설계 가정이에요.', 12, SUB), gap=12)
put('states/StatusAccepted.dc.html', status_accepted)


def check_item(kind, text, sub):
    ic = {'ok': ('check', OK, OK_BG), 'wait': ('clock', WARN_FG, WARN_BG), 'todo': ('dash', SUB, '#F0F1F4')}[kind]
    return ('<li style="display: flex; gap: 10px; align-items: flex-start"><span style="width: 24px; height: 24px; border-radius: 12px; background: %s; display: flex; align-items: center; justify-content: center; flex-shrink: 0">%s</span>'
            '<span style="display: flex; flex-direction: column; gap: 1px"><b style="font-size: 13px">%s</b><span style="font-size: 12px; color: %s">%s</span></span></li>'
            % (ic[2], icon(ic[0], ic[1], 13, 3), text, SUB, sub))


status_final = screen('최종 확인', '최종 확인', ''.join([
    title_block(badge('wait', '최종 확인 중') + ' ' + SIM_TAG, '마지막으로 확인하고 있어요', '이 단계가 끝나야 &#39;교환 완료&#39;가 표시돼요.'),
    '<ul style="margin: 0; padding: 14px; list-style: none; display: flex; flex-direction: column; gap: 12px; border: 1px solid #E6E8EC; border-radius: 16px">'
    + check_item('ok', '두 티켓이 모두 유효한지', '확인됨 (모의)')
    + check_item('ok', '양쪽 수락이 그대로인지', '확인됨 (모의)')
    + check_item('wait', '교환 정책 확인 상태', '확인 중 (모의)')
    + check_item('todo', '새 티켓 준비', '앞 단계가 끝나면 시작해요') + '</ul>',
    box('<div style="display: flex; gap: 6px; align-items: center">%s<b style="font-size: 12px">하나라도 실패하면</b></div>' % GOAL_TAG
        + p('교환은 진행되지 않고 원래 티켓이 유지되는 것을 목표로 해요. 목표 UX와 시스템 요구사항이며, 이 프로토타입은 실제 티켓을 처리하지 않아요.', 12, SUB2), bg=SOFT, gap=6),
]), footer=cta('확인이 끝나면 알려드려요', disabled=True), gap=14)
put('states/StatusFinal.dc.html', status_final)


# ================================================================== F. 예외 상황
def ex_screen(header, b, headline, body, info='', buttons='', note=''):
    return screen(header, header, ''.join([
        title_block(b + ' ' + SIM_TAG, headline, body), info, note]), footer=buttons, gap=14)


def kv(label, value, kind=None, ktext=''):
    right = badge(kind, ktext, 11) if kind else '<b style="font-size: 12px">%s</b>' % value
    return ('<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 0; border-top: 1px solid #EEF0F3">'
            '<span style="display: flex; flex-direction: column; gap: 1px"><span style="font-size: 12px; font-weight: 700">%s</span>%s</span>%s</div>'
            % (label, ('<span style="font-size: 12px; color: %s">%s</span>' % (SUB, value)) if kind else '', right))


put('exceptions/ExMismatch.dc.html', ex_screen(
    '필수 조건 불일치', badge('no', '후보 제외'), '필수 조건이 맞지 않는 후보는 보여주지 않아요',
    '선호 조건은 맞지 않아도 후보로 남기고 차이를 알려줘요. 필수 조건은 내가 직접 바꾸기 전까지 그대로예요.',
    box(result_row('회차', '내 조건 12.21 (월) 14:00 · 후보 티켓 12.20 (일) 14:00', '필수', 'no', '불일치', '이 후보는 후보 목록에 올리지 않았어요.')
        + result_row('구역', '내 조건 A·B구역 · 후보 티켓 A구역', '선호', 'ok', '충족'), bg='#FFFFFF', border='border: 1px solid #E6E8EC', gap=0),
    cta('조건 수정하기') + cta('필수를 선호로 바꿔 보기', 'ghost') + p('중요도는 내가 직접 고른 경우에만 바뀌어요.', 12, SUB)))

put('exceptions/ExNoCandidate.dc.html', ex_screen(
    '교환 가능한 후보 없음', badge('mute', '후보 없음'), '지금은 맞는 후보가 없어요',
    '교환 신청은 유지돼요. 내 티켓은 그대로 유효해요.',
    box('<b style="font-size: 13px">조건을 넓혀 볼 수 있어요</b>' + ul([li('회차를 더 추가해요'), li('구역을 더 추가해요'), li('열 범위를 넓혀요'), li('필수 조건을 선호로 바꿔요 (내가 직접 선택)')])
        + p('새 후보가 생기면 알려드려요 (서비스 설계 가정). 후보가 생긴다고 보장하지는 않아요.', 12, SUB), gap=8),
    cta('조건 수정하기') + cta('교환 신청 취소', 'ghost')))

put('exceptions/ExDeclined.dc.html', ex_screen(
    '상대방 제안 거절', badge('no', '거절'), '상대방이 제안을 거절했어요',
    '거절 사유는 공개되지 않아요. 내 티켓은 그대로 유효해요.',
    box(kv('내 티켓', MINE, 'ok', '변경 없음') + kv('진행 상태', '이 후보와의 교환', 'no', '거절됨'), bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='4px 14px', gap=0),
    cta('다른 후보 찾기') + cta('교환 신청 취소', 'ghost')))

put('exceptions/ExCancelled.dc.html', ex_screen(
    '신청자 취소', badge('cancel', '취소'), '교환 신청을 취소했어요',
    '진행 중이던 제안은 닫혔어요. 상대방에게는 &#39;취소됨&#39;으로 보인다고 가정했어요 (서비스 설계 가정). 내 티켓은 그대로 유효해요.',
    box('<b style="font-size: 13px">다시 신청할 수 있어요</b>' + p('신청 횟수와 간격 제한은 가상 규칙이에요. 공식 정책으로 확인된 내용이 아니에요.', 12, SUB2), gap=6),
    cta('교환 다시 신청') + cta('예매 상세로', 'ghost')))

put('exceptions/ExTicketChanged.dc.html', ex_screen(
    '티켓 상태 변경', badge('need', '확인 필요'), '티켓 상태가 바뀌어 진행을 멈췄어요',
    '내 티켓 또는 후보 티켓이 취소·변경됐을 수 있어요. 상태를 확인할 때까지 제안은 일시 중지돼요.',
    box(kv('내 티켓', MINE, 'ok', '유효') + kv('후보 티켓', CAND, 'need', '상태 확인 필요'), bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='4px 14px', gap=0),
    cta('상태 다시 확인') + cta('교환 신청 취소', 'ghost'),
    note=p('위 상태는 시연용 모의 데이터예요. 실제 예매 시스템에서 티켓 상태를 읽어 온다고 가정하지 않아요.', 12, SUB)))

put('exceptions/ExFinalFailed.dc.html', ex_screen(
    '최종 확인 실패', badge('fail', '실패'), '최종 확인에 실패했어요',
    '교환은 진행되지 않았어요. 원래 티켓이 그대로 유지되는 것을 목표로 설계했어요.',
    box('<div style="display: flex; gap: 6px; align-items: center">%s<b style="font-size: 12px">목표 UX · 시스템 요구사항</b></div>' % GOAL_TAG
        + p('이 프로토타입은 실제 티켓을 처리하지 않아요. 실제 서비스에서는 두 티켓을 한 번에 처리하고, 실패하면 아무것도 바꾸지 않는 기능이 필요해요.', 12, SUB2), bg=SOFT, gap=6)
    + box(kv('내 티켓', MINE, 'ok', '유지 (목표)') + kv('실패 사유 (시연)', '후보 티켓 상태 변경', 'no', '확인 실패'), bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='4px 14px', gap=0),
    cta('내 티켓 확인') + cta('다시 신청', 'ghost')))


# ================================================================== G. 연석 만들기
def radio_card(name, checked, title, desc, default=False):
    border = 'border: 1.5px solid #5B3DF5; background: #F7F5FF' if checked else 'border: 1px solid #E6E8EC; background: #FFFFFF'
    d = ' ' + tag('기본값', PRIMARY_DARK, SOFT2) if default else ''
    return ('<label style="display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border-radius: 14px; %s">'
            '<input type="radio" name="intent"%s style="width: 20px; height: 20px; accent-color: #5B3DF5; margin: 2px 0 0; flex-shrink: 0">'
            '<span style="display: flex; flex-direction: column; gap: 3px"><b style="font-size: 14px; display: flex; gap: 6px; align-items: center">%s%s</b>'
            '<span style="font-size: 12px; line-height: 1.5; color: %s">%s</span></span></label>' % (border, ' checked' if checked else '', title, d, SUB2, desc))


put('pair/PairIntent.dc.html', screen('옆자리 교환 제안 설정', '옆자리 교환 제안 설정', ''.join([
    '<div style="display: flex; gap: 6px; flex-wrap: wrap">%s%s</div>' % (tag('실험 기능 · 수요 미검증', WARN_FG, WARN_BG), ASSUME_TAG),
    box('<span style="font-size: 11px; font-weight: 500; color: %s">내 티켓</span><span style="font-size: 13px; font-weight: 700">12.20 (일) 18:00 · 3회차 · R석 B구역 11열 5번</span>' % SUB, gap=3),
    h2('옆자리 교환 제안 받기'),
    radio_card('intent', False, '받기', '옆자리 관객이 좌석 교환을 제안할 수 있어요.'),
    radio_card('intent', True, '받지 않기', '켜기 전에는 어떤 제안도 나에게 전송되지 않아요.', default=True),
    box('<b style="font-size: 12px">받기를 켜면</b>' + ul([li('같은 가격·등급 좌석의 제안만 받아요 (MVP 범위)'),
                                                            li('제안마다 수락과 거절을 직접 골라요. 거절해도 불이익이 없다고 가정했어요'),
                                                            li('언제든 다시 끌 수 있어요')]), gap=7),
    checkbox_row('내 좌석도 연석 교환 대상으로 등록해요 (교환 의향 등록)'),
]), footer=cta('설정 저장'), gap=11))


def cand_card(nm, res, rows):
    lines = ''.join(
        '<div style="display: flex; justify-content: space-between; align-items: center; gap: 8px">'
        '<span style="font-size: 12px; color: %s">%s</span>%s</div>' % (SUB2, l, b) for l, b in rows)
    return ('<section style="border: 1px solid #E6E8EC; border-radius: 14px; padding: 10px 14px; display: flex; flex-direction: column; gap: 5px">'
            '<div style="display: flex; justify-content: space-between; align-items: center"><b style="font-size: 13px">%s</b>%s</div>%s</section>'
            % (nm, res, lines))


CANDS = [
    ('후보 1 · 11열 5번', badge('ok', '제안 가능', 11), [('제안 수신 의향', badge('ok', '있음', 11)), ('인접 여부 (11열 4번)', badge('ok', '같은 블록 확인 (시연)', 11)), ('교환 자격', badge('ok', '교환 가능 (시연)', 11))]),
    ('후보 2 · 11열 3번', badge('no', '제안 불가', 11), [('제안 수신 의향', badge('no', '없음', 11)), ('인접 여부 (11열 4번)', badge('ok', '같은 블록 확인 (시연)', 11)), ('교환 자격', badge('ok', '교환 가능 (시연)', 11))]),
    ('후보 3 · 7열 13번', badge('need', '제안 보류', 11), [('제안 수신 의향', badge('ok', '있음', 11)), ('인접 여부 (7열 12번)', badge('need', '확인 필요', 11)), ('교환 자격', badge('ok', '교환 가능 (시연)', 11))]),
]

put('pair/PairAdjacency.dc.html', screen('연석 후보 확인', '연석 후보 확인', ''.join([
    banner('좌석 번호가 이어져도 물리적으로 붙어 있다고 판단하지 않아요. 배치도 데이터로 인접 여부를 따로 확인해요 (시연).', 'plan'),
    ticket_row('내 좌석 (떨어져 있어요)', 'R석 B구역 7열 12번 · 11열 4번'),
    ''.join(cand_card(nm, res, rows) for nm, res, rows in CANDS),
    p('의향이 없는 관객에게는 제안을 자동으로 보내지 않아요. 인접 여부를 확인하지 못한 후보는 보류해요 (통로·구역 경계 배치도 데이터가 없는 경우).', 12, SUB),
]), gap=9))

put('pair/PairWarn.dc.html', screen('제안 보내기 전 확인', '제안 보내기 전 확인', ''.join([
    '<div style="display: flex; gap: 6px; flex-wrap: wrap">%s%s</div>' % (tag('실험 기능 · 수요 미검증', WARN_FG, WARN_BG), SIM_TAG),
    ticket_row('내 좌석 (지금)', '7열 12번 · 11열 4번 · 떨어져 있어요'),
    ticket_row('교환이 완료되면', '11열 4번 · 11열 5번 · 나란히 (완료 시에만)', accent=True),
    box('<b style="font-size: 12px">상대 후보 (11열 5번) 좌석 변화</b>' + p('11열 5번 → 7열 12번으로 옮겨요. 좋고 나쁨은 사람마다 달라요.', 12, SUB2), gap=3),
    box('<b style="font-size: 13px">동행 좌석이 분리될 수 있어요</b>' + ul([
        li('제안이 거절되거나 취소되면 지금처럼 떨어진 좌석이 유지돼요', 'warn'),
        li('상대가 수락해도 최종 확인에 실패하면 교환되지 않아요', 'warn'),
        li('교환이 완료되기 전에는 나란히 앉는다고 보장되지 않아요', 'warn'),
        li('상대는 언제든 거절할 수 있어요 (수신자의 권한)')]), bg=WARN_BG, gap=8),
    checkbox_row('위 내용을 확인했어요'),
]), footer=cta('의향을 등록한 옆자리에 제안 보내기'), gap=10))

put('pair/PairAccepted.dc.html', screen('연석 교환 진행 현황', '연석 교환 진행 현황', ''.join([
    title_block(badge('ok', '상대방 수락') + ' ' + SIM_TAG, '옆자리 관객이 수락했어요'),
    banner('아직 교환이 완료된 것은 아니에요. 최종 확인 전까지 내 좌석은 그대로예요.', 'warn'),
    ticket_row('내 좌석 (지금 · 유효)', '7열 12번 · 11열 4번'),
    ticket_row('최종 확인을 통과하면', '11열 4번 · 11열 5번', accent=True),
    timeline([('제안 전송', '내 수락(동의) 완료', 'done'), ('상대방 수락', '옆자리 관객도 수락했어요', 'now'),
              ('최종 확인 중', '다음 단계예요', 'todo'), ('교환 완료', '최종 확인을 통과해야 표시돼요', 'todo')]),
]), footer=p('실패하면 원래 좌석이 유지되는 것을 목표로 해요 (목표 UX·시스템 요구사항).', 12, SUB), gap=12))

put('pair/PairDeclined.dc.html', screen('연석 교환 진행 현황', '연석 교환 진행 현황', ''.join([
    title_block(badge('no', '거절') + ' ' + SIM_TAG, '옆자리 관객이 제안을 거절했어요',
                '수신자는 언제든 거절할 수 있어요. 사유는 공개되지 않아요.'),
    box(kv('내 좌석', '7열 12번 · 11열 4번 (변경 없음)', 'ok', '그대로') + kv('옆자리 후보 1', '11열 5번', 'no', '거절됨'), bg='#FFFFFF', border='border: 1px solid #E6E8EC', pad='4px 14px', gap=0),
    banner('여전히 일행과 떨어진 좌석이에요. 다른 후보를 확인하거나 반대 방향으로 모으는 방법을 볼 수 있어요.', 'info'),
]), footer=cta('다른 후보 확인하기') + cta('반대 방향으로 모으기 보기', 'ghost'), gap=14))

print('신규 화면 생성 완료')
