# 소스 추출·재번들 가이드 (STEP 2A)

원본 단일 HTML(`original/티켓 교환 UX UI 포트폴리오.html`)을 **수정하지 않고** 사람이 탐색할 수 있는
소스(`src/`)로 풀고, 같은 화면을 다시 만들어 내는(`dist/`) 방법과 검증 결과를 기록한다.
이 단계에서는 디자인·문구·기능을 바꾸지 않았고, 순수 HTML/CSS/JS 전환((b) 단계)도 하지 않았다.

## 1. 디렉터리 구조

```
original/                      원본 보존 (읽기 전용 파일 + SHA256SUMS.txt)
src/
  bundle.json                  번들 명세: 페이지 순서, 페이지·리소스 uuid, 압축 여부, 리소스 경로
  loader/shell.html            원본 로더 셸 (제목만 {{TITLE}} 로 치환). 로더 JS 는 원본 그대로
  root/template.html           루트 보드: 1920×1080 iframe 10개 (페이지 uuid 는 {{page:슬러그}})
  pages/pNN-슬러그/page.html   페이지 10개의 템플릿 (리소스 uuid 는 {{asset:경로}})
  components/exchange/*.dc.html  P07 모바일 화면 6종: Main Request Waiting Match Done Expired
  components/pair/*.dc.html      P08 모바일 화면 4종: PairMode PairSeat PairReceive PairDone
                                 (P01 표지는 PairSeat·PairDone 을 재사용)
  vendor/dc-runtime/support.js   .dc.html 런타임 (원본 그대로, "생성 파일 – 직접 수정 금지")
  vendor/react/…                 React 18.3.1, ReactDOM 18.3.1 (원본 그대로)
tools/
  extract.py                   원본 → src/
  build.py                     src/ → dist/ticket-exchange-portfolio.html
  verify_bytes.py              디코딩된 내용 기준 항목별 일치 확인 (140항목)
  verify_render.cjs            Chromium 으로 렌더링·DOM·인터랙션·콘솔 수집 (Playwright)
  compare_render.py            수집물 두 벌 비교 (픽셀·DOM·텍스트·구조)
  compare_structure.py         문구만 바꾼 작업 전후의 구조·인터랙션 비교
  check_overflow.cjs           문구 수정 후 넘침·잘림 점검
  run_verification.sh          위 둘을 묶은 전체 검증 (원본 2회 + 대상 1회)
  probes/                      원인 조사·표본 측정용 보조 스크립트 (5절, 8절)
dist/                          재번들 결과물
docs/                          EXTRACTION.md(이 문서), STEP2B_CHANGES.md, KNOWN_ISSUES.md
verify/results-final/          STEP 2A 최초 검증 결과 (초판 도구로 측정, 5절 정정 참고)
verify/results-2a-reverify/    고친 도구로 다시 측정한 STEP 2A 동등성 (아래 4절의 최종 근거)
verify/results-2b/             STEP 2B 후 구조 비교와 페이지별 스크린샷
```

원본 번들의 구조(2단 중첩)는 다음과 같다.

```
원본 HTML ── 로더 + 데이터 블록 4개(manifest / ext_resources / page_order / template)
 └ 루트 템플릿: iframe 10개 (about:blank#<페이지 uuid>)
    └ 각 페이지 = 같은 로더를 가진 번들 (제목만 다름, 확인됨)
       └ 리소스: dc-runtime, React, ReactDOM, 컴포넌트 .dc.html
```

추출 시 중복은 합쳤다: 런타임·React·ReactDOM은 페이지 10개에 바이트 단위로 동일하게 들어 있었고,
PairSeat·PairDone은 P01과 P08에 동일하게 들어 있었다. 고유 리소스는 13개다.
각 페이지가 자기 uuid 를 유지하므로 `bundle.json` 이 페이지별 대응을 기록한다.

## 2. 실행 방법

필요한 것: Python 3(표준 라이브러리만), 검증용으로 Node + Playwright(+Chromium), Pillow, numpy.

```bash
# 1) 원본 → src/  (src/ 가 비어 있지 않으면 --force 필요)
python3 tools/extract.py

# 2) src/ → dist/ticket-exchange-portfolio.html  (결정적: 같은 입력이면 같은 해시)
python3 tools/build.py

# 3) 디코딩된 내용 비교 (원본 vs 재번들, 140항목)
python3 tools/verify_bytes.py

# 4) 렌더링 동등성 전체 검증 (출력 디렉터리는 비어 있어야 함, 약 2분)
bash tools/run_verification.sh verify/results-new
```

Google Fonts(Noto Sans KR)를 받아야 원본과 같은 글꼴로 렌더링된다. 프록시 환경에서는
`HTTPS_PROXY` 를 자동으로 사용한다. 폰트를 받지 못하면 두 번들 모두 같은 대체 글꼴로 그려지지만
원본 외관과 비교할 수는 없다.

## 3. 동등성의 정의

