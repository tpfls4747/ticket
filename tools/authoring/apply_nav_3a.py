"""STEP 3A: 폰 화면 링크를 '같은 자리 화면 전환'으로 정상화한다 (페이지 템플릿만 수정, vendor 무수정).

원인: 링크가 상대 경로(href="Request.dc.html")인데 페이지 프레임 문서가 blob:null/<uuid> 라서
상대 경로를 해석할 기준이 없다 (new URL() 가 Invalid URL). 브라우저는 해석에 실패한 이동을
about:blank#blocked 로 보낸다. 런타임(support.js)에는 화면 전환 기능이 없다.

해결: 각 폰 화면 틀(scale div)에 onclick 핸들러를 둔다. 자식 컴포넌트의 링크 클릭이 버블링되면
  - href 가 'X.dc.html' 이고 X 가 이 보드에 실제로 있는 화면이면 같은 자리에서 X 로 전환
  - 이 보드에 없는 화면이면 기본 이동만 막고 현재 화면 유지
  - aria-label="뒤로" 링크는 이전 화면이 있으면 그 화면으로, 없으면 링크가 가리키는 화면으로
  - Esc 키: 처음 화면으로
화면은 미리 모두 렌더링하고 display 로만 바꾼다 → 다른 화면에 다녀와도 입력 상태가 유지된다.
링크 href, 컴포넌트 파일, 문구는 바꾸지 않는다.

사용법: python3 tools/authoring/apply_nav_3a.py <slug> [<slug> ...]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# 보드별 설정: screens = 각 폰이 전환할 수 있는 화면(이 보드의 manifest 에 있는 것만), 비어 있으면 전환 없음(기본 이동만 막음)
CONFIG = {
    'p07-ui-exchange': ['Main', 'Request', 'Waiting', 'Match', 'Done', 'Expired'],
    'p08-ui-pair': ['PairMode', 'PairSeat', 'PairReceive', 'PairDone'],
    'p01-cover': [],
    'p07c-status': [],
}

HOST_RE = re.compile(
    r'(<div style="width: 390px; height: 844px; transform: scale\([0-9.]+\); transform-origin: top left">)'
    r'(\s*)<dc-import name="(\w+)" hint-size="390px,844px"></dc-import>(\s*)</div>')

LOGIC = r'''
class Component extends DCLogic {
constructor(props) {
super(props);
this.state = { stacks: INITIAL.map(function (s) { return [s]; }) };
}
navigate(i, e) {
var t = e && e.target;
var a = t && t.closest ? t.closest('a[href]') : null;
if (!a) return;
var href = a.getAttribute('href') || '';
var m = /^(?:\.\/)?([A-Za-z0-9_-]+)\.dc\.html$/.exec(href);
if (!m) return;
e.preventDefault();
var target = m[1];
var back = a.getAttribute('aria-label') === '뒤로';
var screens = HOSTS[i];
var hostEl = a.closest('[data-nav-host]');
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
}, function () {
// 화면이 바뀌면 누른 링크가 숨겨져 포커스가 사라지므로, 폰 틀로 포커스를 옮겨 키보드 위치를 유지한다
if (moved && hostEl && hostEl.focus) { try { hostEl.focus({ preventScroll: true }); } catch (err) { /* 무시 */ } }
});
}
keydown(i, e) {
if (e && e.key === 'Escape') {
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
var v = { nosubmit: function (e) { if (e && e.preventDefault) e.preventDefault(); } };
INITIAL.forEach(function (_, i) {
var cur = stacks[i][stacks[i].length - 1];
HOSTS[i].forEach(function (s) { v['v_' + i + '_' + s] = s === cur ? 'block' : 'none'; });
v['nav_' + i] = function (e) { self.navigate(i, e); };
v['key_' + i] = function (e) { self.keydown(i, e); };
});
return Object.assign({}, BASE_VALS(this), v);
}
}
'''


def apply(slug):
    path = ROOT / 'src' / 'pages' / slug / 'page.html'
    t = path.read_text(encoding='utf-8')
    if 'data-nav-host' in t:
        print('이미 적용됨:', slug)
        return
    screens = CONFIG[slug]
    initial, hosts = [], []

    def repl(m):
        i = len(initial)
        name = m.group(3)
        initial.append(name)
        hs = screens if screens else [name]
        if name not in hs:
            raise SystemExit('%s: 초기 화면 %s 가 화면 목록에 없음' % (slug, name))
        hosts.append(hs)
        # dc-import 의 style 은 런타임이 틀(sc-host)에 전달하지 않으므로 일반 div 로 감싸 표시를 바꾼다
        # 각 화면을 <form> 으로 감싼다: 같은 화면이 여러 폰에 있어도 라디오 그룹(name)이 화면 단위로 분리된다.
        # 기존 <button> 은 type 이 없어 제출 버튼으로 동작하므로 onsubmit 에서 제출을 막는다.
        imports = ''.join('<form data-nav-screen="%s" onsubmit="{{nosubmit}}" style="display: {{v_%d_%s}}; margin: 0"><dc-import name="%s" hint-size="390px,844px"></dc-import></form>' % (s, i, s, s) for s in hs)
        open_div = m.group(1).replace('<div ', '<div data-nav-host="%d" tabIndex="-1" onclick="{{nav_%d}}" onkeydown="{{key_%d}}" ' % (i, i, i), 1)
        open_div = open_div.replace('style="', 'style="outline: none; ', 1)
        return open_div + m.group(2) + imports + m.group(4) + '</div>'

    t2 = HOST_RE.sub(repl, t)
    if not initial:
        raise SystemExit('%s: 폰 화면 틀을 찾지 못함' % slug)
    head = 'var INITIAL = %s;\nvar HOSTS = %s;' % (json.dumps(initial), json.dumps(hosts))
    old_logic = re.search(r'class Component extends DCLogic \{\nrenderVals\(\) \{\nreturn \{\};\n\}\n\}\n', t2)
    if old_logic:
        base = 'function BASE_VALS(self) { return {}; }\n'
        t2 = t2.replace(old_logic.group(0), head + '\n' + base + LOGIC.lstrip('\n'))
    else:
        # 기존 로직(예: 표지의 좌석 장식)이 있으면 그대로 두고 기반 클래스로 쓴다
        if t2.count('class Component extends DCLogic {') != 1:
            raise SystemExit('%s: 로직 블록 구조를 알 수 없음' % slug)
        t2 = t2.replace('class Component extends DCLogic {', 'class BaseLogic extends DCLogic {', 1)
        end = t2.index('</script>', t2.index('class BaseLogic'))
        base = 'function BASE_VALS(self) { return BaseLogic.prototype.renderVals.call(self) || {}; }\n'
        t2 = t2[:end] + head + '\n' + base + LOGIC.lstrip('\n').replace('extends DCLogic', 'extends BaseLogic') + t2[end:]
    path.write_text(t2, encoding='utf-8')
    print('적용: %s (폰 %d개, 화면 %s)' % (slug, len(initial), screens or '자기 화면만'))


if __name__ == '__main__':
    for s in sys.argv[1:]:
        apply(s)
