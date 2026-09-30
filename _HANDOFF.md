# 승정 ERP · 작업 인수인계 (HANDOFF)
> 다른 PC에서 Claude에게 "이 저장소의 _HANDOFF.md 읽고 이어서 해줘" 라고 하면 이 파일부터 읽고 이어서 작업합니다.
> 프로젝트 규칙과 구조는 저장소 맨 위 `CLAUDE.md`에 있습니다(Claude가 자동으로 읽음). 사람용 사용법은 `docs/멀티PC_작업가이드.md`를 보세요.
> 마지막 갱신: 2026-09-28

## 기본 정보
- 저장소: `jachungu29/seungjeong-erp`, 브랜치 **master**(main 아님). **공개(PUBLIC) 저장소**입니다.
  - 이름이 비슷한 다른 저장소(seungjeong-erp-v379 등)는 옛 복사본이므로 건드리지 않습니다.
- 로컬 폴더: **모든 PC에서 `C:\ERP\seungjeong-erp`**. 경로가 같아야 Claude 메모리가 이어집니다.
  - 옛 작업폴더 `C:\ERP\SEUNGJEONG ERP V2`에서는 더 이상 Claude Code를 열지 않습니다.
- 배포: GitHub Pages(빌드 없음) https://jachungu29.github.io/seungjeong-erp/
  - push하고 1~2분 뒤 반영됩니다. 옛 화면이 보이면 탭을 닫고 다시 열거나 Ctrl+F5를 누릅니다.
- 진입 순서: `SEUNGJEONG ERP.html`(유일한 시작 화면, 약 11KB) → `legacy.html`(ERP 본체, 약 50MB)
  - 옛 이동용 파일 `index.html`·`index2.html`은 2026-09-29 삭제했습니다(사장님 지시). 로고·'← 메인' 버튼·앱 설치 시작 주소가 모두 `SEUNGJEONG ERP.html`을 가리킵니다. 인터넷 주소는 맨 앞(…/seungjeong-erp/)만으로는 열리지 않으니 …/seungjeong-erp/SEUNGJEONG%20ERP.html 을 씁니다.
- 폴더 구조(2026-07-27 사무실 PC가 정리): 화면은 `화면/` 한 폴더(2026-09-29 8개 폴더 통합), 공통 엔진은 `_lib/`, 참고문서·옛 화면은 `_archive/`. 폴더 안 화면은 `<base href="../">`로 루트 기준 경로를 씁니다.
- DB(현재, 2026-09-30~): 회사 나스의 **자체 호스팅 Supabase(Docker)**로 옮기는 중입니다(사내망 전용). 옛 인터넷 DB(Supabase)는 2026-09-29 사장님이 삭제했습니다(되살리지 않음). 집 PC에도 같은 구성의 Docker Supabase가 있지만 나스와는 서로 다른 DB입니다(자동 동기화 없음). 접속 주소·키는 `_lib/sb-env.js`가 정하고, 값은 PC(브라우저)마다 `화면/db-setup.html`(런처 '설계 · 참고'의 'DB 접속 설정' 카드)에서 입력합니다(저장소에는 없음). 공통 헬퍼는 `_lib/cloud.js`(`Cloud.get/set/on`)이고, 화면 데이터는 `app_state(key, value, src, updated_at)` 키/값 테이블에 들어갑니다.
  - 그 밖의 테이블: `bom`, `production`, `item_master`, `partners`, `sales_order`, `custom_pages`
- ISIR 성적서 PDF(18개, 약 445MB)는 저장소 밖 `C:\ERP\_ARCHIVE_isir_pdf`에 있습니다(PC마다 따로 보관).

## 🔑 황금 규칙
1. **시작할 때**: `tools\작업시작.bat`을 더블클릭합니다(최신 코드 pull + Claude 메모리 받기). 그다음 Claude 새 대화를 엽니다.
2. **끝낼 때**: `tools\작업종료.bat`을 더블클릭합니다(메모리 올리기 + 변경 확인). 그다음 GitHub Desktop에서 **Commit → Push** 합니다.
3. **집·사무실 동시 편집 금지**. 한 PC에서 끝내고 push까지 마친 뒤 다른 PC에서 시작합니다.
4. **실데이터 삭제·훼손 금지**: 각 PC 브라우저 저장 자료, `_private\백업`의 백업 파일(BOM 원본 278행 포함), 앞으로 나스 DB의 자료. 옛 인터넷 DB는 2026-09-29 사장님이 이미 삭제했습니다(되살리지 않음).
5. **공개 저장소이므로** IP, 서버 주소, NAS 이름, 계정, 비밀번호, 키, .env 내용은 절대 커밋하지 않습니다.
   - 비공개 메모는 회사 OneDrive `SEUNGJEONG_ERP_DEV\PRIVATE_인프라정보.md`에만 둡니다.
   - 비밀번호와 키는 회사 NAS와 사무실 PC에만 둡니다.
