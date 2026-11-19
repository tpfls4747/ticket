#!/usr/bin/env python3
"""원본 번들 HTML을 사람이 탐색할 수 있는 src/ 디렉터리로 무손실 추출한다.

사용법:
    python3 tools/extract.py [--original PATH] [--out src] [--force]

원본은 읽기만 한다. 추출 결과는 tools/build.py 로 다시 번들할 수 있다.
표준 라이브러리만 사용한다.
"""
import argparse, base64, gzip, hashlib, json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ORIGINAL = ROOT / "original" / "티켓 교환 UX UI 포트폴리오.html"

BLOCK_RE = re.compile(
    r'(<script type="__bundler/(manifest|ext_resources|page_order|template)">\n)(.*?)(\n  </script>)',
    re.S,
)
UUID_RE = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')

# 페이지 uuid(루트 manifest 순서) -> (슬러그, 보드 제목은 루트 템플릿에서 읽음)
PAGE_SLUGS = ["p01-cover", "p02-overview", "p03-problem", "p04-desk-research",
              "p05-policy", "p06-user-flow", "p07-ui-exchange", "p08-ui-pair",
              "p09-components", "p10-retrospective"]

# 컴포넌트 .dc.html 의 소속 디렉터리 (P01 은 P08 의 PairSeat/PairDone 을 재사용)
COMPONENT_DIRS = {
    "Main": "exchange", "Request": "exchange", "Waiting": "exchange",
    "Match": "exchange", "Done": "exchange", "Expired": "exchange",
    "PairMode": "pair", "PairSeat": "pair", "PairReceive": "pair", "PairDone": "pair",
}


def split_bundle(text):
    """번들 HTML -> (데이터 블록이 @@이름@@ 로 치환된 셸, {이름: 원문})"""
    blocks = {}
    def repl(m):
        blocks[m.group(2)] = m.group(3)
        return m.group(1) + "@@" + m.group(2) + "@@" + m.group(4)
    shell = BLOCK_RE.sub(repl, text)
    if set(blocks) != {"manifest", "ext_resources", "page_order", "template"}:
        raise SystemExit("번들 데이터 블록 4종을 모두 찾지 못했습니다: %s" % sorted(blocks))
    return shell, blocks


def decode_entry(entry):
    raw = base64.b64decode(entry["data"])
    return gzip.decompress(raw) if entry.get("compressed") else raw