- **보장하는 것:** 로더가 받는 입력 전체(로더 셸, manifest 구성, ext_resources, page_order,
  템플릿, 모든 리소스 바이트·MIME·압축 여부)가 원본과 같다. 렌더링 결과도 같다(4절).
- **보장하지 않는 것:** 파일 바이트 동일. 번들 안의 gzip 바이트는 원본이 쓴 압축기와 달라서 재현되지 않는다
  (헤더 OS 필드 0x0a 로 보아 브라우저 CompressionStream 계열). 풀면 내용은 동일하며 기능에 영향이 없다.
  재번들 파일은 원본보다 약 1.3KB 크다(1,127,690 vs 1,126,358 bytes).

## 4. 검증 결과

**최종 근거는 `verify/results-2a-reverify/`** 이다. STEP 2A 최초 측정(`verify/results-final/`)은 클릭을 잘못된 방식으로
수행한 초판 도구를 썼고(5절·8절), 그 값 중 링크·컨트롤 클릭 항목은 신뢰하지 않는다. 고친 도구로 다시 측정한 결과는
아래와 같고 스크린샷 56장은 두 측정 모두 완전히 일치했다.

`dist/` 는 현재 STEP 2B 문구가 반영된 빌드다. 아래 표는 문구 수정 전(STEP 2A 상태의 `src/`) 빌드로 측정했다.
2B 빌드는 원본과 문구가 다르므로 픽셀·텍스트 비교 대신 구조·인터랙션만 비교했다(`verify/results-2b/structure-comparison.txt`, 불일치 0).

| 항목 | 결과 |
|---|---|
| 원본 SHA-256 | `cd20d387c6638754f4efaf14176cf1b7a96486019c1f09dae444b16ab2d0473e` (보존본과 일치 확인) |
| 디코딩 내용 비교 | 140항목 중 불일치 0 |
| 빌드 결정성 | 같은 입력으로 2회 빌드한 해시 동일 |
| 1920×1080 보드 10장 | 픽셀 완전 일치 10/10 |
| 390×844 폰 화면 요소 | 픽셀 완전 일치 (P01 6장, P07 18장, P08 12장) |
| 390×844 뷰포트 캡처 | 픽셀 완전 일치 10/10 |
| DOM·텍스트 | 페이지 10개 전부 일치 (blob/uuid 는 정규화) |
| 화면 구조 핑거프린트 | 일치 (태그·배경·글자 크기·치수별 개수) |
| 리소스 목록 / 폰트 종류 | 페이지별 `__resources` 키와 로드된 폰트(family·weight) 일치, 폰트 로드 실패 0 |
| 콘솔 오류·경고, 네트워크 실패(4xx) | 원본 0, 재번들 0 |
| 링크 대상 목록, 포커스 순서, 라디오·체크박스 클릭 결과, 첫 링크 클릭 결과 | 일치 (실제 마우스 클릭으로 측정) |
| 기준선(원본 vs 원본 재실행) | 스크린샷 56/56 일치, 구조 불일치 0 |

스크린샷 56장 모두 완전 일치였고(`verify/results-2a-reverify/comparison.txt`) 렌더링 옵션을 고정해 측정했다(8절).
따라서 "미세한 폰트 렌더링 차이"로 분류할 항목은 최종 실행에는 없었다.
개발 중 관찰한 차이는 8절에 모두 적었다.

## 5. 기능·인터랙션 보존 결과 (정정판)

**정정:** 이 문서의 초판과 STEP 1·2A 보고에는 틀린 서술이 있었다 (자세한 내용은 `docs/KNOWN_ISSUES.md` A-3).
핸들러(`onclick`)는 없지만 다음이 구현되어 있다.

- **화면 간 링크:** 컴포넌트 안의 `<a href="Request.dc.html">` (뒤로가기, CTA, 화면 이동). P01 6개, P07·P08 다수.
  대상 목록은 원본과 재번들이 일치한다.
- **네이티브 컨트롤:** 연석 흐름의 라디오(`name="mode"`, `name="dir"`)와 체크박스. 일반 폼처럼 정상 동작하며
  반복 측정(원본 6/6, 재번들 6/6)에서 결과가 항상 같았다.
- **칩 상태:** P07 조건 등록의 `aria-pressed` 값(정적 값).
- 나머지 버튼은 동작이 없다.

**링크의 실제 동작 (원본과 재번들이 같다):** 실제 마우스로 링크를 누르면 그 페이지의 프레임이
`about:blank#blocked` 로 이동하고 화면이 비어 버린다. 이것은 원본 번들 자체의 문제이며 재번들이 그대로 재현한다.
수정은 STEP 3 (`docs/KNOWN_ISSUES.md` A-1).

초판이 "P07 링크는 변화 없음", "P08 결과가 실행마다 다름"이라고 한 것은 앱의 성질이 아니라 측정 방식의 문제였다
(`click({force:true})` 가 요소 안정화 전 좌표를 눌러 빗나감). 요소의 실제 좌표를 마우스로 누르면 항상 같다.

## 6. 발견된 문제와 해결되지 않은 위험

