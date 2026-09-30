# CLAUDE.md — 승정 ERP (seungjeong-erp)

사출·조립 제조사 승정의 **정적 HTML ERP**입니다. 빌드 과정 없이 GitHub Pages(`jachungu29/seungjeong-erp`, 브랜치 **master**, main 아님)로 배포하고, 데이터는 Supabase(`app_state` 키/값 등)에 저장합니다.
사용자는 코딩을 모르는 대표이사(초보)입니다. **한국어로, 클릭 단위로** 안내하고, SQL·설정처럼 어려운 일은 Claude가 대신 합니다. 사용자는 클릭과 입력만 합니다.

> [!WARNING]
> **이 저장소는 공개(PUBLIC)입니다.** 커밋하는 모든 파일(이 CLAUDE.md 포함)을 누구나 볼 수 있습니다.
> - **절대 커밋 금지:** 비밀번호, IP 주소, NAS 호스트명·원격접속 ID, NAS/관리자 계정명, NAS 내부 파일 경로, JWT·API 키·service_role 키, 자체 호스팅 `.env` 내용
> - 위 정보는 **회사 OneDrive `SEUNGJEONG_ERP_DEV\PRIVATE_인프라정보.md`에만** 둡니다(개인 OneDrive 사용 금지). 필요하면 사용자에게 그 파일을 열어 달라고 요청하세요. 그 내용은 저장소 파일·커밋 메시지·코드 주석 어디에도 옮기지 않습니다.
> - `cloud.js` 등에 들어 있는 Supabase publishable 키는 원래 공개용이지만, 문서나 메모에 다시 복사하지 않습니다.
> - 커밋 전 점검(나온 결과는 하나씩 사람이 확인):
>   `git diff --cached -U0 | grep -nE 'eyJhbGci|service_role|sb_secret_|JWT_SECRET|PASSWORD|[0-9]{1,3}(\.[0-9]{1,3}){3}'`
> - `.gitignore`가 `.env`, `*.env`, `_KEYS*`, `*접속키*`, `BUILD_LOG*.txt`, `*.zip`, `*.bak`, `*_chk.js`를 막고 있습니다. 이 규칙을 지우지 마세요.

---

## 0. 실행 방식과 정리 원칙 (2026-09-29 사장님 결정 — 모든 작업보다 우선)

