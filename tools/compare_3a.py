#!/usr/bin/env python3
"""STEP 3A 회귀 비교: 화면 전환 적용 전(STEP 2C) 수집물과 후 수집물을 비교한다.

사용법: python3 tools/compare_3a.py <이전 수집 디렉터리> <이후 수집 디렉터리>

- 데스크톱 1920x1080 보드, 모바일 390px 뷰포트 캡처: 픽셀 비교
- 보드 제목·크기, 모바일 가로 스크롤 폭, 콘솔/네트워크 로그
- 보이는 상호작용 요소(링크·입력, 폰 틀 tabindex 제외), 라디오·체크박스 클릭 결과, Tab 순서, 첫 링크 클릭
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

A, B = Path(sys.argv[1]), Path(sys.argv[2])


def px(a, b):
    x = np.asarray(Image.open(a).convert('RGB'), dtype=np.int16)
    y = np.asarray(Image.open(b).convert('RGB'), dtype=np.int16)
    if x.shape != y.shape:
        return '크기 다름'
    d = np.abs(x - y).max(axis=2) > 0
    if not d.any():
        return None
    ys, xs = np.where(d)
    return '%d px (%.3f%%), 영역 x%d-%d y%d-%d' % (d.sum(), d.mean() * 100, xs.min(), xs.max(), ys.min(), ys.max())


print('== 픽셀 비교')
for sub in ('desktop', 'mobile'):
    same = 0
    files = [p for p in sorted((A / sub).glob('*.png')) if sub == 'desktop' or p.name.endswith('-viewport.png')]
    for p in files:
        r = px(p, B / sub / p.name)
        if r:
            print('  차이', sub, p.name, r)
        else:
            same += 1
    print('  %s: %d장 중 동일 %d장' % (sub, len(files), same))

ra = json.load(open(A / 'report.json', encoding='utf-8'))
rb = json.load(open(B / 'report.json', encoding='utf-8'))
print('== 구조')
print('  보드 제목 동일:', ra['root']['boardTitles'] == rb['root']['boardTitles'], '| 보드 크기 동일:', ra['root']['iframeRects'] == rb['root']['iframeRects'])
print('  모바일 가로 스크롤 폭:', ra['mobile']['rootScrollWidth'], '→', rb['mobile']['rootScrollWidth'])
print('  콘솔/네트워크 로그:', len(ra['logs']), '→', len(rb['logs']))


def vis(items):
    return [(i['tag'], i.get('href'), i.get('type'), i.get('name'), i.get('checked')) for i in items
            if i.get('visible', True) and not (i['tag'] == 'div' and i.get('href') is None and i.get('type') is None)]


print('== 페이지별')
for pid in ra['pages']:
    a, b = ra['pages'][pid], rb['pages'][pid]
    msgs = []
    if vis(a['interactive']) != vis(b['interactive']):
        msgs.append('보이는 링크·입력 요소 다름 (%d → %d)' % (len(vis(a['interactive'])), len(vis(b['interactive']))))
    if a['controlSteps'] != b['controlSteps']:
        msgs.append('라디오·체크박스 클릭 결과 다름')
    if a['tabOrder'] != b['tabOrder']:
        msgs.append('Tab 순서 다름: %s → %s' % (a['tabOrder'], b['tabOrder']))
    if a['firstLinkClick'] != b['firstLinkClick']:
        fa, fb = a['firstLinkClick'], b['firstLinkClick']
        msgs.append('첫 링크 클릭: %s(%s) → %s(%s)' % (fa['urlAfter'], fa['bodyTextAfter'], fb['urlAfter'], fb['bodyTextAfter']))
    if msgs:
        print(' ', pid, rb['root']['boardTitles'][int(pid[1:]) - 1])
        for m in msgs:
            print('     -', m)
