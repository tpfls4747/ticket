#!/usr/bin/env python3
"""모의 데이터의 날짜·요일·회차 번호를 2026년 달력에 맞춘다 (STEP 2C, 1회성 보정 스크립트).

- "MM.DD (요일)" 의 요일을 2026년 실제 요일로 고친다. (2026-12-20 은 일요일)
- 회차 번호를 시간순으로 고정한다:
    12.19 19:30 = 1회차, 12.20 14:00 = 2회차, 12.20 18:00 = 3회차, 12.21 14:00 = 4회차
사용법: python3 tools/authoring/fix_dates_2026.py   (이미 보정된 파일은 바뀌지 않는다)
"""
import datetime, glob, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WD = '월화수목금토일'
PAT = re.compile(r'(\d{1,2})\.(\d{1,2}) ?\(([월화수목금토일])\)')
ROUNDS = {('12.19', '19:30'): 1, ('12.20', '14:00'): 2, ('12.20', '18:00'): 3, ('12.21', '14:00'): 4}
PAT_ROUND = re.compile(r'(\d{2}\.\d{2}) \([월화수목금토일]\) (\d{2}:\d{2}) · \d회차')


def fix(text):
    def wd(m):
        d = datetime.date(2026, int(m.group(1)), int(m.group(2)))
        return '%s.%s (%s)' % (m.group(1), m.group(2), WD[d.weekday()])
    text = PAT.sub(wd, text)
    def rnd(m):
        n = ROUNDS.get((m.group(1), m.group(2)))
        return m.group(0) if n is None else re.sub(r'\d회차', '%d회차' % n, m.group(0))
    return PAT_ROUND.sub(rnd, text)


if __name__ == '__main__':
    changed = 0
    for f in sorted(glob.glob(str(ROOT / 'src/pages/*/page.html')) + glob.glob(str(ROOT / 'src/components/*/*.html'))):
        t = Path(f).read_text(encoding='utf-8')
        n = fix(t)
        if n != t:
            Path(f).write_text(n, encoding='utf-8')
            changed += 1
            print('보정:', Path(f).relative_to(ROOT))
    print('파일 %d개 보정' % changed)
