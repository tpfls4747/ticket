"""STEP 2C 화면 작성용 공용 부품 (1회성 작성 보조 도구).

기존 .dc.html 컴포넌트의 구조·토큰(색, 글자 크기, 라운드)을 그대로 따른다.
생성된 결과물은 src/ 에 들어가며, 이후에는 src/ 가 원본이다 (이 도구를 다시 돌려 덮어쓰지 말 것).
"""

# ---- 디자인 토큰 (기존 컴포넌트에서 쓰던 값만 사용) -------------------------------------------
PRIMARY, PRIMARY_DARK, SOFT, SOFT2 = '#5B3DF5', '#3A26C4', '#F0EDFF', '#E9E5FF'
TEXT, SUB, SUB2 = '#191B22', '#5F6370', '#4A4F5C'
LINE, BG, BG2 = '#E6E8EC', '#F5F6F8', '#EEF0F3'
OK, OK_BG = '#1F7A4D', '#E6F6EE'
WARN, WARN_BG, WARN_FG = '#D9620F', '#FFF1E6', '#A3440B'
BAD, BAD_BG = '#B03A3A', '#FDF0F0'

ICONS = {
    'check': '<path d="M5 12l5 5L19 7"/>',
    'x': '<path d="M18 6L6 18"/><path d="M6 6l12 12"/>',
    'q': '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.2a2.5 2.5 0 1 1 3.6 2.2c-.8.4-1.2 1-1.2 1.8"/><path d="M12 17h.01"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'dash': '<path d="M6 12h12"/>',
    'dot': '<circle cx="12" cy="12" r="4"/>',
    'slash': '<circle cx="12" cy="12" r="9"/><path d="M6 6l12 12"/>',
    'info': '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
    'swap': '<path d="M7 4l-4 4 4 4"/><path d="M3 8h14"/><path d="M17 20l4-4-4-4"/><path d="M21 16H7"/>',
    'back': '<path d="M15 18l-6-6 6-6"/>',
    'down': '<path d="M12 5v14"/><path d="M6 13l6 6 6-6"/>',
    'arrow': '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
    'lock': '<rect x="4" y="11" width="16" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
}


def icon(name, color, size=14, sw=2.5):
    return ('<svg width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="%s" stroke-width="%s" '
            'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="flex-shrink: 0">%s</svg>'
            % (size, size, color, sw, ICONS[name]))


# ---- 상태 배지: 색 + 아이콘 + 텍스트 (색만으로 구분하지 않는다) ---------------------------------
KINDS = {
    'ok':    (OK, OK_BG, 'check', None),
    'need':  (WARN_FG, WARN_BG, 'q', None),
    'no':    (BAD, BAD_BG, 'x', None),
    'plan':  (PRIMARY_DARK, SOFT2, 'dot', None),
    'wait':  (WARN_FG, WARN_BG, 'clock', None),
    'mute':  (SUB2, '#F0F1F4', 'dash', None),
    'cancel': (SUB2, '#F0F1F4', 'slash', None),
    'done':  ('#FFFFFF', OK, 'check', OK),
    'fail':  ('#FFFFFF', BAD, 'x', BAD),
}


def badge(kind, text, size=12):
    fg, bg, ic, border = KINDS[kind]
    b = 'border: 1px solid %s; ' % border if border else ''
    return ('<span style="display: inline-flex; align-items: center; gap: 4px; font-size: %dpx; font-weight: 700; '
            'color: %s; background: %s; %spadding: 4px 8px; border-radius: 6px; white-space: nowrap">%s%s</span>'
            % (size, fg, bg, b, icon(ic, fg, 12, 3), text))


def tag(text, fg=SUB2, bg='#F0F1F4'):
    return ('<span style="font-size: 11px; font-weight: 700; color: %s; background: %s; padding: 2px 6px; '
            'border-radius: 4px; white-space: nowrap">%s</span>' % (fg, bg, text))


SIM_TAG = tag('시연용 모의 데이터')
ASSUME_TAG = tag('서비스 설계 가정', PRIMARY_DARK, SOFT2)
VIRTUAL_TAG = tag('가상 규칙')
NEED_TAG = tag('확인 필요', WARN_FG, WARN_BG)
GOAL_TAG = tag('목표 UX', PRIMARY_DARK, SOFT2)

IMPORTANCE = {'필수': ('#FFFFFF', TEXT), '선호': (PRIMARY_DARK, SOFT2), '무관': (SUB2, '#E6E8EC')}


