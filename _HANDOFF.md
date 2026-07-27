# 승정 ERP · 작업 인수인계 (HANDOFF)

> ⚠️ **2026-07-14 저장소 경량화 (중요)**: 용량 2.5GB→185MB 로 줄이려고 **전체 git 이력을 1커밋으로 압축(force-push)** 했습니다.
> - **다른 PC(집 등)는 반드시 "새로 내려받기(재클론)"** 하세요. 일반 pull 하면 충돌납니다.
>   방법: 기존 `C:\ERP\seungjeong-erp` 폴더를 지우거나 이름 바꾼 뒤, `jachungu29/seungjeong-erp` 를 다시 clone.
> - **ISIR PDF 18개(445MB)** 는 저장소에서 빼서 `C:\ERP\_ARCHIVE_isir_pdf` 에 보관. `.gitignore` 로 `isir_pdf/`·`*.pdf` 재추가 차단. (isir.html 의 PDF 링크는 웹에서 안 열림 — 필요시 링크 정리)


> 집·사무실 어디서든 이 파일을 읽고 **이어서 작업**하기 위한 메모.
> 집에서 Claude Code에게: **"이 저장소의 `_HANDOFF.md` 읽고 이어서 해줘"** 라고 하면 됩니다.

## 기본 정보
- 저장소: `jachungu29/seungjeong-erp` (branch **master**)
- 로컬 폴더(권장): `C:\ERP\seungjeong-erp`
- 배포(GitHub Pages): https://jachungu29.github.io/seungjeong-erp/index2.html
- 클라우드: Supabase — URL/KEY 는 `cloud.js` 안에 있음.
  - 방식: `app_state(key, value, src, updated_at)` 키/값 테이블. `Cloud.get/set/on` 헬퍼.
  - 실데이터 테이블: `bom`(278건, 절대 삭제 금지), `production`(생산실적), `partners`, `item_master`.

## 🔑 황금 규칙 (반드시)
1. 작업 **시작 전 `git pull`** (최신 받기)
2. 작업 **끝나면 `git push`**
3. **집·사무실 동시 편집 금지** (한 곳 끝내고 다른 곳)
4. **실데이터 절대 삭제/훼손 금지** (bom 278건, production, app_state)

## ✅ 지금까지 완료
- index2.html = 깨끗한 런처(클라우드 업무 칸: 경영자 대시보드 스위치, 현장 대시보드, 생산관리, 월간 생산보고, BOM, 품목).
- cloud.js = Supabase 공통 헬퍼(app_state probe).
- exec-dashboard.html = 경영자 대시보드(실데이터: BOM·거래처·수주·생산부).
- dashboard.html = 종합대시보드(현장용) — 실데이터 모드.
- production.html = 생산부 생산실적 입력 + 년도·월 필터 + 년도별 이력 스위치. (Supabase `production` 테이블 필요; SQL은 화면 안 안내)
- home.html = 집·사무실 공통 안내(복사 버튼).
- **prod-report.html** (월간 생산보고 v4) = 원본 그대로 + **상단에 localStorage↔Supabase 동기화 한 겹** 얹음.
  - app_state 키: `monthreport_v4` (전체 `sj*` localStorage 스냅샷 저장).
  - 첫 로드 시 클라우드→localStorage 후 1회 새로고침, 편집 시 자동 저장(좌하단 배지), 다른 PC 변경 시 새로고침.
  - 4MB 초과(사진 등)면 클라우드 저장 생략(로컬만).
- **prod-plan.html** (생산계획·실적 v3) = ✅ **클라우드 연동 완료**. `/api/*` 서버 저장을 Supabase `app_state` 로 교체.
  - 핵심 데이터(일일계획·생산일보·불량·품목마스터) → app_state 키 `prodplan_v3` 1건.
  - BOM 탭 → app_state 키 `prodplan_bom`. 5초 폴링으로 전 PC 동기화.
  - index2 "클라우드 업무"에 카드 추가. **남은 것**: 파일함/네트워크 저장(`/api/files`,`/api/upload`,`/api/info`)은 서버 전용이라 GitHub Pages에선 비활성(그레이스풀). 필요 시 Supabase Storage로 전환 검토.
  - 다른 화면들(수주/판매/품질/인사 등)도 모두 app_state 사용 → 전 PC 공유 OK. (`SPC측정관리.html`만 로컬 저장 — 추후 연동)

## ▶ 다음 작업 (B단계 계속): prod-plan.html 클라우드 연동
목표: 핵심 탭 데이터를 **Supabase로 저장/전 PC 공유**.

### prod-plan.html 특징 (중요)
- 저장을 **사내 서버 API**로 함: `const API_BASE = window.location.origin;` → `fetch(API_BASE + '/api/files'|'/api/bom'|'/api/info'|'/api/upload/...')`.
- 그래서 **GitHub Pages(정적)에서는 저장/파일함/BOM동기화가 안 됨** (API 없음). `STORE_KEY='sj_prod_v3'` 는 미사용(호환용).
- 탭: 일일계획 · 생산일보 · 불량분석 · 품목마스터 · BOM관리 · 파일함 · 주간계획 · 월간계획.

### 권장 방법 (단계적)
1. 먼저 prod-plan.html 을 읽어 **데이터가 실제로 담기는 전역 변수/함수**를 파악 (일일계획·생산일보·불량 데이터 구조).
2. **파일함/파일업로드(`/api/files`,`/api/upload`)** 처럼 서버가 꼭 필요한 기능은 **제외 또는 "서버 전용" 표시**.
3. 나머지 핵심(일일계획·생산일보·불량분석·품목·BOM목록)은:
   - 방법A: 앱 데이터 객체를 **Supabase `app_state` 키**(예: `prodplan_daily`, `prodplan_defect`)에 저장/구독 — prod-report.html 상단 동기화 스크립트 패턴 재사용.
   - 방법B(더 깔끔): 전용 테이블(예: `prod_plan`, `prod_defect`) 만들고 CRUD 교체. (SQL은 화면 안내 + Supabase에서 사용자가 Run)
4. 잘 되면 index2 "클라우드 업무"에 **📋 생산계획·실적** 카드 추가 + 바로가기 목록에 추가.

### 참고 (재사용할 것)
- **prod-report.html 상단의 동기화 `<script>`** — localStorage 전체를 app_state 한 키에 미러링하는 패턴. prod-plan이 localStorage를 쓰도록 먼저 바꾸면 이 패턴을 그대로 재사용 가능.
- **cloud.js** — `Cloud.get(key)/set(key,value)/on(key,cb)`.
- **production.html** — 전용 테이블(CRUD) + 실시간 구독 예시.

## 검증 방법
- 저장 후 `git push` → 1~2분 뒤 Pages 반영 → 다른 PC(또는 시크릿창)에서 열어 같은 데이터 보이면 성공.
- 각 화면 좌하단/상단 클라우드 상태 배지 확인.
