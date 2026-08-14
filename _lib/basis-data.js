/* ============================================================================
 * 승정 ERP · 기준정보(마스터 데이터) 단일 원본
 * 출처: 승정_전체양식_서식집_398종_v11.0_ERP설계.html 의 기준정보(BAS) 데이터
 * 용도: 기준정보 불러오기 페이지(기준정보/승정_기준정보_불러오기.html)에서 사용
 * 원칙: "항목이 일치하는 마스터는 현재 화면(양식)에 그대로 채워 넣는다."
 *  - apply:true  → 현재 ERP 저장소(Supabase/localStorage)에 바로 불러올 수 있음
 *  - apply:false → 현재 대응 화면이 없거나 이미 더 상세한 데이터가 있어 미리보기·CSV만
 * ============================================================================ */
(function (root) {
  'use strict';

  /* 라인 코드 → 라인명 (품목/금형 비고 표기에 사용) */
  var LINE_NAME = {
    'LN-V': '수직사출', 'LN-H': '수평사출', 'LN-D': '이중사출',
    'LN-HM': '호스조립(수동)', 'LN-HA': '호스조립(자동)',
    'LN-BM': 'BODY 수동조립', 'LN-BA': 'BODY 자동조립',
    'LN-TC': '열코킹', 'LN-VS': '비전검사'
  };
  var CUST_NAME = { HMC: '현대자동차', KIA: '기아', MOB: '현대모비스', MND: 'HL만도' };

  /* ── 소스 원천 배열(서식집 그대로) ────────────────────────────────── */

  // 품번·품명·라인·고객·재질·단가·C/T·캐비티·분류(SF=반제품, FG=완제품)
  var S_ITEM = [
    ['SJ-VI-2601-001', 'HOSE BRACKET A', 'LN-V', 'MOB', 'PA66-GF30', 1180, 34, 2, 'SF'],
    ['SJ-VI-2601-002', 'HOSE BRACKET B', 'LN-V', 'HMC', 'PA66-GF30', 1460, 41, 1, 'SF'],
    ['SJ-VI-2601-003', 'CONNECTOR HOUSING', 'LN-V', 'KIA', 'PBT-GF20', 980, 29, 2, 'SF'],
    ['SJ-VI-2601-004', 'INSERT BRACKET C', 'LN-V', 'MOB', 'PA66-GF30', 1320, 37, 2, 'SF'],
    ['SJ-VI-2601-005', 'MOUNT BUSH', 'LN-V', 'MND', 'PA6-GF15', 760, 25, 4, 'SF'],
    ['SJ-HO-2602-011', 'CLAMP BODY', 'LN-H', 'HMC', 'POM', 420, 24, 4, 'SF'],
    ['SJ-HO-2602-012', 'DUCT COVER', 'LN-H', 'KIA', 'PP-TD20', 760, 38, 2, 'SF'],
    ['SJ-HO-2602-013', 'SENSOR BRACKET', 'LN-H', 'MND', 'PA6-GF15', 890, 31, 2, 'SF'],
    ['SJ-HO-2602-014', 'GROMMET CAP', 'LN-H', 'MOB', 'TPE', 350, 22, 4, 'SF'],
    ['SJ-HO-2602-015', 'PROTECTOR PLATE', 'LN-H', 'KIA', 'PP-TD20', 540, 28, 4, 'SF'],
    ['SJ-HO-2602-016', 'AIR GUIDE', 'LN-H', 'HMC', 'PP-TD20', 680, 33, 2, 'SF'],
    ['SJ-DB-2603-004', 'DUAL COVER', 'LN-D', 'HMC', 'ABS+TPE', 2340, 62, 1, 'SF'],
    ['SJ-DB-2603-005', 'SWITCH CAP', 'LN-D', 'MOB', 'PC+TPE', 2080, 55, 1, 'SF'],
    ['SJ-AS-2604-001', 'COOLING HOSE ASSY', 'LN-HM', 'MND', 'EPDM+PA', 3150, 52, 1, 'FG'],
    ['SJ-AS-2604-002', 'BRAKE HOSE ASSY', 'LN-HM', 'MND', 'EPDM', 3720, 58, 1, 'FG'],
    ['SJ-AS-2604-003', 'FUEL HOSE ASSY', 'LN-HA', 'MOB', 'EPDM+PA', 3480, 31, 1, 'FG'],
    ['SJ-AS-2604-004', 'WASHER HOSE ASSY', 'LN-HA', 'KIA', 'EPDM', 2760, 28, 1, 'FG'],
    ['SJ-BD-2605-001', 'BODY ASSY FRONT', 'LN-BM', 'KIA', 'ASSY', 5480, 74, 1, 'FG'],
    ['SJ-BD-2605-002', 'BODY ASSY REAR', 'LN-BM', 'MOB', 'ASSY', 5960, 80, 1, 'FG'],
    ['SJ-BD-2605-003', 'BODY ASSY SIDE-L', 'LN-BA', 'HMC', 'ASSY', 4820, 46, 1, 'FG'],
    ['SJ-BD-2605-004', 'BODY ASSY SIDE-R', 'LN-BA', 'HMC', 'ASSY', 4820, 46, 1, 'FG'],
    ['SJ-TC-2606-001', 'HEAT CAULK COVER', 'LN-TC', 'MOB', 'PP+ABS', 1980, 38, 1, 'FG'],
    ['SJ-TC-2606-002', 'HEAT CAULK BRACKET', 'LN-TC', 'MND', 'PA66+STL', 2240, 42, 1, 'FG']
  ];

  // 사번·성명·부서·직급·국적·입사일·권한·상태
  var S_EMP = [
    ['26-001', 'SOKHA CHAN', '생산부 · PRODUCTION', 'G1', '캄보디아', '2026-01-05', 'L1', '재직'],
    ['26-002', 'THIDA SOK', '생산부 · PRODUCTION', 'G1', '캄보디아', '2026-01-05', 'L1', '재직'],
    ['26-003', 'RATANA KEO', '생산부 · PRODUCTION', 'G1', '캄보디아', '2026-02-02', 'L1', '재직'],
    ['25-011', 'SOMSAK PHAN', '생산부 · PRODUCTION', 'G2', '태국', '2025-03-10', 'L1', '재직'],
    ['25-012', 'MALEE SRI', '생산부 · PRODUCTION', 'G1', '태국', '2025-03-10', 'L1', '재직'],
    ['25-021', 'NGUYEN VAN', '생산부 · PRODUCTION', 'G2', '베트남', '2025-05-02', 'L1', '재직'],
    ['25-022', 'TRAN THI', '품질 · QUALITY', 'G1', '베트남', '2025-05-02', 'L1', '재직'],
    ['25-031', 'KHAM VONG', '생산부 · PRODUCTION', 'G2', '라오스', '2025-06-15', 'L1', '재직'],
    ['24-008', 'BISHAL K.', '품질 · QUALITY', 'G1', '네팔', '2024-07-15', 'L1', '재직'],
    ['24-009', 'SUMAN RAI', '생산부 · PRODUCTION', 'G1', '네팔', '2024-07-15', 'L1', '재직'],
    ['24-011', 'JOSE REYES', '생산부 · PRODUCTION', 'G1', '필리핀', '2024-08-01', 'L1', '재직'],
    ['24-012', 'MARIA CRUZ', '생산부 · PRODUCTION', 'G1', '필리핀', '2024-08-01', 'L1', '재직'],
    ['23-005', 'LI WEI', '생산기술부 · PRODUCTION ENGINEERING', 'G3', '중국', '2023-04-03', 'L2', '재직'],
    ['23-006', 'ZHANG MIN', '생산부 · PRODUCTION', 'G2', '중국', '2023-04-03', 'L1', '재직'],
    ['23-012', 'AZIZ TOSH', '생산부 · PRODUCTION', 'G2', '우즈베키스탄', '2023-09-11', 'L1', '재직'],
    ['23-013', 'BEKZOD N.', '생산부 · PRODUCTION', 'G1', '우즈베키스탄', '2023-09-11', 'L1', '재직'],
    ['22-003', '반장 A', '생산부 · PRODUCTION', 'G4', '대한민국', '2022-06-20', 'L2', '재직'],
    ['22-004', '반장 B', '생산부 · PRODUCTION', 'G4', '대한민국', '2022-06-20', 'L2', '재직'],
    ['21-001', '생산팀장', '생산부 · PRODUCTION', 'G5', '대한민국', '2021-02-01', 'L3', '재직'],
    ['21-002', '품질팀장', '품질 · QUALITY', 'G5', '대한민국', '2021-02-01', 'L3', '재직'],
    ['20-001', '생산기술부장', '생산기술부 · PRODUCTION ENGINEERING', 'G6', '대한민국', '2020-03-02', 'L3', '재직'],
    ['20-002', '관리부장', '관리부', 'G6', '대한민국', '2020-03-02', 'L4', '재직'],
    ['19-001', '품질부장', '품질 · QUALITY', 'G6', '대한민국', '2019-05-06', 'L4', '재직'],
    ['15-001', '대표이사 · CEO', 'CEO 경영총괄', 'G8', '대한민국', '2015-01-02', 'L5', '재직']
  ];

  // 고객사 : 코드·고객사명·구분·주요납품품목·등급·상태
  var S_CUST = [
    ['HMC', '현대자동차', '완성차 · OEM', '브라켓 · 클립 · 덕트 · BODY SIDE', 'A', '거래중'],
    ['KIA', '기아', '완성차 · OEM', '하우징 · 커버 · BODY FRONT · 호스 ASSY', 'A', '거래중'],
    ['MOB', '현대모비스', '1차 · TIER 1', '브라켓 · 스위치캡 · BODY REAR · 열코킹품', 'A', '거래중'],
    ['MND', 'HL만도', '1차 · TIER 1', '센서브라켓 · 부시 · 냉각/브레이크 호스 ASSY', 'B', '거래중']
  ];

  // 협력사 : 코드·명·공급품목군·리드타임·등급·상태
  var S_SUPP = [
    ['SP-001', '대한폴리켐', '수지(PA66 · PA6)', '7일', 'A', '거래중'],
    ['SP-002', '한성플라스틱', '수지(PP · POM)', '5일', 'A', '거래중'],
    ['SP-003', '동양엘라스토머', 'TPE · EPDM', '10일', 'B', '거래중'],
    ['SP-004', '제일엔지니어링플라스틱', 'ABS · PC · PBT', '7일', 'A', '거래중'],
    ['SP-005', '정밀화스너', '인서트 너트 · 클램프', '5일', 'A', '거래중'],
    ['SP-006', '신흥호스', 'EPDM 호스', '12일', 'B', '거래중'],
    ['SP-007', '대동스틸', '스틸 브라켓', '9일', 'B', '거래중'],
    ['SP-008', '명진라벨', '라벨 · 포장재', '3일', 'A', '거래중']
  ];

  // 외주처 : 코드·명·외주공정·사급구분·가공단가·상태
  var S_OUT = [
    ['OS-001', '대성도장', '도장 · PAINTING', '사급', '180 원/EA', '거래중'],
    ['OS-002', '한빛도금', '도금 · PLATING', '사급', '240 원/EA', '거래중'],
    ['OS-003', '정우열처리', '열처리 · HEAT TREATMENT', '유상', '95 원/EA', '거래중'],
    ['OS-004', '서진초음파', '초음파 융착 · ULTRASONIC WELDING', '사급', '130 원/EA', '거래중'],
    ['OS-005', '태진버제거', '후가공(버 제거) · DEBURRING', '사급', '60 원/EA', '거래중']
  ];

  // 금형 : 관리번호·금형명·적용품번·라인·한도쇼트·누적쇼트
  var S_MOLD = [
    ['MD-VI-018', 'HOSE BRACKET A 금형', 'SJ-VI-2601-001', 'LN-V', 600000, 412000],
    ['MD-VI-019', 'HOSE BRACKET B 금형', 'SJ-VI-2601-002', 'LN-V', 500000, 338000],
    ['MD-VI-020', 'CONNECTOR HOUSING 금형', 'SJ-VI-2601-003', 'LN-V', 600000, 521000],
    ['MD-VI-021', 'INSERT BRACKET C 금형', 'SJ-VI-2601-004', 'LN-V', 600000, 186000],
    ['MD-VI-022', 'MOUNT BUSH 4C', 'SJ-VI-2601-005', 'LN-V', 800000, 742000],
    ['MD-HO-031', 'CLAMP BODY 4C', 'SJ-HO-2602-011', 'LN-H', 800000, 694000],
    ['MD-HO-032', 'DUCT COVER 2C', 'SJ-HO-2602-012', 'LN-H', 600000, 246000],
    ['MD-HO-033', 'SENSOR BRACKET 2C', 'SJ-HO-2602-013', 'LN-H', 600000, 455000],
    ['MD-HO-034', 'GROMMET CAP 4C', 'SJ-HO-2602-014', 'LN-H', 800000, 762000],
    ['MD-HO-035', 'PROTECTOR PLATE 4C', 'SJ-HO-2602-015', 'LN-H', 800000, 318000],
    ['MD-HO-036', 'AIR GUIDE 2C', 'SJ-HO-2602-016', 'LN-H', 600000, 129000],
    ['MD-DB-041', 'DUAL COVER 2중', 'SJ-DB-2603-004', 'LN-D', 400000, 287000],
    ['MD-DB-042', 'SWITCH CAP 2중', 'SJ-DB-2603-005', 'LN-D', 400000, 198000],
    ['JG-HM-051', '냉각호스 압입지그', 'SJ-AS-2604-001', 'LN-HM', 300000, 214000],
    ['JG-HM-052', '브레이크호스 압입지그', 'SJ-AS-2604-002', 'LN-HM', 300000, 167000],
    ['JG-HA-053', '자동호스조립 지그', 'SJ-AS-2604-003', 'LN-HA', 400000, 238000],
    ['JG-BM-061', 'BODY 수동조립 지그', 'SJ-BD-2605-001', 'LN-BM', 250000, 142000],
    ['JG-BA-062', 'BODY 자동조립 지그', 'SJ-BD-2605-003', 'LN-BA', 400000, 205000],
    ['JG-TC-071', '열코킹 지그', 'SJ-TC-2606-001', 'LN-TC', 300000, 268000]
  ];

  // 자재 : 코드·명·단위·단가·안전재고·기초재고
  var S_MAT = [
    ['RM-PA66', 'PA66-GF30', 'kg', 4200, 3000, 4850], ['RM-PBT', 'PBT-GF20', 'kg', 3800, 2000, 2260],
    ['RM-POM', 'POM', 'kg', 3300, 2500, 1980], ['RM-PP', 'PP-TD20', 'kg', 2100, 3000, 5120],
    ['RM-PA6', 'PA6-GF15', 'kg', 3600, 2000, 2740], ['RM-TPE', 'TPE', 'kg', 5400, 1500, 1180],
    ['RM-ABS', 'ABS', 'kg', 2900, 1500, 2050], ['RM-PC', 'PC', 'kg', 6100, 1000, 860],
    ['RM-PPAB', 'PP+ABS', 'kg', 2600, 1500, 2380],
    ['SM-INS', '인서트 너트', 'EA', 95, 50000, 78000], ['SM-HOSE', 'EPDM 호스', 'M', 780, 8000, 6400],
    ['SM-CLMP', '클램프', 'EA', 210, 20000, 31500], ['SM-STL', '스틸 브라켓', 'EA', 430, 10000, 12800],
    ['SM-LBL', '라벨', 'EA', 38, 30000, 44000]
  ];

  // 불량코드 : 계열·적용라인/공정·코드·불량유형·판정구분·처리방법
  var S_DEFECT = [
    ['V', '수직사출 (LN-V)', 'V01', '미성형 · SHORT SHOT', '폐기', '재발 방지 조건 재설정'],
    ['V', '수직사출 (LN-V)', 'V02', '웰드라인 · WELD LINE', '재작업', '게이트 위치·수지온 조정'],
    ['V', '수직사출 (LN-V)', 'V03', '버(Burr) · BURR', '재작업', '형체력·파팅면 점검'],
    ['V', '수직사출 (LN-V)', 'V04', '기포·보이드 · VOID', '폐기', '건조 조건·보압 조정'],
    ['V', '수직사출 (LN-V)', 'V05', '변색·탄화 · DISCOLORATION', '폐기', '실린더 퍼징·체류시간 단축'],
    ['V', '수직사출 (LN-V)', 'V06', '인서트 이탈 · INSERT MISSING', '폐기', '인서트 지그 점검'],
    ['H', '수평사출 (LN-H)', 'H01', '미성형 · SHORT SHOT', '폐기', '사출압·계량 재설정'],
    ['H', '수평사출 (LN-H)', 'H02', '실버스트릭 · SILVER STREAK', '폐기', '수지 건조 재실시'],
    ['H', '수평사출 (LN-H)', 'H03', '크랙·파손 · CRACK', '폐기', '취출 조건·이젝터 점검'],
    ['H', '수평사출 (LN-H)', 'H04', '수축(싱크) · SINK MARK', '재작업', '보압·냉각시간 조정'],
    ['H', '수평사출 (LN-H)', 'H05', '이물혼입 · CONTAMINATION', '폐기', '호퍼·주변 청소'],
    ['H', '수평사출 (LN-H)', 'H06', '게이트 불량 · GATE DEFECT', '재작업', '게이트 컷 지그 점검'],
    ['A', '조립 (LN-HA · LN-BA)', 'A01', '부품 누락 · PART MISSING', '재작업', '포카요케 확인'],
    ['A', '조립 (LN-HA · LN-BA)', 'A02', '압입 불량 · PRESS-FIT NG', '재작업', '압입력·지그 점검'],
    ['A', '조립 (LN-HA · LN-BA)', 'A03', '호스 삽입 불량 · HOSE INSERT NG', '재작업', '삽입 깊이 게이지 확인'],
    ['A', '조립 (LN-HA · LN-BA)', 'A04', '외관 스크래치 · SCRATCH', '재작업', '취급·포장 방법 개선'],
    ['A', '조립 (LN-HA · LN-BA)', 'A05', '체결토크 부족 · LOW TORQUE', '재작업', '토크렌치 교정 확인'],
    ['A', '조립 (LN-HA · LN-BA)', 'A06', '라벨 오부착 · WRONG LABEL', '재작업', '라벨 발행 연동 확인']
  ];

  // 비가동 코드 : 코드·비가동명·귀책부서·손실구분
  var S_DOWNTIME = [
    ['DT01', '설비 고장 · M/C BREAKDOWN', '설비관리팀', '고장 정지'],
    ['DT02', '금형 고장 · MOLD BREAKDOWN', '금형팀', '고장 정지'],
    ['DT03', '금형 교체 · MOLD CHANGE', '금형팀', '작업 준비'],
    ['DT04', '재료 교체 · MATERIAL CHANGE', '생산운영팀', '작업 준비'],
    ['DT05', '색상 교체(퍼징) · COLOR CHANGE', '생산운영팀', '작업 준비'],
    ['DT06', '품질 조정(초품 대기) · QUALITY ADJUST', '품질관리팀', '작업 준비'],
    ['DT07', '자재 결품 · MATERIAL SHORTAGE', '구매관리', '비가동 손실'],
    ['DT08', '작업 대기 · WAITING', '생산관리팀', '비가동 손실'],
    ['DT09', '작업 준비(셋업) · SET-UP', '생산운영팀', '작업 준비'],
    ['DT10', '계획 정지(TPM) · PLANNED STOP', '설비관리팀', '계획 정지'],
    ['DT11', '청소 · 3정5S · CLEANING · 5S', '생산운영팀', '계획 정지'],
    ['DT12', '교육 · 회의 · TRAINING · MEETING', '인사관리', '계획 정지'],
    ['DT13', '검사 대기 · INSPECTION WAIT', '품질관리팀', '비가동 손실'],
    ['DT14', '금형 수리 · MOLD REPAIR', '금형팀', '고장 정지'],
    ['DT15', '유틸리티 이상 · UTILITY FAILURE', '설비관리팀', '고장 정지'],
    ['DT16', '기타 · ETC', '생산부', '비가동 손실'],
    ['ET01', '정전 · 비상 정지 · POWER FAILURE', '공장관리팀', '외부 요인']
  ];

  // 라인 · 공정 : 코드·라인명·구분·표준C/T(초)·캐비티
  var S_LINE = [
    ['LN-V', '수직사출 · VERTICAL INJECTION', '사출', 34, 2],
    ['LN-H', '수평사출 · HORIZONTAL INJECTION', '사출', 26, 4],
    ['LN-D', '이중사출 · DUAL INJECTION', '사출', 62, 1],
    ['LN-HM', '호스조립(수동) · HOSE ASSY (MANUAL)', '조립', 52, 1],
    ['LN-HA', '호스조립(자동) · HOSE ASSY (AUTO)', '조립', 31, 1],
    ['LN-BM', 'BODY 수동조립 · BODY ASSY (MANUAL)', '조립', 74, 1],
    ['LN-BA', 'BODY 자동조립 · BODY ASSY (AUTO)', '조립', 46, 1],
    ['LN-TC', '열코킹 · HEAT CAULKING', '후공정', 38, 1],
    ['LN-VS', '비전검사 · VISION INSPECTION', '검사', 12, 1]
  ];

  // 창고 : 코드·창고명·보관품목·용량·상태
  var S_WH = [
    ['WH-RM', '원자재 창고 · RAW MATERIAL W/H', '원자재 · 부자재', '48', '사용'],
    ['WH-SF', '반제품 창고 · SEMI-FINISHED W/H', '반제품(사출품)', '36', '사용'],
    ['WH-FG', '완제품 창고 · FINISHED GOODS W/H', '완제품 · FINISHED GOODS', '60', '사용'],
    ['WH-NG', '부적합품 격리구역 · NONCONFORMING', '보류 · 부적합 · HOLD', '12', '사용'],
    ['WH-MD', '금형 · 예비품 창고 · MOLD · SPARE W/H', '금형 · 스페어', '24', '사용'],
    ['WH-OS', '외주 대기장 · OUTSOURCING YARD', '사급 · 외주 입출', '10', '사용']
  ];

  // 계측기 : 관리번호·계측기명·모델·교정주기·차기교정일·통신·상태
  var S_GAUGE = [
    ['MI-001', '디지털 캘리퍼스 0-150', 'Mitutoyo CD-15AX', '연 1회', '2027-01-20', '블루투스', '사용'],
    ['MI-002', '디지털 캘리퍼스 0-200', 'Mitutoyo CD-20AX', '연 1회', '2027-02-10', '블루투스', '사용'],
    ['MI-003', '마이크로미터 0-25', 'Mitutoyo MDC-25MX', '연 1회', '2027-03-05', '―', '사용'],
    ['MI-004', '하이트게이지 0-300', 'Mitutoyo HD-30AX', '연 1회', '2027-03-18', '―', '사용'],
    ['TN-001', '디지털 토크렌치 5-25N·m', 'Tohnichi CEM3-G', '연 1회', '2027-01-15', '블루투스', '사용'],
    ['TN-002', '디지털 토크렌치 10-50N·m', 'Tohnichi CEM10-G', '연 1회', '2027-04-02', '블루투스', '사용'],
    ['SC-001', '전자저울 0-3kg', 'A&D EK-3000i', '연 1회', '2027-02-28', '―', '사용'],
    ['TH-001', '표면온도계(열코킹)', 'Testo 905-T2', '연 1회', '2027-05-11', '―', '사용']
  ];

  /* ── 현재 ERP 화면(양식) 스키마로 매핑 ───────────────────────────── */

  function catOf(cls) { return cls === 'FG' ? '완제품' : (cls === 'SF' ? '반제품' : '부품'); }

  // 품목마스터(item_master) : pno·name·cat·spec·mat·price·unit·sup·remark
  var itemRows = S_ITEM.map(function (x) {
    return {
      pno: x[0], name: x[1], cat: catOf(x[8]), spec: x[7] + 'C',
      mat: x[4], price: String(x[5]), unit: 'EA', sup: '자사생산',
      remark: '고객:' + (CUST_NAME[x[3]] || x[3]) + ' / 라인:' + (LINE_NAME[x[2]] || x[2]) + ' / C/T ' + x[6] + '초'
    };
  });

  // 사원마스터(emp_master_v1) : {mgr, wrk, day, quit}
  var empMgr = [], empWrk = [];
  S_EMP.forEach(function (e) {
    var isMgr = /G[5-8]/.test(e[3]) || /팀장|부장|이사|대표/.test(e[1]);
    if (isMgr) {
      empMgr.push({ no: e[0], name: e[1], dept: e[2], rank: e[3], hire: e[5], duty: '', tel: '', status: e[7], memo: '국적:' + e[4] + ' / 권한:' + e[6] });
    } else {
      empWrk.push({ no: e[0], name: e[1], skills: [], shift: '주간', hire: e[5], status: e[7], memo: e[2] + ' / ' + e[3] + ' / 국적:' + e[4] });
    }
  });
  var empValue = { mgr: empMgr, wrk: empWrk, day: [], quit: [] };

  // 고객사(SJ_CUST) : {code,name,kind,biz,ceo,contact,dept,tel,mobile,email,addr,pay,credit,status,note}
  function party(code, name, kind, status, note) {
    return { code: code, name: name, kind: kind, biz: '', ceo: '', contact: '', dept: '', tel: '', mobile: '', email: '', addr: '', pay: '', credit: '', status: status, note: note };
  }
  var custRows = S_CUST.map(function (x) {
    return party(x[0], x[1], '매출처', x[5] === '거래중' ? '활성' : x[5], x[2] + ' / 납품:' + x[3] + ' / 등급 ' + x[4]);
  });

  // 협력사 + 외주처(SJ_SUPP)
  var suppRows = S_SUPP.map(function (x) {
    return party(x[0], x[1], '공급사', x[5] === '거래중' ? '활성' : x[5], x[2] + ' / 리드타임 ' + x[3] + ' / 등급 ' + x[4]);
  }).concat(S_OUT.map(function (x) {
    return party(x[0], x[1], '외주', x[5] === '거래중' ? '활성' : x[5], x[2] + ' / ' + x[3] + ' / ' + x[4]);
  }));

  // 금형(SJ_MOLDNO) : {no,name,cav,equip,maker,date,shot,status,remark}
  var itemCav = {}; S_ITEM.forEach(function (x) { itemCav[x[0]] = x[7]; });
  var moldRows = S_MOLD.map(function (m) {
    return {
      no: m[0], name: m[1], cav: (itemCav[m[2]] || '') + (itemCav[m[2]] ? 'C' : ''),
      equip: LINE_NAME[m[3]] || m[3], maker: '', date: '',
      shot: (m[4] || 0).toLocaleString(), status: '사용',
      remark: '적용품번:' + m[2] + ' / 누적쇼트 ' + (m[5] || 0).toLocaleString()
    };
  });

  /* ── 마스터 카탈로그(불러오기 페이지가 이 목록을 그린다) ─────────── */
  var MASTERS = [
    {
      id: 'item', title: '품목(품번) 마스터', icon: '📦',
      storage: 'supabase-table', table: 'item_master', apply: true,
      cols: ['pno', 'name', 'cat', 'spec', 'mat', 'price', 'unit', 'sup', 'remark'],
      colLabels: ['품번', '품명', '구분', '규격', '재질', '단가', '단위', '공급처', '비고'],
      screen: '생산/itemmaster.html', rows: itemRows,
      note: '현재 품목마스터(Supabase item_master)에 그대로 불러옵니다.'
    },
    {
      id: 'emp', title: '사원 마스터', icon: '👤',
      storage: 'app_state', key: 'emp_master_v1', apply: true,
      value: empValue, screen: '인사/사원마스터.html',
      preview: empMgr.concat(empWrk),
      cols: ['no', 'name', 'dept', 'rank', 'hire', 'status', 'memo'],
      colLabels: ['사번', '성명', '부서', '직급', '입사일', '상태', '비고'],
      note: '관리직 ' + empMgr.length + '명 + 생산직 ' + empWrk.length + '명. 사원마스터(클라우드 emp_master_v1)에 불러옵니다.'
    },
    {
      id: 'cust', title: '고객사 마스터', icon: '🏢',
      storage: 'localStorage', key: 'SJ_CUST', apply: true,
      cols: ['code', 'name', 'kind', 'status', 'note'],
      colLabels: ['코드', '고객사명', '구분', '상태', '비고'],
      screen: 'legacy.html · 거래처(고객사)', rows: custRows,
      note: '현재 고객사 목록(SJ_CUST)을 교체합니다. 기존 데이터는 자동 백업됩니다.'
    },
    {
      id: 'supp', title: '협력사 · 외주처 마스터', icon: '🤝',
      storage: 'localStorage', key: 'SJ_SUPP', apply: true,
      cols: ['code', 'name', 'kind', 'status', 'note'],
      colLabels: ['코드', '거래처명', '구분', '상태', '비고'],
      screen: 'legacy.html · 공급사', rows: suppRows,
      note: '협력사 8 + 외주처 5 = 13곳. 현재 공급사 목록(SJ_SUPP)을 교체합니다. 기존 데이터는 자동 백업됩니다.'
    },
    {
      id: 'mold', title: '금형 · 지그 마스터', icon: '🧩',
      storage: 'localStorage', key: 'SJ_MOLDNO', apply: true,
      cols: ['no', 'name', 'cav', 'equip', 'shot', 'status', 'remark'],
      colLabels: ['관리번호', '금형명', '캐비티', '설비/라인', '한도쇼트', '상태', '비고'],
      screen: 'legacy.html · 금형관리', rows: moldRows,
      note: '금형 13 + 지그 6 = 19개. 현재 금형번호 목록(SJ_MOLDNO)을 교체합니다. 기존 데이터는 자동 백업됩니다.'
    },
    /* ── 아래는 현재 대응 화면이 없거나(라인/자재/불량/비가동/창고),
          이미 더 상세한 데이터가 있어(설비/계측기) 미리보기·CSV만 제공 ── */
    {
      id: 'line', title: '라인 · 공정', icon: '🏭', storage: 'reference', apply: false,
      cols: ['code', 'name', 'kind', 'ct', 'cav'],
      colLabels: ['코드', '라인명', '구분', '표준C/T(초)', '캐비티'],
      rows: S_LINE.map(function (x) { return { code: x[0], name: x[1], kind: x[2], ct: x[3], cav: x[4] }; }),
      note: '참고용 · 현재 ERP는 라인을 화면 로직에 내장. 미리보기·CSV 내보내기만.'
    },
    {
      id: 'mat', title: '자재 마스터', icon: '🧱', storage: 'reference', apply: false,
      cols: ['code', 'name', 'unit', 'price', 'safe', 'stock'],
      colLabels: ['코드', '자재명', '단위', '단가', '안전재고', '기초재고'],
      rows: S_MAT.map(function (x) { return { code: x[0], name: x[1], unit: x[2], price: x[3], safe: x[4], stock: x[5] }; }),
      note: '참고용 · 현재 원자재는 legacy 별도 구조(SJ_RAW). 미리보기·CSV 내보내기만.'
    },
    {
      id: 'defect', title: '불량코드', icon: '⚠️', storage: 'reference', apply: false,
      cols: ['series', 'line', 'code', 'type', 'judge', 'action'],
      colLabels: ['계열', '적용라인/공정', '코드', '불량유형', '판정', '처리방법'],
      rows: S_DEFECT.map(function (x) { return { series: x[0], line: x[1], code: x[2], type: x[3], judge: x[4], action: x[5] }; }),
      note: '참고용 · 불량코드는 화면 로직 내장. 미리보기·CSV 내보내기만.'
    },
    {
      id: 'downtime', title: '비가동 코드', icon: '⏸️', storage: 'reference', apply: false,
      cols: ['code', 'name', 'dept', 'loss'],
      colLabels: ['코드', '비가동명', '귀책부서', '손실구분'],
      rows: S_DOWNTIME.map(function (x) { return { code: x[0], name: x[1], dept: x[2], loss: x[3] }; }),
      note: '참고용 · 미리보기·CSV 내보내기만.'
    },
    {
      id: 'warehouse', title: '창고 마스터', icon: '🏬', storage: 'reference', apply: false,
      cols: ['code', 'name', 'keep', 'cap', 'status'],
      colLabels: ['코드', '창고명', '보관품목', '용량', '상태'],
      rows: S_WH.map(function (x) { return { code: x[0], name: x[1], keep: x[2], cap: x[3], status: x[4] }; }),
      note: '참고용 · 미리보기·CSV 내보내기만.'
    },
    {
      id: 'gauge', title: '계측기 마스터', icon: '📏', storage: 'reference', apply: false, warn: true,
      cols: ['id', 'name', 'model', 'cyc', 'next', 'comm', 'status'],
      colLabels: ['관리번호', '계측기명', '모델', '교정주기', '차기교정일', '통신', '상태'],
      rows: S_GAUGE.map(function (x) { return { id: x[0], name: x[1], model: x[2], cyc: x[3], next: x[4], comm: x[5], status: x[6] }; }),
      note: '⚠️ 현재 ERP에는 이미 계측기 47대(교정이력 포함)가 있습니다. 소스는 8대뿐이라 덮으면 손해 → 미리보기·CSV만.'
    },
    {
      id: 'eqp', title: '설비 마스터', icon: '⚙️', storage: 'reference', apply: false, warn: true,
      cols: ['note'], colLabels: ['안내'],
      rows: [{ note: '현재 ERP 설비(EQREG)는 상세 사양·PM·수리이력까지 보유. 소스보다 상세하므로 교체하지 않습니다.' }],
      note: '⚠️ 현재 데이터가 더 상세 → 교체 제외(안전).'
    }
  ];

  root.SJ_BASIS = {
    source: '승정_전체양식_서식집_398종_v11.0_ERP설계.html',
    generatedNote: '기준정보 단일 원본 · 불러오기 페이지 전용',
    supabaseUrl: 'https://gyasbmiordkxcfpwgvio.supabase.co',
    supabaseKey: 'sb_publishable_oMdTYbr11auTzSaYwY9Jew_qbKO3SbF',
    masters: MASTERS
  };
})(window);
