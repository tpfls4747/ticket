#!/usr/bin/env python3
"""verify_render.cjs 수집물 두 벌을 비교한다.

사용법: python3 tools/compare_render.py <기준 디렉터리> <대상 디렉터리> [--diff-dir DIR]

분류:
  기능적 차이  : DOM/텍스트/핑거프린트/인터랙션/콘솔·네트워크/리소스 목록 불일치
  렌더링 노이즈: 위 항목은 모두 같은데 스크린샷 픽셀만 다른 경우 (폰트 안티앨리어싱 등)
  완전 일치    : 픽셀까지 동일
종료 코드: 기능적 차이가 있으면 1, 없으면 0.
"""
import json, sys
from pathlib import Path

import numpy as np
from PIL import Image


def load(d):
    return json.loads((d / "report.json").read_text(encoding="utf-8"))


def pixel_stats(a, b, diff_path=None):
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return {"size_a": ia.size, "size_b": ib.size, "same_size": False}
    xa, xb = np.asarray(ia, dtype=np.int16), np.asarray(ib, dtype=np.int16)
    d = np.abs(xa - xb).max(axis=2)
    n = int((d > 0).sum())
    st = {"same_size": True, "diff_pixels": n, "ratio": n / d.size,
          "max_channel_diff": int(d.max()), "px_over_32": int((d > 32).sum())}
    if n and diff_path:
        Path(diff_path).parent.mkdir(parents=True, exist_ok=True)
        vis = np.clip(d * 8, 0, 255).astype(np.uint8)
        Image.fromarray(vis).save(diff_path)
    return st


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    diff_dir = None
    if "--diff-dir" in sys.argv:
        diff_dir = Path(sys.argv[sys.argv.index("--diff-dir") + 1])
        args = [x for x in args if x != str(diff_dir)]
    A, B = Path(args[0]), Path(args[1])
    ra, rb = load(A), load(B)
    functional, notes = [], []

    def check(name, ok, detail=""):
        if not ok:
            functional.append((name, detail))

    # 루트
    for k in ("title", "boardTitles", "scrollHeight", "iframeRects", "scrollTops"):
        check("루트." + k, ra["root"].get(k) == rb["root"].get(k), "%s != %s" % (ra["root"].get(k), rb["root"].get(k)))
    check("모바일 스크롤 폭", ra["mobile"].get("rootScrollWidth") == rb["mobile"].get("rootScrollWidth"))
    for pid in ra["pages"]:
        pa, pb = ra["pages"][pid], rb["pages"][pid]
        check(pid + " DOM", (A / "dom" / (pid + ".html")).read_text() == (B / "dom" / (pid + ".html")).read_text())
        check(pid + " 텍스트", (A / "text" / (pid + ".txt")).read_text() == (B / "text" / (pid + ".txt")).read_text())
        # 폰트: unicode-range 서브셋은 지연 로드라 FontFace 개수가 실행마다 달라진다.
        # 따라서 (family, weight) 종류의 집합과 실패 여부로 비교하고, 개수는 참고용으로만 둔다.
        ia, ib = dict(pa["info"]), dict(pb["info"])
        fa, fb = set(ia.pop("fontsLoaded")), set(ib.pop("fontsLoaded"))
        check(pid + " 로드된 폰트 종류", fa == fb, "%s != %s" % (sorted(fa), sorted(fb)))
        check(pid + " info(폰트 제외)", ia == ib)
        # clicksInfoOnly(링크 클릭 결과)는 원본 자체가 실행마다 달라 비교에서 제외한다.
        # 클릭은 실제 마우스 클릭으로 수행하며 결과가 결정적이다(원본·재번들 반복 측정으로 확인).
        for k in ("fingerprint", "phoneFrames390x844", "interactive", "focusable", "controlSteps",
                  "firstLinkClick", "tabOrder"):
            check("%s %s" % (pid, k), pa[k] == pb[k])
        check(pid + " 폰 화면 구성", ra["phones"][pid] == rb["phones"][pid])
        check(pid + " 모바일 스크롤 위치", ra["mobile"][pid] == rb["mobile"][pid])
    check("콘솔/네트워크 로그 동일", ra["logs"] == rb["logs"], "%s vs %s" % (ra["logs"][:3], rb["logs"][:3]))

    # 스크린샷
    rows, noise, ident = [], 0, 0
    for sub in ("desktop", "phones", "mobile"):
        for pa_ in sorted((A / sub).glob("*.png")):
            if sub == "mobile" and not pa_.name.endswith("-viewport.png"):
                continue
            pb_ = B / sub / pa_.name
            if not pb_.exists():
                functional.append(("스크린샷 누락 " + sub + "/" + pa_.name, ""))
                continue
            st = pixel_stats(pa_, pb_, (diff_dir / sub / pa_.name) if diff_dir else None)
            if not st["same_size"]:
                functional.append(("스크린샷 크기 불일치 %s/%s" % (sub, pa_.name), str(st)))
            elif st["diff_pixels"] == 0:
                ident += 1
            else:
                noise += 1
            rows.append((sub + "/" + pa_.name, st))
        extra = {p.name for p in (B / sub).glob("*.png")} - {p.name for p in (A / sub).glob("*.png")}
        for e in sorted(extra):
            functional.append(("스크린샷 추가분 %s/%s" % (sub, e), ""))

    print("기준=%s 대상=%s" % (A, B))
    print("스크린샷 %d장: 완전 일치 %d, 픽셀 차이 있음(렌더링 노이즈 후보) %d" % (len(rows), ident, noise))
    # 분류 규칙: 구조·기능 항목이 모두 같고(functional 비어 있음), 차이 픽셀이 전체의 1% 미만이며
    # 최대 채널 차이가 64 이하이면 '렌더링 노이즈(글리프 안티앨리어싱 수준)', 아니면 '확인 필요'.
    for name, st in rows:
        if st.get("diff_pixels"):
            small = st["ratio"] < 0.01 and st["max_channel_diff"] <= 64
            label = "렌더링 노이즈" if (small and not functional) else "확인 필요"
            print("  [%s] %-30s 차이 픽셀 %d (%.4f%%) 최대 채널차 %d, 32 초과 %d" %
                  (label, name, st["diff_pixels"], st["ratio"] * 100, st["max_channel_diff"], st["px_over_32"]))
    print("구조·기능 항목 불일치: %d" % len(functional))
    for name, detail in functional:
        print("  [기능적 차이]", name, detail[:200])
    sys.exit(1 if functional else 0)


if __name__ == "__main__":
    main()
