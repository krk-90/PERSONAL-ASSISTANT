create extension if not exists pgcrypto;

create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null check (char_length(trim(title)) > 0),
  description text not null default '',
  status text not null default 'pending',
  priority text not null default 'medium',
  due_date timestamptz,
  tags text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  constraint tasks_status_check check (status in ('pending', 'in_progress', 'completed', 'cancelled')),
  constraint tasks_priority_check check (priority in ('low', 'medium', 'high', 'urgent'))
);

create index if not exists tasks_user_id_created_at_idx on public.tasks (user_id, created_at);
create index if not exists tasks_user_id_status_idx on public.tasks (user_id, status);
create index if not exists tasks_user_id_priority_idx on public.tasks (user_id, priority);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_tasks_updated_at on public.tasks;
create trigger set_tasks_updated_at
before update on public.tasks
for each row
execute function public.set_updated_at();

alter table public.tasks enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'tasks' and policyname = 'Users can read own tasks') then
    create policy "Users can read own tasks"
    on public.tasks for select
    to authenticated
    using ((select auth.uid()) = user_id);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'tasks' and policyname = 'Users can create own tasks') then
    create policy "Users can create own tasks"
    on public.tasks for insert
    to authenticated
    with check ((select auth.uid()) = user_id);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'tasks' and policyname = 'Users can update own tasks') then
    create policy "Users can update own tasks"
    on public.tasks for update
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'tasks' and policyname = 'Users can delete own tasks') then
    create policy "Users can delete own tasks"
    on public.tasks for delete
    to authenticated
    using ((select auth.uid()) = user_id);
  end if;
end $$;
