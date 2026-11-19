#!/usr/bin/env python3
"""src/ 에서 단일 HTML 번들을 다시 만든다.

사용법:
    python3 tools/build.py [--src src] [--out dist/ticket-exchange-portfolio.html]

- 로더 셸(src/loader/shell.html)은 원본 그대로이며 제목만 치환한다.
- 페이지 템플릿의 {{asset:경로}} 는 원본과 같은 uuid 로, 루트 템플릿의
  {{page:슬러그}} 는 해당 페이지 uuid 로 되돌린다.
- 동일 입력이면 항상 동일한 출력이 나온다 (gzip mtime=0).
표준 라이브러리만 사용한다.
"""
import argparse, base64, gzip, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def jdump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def encode_template(text):
    # 원본과 동일한 규칙: </ 는 </ 로 써서 </script> 로 오인되지 않게 한다.
    return jdump(text).replace("</", "<\\u002F")


def pack(content, compressed):
    raw = gzip.compress(content, 9, mtime=0) if compressed else content
    return base64.b64encode(raw).decode("ascii")


def fill_shell(shell, title, manifest, ext, page_order, template):
    out = shell.replace("{{TITLE}}", title)
    for key, val in (("manifest", manifest), ("ext_resources", ext),
                     ("page_order", page_order), ("template", template)):
        token = "@@%s@@" % key
        if out.count(token) != 1:
            raise SystemExit("셸에서 %s 위치를 찾지 못했습니다." % token)
        out = out.replace(token, val)
    return out


def build(src, out_path):
    bundle = json.loads((src / "bundle.json").read_text(encoding="utf-8"))
    shell = (src / "loader" / "shell.html").read_text(encoding="utf-8")

    page_html = {}      # uuid -> 완성된 페이지 HTML
    for slug, page in bundle["pages"].items():
        uuid_of_src = {}
        manifest = {}
        for a in page["assets"]:
            content = (src / a["src"]).read_bytes()
            uuid_of_src[a["src"]] = a["uuid"]
            manifest[a["uuid"]] = {"mime": a["mime"], "compressed": a["compressed"],
                                   "data": pack(content, a["compressed"])}
        ext = [{"id": a["ext_id"], "uuid": a["uuid"]}
               for u in page["ext_resources_order"]
               for a in page["assets"] if a["uuid"] == u]
        tpl = (src / page["template"]).read_text(encoding="utf-8")
        def asset_repl(m):
            if m.group(1) not in uuid_of_src:
                raise SystemExit("%s: 알 수 없는 리소스 참조 %s" % (slug, m.group(1)))
            return uuid_of_src[m.group(1)]
        tpl = re.sub(r"\{\{asset:([^}]+)\}\}", asset_repl, tpl)
        html = fill_shell(shell, page["title"], jdump(manifest), jdump(ext), "[]",
                          encode_template(tpl))
        uuid = next(p["uuid"] for p in bundle["root"]["page_order"] if p["slug"] == slug)
        page_html[uuid] = html

    root = bundle["root"]
    uuid_of_slug = {p["slug"]: p["uuid"] for p in root["page_order"]}
    rtpl = (src / root["template"]).read_text(encoding="utf-8")
    rtpl = re.sub(r"\{\{page:([^}]+)\}\}", lambda m: uuid_of_slug[m.group(1)], rtpl)
    manifest = {}
    for p in root["page_order"]:
        u = p["uuid"]
        comp = root["manifest_compressed"][u]
        manifest[u] = {"mime": "text/html", "compressed": comp,
                       "data": pack(page_html[u].encode("utf-8"), comp)}
    html = fill_shell(shell, root["title"], jdump(manifest), "[]",
                      jdump([p["uuid"] for p in root["page_order"]]),
                      encode_template(rtpl))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(html.encode("utf-8"))
    return len(html.encode("utf-8"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT / "src"))
    ap.add_argument("--out", default=str(ROOT / "dist" / "ticket-exchange-portfolio.html"))
    a = ap.parse_args()
    size = build(Path(a.src), Path(a.out))
    print("빌드 완료: %s (%d bytes)" % (a.out, size))


if __name__ == "__main__":
    main()
