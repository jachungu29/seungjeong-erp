/* ===================================================================
   승정 ERP — Supabase 공통 클라이언트 + app_state(key/value) 동기화
   ★ 준비확인(probe): app_state 테이블이 있어야만 클라우드로 동작.
     없으면(=SQL 미실행) "같은 PC(로컬)" 모드로만 동작(에러 없음).
   사용: <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
         <script src="_lib/cloud.js"></script>
     · Cloud.get(key) → Promise(value|null)
     · Cloud.set(key, value)
     · Cloud.on(key, cb)
     · Cloud.ready → Promise(true|false)
   =================================================================== */
(function(){
  window.SB_URL = window.SB_URL || "https://gyasbmiordkxcfpwgvio.supabase.co";
  window.SB_KEY = window.SB_KEY || "sb_publishable_oMdTYbr11auTzSaYwY9Jew_qbKO3SbF";
  if(!window.__CID) window.__CID = 'c'+Math.random().toString(36).slice(2,9);

  var sb=null;
  try{ if(window.supabase && window.supabase.createClient){ sb=window.supabase.createClient(window.SB_URL, window.SB_KEY); window.SB=sb; } }catch(e){}

  var active=false, resolveReady;
  var ready=new Promise(function(r){ resolveReady=r; });

  if(sb){
    sb.from('app_state').select('key').limit(1)
      .then(function(r){
        active = !(r && r.error);
        console.log(active?'[Cloud] 클라우드 공유 활성':'[Cloud] app_state 없음 → 로컬 모드. supabase-setup.sql 실행 시 공유 켜짐');
        resolveReady(active);
      })
      .catch(function(){ active=false; resolveReady(false); });
  } else { console.log('[Cloud] Supabase 라이브러리 없음 → 로컬 모드'); resolveReady(false); }

  window.Cloud = {
    ok:function(){ return active; },
    ready:ready,
    get:function(key){
      if(!sb) return Promise.resolve(null);
      return ready.then(function(a){ if(!a) return null;
        return sb.from('app_state').select('value').eq('key',key).maybeSingle()
          .then(function(r){ return (r && r.data) ? r.data.value : null; }).catch(function(){ return null; }); });
    },
    set:function(key,value){
      if(!sb) return Promise.resolve();
      return ready.then(function(a){ if(!a) return;
        return sb.from('app_state').upsert({key:key, value:value, src:window.__CID, updated_at:new Date().toISOString()})
          .then(function(r){ if(r && r.error) console.warn('[Cloud] 저장 실패', r.error.message); }).catch(function(){}); });
    },
    on:function(key,cb){
      if(!sb) return;
      ready.then(function(a){ if(!a) return;
        try{ sb.channel('app_'+key).on('postgres_changes',
              {event:'*', schema:'public', table:'app_state', filter:'key=eq.'+key},
              function(p){ var row=(p && p.new)||{}; if(row.src===window.__CID) return; cb(row.value); }).subscribe();
        }catch(e){} });
    }
  };
})();
