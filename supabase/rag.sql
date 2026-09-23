create extension if not exists vector;

create table if not exists public.rag_documents (
  id text primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  source text not null,
  content text not null,
  chunk_id integer not null,
  embedding vector(384) not null,
  created_at timestamptz not null default now(),
  constraint rag_documents_user_id_source_chunk_id_key unique (user_id, source, chunk_id)
);

create index if not exists rag_documents_user_id_idx on public.rag_documents (user_id);
create index if not exists rag_documents_embedding_idx
on public.rag_documents
using ivfflat (embedding vector_cosine_ops) with (lists = 100);

alter table public.rag_documents enable row level security;

do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'rag_documents' and policyname = 'Users can read own rag documents') then
    create policy "Users can read own rag documents"
    on public.rag_documents for select
    to authenticated
    using ((select auth.uid()) = user_id);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'rag_documents' and policyname = 'Users can create own rag documents') then
    create policy "Users can create own rag documents"
    on public.rag_documents for insert
    to authenticated
    with check ((select auth.uid()) = user_id);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'rag_documents' and policyname = 'Users can update own rag documents') then
    create policy "Users can update own rag documents"
    on public.rag_documents for update
    to authenticated
    using ((select auth.uid()) = user_id)
    with check ((select auth.uid()) = user_id);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'rag_documents' and policyname = 'Users can delete own rag documents') then
    create policy "Users can delete own rag documents"
    on public.rag_documents for delete
    to authenticated
    using ((select auth.uid()) = user_id);
  end if;
end $$;

create or replace function public.match_rag_documents(
  query_embedding vector,
  match_user_id uuid,
  match_count integer default 4
)
returns table(id text, source text, content text, chunk_id integer, similarity real)
language sql
stable
set search_path = public
as $$
  select
    documents.id,
    documents.source,
    documents.content,
    documents.chunk_id,
    (1 - (documents.embedding <=> query_embedding))::real as similarity
  from public.rag_documents as documents
  where documents.user_id = match_user_id
  order by documents.embedding <=> query_embedding
  limit match_count;
$$;

create or replace function public.match_documents(
  query_embedding vector,
  match_count integer default 5,
  filter_user uuid default null
)
returns table(id text, source text, content text, similarity double precision)
language sql
stable
set search_path = public
as $$
  select
    documents.id,
    documents.source,
    documents.content,
    1 - (documents.embedding <=> query_embedding) as similarity
  from public.rag_documents as documents
  where filter_user is null or documents.user_id = filter_user
  order by documents.embedding <=> query_embedding
  limit match_count;
$$;
