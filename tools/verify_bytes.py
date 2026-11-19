#!/usr/bin/env python3
"""원본 번들과 재번들 결과를 '디코딩된 내용' 기준으로 항목별 비교한다.

렌더링을 보기 전에, 로더가 받는 입력(셸·manifest·ext_resources·page_order·템플릿·
모든 리소스 바이트)이 원본과 같은지 확인한다. gzip/base64 바이트는 압축기에 따라
달라질 수 있으므로 디코딩 후 SHA-256 으로 비교한다.

사용법: python3 tools/verify_bytes.py [원본] [재번들]
"""
import hashlib, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import split_bundle, decode_entry  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def sha(b):
    if isinstance(b, str):
        b = b.encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def parse(text):
    shell, blocks = split_bundle(text)
    return {
        "shell": shell,
        "manifest": json.loads(blocks["manifest"]),
        "ext": json.loads(blocks["ext_resources"]),
        "order": json.loads(blocks["page_order"]),
        "template": json.loads(blocks["template"]),
        "raw": blocks,
    }


def compare(a, b, label, results, nested=False):
    """nested=True: 이 번들의 리소스가 다시 번들(페이지)인 경우.
    페이지 HTML 안에는 하위 리소스의 gzip 바이트가 들어 있어 압축기에 따라 텍스트가
    달라지므로, 데이터는 직접 비교하지 않고 호출부가 하위 번들을 재귀 비교한다."""
    def rec(name, ok, detail=""):
        results.append((label + name, ok, detail))
    rec("셸(로더 포함)", a["shell"] == b["shell"])
    rec("page_order", a["order"] == b["order"])
    rec("ext_resources(순서 포함)", a["ext"] == b["ext"])
    rec("template", a["template"] == b["template"])
    rec("manifest 키·순서", list(a["manifest"]) == list(b["manifest"]))
    for u, ea in a["manifest"].items():
        eb = b["manifest"].get(u)
        if eb is None:
            rec("리소스 %s" % u[:8], False, "재번들에 없음")
            continue
        same_meta = ea["mime"] == eb["mime"] and bool(ea.get("compressed")) == bool(eb.get("compressed"))
        if nested:
            rec("페이지 리소스 %s 메타(mime·압축여부)" % u[:8], same_meta)
            continue
        same_data = sha(decode_entry(ea)) == sha(decode_entry(eb))
        rec("리소스 %s (%s)" % (u[:8], ea["mime"]), same_meta and same_data,
            "" if same_meta and same_data else "메타=%s 데이터=%s" % (same_meta, same_data))
    # JSON 직렬화 형태(공백 등)까지 같은지: data 필드를 제외하고 비교
    for key in ("ext_resources", "page_order", "template"):
        rec("직렬화 원문 %s" % key, a["raw"][key] == b["raw"][key])


def main():
    orig = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "original" / "티켓 교환 UX UI 포트폴리오.html"
    new = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "dist" / "ticket-exchange-portfolio.html"
    A = parse(orig.read_text(encoding="utf-8"))
    B = parse(new.read_text(encoding="utf-8"))
    results = []
    compare(A, B, "[루트] ", results, nested=True)
    for u in A["order"]:
        pa = parse(decode_entry(A["manifest"][u]).decode("utf-8"))
        pb = parse(decode_entry(B["manifest"][u]).decode("utf-8"))
        compare(pa, pb, "[페이지 %s] " % u[:8], results)
    bad = [r for r in results if not r[1]]
    print("비교 항목 %d개, 불일치 %d개" % (len(results), len(bad)))
    for name, ok, detail in bad:
        print("  불일치:", name, detail)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
