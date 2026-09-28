@echo off
chcp 65001 >nul
setlocal EnableExtensions
title 승정 ERP - 작업 시작
rem ================================================================
rem  승정 ERP - 작업 시작  (작업 전에 더블클릭 한 번)
rem   [1] GitHub 에서 최신 코드 받기  (git pull --ff-only)
rem   [2] 회사 OneDrive 의 Claude 메모리를 이 PC 로 복사
rem       - 더 최신 파일만 덮어씀. 아무것도 지우지 않음.
rem   [3] 이 PC 에 Claude 설정 파일이 없을 때만 OneDrive 백업본을 복사
rem  * 개인 OneDrive 는 절대 쓰지 않습니다. 회사 OneDrive 만 씁니다.
rem  * 한 번에 한 PC 에서만 작업하세요. 집과 사무실 동시 작업 금지.
rem  * GitHub 저장소가 공개되어 있으므로 이 파일에 비밀번호, 서버 주소,
rem    키 같은 비밀 정보를 절대 적지 마세요.
rem ================================================================

rem ---- 저장소 폴더 = 이 파일이 들어 있는 tools 폴더의 상위 폴더
for %%I in ("%~dp0..") do set "REPO=%%~fI"

rem ---- [테스트 전용] 자동 테스트할 때만 쓰는 변수입니다. 평소에는 설정하지 마세요.
rem      SJ_TEST_OD      = 회사 OneDrive 대신 쓸 가짜 폴더
rem      SJ_TEST_PROFILE = 사용자 폴더 대신 쓸 가짜 폴더
rem      SJ_TEST_NOGIT   = git 명령을 건너뜀
rem      SJ_NOPAUSE      = 마지막 일시정지를 건너뜀
set "UPROF=%USERPROFILE%"
if defined SJ_TEST_PROFILE set "UPROF=%SJ_TEST_PROFILE%"

echo ================================================================
echo  승정 ERP - 작업 시작
echo ================================================================
if /i "%REPO%"=="C:\ERP\seungjeong-erp" goto :REPO_OK
echo  [주의] 저장소 위치가 C:\ERP\seungjeong-erp 가 아닙니다.
echo         지금 위치: "%REPO%"
echo         모든 PC 에서 같은 위치여야 Claude 메모리가 이어집니다.
echo.
:REPO_OK

rem ---- [OneDrive 감지 시작] ----
rem  회사(비즈니스) OneDrive 폴더를 찾습니다. 개인 OneDrive 는 쓰지 않습니다.
set "OD="
set "OD_HOW="
if defined SJ_TEST_OD set "OD=%SJ_TEST_OD%"
if defined SJ_TEST_OD set "OD_HOW=테스트 폴더"
if defined SJ_TEST_OD goto :OD_CHECK
rem  (1) 환경변수 OneDriveCommercial
if defined OneDriveCommercial if exist "%OneDriveCommercial%\" set "OD=%OneDriveCommercial%"
if defined OD set "OD_HOW=환경변수 OneDriveCommercial"
if defined OD goto :OD_CHECK
rem  (2) 레지스트리: 회사 계정 Business1 의 UserFolder
for /f "tokens=1,2,*" %%A in ('reg query "HKCU\Software\Microsoft\OneDrive\Accounts\Business1" /v UserFolder 2^>nul') do if /i "%%A"=="UserFolder" set "OD=%%C"
if defined OD if not exist "%OD%\" set "OD="
if defined OD set "OD_HOW=레지스트리 Business1"
if defined OD goto :OD_CHECK
rem  (3) 사용자 폴더 안의 "OneDrive - 회사이름" 폴더. 개인 OneDrive 는 제외.
set "OD_PERSONAL="
for /f "tokens=1,2,*" %%A in ('reg query "HKCU\Software\Microsoft\OneDrive\Accounts\Personal" /v UserFolder 2^>nul') do if /i "%%A"=="UserFolder" set "OD_PERSONAL=%%C"
for /d %%D in ("%USERPROFILE%\OneDrive - *") do if not defined OD if /i not "%%~fD"=="%OD_PERSONAL%" if /i not "%%~nxD"=="OneDrive - Personal" if /i not "%%~nxD"=="OneDrive - 개인" set "OD=%%~fD"
if defined OD set "OD_HOW=폴더 이름 검색"
:OD_CHECK
rem ---- [OneDrive 감지 끝] ----
if not defined OD goto :NO_OD
if not exist "%OD%\" goto :NO_OD
for %%I in ("%OD%\.") do set "OD=%%~fI"

