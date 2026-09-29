@echo off
chcp 65001 >nul
setlocal EnableExtensions
title 승정 ERP - 브라우저 데이터 백업
rem ================================================================
rem  승정 ERP - 브라우저 데이터 백업  (더블클릭 한 번)
rem   엣지 / 크롬 / 웨일 / 브레이브 / 클로드 앱 / 파이어폭스에 들어 있는
rem   ERP 데이터 원본 폴더를 _private\백업 아래로 "복사만" 합니다.
rem   브라우저 폴더는 읽기만 합니다. 아무것도 지우거나 고치지 않습니다.
rem   실제 작업은 같은 폴더의 브라우저백업_작업.ps1 이 합니다.
rem   옵션: -OutRoot "저장폴더"  -NoExplorer  -NoPause
rem  * 공개 저장소이므로 이 파일에 비밀 정보를 절대 적지 마세요.
rem ================================================================
set "NOPAUSE="
if defined SJ_NOPAUSE set "NOPAUSE=1"
for %%A in (%*) do if /i "%%~A"=="-NoPause" set "NOPAUSE=1"
set "PSEXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PSEXE%" set "PSEXE=powershell"
"%PSEXE%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0브라우저백업_작업.ps1" %*
set "RC=%ERRORLEVEL%"
if not defined NOPAUSE pause
endlocal & exit /b %RC%