**실행 방식은 하나: "더블클릭 + 나스".**
- 컴퓨터: `C:\ERP\seungjeong-erp\SEUNGJEONG ERP.html`을 **더블클릭**해서 엽니다(유일한 시작 화면). 로컬 서버·앱 설치(서비스워커)·인터넷 주소는 쓰지 않는 방향입니다.
- 데이터: 회사 나스(사내망 전용)에 저장합니다. 인터넷 클라우드 DB는 쓰지 않습니다.
- 휴대폰 안전신고만: 나스 웹 기능으로 안전신고 화면만 제공합니다(회사 와이파이 전용).
- 더블클릭(file://)에서는 화면이 다른 파일을 `fetch`로 읽는 것이 막힙니다. 새 기능에 쓰지 말고, 필요한 자료는 나스에서 받습니다(현재 해당: `_archive/도면BOM.html`이 `도면관리.html`을 읽는 부분 — 내장 사본으로 대체 작동 중, 정리 때 두 화면 통합).

**정리 원칙 — 불필요한 것 없이 프로그래밍합니다.**
1. 옛 판·복사본 파일을 두지 않습니다. 옛 것은 깃허브 기록에만 남깁니다(`_v2`, `_old`, `.bak`, 날짜 붙은 사본 금지).
2. 중간에 거쳐 가기만 하는 이동용 파일(리다이렉트 stub)을 만들지 않습니다.
3. 새 화면은 **메뉴 연결과 함께** 만듭니다. 어디에서도 들어갈 수 없는 화면은 남기지 않습니다.
4. 사진·PDF·데이터를 화면 파일 안에 넣지 않습니다(data: 주소·큰 배열 금지). 나스에 둡니다.
5. 서버 주소·키는 설정 파일 **한 곳**에만 둡니다(공개 저장소에 올리지 않는 `_private` 등).
6. 백업·분석 결과물은 `_private\`에만 둡니다(깃허브 차단 확인).
7. 사람이 보는 이름·문구·안내는 **한국어**로 씁니다.
8. 파일을 지우기 전에는 ①메뉴·시작 화면·QR 연결 ②실제 데이터가 쓰는지 ③다른 파일과 중복인지 확인합니다. 회사PC 백업 전에는 서비스워커(`sw.js`)를 바꾸지 않고, 캐시 이름 `sj-erp-shell-v1`은 절대 바꾸지 않습니다.

## 1. 멀티 PC 황금 규칙 (집·사무실)

1. **모든 PC에서 저장소 경로를 `C:\ERP\seungjeong-erp` 하나로 통일합니다.** Claude 메모리 폴더 `%USERPROFILE%\.claude\projects\C--ERP-seungjeong-erp\memory`와 `.url` 바로가기의 IconFile(`C:\ERP\seungjeong-erp\승정.ico`)이 이 경로에 묶여 있습니다. Claude Code도 반드시 이 폴더에서 실행합니다. 옛 폴더 `C:\ERP\SEUNGJEONG ERP V2`는 더 이상 쓰지 않습니다.
2. **작업 시작 = `tools\작업시작.bat` 더블클릭.** 순서: [1] `git pull --ff-only` → [2] OneDrive `claude-memory\`를 이 PC 메모리로 복사(더 최신 파일만, 삭제 없음) → [3] 이 PC에 `%USERPROFILE%\.claude\settings.json`이 없을 때만 OneDrive 백업본을 복사.
3. **작업 끝 = `tools\작업종료.bat` 더블클릭.** 순서: [1] 이 PC 메모리를 OneDrive로 복사 → [2] settings.json 백업(이 PC 쪽이 더 최신일 때만) → [3] `git status`로 커밋·push 안 된 변경을 알려줌. **자동 commit/push는 하지 않습니다.** 사용자가 GitHub Desktop에서 Commit → Push 합니다.
4. **pull 먼저, push 나중.** 한 번에 **한 PC에서만** 작업하고, 집과 사무실에서 동시에 편집하지 않습니다. 다른 PC로 옮기기 전에 반드시 push합니다(push 안 한 커밋이 남아 있으면 다른 PC는 옛 코드로 작업하게 됩니다).
5. **커밋·push는 사용자가 요청할 때만** 합니다. 평소 push는 사용자가 GitHub Desktop으로 합니다. 사용자가 Claude에게 push를 부탁하면 인증 창에서 멈추지 않도록 `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`를 켜고 실행합니다(이 PC의 Git Credential Manager에 로그인이 저장돼 있으면 성공합니다). **force push는 절대 하지 않습니다**(다른 PC 작업이 사라짐).
6. **실데이터 삭제·훼손 금지:** `bom` 테이블(278건), `production`, `app_state`.
7. 수십 MB가 넘는 파일은 커밋하지 말고 OneDrive `대용량파일\`로 보냅니다. GitHub은 파일 하나가 50MB를 넘으면 경고하고 100MB를 넘으면 거부합니다.

**Claude 행동 규칙:** 사용자가 방금 PC를 옮긴 것 같으면("집이에요", "사무실에서 이어서", 기억과 다른 파일 상태 등) 먼저 두 가지를 확인합니다.
- `git -c core.quotepath=false status -sb`와 `git log -3 --oneline`으로 현재 상태를 봅니다.
- "작업시작.bat을 먼저 실행하셨나요?"라고 물어봅니다. 브랜치가 behind이거나 메모리가 오래돼 보이면 작업시작.bat부터 실행하게 합니다.
- `git status`가 **ahead N, behind M**(둘 다 0이 아님)이거나 `no merge base`가 나오면 두 PC가 갈라진 것입니다. 혼자 merge·reset·force push 하지 말고, 어느 쪽을 기준으로 할지 사용자에게 먼저 묻습니다. 먼저 `git branch backup/<이름>-<날짜> HEAD`로 백업 브랜치를 만듭니다.

작업을 마칠 때는 **"GitHub Desktop에서 Commit·Push → 작업종료.bat 실행"**을 안내합니다. 메모리를 갱신했다면 작업종료.bat을 반드시 실행해야 다른 PC에 전달됩니다.

### 회사 OneDrive 공유 폴더 (git 밖)
회사(비즈니스) OneDrive만 씁니다. bat 파일이 폴더를 찾는 순서:
1. 환경변수 `%OneDriveCommercial%`
2. 레지스트리 `HKCU\Software\Microsoft\OneDrive\Accounts\Business1`의 `UserFolder`
3. `%USERPROFILE%\OneDrive - <회사명>` 폴더

**개인 OneDrive(`%USERPROFILE%\OneDrive`)는 절대 쓰지 않습니다.**
```
<회사 OneDrive>\SEUNGJEONG_ERP_DEV\
  claude-memory\           Claude 자동 메모리 (작업시작/종료.bat이 양방향 복사, 최신 파일만 덮어씀, 삭제 없음)
  claude-settings.json     %USERPROFILE%\.claude\settings.json 백업
  대용량파일\              git에 넣지 않는 큰 파일 (예: 저장소 밖 standalone MES 개발본 REV35, 약 34MB)
  PRIVATE_인프라정보.md    NAS·서버 주소, 계정, 키 등 비공개 정보 (이곳에만!)
  README.md                폴더 설명
```

---

## 2. 저장소 지도

2026-07-27에 사무실 PC가 저장소를 경량화(이력 1커밋 압축, ISIR PDF 제거)하고 화면을 **분류 폴더**로 옮겼습니다. 루트에는 진입·본체·공통 파일만 있습니다.

```
/                     SEUNGJEONG ERP.html(유일한 시작 화면) · legacy.html(본체) · sos.html
                      manifest-erp.json · sw.js(데스크톱 앱 PWA) · manifest.json(안전신고 PWA) · 아이콘(sj-icon*.png, 승정.ico)
_lib/                 cloud.js · supabase.js · sj-sheet.js · basis-data.js · xlsx.full.min.js  (공통 엔진)
화면/                 화면 파일 전부(HTML 27개 + 브랜드 로고 SVG) — 한 폴더(2026-09-29 8개 폴더 통합)
_archive/             참고문서·옛 화면(legacy가 아직 iframe으로 여는 것 포함: FMEA, 관리계획서, 도면관리, 조도관리, 수입검사 대장 등)
eq_photos/            설비 사진 (브랜드 로고 SVG는 화면/ 폴더)
tools/  docs/         멀티 PC 루틴 bat / 사용자 가이드
_private/              비공개(깃허브 차단): 백업·분석·나스 접속키
26_seungjeong_ERP/     사장님의 별도 깃허브 저장소(ERP와 무관, .gitignore로 제외 — 이 저장소에 절대 추가하지 않음)
```

| 파일 | 역할 |
|---|---|
| `SEUNGJEONG ERP.html` | **유일한 시작 화면**(2026-09-29 사장님 지시로 옛 이동용 파일 index.html·index2.html 삭제). legacy 로고 클릭, 각 화면 '← 메인' 버튼, `manifest-erp.json` 시작 주소가 이 파일을 가리킵니다. `sw.js`의 미리 저장 목록(SHELL)은 회사PC 백업이 끝날 때까지 **일부러 그대로 둡니다**(바꾸면 모든 PC에서 서비스워커가 다시 설치됨 — 동결 기간). 백업 뒤 SHELL의 'index2.html'을 'SEUNGJEONG%20ERP.html'로, '로고/승정로고_투명.svg'를 '화면/승정로고_투명.svg'로(2026-09-29 폴더 통합으로 옮겨짐) 바꾸고, 캐시 이름 `sj-erp-shell-v1`은 절대 바꾸지 않습니다. 메인 런처(약 9KB). '앱 열기'로 `legacy.html`을 엽니다. 설계 카드: `화면/rev0-map`, `화면/graph`, `화면/obsidian`, `화면/apps`. 대분류 섹션 9개는 비어 있음("항목 추가 예정"). 상단 로고(`화면/승정로고_투명.svg`), 앱 카드 오른쪽 위 안전신고 QR 배지(`sos.html`, jsdelivr qrcode-generator로 그림), PWA 등록(manifest-erp.json + sw.js). |
| `legacy.html` | **ERP 본체 SPA(약 52MB, v378 프로토타입 기반 REV-0).** 좌측 NAV와 전체 뷰가 들어 있습니다. **절대 통째로 Read하지 않습니다**(§5 참조). |
| `_lib/cloud.js` | 공통 Supabase 헬퍼(약 58줄). `window.SB_URL/SB_KEY`, `window.SB`, `window.__CID`, `window.Cloud`. 반드시 `_lib/supabase.js` 다음에 로드합니다. |
| `_lib/supabase.js` | supabase-js v2 UMD 로컬 사본(`window.supabase.createClient`). **수정 금지.** CDN 대신 이 파일을 씁니다. |
| `_lib/sj-sheet.js` | 영업·수주 9개 화면 공통 툴바(검색 + CSV). 한 곳 고치면 전체 반영. |
| `_lib/basis-data.js` | 기준정보 마스터(398종 서식집 단일 원본). **아직 어느 화면에도 연결 안 됨**(보존용). |
| `_lib/xlsx.full.min.js` | SheetJS 로컬 사본. 다른 화면은 cdnjs 버전을 씁니다. |
| `manifest.json`, `sos.html` | 안전신고 PWA(start_url `화면/이상안전신고.html`. `id`는 이미 설치한 휴대폰과 같은 앱으로 인식되도록 옛 주소 `/seungjeong-erp/안전/이상안전신고.html`로 고정 — 고치지 않습니다). `sos.html`은 영문 짧은 주소 리다이렉트(QR용)입니다. |
| `화면/graph.html` | **구조도(메뉴) 편집의 단일 원본.** 5단 편집기(순번 ▲▼, 승격◀/강등▶, 확대·축소, 방향키). 열 때 `Cloud.get('map_struct')`를 받습니다. |
| `화면/rev0-map.html` | 구조도 편집기. ⚠ 열 때 클라우드를 받지 않고 로컬/_DEF만 읽으므로 다른 PC의 편집을 덮어쓸 수 있습니다. 편집은 graph.html에서 하세요. |
| `화면/obsidian.html` | 구조도 그래프 뷰(읽기 전용, 실시간 구독). |
| `화면/apps.html`, `화면/bom.html` | `custom_pages` 업로드기와 BOM LIST 로더(삭제된 인터넷 DB 전용 — 지금은 빈 화면, 나스 연결 때 다시 씀). 생산계획현황 로더 `생산/plan.html`은 2026-09-29 삭제. |
| `.claude/launch.json` | 로컬 미리보기 `erp-static`(`python -m http.server 8791`). |
| `.gitignore`, `.gitattributes` | 비밀·스크래치·PDF 차단 / `*.bat`·`*.cmd`를 CRLF로 고정. |
| `tools/작업시작.bat`, `tools/작업종료.bat` | §1의 세션 시작·종료 루틴(UTF-8 BOM 없음 + `chcp 65001`). |
| `_HANDOFF.md` | 현재 상태와 다음 할 일(다른 PC에서 "_HANDOFF.md 읽고 이어서 해줘"로 시작). |

**폴더 안 화면 파일의 규칙:** `<head>` 맨 앞에 `<base href="../">`가 있어서 모든 상대 경로가 **루트 기준**입니다(`_lib/cloud.js`, `sj-icon.png`, `화면/수주관리.html` 등). 새 화면도 이 규칙을 따릅니다.

**화면 파일(한 파일 = 한 화면, CSS/JS 인라인)과 app_state 키** — 괄호 안 폴더가 위치입니다.
- 영업(`화면/`): 수주관리(`sales_po_v1`), 수요예측(`demand_forecast_v1`), 수주잔량(`order_backlog_v1`), 긴급수주(`rush_order_v1`), 판매관리(`sales_sell_v1`), 납품관리(`sales_deliv_v1`), 매출관리(`sales_revenue_v1`)
- 출하(`화면/`): 출하지시(`ship_do_v1`), 납품현황(`deliv_status_v1`), 완제품재고(`fg_stock_v1`). legacy 내장 sales_ship/mat_fg 매핑을 대체합니다.
- 품질(`화면/`): 품질관리(`quality_v1`, `?tab=insp|defect|capa|m4|gauge|edu` → 뷰 `q_insp`~`q_edu`), 불량관리(`defect_hfp_v1`, `q_hfp`), 수입검사(`incoming_ims_v1`)
- 품질(`_archive/`, legacy가 iframe으로 엶): 조도관리(`illumination_v1`, `q_illum`), 도면관리(`quality_drawing_v2`), 도면BOM(`q_dbom`, 도면관리.html을 fetch해 `BOM_ITEMS_RAW`/`BOM_LINKS_RAW`를 재추출), 공정검사SPC(`process_spc_v1`), SPC측정관리(**로컬 전용** `spc_records_v1`, `ins_*`), 관리계획서(`control_plan_v1`), FMEA(`fmea_docs_v1`/`fmea_system_v1`), 수입검사 대장·절차서(`iip_doc_v5`, 나머지는 정적)
  - ⚠ legacy에 `SPC측정관리.html`(루트) iframe이 남아 있는데 파일은 `_archive/`에 있습니다. 그 메뉴는 404일 수 있습니다(수정 후보).
- IATF/APQP(`화면/`): apqp(`apqp_register`), isir(`isir_reports`), imds(`imds_data`). 문서관리대장(`iatf_docs_2026`)·IATF절차서(`iatf_procs_v1`)·IATF16949요구사항(`iatf_req_status_v1`)은 `_archive/`
  - ISIR 스캔 PDF(18개, 약 445MB)는 **저장소 밖** `C:\ERP\_ARCHIVE_isir_pdf`에 있습니다. `.gitignore`가 `isir_pdf/`·`*.pdf`를 막습니다. 웹(Pages)에서 isir.html의 PDF 링크는 열리지 않습니다.
- 생산(`화면/`): prod-report(월간 생산보고, 이 PC 저장만 — `sjprod_data_v8` 등 11개 키. 2026-09-29 'sj*' 전체를 인터넷에 올리던 동기화 제거; 메뉴 '생산보고시스템'·'월간 보고서 관리' = ph_r074/ph_r075), 생산계획현황(원본 화면; 메뉴 '생산계획현황' = plan_cloud가 직접 엶, `?m=2026_09`처럼 월 선택 — 7월 외 달은 단가·가동율이 7월 원본 기준이라는 안내 표시), bom(로더). ※ 2026-09-29 prod-plan·production·itemmaster 삭제(깃허브 기록에 있음)
- 인사(`화면/`): 사원마스터(`emp_master_v1`, `?tab=mgr|wrk|day|quit` → `emp_office/emp_prod/emp_day/emp_quit`). 인사고과는 legacy 내장(`hr_office/hr_prod`, `hrCompute()`)입니다.
- 안전(`화면/`): 이상안전신고·이상안전이력(`safety_reports`). 안전대시보드(`safety_dash_cfg`)는 `화면/`, 점검체크시트(`safety_inspect_v2`)·신고QR포스터는 `_archive/`
- 대시보드(`화면/`): 안전대시보드 (dashboard·exec-dashboard는 2026-09-29 삭제)
- 자산: `eq_photos/`(설비 사진), 브랜드 아이콘(`sj-icon.png`, `sj-icon-mask.png`, `승정.ico`, `화면/승정로고_투명.svg`; 감청 #15408F, 골드 #F2C14E)

---

## 3. 아키텍처

**진입 흐름:** `SEUNGJEONG ERP.html`(유일한 시작 화면 — 더블클릭 또는 로컬 서버 주소/SEUNGJEONG%20ERP.html) → `legacy.html`(앱) → 메뉴를 누르면 네이티브 뷰 또는 iframe 화면이 뜹니다.

**legacy.html의 배선** (줄번호는 바뀔 수 있으니 항상 Grep으로 다시 확인)
- 975줄 `<script src="_lib/supabase.js"></script><script src="_lib/cloud.js">`
- 1446 `const _NAV_DEFAULT`, 1447 `function _nePatchNav`, 1448 `var _L2V={...}`(`var _GM`, `function _structToNav`, `function _neLoadNav`도 같은 줄), 1449 `let NAV = _neLoadNav();`, 1450~1453 map_struct 클라우드 구독. 1446·1448줄은 한 줄이 1만 자가 넘습니다.
- 2748 `const EQREG`, 12167 `const VIEWS={`, 12172~ `SJ_*` 주입 블록, 12830 `function renderView`, 13247 `SJ_DB_KEY`, 13323 `sjStoreWrite`/`sjStoreRead`, 13561 `VIEWS.bom_cloud=`(iframe 화면 정의가 모인 곳). iframe `src`는 `화면/수주관리.html`처럼 **폴더 경로**입니다.
- 렌더링: 메뉴 클릭 → `renderView()` → `VIEWS[current]()`가 돌려준 HTML을 그립니다. 메뉴 이름 → 뷰 id 변환은 `_L2V[name] || ('ph_'+name)`이고, 매핑이 없으면 '준비중' 빈 화면이 됩니다.
- `_neLoadNav()` 우선순위: `SJ_MAP_STRUCT`(대분류 8개 이상) → `_structToNav` → 없으면 localStorage `SJ_NAV_V2` → `_NAV_DEFAULT`. 뒤의 두 경우에는 `_nePatchNav`(DEL 배열·이름 변경·강제 매핑)가 적용됩니다.

**메뉴 구조 단일 원본:** app_state 키 `map_struct` = `[{num,label,color,mids:[{hdr,items:[{name,st:'live'|'todo'|'bom'}]}]}]`
- 쓰는 쪽: `화면/graph.html`의 `saveStruct()`(권장), `화면/rev0-map.html`의 `mapSaveNow()`. 둘 다 `SJ_MAP_STRUCT`와 `Cloud.set('map_struct')`를 갱신합니다.
- 읽는 쪽: legacy(`Cloud.get`+`Cloud.on` → `NAV=_neLoadNav()` → `renderNav()`), `화면/obsidian.html`
- 구조도는 클라우드에 있으므로 **메뉴만 바꿀 때는 git push가 필요 없습니다.** 옛 `custom_pages '__map_struct__'` 방식은 폐기됐습니다.

**cloud.js API:** `Cloud.ok()`, `Cloud.ready`(Promise), `Cloud.get(key)`, `Cloud.set(key,value)`, `Cloud.on(key,cb)`
- `set`은 `app_state`에 `{key,value,src:__CID,updated_at}`를 upsert합니다.
- `on`은 `postgres_changes`를 구독하고, `src===__CID`인 자기 변경은 무시합니다.
- `app_state`가 없으면 조용히 로컬 모드로 동작합니다.
- 페이지가 `cloud.js`보다 먼저 `window.SB_URL/SB_KEY`를 정의하면 그 값을 씁니다.

**화면 데이터 패턴 (화면 1개 = app_state 문서 1개)**
1. localStorage로 먼저 그림
2. 클라우드 확인 후 `select('value').eq('key',K).maybeSingle()`로 다시 그림
3. 저장할 때 로컬 저장 + upsert
4. 실시간 구독. 편집 중(dirty)이거나 자기 변경이면 무시

화면 간 연계는 '↻ ~에서 불러오기' 버튼으로 다른 화면의 키를 읽어 병합합니다. 예: 수주잔량은 `sales_po_v1`을 읽고, 같은 수주번호면 기존 납품량을 유지합니다.

**Supabase 테이블:**
- `app_state`(key PK, value jsonb, src, updated_at; realtime)
- `custom_pages`(id, slug, title, html, updated_at; id=2 BOM_LIST, id=4 생산계획현황)
- `bom`(lv, text 열 + cat, pos)
- `production`(realtime)
- `item_master`, `partners`, `sales_order`

**클라우드 공유 vs PC별 로컬 (중요)**
- 전 PC 공유: 위 app_state 키들, 위 테이블들, 그리고 저장소에 커밋된 정적 파일(`eq_photos/` 등). ISIR PDF는 저장소 밖이라 **PC마다 따로** 둡니다(`C:\ERP\_ARCHIVE_isir_pdf`).
- **PC마다 다름(localStorage 전용):**
  - legacy 핵심 마스터 `SEUNGJEONG_ERP_DB`(EQREG, CUST_DATA 등. `sjStoreWrite/sjStoreRead`만 거치므로 이 두 함수를 바꾸는 것이 클라우드화의 연결 지점)
  - `SJ_NAV_V2`, 인사고과 `SJ_HR_*`, 설비대장 확장 `sj_eq_ledger_v1`(전역 `EQL`), `spc_records_v1`, `drawingMgmt_v2`, `CP_INJ_V2`
- "집과 사무실 화면·데이터가 다르다"는 문제의 원인은 대부분 이 로컬 전용 데이터입니다. 공유가 필요한 데이터는 반드시 app_state에 저장합니다.

**URL/키 하드코딩 현황:** `_lib/cloud.js` 방식(legacy, graph, rev0-map, obsidian, apqp, isir, imds, 이상안전신고 등)과, 파일마다 `const SB_URL=…, SB_KEY=…`를 인라인으로 두는 방식(`_archive` 제외 약 19개 파일: apps, bom, 생산계획현황, 영업·출하·품질 화면 대부분, 사원마스터 등)이 섞여 있습니다. 불량관리·조도관리는 `/rest/v1/app_state`를 fetch로 직접 호출합니다. **새 화면은 URL/키를 하드코딩하지 말고 `cloud.js`(`window.SB`/`window.Cloud`)를 쓰세요.** DB 주소를 바꿀 때 cloud.js 한 곳만 고치면 되게 하려는 것입니다.

---

## 4. 자주 쓰는 작업 레시피

**A. 새 화면 추가 (정적 파일 + iframe, 가장 흔한 작업)**
1. `화면/` 폴더에 `<화면>.html`을 만듭니다. `<head>` 맨 앞에 `<base href="../">`를 넣고, `<script src="_lib/supabase.js"></script><script src="_lib/cloud.js"></script>`를 넣고(CDN 금지), app_state 키는 `<기능>_v1`로 정합니다. no-cache meta 3종(Cache-Control/Pragma/Expires)을 넣고, 화면에 버전(예: `v1`)을 표시하고, 파비콘은 `sj-icon.png`, 다크 테마 CSS 변수(`--bg #0d1117` 등)를 씁니다. 영업·출하 계열은 수주관리.html/수요예측.html 프레임워크(KPI 카드, 대표이사 인쇄보고서)를 복제합니다.
2. legacy.html의 `VIEWS.bom_cloud=` 근처에 추가합니다.
   `if(typeof VIEWS!=='undefined'){VIEWS.<viewid>=function(){return '<iframe src="화면/<화면>.html" style="position:fixed;top:54px;left:248px;width:calc(100vw - 248px);height:calc(100vh - 54px);border:0;display:block;background:#fff;z-index:5"></iframe>';};}`
3. `var _L2V={` 안에 `"<메뉴라벨>":"<viewid>"`를 넣습니다. 라벨은 map_struct의 name과 **공백까지 정확히** 같아야 하므로 공백 있는/없는 형태를 둘 다 등록합니다. 같은 키가 중복되면 뒤쪽이 이기니, 가능하면 기존 항목을 교체합니다.
4. 메뉴에 항목이 없으면 `화면/graph.html`에서 추가합니다(클라우드 반영, push 불필요).
5. 브라우저로 검증(§5)한 뒤 **새 파일과 legacy.html을 함께** 커밋합니다.

**B. 한 파일 여러 탭:** `?tab=` 파라미터로 첫 탭을 고르게 하고, 메뉴마다 뷰 id를 따로 둔 뒤 같은 파일을 다른 tab으로 iframe합니다(품질관리, 사원마스터, SPC측정관리 사례). 한 뷰 id를 여러 메뉴가 공유할 수 있으므로, 한 항목만 바꿀 때는 새 뷰 id를 만듭니다(불량관리 → `q_hfp` 사례).

**C. 클라우드 업로드 페이지(custom_pages):** apps.html로 HTML을 업로드하면 같은 title의 행이 교체됩니다. 로더(bom.html을 복제)가 slug·title 키워드로 행을 골라 `iframe.srcdoc`으로 띄웁니다. 로더 파일과 VIEWS/_L2V는 처음 한 번만 push하면 되고, 이후 내용 교체는 push 없이 전 PC에 반영됩니다.

**D. 네이티브 뷰 재사용(먼저 확인!):** legacy에는 v378 코어(`vDefect`, `vGaugeReg`, `vQStd` 등)가 이미 들어 있습니다. 새로 만들기 전에 `grep -o 'qual_[a-z_]*:v[A-Za-z]*' legacy.html`처럼 검색하세요. 있으면 `_L2V` 한 줄로 끝나고, 쓸모없어진 iframe VIEWS와 대용량 파일은 삭제합니다. 사례: 계측기 → `qual_gauge`, 검사기준서 → `qual_std`, 불량집계(자동) → `qual_defect`.

**E. 코드 수준 메뉴 이름변경·삭제·강제매핑:** `_nePatchNav(nav)`의 DEL 배열이나 정규식 규칙에 추가합니다. 로드 때마다 적용됩니다.

**F. legacy 내부 주입(마커 블록)**
- 형식: `/*SJ_XXX_START ==== 설명 ==== */ … /*SJ_XXX_END*/`. 현재 블록은 SJ_EQTABLE, SJ_EQLEDGER, SJ_EQMIG, SJ_EQMIG4입니다.
- 제거·교체 정규식은 **반드시** `r'/\*SJ_XXX_START.*?/\*SJ_XXX_END\*/'`(Python `re.S`)로 씁니다. START 뒤에 `\*/`를 붙이면 설명문 때문에 매칭이 실패하고 블록이 중복으로 쌓입니다.
- 스크립트는 멱등하게 짭니다(블록 삭제 → 다시 삽입). 기존 뷰를 덮어쓸 때는 원본을 `VIEWS.<id>_orig`로 보존합니다(`equip_list` → `equip_orig`). 확장 데이터는 별도 전역과 별도 localStorage 키에 둡니다.
- PC당 한 번만 반영할 데이터는 플래그 키(예: `sj_mig_in01_v3`)를 둔 부팅 마이그레이션으로 처리합니다.

**G. legacy.html 수정 방법:** Edit 대신 scratchpad의 Python 스크립트로 합니다.
- `open(p,encoding='utf-8',newline='')`으로 읽기 → `assert s.count(ANCHOR)==1` → 치환 → 같은 옵션으로 쓰기
- 큰 블록은 scratchpad에 블록 파일을 만들어 `node --check`로 검증한 뒤, 시작~끝 앵커 구간을 통째로 치환합니다.
- 앵커가 이미 바뀐 파일에 옛 빌더 스크립트를 다시 돌리지 마세요.

**H. 로컬 앱을 클라우드 공유로 바꾸기:** 대상 localStorage 키만 `setItem`을 가로채 800ms 디바운스로 `Cloud.set('<name>_v1',…)`에 올립니다. 부팅 때 pull해서 값이 다르면 로컬에 쓰고 `location.reload()`를 1회만 합니다(가드 플래그로 무한루프 방지). 테스트는 저장 → 로컬 삭제 → 새로고침 → 복원까지 확인합니다.

**I. 데이터 구조 변경:** 기존 키를 깨지 말고 `_v2` 새 키를 만듭니다. 테이블은 나중에 ALTER가 적도록 처음부터 열을 넉넉히 잡습니다. SQL은 Claude가 작성하고 사용자는 실행만 합니다.

**J. 인쇄보고서 결재란**(작성/검토/검토/승인)은 반드시 `<td class="gh">`로 만듭니다. th로 만들면 흰 글자 규칙 때문에 글자가 보이지 않습니다.

**K. 휴대폰·외부 공유 주소**는 한글 URL을 피하고 영문 stub(`sos.html` 방식)을 둡니다.

---

## 5. 함정과 교훈

- **legacy.html(약 52MB)은 절대 통째로 Read하지 않습니다.** `grep -n -o '패턴' legacy.html`이나 `sed -n 'Np' legacy.html | cut -c1-400`으로 잘라서 봅니다. 한 줄이 1만 자가 넘는 곳이 있으므로 고유한 조각을 앵커로 씁니다. base64 이미지 때문에 대소문자 무시 검색은 가짜로 걸리는 경우가 많습니다.
- **식별자 충돌:** 주입 코드에서 `EQ_PHOTOS`를 선언했는데 원본에 이미 18곳 있었습니다. 재선언 SyntaxError로 메인 스크립트 전체가 죽어 `VIEWS`·`EQREG`가 undefined가 되고 메뉴가 사라졌습니다(`EQLPHOTO`로 개명해 해결). 새 전역 이름은 주입 전에 `grep -c`로 중복을 확인하고 고유 접두사(`ne*`, `SJ_*`, `EQL*`)를 씁니다.
- **const:** `EQREG`는 const 배열이라 재할당하면 오류가 납니다. `splice`/`push`로 제자리 수정합니다. `VIEWS`도 const이므로 `VIEWS.x=…`처럼 속성만 추가합니다.
- **`node --check` 추출:** 문자열 안의 `</script>` 때문에 스크립트 경계를 잘못 자르기 쉽습니다. 추출한 `.js`는 scratchpad에 두고 저장소에 남기지 않습니다(`*_chk.js`는 ignore 대상).
- **Windows 인코딩:**
  - Python 기본 인코딩은 cp949입니다. 모든 `open()`에 `encoding='utf-8'`을 붙이고, 콘솔에 한글을 출력할 때는 `PYTHONUTF8=1`을 설정합니다.
  - Git Bash에서는 `git -c core.quotepath=false status`로 봐야 한글 파일명이 보입니다.
  - `core.autocrlf=true`라 작업트리는 CRLF, 인덱스는 LF입니다. 줄끝 확인은 Python bytes로 합니다.
  - Git Bash에서 `reg query`로 한글 값을 읽으면 깨집니다. PowerShell `(Get-ItemProperty 'HKCU:\Software\Microsoft\OneDrive\Accounts\Business1').UserFolder`를 씁니다.
  - PowerShell 5.1의 `Set-Content` 기본값은 ANSI입니다. `-Encoding utf8`을 명시합니다.
  - 한글 `.bat`는 UTF-8 **BOM 없이** 저장하고 맨 위에 `chcp 65001 >nul`을 둡니다. 줄끝은 CRLF(`.gitattributes`가 고정)입니다.
- **로컬 확인은 http로 합니다**(file://에서는 fetch·iframe이 막힘).
  1. `preview_start` name=`erp-static`
  2. `http://localhost:8791/legacy.html`로 이동
  3. `javascript_tool`로 `typeof VIEWS, typeof EQREG, _L2V['<라벨>'], typeof VIEWS['<viewid>']`를 확인
  4. 메뉴를 클릭하거나 뷰를 렌더
  5. `read_console_messages(onlyErrors)`로 SyntaxError·ReferenceError가 없는지 확인
  6. 클라우드 화면은 저장한 뒤 새 탭에서 같은 데이터가 보이는지 확인
- **스크린샷은 legacy처럼 무거운 페이지에서 시간 초과될 수 있습니다.** `read_page`/`find`/`javascript_tool`을 우선 씁니다.
- **캐시:** push 후 반영까지 1~2분 걸립니다. 첫 404나 옛 화면이 보이면 탭을 완전히 닫았다 열거나 Ctrl+F5를 누르게 안내합니다.
- **localStorage는 PC 간에 동기화되지 않습니다**(§3). app_state 값이 커지고 있으므로(옛 `monthreport_v4` 약 1.1MB — 월간 생산보고는 이제 인터넷에 올리지 않음) 사진은 클라우드 base64로만 저장하고 로컬에는 `hasPhoto`만 둡니다. 4MB를 넘는 스냅샷은 클라우드 저장을 건너뛰는 가드를 둡니다.
- **저장소 용량:** 2026-07-27 경량화로 파일은 약 110MB입니다(그중 `legacy.html` 약 50MB, 이미 50MB 경고선). legacy를 고쳐 커밋할 때마다 약 50MB씩 이력이 늘어나므로, 자잘한 수정은 모아서 한 번에 커밋합니다.
- **이력 압축(force push) 사고 교훈 (2026-09-28):** 사무실 PC가 7/27에 이력을 압축해 force push한 뒤, 집 PC는 옛 이력 위에서 두 달간 작업해 `no merge base`로 갈라졌습니다. 집 PC를 GitHub 기준으로 맞추고(`git checkout -B master origin/master`) 새 파일만 옮겨 해결했습니다. 옛 상태는 그 PC의 로컬 브랜치 `backup/this-pc-2026-09-28`에 있습니다(그래서 그 PC의 `.git`은 아직 약 2.6GB). **이력을 다시 쓰는 작업은 모든 PC에 알리고, 다른 PC는 재clone 하게 해야 합니다.**
- 옛 메모리·문서의 "SEUNGJEONG ERP.html = 52MB 앱", "graph.html·cloud.js가 루트에 있음"은 옛 구조 기준입니다. 지금은 9KB 런처 + `legacy.html` 본체 + `화면/`·`_lib/` 폴더입니다.
- 같은 계정의 비슷한 이름 저장소(`seungjeong-erp-v379`, `-seungjeong-erp`, `C-MES-SEUNG-JEONG-ERP-SYSTEM` 등)는 옛 복사본입니다. 건드리지 않습니다.
- 외부 CDN(cdnjs의 Chart.js·exceljs·xlsx·html2canvas, jsdelivr의 qrcode-generator)을 쓰는 화면은 인터넷이 없는 LAN 전용 환경에서 깨질 수 있습니다. 필요하면 로컬 사본으로 바꿉니다.

---

## 6. 현재 상태와 다음 할 일 (2026-09 기준)

**완료:** GitHub Pages 배포, 외부 클라우드 Supabase 연동, 22대분류 메뉴 단일 원본(graph → legacy/obsidian 실시간), 영업 7화면, 출하 3화면, 품질(품질관리·SPC·수입검사·불량·조도·계측기·검사기준서), 인사(사원마스터·인사고과), 안전신고(QR/PWA), ISIR PDF 열람, 설비관리대장, 도면기반 BOM.

**2026-09-28 반영:** 집 PC를 GitHub(사무실 폴더 구조) 기준으로 맞추고, 그 위에 런처 개편(`SEUNGJEONG ERP.html` + index/index2 stub, 설계 링크는 `설계/` 경로), `.gitignore` 통합, `.gitattributes`, `tools/`, `docs/`, 이 CLAUDE.md, `_HANDOFF.md`를 한 커밋으로 올렸습니다. `sos.html`의 meta refresh 경로도 `안전/`로 고쳤습니다.

**2026-09-29 화면 폴더 통합:** 화면 폴더 8개(영업·생산·품질·안전·인사·대시보드·설계·로고)의 파일 28개를 `화면/` 한 폴더로 옮겼습니다(파일 이름 그대로, `git mv`). legacy iframe 경로 31곳, 런처(로고·설계 카드), `sos.html`, `manifest.json`, 화면 사이 링크 5곳을 함께 고쳤습니다. `<base href="../">` 덕분에 화면 안의 `_lib/`·아이콘·'← 메인' 경로는 그대로 맞습니다. `sw.js` SHELL에 남은 옛 로고 경로는 동결 기간이라 그대로 둡니다(미리 저장 실패는 원래 무시됨).

**진행 중: DB를 회사 NAS의 자체 호스팅 Supabase로 이전(사내 LAN 전용).** 정적 HTML + GitHub 구조는 유지하고(재개발 없음), NAS는 DB만 맡습니다. 기존 외부 Supabase 데이터는 삭제하지 않고 보존하며, 새 서버는 빈 테이블로 시작합니다. 남은 단계:
1. 관리 대시보드 연결 문제 해결
2. NAS 웹서버로 ERP 제공
3. 빈 테이블 생성(`app_state`, `custom_pages`, `bom`, `production`, `item_master`, `partners`, `sales_order` + realtime 게시)
4. `_lib/cloud.js`와 약 21개 파일의 `SB_URL/SB_KEY` 교체(또는 공통 설정으로 통합)
5. 자동 백업

주소·계정·키·진단 절차는 **PRIVATE_인프라정보.md에만** 있습니다.

**다음/미완:**
- legacy 핵심 마스터(`SEUNGJEONG_ERP_DB`) 클라우드화(`sjStoreWrite/sjStoreRead` 교체)
- SPC측정관리 클라우드 연동
- 사원마스터와 생산계획현황 작업자마스터 연동
- HFP 불량관리(`q_hfp`)와 네이티브 `vDefect`의 중복 정리
- 데이터 권한 정책 강화 + 매일 백업
- legacy의 `SPC측정관리.html` iframe 경로를 `_archive/SPC측정관리.html`로 고치기(현재 404 가능)
- `화면/rev0-map.html`이 열 때 클라우드를 받도록 개선
- 런처 대분류 9칸 채우기

---

## 7. 관련 문서

- `docs/멀티PC_작업가이드.md`: 새 PC 준비(clone 경로, GitHub Desktop, OneDrive)와 매일 작업 절차(초보자용)
- `tools/작업시작.bat`, `tools/작업종료.bat`: §1 루틴. 파일 안 주석에 단계가 설명돼 있습니다.
- `_HANDOFF.md`: 집↔사무실 인수인계(현재 상태·다음 작업). 작업을 마칠 때 갱신합니다.
- 회사 OneDrive `SEUNGJEONG_ERP_DEV\README.md`, `PRIVATE_인프라정보.md`: 비공개. 저장소에 복사 금지.
