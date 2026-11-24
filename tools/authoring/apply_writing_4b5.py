"""STEP 4B.5: UX 라이팅·정보 밀도 다듬기 (1회성 적용 스크립트, STEP 4B 커밋 상태에서 실행).

원칙: 한 화면 한 메시지 · 제목은 상태/다음 행동 · 보조 설명 1~2문장 · 행동 중심 버튼 · 이미 보이는 정보는 반복하지 않기.
- 앱 안의 설계 설명('서비스 설계 가정', '목표 UX·시스템 요구사항', '모의 화면이에요' 같은 긴 문장)은 빼고,
  확대 보기 패널의 '설계 메모'(포트폴리오 영역)로 옮긴다. 앱 안에는 짧은 '시연' 표기와 값 옆 '(가상)'만 남긴다.
- 필수 정보는 남긴다: 교환 전후 좌석·회차, 가격·조건 차이, 필수 불일치, 상대 동의, 수락≠완료, 실패·기존 티켓 상태,
  자격·정책 제한, 개인정보·동행, 시뮬레이션 표기.
- 디자인 시스템·레이아웃·기능·매칭 로직은 바꾸지 않는다 (엔진은 문구만).
사용법: python3 tools/authoring/apply_writing_4b5.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import apply_demo_3b as B3            # noqa: E402  (import 시 현재 엔진으로 기본 화면 데이터를 계산)
import apply_pair_3c as C3            # noqa: E402
import apply_ux_4a as U4              # noqa: E402

SRC, COMP = B3.SRC, B3.COMP


def rep(rel, pairs, every=False):
    p = COMP / rel
    t = p.read_text(encoding='utf-8')
    for old, new in pairs:
        n = t.count(old)
        if n == 0 or (n > 1 and not every):
            sys.exit('%s: 치환 대상 %d회 (%s)' % (rel, n, old[:70]))
        t = t.replace(old, new)
    p.write_text(t, encoding='utf-8')


def drop_re(rel, pattern):
    p = COMP / rel
    t = p.read_text(encoding='utf-8')
    t2, n = re.subn(pattern, '', t, count=1, flags=re.S)
    if n != 1:
        sys.exit('%s: 제거 대상 없음 (%s)' % (rel, pattern[:60]))
    p.write_text(t2, encoding='utf-8')


SUB = '<span style="font-size: 12px; line-height: 1.45; color: #5F6370">%s</span>'


# ================================================================ 화면별 문구
def writing():
    # 공통: 시뮬레이션 표기는 짧게 (매 화면 하나)
    for p in sorted(COMP.glob('*/*.dc.html')):
        t = p.read_text(encoding='utf-8')
        if '>시연용 모의 데이터<' in t:
            p.write_text(t.replace('>시연용 모의 데이터<', '>시연<'), encoding='utf-8')
    # 예매 상세
    rep('exchange/Main.dc.html', [
        ('가상 데이터로 교환 허용 공연이라고 가정한 예시예요. 실제 예매처 정책 검증 결과가 아니에요. 같은 가격·등급 좌석끼리 신청할 수 있고, 신청 마감(12.13 (일) 23:59)은 가상 규칙이에요.',
         '같은 가격·등급 좌석끼리 교환할 수 있어요. 신청 마감 12.13 (일) 23:59 (가상)')])
    rep('exchange/Main.dc.html', [('교환 가능 · 시연용 판정', '교환 가능 · 시연 판정')])
    # 신청 현황
    rep('exchange/Waiting.dc.html', [
        ('후보가 나타나면 알려드릴게요 (서비스 설계 가정). 기다리는 동안에도 내 티켓은 그대로 유효해요.', '후보가 나타나면 알려드릴게요. 기다리는 동안 내 티켓은 그대로 유효해요.'),
        ('알림 도착 (프로토타입)', '후보 알림 열기 (시연)')])
    # 양방향 확인: 필수 충족 한 줄 옆의 중복 설명 제거
    rep('states/MatchCheck.dc.html', [('<span style="font-size: 12px; color: #4A4F5C">회차·구역·열 중 필수로 고른 조건</span>', '')])
    # 전후 비교: 수락≠완료는 짧게 유지
    rep('states/Compare.dc.html', [('제안을 보내도 교환은 확정되지 않아요. 상대방이 수락하고 최종 확인을 통과해야 완료돼요.', '보내도 바로 교환되지 않아요. 상대 수락과 최종 확인을 거쳐 완료돼요.')])
    # 수락 (일반): 지난 단계 설명·제목 반복·설계 가정 제거
    rel = 'states/StatusAccepted.dc.html'
    for s in ['조건 등록 완료', '양방향 조건 확인 통과', '비교 화면에서 내 동의 완료', '검토 완료', '상대방이 제안을 수락했어요', '다음 단계예요']:
        rep(rel, [(SUB % s, SUB % '')])
    drop_re(rel, r'<p style="[^"]*">최종 확인 전 취소 가능 여부는 서비스 설계 가정이에요\.</p>')
    # 최종 확인: (모의) 반복 제거, 실패 시 유지는 짧게 + (목표)
    rep('states/StatusFinal.dc.html', [('확인됨 (모의)', '확인됨'), ('확인 중 (모의)', '확인 중'),
                                      ('교환은 진행되지 않고 원래 티켓이 유지되는 것을 목표로 해요. 목표 UX와 시스템 요구사항이며, 이 프로토타입은 실제 티켓을 처리하지 않아요.',
                                       '교환하지 않고 원래 티켓을 유지해요 (목표).')], every=True)
    rep('states/StatusFinal.dc.html', [('>목표 UX<', '>목표<'), ('교환하지 않고 원래 티켓을 유지해요 (목표).', '교환하지 않고 원래 티켓을 유지해요.')])
    # 교환 완료 (일반)
    rep('exchange/Done.dc.html', [
        ('최종 확인을 통과해 새 티켓이 발급됐다고 가정한 모의 화면이에요.<br>입장할 때는 새 모바일 티켓을 보여주세요.', '새 티켓이 발급됐어요 (시연).<br>입장할 때는 새 모바일 티켓을 보여주세요.'),
        ('시연용 모의 화면이에요. 공연당 1회 제한과 취소 수수료 기준은 프로토타입 가상 규칙이고, 실제 기준은 공연별 안내 확인이 필요해요.',
         '교환은 공연당 1회 (가상 규칙) · 취소 수수료는 공연별 안내를 확인하세요.')])
    # 최종 확인 실패
    rel = 'exceptions/ExFinalFailed.dc.html'
    rep(rel, [('원래 티켓이 그대로 유지되는 것을 목표로 설계했어요.', '내 티켓은 그대로 유지돼요 (목표).'), ('실패 사유 (시연)', '실패 사유')])
    drop_re(rel, r'<div style="background: #F0EDFF; border-radius: 14px; padding: 12px 14px; display: flex; flex-direction: column; gap: 6px; ">'
                 r'<div style="display: flex; gap: 6px; align-items: center"><span[^>]*>목표 UX</span><b[^>]*>목표 UX · 시스템 요구사항</b></div><p[^>]*>[^<]*</p></div>')
    # 신청자 취소
    rep('exceptions/ExCancelled.dc.html', [('신청 횟수와 간격 제한은 가상 규칙이에요. 공식 정책으로 확인된 내용이 아니에요.', '신청 횟수·간격 제한이 있을 수 있어요 (가상 규칙).')])
    # 필수 조건 불일치
    rep('exceptions/ExMismatch.dc.html', [
        ('선호 조건은 맞지 않아도 후보로 남기고 차이를 알려줘요. 필수 조건은 내가 직접 바꾸기 전까지 그대로예요.', '필수 조건은 내가 직접 바꾸기 전까지 그대로예요.'),
        ('후보의 필수 조건이 맞지 않는 경우예요. 상대방의 조건은 내가 바꿀 수 없어요.', '상대의 필수 조건은 바꿀 수 없어요.')])
    # 후보 없음
    rep('exceptions/ExNoCandidate.dc.html', [('새 후보가 생기면 알려드려요 (서비스 설계 가정). 후보가 생긴다고 보장하지는 않아요.', '새 후보가 생기면 알려드려요. 생긴다는 보장은 없어요.')])
    # 티켓 상태 변경 (정적)
    drop_re('exceptions/ExTicketChanged.dc.html', r'<p style="[^"]*">위 상태는 시연용 모의 데이터예요\. 실제 예매 시스템에서 티켓 상태를 읽어 온다고 가정하지 않아요\.</p>')
    # 교환 제안 받음 (정적, 2C 화면)
    t = (COMP / 'exchange/Match.dc.html').read_text(encoding='utf-8')
    m = re.search(r'>([^<]*응답 시간\(예: 12시간, 가상 규칙\) 안에 응답이 없으면 제안이 취소돼요\. 거절해도 불이익이 없다고 가정했어요 \(서비스 설계 가정\))<', t)
    if not m:
        sys.exit('Match: 안내 문구 없음')
    rep('exchange/Match.dc.html', [(m.group(1), '수락해도 최종 확인을 거쳐 교환돼요. 응답 기한 12시간 (가상) 안에 응답이 없으면 제안이 취소돼요.')])
    # 교환 자격 확인 (정적)
    rep('states/Eligibility.dc.html', [
        ('프로토타입 판정 · 가상 데이터로 보여 주는 시연이에요. 실제 예매처 정책을 검증한 결과가 아니에요.', '시연 판정 · 실제 예매처 정책 검증 결과가 아니에요.'),
        ('시연 데이터 기준: 교환을 허용하는 공연으로 표시돼 있고, 신청 기간 안이며, 변경 이력이 없어요.', '교환 허용 공연 · 신청 기간 안 · 변경 이력 없음'),
        ('교환 허용 여부 정보가 없어요. 없는 정보는 추정하지 않고 &#39;확인 필요&#39;로 표시해요.', '교환 허용 여부 정보가 없어요.'),
        ('확인되기 전에는 교환 신청이 열리지 않아요 (서비스 설계 가정).', '확인되기 전에는 신청할 수 없어요.'),
        ('시연 데이터에서 교환을 허용하지 않는 공연으로 설정돼 있어요.', '교환을 허용하지 않는 공연이에요.'),
        ('교환 신청을 할 수 없어요. 예매 취소·변경 가능 여부는 공연 안내에서 확인하세요.', '취소·변경 가능 여부는 공연 안내에서 확인하세요.')])
    # 조건 설정 (정적): 중요도 정의는 남기고 짧게
    rep('states/ConditionsCast.dc.html', [
        ('필수는 맞지 않으면 후보에서 제외, 선호는 맞지 않아도 후보로 두고 차이를 알려줘요, 무관은 비교하지 않아요. 고르지 않은 조건은 &#39;무관&#39;으로 처리하지 않아요.',
         '필수: 안 맞으면 후보 제외 · 선호: 달라도 후보로 두고 차이 표시 · 무관: 비교 안 함')])
    # ---- 연석 (신청자)
    rep('pair/PairMode.dc.html', [
        ('2장 중 한 장은 <b>유지할 좌석</b>으로 두고, 다른 한 장을 <b>교환에 제공할 좌석</b>으로 옆자리 관객 좌석과 바꿔요. 유지할 좌석은 다음 단계에서 골라요.',
         '<b>유지할 좌석</b> 1장은 그대로 두고, <b>교환에 제공할 좌석</b> 1장을 옆자리 관객 좌석과 바꿔요.'),
        ('원하는 회차·구역·열을 정해 두고, 조건에 맞는 상대를 기다려요', '조건을 등록하고 맞는 상대를 기다려요'),
        ("떨어진 2장을 나란히 붙여요. '교환 제안 받기'를 켠 옆자리 관객에게만 제안을 보내요 (수요 미검증)", "떨어진 2장을 나란히 붙여요. '교환 제안 받기'를 켠 옆자리 관객에게만 제안해요")], every=True)
    rep('pair/PairSeat.dc.html', [
        ('옆자리 관객이 7열 12번으로 옮겨 가요. 같은 R석이지만 좌석 위치는 바뀌어요', '11열 4번 유지 · 7열 12번 제공 (옆자리 관객이 이 좌석으로 옮겨요)'),
        ('옆자리 관객이 11열 4번으로 옮겨야 해요. 같은 R석이지만 좌석 위치는 바뀌어요', '7열 12번 유지 · 11열 4번 제공 (옆자리 관객이 이 좌석으로 옮겨요)')])
    drop_re('pair/PairSeat.dc.html', r"<p style=\"[^\"]*\">'교환 제안 받기'를 켠 관객에게만 제안해요 \(서비스 설계 가정\)\.[^<]*</p>")
    rep('pair/PairAdjacency.dc.html', [("후보는 '교환 제안 받기'를 켠 관객 중 조건이 맞는 좌석만 보여줘요. 다른 관객의 설정·사유는 표시하지 않아요.", "'교환 제안 받기'를 켠 관객 중 조건이 맞는 좌석만 보여줘요.")])
    rel = 'pair/PairAccepted.dc.html'
    for s in ['내가 제안을 보냈어요 (내 수락)', '옆자리 관객이 제안을 수락했어요', '다음 단계예요']:
        rep(rel, [(SUB % s, SUB % '')])
    rep(rel, [('실패하면 원래 좌석이 유지되는 것을 목표로 해요 (목표 UX·시스템 요구사항).', '실패하면 원래 좌석을 유지해요 (목표).')])
    rep('pair/PairDeclined.dc.html', [('수신자는 언제든 거절할 수 있어요. 사유는 공개되지 않아요.', '거절 사유는 공개되지 않아요.'),
                                     ('여전히 일행과 떨어진 좌석이에요. 같은 방향의 다른 후보를 찾거나, 이전 단계에서 유지할 좌석을 다시 고를 수 있어요.', '여전히 일행과 떨어진 좌석이에요.')])
    rep('pair/PairDone.dc.html', [('{{cand}} 관객의 수락과 최종 확인을 거쳐<br>교환이 완료됐다고 가정한 모의 화면이에요.', '{{cand}} 관객의 수락과 최종 확인을 거쳐<br>교환됐어요 (시연).'),
                                 ('시연용 모의 화면이에요. 교환에 제공한 {{gave}} 좌석은 옆자리 관객의 새 좌석이 됐어요.', '교환에 제공한 {{gave}} 좌석은 옆자리 관객의 새 좌석이 됐어요.')])
    # ---- 연석 (수신자)
    t = (COMP / 'pair/PairIntent.dc.html').read_text(encoding='utf-8')
    tag = re.search(r'<span style="[^"]*">서비스 설계 가정</span>', t).group(0)
    rep('pair/PairIntent.dc.html', [(tag, tag.replace('>서비스 설계 가정<', '>시연<')), ('같은 가격·등급 좌석의 제안만 받아요 (MVP 범위) · 언제든 끌 수 있어요', '같은 가격·등급 좌석 제안만 받아요 · 언제든 끌 수 있어요')])
    rep('pair/PairIntent.dc.html', [('>실험 기능 · 수요 미검증<', '>실험 기능<')], every=True)
    drop_re('pair/PairReceive.dc.html', r"<p style=\"[^\"]*\">'교환 제안 받기'를 켠 경우에만 받는 제안이에요\.[^<]*</p>")
    rep('pair/PairReceive.dc.html', [(U4.B_TAG, '<div style="display: flex; gap: 6px; align-items: center">%s%s</div>' % (U4.B_TAG, U4.SIM_NOTE.replace('시연용 모의 데이터', '시연')))])
    print('화면 문구 수정 완료')


def refresh_defaults():
    """컴포넌트의 기본 화면 데이터(정적 보드용)를 문구가 바뀐 엔진 값으로 다시 계산한다."""
    pat = re.compile(r'var v = \(d && d\.(\w+)\) \|\| DEFAULT_VIEW;')
    n = 0
    for p in sorted(COMP.glob('*/*.dc.html')):
        t = p.read_text(encoding='utf-8')
        m = pat.search(t)
        if not m:
            continue
        key = m.group(1)
        rel = str(p.relative_to(COMP))
        dv = C3.PDEF if rel.startswith('pair/') else B3.DEFAULTS
        if key not in dv:
            sys.exit('%s: 기본값 키 없음 %s' % (rel, key))
        p.write_text(C3.write_logic(t, C3.mk_logic(dv, key)), encoding='utf-8')
        n += 1
    print('기본 화면 데이터 갱신: 컴포넌트 %d개' % n)


def refresh_stores():
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
    print('페이지 엔진 사본 갱신')


# ================================================================ 설계 메모 (앱에서 뺀 설명 → 확대 보기 패널, 포트폴리오 영역)
NOTES = {
    'Main': ['교환 가능 여부는 가상 데이터로 정한 시연 판정이에요. 실제 예매처 정책을 검증한 결과가 아니에요.',
             '같은 가격·등급 제한과 신청 마감일은 가상 규칙이에요.'],
    'Request': ["양쪽 수락과 최종 확인이 끝나야 교환이 완료된다는 규칙은 비교·진행 화면에서 안내해요 (서비스 설계 가정).",
                "중요도를 고르지 않은 조건을 '무관'으로 처리하지 않는다는 원칙은 입력 검증 문구로 보여줘요."],
    'Waiting': ["후보 알림은 서비스 설계 가정이에요. '후보 알림 열기 (시연)'은 알림 도착을 흉내 내는 시연 조작이에요."],
    'MatchCheck': ["한쪽 조건만 맞아도 '매칭 완료'로 표시하지 않아요 (양방향 판정 원칙).", '조건별 판정 전체는 \'조건 전체 보기\'에 접어 두었어요.'],
    'Compare': ["정보가 없는 항목은 추정하지 않고 '확인 필요'로 표시해요 (같은 항목 보기 안에도 안내)."],
    'StatusSent': ['응답 기한(12시간)은 가상 규칙이에요.', '지난 단계의 보조 설명은 단계 이름과 완료 표시로 충분해 뺐어요.'],
    'StatusAccepted': ['최종 확인 전 취소 가능 여부는 서비스 설계 가정이에요.'],
    'StatusFinal': ['실패하면 원래 티켓을 유지하는 것은 목표 UX이자 시스템 요구사항이에요. 두 티켓을 한 번에 처리하고 실패하면 아무것도 바꾸지 않는 기능이 필요해요.',
                    '이 프로토타입은 실제 티켓을 처리하지 않아요. 확인 항목의 결과는 모의 값이에요.'],
    'Done': ['새 티켓 발급은 최종 확인 통과를 가정한 모의 화면이에요.', '공연당 1회 제한·취소 수수료 기준은 가상 규칙이에요. 실제 기준은 공연별 안내 확인이 필요해요.'],
    'ExFinalFailed': ['원래 티켓 유지는 목표 UX·시스템 요구사항이에요. 실제 서비스에는 두 티켓을 한 번에 처리하고 실패하면 아무것도 바꾸지 않는 기능이 필요해요.',
                      '이 프로토타입은 실제 티켓을 처리하지 않아요.'],
    'ExCancelled': ["상대방에게 '취소됨'으로 보인다는 것은 서비스 설계 가정이에요.", '신청 횟수·간격 제한은 가상 규칙이에요. 공식 정책으로 확인된 내용이 아니에요.'],
    'ExNoCandidate': ['새 후보 알림은 서비스 설계 가정이에요.'],
    'ExMismatch': ['선호 조건은 맞지 않아도 후보로 남기고 차이를 알려줘요 (양방향 판정 원칙).'],
    'ExTicketChanged': ['티켓 상태는 시연용 모의 데이터예요. 실제 예매 시스템에서 상태를 읽어 온다고 가정하지 않아요.'],
    'Match': ['응답 기한(12시간)은 가상 규칙이에요.', '거절해도 불이익이 없다는 것은 서비스 설계 가정이에요.'],
    'Eligibility': ['판정은 가상 데이터로 보여 주는 시연이에요.', "없는 정보는 추정하지 않고 '확인 필요'로 표시해요. 확인 전에는 신청이 열리지 않는다는 것은 서비스 설계 가정이에요."],
    'ConditionsCast': ["고르지 않은 조건은 '무관'으로 처리하지 않아요 (위쪽 '중요도를 선택해 주세요' 안내)."],
    'PairMode': ['연석 만들기는 수요를 검증하지 않은 실험 기능이에요.'],
    'PairSeat': ["'교환 제안 받기'를 켠 관객에게만 제안한다는 것은 서비스 설계 가정이에요.",
                 '번호가 이어져도 인접 여부는 배치도 데이터로 따로 확인해요 (다음 화면에서 표시).', '상대가 수락해도 최종 확인 뒤에 교환돼요 (진행 화면에서 표시).'],
    'PairAdjacency': ['다른 관객의 수신 설정·제외 사유는 개인정보라 표시하지 않아요.'],
    'PairWarn': ["상대 수락과 최종 확인이 남았다는 점은 단계 표시('다음: 상대 수락')와 확인 목록으로 안내해요."],
    'PairAccepted': ['실패 시 원래 좌석 유지는 목표 UX·시스템 요구사항이에요.'],
    'PairDeclined': ['수신자는 언제든 거절할 수 있어요 (수신자의 권한).'],
    'PairDone': ['교환 완료는 수락과 최종 확인 통과를 가정한 모의 화면이에요.'],
    'PairIntent': ['같은 가격·등급 제안만 받는 것은 MVP 범위로 정한 서비스 설계 가정이에요.', '연석 만들기는 수요를 검증하지 않은 실험 기능이에요.'],
    'PairReceive': ['수신자 화면의 \'(목표)\' 표기: 실패 시 원래 좌석 유지는 목표 UX·시스템 요구사항이에요.', '교환이 예매처 안에서 처리되고 송금·연락이 필요 없다는 것은 서비스 설계 가정이에요.', '응답 기한은 가상 규칙이에요.'],
}

NOTES_TPL = ('<sc-if value="{{zoomHasNotes}}"><div style="border-top: 1px solid rgba(255, 255, 255, 0.3); padding-top: 12px; display: flex; flex-direction: column; gap: 8px">'
             '<b style="font-size: 15px">설계 메모 · 앱 화면에서 뺀 설명</b><ul style="margin: 0; padding: 0 0 0 18px; display: flex; flex-direction: column; gap: 6px">'
             '<sc-for list="{{zoomNotes}}" as="n"><li style="font-size: 14px; line-height: 1.55; color: #E3DDFF">{{n}}</li></sc-for></ul></div></sc-if>')


def zoom_notes():
    for page in ['p07-ui-exchange', 'p08-ui-pair', 'p07b-conditions-match', 'p07c-status', 'p07d-exceptions', 'p08b-pair-states']:
        p = SRC / 'pages' / page / 'page.html'
        t = p.read_text(encoding='utf-8')
        # 폰 번호별 화면 이름 (정적 폰은 dc-import 하나, 전환형 폰은 상태에서 현재 화면을 읽는다)
        screens = {}
        for m in re.finditer(r'data-zoom-host="(\d+)"', t):
            i = int(m.group(1))
            seg = t[m.end():m.end() + 600]
            d = re.search(r'<dc-import name="(\w+)"', seg)
            screens[i] = d.group(1) if d else None
        n = max(screens) + 1
        code_add = ('var ZOOM_NOTES = %s;\nvar ZOOM_STATIC = %s;\n' % (json.dumps(NOTES, ensure_ascii=False), json.dumps([screens.get(i) for i in range(n)])))
        a = "v.zoomLive = z ? '크게 보기 열림: ' + v.zoomTitle + '. Esc 로 닫아요.' : '';"
        b = ("var st = self.state && self.state.stacks;\n"
             "var notes = [];\n"
             "(z || []).forEach(function (i) { var name = st && st[i] ? st[i][st[i].length - 1] : ZOOM_STATIC[i]; (ZOOM_NOTES[name] || []).forEach(function (x) { if (notes.indexOf(x) < 0) notes.push(x); }); });\n"
             "v.zoomNotes = notes; v.zoomHasNotes = notes.length > 0;\n" + a)
        if t.count(a) != 1 or t.count('var ZOOM_BASE = ') != 1:
            sys.exit(page + ': 확대 로직 없음')
        t = t.replace(a, b).replace('var ZOOM_BASE = ', code_add + 'var ZOOM_BASE = ', 1)
        c = '<button type="button" data-zoom-close=""'
        if t.count(c) != 1:
            sys.exit(page + ': 확대 패널 없음')
        t = t.replace(c, NOTES_TPL + c)
        if '</' in C3.SCRIPT_RE.search(t).group(2):
            sys.exit(page + ': 로직에 </ 가 있음')
        p.write_text(t, encoding='utf-8')
    print('설계 메모: 확대 보기 패널 6개 보드')


if __name__ == '__main__':
    writing()
    refresh_defaults()
    refresh_stores()
    zoom_notes()
