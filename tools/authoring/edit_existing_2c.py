"""STEP 2C: 기존 컴포넌트의 최소 수정 (1회성). 각 치환은 정확히 지정한 횟수만큼 일치해야 한다.

링크(<a href>)와 기존 구조는 건드리지 않고 문구·상태 표기와 입력 UI만 보강한다.
"""
import re
import sys
from pathlib import Path
from dc_kit import *

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / 'src' / 'components'
LOG = []


def edit(rel, old, new, count=1, note=''):
    p = C / rel
    t = p.read_text(encoding='utf-8')
    n = t.count(old)
    if n != count:
        print('실패: %s 일치 %d회(기대 %d): %s' % (rel, n, count, old[:70]))
        sys.exit(1)
    p.write_text(t.replace(old, new), encoding='utf-8')
    LOG.append((rel, note or old[:40]))


# ---------------------------------------------------------------- Main (예매 상세): 교환 자격 '교환 가능' 상태
edit('exchange/Main.dc.html', '좌석·회차 교환이 가능한 공연이에요 (예시)', '교환 가능 · 시연용 판정')
edit('exchange/Main.dc.html',
     '교환 가능 공연이라고 가정한 예시예요. 같은 가격·등급 좌석끼리 신청할 수 있고, 신청 마감(12.13 (일) 23:59)은 가상 규칙이에요.',
     '가상 데이터로 교환 허용 공연이라고 가정한 예시예요. 실제 예매처 정책 검증 결과가 아니에요. 같은 가격·등급 좌석끼리 신청할 수 있고, 신청 마감(12.13 (일) 23:59)은 가상 규칙이에요.')

# ---------------------------------------------------------------- Request (조건 등록): 중요도 + 캐스팅 행
R = 'exchange/Request.dc.html'
edit(R, 'gap: 24px; padding: 8px 20px 16px; overflow: hidden', 'gap: 13px; padding: 4px 20px 12px; overflow: hidden', note='간격 축소')
edit(R, 'display: flex; align-items: baseline; justify-content: space-between', 'display: flex; align-items: center; justify-content: space-between', count=3)
edit(R, '<span style="font-size: 13px; color: #5F6370">여러 개 선택 가능</span>', importance_seg('필수'), note='회차 중요도(필수)')
edit(R, '<span style="font-size: 13px; color: #5F6370">R석 안에서만</span>', importance_seg('선호'), note='구역 중요도(선호)')
edit(R, '<span style="font-size: 15px; font-weight: 700; color: #3A26C4">1열 ~ 10열</span>',
     '<span style="display: flex; align-items: center; gap: 8px"><span style="font-size: 13px; font-weight: 700; color: #3A26C4">1열 ~ 10열</span>%s</span>' % importance_seg('선호'),
     note='열 중요도(선호)')
edit(R, 'height: 56px; border', 'height: 46px; border', count=4, note='회차 칩 높이 축소')
edit(R, 'height: 44px; padding: 0 18px;', 'height: 38px; padding: 0 16px;', count=4, note='구역 칩 높이 축소')
edit(R, 'gap: 12px">\n<div style="display: flex; align-items: center; justify-content: space-between">',
     'gap: 10px">\n<div style="display: flex; align-items: center; justify-content: space-between">', count=2, note='섹션 간격')
casting_row = ('<section style="display: flex; align-items: center; justify-content: space-between; gap: 8px">'
               '<h2 style="margin: 0; font-size: 16px; font-weight: 700">캐스팅</h2>'
               + tag('이 공연은 해당 없음') + '</section>\n')
note_div = '<div style="background: #F5F6F8; border-radius: 14px; padding: 14px 16px; display: flex; gap: 10px; align-items: flex-start">'
edit(R, note_div, casting_row + note_div, note='캐스팅 행(해당 없음) 추가')
edit(R, '양쪽 수락과 최종 확인이 끝나면 기존 티켓은 무효 처리되고 새 티켓이 발급돼요 (설계 가정). 개인 간 송금은 없어요.',
     '중요도를 고르지 않은 조건은 &#39;무관&#39;으로 처리하지 않아요. 필수는 맞지 않으면 후보에서 제외돼요. 양쪽 수락과 최종 확인이 끝나야 교환이 완료돼요 (서비스 설계 가정).')
edit(R, '교환 대기 등록</a>', '교환 신청 등록</a>')

# ---------------------------------------------------------------- Waiting: 상태 이름을 공통 상태에 맞춤
W = 'exchange/Waiting.dc.html'
edit(W, '>매칭 대기 중<', '>교환 신청 · 후보 탐색 중<')
edit(W, '조건에 맞는 상대를<br>찾고 있어요', '조건에 맞는 후보를<br>찾고 있어요')
edit(W, '상대가 나타나면 알림으로 알려드릴게요. 기다리는 동안에도 내 티켓은 그대로 유효해요.',
     '후보가 나타나면 알려드릴게요 (서비스 설계 가정). 기다리는 동안에도 내 티켓은 그대로 유효해요.')
