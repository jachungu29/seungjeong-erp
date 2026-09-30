# 승정 ERP · 여러 PC에서 Claude와 작업하기 (사장님용 가이드)

> 사무실 PC와 집 PC 어디서든 **같은 코드, 같은 Claude 기억**으로 이어서 작업하는 방법입니다.
> 한 줄 요약: **시작할 때 `작업시작.bat` → Claude와 작업 → 끝날 때 `작업종료.bat` → GitHub Desktop에서 Commit → Push**

---

## 0. 가장 쉬운 시작 — "집이야" / "사무실이야" 한마디

Claude Code를 열고 채팅창에 **"집이야"** 또는 **"사무실이야"** 라고만 치세요.
- Claude가 자동으로 GitHub 최신 내용을 받고(pull) 상태를 확인해 "준비 완료"라고 알려줍니다.
- 작업이 끝나면 **"끝"** 또는 **"저장"** 이라고 치면 GitHub에 자동으로 올려(push)줍니다.

> Claude의 대화 기억(메모리)까지 PC 간에 옮기려면 시작 전에 `tools\작업시작.bat`을 더블클릭하는 것이 가장 좋습니다. 코드 최신화만 필요하면 "집이야" 한마디로 충분합니다.

---

## 1. 왜 이렇게 하나요?

작업에 쓰는 재료를 **네 곳**에 나눠 둡니다. 각자 잘하는 일이 다르기 때문입니다.

```
            [ GitHub · 공개 저장소 ]  ←  코드 (화면 HTML 파일)
              ▲ push   │ pull                ▲ push   │ pull
              │        ▼                     │        ▼
        [ 사무실 PC ]   ◀── 동시 작업 금지 ──▶   [ 집 PC ]
     C:\ERP\seungjeong-erp               C:\ERP\seungjeong-erp
              │ 올리기  ▲ 받기                │ 올리기  ▲ 받기
              ▼        │                     ▼        │
    [ 회사 OneDrive · SEUNGJEONG_ERP_DEV ]  ←  Claude 기억 · 대용량 파일 · 비공개 메모

    [ 회사 NAS · 사내망 전용 ]  ←  ERP 실제 데이터(DB), 서버 비밀번호·키 (사무실에서만 접속)
```

| 무엇 | 어디에 | 이유 |
|---|---|---|
| 코드(화면 파일) | GitHub | 누가 언제 무엇을 바꿨는지 기록이 남고, 인터넷에 공개 배포(GitHub Pages)됩니다 |
| Claude 기억, 대용량 파일, 비공개 메모 | 회사 OneDrive | GitHub가 **공개** 저장소라서 여기에 두면 안 되는 것들입니다 |
| 실제 업무 데이터 | DB (지금은 외부 클라우드 → 회사 NAS로 옮기는 중) | 코드와 데이터는 따로 둡니다 |
| 서버 비밀번호·키 | 회사 NAS와 사무실 PC에만 | 어떤 클라우드에도 올리지 않습니다 |

**왜 모든 PC에서 폴더 위치가 `C:\ERP\seungjeong-erp`로 똑같아야 하나요?**
- Claude Code는 작업 폴더 경로로 "기억 폴더" 이름을 만듭니다.
  - `C:\ERP\seungjeong-erp` → `C--ERP-seungjeong-erp`
- PC마다 경로가 다르면 기억 폴더도 달라져서 지난 작업을 이어서 기억하지 못합니다.
- 바탕화면 바로가기(`승정 ERP.url`)의 아이콘도 이 경로를 씁니다.

**왜 개인 OneDrive는 안 쓰나요?**
- 회사 자료는 회사(비즈니스) OneDrive에만 둡니다.
- 스크립트도 개인 OneDrive는 일부러 건너뛰도록 만들었습니다.

---

## 2. 새 PC 1회 준비 (처음 한 번만)

처음 한 번만 하면 됩니다. 순서대로 따라 하세요.