def importance_seg(selected):
    """필수/선호/무관 선택기. selected=None 이면 '선택 필요' 상태(어느 것도 기본 선택하지 않음)."""
    parts = []
    for name in ('필수', '선호', '무관'):
        if name == selected:
            fg, bg = IMPORTANCE[name]
            st = 'background: %s; color: %s; font-weight: 700; border: 1px solid %s' % (bg, fg, bg)
        else:
            st = 'background: #FFFFFF; color: %s; font-weight: 500; border: 1px solid #DADDE3' % SUB2
        parts.append('<button type="button" aria-pressed="%s" style="height: 28px; padding: 0 10px; font-family: inherit; '
                     'font-size: 12px; border-radius: 8px; %s">%s</button>'
                     % ('true' if name == selected else 'false', st, name))
    wrap = ('display: flex; gap: 4px; padding: 3px; border-radius: 11px; border: 1.5px dashed %s; background: #FFF8F2' % WARN
            if selected is None else 'display: flex; gap: 4px')
    return '<span style="%s">%s</span>' % (wrap, ''.join(parts))


def importance_tag(name):
    fg, bg = IMPORTANCE[name]
    return ('<span style="font-size: 11px; font-weight: 700; color: %s; background: %s; padding: 2px 6px; border-radius: 4px">%s</span>'
            % (fg, bg, name))


# ---- 화면 틀 -------------------------------------------------------------------------------
def screen(title, header, main, footer='', gap=14, pad='4px 20px 16px', bg='#FFFFFF', back=True):
    head_back = ('<span aria-hidden="true" style="width: 44px; height: 44px; display: flex; align-items: center; justify-content: center">%s</span>'
                 % icon('back', TEXT, 24, 2)) if back else '<span style="width: 12px"></span>'
    foot = ('<footer style="padding: 12px 20px 28px; display: flex; flex-direction: column; gap: 10px; flex-shrink: 0; '
            'border-top: 1px solid #EEF0F3">%s</footer>' % footer) if footer else ''
    return f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&amp;display=swap">