edit(W, '>상대 찾는 중<', '>후보 탐색 중<')
edit(W, '>새 티켓 발급<', '>최종 확인 후 교환 완료<')
edit(W, '12.19 (토) 19:30, 12.21 (월) 14:00', '12.19 (토) 19:30, 12.21 (월) 14:00 · 필수')
edit(W, '>R석 A·B구역<', '>R석 A·B구역 · 선호<')
edit(W, '>1열 ~ 10열<', '>1열 ~ 10열 · 선호<')

# ---------------------------------------------------------------- Match: 제안을 받은 쪽(상대방 검토) 시점으로 정리
M = 'exchange/Match.dc.html'
edit(M, '조건에 맞는 좌석을<br>찾았어요', '교환 제안이<br>도착했어요')
edit(M, '12.20 (일) 18:00 · B구역 7열 12번</span>\n</div>\n<div style="display: flex; justify-content: center',
     '__MY__</span>\n</div>\n<div style="display: flex; justify-content: center')
edit(M, '12.21 (월) 14:00 · A구역 5열 8번</span>', '12.20 (일) 18:00 · B구역 7열 12번</span>')
edit(M, '__MY__', '12.21 (월) 14:00 · A구역 5열 8번')
# 미니 배치도: 받는 쪽 기준으로 '지금 좌석'은 A구역, '바뀔 좌석'은 B구역
t = (C / M).read_text(encoding='utf-8')
g0 = t.index('<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; width: 100%">')
d1 = t.index('<div style="height: 76px', g0)
d2 = t.index('<div style="height: 76px', d1 + 10)
d3 = t.index('<div style="height: 76px', d2 + 10)
a_html, b_html = t[d1:d2], t[d2:d3]
assert '>A</span>' in a_html and '>B</span>' in b_html
new_a = b_html.replace('>B</span>', '>A</span>')
new_b = a_html.replace('>A</span>', '>B</span>')
(C / M).write_text(t[:d1] + new_a + new_b + t[d3:], encoding='utf-8')
LOG.append((M, '미니 배치도 구역 스타일 교환(받는 쪽 기준)'))
edit(M, '응답 시간(예: 12시간, 가상 규칙) 안에 응답이 없으면 제안이 취소돼요',
     '응답 시간(예: 12시간, 가상 규칙) 안에 응답이 없으면 제안이 취소돼요. 거절해도 불이익이 없다고 가정했어요 (서비스 설계 가정)')

# ---------------------------------------------------------------- Done: 시연용 모의 화면 표기
D = 'exchange/Done.dc.html'
edit(D, '새 티켓이 발급됐어요.<br>입장할 때는 새 모바일 티켓을 보여주세요.',
     '최종 확인을 통과해 새 티켓이 발급됐다고 가정한 모의 화면이에요.<br>입장할 때는 새 모바일 티켓을 보여주세요.')
edit(D, '공연당 1회 제한과 취소 수수료 기준은 프로토타입 가상 규칙이에요. 실제 기준은 공연별 안내 확인이 필요해요.',
     '시연용 모의 화면이에요. 공연당 1회 제한과 취소 수수료 기준은 프로토타입 가상 규칙이고, 실제 기준은 공연별 안내 확인이 필요해요.')

# ---------------------------------------------------------------- 연석: PairSeat / PairReceive / PairDone
S = 'pair/PairSeat.dc.html'
edit(S, '제안 보낼 옆자리</span>', '제안 후보 옆자리</span>')
edit(S, '교환 의향을 등록했거나 제안 수신에 동의한 관객에게만 제안해요 (설계 가정). 동행석이 분리될 수 있어요. 먼저 수락한 관객과 최종 확인 후 교환돼요.',
     '교환 의향을 등록했거나 제안 수신에 동의한 관객에게만 제안해요 (설계 가정). 번호가 이어져도 인접 여부는 배치도로 따로 확인해요. 동행석이 분리될 수 있어요. 수락해도 최종 확인 후에 교환돼요.')
RC = 'pair/PairReceive.dc.html'
edit(RC, '예매처가 직접 교환해 줘서 송금이나 연락이 필요 없어요',
     '교환은 예매처 안에서 처리된다고 가정했어요 (서비스 설계 가정). 송금이나 연락은 필요 없어요')
edit(RC, '다른 관객이 먼저 수락하면 이 제안은 자동으로 닫혀요',
     '거절해도 불이익이 없다고 가정했어요. 수락해도 바로 교환되지 않고 최종 확인을 거쳐요. 다른 관객이 먼저 수락하면 이 제안은 닫혀요')
PD = 'pair/PairDone.dc.html'
edit(PD, '11열 5번 관객이 수락했고 최종 확인을 마쳐<br>교환이 완료됐어요. 새 티켓 2장을 확인하세요.',
     '11열 5번 관객의 수락과 최종 확인을 거쳐<br>교환이 완료됐다고 가정한 모의 화면이에요.')
edit(PD, '11열 3번 관객에게 보낸 제안은 자동으로 취소됐어요.',
     '시연용 모의 화면이에요. 의향을 등록한 다른 후보에게 보낸 제안은 닫혔어요.')

for rel, note in LOG:
    print('수정:', rel, '-', note)
