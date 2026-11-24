#!/usr/bin/env python3
"""STEP 4C-2A 근거 대조: 보드에 쓴 리서치 수치를 원본 분류표(Seat-Swap-X-Research.xlsx)의 행 단위 데이터로 다시 계산해 비교하고,
11장(검증·회고)의 자동 점검 수치를 실제 테스트 로그와 비교한다.

사용법: python3 tools/check_research_4c2a.py [테스트 로그 디렉터리]
  로그 디렉터리를 주면 *.txt 의 '합계 N건, 실패 0건' 을 읽어 11장 수치와 대조한다.
"""
import re
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
wb = openpyxl.load_workbook(ROOT / 'Seat-Swap-X-Research.xlsx', data_only=True)
ws = wb['교환글 분류']
rows = list(ws.iter_rows(values_only=True))
head = rows[6]
data = [r for r in rows[7:] if r[0] not in (None, '') and r[1] not in (None, '')]  # 번호만 미리 채워진 빈 행 제외
ix = {h: i for i, h in enumerate(head) if h}

ok_n = fail_n = 0


def ok(name, cond, detail=''):
    global ok_n, fail_n
    if cond:
        ok_n += 1
        print('  PASS', name)
    else:
        fail_n += 1
        print('  FAIL', name, '—', detail)


def col(name):
    return [r[ix[name]] for r in data]


n = len(data)
counts = [int(c) for c in col('조건 개수')]
tag_cols = list(range(ix['회차'], ix['매수'] + 1))
tag_sum = [sum(int(r[i] or 0) for i in tag_cols) for r in data]
avg = sum(counts) / n
types = {t: col('교환 유형').count(t) for t in set(col('교환 유형'))}
mention = {k: sum(int(r[ix[k]] or 0) for r in data) for k in ['회차', '구역', '열', '캐스팅']}
memo_pat = re.compile('허용|비슷|선호|또는|범위|까지|넓게|수용|우대|이내|미만')
memo_hits = sum(1 for m in col('메모') if memo_pat.search(str(m)))
contact = [c for c in col('연락 절차') if c]
method_none = col('교환 방식').count('미기재')
result_unknown = col('성사 여부').count('알 수 없음')
safety = sum(1 for c in col('인증·안전 명시') if c)
pair_req = sum(1 for c in col('연석 요청') if str(c).lower() in ('true', '1'))

print('[원본 분류표 다시 계산] 유효 게시글 %d건' % n)
ok('유효 표본 21건', n == 21, n)
ok('행별 조건 개수 = 조건 태그 합 (21행 모두)', counts == tag_sum, list(zip(counts, tag_sum)))
ok('평균 조건 3.86개 (81 / 21)', round(avg, 2) == 3.86 and sum(counts) == 81, avg)
ok('최소 2개 · 최대 6개 · 모든 글 2개 이상', min(counts) == 2 and max(counts) == 6, (min(counts), max(counts)))
ok('교환 유형 좌석 9 · 회차 7 · 좌석+회차 5', types == {'좌석 교환': 9, '회차 교환': 7, '좌석+회차': 5}, types)
ok('조건 언급 회차 19 · 구역 18 · 열 10 · 캐스팅 7', mention == {'회차': 19, '구역': 18, '열': 10, '캐스팅': 7}, mention)
ok('허용 범위·우선순위 표현 18건 (분류 메모 기준)', memo_hits == 18, memo_hits)
ok('연락이 DM·오픈채팅으로 넘어간 글 17건', len(contact) == 17 and all(('DM' in c) or ('오픈채팅' in c) for c in contact), contact)
ok('교환 방식 미기재 18건', method_none == 18, method_none)
ok('교환 결과 확인 0건 (알 수 없음 21건)', result_unknown == 21, result_unknown)
ok('안전 관련 표현 1건', safety == 1, safety)
ok('명시적 연석 요청 0건', pair_req == 0, pair_req)
summ = {r[0]: r[1] for r in wb['정량 요약'].iter_rows(values_only=True) if r[0]}
ok('정량 요약 시트와 일치 (목표 50건 대비 21건)', str(summ.get('목표 50건 대비')) == '21', summ.get('목표 50건 대비'))

print('[보드 문구에 같은 수치가 쓰였는지]')


def text(slug):
    return re.sub(r'<[^>]+>', ' ', (ROOT / 'src/pages' / slug / 'page.html').read_text(encoding='utf-8'))


p04, p03, p11 = text('p04-desk-research'), text('p03-problem'), text('p10-retrospective')
for s in ['3.86개', '최소 2개, 최대 6개', '회차 19 · 구역 18 · 열 10 · 캐스팅 7', '18건', '(17건)', '18건이 적지 않았어요', '안전 표현 1건', '0건', '목표 50건 중 21건', '연석 요청 0건', '원본 분류표(엑셀) 행 단위 대조 완료']:
    ok('04장: "%s"' % s, s in p04)
ok('04장: AI 시뮬레이션을 인터뷰로 분류하지 않음', 'AI 시뮬레이션' in p04 and '사용자 근거로 쓰지 않았어요' in p04)
ok('03장: 3.86 수치에 표본(21건) 표기', '21건은 게시글당 평균 3.86개' in p03)
ok('03장: 안전 표현 1건 · 방식 미기재 18건', '1건뿐이라' in p03 and '18건은 교환 방식을 적지 않았어요' in p03)

if len(sys.argv) > 1:
    print('[11장 자동 점검 수치 ↔ 테스트 로그]')
    logs = Path(sys.argv[1])
    want = {'demo-engine-test.txt': 33, 'pair-engine-test.txt': 66, 'demo-flows-3b.txt': 184, 'pair-flows.txt': 146,
            'ux4a-flows.txt': 104, 'ux4b-visual.txt': 61, 'nav-test.txt': 57}
    for f, v in want.items():
        m = re.search(r'합계 (\d+)건, 실패 (\d+)건', (logs / f).read_text(encoding='utf-8'))
        ok('%s: 합계 %d건 · 실패 0' % (f, v), m and int(m.group(1)) == v and m.group(2) == '0', m.group(0) if m else '없음')
        ok('11장에 %d 표기' % v, ('>%d<' % v) in (ROOT / 'src/pages/p10-retrospective/page.html').read_text(encoding='utf-8'))
    ok('11장: 합산하지 않는다고 명시', '합산하지 않아요' in p11)

print('합계 %d건, 실패 %d건' % (ok_n + fail_n, fail_n))
sys.exit(1 if fail_n else 0)
