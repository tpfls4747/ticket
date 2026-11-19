#!/usr/bin/env bash
# 원본을 2회(기준선), 대상 번들을 1회 렌더링한 뒤 비교한다.
# 사용법: bash tools/run_verification.sh [출력 디렉터리, 기본 verify/results] [대상 번들, 기본 dist/ticket-exchange-portfolio.html]
# 출력 디렉터리는 비어 있거나 존재하지 않아야 한다 (이전 결과가 섞이는 것을 막기 위해).
# 대상이 문구를 바꾼 빌드라면 DOM·텍스트·스크린샷 비교는 의도한 차이로 실패한다.
# 그 경우에는 원본이 아니라 변경 직전 빌드와 tools/compare_structure.py 로 구조를 비교한다.
set -u
cd "$(dirname "$0")/.."
OUT="${1:-verify/results}"
NEW="${2:-dist/ticket-exchange-portfolio.html}"
if [ -e "$OUT" ] && [ -n "$(ls -A "$OUT" 2>/dev/null)" ]; then
  echo "출력 디렉터리 $OUT 가 비어 있지 않습니다. 다른 경로를 지정하세요." >&2
  exit 2
fi
ORIG="original/티켓 교환 UX UI 포트폴리오.html"
mkdir -p "$OUT"
node tools/verify_render.cjs "$ORIG" "$OUT/original"        || exit 1
node tools/verify_render.cjs "$ORIG" "$OUT/original_repeat" || exit 1
node tools/verify_render.cjs "$NEW"  "$OUT/rebundled"       || exit 1
echo "######## 기준선: 원본 vs 원본(재실행)" | tee "$OUT/comparison.txt"
python3 tools/compare_render.py "$OUT/original" "$OUT/original_repeat" | tee -a "$OUT/comparison.txt"
echo "######## 본 비교: 원본 vs 대상 번들 ($NEW)" | tee -a "$OUT/comparison.txt"
python3 tools/compare_render.py "$OUT/original" "$OUT/rebundled" --diff-dir "$OUT/diffs" | tee -a "$OUT/comparison.txt"
