-- Run this in the Supabase SQL Editor (once per project).

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

alter table public.users enable row level security;
alter table public.complaints enable row level security;

insert into storage.buckets (id, name, public)
values ('complaint-photos', 'complaint-photos', true)
on conflict (id) do nothing;

drop policy if exists "Public read complaint photos" on storage.objects;
create policy "Public read complaint photos"
on storage.objects for select
using (bucket_id = 'complaint-photos');
