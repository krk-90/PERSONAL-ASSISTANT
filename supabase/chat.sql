create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'New Conversation',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system', 'tool')),
  content text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists conversations_user_id_updated_idx on public.conversations (user_id, updated_at desc);
create index if not exists messages_conversation_created_idx on public.messages (conversation_id, created_at);
create index if not exists messages_user_id_idx on public.messages (user_id);

alter table public.conversations enable row level security;
alter table public.messages enable row level security;

do $$
declare t text; c text;
begin
  foreach t in array array['conversations', 'messages'] loop
    for c in select unnest(array['select','insert','update','delete']) loop
      if not exists (select 1 from pg_policies where schemaname='public' and tablename=t and policyname='Users can '||c||' own '||t) then
        if c = 'insert' then
          execute format('create policy %I on public.%I for insert to authenticated with check ((select auth.uid()) = user_id)', 'Users can '||c||' own '||t, t);
        elsif c = 'update' then
          execute format('create policy %I on public.%I for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id)', 'Users can '||c||' own '||t, t);
        else
          execute format('create policy %I on public.%I for %s to authenticated using ((select auth.uid()) = user_id)', 'Users can '||c||' own '||t, t, c);
        end if;
      end if;
    end loop;
  end loop;
end $$;