def sha(b):
    return hashlib.sha256(b).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    path.write_bytes(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--original", default=str(DEFAULT_ORIGINAL))
    ap.add_argument("--out", default=str(ROOT / "src"))
    ap.add_argument("--force", action="store_true", help="기존 src/ 를 지우고 다시 추출")
    a = ap.parse_args()

    original = Path(a.original)
    out = Path(a.out)
    if out.exists() and any(out.iterdir()):
        if not a.force:
            raise SystemExit("%s 가 비어 있지 않습니다. --force 로 다시 추출하세요." % out)
        shutil.rmtree(out)

    text = original.read_text(encoding="utf-8")
    root_shell, rb = split_bundle(text)
    root_title = re.search(r"<title>(.*?)</title>", root_shell).group(1)
    shell_tpl = root_shell.replace(root_title, "{{TITLE}}")
    write(out / "loader" / "shell.html", shell_tpl)

    root_manifest = json.loads(rb["manifest"])
    page_order = json.loads(rb["page_order"])
    root_template = json.loads(rb["template"])
    assert len(page_order) == len(PAGE_SLUGS) == len(root_manifest), "페이지 수 불일치"
    assert set(page_order) == set(root_manifest), "루트 manifest 와 page_order 불일치"

    slug_of = dict(zip(page_order, PAGE_SLUGS))
    # 루트 템플릿: 페이지 iframe 마커의 uuid 를 {{page:슬러그}} 로
    tpl = root_template
    for uuid, slug in slug_of.items():
        assert tpl.count(uuid) == 1, "루트 템플릿에서 페이지 uuid 참조 횟수 이상: " + uuid
        tpl = tpl.replace(uuid, "{{page:%s}}" % slug)
    assert not UUID_RE.search(tpl), "루트 템플릿에 처리되지 않은 uuid 가 남았습니다"
    write(out / "root" / "template.html", tpl)

    # 중복 제거용: 내용 해시 -> 저장 경로
    stored = {}
    def store(content, rel):
        h = sha(content)
        if h in stored:
            return stored[h]
        write(out / rel, content)
        stored[h] = rel
        return rel

    bundle = {
        "_comment": "tools/build.py 가 읽는 번들 명세. uuid 는 원본과 동일하게 보존한다.",
        "root": {
            "title": root_title,
            "template": "root/template.html",
            "manifest_compressed": {u: bool(e.get("compressed")) for u, e in root_manifest.items()},
            "page_order": [{"slug": slug_of[u], "uuid": u} for u in page_order],
        },
        "pages": {},
    }

    page_titles = {}
    for uuid in page_order:
        slug = slug_of[uuid]
        page_text = decode_entry(root_manifest[uuid]).decode("utf-8")
        pshell, pb = split_bundle(page_text)
        ptitle = re.search(r"<title>(.*?)</title>", pshell).group(1)
        # 셸은 루트와 제목만 다른지 확인 (다르면 무손실 보장이 깨지므로 중단)
        if pshell.replace(ptitle, "{{TITLE}}") != shell_tpl:
            raise SystemExit("%s: 로더 셸이 루트와 다릅니다. 무손실 추출 불가." % slug)
        assert json.loads(pb["page_order"]) == [], "중첩 번들의 page_order 가 비어있지 않음"
        manifest = json.loads(pb["manifest"])
        ext = json.loads(pb["ext_resources"])
        ext_by_uuid = {e["uuid"]: e["id"] for e in ext}
        ptpl = json.loads(pb["template"])

        assets = []
        for auuid, entry in manifest.items():
            content = decode_entry(entry)
            ext_id = ext_by_uuid.get(auuid)
            if ext_id and ext_id.startswith("./") and ext_id.endswith(".dc.html"):
                name = ext_id[2:-len(".dc.html")]
                rel = "components/%s/%s.dc.html" % (COMPONENT_DIRS[name], name)
                kind = "component"
            elif ext_id and "react-dom" in ext_id:
                rel, kind = "vendor/react/react-dom.production.min.js", "vendor"
            elif ext_id and "react" in ext_id:
                rel, kind = "vendor/react/react.production.min.js", "vendor"
            elif entry["mime"] == "text/javascript" and ext_id is None:
                rel, kind = "vendor/dc-runtime/support.js", "runtime"
            else:
                raise SystemExit("%s: 분류되지 않은 리소스 %s (%s, ext=%s)" % (slug, auuid, entry["mime"], ext_id))
            rel = store(content, rel)
            assets.append({"uuid": auuid, "mime": entry["mime"],
                           "compressed": bool(entry.get("compressed")),
                           "kind": kind, "src": rel, "ext_id": ext_id,
                           "sha256": sha(content)})
            # 템플릿 안의 uuid 참조를 {{asset:uuid-앞8자리}} 가 아닌 경로 표기로 치환
            if ptpl.count(auuid):
                ptpl = ptpl.replace(auuid, "{{asset:%s}}" % rel)
        # ext_resources 에만 있고 manifest 에 없는 항목이 있으면 손실 위험
        missing = [e for e in ext if e["uuid"] not in manifest]
        if missing:
            raise SystemExit("%s: ext_resources 항목이 manifest 에 없음: %s" % (slug, missing))
        leftover = set(UUID_RE.findall(ptpl))
        if leftover:
            raise SystemExit("%s: 템플릿에 처리되지 않은 uuid: %s" % (slug, sorted(leftover)))
        write(out / "pages" / slug / "page.html", ptpl)
        page_titles[slug] = ptitle
        bundle["pages"][slug] = {
            "title": ptitle,
            "template": "pages/%s/page.html" % slug,
            "assets": assets,                    # 원본 manifest 순서 그대로
            "ext_resources_order": [e["uuid"] for e in ext],
        }

    write(out / "bundle.json", json.dumps(bundle, ensure_ascii=False, indent=2) + "\n")
    n = sum(1 for p in out.rglob("*") if p.is_file())
    print("추출 완료: %s (파일 %d개, 고유 리소스 %d개)" % (out, n, len(stored)))


if __name__ == "__main__":
    main()
