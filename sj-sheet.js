/* ============================================================
   sj-sheet.js — 승정 ERP 공통 표 도구 (검색 + CSV 내보내기)
   ★ 이 파일 하나만 고치면 이걸 포함한 모든 화면의 검색/CSV 형식이 함께 바뀝니다.
   사용법: 화면 <body> 끝에 <script src="sj-sheet.js"></script> 한 줄만 추가.
     - 화면의 '가장 큰 표' 위에 [🔍 전체검색] [📄 CSV] 툴바를 자동으로 붙입니다.
     - 표를 다시 그려도(비동기 로드) 검색·CSV는 그 시점의 행에 실시간 적용됩니다.
     - 제외: data-nosheet="1" 가 붙은 표, 또는 이미 자체 필터가 있는 화면(예: 수주관리)은
       body 에 data-sjsheet-off 를 두면 건너뜁니다.
   ============================================================ */
(function(){
 function ready(fn){ if(document.readyState!=='loading') setTimeout(fn,0); else document.addEventListener('DOMContentLoaded',fn); }
 function rowText(r){ var t=r.textContent||''; var f=r.querySelectorAll('input,select,textarea'); for(var i=0;i<f.length;i++){ t+=' '+(f[i].value||''); } return t.toLowerCase(); }
 function cellVal(c){ var e=c.querySelector('input,select,textarea'); var v=e?(e.value!=null?e.value:(e.textContent||'')):(c.textContent||''); v=(''+v).replace(/\s+/g,' ').trim(); return /[",\n]/.test(v)?('"'+v.replace(/"/g,'""')+'"'):v; }
 function csvRow(r){ return [].map.call(r.cells,cellVal).join(','); }
 ready(function(){
  try{
   if(document.body.hasAttribute('data-sjsheet-off')) return;
   var tables=[].slice.call(document.querySelectorAll('table')).filter(function(t){ return !t.hasAttribute('data-nosheet'); });
   if(!tables.length) return;
   /* 데이터가 담기는 '가장 큰 표'(열 수 기준) 선택 */
   tables.sort(function(a,b){ var ca=(a.rows[0]?a.rows[0].cells.length:0), cb=(b.rows[0]?b.rows[0].cells.length:0); return cb-ca; });
   var tbl=tables[0];
   if(tbl.dataset.sjsheet) return; tbl.dataset.sjsheet='1';

   var bar=document.createElement('div');
   bar.className='sj-sheet-bar';
   bar.style.cssText='display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:10px 0;font-family:inherit';
   bar.innerHTML=
     '<span style="font-size:12px;color:#64748b;font-weight:700">🔎 조회</span>'+
     '<input class="sjq" placeholder="전체 검색 (거래처·품번·품명 등)" style="flex:1;min-width:170px;padding:7px 11px;border:1px solid #cbd5e1;border-radius:8px;font:inherit;font-size:13px;background:#fff;color:#1c2430">'+
     '<button type="button" class="sjrst" style="padding:7px 12px;border:1px solid #cbd5e1;background:#fff;color:#334155;border-radius:8px;font:inherit;font-size:12.5px;cursor:pointer">초기화</button>'+
     '<button type="button" class="sjcsv" style="padding:7px 13px;border:1px solid #9ccbb4;background:#fff;color:#0d7a52;border-radius:8px;font:inherit;font-size:12.5px;font-weight:700;cursor:pointer">📄 CSV 내보내기</button>'+
     '<span class="sjcnt" style="margin-left:auto;font-size:12px;color:#64748b"></span>';
   tbl.parentNode.insertBefore(bar, tbl);
   var q=bar.querySelector('.sjq'), cnt=bar.querySelector('.sjcnt');

   function body(){ return tbl.tBodies&&tbl.tBodies[0] ? tbl.tBodies[0] : tbl; }
   function apply(){
    var s=(q.value||'').toLowerCase().trim(), shown=0, total=0, rows=body().rows;
    for(var i=0;i<rows.length;i++){ var r=rows[i];
      /* 합계/빈줄 행은 검색에서 제외(항상 표시) */
      if(r.className && /total|합계|empty/.test(r.className)){ r.style.display=''; continue; }
      total++; var ok=!s||rowText(r).indexOf(s)>=0; r.style.display=ok?'':'none'; if(ok)shown++;
    }
    cnt.textContent=s?('표시 '+shown+' / '+total):'';
   }
   q.addEventListener('input',apply);
   bar.querySelector('.sjrst').addEventListener('click',function(){ q.value=''; apply(); q.focus(); });
   bar.querySelector('.sjcsv').addEventListener('click',function(){
    var out=[]; var head = tbl.tHead ? tbl.tHead.rows[0] : (tbl.rows[0]||null);
    if(head) out.push([].map.call(head.cells,function(c){ return cellVal(c); }).join(','));
    var rows=body().rows;
    for(var i=0;i<rows.length;i++){ var r=rows[i]; if(r.style.display==='none')continue; if(head&&r===head)continue; out.push(csvRow(r)); }
    var name=(document.title||'export').split('·')[0].replace(/[^\w가-힣]+/g,'_').replace(/^_+|_+$/g,'')||'export';
    var blob=new Blob(['﻿'+out.join('\r\n')],{type:'text/csv;charset=utf-8'});
    var a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name+'.csv'; document.body.appendChild(a); a.click(); a.remove();
   });
  }catch(e){ /* 조용히 무시 — 화면 기능에 영향 없음 */ }
 });
})();
