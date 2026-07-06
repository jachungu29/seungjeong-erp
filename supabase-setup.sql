-- ===================================================================
-- 승정 ERP — Supabase 테이블 설정 (한 번만 실행)
-- Supabase 대시보드 → SQL Editor → New query → 붙여넣고 Run.
-- ===================================================================

-- [A] 구조도 등 공용 상태 (key/value · 형식 그대로 JSONB 저장)
create table if not exists app_state (
  key        text primary key,   -- 예: 'map_struct'
  value      jsonb,
  src        text,
  updated_at timestamptz default now()
);
alter table app_state enable row level security;
drop policy if exists "allow all" on app_state;
create policy "allow all" on app_state for all to anon using(true) with check(true);
alter table app_state replica identity full;
do $$ begin
  begin alter publication supabase_realtime add table app_state;
  exception when duplicate_object then null; end;
end $$;

-- [B] 품목 마스터 (itemmaster.html — 현재 404, 이 표가 없어서 화면이 깨짐)
create table if not exists item_master (
  id bigserial primary key,
  pno text, name text, cat text, spec text, mat text,
  price text, unit text, sup text, remark text,
  updated_at timestamptz default now()
);
alter table item_master enable row level security;
drop policy if exists "allow all" on item_master;
create policy "allow all" on item_master for all to anon using(true) with check(true);

-- [C] 수주 관리 (sales.html)
create table if not exists sales_order (
  id bigserial primary key,
  ono text, odate text, cust text, pno text, pname text,
  qty text, price text, due text, status text default '진행', remark text,
  updated_at timestamptz default now());
alter table sales_order enable row level security;
drop policy if exists "allow all" on sales_order;
create policy "allow all" on sales_order for all to anon using(true) with check(true);
alter table sales_order replica identity full;
do $$ begin
  begin alter publication supabase_realtime add table sales_order;
  exception when duplicate_object then null; end;
end $$;

-- [D] 업체 관리 (partners.html) — 고객사·공급사·외주 동일 양식
create table if not exists partners (
  id bigserial primary key, code text, gubun text default '고객사',
  name text, bizno text, ceo text, item text, bizType text, bizItem text,
  tel text, fax text, addr text, pay text, taxEmail text,
  mgrName text, mgrRole text, mgrMobile text, mgrEmail text,
  status text default '거래중', remark text, updated_at timestamptz default now());
alter table partners enable row level security;
drop policy if exists "allow all" on partners;
create policy "allow all" on partners for all to anon using(true) with check(true);
alter table partners replica identity full;
do $$ begin
  begin alter publication supabase_realtime add table partners;
  exception when duplicate_object then null; end;
end $$;
