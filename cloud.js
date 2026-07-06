/* ===================================================================
   승정 ERP — Supabase 공통 클라이언트 + app_state(key/value) 동기화
   기존 데이터 형식을 "그대로" 저장/불러오기 → index2 등 표시 구조 불변.
   사용: <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
         <script src="cloud.js"></script>
     · Cloud.get(key) → Promise(value|null)
     · Cloud.set(key, value)
     · Cloud.on(key, cb)  // 다른 PC 변경 실시간(자기 변경 무시)
   =================================================================== */
(function(){
  window.SB_URL = window.SB_URL || "https://gyasbmiordkxcfpwgvio.supabase.co";
  window.SB_KEY = window.SB_KEY || "sb_publishable_oMdTYbr11auTzSaYwY9Jew_qbKO3SbF";
  if(!window.__CID) window.__CID = 'c'+Math.random().toString(36).slice(2,9);
  try{
    if(window.supabase && window.supabase.createClient && !window.SB){
      window.SB = window.supabase.createClient(window.SB_URL, window.SB_KEY);
    }
  }catch(e){ console.warn('[Cloud] init 실패', e); }

  window.Cloud = {
    ok:function(){ return !!window.SB; },
    get:function(key){
      if(!window.SB) return Promise.resolve(null);
      return window.SB.from('app_state').select('value').eq('key',key).maybeSingle()
        .then(function(r){ return (r && r.data) ? r.data.value : null; })
        .catch(function(){ return null; });
    },
    set:function(key,value){
      if(!window.SB) return Promise.resolve();
      return window.SB.from('app_state')
        .upsert({key:key, value:value, src:window.__CID, updated_at:new Date().toISOString()})
        .then(function(r){ if(r && r.error) console.warn('[Cloud] 저장 실패', r.error.message); })
        .catch(function(){});
    },
    on:function(key,cb){
      if(!window.SB) return;
      try{
        window.SB.channel('app_'+key)
          .on('postgres_changes',
            {event:'*', schema:'public', table:'app_state', filter:'key=eq.'+key},
            function(p){ var row=(p && p.new)||{}; if(row.src===window.__CID) return; cb(row.value); })
          .subscribe();
      }catch(e){}
    }
  };
})();
