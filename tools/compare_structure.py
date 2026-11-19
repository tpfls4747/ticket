#!/usr/bin/env python3
"""문구만 바꾼 작업(STEP 2B 등) 전후로 '구조와 인터랙션'이 같은지 비교한다.

사용법: python3 tools/compare_structure.py <이전 report.json> <이후 report.json>

비교하는 것: 보드 크기·스크롤 높이, 폰 화면 개수, 인터랙티브 요소의 종류·href·입력 타입·이름·초기 checked,
포커스 가능 요소 수, 로드된 리소스·스크립트·폰트 종류, 콘솔/네트워크 오류.
비교하지 않는 것: 화면 텍스트(의도적으로 바뀜), 링크·컨트롤 클릭 결과(원본에서 실행마다 달라짐).
"""
import json, sys

a = json.load(open(sys.argv[1], encoding='utf-8'))
b = json.load(open(sys.argv[2], encoding='utf-8'))
bad = []

def chk(name, x, y):
    if x != y:
        bad.append((name, x, y))

for k in ('boardTitles', 'scrollHeight', 'iframeRects'):
    chk('root.' + k, a['root'][k], b['root'][k])
for pid in a['pages']:
    pa, pb = a['pages'][pid], b['pages'][pid]
    chk(pid + ' 폰 화면 수', a['phones'][pid]['count'], b['phones'][pid]['count'])
    strip = lambda L: [{k: v for k, v in i.items() if k != 'text'} for i in L]
    chk(pid + ' 인터랙티브 요소(텍스트 제외)', strip(pa['interactive']), strip(pb['interactive']))
    chk(pid + ' 포커스 가능 수', pa['focusable'], pb['focusable'])
    chk(pid + ' 라디오·체크박스 클릭 결과', pa['controlSteps'], pb['controlSteps'])
    chk(pid + ' 첫 링크 클릭 결과', pa['firstLinkClick'], pb['firstLinkClick'])
    ia, ib = dict(pa['info']), dict(pb['info'])
    fa, fb = set(ia.pop('fontsLoaded')), set(ib.pop('fontsLoaded'))
    chk(pid + ' 폰트 종류', sorted(fa), sorted(fb))
    ia.pop('title', None); ib.pop('title', None)
    chk(pid + ' 리소스·스크립트·스타일시트', ia, ib)
chk('콘솔/네트워크 로그', a['logs'], b['logs'])
print('구조 항목 불일치: %d' % len(bad))
for n, x, y in bad:
    print('  -', n, '\n     이전:', str(x)[:160], '\n     이후:', str(y)[:160])
sys.exit(1 if bad else 0)