6. **force push 금지.** 두 PC가 갈라지면(ahead·behind 둘 다 있음) 백업 브랜치부터 만들고 사용자에게 기준을 묻습니다.

## 데이터 안전 메모
- app_state 키 이름은 `<기능>_v1` 형식입니다. 구조가 바뀌면 기존 키를 고치지 말고 `_v2` 새 키를 만듭니다.
- 메뉴 구조의 원본은 app_state `map_struct` 하나입니다. 고치기 전에 `Cloud.get('map_struct')`로 백업부터 받습니다.
  - 편집은 `화면/graph.html`에서 합니다(열 때 클라우드 값을 받아옴).
  - `화면/rev0-map.html`은 열 때 클라우드를 읽지 않아서, 다른 PC에서 고친 구조를 덮어쓸 수 있습니다.
- 브라우저 localStorage는 PC마다 따로입니다. 공유해야 하는 데이터는 반드시 app_state(Cloud.set)에 저장합니다.
- 아직 PC별 로컬에만 저장되는 것: legacy 핵심 마스터(`SEUNGJEONG_ERP_DB`), `_archive/SPC측정관리.html`

## legacy.html 다룰 때 주의
- 약 50MB이고 한 줄이 매우 깁니다. Read로 통째로 열지 말고 Grep 패턴으로만 봅니다.
- 수정은 scratchpad의 Python 스크립트로 합니다: utf-8로 읽기 → 앵커가 정확히 1개인지 확인 → 치환 → utf-8로 쓰기
- 새 전역 이름을 넣기 전에 grep으로 이름이 겹치지 않는지 확인하고, 고유 접두사(`SJ_`, `ne`, `EQL`)를 씁니다.
- 새 화면을 붙이는 방법: `화면/` 폴더에 단독 HTML을 만들고 `VIEWS.<id>` iframe(`src="화면/<화면>.html"`)과 `_L2V` 매핑을 추가합니다. 자세한 레시피는 `CLAUDE.md`에 있습니다.
- legacy를 커밋할 때마다 이력이 약 50MB씩 늘어납니다. 자잘한 수정은 모아서 한 번에 커밋합니다.

## ✅ 지금까지 완료 (요약)
- GitHub Pages 배포와 외부 Supabase 연동(app_state / custom_pages / bom / production / item_master)
- 22대분류 메뉴 단일 원본: `화면/graph.html`에서 편집하면 legacy/obsidian에 실시간 반영. 5단 편집기(순번 ▲▼, 승격/강등, 확대·축소, 방향키)
- 영업 7화면, 출하 3화면(공통 툴바 `_lib/sj-sheet.js`)
- 품질: 품질관리·SPC·수입검사·불량·조도·계측기·검사기준서
- 인사: 사원마스터·인사고과
- 안전신고(휴대폰 QR/PWA), 설비관리대장, 도면기반 BOM
- 생산계획현황 메뉴는 원본 `화면/생산계획현황.html`을 직접 엶(2026-09-29, 빈 로더 plan.html 삭제). 월간 생산보고(prod-report)는 메뉴 '생산보고시스템'·'월간 보고서 관리'에 연결, 인터넷 동기화 제거(이 PC 저장만). 품질 메뉴에 '수입검사 MASTER LIST' 자동 추가(불러올 때마다 붙음).
- 화면 폴더 8개(영업·생산·품질·안전·인사·대시보드·설계·로고)의 파일 28개를 `화면/` 한 폴더로 통합(2026-09-29, 파일 이름 그대로). legacy iframe 31곳·런처·`sos.html`·`manifest.json`·화면 사이 링크 5곳을 함께 고침.
  - `sw.js` SHELL의 옛 로고 경로(`로고/…svg`)는 동결 기간이라 그대로 둠. 회사PC 백업 뒤 `화면/승정로고_투명.svg`로 바꿉니다.
  - master 반영 뒤: 휴대폰 홈 화면에 '안전신고' 앱을 추가해 둔 직원(특히 아이폰)은 아이콘을 지우고 QR로 다시 추가해야 할 수 있습니다. QR → sos.html 경로는 그대로 됩니다.
