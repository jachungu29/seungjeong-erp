/* ===================================================================
   승정 ERP — DB(자체 호스팅 Supabase) 접속 설정 단일 원본
   모든 화면이 Supabase를 쓰기 전에 이 파일을 먼저 불러옵니다.
     <script src="_lib/sb-env.js"></script>   (폴더 화면은 <base href="../"> 덕분에 같은 경로)
   결과: window.SB_URL, window.SB_KEY, window.SB_ENV_SRC(설정 출처)

   ⚠ 공개 저장소입니다. 주소·키를 이 파일에 적지 마세요.
   설정 우선순위 (위가 이김)
     1) 화면이 이 파일보다 먼저 window.SB_URL/SB_KEY를 정한 경우
     2) 이 브라우저에 저장한 값 — 설계/db-setup.html 에서 입력(localStorage SJ_SB_URL / SJ_SB_KEY)
     3) _lib/sb-config.json (git 제외 파일. 각 PC·NAS 웹서버에만 둠)
          {"url":"http://<서버>:8000","key":"<anon key>"}
     4) 기본값: 이 화면을 연 서버의 8000번 포트(http일 때) → 아니면 http://localhost:8000
        (Docker Supabase 기본 포트. 키가 없으면 접속은 실패하고 화면은 로컬 모드로 동작)
   =================================================================== */
(function(){
  var src = 'page';
  function ls(k){ try{ return localStorage.getItem(k) || ''; }catch(e){ return ''; } }

  if(!window.SB_URL){
    var u = ls('SJ_SB_URL'), k = ls('SJ_SB_KEY');
    if(u){ window.SB_URL = u; window.SB_KEY = window.SB_KEY || k; src = 'browser'; }
  }

  if(!window.SB_URL){
    try{
      var me = document.currentScript && document.currentScript.src;
      var cfgUrl = me ? new URL('sb-config.json', me).href : '_lib/sb-config.json';
      var x = new XMLHttpRequest();
      x.open('GET', cfgUrl + '?t=' + Date.now(), false);   // 동기: 다음 스크립트보다 먼저 값이 있어야 함
      x.send(null);
      if(x.status === 200){
        var c = JSON.parse(x.responseText);
        if(c && c.url){ window.SB_URL = c.url; window.SB_KEY = window.SB_KEY || c.key || ''; src = 'file'; }
      }
    }catch(e){}
  }

  if(!window.SB_URL){
    var h = (location.protocol === 'http:' && location.hostname) ? location.hostname : 'localhost';
    window.SB_URL = 'http://' + h + ':8000';
    src = 'default';
  }

  window.SB_URL = String(window.SB_URL).replace(/\/+$/, '');
  window.SB_CONFIGURED = !!window.SB_KEY;
  if(!window.SB_KEY) window.SB_KEY = 'no-key';   // createClient가 빈 키에서 예외를 내지 않도록
  window.SB_ENV_SRC = src;
})();