<style>
body{{margin:0}}
a{{color:#5B3DF5}}a:hover{{color:#4328D9}}
</style>
</helmet>
<div style="width: 390px; height: 844px; box-sizing: border-box; background: {bg}; font-family: 'Noto Sans KR', sans-serif; color: {TEXT}; display: flex; flex-direction: column; overflow: hidden">
<header style="height: 56px; display: flex; align-items: center; gap: 4px; padding: 0 8px; flex-shrink: 0">
{head_back}
<h1 style="margin: 0; font-size: 18px; font-weight: 700">{header}</h1>
</header>
<main style="flex: 1; display: flex; flex-direction: column; gap: {gap}px; padding: {pad}; overflow: hidden">
{main}
</main>
{foot}
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":390,"height":844}}}}'>
class Component extends DCLogic {{
renderVals() {{
return {{}};
}}
}}
</script>
</body>
</html>
'''


# ---- 자주 쓰는 블록 ----------------------------------------------------------------------
def banner(text, kind='info'):
    fg, bg, ic = {'info': (SUB2, BG, 'info'), 'warn': (WARN_FG, WARN_BG, 'info'), 'plan': (PRIMARY_DARK, SOFT, 'info'),
                  'bad': (BAD, BAD_BG, 'info'), 'ok': (OK, OK_BG, 'check')}[kind]
    return ('<div style="display: flex; gap: 8px; align-items: flex-start; background: %s; border-radius: 12px; padding: 10px 12px">'
            '%s<p style="margin: 0; font-size: 12px; line-height: 1.5; color: %s">%s</p></div>' % (bg, icon(ic, fg, 14, 2.2), fg, text))


def h2(text, right=''):
    return ('<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px">'
            '<h2 style="margin: 0; font-size: 15px; font-weight: 700">%s</h2>%s</div>' % (text, right))


def cta(text, kind='primary', disabled=False):
    if disabled:
        st = 'background: #E6E8EC; color: #8B909C; border: 0'
    elif kind == 'primary':
        st = 'background: #5B3DF5; color: #FFFFFF; border: 0'
    elif kind == 'dark':
        st = 'background: #191B22; color: #FFFFFF; border: 0'
    else:
        st = 'background: #FFFFFF; color: #4A4F5C; border: 1px solid #DADDE3'
    return ('<button type="button"%s style="height: 50px; border-radius: 14px; font-family: inherit; font-size: 15px; font-weight: 700; %s">%s</button>'
            % (' disabled' if disabled else '', st, text))


def small_btn(text, kind='primary'):
    st = ('background: #5B3DF5; color: #FFFFFF; border: 0' if kind == 'primary'
          else 'background: #FFFFFF; color: #3A26C4; border: 1px solid #C9BFFF')
    return ('<button type="button" style="height: 36px; padding: 0 14px; border-radius: 10px; font-family: inherit; '
            'font-size: 13px; font-weight: 700; %s">%s</button>' % (st, text))


def ticket_row(label, value, strong=False, accent=False):
    border = 'border: 1.5px solid #5B3DF5; background: #F7F5FF' if accent else 'border: 1px solid #E6E8EC'
    lab = PRIMARY_DARK if accent else SUB
    return ('<div style="%s; border-radius: 14px; padding: 10px 14px; display: flex; flex-direction: column; gap: 2px">'
            '<span style="font-size: 11px; font-weight: 700; color: %s">%s</span>'
            '<span style="font-size: %dpx; font-weight: %d">%s</span></div>'
            % (border, lab, label, 14 if strong else 13, 700 if strong else 500, value))


def timeline(steps):
    """steps: [(label, sub, state)], state in done|now|todo|fail|stop"""
    out = []
    n = len(steps)
    for i, (label, sub, st) in enumerate(steps):
        if st == 'done':
            dot = '<span style="width: 22px; height: 22px; border-radius: 11px; background: %s; display: flex; align-items: center; justify-content: center; flex-shrink: 0">%s</span>' % (OK, icon('check', '#FFFFFF', 12, 3.5))
            col = TEXT
        elif st == 'now':
            dot = '<span style="width: 22px; height: 22px; border-radius: 11px; border: 2px solid %s; background: #FFFFFF; box-sizing: border-box; display: flex; align-items: center; justify-content: center; flex-shrink: 0"><span style="width: 8px; height: 8px; border-radius: 4px; background: %s"></span></span>' % (PRIMARY, PRIMARY)
            col = PRIMARY_DARK
        elif st == 'fail':
            dot = '<span style="width: 22px; height: 22px; border-radius: 11px; background: %s; display: flex; align-items: center; justify-content: center; flex-shrink: 0">%s</span>' % (BAD, icon('x', '#FFFFFF', 12, 3.5))
            col = BAD
        elif st == 'stop':
            dot = '<span style="width: 22px; height: 22px; border-radius: 11px; background: #8B909C; display: flex; align-items: center; justify-content: center; flex-shrink: 0">%s</span>' % icon('dash', '#FFFFFF', 12, 3.5)
            col = SUB
        else:
            dot = '<span style="width: 22px; height: 22px; border-radius: 11px; border: 2px solid #DADDE3; background: #FFFFFF; box-sizing: border-box; flex-shrink: 0"></span>'
            col = '#8B909C'
        line = '' if i == n - 1 else '<span style="position: absolute; left: 10px; top: 24px; bottom: -8px; width: 2px; background: #E6E8EC"></span>'
        st_txt = {'done': '완료', 'now': '지금 단계', 'todo': '남은 단계', 'fail': '실패', 'stop': '중단'}[st]
        out.append('<li style="position: relative; display: flex; gap: 12px; align-items: flex-start; padding-bottom: 12px">%s%s'
                   '<span style="display: flex; flex-direction: column; gap: 1px"><span style="font-size: 14px; font-weight: 700; color: %s">%s <span style="font-size: 11px; font-weight: 500; color: %s">· %s</span></span>'
                   '<span style="font-size: 12px; line-height: 1.45; color: %s">%s</span></span></li>'
                   % (line, dot, col, label, col, st_txt, SUB, sub))
    return '<ol aria-label="진행 단계" style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column">%s</ol>' % ''.join(out)


def result_row(label, mine, imp, res_kind, res_text, note=''):
    """조건 한 줄: 조건명 · 중요도 · 상대 티켓 값 · 결과 배지(+설명)"""
    n = ('<span style="font-size: 12px; line-height: 1.45; color: %s">%s</span>' % (SUB, note)) if note else ''
    return ('<div style="display: flex; flex-direction: column; gap: 4px; padding: 8px 0; border-top: 1px solid #EEF0F3">'
            '<div style="display: flex; align-items: center; justify-content: space-between; gap: 8px">'
            '<span style="display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700">%s%s</span>%s</div>'
            '<span style="font-size: 12px; color: %s">%s</span>%s</div>'
            % (label, importance_tag(imp) if imp in IMPORTANCE else tag(imp), badge(res_kind, res_text), SUB2, mine, n))


def result_row_c(label, detail, imp, res_kind, res_text, note=''):
    """compact 조건 한 줄: [조건명 중요도 ........ 결과 배지] + 한 줄 설명(+선택 설명)"""
    n = ('<span style="font-size: 11px; line-height: 1.4; color: %s">%s</span>' % (SUB, note)) if note else ''
    return ('<div style="display: flex; flex-direction: column; gap: 2px; padding: 5px 0; border-top: 1px solid #EEF0F3">'
            '<div style="display: flex; align-items: center; justify-content: space-between; gap: 6px">'
            '<span style="display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700">%s%s</span>%s</div>'
            '<span style="font-size: 11px; line-height: 1.4; color: %s">%s</span>%s</div>'
            % (label, importance_tag(imp) if imp in IMPORTANCE else tag(imp), badge(res_kind, res_text, 11), SUB2, detail, n))