### ① GitHub Desktop 설치하고 로그인
1. 인터넷 브라우저에서 `desktop.github.com`에 들어가 GitHub Desktop을 내려받아 설치합니다.
2. 실행한 뒤 **Sign in to GitHub.com**을 누릅니다. 브라우저 창이 열리면 회사 GitHub 계정(jachungu29)으로 로그인하고 승인합니다.
   - 비밀번호는 사장님이 직접 입력합니다. Claude에게 알려 주지 마세요.
3. 이름·이메일 확인 화면이 나오면 그대로 **Finish**를 누릅니다.

### ② 저장소를 반드시 `C:\ERP\seungjeong-erp`에 받기 (Clone)

> **이미 폴더가 있는데 구조가 다를 때:** 새로 clone 하지 말고 `tools\작업시작.bat`을 더블클릭해 최신을 받으세요. 표준은 **`화면/` 폴더 하나** 구조입니다(2026-09-30 사장님 결정).

1. 파일 탐색기에서 `C:` 드라이브를 열고 **`ERP`** 폴더가 없으면 새로 만듭니다.
2. GitHub Desktop 메뉴에서 **File → Clone repository...** 를 누릅니다.
3. **GitHub.com** 탭에서 `jachungu29/seungjeong-erp`를 고릅니다. 목록에 없으면 **URL** 탭에 `jachungu29/seungjeong-erp`를 입력합니다.
4. 아래쪽 **Local path** 칸을 **정확히** 다음처럼 고칩니다.
   ```
   C:\ERP\seungjeong-erp
   ```
   - 기본값(`...\Documents\GitHub\...`)을 그대로 두면 안 됩니다.
   - 소문자와 하이픈(-)까지 똑같아야 합니다.
   - 옛 폴더 `C:\ERP\SEUNGJEONG ERP V2`는 쓰지 않습니다.
5. **Clone**을 누릅니다.
   - 약 100MB 정도라 몇 분 걸릴 수 있습니다. 끝날 때까지 기다리세요.
   - 이미 `C:\ERP\seungjeong-erp` 폴더가 있는데 오래된 것이라면, 먼저 폴더 이름을 `seungjeong-erp_옛날`처럼 바꾼 뒤 Clone 하세요(Q9 참고).
7. (ISIR 성적서 PDF가 필요한 PC만) PDF 18개는 GitHub에 없습니다. 다른 PC의 `C:\ERP\_ARCHIVE_isir_pdf` 폴더를 USB나 회사 OneDrive `대용량파일`로 옮겨 같은 위치에 둡니다.
6. 끝나면 위쪽 **Current branch**가 `master`인지 확인합니다.

### ③ 회사 OneDrive 로그인 확인
1. 화면 오른쪽 아래 작업표시줄에서 **구름 모양 OneDrive 아이콘**을 누릅니다.
2. **회사(비즈니스) Microsoft 계정**으로 로그인되어 있는지 확인합니다. 안 되어 있으면 로그인하고 동기화가 끝날 때까지 기다립니다.
3. 파일 탐색기 왼쪽에 **`OneDrive - 승정`** 이 보이고, 그 안에 **`SEUNGJEONG_ERP_DEV`** 폴더가 있는지 확인합니다.
   - 개인 OneDrive(`OneDrive - Personal` 또는 그냥 `OneDrive`)는 쓰지 않습니다.
4. (권장) `SEUNGJEONG_ERP_DEV` 폴더를 마우스 오른쪽 버튼으로 누르고 **"이 장치에 항상 유지"** 를 고릅니다. 파일이 PC에 미리 내려받아져 있어 복사가 안정적입니다.

### ④ 처음 한 번 `작업시작.bat` 실행
1. 파일 탐색기에서 `C:\ERP\seungjeong-erp\tools` 폴더를 엽니다.
2. **`작업시작.bat`** 을 더블클릭합니다.
3. 검은 창에 [1/3] [2/3] [3/3] 이 차례로 나오고, 마지막에 요약이 나옵니다.
   - "Claude 메모리 : 이번에 N개 받음" 이 나오면 OneDrive에 있던 기억이 이 PC로 들어온 것입니다.
   - "Claude 설정 : OneDrive 백업본을 이 PC 로 복사함" 이 나오면 Claude 권한 설정도 들어온 것입니다.
