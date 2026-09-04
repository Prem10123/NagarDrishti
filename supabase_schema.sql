-- Run this in the Supabase SQL Editor (once per project).
-- The FastAPI backend uses the service role key, which bypasses RLS.
-- Anon/authenticated clients should have no direct table or photo access.

create table if not exists public.users (
  id bigint generated always as identity primary key,
  mobile_number text unique not null,
  full_name text not null,
  password_hash text,
  swachhata_user_id integer,
  created_at timestamptz not null default now()
);

create table if not exists public.complaints (
  id bigint generated always as identity primary key,
  user_id bigint not null references public.users(id) on delete cascade,
  category_id integer not null,
  latitude double precision not null default 0,
  longitude double precision not null default 0,
  address text not null,
  landmark text,
  image_url text not null,
  description text,
  swachhata_complaint_id text,
  status text not null default 'Pending Sync',
  created_at timestamptz not null default now()
);

create index if not exists complaints_user_id_idx on public.complaints (user_id);
create index if not exists complaints_created_at_idx on public.complaints (created_at desc);

alter table public.users enable row level security;
alter table public.complaints enable row level security;

revoke all on public.users from anon, authenticated;
revoke all on public.complaints from anon, authenticated;
grant all on public.users to service_role;
grant all on public.complaints to service_role;

insert into storage.buckets (id, name, public)
values ('complaint-photos', 'complaint-photos', false)
on conflict (id) do update set public = false;

drop policy if exists "Public read complaint photos" on storage.objects;
drop policy if exists "Anyone can upload complaint photos" on storage.objects;
drop policy if exists "Public upload complaint photos" on storage.objects;