set "DEV=%OD%\SEUNGJEONG_ERP_DEV"
set "MEM_CLOUD=%DEV%\claude-memory"
set "MEM_LOCAL=%UPROF%\.claude\projects\C--ERP-seungjeong-erp\memory"
set "SET_LOCAL=%UPROF%\.claude\settings.json"
set "SET_CLOUD=%DEV%\claude-settings.json"
echo  회사 OneDrive : "%OD%"
echo.

rem ================= [1/3] 최신 코드 받기 =================
echo [1/3] GitHub 에서 최신 코드 받는 중...
set "GIT_RESULT="
if defined SJ_TEST_NOGIT set "GIT_RESULT=건너뜀 - 테스트 모드"
if defined SJ_TEST_NOGIT echo    → 건너뜀 - 테스트 모드
if defined SJ_TEST_NOGIT goto :MEM_STEP
call :FIND_GIT
if not defined GIT goto :GIT_MISSING
if not exist "%REPO%\.git\" goto :GIT_NOREPO
set "GIT_TERMINAL_PROMPT=0"
"%GIT%" -C "%REPO%" pull --ff-only
if errorlevel 1 goto :GIT_PULL_FAIL
set "GIT_RESULT=최신 코드 받기 완료"
echo    → 최신 코드 받기 완료
goto :MEM_STEP

:GIT_PULL_FAIL
set "GIT_RESULT=실패 - GitHub Desktop 확인 필요"
echo.
echo  [주의] 최신 코드를 받지 못했습니다. 메모리 복사는 계속 진행합니다.
echo    흔한 이유: 이 PC 에 아직 Commit/Push 하지 않은 수정이 있거나,
echo               다른 PC 에서 올린 수정과 같은 파일이 겹쳤습니다.
echo    해결 방법:
echo      1. GitHub Desktop 을 엽니다.
echo      2. 바뀐 파일이 보이면 Summary 칸에 메모를 쓰고 "Commit to master" 를 누릅니다.
echo      3. 위쪽 "Fetch origin" 또는 "Pull origin" 을 누릅니다.
echo      4. "Conflict" (충돌) 가 나오면 혼자 고치지 말고 Claude 에게 물어보세요.
echo.
goto :MEM_STEP

:GIT_MISSING
set "GIT_RESULT=git 없음 - GitHub Desktop 에서 직접 Pull 필요"
echo  [주의] git 프로그램을 찾지 못했습니다.
echo         GitHub Desktop 에서 "Fetch origin" / "Pull origin" 을 직접 눌러 주세요.
goto :MEM_STEP

:GIT_NOREPO
set "GIT_RESULT=git 저장소 아님 - 확인 필요"
echo  [주의] 이 폴더는 git 저장소가 아니라서 코드 받기를 건너뜁니다: "%REPO%"
goto :MEM_STEP

rem ================= [2/3] Claude 메모리 받기 =================
:MEM_STEP
echo.
echo [2/3] Claude 메모리 받기: 회사 OneDrive → 이 PC  (더 최신 파일만, 삭제 없음)
set "BAD_DIR=%MEM_CLOUD%"
if not exist "%MEM_CLOUD%\" mkdir "%MEM_CLOUD%" 2>nul
if not exist "%MEM_CLOUD%\" goto :MKDIR_FAIL
set "BAD_DIR=%MEM_LOCAL%"
if not exist "%MEM_LOCAL%\" mkdir "%MEM_LOCAL%" 2>nul
if not exist "%MEM_LOCAL%\" goto :MKDIR_FAIL
set "RLOG=%TEMP%\sj_robocopy_%RANDOM%%RANDOM%.log"
robocopy "%MEM_CLOUD%" "%MEM_LOCAL%" /E /XO /XX /R:1 /W:1 /NJH /NJS /NDL /NP /UNILOG:"%RLOG%" >nul 2>&1
if %ERRORLEVEL% GEQ 8 goto :MEM_FAIL
rem  복사된 파일 목록 = robocopy 기록의 3번째 칸 (delims= 뒤에는 탭 문자 1개, 스페이스 아님)
set /a COPIED=0
if exist "%RLOG%" for /f "usebackq tokens=3 delims=	" %%P in (`type "%RLOG%"`) do (
  set /a COPIED+=1
  echo      + %%~nxP
)
if exist "%RLOG%" del /q "%RLOG%" >nul 2>&1
set /a TOTAL=0
for /r "%MEM_LOCAL%" %%F in (*) do set /a TOTAL+=1
echo    → 이번에 받은 파일 %COPIED%개 / 이 PC 메모리 파일 총 %TOTAL%개