4. 아무 키나 눌러 창을 닫습니다.

### ⑤ Claude Code에서 그 폴더 열기
1. Claude 데스크톱 앱을 설치하고 로그인합니다.
2. Claude Code 작업 폴더로 **`C:\ERP\seungjeong-erp`** 를 고릅니다.
3. **새 대화**를 열고 이렇게 말합니다: **"이 저장소의 _HANDOFF.md 읽고 이어서 해줘"**
   - Claude는 저장소 맨 위의 `CLAUDE.md`(프로젝트 규칙)를 자동으로 읽습니다.
   - 기억(메모리)은 **대화를 시작할 때** 읽습니다. 그래서 `작업시작.bat`을 **먼저** 실행해야 합니다.

> (선택) 화면을 PC에서 미리 볼 때 Python이 필요할 수 있습니다. 필요하면 Claude가 안내합니다.

---

## 3. 매일 루틴

### 🌅 시작할 때
1. 다른 PC에서 하던 작업을 **끝내고 Push까지 했는지** 확인합니다. 동시 작업은 금지입니다.
2. `C:\ERP\seungjeong-erp\tools\작업시작.bat` 을 더블클릭하고, 마지막 요약을 확인한 뒤 아무 키나 눌러 닫습니다.
3. Claude Code에서 `C:\ERP\seungjeong-erp` 폴더로 **새 대화**를 열고 **"_HANDOFF.md 읽고 이어서 하자"** 라고 말합니다.

### 🌙 끝낼 때
1. (권장) Claude에게 **"오늘 작업 정리해서 _HANDOFF.md 갱신해줘"** 라고 말합니다.
2. `tools\작업종료.bat` 을 더블클릭합니다. 바뀐 파일 목록을 보여 줍니다.
3. **GitHub Desktop**에서 올립니다.
   1. 왼쪽 목록에서 바뀐 파일을 확인합니다.
   2. 왼쪽 아래 **Summary** 칸에 무엇을 했는지 짧게 적습니다(예: `품질관리 화면 수정`).
   3. **Commit to master** 를 누릅니다.
   4. 위쪽 **Push origin** 을 누릅니다.
4. 작업표시줄 OneDrive 구름 아이콘이 **"최신 상태"** 가 된 뒤에 PC를 끕니다.

### 두 파일이 실제로 하는 일

**`작업시작.bat`** (작업 전)

| 단계 | 하는 일 |
|---|---|
| 확인 | 저장소 위치가 `C:\ERP\seungjeong-erp`가 아니면 [주의]를 띄웁니다(작업은 계속). |
| 회사 OneDrive 찾기 | ① 환경변수 `OneDriveCommercial` ② 레지스트리의 회사 계정 폴더 ③ 사용자 폴더의 `OneDrive - 회사이름` 폴더(개인 것 제외) 순서로 찾습니다. 못 찾으면 **아무것도 복사하지 않고** 끝납니다. |
| [1/3] 최신 코드 받기 | `git pull --ff-only` 로 GitHub에서 최신 코드를 받습니다. git은 GitHub Desktop에 들어 있는 것도 찾아 씁니다. 실패하면 방법을 안내하고 다음 단계는 계속합니다. |
| [2/3] Claude 기억 받기 | OneDrive `claude-memory` → 이 PC `%USERPROFILE%\.claude\projects\C--ERP-seungjeong-erp\memory`. **새 파일과 더 최신인 파일만** 복사하고 **아무것도 지우지 않습니다**. 받은 파일 이름과 개수를 보여 줍니다. |
| [3/3] Claude 설정 | 이 PC에 `%USERPROFILE%\.claude\settings.json` 이 **없을 때만** OneDrive의 `claude-settings.json` 을 복사합니다. 이미 있으면 건드리지 않습니다. |

**`작업종료.bat`** (작업 후)

