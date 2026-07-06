/* ===================================================================
   승정 ERP — Supabase 공통 클라이언트 + app_state(key/value) 동기화
   ★ 준비확인(probe): app_state 테이블이 있어야만 클라우드로 동작.
     테이블이 없으면(= supabase-setup.sql 미실행) → "같은 PC(로컬)" 모드로만 동작
     (불필요한 클라우드 요청/에러 없음). SQL 실행 후 다음 접속부터 자동 공유.
   사용: <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
         <script src="cloud.js"></script>
     · Cloud.get(key) → Promise(value|null)   (미준비면 null → 로컬 폴백)
     · Cloud.set(key, value)                    (미준비면 무시 → 로컬만 저장)
     · Cloud.on(key, cb)                        (미준비면 구독 안 함)
     · Cloud.ready → Promise(true|false)        (클라우드 활성 여부)
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
    /* app_state 존재 확인 — 있으면 클라우드 활성, 없으면 로컬 모드 */
    sb.from('app_state').select('key').limit(1)
      .then(function(r){
        active = !(r && r.error);
        if(active) console.log('[Cloud] 클라우드 공유 활성 (집·사무실 실시간)');
        else console.log('[Cloud] app_state 없음 → 같은 PC(로컬)로만 동작. Supabase에서 supabase-setup.sql 실행 시 공유가 켜집니다.');
        resolveReady(active);
      })
      .catch(function(){ active=false; resolveReady(false); });
  } else {
    console.log('[Cloud] Supabase 라이브러리 없음 → 로컬 모드');
    resolveReady(false);
  }

  window.Cloud = {
    ok:function(){ return active; },
    ready:ready,
    get:function(key){
      if(!sb) return Promise.resolve(null);
      return ready.then(function(a){
        if(!a) return null;
        return sb.from('app_state').select('value').eq('key',key).maybeSingle()
          .then(function(r){ return (r && r.data) ? r.data.value : null; })
          .catch(function(){ return null; });
      });
    },
    set:function(key,value){
      if(!sb) return Promise.resolve();
      return ready.then(function(a){
        if(!a) return;   // 미준비(테이블 없음) → 클라우드 저장 안 함(로컬만)
        return sb.from('app_state')
          .upsert({key:key, value:value, src:window.__CID, updated_at:new Date().toISOString()})
          .then(function(r){ if(r && r.error) console.warn('[Cloud] 저장 실패', r.error.message); })
          .catch(function(){});
      });
    },
    on:function(key,cb){
      if(!sb) return;
      ready.then(function(a){
        if(!a) return;   // 미준비 → 실시간 구독 안 함
        try{
          sb.channel('app_'+key)
            .on('postgres_changes',
              {event:'*', schema:'public', table:'app_state', filter:'key=eq.'+key},
              function(p){ var row=(p && p.new)||{}; if(row.src===window.__CID) return; cb(row.value); })
            .subscribe();
        }catch(e){}
      });
    }
  };
})();