rem ================= [3/3] Claude 설정 파일 =================
echo.
echo [3/3] Claude 설정 파일(settings.json) 확인
if exist "%SET_LOCAL%" set "SET_RESULT=이 PC 설정 그대로 유지 (덮어쓰지 않음)"
if exist "%SET_LOCAL%" goto :SET_DONE
if not exist "%SET_CLOUD%" set "SET_RESULT=OneDrive 에 백업 없음 - 건너뜀"
if not exist "%SET_CLOUD%" goto :SET_DONE
if not exist "%UPROF%\.claude\" mkdir "%UPROF%\.claude" 2>nul
copy /Y "%SET_CLOUD%" "%SET_LOCAL%" >nul 2>&1
if errorlevel 1 goto :SET_FAIL
set "SET_RESULT=OneDrive 백업본을 이 PC 로 복사함"
goto :SET_DONE
:SET_FAIL
set "SET_RESULT=복사 실패 - 직접 확인 필요"
:SET_DONE
echo    → %SET_RESULT%

echo.
echo ================================================================
echo  작업 시작 준비 완료
echo    회사 OneDrive : "%OD%"
echo    최신 코드     : %GIT_RESULT%
echo    Claude 메모리 : 이번에 %COPIED%개 받음 / 이 PC 에 총 %TOTAL%개
echo    Claude 설정   : %SET_RESULT%
echo.
echo  ※ 한 번에 한 PC 에서만 작업하세요. 집/사무실 동시 작업 금지.
echo  ※ 작업을 마치면 tools\작업종료.bat 을 꼭 더블클릭하세요.
echo ================================================================
call :PAUSE_END
endlocal
exit /b 0

rem ================= 오류 처리 =================
:NO_OD
echo.
echo  [오류] 회사 OneDrive (승정) 폴더를 찾지 못했습니다.
echo    1. 화면 오른쪽 아래 작업표시줄의 구름 모양 OneDrive 아이콘을 누릅니다.
echo    2. 회사 계정(승정)으로 로그인하고 동기화가 끝날 때까지 기다립니다.
echo    3. 파일 탐색기 왼쪽에 "OneDrive - 승정" 이 보이면 이 파일을 다시 실행합니다.
echo    ※ 개인 OneDrive 는 쓰지 않습니다. 회사 자료는 회사 OneDrive 에만 저장합니다.
echo    아무것도 복사하지 않고 종료합니다.
if defined SJ_TEST_OD echo    [테스트] SJ_TEST_OD 폴더 없음: "%SJ_TEST_OD%"
call :PAUSE_END
exit /b 1

:MKDIR_FAIL
echo.
echo  [오류] 폴더를 만들 수 없습니다: "%BAD_DIR%"
echo         OneDrive 로그인 상태와 남은 저장 공간을 확인한 뒤 다시 실행하세요.
call :PAUSE_END
exit /b 3

:MEM_FAIL
set "RC=%ERRORLEVEL%"
echo.
echo  [오류] Claude 메모리 복사에 실패했습니다. (robocopy 코드 %RC%)
echo    - OneDrive 가 동기화 중이거나 파일이 다른 프로그램에서 열려 있을 수 있습니다.
echo    - 잠시 뒤 다시 실행해 보세요. 계속 안 되면 아래 내용을 Claude 에게 보여 주세요.
if exist "%RLOG%" type "%RLOG%"
if exist "%RLOG%" del /q "%RLOG%" >nul 2>&1
call :PAUSE_END
exit /b 2

rem ================= 보조 기능 =================
:PAUSE_END
if not defined SJ_NOPAUSE pause
exit /b 0

:FIND_GIT
rem  git.exe 찾기: PATH → GitHub Desktop 내장 git → Git for Windows 기본 위치
set "GIT="
for %%G in (git.exe) do if not "%%~$PATH:G"=="" set "GIT=%%~$PATH:G"
if defined GIT exit /b 0
for /d %%D in ("%LOCALAPPDATA%\GitHubDesktop\app-*") do if exist "%%~fD\resources\app\git\cmd\git.exe" set "GIT=%%~fD\resources\app\git\cmd\git.exe"
if defined GIT exit /b 0
if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
exit /b 0