| 단계 | 하는 일 |
|---|---|
| 확인 | 시작 파일과 똑같이 위치를 확인하고 회사 OneDrive를 찾습니다. |
| [1/3] Claude 기억 올리기 | 이 PC `memory` 폴더 → OneDrive `claude-memory`. **새 파일과 더 최신인 파일만** 복사하고 **아무것도 지우지 않습니다**. |
| [2/3] Claude 설정 백업 | `settings.json` → OneDrive `claude-settings.json`. 백업이 없으면 처음 만들고, 내용이 같으면 그대로 둡니다. **이 PC 쪽이 더 최신일 때만** 덮어씁니다. |
| [3/3] 코드 변경 확인 | GitHub에 아직 안 올린 변경 파일 목록과 개수, Commit은 했지만 Push 안 한 개수를 보여 줍니다. **자동으로 Commit/Push 하지 않습니다.** GitHub Desktop에서 직접 합니다. |

---

## 4. 공유 폴더 구조 (회사 OneDrive)

```
OneDrive - 승정\
└─ SEUNGJEONG_ERP_DEV\
   ├─ README.md               이 폴더 설명
   ├─ PRIVATE_인프라정보.md     서버 접속 정보 같은 비공개 메모 (GitHub에 절대 올리지 않음)
   ├─ claude-settings.json    Claude 권한 설정 백업 (bat 파일이 자동 관리)
   ├─ claude-memory\          Claude 작업 기억 (bat 파일이 자동 복사)
   └─ 대용량파일\              Git에 넣지 않는 큰 파일 (예: 승정_MES_개발본_REV35.html)
```

각 PC 안에서는 이렇게 이어집니다.

```
C:\ERP\seungjeong-erp\                                       ← 코드 (GitHub와 동기화)
%USERPROFILE%\.claude\projects\C--ERP-seungjeong-erp\memory\  ← Claude 기억 (이 PC)
%USERPROFILE%\.claude\settings.json                          ← Claude 설정 (이 PC)
```

- `claude-memory` 안의 파일은 손으로 고치지 마세요. Claude가 관리합니다.
- 서버 비밀번호와 키는 `PRIVATE_인프라정보.md`에도 적지 않습니다. 회사 NAS와 사무실 PC에만 있습니다.

---

## 5. Git(GitHub)에 없는 것과 있는 곳

| 무엇 | 있는 곳 | 비고 |
|---|---|---|
| Claude 기억(메모리) | OneDrive `claude-memory` ↔ 각 PC의 `memory` 폴더 | 작업시작/종료 bat가 옮겨 줍니다 |
| Claude 설정(settings.json) | OneDrive `claude-settings.json` ↔ 각 PC | 새 PC에 없을 때만 받아 옵니다 |
| REV35 MES 개발본 등 큰 파일 | OneDrive `대용량파일` | GitHub는 50MB에서 경고, 100MB에서 거부합니다. `legacy.html`만으로 이미 약 50MB입니다 |
| ISIR 성적서 PDF 18개(약 445MB) | 각 PC의 `C:\ERP\_ARCHIVE_isir_pdf` | 저장소를 가볍게 하려고 뺐습니다. `.gitignore`가 PDF를 막습니다 |
| 서버 접속 정보 같은 내부 메모 | OneDrive `PRIVATE_인프라정보.md` | 공개 저장소에 올리면 안 됩니다 |
| **NAS 서버 비밀번호·접속키(.env 등)** | **회사 NAS 안의 원본과 사무실 PC에만** | **클라우드 동기화 안 함.** OneDrive에도 두지 않습니다 |
| ERP 실제 업무 데이터 | DB (지금 외부 클라우드, 이전 후 회사 NAS) | 코드와 별개입니다. 메뉴 구조(map_struct)도 DB에 있어 push가 필요 없습니다 |
| 브라우저에만 저장된 값(localStorage) | 각 PC의 브라우저 | PC끼리 공유되지 않습니다. 공유가 필요하면 Claude에게 클라우드 저장으로 바꿔 달라고 하세요 |

- 저장소의 `.gitignore`가 `.env`, `*.zip`, `_KEYS*`, `*접속키*`, `BUILD_LOG*.txt`, `*.bak` 같은 파일이 실수로 올라가지 않게 막아 줍니다.
- 그래도 **비밀번호·키·서버 주소는 저장소 폴더에 아예 두지 않는 것**이 원칙입니다.