- 사무실 PC(7/27~8/29): 저장소 경량화, 분류 폴더 정리, 데스크톱 앱(PWA), 기준정보 마스터 `_lib/basis-data.js` 보존(미연결)
- 집 PC(9/28): GitHub 기준으로 맞춘 뒤 런처 `SEUNGJEONG ERP.html`(대분류 9칸은 '항목 추가 예정'), 멀티 PC 체계(`CLAUDE.md`, `tools\작업시작/종료.bat`, `.gitignore`·`.gitattributes`, `docs/멀티PC_작업가이드.md`)를 올림
  - 집 PC의 옛 상태는 그 PC의 로컬 브랜치 `backup/this-pc-2026-09-28`에 남아 있습니다(9/27 시작화면 전체 메뉴 복원본 포함).

## ✅ 2026-09-30 DB 설정 일원화 (코드 완료)
- 하드코딩된 옛 클라우드 URL·키를 약 30개 파일에서 모두 제거 → `_lib/sb-env.js` 한 곳에서 결정.
- 새 파일: `_lib/sb-env.js`, `_lib/sb-config.example.json`, `화면/db-setup.html`(주소·키 입력·연결 시험 — 런처 '설계 · 참고'의 'DB 접속 설정' 카드), `tools/supabase-setup.sql`(7개 테이블+RLS(지우기는 custom_pages·item_master만)+app_state 변경 이력+realtime, 여러 번 실행 안전).
- 설정 우선순위(`sb-env.js`): 화면이 먼저 정한 값 → 이 브라우저 저장값(db-setup, localStorage `SJ_SB_URL/SJ_SB_KEY`) → `_lib/sb-config.json`(git 제외 — `.gitignore`가 막음, 형식은 `sb-config.example.json`) → 기본값 `http://<연 서버>:8000` 또는 `http://localhost:8000`. 더블클릭(file://)에서는 sb-config.json을 읽지 못하므로 브라우저 저장값을 씁니다.
- 각 PC에서 할 일: Docker Supabase Studio에서 `tools/supabase-setup.sql` 실행 → **연결 전에 `tools\브라우저백업.bat`로 이 PC 백업 → 어느 PC를 원본으로 할지 사장님이 정함 → 원본 PC를 먼저 연결**(연결되면 구조도·불량관리·영업·품질 화면은 DB 값이 이 PC 값을 덮어쓸 수 있음) → `화면/db-setup.html`에서 주소·anon 키 저장 → 연결 시험 초록색 확인 → ERP를 다시 열기(더블클릭).
- 옛 인터넷 DB의 custom_pages BOM_LIST와 bom 278건은 새 DB에 없음 → 남은 백업(브라우저백업·엑셀)에서 다시 넣어야 함(생산계획현황은 원본 화면을 직접 열므로 필요 없음).
- 월간 생산보고(`화면/prod-report.html`)는 정리본대로 클라우드 동기화 없음(이 PC 저장만) — 이번 합치기에서도 그대로 둠.
- 나스에서 따로 할 일: `.env`의 예시 키(`JWT_SECRET`·`ANON_KEY`·`SERVICE_ROLE_KEY`)를 새 값으로 바꾸기, 8000번 포트는 사내망에서만 열기(방화벽), 매일 `pg_dump` 백업. anon 키는 모든 PC 브라우저에 저장되므로 사실상 공개라는 전제입니다.

## 🔧 진행중 ① DB를 회사 NAS의 자체 호스팅 Supabase로 이전 (사내망 전용) — 아래는 이전 기록(참고)
- 설계:
  - 정적 HTML 코드와 GitHub는 그대로 둡니다. NAS는 DB 역할만 합니다.
  - 사무실 PC에서 웹 ERP를 열면 API를 통해 NAS 데이터를 읽고 씁니다.
  - 회사 밖(집)에서는 NAS에 접속되지 않는 것이 정상입니다.
- 새 서버는 빈 테이블로 시작합니다. 자료는 각 PC 백업(엣지 더블클릭 저장본이 기준)과 `_private\백업\승정ERP_BOM원본_278행_integrated.json`에서 옮겨 넣습니다.
- 완료: NAS에서 Supabase 컨테이너가 실행 중입니다(경량 구성).
- 남은 일(순서대로):
  1. 관리 화면(대시보드) 연결 문제 해결
  2. NAS 웹서버에서 ERP 화면 제공
  3. 빈 테이블 만들기: app_state, custom_pages, bom, production, item_master, partners, sales_order
     - app_state·production은 실시간(realtime) 게시도 켭니다.
  4. `SB_URL`/`SB_KEY` 바꾸기
     - `_lib/cloud.js`뿐 아니라 약 21개 화면 파일에 직접 적혀 있습니다.
     - 설정을 한 곳으로 모으는 방법을 검토합니다.
  5. 자동 백업 설정
  6. 인터넷이 없어도 되도록, CDN으로 불러오는 라이브러리(Chart.js, xlsx, exceljs, html2canvas, qrcode)의 로컬 사본 검토
- 서버 주소·계정·키는 이 저장소에 적지 않습니다. 필요하면 사용자에게 OneDrive `PRIVATE_인프라정보.md`를 확인해 달라고 합니다.

## ⚠️ 폴더 구조 일원화 — 사장님 최종 결정 (2026-09-30)
- **표준 = 집 컴퓨터 정리본(`화면/` 폴더 하나 구조)**. 사장님이 두 안을 비교한 뒤 직접 골랐습니다. 같은 날 아침 회사PC 클로드가 적었던 "분류 폴더가 표준, 집 PC 구조는 버림(재clone)" 기록은 **취소**합니다(사장님 결정 전 회사PC 클로드가 단독으로 적은 것).
- 표준 구조: `SEUNGJEONG ERP.html`(유일한 시작 화면) · `legacy.html` · `화면/`(화면 30개, 로고 포함 — 2026-09-30 db-setup 추가) · `sos.html` · `_archive/ _lib/ eq_photos/ tools/ docs/` · 비공개 `_private/` · 별도 저장소 `26_seungjeong_ERP/`(제외). index.html·index2.html·참고/ 등은 삭제됨.
- 회사PC 맞추는 법: 재clone 하지 말고 ① `tools\작업시작.bat`(최신 받기) ② `tools\브라우저백업.bat`(백업) → 사장님이 "백업 끝"이라고 하면 집PC 클로드가 master 에 반영 → ③ 회사PC `작업시작.bat` 한 번 더. 옛 분류 폴더에 회사PC에만 있는 파일이 남아 있으면 폴더가 안 사라질 수 있으니 확인.

## 🔧 진행중 ② 멀티 PC 체계 마무리
1. 사무실 PC에서 `tools\작업시작.bat`을 처음 실행해 최신 코드(이번 런처·bat·문서)를 받습니다.
2. 메모리 통합을 확인합니다: 각 PC의 `%USERPROFILE%\.claude\projects\C--ERP-seungjeong-erp\memory`와 OneDrive `claude-memory`.
3. (선택) 집 PC의 `.git`이 옛 이력 때문에 약 2.6GB입니다. 필요 없어지면 `backup/this-pc-2026-09-28` 브랜치를 지우고 재clone 하면 가벼워집니다. 지우기 전에 사용자에게 꼭 확인합니다.

## ▶ 다음 작업 (우선순위 순)
1. **보안**
   - app_state 등에서 익명(anon) 삭제 권한을 막고, 매일 자동 백업을 설정합니다.
   - 안전신고의 민감정보를 분리합니다.
   - 옛 Supabase 프로젝트의 공개(anon) 키가 공개 이력에 남아 있습니다(삭제된 `안전신고_카톡v1.0.6_백업.html`). 옛 프로젝트가 아직 있으면 일시정지하거나 키를 교체합니다.
   - `eq_photos/`와 legacy 설비 샘플 데이터 '위치' 칸의 네트워크 주소 형태 값이 공개돼도 되는지 검토합니다.
2. legacy의 `SPC측정관리.html` iframe 경로 → `_archive/SPC측정관리.html` (지금은 404 가능)
3. legacy 핵심 마스터 클라우드화: `sjStoreWrite/sjStoreRead` 두 함수만 바꾸면 됩니다.
4. SPC측정관리 클라우드 연동, 사원마스터(`emp_master_v1`)와 생산계획현황 작업자 연동
5. 런처 대분류 9칸 채우기(필요하면 백업 브랜치의 9/27 전체 메뉴 복원본 참고)
6. `화면/rev0-map.html`이 열 때 `Cloud.get`을 하도록 수정(덮어쓰기 방지)
7. 기타
   - HFP 불량관리(q_hfp)와 vDefect 중복 정리
   - `_lib/basis-data.js`(398종 서식집) 화면 연결

## 검증 방법
- 로컬 확인: `.claude/launch.json`의 `erp-static`(python http.server 8791) → http://localhost:8791/SEUNGJEONG%20ERP.html (맨 앞 주소 localhost:8791/ 은 이제 파일 목록만 보입니다)
  - file:// 로 열면 fetch와 iframe이 막히므로 쓰지 않습니다.
- 콘솔 오류(SyntaxError·ReferenceError)가 없는지 확인합니다.
- 클라우드 화면은 저장한 뒤 시크릿창이나 다른 PC에서 같은 데이터가 보이는지 확인합니다.
- push하고 1~2분 뒤 Pages에서 확인합니다. 각 화면의 클라우드 상태 배지(☁️)도 확인합니다.