1. **바이트 동일 불가** (3절). 해결 대상 아님.
2. **번들 안 링크가 프레임을 비운다** (5절). 원본에도 있는 문제이며 STEP 3 에서 수정. 원인은 미확인이다
   (상대 경로 `href` 가 `blob:` 문서에서 해석되지 못해 이동이 차단되는 것으로 추정).
3. **런타임 의존.** `.dc.html`·`x-dc`·`sc-if`·`sc-for`·`dc-import` 는 `support.js` 가 해석한다.
   런타임은 생성 파일이라 직접 수정하지 않는다. 컴포넌트 수정 시에는 이 문법 안에서 해야 한다.
4. **외부 의존: Google Fonts.** 오프라인이면 폰트가 달라진다 (원본과 동일한 한계).
5. **원본 번들러 도구 부재.** `build.py` 는 원본 로더 동작을 복제한 것이다. 로더 셸은 원본 그대로이므로
   로더 동작의 차이는 없다고 보지만, 원본 번들러가 부수적으로 하던 일이 있었다면 확인할 수 없다.
6. **`hint-*` 속성 보존.** 렌더링과 무관한 편집 도구용 속성을 그대로 두었다.
7. **검증 한계.** Chromium 한 가지, 1920×1080 / 390×844 두 해상도만 확인했다. Safari·Firefox, 터치 입력,
   `file://` 이외의 호스팅(HTTP)은 확인하지 않았다.
8. **날짜·요일 오류 등 STEP 1 에서 찾은 콘텐츠 문제**는 그대로 두었다(수정은 STEP 2B).

## 7. 다음 단계에서 수정 가능한 범위

모든 수정은 `src/` 에서 하고 `python3 tools/build.py` 로 다시 만든다. 수정 후에는
`python3 tools/verify_bytes.py` 는 의도한 변경 때문에 달라지므로 쓰지 말고, 변경 전후
스크린샷 비교(`tools/run_verification.sh`)로 영향 범위를 확인한다.

| 영역 | 파일 | 비고 |
|---|---|---|
| P02~P06, P09, P10 문구·레이아웃 | `src/pages/pNN-*/page.html` | 인라인 스타일, 디자인 토큰 변수 없음 |
| P01 표지 | `src/pages/p01-cover/page.html` | 폰 목업은 PairSeat/PairDone 재사용 |
| P07 일반 교환 화면 | `src/components/exchange/*.dc.html` | 6종 |
| P08·P01 연석 화면 | `src/components/pair/*.dc.html` | 4종 |
| 보드 구성 | `src/root/template.html` | 페이지 제목과 크기 |
| 새 페이지·리소스 추가 | `src/bundle.json` + 템플릿 | 새 uuid 필요 |

수정하지 말 것: `src/loader/shell.html`, `src/vendor/**`.

## 8. 개발 중 관찰한 측정 문제 (기록용)

최종 결과 이전에 발견해 도구를 고친 것들이다. 재번들 결함이 아니다.

- **빈 화면 캡처:** 헤드리스 Chromium 이 큰 iframe 을 래스터화하기 전에 캡처하면 흰 화면(약 34KB PNG)이
  나온다. 원본과 재번들 모두에서 무작위로 P07·P08 등에 발생했다
  (`tools/probes/probe_blank_capture.cjs`). `verify_render.cjs` 가 색 종류가 적으면 다시 찍는다.
  재시도 기록은 `report.json` 의 `blankRetries` (최종 실행: 원본 각 2회, 재번들 1회).
- **포커스 누수:** 초기 도구는 Tab 순회가 다음 iframe 으로 포커스를 넘겨 P09 버튼에 포커스 링이
  생겼다. 스크린샷과 인터랙션 테스트를 별도 페이지 로드로 분리하고 Tab 횟수를 제한해서 해결했다.
- **폰트 서브셋 개수:** unicode-range 서브셋은 지연 로드라 로드된 FontFace 개수가 실행마다 달라진다.
  (family, weight) 종류의 집합으로 비교한다.
- **390px 뷰포트 캡처의 글리프 가장자리 차이(0.1~0.6%):** 초기 도구에서 원본끼리의 기준선에서도 같은 크기로
  나타났다. 최종 실행에서는 발생하지 않았다.
- **클릭 빗나감(가장 중요):** 초판 도구의 `click({force:true})` 는 요소가 안정화되기 전의 좌표를 눌러 클릭이 빗나갔고,
  그 결과가 "실행마다 다름"처럼 보였다. 실제 좌표를 `page.mouse.click` 으로 누르도록 고쳤다 (`tools/probes/` 에 증거).
- **글자 가장자리 렌더링:** 고친 도구로 처음 돌렸을 때 같은 원본끼리 비교한 기준선에도 안티앨리어싱 차이가 생겼다
  (첫 실행만 일관되게 달랐고 원인은 확정하지 못했다). Chromium 옵션
  `--font-render-hinting=none --disable-lcd-text --force-color-profile=srgb --disable-gpu` 로 고정하자 기준선이
  56/56 일치로 돌아왔다. 캡처는 연속 두 번 같을 때만 채택한다.