---

## 6. 문제 해결 FAQ

### Q1. `작업시작.bat`에 "[주의] 최신 코드를 받지 못했습니다"가 떠요
- **이유**
  - 이 PC에 아직 Commit/Push 하지 않은 수정이 있거나, 다른 PC에서 올린 수정과 겹친 경우입니다.
  - `--ff-only`는 "안전하게 앞으로만 받기"라서, 엇갈리면 **아무것도 바꾸지 않고 멈춥니다**. 파일이 망가지지 않습니다.
- **해결**
  1. GitHub Desktop을 엽니다.
  2. 바뀐 파일이 보이면 Summary를 적고 **Commit to master**를 누릅니다.
  3. 위쪽 **Fetch origin** 또는 **Pull origin**을 누릅니다.
  4. **"Conflict(충돌)"** 가 나오면 혼자 고치지 말고, 그 화면을 Claude에게 보여 주며 "충돌 해결해줘"라고 하세요.
- 기억(메모리) 받기는 코드 받기가 실패해도 계속 진행됩니다.

### Q2. Push를 눌렀더니 거절(rejected)되거나 "먼저 Pull 하라"고 해요
- 다른 PC에서 먼저 올린 것이 있다는 뜻입니다.
- **Pull origin** → 다시 **Push origin** 순서로 누릅니다.
- "한 번에 한 PC" 규칙을 지키면 거의 생기지 않습니다.

### Q3. "[오류] 회사 OneDrive (승정) 폴더를 찾지 못했습니다"
1. 작업표시줄 구름 아이콘을 누르고 **회사(비즈니스) 계정**으로 로그인한 뒤, 동기화가 끝날 때까지 기다립니다.
2. 파일 탐색기 왼쪽에 `OneDrive - 승정`이 보이면 bat 파일을 다시 실행합니다.
- 개인 OneDrive만 로그인되어 있으면 이 오류가 나는 것이 **정상**입니다. 개인 OneDrive는 일부러 쓰지 않습니다.
- "폴더를 만들 수 없습니다" 또는 "메모리 복사에 실패했습니다(robocopy 코드 …)"가 나오면:
  - OneDrive가 동기화 중이거나 저장 공간이 부족한 경우입니다. 잠시 뒤 다시 실행하세요.
  - 계속되면 그 화면을 Claude에게 보여 주세요.

### Q4. "[주의] 저장소 위치가 C:\ERP\seungjeong-erp 가 아닙니다"
- 다른 위치에 Clone한 것입니다. 이대로 두면 Claude 기억이 이어지지 않습니다.
- **해결**
  1. GitHub Desktop과 Claude를 닫습니다.
  2. 파일 탐색기에서 폴더를 `C:\ERP\seungjeong-erp`로 옮깁니다(이름까지 똑같이).
  3. GitHub Desktop을 열면 "저장소를 찾을 수 없음"이 나옵니다. **Locate...** 를 눌러 새 위치를 지정합니다.
- 어렵다면 Claude에게 "저장소 위치 바로잡는 것 도와줘"라고 하세요.

### Q5. 집에서는 NAS 데이터가 안 보여요
- **정상입니다.** 회사 NAS의 DB는 **사내망 전용**으로 설계했습니다. 회사 밖에서는 연결되지 않습니다.
- **코드 작업**(화면 만들기·수정)은 집에서도 됩니다. 실제 데이터 확인과 입력 테스트는 사무실에서 합니다.
- NAS 이전이 끝나기 전까지는 외부 클라우드 DB를 쓰는 화면이 많아서 집에서도 보일 수 있습니다. NAS로 바꾼 화면부터 집에서는 안 보이거나 "로컬 모드"로 표시됩니다.
- 집에서 NAS를 쓰겠다고 인터넷 쪽 접속을 임의로 열지 마세요. 필요하면 Claude와 보안 검토부터 합니다.

