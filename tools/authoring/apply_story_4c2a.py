"""STEP 4C-2A: 포트폴리오 스토리텔링·콘텐츠 정리 (1회성 적용 스크립트, STEP 4B.5 커밋 78a26f7 상태에서 실행).

- 표시 순서: 본문 11장(P01 P02 P03 P04 P05 P06 P07 P08 P09 P12 P16) + 부록 5장(P10 P11 P13 P14 P15).
  내부 식별자(slug·uuid)와 파일 이름은 그대로 두고, 표시 순서·번호·푸터·목차·참조 문구만 바꾼다.
- 공개를 막는 자리표시자와 내부 개발 메모를 화면에서 없앤다 (확인되지 않은 값은 만들지 않는다).
- P04 리서치(원본 엑셀 Seat-Swap-X-Research.xlsx 행 단위 대조), P05·P06·P07 역할 분리, P16 검증·한계·회고를 다시 쓴다.
- 디자인 시스템(색·글꼴·카드·배지 스타일)은 기존 보드의 인라인 스타일을 그대로 쓴다.
사용법: python3 tools/authoring/apply_story_4c2a.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
PAGES = SRC / 'pages'
COMP = SRC / 'components'

# ------------------------------------------------------------------ 새 구성 (slug, 화면 번호, 보드 이름, 이야기 단계 / 부록 문자)
MAIN = [
    ('p01-cover', '01', '표지', None),
    ('p02-overview', '02', '개요', '개요'),
    ('p03-problem', '03', '문제 정의', '문제'),
    ('p04-desk-research', '04', '조사와 핵심 인사이트', '조사·인사이트'),
    ('p05-policy', '05', 'UX 전략 ① 문제와 설계 원칙', '전략'),
    ('p06-user-flow', '06', 'UX 전략 ② 사용자 여정과 기능 구조', '전략'),
    ('p06b-state-flow', '07', 'UX 전략 ③ 핵심 의사결정', '전략'),
    ('p07-ui-exchange', '08', '솔루션 · 좌석·회차 교환 체험', '솔루션'),
    ('p07b-conditions-match', '09', '솔루션 · 양방향 매칭과 비교', '솔루션'),
    ('p08-ui-pair', '10', '실험 기능 · 연석 만들기 체험', '실험 기능'),
    ('p10-retrospective', '11', '검증 · 한계 · 회고', '검증·회고'),
]
APPX = [
    ('p07c-status', '12', 'A', '교환 처리 상태', '본문 07장 보충'),
    ('p07d-exceptions', '13', 'B', '예외 상황', '본문 07장 보충'),
    ('p08b-pair-states', '14', 'C', '연석 상세 상태', '본문 10장 보충'),
    ('p09-components', '15', 'D', '컴포넌트', '디자인 시스템'),
    ('p09b-state-components', '16', 'E', '상태 컴포넌트 · 표기 범례', '디자인 시스템'),
]
TOTAL = 16
STAGES = ['개요', '문제', '조사·인사이트', '전략', '솔루션', '실험 기능', '검증·회고']
CHIPS = {
    'p02-overview': 'OVERVIEW · 개요',
    'p03-problem': 'PROBLEM · 문제 정의',
    'p04-desk-research': 'RESEARCH · 조사와 인사이트',
    'p05-policy': 'STRATEGY ① · 문제와 설계 원칙',
    'p06-user-flow': 'STRATEGY ② · 사용자 여정과 기능 구조',
    'p06b-state-flow': 'STRATEGY ③ · 핵심 의사결정',
    'p07-ui-exchange': 'SOLUTION · 좌석·회차 교환 (핵심)',
    'p07b-conditions-match': 'SOLUTION · 양방향 매칭과 비교',
    'p08-ui-pair': 'EXPERIMENT · 연석 만들기 · 실험 기능',
    'p10-retrospective': 'VALIDATION · 검증·한계·회고',
    'p07c-status': 'APPENDIX A · 교환 처리 상태',
    'p07d-exceptions': 'APPENDIX B · 예외 상황',
    'p08b-pair-states': 'APPENDIX C · 연석 상세 상태 · 실험 기능',
    'p09-components': 'APPENDIX D · 컴포넌트',
    'p09b-state-components': 'APPENDIX E · 상태 컴포넌트 · 표기 범례',
}


def page(slug):
    return PAGES / slug / 'page.html'


def read(slug):
    return page(slug).read_text(encoding='utf-8')


def write(slug, t):
    page(slug).write_text(t, encoding='utf-8')


def rep(t, pairs, where, count=1):
    for old, new in pairs:
        n = t.count(old)
        if n != count and not (count == 0 and n >= 1):
            sys.exit('%s: 치환 대상 %d회 (%s)' % (where, n, old[:80]))
        t = t.replace(old, new)
    return t


# ------------------------------------------------------------------ 공통 조각 (기존 보드의 스타일을 그대로 쓴다)
BRAND = ('<span style="display: flex; align-items: center; gap: 10px"><span aria-hidden="true" style="display: flex; gap: 3px">'
         '<span style="width: 10px; height: 10px; border-radius: 3px; background: #5B3DF5"></span>'
         '<span style="width: 10px; height: 10px; border-radius: 3px; background: #5B3DF5"></span></span>좌석·회차 교환 UX/UI</span>')


def track(stage):
    """푸터의 이야기 흐름 표시: 지난 단계 · 현재 단계 · 남은 단계를 글과 색으로 함께 보여 준다."""
    i = STAGES.index(stage)
    out = []
    for k, s in enumerate(STAGES):
        if k < i:
            sty = 'color: #5B3DF5; background: #F0EDFF'
        elif k == i:
            sty = 'color: #FFFFFF; background: #5B3DF5; font-weight: 700'
        else:
            sty = 'color: #8B909C; background: #FFFFFF; border: 1px solid #E6E8EC'
        cur = ' aria-current="step"' if k == i else ''
        out.append('<span%s style="font-size: 12px; line-height: 1; padding: 5px 10px; border-radius: 999px; white-space: nowrap; %s">%s</span>' % (cur, sty, s))
    return ('<span role="list" aria-label="케이스 스터디 흐름 · 현재: %s" style="display: flex; align-items: center; gap: 4px">%s</span>'
            % (stage, ''.join('<span role="listitem" style="display: flex">%s</span>' % o for o in out)))


def foot_right_main(no, stage):
    return ('<span style="display: flex; align-items: center; gap: 20px">%s<span style="white-space: nowrap">본문 · <b style="color: #191B22">%s</b> / %d</span></span>'
            % (track(stage), no, TOTAL))


def foot_right_appx(no, letter, note):
    return ('<span style="display: flex; align-items: center; gap: 14px"><span style="font-size: 12px; font-weight: 700; color: #5F6370; background: #EEF0F3; padding: 5px 10px; border-radius: 999px; white-space: nowrap">부록 %s · %s</span>'
            '<span style="white-space: nowrap"><b style="color: #191B22">%s</b> / %d</span></span>' % (letter, note, no, TOTAL))


def footer(right):
    return ('<div style="display: flex; justify-content: space-between; align-items: center; font-size: 14px; color: #6B7080">%s%s</div>' % (BRAND, right))


def badge(text, kind='gray'):
    sty = {'gray': 'color: #4A4F5C; background: #F0F1F4', 'purple': 'color: #3A26C4; background: #E9E5FF',
           'orange': 'color: #A3440B; background: #FFF1E6', 'green': 'color: #1F7A4D; background: #E6F6EE',
           'red': 'color: #B03A3A; background: #FDF0F0', 'dark': 'color: #FFFFFF; background: #191B22'}[kind]
    return '<span style="font-size: 12px; font-weight: 700; %s; padding: 4px 8px; border-radius: 6px; white-space: nowrap">%s</span>' % (sty, text)


def header(num, chip, h1, sub=None, right=None, sub_w=1100):
    s = ('<div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 32px">'
         '<div style="display: flex; align-items: flex-start; gap: 32px">'
         '<span aria-hidden="true" style="font-size: 128px; font-weight: 900; line-height: 0.82; color: #DCD5FF; letter-spacing: -4px">%s</span>'
         '<div style="display: flex; flex-direction: column; gap: 14px">'
         '<span style="align-self: flex-start; font-size: 14px; font-weight: 700; letter-spacing: 2px; color: #5B3DF5; background: #E9E5FF; padding: 6px 14px; border-radius: 999px">%s</span>'
         '<h1 style="margin: 0; font-size: 48px; font-weight: 900; line-height: 1.25; letter-spacing: -1px">%s</h1>' % (num, chip, h1))
    if sub:
        s += '<p style="margin: 0; width: %dpx; font-size: 20px; line-height: 1.6; color: #5F6370">%s</p>' % (sub_w, sub)
    s += '</div></div>'
    if right:
        s += right
    return s + '</div>'


def frame(bg, inner, gap=36):
    return ('<div style="position: relative; width: 1920px; height: 1080px; box-sizing: border-box; padding: 88px 120px 56px; background: %s; '
            "font-family: 'Noto Sans KR', sans-serif; color: #191B22; display: flex; flex-direction: column; gap: %dpx; overflow: hidden\">\n%s\n</div>" % (bg, gap, inner))


def set_body(slug, body):
    t = read(slug)
    a = t.index('</helmet>\n') + len('</helmet>\n')
    b = t.index('\n</x-dc>')
    write(slug, t[:a] + body + t[b:])


# ================================================================ 1. 번호·칩·푸터 (모든 보드)
NUM_RE = re.compile(r'(font-size: 128px; font-weight: 900; line-height: 0\.82; color: )#DCD5FF(; letter-spacing: -4px">)[0-9]{2}<')
CHIP_RE = re.compile(r'(letter-spacing: 2px; color: )#5B3DF5(; background: )#E9E5FF(;[^>]*>)[^<]*<')
FOOT_RE = re.compile(r'<span><b style="color: #191B22">[0-9]{2}</b> / 10[^<]*</span>')


def renumber(slug, num, chip, right, appendix=False):
    t = read(slug)
    color, ccol, cbg = ('#E3E5EA', '#5F6370', '#EEF0F3') if appendix else ('#DCD5FF', '#5B3DF5', '#E9E5FF')
    t, n1 = NUM_RE.subn(lambda m: m.group(1) + color + m.group(2) + num + '<', t, count=1)
    t, n2 = CHIP_RE.subn(lambda m: m.group(1) + ccol + m.group(2) + cbg + m.group(3) + chip + '<', t, count=1)
    if slug == 'p06-user-flow':
        old = re.search(r'<div style="position: absolute; left: 1640px; top: 1004px; width: 160px; text-align: right; font-size: 14px; color: #6B7080"><b style="color: #191B22">06</b> / 10</div>', t)
        n3 = 1 if old else 0
        if old:
            t = t.replace(old.group(0), '<div style="position: absolute; left: 900px; top: 1000px; width: 900px; display: flex; justify-content: flex-end; font-size: 14px; color: #6B7080">%s</div>' % right)
    else:
        t, n3 = FOOT_RE.subn(lambda m: right, t, count=1)
    if (n1, n2, n3) != (1, 1, 1):
        sys.exit('%s: 번호 %d 칩 %d 푸터 %d' % (slug, n1, n2, n3))
    write(slug, t)


REWRITTEN = {'p04-desk-research', 'p05-policy', 'p06b-state-flow', 'p10-retrospective'}  # 새로 쓴 보드는 머리·푸터를 이미 새 형식으로 만든다


def renumber_all():
    for slug, no, _, stage in MAIN[1:]:
        if slug not in REWRITTEN:
            renumber(slug, no, CHIPS[slug], foot_right_main(no, stage))
    for slug, no, letter, _, note in APPX:
        renumber(slug, letter, CHIPS[slug], foot_right_appx(no, letter, note), appendix=True)
    print('번호·칩·푸터: 보드 15장 (표지 제외)')


# ================================================================ 2. 루트 템플릿 (표시 순서 · 보드 이름 · 목차) + 번들 명세 순서
def template():
    p = SRC / 'root' / 'template.html'
    t = p.read_text(encoding='utf-8')
    style_old = '.board iframe{display:block;border:0;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.12)}\n'
    style_new = style_old + (
        '.toc{width:1920px;box-sizing:border-box;background:#fff;border-radius:16px;padding:28px 32px;box-shadow:0 1px 3px rgba(0,0,0,.08);display:flex;gap:48px}\n'
        '.toc h1{margin:0 0 6px;font-size:20px}.toc p{margin:0;color:#6b6a68;font-size:13px;line-height:1.6}\n'
        '.toc ol{margin:0;padding:0;list-style:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:repeat(6,auto);grid-auto-flow:column;gap:4px 32px}\n'
        '.toc a{display:flex;gap:10px;align-items:baseline;color:#1f1e1d;text-decoration:none;padding:4px 0;font-size:14px}\n'
        '.toc a:hover,.toc a:focus-visible{color:#5b3df5;text-decoration:underline}\n'
        '.toc b{font-variant-numeric:tabular-nums;color:#5b3df5;min-width:58px}\n'
        '.toc .appx b{color:#6b6a68}\n'
        '.toc .tag{font-size:11px;font-weight:700;color:#3a26c4;background:#e9e5ff;border-radius:4px;padding:1px 6px}\n'
        '.toc h2{margin:0 0 8px;font-size:13px;color:#6b6a68;font-weight:700}\n'
        '.board{scroll-margin-top:24px}\n')
    if t.count(style_old) != 1:
        sys.exit('template: 스타일 없음')
    t = t.replace(style_old, style_new)
    items_main, items_appx, boards = [], [], []
    for slug, no, name, _ in MAIN:
        tag = ' <span class="tag">체험</span>' if slug in ('p07-ui-exchange', 'p08-ui-pair') else ''
        items_main.append('<li><a href="#board-%s"><b>%s</b><span>%s%s</span></a></li>' % (no, no, name, tag))
        boards.append((slug, no, '%s · %s' % (no, name)))
    for slug, no, letter, name, _ in APPX:
        items_appx.append('<li class="appx"><a href="#board-%s"><b>부록 %s</b><span>%s</span></a></li>' % (no, letter, name))
        boards.append((slug, no, '부록 %s (%s) · %s' % (letter, no, name)))
    toc = ('<nav class="toc" aria-label="목차"><div style="width:360px;flex-shrink:0"><h1>좌석·회차 교환 UX/UI 케이스 스터디</h1>'
           '<p>본문 11장 + 부록 5장. 08장(좌석·회차 교환)과 10장(연석 만들기, 실험 기능)은 폰을 직접 눌러 체험할 수 있어요. '
           '모든 화면은 모의 데이터로 동작하는 시연이며, 실제 예매처 서비스·정책이 아니에요.</p></div>'
           '<div style="flex:1"><h2>본문</h2><ol>%s</ol></div><div style="width:300px;flex-shrink:0"><h2>부록</h2><ol style="grid-template-columns:1fr;grid-template-rows:none;grid-auto-flow:row">%s</ol></div></nav>\n'
           % (''.join(items_main), ''.join(items_appx)))
    sec = ''.join('<section class="board" id="board-%s" data-board="%s"><h2>%s</h2><iframe src="about:blank#{{page:%s}}" title="%s" width="1920" height="1080" loading="eager" style="width:1920px;height:1080px"></iframe></section>\n'
                  % (no, slug, label, slug, label) for slug, no, label in boards)
    a = t.index('<body>\n') + len('<body>\n')
    b = t.index('</body>')
    t = t[:a] + toc + sec + t[b:]
    t = t.replace('<html lang="en">', '<html lang="ko">').replace('<title>티켓 교환 UX/UI 포트폴리오</title>', '<title>좌석·회차 교환 UX/UI 포트폴리오</title>')
    p.write_text(t, encoding='utf-8')
    # 번들 명세: 같은 uuid·slug 를 새 표시 순서로 (식별자는 바꾸지 않는다)
    bp = SRC / 'bundle.json'
    bj = json.loads(bp.read_text(encoding='utf-8'))
    by = {x['slug']: x for x in bj['root']['page_order']}
    order = [s for s, *_ in MAIN] + [s for s, *_ in APPX]
    if sorted(order) != sorted(by):
        sys.exit('bundle.json: 보드 목록 불일치')
    bj['root']['page_order'] = [by[s] for s in order]
    bp.write_text(json.dumps(bj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('루트 템플릿: 목차 + 보드 16장 재배열, bundle.json 순서 갱신')


# ================================================================ 3. 자리표시자 · 내부 메모 · 보드 참조
def placeholders():
    # 표지: 이름·연락처는 확인된 값이 없어 공개 화면에서 뺀다 (보고서에 확인 필요로 남긴다)
    t = read('p01-cover')
    t = rep(t, [('<div style="position: absolute; left: 120px; top: 952px; font-size: 18px; color: #E3DDFF">[이름] · [연락처]</div>', '')], 'p01')
    write('p01-cover', t)
    # 예매 상세 폰: 공연장명은 시연용 가상 데이터로 표시
    p = COMP / 'exchange' / 'Main.dc.html'
    c = p.read_text(encoding='utf-8')
    c = rep(c, [('[공연장명]', '가상 공연장 (시연)')], 'Main')
    p.write_text(c, encoding='utf-8')
    # 설명용 폰의 체험 안내: 새 장 번호
    for rel, old, new in [('pair/PairWarn.dc.html', '설명용 화면 · 체험은 07 보드', '설명용 화면 · 체험은 10장'),
                          ('pair/PairIntent.dc.html', '설명용 화면 · 체험은 07 보드의 수신자 B 폰', '설명용 화면 · 체험은 10장의 수신자 B 폰')]:
        q = COMP / rel
        q.write_text(rep(q.read_text(encoding='utf-8'), [(old, new)], rel), encoding='utf-8')
    # 설명용 보드 배지: 직접 체험 위치
    for slug, where in [('p07b-conditions-match', '08장'), ('p07c-status', '08장'), ('p07d-exceptions', '08장'), ('p08b-pair-states', '10장')]:
        t = read(slug)
        t = rep(t, [('정적 화면이에요 · 직접 체험은 06·07 보드 · 폰의 ', '정적 화면이에요 · 직접 체험은 %s · 폰의 ' % where)], slug)
        write(slug, t)
    print('자리표시자·체험 안내 정리')


# ================================================================ 4. 개요 (P02): 확인된 사실 카드 + 공통 범례
LEGEND = [('시연', 'gray', '모의 데이터로 동작하는 화면. 실제 예매·결제와 연결되지 않아요'),
          ('가정', 'purple', '서비스 설계 가정. 공식 정책으로 확인되지 않았어요'),
          ('가상', 'gray', '예시로 정한 규칙 값 (응답 12시간 · 공연당 1회 등)'),
          ('목표', 'purple', '목표 UX·시스템 요구사항. 동작을 보장하지 않아요'),
          ('확인 필요', 'orange', '정보·정책을 아직 확인하지 못했어요'),
          ('실험 기능', 'orange', '수요를 검증하지 않은 기능 (연석 만들기)')]


def legend_strip():
    cells = ''.join('<span style="display: flex; align-items: center; gap: 8px; min-width: 0">%s<span style="font-size: 14px; line-height: 1.45; color: #4A4F5C">%s</span></span>'
                    % (badge(k, c), v) for k, c, v in LEGEND)
    return ('<section aria-label="표기 범례" style="background: #FFFFFF; border-radius: 20px; padding: 18px 28px; display: flex; align-items: center; gap: 28px">'
            '<b style="font-size: 16px; white-space: nowrap">표기 범례</b>'
            '<div style="flex: 1; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px 28px">%s</div></section>' % cells)


def overview():
    t = read('p02-overview')
    t = rep(t, [
        ('<span style="font-size: 14px; font-weight: 500; color: #5F6370">기간</span><span style="font-size: 20px; font-weight: 700; line-height: 1.4">[4주]</span>',
         '<span style="font-size: 14px; font-weight: 500; color: #5F6370">결과물</span><span style="font-size: 20px; font-weight: 700; line-height: 1.4">인터랙티브 웹 프로토타입</span>'),
        ('<span style="font-size: 14px; font-weight: 500; color: #5F6370">도구</span><span style="font-size: 20px; font-weight: 700; line-height: 1.4">[Figma 등]</span>',
         '<span style="font-size: 14px; font-weight: 500; color: #5F6370">근거</span><span style="font-size: 20px; font-weight: 700; line-height: 1.4">X 공개 교환글 21건 분석</span>'),
        ('조건 매칭으로 상대를 찾는 부담을 줄이는 것이 목표예요 (미검증)', '조건 매칭으로 상대를 찾는 부담을 줄이는 것'),
        ('개인 간 송금·연락 없이 예매처가 처리하는 구조를 가정해요 (설계 가정)', '개인 간 송금·연락 없이 예매처가 처리하는 구조'),
        ('떨어진 좌석을 연석으로 만드는 실험 기능이에요. 수요는 아직 검증되지 않았어요', '떨어진 좌석을 붙이는 실험 기능. 수요는 검증 전이에요'),
        ('<h2 style="margin: 0; font-size: 26px; font-weight: 700">이 프로젝트의 목표 · 검증 전 가설</h2>', '<h2 style="margin: 0; font-size: 26px; font-weight: 700">목표 · 사용자 검증 전 가설</h2>'),
        ('2026.11.18 조사한 X 공개 교환글 21건에서 관객이 직접 교환 상대를 찾는 모습을 확인했어요. 이 프로젝트는 그 과정을 예매 앱 안에서 처리하는 방식을 제안해요.',
         'X 공개 교환글 21건(2026.11.18 수집)에서 관객이 직접 교환 상대를 찾는 모습을 확인했어요. 그 과정을 예매 앱 안에서 처리하는 방식을 제안하는 컨셉 프로젝트예요.'),
    ], 'p02')
    # 아래 영역(목표·범위) 뒤에 범례를 붙인다: 푸터 바로 앞
    i = t.index('<div style="display: flex; justify-content: space-between; align-items: center; font-size: 14px; color: #6B7080">')
    t = t[:i] + legend_strip() + '\n' + t[i:]
    t = t.replace('padding: 88px 120px 56px; background: #F7F7FA; font-family: \'Noto Sans KR\', sans-serif; color: #191B22; display: flex; flex-direction: column; gap: 40px',
                  'padding: 88px 120px 56px; background: #F7F7FA; font-family: \'Noto Sans KR\', sans-serif; color: #191B22; display: flex; flex-direction: column; gap: 28px', 1)
    t = rep(t, [('<rect x="3" y="5" width="18" height="16" rx="2"></rect><path d="M3 10h18"></path><path d="M8 3v4"></path><path d="M16 3v4"></path>',
                 '<rect x="6" y="2" width="12" height="20" rx="2.5"></rect><path d="M10 18h4"></path>'),
                ('<path d="M12 19l7-7 3 3-7 7-3-3z"></path><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"></path><path d="M2 2l7.6 7.6"></path><circle cx="11" cy="11" r="2"></circle>',
                 '<circle cx="11" cy="11" r="7"></circle><path d="M21 21l-4.3-4.3"></path>')], 'p02 icons')
    t = t.replace('<div style="background: #FFFFFF; border-radius: 24px; padding: 28px; display: flex; align-items: center; gap: 20px">',
                  '<div style="background: #FFFFFF; border-radius: 24px; padding: 18px 28px; display: flex; align-items: center; gap: 20px">')
    t = t.replace('<div style="background: #6A4FF7; border-radius: 20px; padding: 26px;', '<div style="background: #6A4FF7; border-radius: 20px; padding: 20px 22px;')
    t = t.replace('<div style="background: #FFFFFF; border-radius: 20px; padding: 26px;', '<div style="background: #FFFFFF; border-radius: 20px; padding: 20px 22px;')
    t = t.replace('<section style="background: #5B3DF5; border-radius: 28px; padding: 44px;', '<section style="background: #5B3DF5; border-radius: 28px; padding: 32px 40px;', 1)
    t = t.replace('<section style="background: #FFFFFF; border-radius: 28px; padding: 44px;', '<section style="background: #FFFFFF; border-radius: 28px; padding: 32px 40px;', 1)
    write('p02-overview', t)
    print('P02: 자리표시자 카드 교체 + 표기 범례')


# ================================================================ 5. 문제 정의 (P03): 수치 출처와 근거 위치
def problem():
    t = read('p03-problem')
    t = rep(t, [
        ('X 공개 교환글은 게시글당 평균 3.86개의 조건을 걸었어요. 조건이 많을수록 맞는 상대가 줄 수 있다고 가정했어요.',
         'X 공개 교환글 21건은 게시글당 평균 3.86개의 조건을 걸었어요. 조건이 많을수록 맞는 상대가 줄 수 있다고 봤어요.'),
        ('개인 간 거래에서는 상대의 이행 여부를 확인하기 어렵다고 가정했어요. 사용자 인터뷰는 아직 하지 않았어요.',
         '개인 간 거래에서는 상대의 이행 여부를 확인하기 어렵다고 가정했어요. X 글의 안전 관련 표현은 1건뿐이라 근거로 쓰지 않았어요.'),
        ('취소 후 재예매가 필요한 방식이라면, 그 사이 다른 사람이 좌석을 잡을 수 있다고 가정했어요. X 글 21건 중 실제 교환 결과가 확인된 글은 0건이에요.',
         '취소 후 재예매가 필요한 방식이라면 그 사이 다른 사람이 좌석을 잡을 수 있다고 가정했어요. X 글 21건 중 18건은 교환 방식을 적지 않았어요.'),
    ], 'p03')
    write('p03-problem', t)
    print('P03: 수치 출처·근거 정리')


# ================================================================ 6. 조사와 핵심 인사이트 (P04)
INSIGHTS = [
    {'title': '여러 조건을 한 번에 건다',
     'stat': '3.86개', 'stat_note': '게시글당 평균 조건 수 · 최소 2개, 최대 6개',
     'obs': '21건 모두 조건을 2개 이상 적었어요 (회차·구역·열·캐스팅·정산 등).',
     'ux': '교환은 1:1 맞교환이 아니라, 여러 조건을 동시에 맞추는 탐색 문제예요.',
     'hyp': '조건을 구조화해 입력하면 상대를 찾는 부담이 줄어들 거예요.',
     'sol': '회차·구역·열을 여러 개 고르는 조건 등록', 'where': '08장'},
    {'title': '회차와 구역이 1차 기준이다',
     'stat': '19 · 18건', 'stat_note': '회차 19 · 구역 18 · 열 10 · 캐스팅 7 (언급한 글 수)',
     'obs': '회차와 구역은 거의 모든 글에 있고, 열·캐스팅은 일부 글에만 있어요.',
     'ux': '회차·구역이 맞지 않으면 다른 조건은 판단할 필요가 없어요.',
     'hyp': '조건 입력을 회차 → 구역 → 열 순서로 두고, 캐스팅은 해당 공연에서만 물어요.',
     'sol': '조건 입력 순서 · 캐스팅은 해당 공연만', 'where': '08·09장'},
    {'title': '허용 범위를 함께 적는다',
     'stat': '18건', 'stat_note': "'비슷한 좌석', '○열까지 허용', '선호' 같은 표현 (분류 메모 기준)",
     'obs': '꼭 원하는 조건과 양보할 수 있는 조건을 한 글 안에 섞어 적었어요.',
     'ux': '사용자는 이미 필수와 선호를 구분하고 있어요. 모든 조건을 필수로 대조하면 맞는 상대가 사라져요.',
     'hyp': '조건마다 필수·선호·무관을 직접 고르게 하면, 필수만 맞아도 후보로 남겨 기회를 넓힐 수 있어요.',
     'sol': '중요도 3단계 + 양쪽 필수 조건 대조', 'where': '07·09장'},
    {'title': '과정과 결과는 글에 남지 않는다',
     'stat': '0건', 'stat_note': '교환 결과가 확인된 글 (21건 모두 알 수 없음)',
     'obs': '연락은 DM·오픈채팅으로 넘어가고(17건), 교환 방식은 18건이 적지 않았어요.',
     'ux': '실제 교환은 개인 채널에서 진행돼 진행 상황과 결과가 보이지 않아요. 불안 여부는 이 표본으로 알 수 없어요 (안전 표현 1건).',
     'hyp': '예매처 안에서 처리하고 단계마다 내 티켓 상태를 보여 주면 과정의 불확실성이 줄어들 거예요.',
     'sol': '수락과 완료를 나눈 상태 설계 · 최종 확인', 'where': '07장'},
]


def research():
    def row(label, text, strong=False, kind='gray'):
        return ('<div style="display: flex; flex-direction: column; gap: 4px"><span style="align-self: flex-start">%s</span>'
                '<span style="font-size: 15px; line-height: 1.55; color: %s; %s">%s</span></div>'
                % (badge(label, kind), '#191B22' if strong else '#4A4F5C', 'font-weight: 700' if strong else '', text))
    cols = []
    for k, it in enumerate(INSIGHTS, 1):
        cols.append(
            '<section style="background: #FFFFFF; border-radius: 24px; padding: 24px 24px 22px; display: flex; flex-direction: column; gap: 14px; min-width: 0">'
            '<div style="display: flex; align-items: center; gap: 10px"><span style="width: 32px; height: 32px; border-radius: 10px; background: #5B3DF5; color: #FFFFFF; font-size: 16px; font-weight: 900; display: flex; align-items: center; justify-content: center; flex-shrink: 0">%d</span>'
            '<b style="font-size: 20px; line-height: 1.3">%s</b></div>'
            '<div style="background: #F7F7FA; border-radius: 16px; padding: 14px 16px; display: flex; flex-direction: column; gap: 6px">'
            '<span style="display: flex; align-items: baseline; gap: 10px">%s<b style="font-size: 30px; font-weight: 900; color: #5B3DF5; line-height: 1.1">%s</b></span>'
            '<span style="font-size: 13px; line-height: 1.45; color: #5F6370">%s</span>'
            '<span style="font-size: 15px; line-height: 1.5; color: #191B22">%s</span></div>'
            '%s%s'
            '<div style="margin-top: auto; border-top: 1px solid #EEF0F3; padding-top: 12px; display: flex; align-items: center; gap: 8px">%s'
            '<span style="font-size: 15px; font-weight: 700; color: #3A26C4; line-height: 1.4">%s</span><span style="margin-left: auto; font-size: 13px; color: #5F6370; white-space: nowrap">%s</span></div>'
            '</section>' % (k, it['title'], badge('관찰 · 사실', 'green'), it['stat'], it['stat_note'], it['obs'],
                            row('UX 해석', it['ux']), row('디자인 가설', it['hyp'], strong=True, kind='purple'),
                            badge('솔루션', 'dark'), it['sol'], it['where']))
    limits = [
        ('연석 요청 0건', '21건 중 명시적 연석 요청은 없었어요. 원문을 확보하지 못한 검색 발췌와 다른 플랫폼 글은 표본에서 뺐어요 → 연석 만들기는 실험 기능으로 분리 (10장)'),
        ('표본의 한계', '목표 50건 중 21건 · 1인 분류 · 검색엔진 경유 수집 (X 로그인 제한). 경향을 보는 자료이고 일반화하지 않아요'),
        ('하지 않은 조사', '사용자 인터뷰·사용성 테스트는 미실시. AI 시뮬레이션(Nemotron 시나리오 8개)은 설계 점검용이라 사용자 근거로 쓰지 않았어요'),
    ]
    lim = ''.join('<div style="flex: 1; display: flex; flex-direction: column; gap: 4px; min-width: 0"><b style="font-size: 15px; color: #A3440B">%s</b>'
                  '<span style="font-size: 14px; line-height: 1.5; color: #4A4F5C">%s</span></div>' % (a, b) for a, b in limits)
    right = ('<span style="display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 700; color: #1F7A4D; background: #E6F6EE; padding: 10px 16px; border-radius: 999px; flex-shrink: 0">'
             '원본 분류표(엑셀) 행 단위 대조 완료</span>')
    inner = (header('04', CHIPS['p04-desk-research'], 'X 교환글 21건에서 찾은 <span style="color: #5B3DF5">네 가지 인사이트</span>',
                    '2026.11.18 수집한 X 공개 교환글 21건을 직접 분류했어요. <b style="color: #191B22">관찰</b>은 게시글에서 확인한 사실, '
                    '<b style="color: #191B22">해석·가설</b>은 디자이너의 판단이에요.', right, sub_w=1150)
             + '\n<div style="flex: 1; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 20px; min-height: 0">%s</div>\n' % ''.join(cols)
             + '<section aria-label="조사의 한계" style="background: #FFF9F4; border: 1px solid #FBE6D6; border-radius: 20px; padding: 16px 24px; display: flex; gap: 28px">%s</section>\n' % lim
             + footer(foot_right_main('04', '조사·인사이트')))
    set_body('p04-desk-research', frame('#F7F7FA', inner, gap=24))
    print('P04: 관찰 → 해석 → 가설 → 솔루션 (인사이트 4개)')


# ================================================================ 7. UX 전략 ① 문제와 설계 원칙 (P05)
PRINCIPLES = [
    ('조건이 여러 개라 맞는 상대를 찾기 어렵다', '인사이트 1·2', '조건을 구조화하고, 예매처가 양쪽 조건을 대조해 후보를 찾는다'),
    ('꼭 필요한 조건과 양보할 조건이 섞여 있다', '인사이트 3', '조건마다 중요도(필수·선호·무관)를 사용자가 직접 정한다. 고르지 않은 조건을 무관으로 처리하지 않는다'),
    ('연락과 처리가 개인 채널에서 이뤄져 과정이 보이지 않는다', '인사이트 4', '예매처 안에서 처리하고, 단계와 내 티켓 상태를 항상 보여 준다. 관객끼리 돈·연락을 주고받지 않는다'),
    ('연석 수요를 뒷받침할 근거가 없다', '연석 요청 0건', '핵심 기능과 분리한 실험 기능으로 두고, 제안 받기를 켠 관객에게만 제안한다'),
]
RULES = [
    ('같은 가격·등급끼리만 교환', '가상', 'gray', '차액 정산 없이 처리 단순화 (MVP)'),
    ('두 티켓을 한 번에 교체', '목표', 'purple', '도중에 좌석을 놓치지 않는 시스템 기능 필요'),
    ('제안 응답 기한 12시간', '가상', 'gray', '한 사람 때문에 다른 매칭이 막히지 않게'),
    ('교환은 공연당 1회', '가상', 'gray', '반복 교환으로 좌석을 독점하지 않게'),
    ('공연 전 신청 마감', '가상', 'gray', '마감 일수는 정하지 않았어요'),
    ('교환을 허용한 공연에만', '확인 필요', 'orange', '주최사·예매처의 허용 여부와 권한 범위'),
]


def strategy_principles():
    rows = ''.join(
        '<div style="flex: 1; display: grid; grid-template-columns: minmax(0, 1fr) 40px minmax(0, 1.25fr); align-items: center; gap: 12px; background: #F5F6F8; border-radius: 20px; padding: 18px 22px">'
        '<div style="display: flex; flex-direction: column; gap: 6px"><span style="display: flex; gap: 6px">%s%s</span><b style="font-size: 19px; line-height: 1.4">%s</b></div>'
        '<svg width="28" height="28" sc-camel-view-box="0 0 24 24" fill="none" stroke="#5B3DF5" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"></path><path d="M13 6l6 6-6 6"></path></svg>'
        '<div style="display: flex; flex-direction: column; gap: 6px"><span style="align-self: flex-start">%s</span><span style="font-size: 17px; line-height: 1.5; color: #191B22">%s</span></div></div>'
        % (badge('UX 문제', 'red'), badge(src, 'gray'), prob, badge('설계 원칙 %d' % k, 'purple'), pr)
        for k, (prob, src, pr) in enumerate(PRINCIPLES, 1))
    rules = ''.join(
        '<div style="display: flex; align-items: flex-start; gap: 12px; padding: 12px 0; border-top: 1px solid #EEF0F3"><span style="flex-shrink: 0; width: 64px">%s</span>'
        '<span style="display: flex; flex-direction: column; gap: 2px"><b style="font-size: 16px">%s</b><span style="font-size: 14px; line-height: 1.45; color: #5F6370">%s</span></span></div>'
        % (badge(tag, kind), name, why) for name, tag, kind, why in RULES)
    left = ('<section style="flex: 1.75; display: flex; flex-direction: column; gap: 12px; min-width: 0">'
            '<h2 style="margin: 0; font-size: 22px; font-weight: 700">발견한 문제 → 설계 원칙</h2>%s</section>' % rows)
    right = ('<section style="flex: 1; display: flex; flex-direction: column; gap: 14px; min-width: 0">'
             '<div style="background: #191B22; border-radius: 24px; padding: 26px 28px; color: #FFFFFF; display: flex; flex-direction: column; gap: 10px">'
             '<span style="font-size: 14px; font-weight: 700; letter-spacing: 1px; color: #B7A9FF">핵심 원칙 · 가정</span>'
             '<p style="margin: 0; font-size: 24px; font-weight: 700; line-height: 1.45">교환은 <span style="color: #B7A9FF">예매처가</span> 처리하고, 관객끼리는 <span style="color: #B7A9FF">돈도 연락도</span> 주고받지 않아요.</p></div>'
             '<div style="flex: 1; background: #FFFFFF; border: 1px solid #E6E8EC; border-radius: 24px; padding: 20px 26px 8px; display: flex; flex-direction: column">'
             '<div style="display: flex; align-items: center; justify-content: space-between; padding-bottom: 10px"><b style="font-size: 18px">원칙을 지키는 규칙과 제약</b>%s</div>%s</div></section>'
             % (badge('공식 확인 0건', 'orange'), rules))
    inner = (header('05', CHIPS['p05-policy'], '발견한 문제를 <span style="color: #5B3DF5">설계 원칙</span>으로 바꿨어요',
                    '인사이트에서 나온 UX 문제마다 지켜야 할 원칙을 정했어요. 규칙 값은 공식 정책이 아니라 프로토타입을 위해 정한 것이에요.')
             + '\n<div style="flex: 1; display: flex; gap: 24px; min-height: 0">%s%s</div>\n' % (left, right)
             + footer(foot_right_main('05', '전략')))
    set_body('p05-policy', frame('#FFFFFF', inner, gap=32))
    print('P05: UX 문제 → 설계 원칙 + 규칙·제약')


# ================================================================ 8. UX 전략 ② 사용자 여정과 기능 구조 (P06): 프로토타입과 일치시키기
def journey():
    t = read('p06-user-flow')
    pairs = [
        ('<b>조건 등록</b><br><span style="font-size: 13px; color: #5F6370">회차·구역·열 선택</span>', '<b>조건 등록</b><br><span style="font-size: 13px; color: #5F6370">회차·구역·열 + 중요도</span>'),
        ('<b>매칭 대기</b><br>', '<b>후보 확인</b><br>'),
        ('>내 티켓은 계속 유효<', '>양쪽 조건 대조<'),
        ('<b>교환 제안 확인</b><br>', '<b>비교 · 제안</b><br>'),
        ('>응답 기한 (가상 규칙)<', '>전후 비교 + 내 동의<'),
        ('>양쪽 수락?<', '>상대 수락?<'),
        ('<b>새 티켓 발급</b><br>', '<b>최종 확인</b><br>'),
        ('>최종 확인 후 기존 티켓 무효<', '>통과 → 새 티켓 · 실패 → 기존 유지<'),
        ('<b>모을 방향 선택</b><br>', '<b>유지할 좌석 선택</b><br>'),
        ('>방향별 좌석 변화 안내<', '>방향별 좌석 변화 안내<'),
        ('<b>옆자리에 제안</b><br>', '<b>옆자리 후보 확인</b><br>'),
        ('>동의한 관객에게만 (가정)<', '>제안 받기를 켠 관객만<'),
        ('<b>응답 대기</b><br>', '<b>후보 1명에게 제안</b><br>'),
        ('>먼저 수락한 1명과 최종 확인<', '>전후 비교 + 동행 확인<'),
        ('<b>옆자리 관객 확인</b><br>', '<b>옆자리 관객 응답</b><br>'),
        ('>좌석 변경 제안 받음<', '>제안 검토 후 수락·거절<'),
        ('>누군가 수락?<', '>상대 수락?<'),
        ('>모두 거절 → 방향 바꾸기<', '>거절 → 다른 후보·방향 선택<'),
        ('>두 가지 교환 흐름, <', '>두 가지 교환 흐름, <'),
        ('>하나의 발급 단계<', '>하나의 최종 확인<'),
        ('좌석·회차 교환은 조건 매칭으로, 연석 만들기는 옆자리 관객에게 직접 제안하는 방식으로 상대를 찾아요. 마지막 교환은 모두 예매처가 처리해요.',
         '좌석·회차 교환은 조건 매칭으로, 연석 만들기는 옆자리 관객에게 직접 제안해 상대를 찾아요. 두 흐름 모두 상대가 수락한 뒤 예매처의 최종 확인을 거쳐야 완료돼요.'),
    ]
    for old, new in pairs:
        if t.count(old) != 1:
            sys.exit('p06: 치환 대상 %d회 (%s)' % (t.count(old), old))
        t = t.replace(old, new)
    write('p06-user-flow', t)
    print('P06: 여정 노드를 프로토타입과 일치 (후보 1명 선택, 최종 확인·실패 분기)')


# ================================================================ 9. UX 전략 ③ 핵심 의사결정 (P07)
DECISIONS = [
    {'no': '결정 1', 'title': '후보는 양쪽 필수 조건이 모두 맞을 때만',
     'what': '내 필수 조건과 상대의 필수 조건을 각각 대조해요. 선호가 다르면 후보로 두고 차이를 보여 줘요.',
     'why': '사용자는 필수와 선호를 섞어 적어요 (인사이트 3). 한쪽 조건만 맞추면 상대가 원하지 않는 제안이 생겨요.',
     'alt': '버린 대안: 내 조건만 맞으면 후보로 보여 주기',
     'ui': ('필수 조건: 양쪽 모두 충족', [('매칭 완료 아님', 'orange')]), 'where': '09장 · 양방향 조건 확인',
     'chips': [('후보 발견', 'purple'), ('≠ 매칭 완료', 'gray')]},
    {'no': '결정 2', 'title': '수락과 완료는 다른 상태',
     'what': '양쪽이 명시적으로 수락한 뒤에도 최종 확인(티켓·조건·정책)을 통과해야 교환 완료를 표시해요.',
     'why': '교환 과정과 결과가 보이지 않는 것이 문제였어요 (인사이트 4). 수락 즉시 완료로 보이면 그 뒤의 실패를 설명할 수 없어요.',
     'alt': '버린 대안: 상대가 수락하면 바로 교환 완료',
     'ui': ('상대방이 제안을 수락했어요', [('제안 수락', 'green'), ('→ 최종 확인 중', 'orange')]), 'where': '부록 A · 처리 상태',
     'chips': [('제안 수락', 'green'), ('≠ 교환 완료', 'gray')]},
    {'no': '결정 3', 'title': '어떤 실패에도 내 티켓은 그대로',
     'what': '거절·취소·시간 초과·최종 확인 실패에서 원래 티켓을 유지해요. 모든 단계에 내 티켓 상태를 함께 보여 줘요.',
     'why': '손해 없는 시도여야 교환을 시작할 수 있다고 봤어요 (가설). 두 티켓을 한 번에 처리하는 시스템 기능이 전제예요.',
     'alt': '제약: 원 티켓 유지는 목표 UX·시스템 요구사항',
     'ui': ('교환은 진행되지 않았어요. 내 티켓은 그대로 유지돼요 (목표).', [('실패', 'red')]), 'where': '부록 B · 최종 확인 실패',
     'chips': [('실패', 'red'), ('내 티켓 유지 · 목표', 'purple')]},
]
STATES = [('교환 신청', 'purple'), ('후보 발견', 'purple'), ('제안 전송', 'purple'), ('상대방 검토', 'orange'),
          ('제안 수락', 'green'), ('최종 확인 중', 'orange'), ('교환 완료', 'dark')]


def decisions():
    cards = ''.join(
        '<section style="background: #FFFFFF; border: 1px solid #E6E8EC; border-radius: 24px; padding: 24px 26px; display: flex; flex-direction: column; gap: 12px; min-width: 0">'
        '<span style="display: flex; align-items: center; gap: 8px">%s%s</span>'
        '<b style="font-size: 23px; line-height: 1.35">%s</b>'
        '<span style="font-size: 16px; line-height: 1.6; color: #191B22">%s</span>'
        '<div style="background: #F7F7FA; border-radius: 14px; padding: 12px 14px; display: flex; flex-direction: column; gap: 6px">'
        '<b style="font-size: 13px; color: #5F6370">근거</b><span style="font-size: 15px; line-height: 1.55; color: #4A4F5C">%s</span></div>'
        '<div style="margin-top: auto; border: 1.5px dashed #DCD5FF; border-radius: 14px; padding: 12px 14px; display: flex; flex-direction: column; gap: 8px">'
        '<span style="display: flex; justify-content: space-between; gap: 8px"><b style="font-size: 13px; color: #5B3DF5">화면에서는</b><span style="font-size: 13px; color: #5F6370">%s</span></span>'
        '<span style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap">%s<span style="font-size: 15px; font-weight: 700; color: #191B22">%s</span></span></div>'
        '<span style="font-size: 14px; color: #5F6370">%s</span></section>'
        % (badge(d['no'], 'dark'), ''.join(badge(a, b) for a, b in d['chips']), d['title'], d['what'], d['why'],
           d['where'], ''.join(badge(a, b) for a, b in d['ui'][1]), d['ui'][0], d['alt'])
        for d in DECISIONS)
    arrow = '<svg width="18" height="18" sc-camel-view-box="0 0 24 24" fill="none" stroke="#8B909C" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="flex-shrink: 0"><path d="M5 12h14"></path><path d="M13 6l6 6-6 6"></path></svg>'
    states = arrow.join(
        '<span style="flex: 1; display: flex; flex-direction: column; gap: 6px; align-items: flex-start; min-width: 0">%s<span style="font-size: 12px; font-weight: 700; color: #5F6370">%s</span></span>'
        % (badge(s, k), '새 티켓 (시연)' if s == '교환 완료' else '내 티켓: 유효') for s, k in STATES)
    exc = ''.join(badge(s, k) for s, k in [('거절', 'red'), ('취소', 'gray'), ('시간 초과', 'gray'), ('최종 확인 실패', 'red')])
    track_box = ('<section style="background: #FAF9FF; border: 1px solid #ECE8FF; border-radius: 24px; padding: 20px 26px; display: flex; flex-direction: column; gap: 14px">'
                 '<div style="display: flex; align-items: center; justify-content: space-between"><b style="font-size: 18px">결정이 만든 상태 흐름 · 좌석·회차 교환</b>'
                 '<span style="font-size: 14px; color: #5F6370">화면별 상세는 부록 A · 예외 6종은 부록 B</span></div>'
                 '<div style="display: flex; align-items: center; gap: 10px">%s</div>'
                 '<div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap; border-top: 1px dashed #DCD5FF; padding-top: 12px">%s'
                 '<span style="font-size: 15px; color: #191B22">어느 단계에서 멈춰도 <b>내 티켓은 그대로</b>예요 (최종 확인 실패는 목표).</span>'
                 '<span style="margin-left: auto; font-size: 14px; color: #5F6370">연석 만들기도 같은 상태를 따르고, 앞에 수신 의향·인접 확인이 붙어요 (10장)</span></div></section>'
                 % (states, exc))
    inner = (header('07', CHIPS['p06b-state-flow'], '매칭·수락·완료를 <span style="color: #5B3DF5">따로 판정</span>해요',
                    '한쪽의 기대만으로 교환이 확정되지 않도록 세 가지를 결정했어요. 각 결정은 인사이트와 제약에서 나왔어요.')
             + '\n<div style="flex: 1; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; min-height: 0">%s</div>\n' % cards
             + track_box + '\n' + footer(foot_right_main('07', '전략')))
    set_body('p06b-state-flow', frame('#FFFFFF', inner, gap=28))
    print('P07: 핵심 의사결정 3개 + 상태 흐름')


# ================================================================ 10. 본문 솔루션·부록 보드의 문구
def board_texts():
    t = read('p07b-conditions-match')
    t = rep(t, [('<li style="display: flex; gap: 10px; align-items: flex-start; font-size: 16px; line-height: 1.55; color: #2B2E36"><span style="width: 8px; height: 8px; border-radius: 4px; background: #5B3DF5; margin-top: 9px; flex-shrink: 0"></span><span>판정과 데이터는 <b>시연용</b>이에요. 실제 예매처 정책 검증 결과가 아니에요 (서비스 설계 가정)</span></li>', '')], 'p07b')
    write('p07b-conditions-match', t)
    t = read('p07c-status')
    t = rep(t, [
        ('<h1 style="margin: 0; font-size: 48px; font-weight: 900; line-height: 1.25; letter-spacing: -1px">수락과 완료는 <span style="color: #5B3DF5">다른 상태</span>예요</h1>',
         '<h1 style="margin: 0; font-size: 48px; font-weight: 900; line-height: 1.25; letter-spacing: -1px">수락 뒤에도 <span style="color: #5B3DF5">최종 확인</span>이 남아요</h1>'),
        ('거절·취소·실패에서는 내 티켓이 그대로예요 (실패는 <b>목표 UX·시스템 요구사항</b>)', '거절·취소·실패에서는 내 티켓이 그대로예요 (실패는 <b>목표</b>)'),
        ('<li style="display: flex; gap: 10px; align-items: flex-start; font-size: 16px; line-height: 1.55; color: #2B2E36"><span style="width: 8px; height: 8px; border-radius: 4px; background: #5B3DF5; margin-top: 9px; flex-shrink: 0"></span><span>이 보드의 상태는 모두 <b>시연용 모의 데이터</b>예요. 실제 처리 기능은 없어요</span></li>', ''),
        ('실패하면 원 티켓 유지가 목표예요 (목표 UX)', '실패하면 원 티켓을 유지해요 (목표)'),
    ], 'p07c')
    write('p07c-status', t)
    t = read('p07d-exceptions')
    t = rep(t, [('원 티켓 유지가 목표예요 (목표 UX)', '원 티켓을 유지해요 (목표)')], 'p07d')
    write('p07d-exceptions', t)
    # 상태 컴포넌트 범례: 앱 화면의 실제 태그와 02장 범례에 맞춘다
    t = read('p09b-state-components')
    t = rep(t, [
        ('>시연·가정 표기</h2>', '>표기 범례 · 02장과 같음</h2>'),
        ('white-space: nowrap">시연용 모의 데이터</span><span style="font-size: 12px; color: #5F6370; text-align: right">모의 데이터 화면</span>',
         'white-space: nowrap">시연</span><span style="font-size: 12px; color: #5F6370; text-align: right">모의 데이터로 동작하는 화면</span>'),
        ('white-space: nowrap">서비스 설계 가정</span><span style="font-size: 12px; color: #5F6370; text-align: right">NOL 약관으로 확인 못한 기능</span>',
         'white-space: nowrap">가정</span><span style="font-size: 12px; color: #5F6370; text-align: right">서비스 설계 가정 (공식 정책 아님)</span>'),
        ('white-space: nowrap">가상 규칙</span><span style="font-size: 12px; color: #5F6370; text-align: right">12시간·1회 등 예시 값</span>',
         'white-space: nowrap">가상</span><span style="font-size: 12px; color: #5F6370; text-align: right">예시 규칙 값 (12시간·1회 등)</span>'),
        ('white-space: nowrap">목표 UX</span><span style="font-size: 12px; color: #5F6370; text-align: right">목표 UX·시스템 요구사항</span>',
         'white-space: nowrap">목표</span><span style="font-size: 12px; color: #5F6370; text-align: right">목표 UX·시스템 요구사항</span>'),
        ('white-space: nowrap">실험 기능 · 수요 미검증</span><span style="font-size: 12px; color: #5F6370; text-align: right">연석 만들기</span>',
         'white-space: nowrap">실험 기능</span><span style="font-size: 12px; color: #5F6370; text-align: right">수요 미검증 (연석 만들기)</span>'),
    ], 'p09b')
    write('p09b-state-components', t)
    t = read('p09-components')
    t = rep(t, [('어느 화면에서든 지금 단계를 바로 알 수 있게 했어요', '어느 화면에서든 지금 단계를 알아볼 수 있도록 설계했어요')], 'p09')
    write('p09-components', t)
    print('본문·부록 문구 정리 (P09·부록 A·B·D·E)')


# ================================================================ 11. 검증 · 한계 · 회고 (P16)
TESTS = [('매칭 판정 엔진', 33), ('연석 판정 엔진', 66), ('좌석·회차 교환 흐름', 184), ('연석 교환 흐름', 146),
         ('신청자·수신자 흐름', 104), ('시각·확대 보기', 61), ('보드 이동·링크', 57)]


def retrospective():
    def li(text, color='#5B3DF5'):
        return ('<li style="display: flex; gap: 10px; align-items: flex-start"><span style="width: 7px; height: 7px; border-radius: 4px; background: %s; margin-top: 9px; flex-shrink: 0"></span>'
                '<span>%s</span></li>' % (color, text))
    done = [
        '<b>좌석·회차 교환 체험</b> — 조건 등록 → 후보 확인 → 전후 비교·동의 → 상대 수락 → 최종 확인 → 완료·실패 (08장)',
        '<b>연석 교환 체험</b> — 신청자 A와 수신자 B 양쪽을 한 보드에서 시뮬레이션 (10장)',
        '<b>상태·예외</b> — 처리 상태 10개, 예외 6개 화면 (부록 A·B)',
        '<b>UX 라이팅</b> — 폰 화면의 보이는 글자 8,869자 → 7,100자 (−19.9%), 필수 안내는 유지',
    ]
    test_rows = ''.join('<span style="display: flex; justify-content: space-between; gap: 8px; font-size: 13px; color: #4A4F5C"><span>%s</span><b style="color: #191B22">%d</b></span>' % (n, c) for n, c in TESTS)
    not_yet = [
        ('사용자 인터뷰', '미실시'), ('사용성 테스트', '미실시'), ('이해도·교환 성공률', '측정 안 함'),
        ('실제 교환 수요 · 연석 수요', '근거 없음 (연석 요청 0건)'), ('NOL티켓 운영 정책·기술 연동', '확인 필요 (공식 확인 0건)'),
    ]
    nrows = ''.join('<div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 11px 0; border-top: 1px solid #F2E3D6">'
                    '<span style="font-size: 16px; color: #191B22">%s</span>%s</div>' % (a, badge(b, 'orange')) for a, b in not_yet)
    retro = [
        ('발견한 문제', 'X 교환은 여러 조건을 개인 채널에서 맞추는 일이었고, 진행 과정과 결과가 보이지 않았어요.'),
        ('설계한 것', '조건 중요도와 양방향 판정, 수락과 완료의 분리, 실패해도 내 티켓을 지키는 상태 흐름.'),
        ('선택의 근거와 제약', '21건 관찰에서 출발했지만 표본이 작고 정책을 확인하지 못해, 화면마다 사실·가정·가상 규칙을 나눠 표시했어요. 근거가 없는 연석은 실험 기능으로 분리했어요.'),
        ('다음에 할 일', 'NOL 약관·공연별 안내 원문 확인 → 교환 경험자 인터뷰 → 사용성 테스트 3~5명 (수락과 완료의 구분을 이해하는지, 조건 등록을 끝까지 하는지).'),
    ]
    rrows = ''.join('<div style="display: flex; flex-direction: column; gap: 4px"><b style="font-size: 15px; color: #C9BFFF">%s</b><span style="font-size: 16px; line-height: 1.55">%s</span></div>' % r for r in retro)
    col1 = ('<section style="flex: 1.15; background: #EFF8F3; border-radius: 28px; padding: 30px 32px; display: flex; flex-direction: column; gap: 14px; min-width: 0">'
            '<div style="display: flex; align-items: center; gap: 10px"><b style="font-size: 22px">구현·기술 검증</b>%s</div>'
            '<ul style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 10px; font-size: 16px; line-height: 1.55">%s</ul>'
            '<div style="margin-top: auto; background: #FFFFFF; border-radius: 18px; padding: 16px 18px; display: flex; flex-direction: column; gap: 6px">'
            '<span style="display: flex; align-items: center; justify-content: space-between"><b style="font-size: 15px">자동 점검 7개 묶음 · 마지막 실행 실패 0</b>%s</span>'
            '<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 24px">%s</div>'
            '<span style="font-size: 13px; line-height: 1.5; color: #5F6370">묶음별 점검 항목 수예요. 같은 화면을 여러 묶음이 함께 점검해 합산하지 않아요. 화면이 의도대로 동작하는지 본 것이고 사용성 검증이 아니에요.</span></div></section>'
            % (badge('완료', 'green'), ''.join(li(x, '#1F7A4D') for x in done), badge('기술 검증', 'gray'), test_rows))
    col2 = ('<section style="flex: 0.85; background: #FFF9F4; border-radius: 28px; padding: 30px 32px; display: flex; flex-direction: column; gap: 8px; min-width: 0">'
            '<b style="font-size: 22px; padding-bottom: 6px">아직 검증하지 않은 것</b>%s'
            '<p style="margin: 8px 0 0; font-size: 15px; line-height: 1.6; color: #6B3A12">그래서 이 프로젝트는 효과를 주장하지 않아요. 성공률·만족도 같은 결과 수치는 없어요.</p></section>' % nrows)
    col3 = ('<section style="flex: 1.1; background: #5B3DF5; border-radius: 28px; padding: 30px 32px; display: flex; flex-direction: column; gap: 16px; color: #FFFFFF; min-width: 0">'
            '<b style="font-size: 22px">회고</b>%s</section>' % rrows)
    inner = (header('11', CHIPS['p10-retrospective'], '무엇을 확인했고, <span style="color: #5B3DF5">무엇이 남았나</span>',
                    '동작하는 프로토타입과 자동 점검으로 설계가 의도대로 작동하는지는 확인했어요. 사람에게 맞는지는 아직 확인하지 못했어요.')
             + '\n<div style="flex: 1; display: flex; gap: 20px; min-height: 0">%s%s%s</div>\n' % (col1, col2, col3)
             + footer(foot_right_main('11', '검증·회고')))
    set_body('p10-retrospective', frame('#FFFFFF', inner, gap=32))
    print('P16: 검증·한계·회고')


if __name__ == '__main__':
    placeholders()
    overview()
    problem()
    research()
    strategy_principles()
    journey()
    decisions()
    board_texts()
    retrospective()
    renumber_all()
    template()