### Q6. Claude가 지난 작업을 기억 못 해요 (메모리가 이상해요)
- **다음을 차례로 확인하세요**
  1. `작업시작.bat`을 **Claude 대화를 시작하기 전에** 실행했나요? 기억은 대화를 시작할 때 읽습니다. bat 실행 후 **새 대화**를 여세요.
  2. Claude Code 작업 폴더가 정확히 `C:\ERP\seungjeong-erp`인가요?
  3. 지난번 PC에서 `작업종료.bat`을 실행했고, 그 PC의 OneDrive가 "최신 상태"가 된 뒤에 껐나요?
  4. `%USERPROFILE%\.claude\projects\C--ERP-seungjeong-erp\memory` 폴더에 `MEMORY.md`가 있나요?
- **지운 기억이 자꾸 되살아나요**
  - bat 파일은 안전을 위해 **절대 지우지 않습니다**.
  - 정말 지우려면 이 PC의 memory 폴더와 OneDrive `claude-memory` **양쪽에서** 지워야 합니다. Claude에게 부탁하세요.
- **두 PC에서 같은 기억 파일이 따로 바뀌었어요**
  - **더 나중에 저장된 파일이 이깁니다.** 다른 쪽 변경은 사라집니다. 동시 작업을 금지하는 이유입니다.
  - 잘못 덮어썼다면 OneDrive 웹에서 그 파일을 오른쪽 버튼으로 누르고 **버전 기록**에서 예전 버전으로 되돌릴 수 있습니다.
- 기억이 꼬여도 `_HANDOFF.md`와 `CLAUDE.md`는 저장소(GitHub)에 있습니다. **"_HANDOFF.md 읽고 이어서 해줘"** 로 작업을 이어 갈 수 있습니다.

### Q7. Push했는데 인터넷 ERP 화면이 그대로예요
- GitHub Pages에 반영되기까지 1~2분 걸립니다.
- 탭을 완전히 닫고 다시 열거나 **Ctrl+F5**를 누르세요(옛 화면이 캐시에 남아 있는 경우).

### Q8. 큰 파일을 GitHub에 올리려다 거절됐어요
- GitHub는 파일 하나가 50MB를 넘으면 경고하고, 100MB를 넘으면 거부합니다.
- 큰 파일은 OneDrive `대용량파일` 폴더에 두세요. 이미 Commit했다면 Push하기 전에 Claude에게 "방금 커밋에서 큰 파일 빼줘"라고 하세요.

### Q9. GitHub Desktop이 "diverged(갈라짐)"라고 하거나, Pull이 계속 실패해요
- 두 PC가 서로 다른 버전에서 따로 작업해서 **길이 갈라진** 상태입니다. (2026-09-28에 실제로 있었던 일: 사무실 PC가 7월에 저장소를 가볍게 정리하는 동안, 집 PC는 옛 버전에서 계속 작업했습니다.)
- **혼자 "Force push"를 누르지 마세요.** 다른 PC의 작업이 통째로 사라집니다.
- Claude에게 "두 PC 버전이 갈라졌어, 확인해줘"라고 하세요. Claude가 먼저 백업을 만들고, 어느 쪽을 기준으로 할지 물어본 뒤 맞춰 줍니다.

---

## 꼭 지킬 것 5가지
1. **시작은 `작업시작.bat`, 끝은 `작업종료.bat` → Commit → Push**
2. **집·사무실 동시 작업 금지**
3. 모든 PC에서 **`C:\ERP\seungjeong-erp`** 경로 사용
4. 회사 자료는 **회사 OneDrive**에만(개인 OneDrive 금지)
5. **비밀번호·키·서버 주소는 GitHub에 절대 올리지 않기**(공개 저장소)

### Q7. ERP를 열었는데 데이터가 갑자기 다 안 보여요 (Failed to fetch)
- 예전 인터넷 DB(Supabase)는 **2026-09-29 사장님이 직접 삭제**했습니다. 되살리지 않습니다(데이터는 회사 안 나스에 둘 예정).
- 브라우저의 **"인터넷 사용 기록 삭제 → 쿠키 및 사이트 데이터"는 절대 누르지 마세요**(자료가 지워짐).